// Tests for the optional bearer adapter, independent of the example service and resource.
package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/danielgtaylor/huma/v2"
)

func TestMissingVerifierFailsClosed(t *testing.T) {
	for _, declared := range []bool{false, true} {
		for _, authorization := range []string{"", "Bearer supplied-token"} {
			t.Run(fmtAuthCase(declared, authorization), func(t *testing.T) {
				mux := http.NewServeMux()
				api := NewAPI(mux, "Probe", "1.0.0", nil)
				op := huma.Operation{OperationID: "protectedProbe", Method: "GET", Path: "/v1/probe"}
				if declared {
					op.Security = Bearer
				}
				huma.Register(api, op, func(context.Context, *struct{}) (*struct{}, error) {
					t.Error("protected handler reached without a verifier")
					return nil, nil
				})
				req := httptest.NewRequest("GET", "/v1/probe", nil)
				req.Header.Set("Authorization", authorization)
				rec := httptest.NewRecorder()
				WithRequestID(mux, "").ServeHTTP(rec, req)
				if rec.Code != http.StatusServiceUnavailable {
					t.Fatalf("missing verifier answered %d, want 503: %s", rec.Code, rec.Body.String())
				}
				if rec.Header().Get("Content-Type") != "application/problem+json" || rec.Header().Get("X-Request-ID") == "" {
					t.Fatal("missing verifier response lost the common problem/request-ID behavior")
				}
			})
		}
	}
}

func fmtAuthCase(declared bool, authorization string) string {
	name := "unmarked"
	if declared {
		name = "declared"
	}
	if authorization == "" {
		return name + "/missing-token"
	}
	return name + "/supplied-token"
}

func TestBearerAdapterRequiresAuthenticationByDefault(t *testing.T) {
	for _, tc := range []struct {
		name     string
		metadata map[string]any
		security []map[string][]string
		public   bool
	}{
		{name: "unmarked"},
		{name: "protected", security: Bearer},
		{name: "public", metadata: Public, public: true},
		{name: "public-with-security", metadata: Public, security: Bearer},
	} {
		for _, token := range []string{"", "Bearer invalid", "Bearer valid"} {
			t.Run(tc.name+"/"+token, func(t *testing.T) {
				mux := http.NewServeMux()
				api := NewAPI(mux, "Probe", "1.0.0", func(_ context.Context, token string) (Principal, error) {
					if token == "valid" {
						return Principal{Subject: "caller"}, nil
					}
					return Principal{}, ErrInvalidToken
				})
				huma.Register(api, huma.Operation{
					OperationID: "probe", Method: "GET", Path: "/v1/probe",
					Metadata: tc.metadata, Security: tc.security,
				}, func(ctx context.Context, _ *struct{}) (*struct{}, error) {
					principal, authenticated := PrincipalFrom(ctx)
					if authenticated == tc.public || (!tc.public && principal.Subject != "caller") {
						t.Errorf("principal = %+v, authenticated = %v, public = %v", principal, authenticated, tc.public)
					}
					return nil, nil
				})
				req := httptest.NewRequest("GET", "/v1/probe", nil)
				req.Header.Set("Authorization", token)
				rec := httptest.NewRecorder()
				WithRequestID(mux, "").ServeHTTP(rec, req)
				want := http.StatusUnauthorized
				if tc.public || token == "Bearer valid" {
					want = http.StatusNoContent
				}
				if rec.Code != want {
					t.Fatalf("got %d, want %d: %s", rec.Code, want, rec.Body.String())
				}
				if want == http.StatusUnauthorized {
					if rec.Header().Get("Content-Type") != "application/problem+json" {
						t.Fatal("401 must use the common problem body")
					}
					if rec.Header().Get("WWW-Authenticate") != "Bearer" {
						t.Fatal("401 must carry the bearer challenge")
					}
				}
			})
		}
	}
}

func TestDeclareAuthErrorsClonesSharedMaps(t *testing.T) {
	shared := map[string]*huma.MediaType{"application/problem+json": {}}
	newOperation := func() *huma.Operation {
		return &huma.Operation{
			Security: Bearer, Metadata: Public,
			Responses: map[string]*huma.Response{
				"500": {Description: "Internal Server Error", Content: shared},
			},
		}
	}
	first, second := newOperation(), newOperation()
	declareAuthErrors(nil, first)
	declareAuthErrors(nil, second)

	first.Security[0]["bearer"] = append(first.Security[0]["bearer"], "mutated")
	first.Metadata["public"] = false
	delete(first.Responses["401"].Content, "application/problem+json")

	if len(Bearer[0]["bearer"]) != 0 {
		t.Fatal("mutating one operation's security mutated the shared Bearer requirement")
	}
	if Public["public"] != true {
		t.Fatal("mutating one operation's metadata mutated the shared Public marker")
	}
	if len(second.Security[0]["bearer"]) != 0 || second.Metadata["public"] != true {
		t.Fatal("operations sharing Bearer/Public must receive independent maps")
	}
	if _, ok := second.Responses["401"].Content["application/problem+json"]; !ok {
		t.Fatal("mutating one operation's 401 content mutated another operation")
	}
	if _, ok := first.Responses["503"].Content["application/problem+json"]; !ok {
		t.Fatal("401 and 503 responses of one operation must not share a content map")
	}
}

func TestPublicOperationDoesNotNeedVerifier(t *testing.T) {
	mux := http.NewServeMux()
	api := NewAPI(mux, "Probe", "1.0.0", nil)
	huma.Register(api, huma.Operation{
		OperationID: "publicProbe", Method: "GET", Path: "/v1/probe", Metadata: Public,
	}, func(context.Context, *struct{}) (*struct{}, error) { return nil, nil })
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, httptest.NewRequest("GET", "/v1/probe", nil))
	if rec.Code != http.StatusNoContent {
		t.Fatalf("explicit public operation answered %d", rec.Code)
	}
}
