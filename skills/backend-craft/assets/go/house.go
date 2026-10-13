// Optional common components for a Huma service: RFC 9457 problems, request IDs, router 404/405
// problems and cursor pages. Adapt the components the service needs. Authentication belongs to
// the service's existing middleware or the separate bearer adapter in auth.go.
package main

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"regexp"
	"strings"

	"github.com/danielgtaylor/huma/v2"
)

// Problem is the house error body: RFC 9457 plus request_id and, for invalid input, errors.
type Problem struct {
	Type      string       `json:"type" doc:"Stable identifier of the error class; about:blank when the status says it all."`
	Title     string       `json:"title"`
	Status    int          `json:"status"`
	Detail    string       `json:"detail,omitempty"`
	RequestID string       `json:"request_id" doc:"Equals the X-Request-ID response header and the server's log lines."`
	Errors    []FieldError `json:"errors,omitempty" nullable:"false"`
}

// FieldError locates one invalid input. It never echoes the submitted value, which may be a secret.
type FieldError struct {
	Loc []string `json:"loc" nullable:"false" doc:"Path to the invalid input, starting with body, query, path or header."`
	Msg string   `json:"msg"`
}

func (p *Problem) Error() string  { return p.Detail }
func (p *Problem) GetStatus() int { return p.Status }

// ContentType makes Huma declare and send application/problem+json for every Problem.
func (p *Problem) ContentType(ct string) string {
	if ct == "application/json" {
		return "application/problem+json"
	}
	return ct
}

func newProblem(status int, detail string) *Problem {
	return &Problem{Type: "about:blank", Title: http.StatusText(status), Status: status, Detail: detail}
}

// Huma builds every error through these two hooks, so they must be set before any operation is
// registered: registration reads the error type to document each declared error status.
func init() {
	huma.NewError = func(status int, msg string, errs ...error) huma.StatusError {
		p := newProblem(status, msg)
		for _, err := range errs {
			if err == nil {
				continue
			}
			if d, ok := err.(huma.ErrorDetailer); ok {
				detail := d.ErrorDetail()
				p.Errors = append(p.Errors, FieldError{Loc: splitLocation(detail.Location), Msg: detail.Message})
			} else {
				p.Errors = append(p.Errors, FieldError{Loc: []string{}, Msg: err.Error()})
			}
		}
		return p
	}
	huma.NewErrorWithContext = func(ctx huma.Context, status int, msg string, errs ...error) huma.StatusError {
		p := huma.NewError(status, msg, errs...).(*Problem)
		p.RequestID = RequestIDFrom(ctx.Context())
		return p
	}
}

// splitLocation turns Huma's "body.items[0].name" into ["body", "items", "0", "name"].
func splitLocation(location string) []string {
	if location == "" {
		return []string{}
	}
	location = strings.NewReplacer("[", ".", "]", "").Replace(location)
	return strings.Split(location, ".")
}

// stampRequestID fills request_id on problems created without a request context, such as
// huma.Error404NotFound returned from a handler.
func stampRequestID(ctx huma.Context, _ string, v any) (any, error) {
	if p, ok := v.(*Problem); ok && p.RequestID == "" {
		p.RequestID = RequestIDFrom(ctx.Context())
	}
	return v, nil
}

// Page is the house collection: the items plus an opaque cursor that is null on the last page.
// Return an empty slice, never nil: nil encodes as null and breaks the contract.
type Page[T any] struct {
	Data       []T     `json:"data" nullable:"false"`
	NextCursor *string `json:"next_cursor" doc:"Pass back as ?cursor= for the next page; null on the last page."`
}

type requestIDKey struct{}

// RequestIDFrom returns the request ID that WithRequestID stored, or "".
func RequestIDFrom(ctx context.Context) string {
	id, _ := ctx.Value(requestIDKey{}).(string)
	return id
}

var requestIDShape = regexp.MustCompile(`^[A-Za-z0-9._:-]{1,128}$`)

// WithRequestID gives every request an ID, echoed as X-Request-ID and carried in the context for
// handlers, problems and log lines. trustedHeader names a header that only a trusted ingress sets
// and overwrites (for example X-Vcap-Request-Id behind Gorouter, when nothing bypasses Gorouter);
// leave it empty to always generate. A trusted value is still shape-checked.
func WithRequestID(next http.Handler, trustedHeader string) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := ""
		if trustedHeader != "" {
			if v := r.Header.Get(trustedHeader); requestIDShape.MatchString(v) {
				id = v
			}
		}
		if id == "" {
			b := make([]byte, 16)
			_, _ = rand.Read(b)
			id = hex.EncodeToString(b)
		}
		w.Header().Set("X-Request-ID", id)
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), requestIDKey{}, id)))
	})
}

// statusCapture records what a handler would answer without writing it.
type statusCapture struct {
	header http.Header
	status int
}

func (c *statusCapture) Header() http.Header         { return c.header }
func (c *statusCapture) Write(b []byte) (int, error) { return len(b), nil }
func (c *statusCapture) WriteHeader(status int)      { c.status = status }

// WithProblemFallback answers requests that match no route (404) or no method (405, with Allow)
// with the house problem body instead of the router's plain text.
func WithProblemFallback(mux *http.ServeMux) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		handler, pattern := mux.Handler(r)
		if pattern != "" {
			mux.ServeHTTP(w, r)
			return
		}
		probe := &statusCapture{header: http.Header{}, status: http.StatusOK}
		handler.ServeHTTP(probe, r)
		if allow := probe.header.Get("Allow"); allow != "" {
			w.Header().Set("Allow", allow)
		}
		WriteProblem(w, r, newProblem(probe.status, ""))
	})
}

// WriteProblem sends a problem outside a Huma operation, such as from net/http middleware.
func WriteProblem(w http.ResponseWriter, r *http.Request, p *Problem) {
	p.RequestID = RequestIDFrom(r.Context())
	w.Header().Set("Content-Type", "application/problem+json")
	w.WriteHeader(p.Status)
	_ = json.NewEncoder(w).Encode(p)
}

// HouseConfig supplies common document/error configuration only; it installs no authentication
// or request middleware. Wire the service's SSO middleware before registering shared internal
// operations, and wrap the handler with WithRequestID and WithProblemFallback as applicable.
func HouseConfig(title, version string) huma.Config {
	config := huma.DefaultConfig(title, version)
	// No $schema property or Link header in response bodies: the committed document is the contract.
	config.CreateHooks = nil
	config.Transformers = append(config.Transformers, stampRequestID)
	return config
}
