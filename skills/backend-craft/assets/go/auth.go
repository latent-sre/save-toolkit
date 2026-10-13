// Optional bearer-authentication adapter. Prefer the service's established corporate SSO
// middleware; use this adapter only when verified bearer tokens are its chosen boundary.
// It depends on house.go, but does not require the example main.go or things.go.
package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"strings"

	"github.com/danielgtaylor/huma/v2"
	"github.com/danielgtaylor/huma/v2/adapters/humago"
)

// Principal is the authenticated caller for this adapter; map it to the application's identity.
type Principal struct {
	Subject string
	Scopes  []string
}

type principalKey struct{}

// PrincipalFrom returns the caller that RequireAuth authenticated, or false on a public operation.
func PrincipalFrom(ctx context.Context) (Principal, bool) {
	p, ok := ctx.Value(principalKey{}).(Principal)
	return p, ok
}

// TokenVerifier checks a bearer token using the service's identity integration. It returns
// ErrInvalidToken for an expired or forged token; any other error means verification failed
// (for example, an unreachable identity provider), which is a 503, not a 401.
type TokenVerifier func(ctx context.Context, token string) (Principal, error)

// ErrInvalidToken is the verifier's answer for a token that does not authenticate anyone.
var ErrInvalidToken = errors.New("invalid bearer token")

// Public marks an operation that needs no authentication: set Metadata: Public and leave Security
// empty. Every other operation is authenticated, even one that forgot to declare Bearer, and the
// example document test fails until it declares it.
var Public = map[string]any{"public": true}

// RequireAuth authenticates every operation not marked Public, answering 401 with
// WWW-Authenticate when the token is missing or invalid. A nil verifier fails closed with 503.
// Object-level authorization stays in the handler, which knows the object.
func RequireAuth(api huma.API, verify TokenVerifier) func(huma.Context, func(huma.Context)) {
	return func(ctx huma.Context, next func(huma.Context)) {
		op := ctx.Operation()
		if len(op.Security) == 0 && op.Metadata["public"] == true {
			next(ctx)
			return
		}
		if verify == nil {
			_ = huma.WriteErr(api, ctx, http.StatusServiceUnavailable, "Credentials could not be verified; try again shortly.")
			return
		}
		token, found := strings.CutPrefix(ctx.Header("Authorization"), "Bearer ")
		principal, err := Principal{}, ErrInvalidToken
		if found && token != "" {
			principal, err = verify(ctx.Context(), token)
		}
		switch {
		case errors.Is(err, ErrInvalidToken):
			ctx.SetHeader("WWW-Authenticate", `Bearer`)
			_ = huma.WriteErr(api, ctx, http.StatusUnauthorized, "A valid bearer token is required.")
		case err != nil:
			slog.WarnContext(ctx.Context(), "token verification failed", "error_type", fmt.Sprintf("%T", err))
			_ = huma.WriteErr(api, ctx, http.StatusServiceUnavailable, "Credentials could not be verified; try again shortly.")
		default:
			next(huma.WithValue(ctx, principalKey{}, principal))
		}
	}
}

// NewAPI builds a protected Huma API with the common configuration and this bearer adapter.
// Register operations after it. Unmarked operations require authentication; nil verify returns
// 503 for every protected request. Public operations require explicit Metadata: Public.
func NewAPI(mux *http.ServeMux, title, version string, verify TokenVerifier) huma.API {
	config := HouseConfig(title, version)
	config.Components.SecuritySchemes = map[string]*huma.SecurityScheme{
		"bearer": {Type: "http", Scheme: "bearer"},
	}
	api := humago.New(mux, config)
	api.OpenAPI().OnAddOperation = append(api.OpenAPI().OnAddOperation, declareAuthErrors)
	api.UseMiddleware(RequireAuth(api, verify))
	return api
}

// declareAuthErrors documents the 401 and the verifier-outage 503 that RequireAuth can send on
// every declared authenticated operation, with the same Problem body as the operation's 500.
func declareAuthErrors(_ *huma.OpenAPI, op *huma.Operation) {
	problem := op.Responses["500"]
	if len(op.Security) == 0 || problem == nil {
		return
	}
	for status, description := range map[string]string{"401": "Unauthorized", "503": "Service Unavailable"} {
		if op.Responses[status] == nil {
			op.Responses[status] = &huma.Response{Description: description, Content: problem.Content}
		}
	}
}

// Bearer is the security requirement for an authenticated operation using this adapter.
var Bearer = []map[string][]string{{"bearer": {}}}
