// TestSchemathesis drives the real handler from its own document with Schemathesis (the st
// command): every operation, with valid and invalid inputs, must answer as the document says,
// never with a 500. The replaceable service fixture owns the app and test identity headers.
// Locally it skips without st (uv tool install schemathesis); in CI a missing st fails.
package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestSchemathesis(t *testing.T) {
	st, err := exec.LookPath("st")
	if err != nil {
		if os.Getenv("CI") != "" {
			t.Fatal("st (Schemathesis) must be installed in CI")
		}
		t.Skip("st not installed: uv tool install schemathesis")
	}
	if contractHeaders == nil || (len(authenticatedSchemes) > 0 && len(contractHeaders) == 0) {
		t.Fatal("configure isolated test identity headers in the service fixture")
	}
	handler, document := contractService(t)
	server := httptest.NewServer(handler)
	defer server.Close()
	// The fixture supplies identity, so Schemathesis does not generate security parameters; the
	// service ignores query parameters it does not declare, so an extra one is not invalid input.
	for name, value := range contractHeaders {
		if name == "" || value == "" {
			t.Fatal("test identity header name/value must not be empty")
		}
	}
	var doc struct {
		Paths map[string]map[string]json.RawMessage `json:"paths"`
	}
	if err := json.Unmarshal(document, &doc); err != nil {
		t.Fatal(err)
	}
	groups := map[bool][]string{}
	for _, item := range doc.Paths {
		for method, raw := range item {
			switch method {
			case "get", "put", "post", "delete", "options", "head", "patch", "trace":
			default:
				continue
			}
			var op struct {
				OperationID string `json:"operationId"`
			}
			if err := json.Unmarshal(raw, &op); err != nil {
				t.Fatal(err)
			}
			public := publicOperations[op.OperationID]
			groups[public] = append(groups[public], op.OperationID)
		}
	}
	for _, public := range []bool{false, true} {
		ids := groups[public]
		if len(ids) == 0 {
			continue
		}
		name := "authenticated"
		if public {
			name = "anonymous"
		}
		t.Run(name, func(t *testing.T) {
			baseURL := server.URL
			if public {
				// Inspect every anonymous response, including invalid inputs, without
				// changing schema checks or buffering the handler's streaming responses.
				target, err := url.Parse(server.URL)
				if err != nil {
					t.Fatal(err)
				}
				proxy := httputil.NewSingleHostReverseProxy(target)
				proxy.ModifyResponse = func(response *http.Response) error {
					if response.StatusCode == 401 || response.StatusCode == 403 {
						t.Errorf("public operation requires authentication: HTTP %d", response.StatusCode)
					}
					return nil
				}
				anonymous := httptest.NewServer(proxy)
				defer anonymous.Close()
				baseURL = anonymous.URL
			}
			config := filepath.Join(t.TempDir(), "schemathesis.toml")
			settings := "[generation]\nallow-extra-parameters = false\nwith-security-parameters = false\n"
			if err := os.WriteFile(config, []byte(settings), 0o644); err != nil {
				t.Fatal(err)
			}
			args := []string{"--config-file", config, "run", documentPath, "--url", baseURL, "--max-examples", "25"}
			for _, id := range ids {
				args = append(args, "--include-operation-id", id)
			}
			if !public {
				for name, value := range contractHeaders {
					args = append(args, "-H", name+": "+value)
				}
			}
			cmd := exec.Command(st, args...)
			cmd.Env = append(os.Environ(), "PYTHONUTF8=1") // Windows pipes otherwise default to cp1252
			out, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatalf("Schemathesis found responses that break the document:\n%s", out)
			}
		})
	}
}
