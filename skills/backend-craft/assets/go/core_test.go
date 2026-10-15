// Common-component tests: house.go plus contract_helpers_test.go; no auth or domain example.
package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/danielgtaylor/huma/v2"
	"github.com/danielgtaylor/huma/v2/adapters/humago"
)

func TestHouseComponentsWithoutStarter(t *testing.T) {
	mux := http.NewServeMux()
	api := humago.New(mux, HouseConfig("Existing service", "2.0.0"))
	// Authentication belongs to the consuming service's middleware. This test registers only
	// an explicitly public probe; HouseConfig does not install an authentication policy.
	huma.Register(api, huma.Operation{
		OperationID: "publicProbe", Method: "GET", Path: "/v1/probe",
		Metadata: map[string]any{"public": true}, Errors: []int{404, 422},
	}, func(_ context.Context, _ *struct {
		Limit int `query:"limit" minimum:"1" default:"1"`
	}) (*struct{ Body Page[string] }, error) {
		return nil, huma.Error404NotFound("No result.")
	})
	handler := WithRequestID(WithProblemFallback(mux), "")
	for _, tc := range []struct {
		method string
		path   string
		status int
	}{
		{"GET", "/v1/probe", 404},
		{"GET", "/v1/probe?limit=0", 422},
		{"GET", "/v1/missing", 404},
		{"DELETE", "/v1/probe", 405},
	} {
		t.Run(tc.method+tc.path, func(t *testing.T) {
			rec := httptest.NewRecorder()
			req := httptest.NewRequest(tc.method, tc.path, nil)
			req.Header.Set("X-Request-ID", "spoofed")
			handler.ServeHTTP(rec, req)
			var body map[string]any
			if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
				t.Fatal(err)
			}
			assertProblem(t, reply{status: rec.Code, header: rec.Header(), body: body}, tc.status)
			if rec.Header().Get("X-Request-ID") == "spoofed" {
				t.Fatal("echoed an untrusted client request ID")
			}
			if tc.status == 422 {
				errs, _ := body["errors"].([]any)
				if len(errs) == 0 {
					t.Fatal("422 must locate the invalid query parameter")
				}
				first := errs[0].(map[string]any)
				loc, _ := first["loc"].([]any)
				msg, _ := first["msg"].(string)
				if len(loc) != 2 || loc[0] != "query" || loc[1] != "limit" || msg == "" {
					t.Fatalf("invalid error location/message: %v", first)
				}
				for _, key := range []string{"input", "value"} {
					if _, present := first[key]; present {
						t.Fatalf("error echoes submitted %s", key)
					}
				}
			}
			if rec.Header().Get("Link") != "" {
				t.Fatal("problem advertises a generated schema")
			}
			if tc.status == 405 && !strings.Contains(rec.Header().Get("Allow"), "GET") {
				t.Fatal("405 lost the router's Allow header")
			}
		})
	}
	document, err := json.Marshal(api.OpenAPI())
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(document), "application/problem+json") ||
		!strings.Contains(string(document), `"request_id"`) || strings.Contains(string(document), `"$schema"`) {
		t.Fatalf("common document configuration lost: %s", document)
	}
	if len(api.OpenAPI().Components.SecuritySchemes) != 0 {
		t.Fatal("common configuration must not claim to install authentication")
	}
}
