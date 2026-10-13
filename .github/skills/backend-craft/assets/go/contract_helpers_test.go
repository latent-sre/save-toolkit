// Reusable HTTP assertions; no application, identity, or resource imports.
package main

import (
	"encoding/json"
	"mime"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

type reply struct {
	status int
	header http.Header
	body   map[string]any
}

func call(t *testing.T, h http.Handler, method, target string, headers ...string) reply {
	t.Helper()
	if len(headers)%2 != 0 {
		t.Fatal("request headers must be name/value pairs")
	}
	req := httptest.NewRequest(method, target, nil)
	req.Host = "127.0.0.1:8080"
	for i := 0; i+1 < len(headers); i += 2 {
		req.Header.Set(headers[i], headers[i+1])
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	r := reply{status: rec.Code, header: rec.Header()}
	if rec.Body.Len() > 0 && strings.Contains(rec.Header().Get("Content-Type"), "json") {
		if err := json.Unmarshal(rec.Body.Bytes(), &r.body); err != nil {
			t.Fatalf("%s %s: body is not JSON: %v\n%s", method, target, err, rec.Body.String())
		}
	}
	return r
}

// assertProblem checks the house error shape on any non-2xx answer.
func assertProblem(t *testing.T, r reply, status int) {
	t.Helper()
	if r.status != status {
		t.Fatalf("status %d, want %d: %v", r.status, status, r.body)
	}
	ct, _, err := mime.ParseMediaType(r.header.Get("Content-Type"))
	if err != nil || ct != "application/problem+json" {
		t.Fatalf("Content-Type %q, want application/problem+json", ct)
	}
	for _, field := range []string{"type", "title", "status", "request_id"} {
		if _, ok := r.body[field]; !ok {
			t.Fatalf("problem lacks %q: %v", field, r.body)
		}
	}
	if r.body["status"] != float64(status) {
		t.Fatalf("problem status %v, want %d", r.body["status"], status)
	}
	if r.body["request_id"] != r.header.Get("X-Request-ID") || r.body["request_id"] == "" {
		t.Fatalf("request_id %v does not match X-Request-ID %q", r.body["request_id"], r.header.Get("X-Request-ID"))
	}
	if _, ok := r.body["$schema"]; ok {
		t.Fatalf("problem carries $schema: %v", r.body)
	}
}

// assertRequestID checks any response, including successful and non-JSON responses.
func assertRequestID(t *testing.T, r reply) {
	t.Helper()
	if r.header.Get("X-Request-ID") == "" {
		t.Fatal("response has no X-Request-ID")
	}
}
