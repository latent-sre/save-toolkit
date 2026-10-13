// The committed OpenAPI document is the contract. TestOpenAPIDocument fails when the code and
// openapi.json disagree; after an intended API change, regenerate it and review the diff:
//
//	go test -run TestOpenAPIDocument -update
//
// TestOpenAPIHouseRules fails when an operation breaks a house rule the generator cannot know.
package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

var update = flag.Bool("update", false, "rewrite openapi.json from the code")

// documentPath is openapi.json at the module root, wherever the main package lives.
var documentPath = moduleRootFile("openapi.json")

func moduleRootFile(name string) string {
	dir, err := os.Getwd()
	if err != nil {
		return name
	}
	for d := dir; ; d = filepath.Dir(d) {
		if _, err := os.Stat(filepath.Join(d, "go.mod")); err == nil {
			return filepath.Join(d, name)
		}
		if filepath.Dir(d) == d {
			return name
		}
	}
}

func generatedDocument(t *testing.T) []byte {
	t.Helper()
	_, doc := contractService(t)
	return doc
}

func TestOpenAPIDocument(t *testing.T) {
	got := generatedDocument(t)
	if *update {
		if err := os.WriteFile(documentPath, got, 0o644); err != nil {
			t.Fatal(err)
		}
		return
	}
	want, err := os.ReadFile(documentPath)
	if err != nil {
		t.Fatalf("%v: generate it with go test -run TestOpenAPIDocument -update", err)
	}
	if !bytes.Equal(bytes.ReplaceAll(want, []byte("\r\n"), []byte("\n")), got) {
		t.Fatal("openapi.json differs from the code: run go test -run TestOpenAPIDocument -update, " +
			"then review the document diff as the API change it is")
	}
}

var operationIDShape = regexp.MustCompile(`^[a-z][A-Za-z0-9]*$`)
var versionedPath = regexp.MustCompile(`^/v[0-9]+/`)

func TestOpenAPIHouseRules(t *testing.T) {
	if authenticatedSchemes == nil {
		t.Fatal("configure authenticatedSchemes in the service fixture; use an explicit empty map for a public-only API")
	}
	var doc struct {
		OpenAPI    string                `json:"openapi"`
		Security   []map[string][]string `json:"security"`
		Components struct {
			SecuritySchemes map[string]json.RawMessage `json:"securitySchemes"`
		} `json:"components"`
		Paths map[string]map[string]json.RawMessage `json:"paths"`
	}
	type operation struct {
		OperationID string                    `json:"operationId"`
		Security    json.RawMessage           `json:"security"`
		Responses   map[string]map[string]any `json:"responses"`
		RequestBody map[string]any            `json:"requestBody"`
	}
	if err := json.Unmarshal(generatedDocument(t), &doc); err != nil {
		t.Fatal(err)
	}
	if doc.OpenAPI != "3.1.0" {
		t.Errorf("openapi %q: emit 3.1.0, valid as 3.2", doc.OpenAPI)
	}
	for name := range authenticatedSchemes {
		if _, declared := doc.Components.SecuritySchemes[name]; !declared {
			t.Errorf("configured authentication scheme %q is not declared", name)
		}
	}
	ids := map[string]bool{}
	authFailures := map[int]bool{401: true}
	for _, status := range authErrorStatuses {
		authFailures[status] = true
	}
	for path, ops := range doc.Paths {
		for method, raw := range ops {
			switch method {
			case "get", "put", "post", "delete", "options", "head", "patch", "trace":
			default:
				continue // Path-item parameters, summary and other metadata are not operations.
			}
			var op operation
			if err := json.Unmarshal(raw, &op); err != nil {
				t.Fatal(err)
			}
			where := strings.ToUpper(method) + " " + path
			if ids[op.OperationID] {
				t.Errorf("%s: operationId %q is not unique; generated clients use it", where, op.OperationID)
			}
			ids[op.OperationID] = true
			if !versionedPath.MatchString(path) {
				t.Errorf("%s: API paths start with a version, /v1/", where)
			}
			if !operationIDShape.MatchString(op.OperationID) {
				t.Errorf("%s: operationId %q must be a lowerCamel name; generated clients use it", where, op.OperationID)
			}
			security := doc.Security
			if op.Security != nil {
				// Decode into fresh storage: unmarshalling into inherited slice/maps can
				// retain scheme keys and turn an anonymous override into apparent auth.
				var override []map[string][]string
				if err := json.Unmarshal(op.Security, &override); err != nil {
					t.Fatal(err)
				}
				security = override
			}
			for _, alternative := range security {
				for name := range alternative {
					if _, declared := doc.Components.SecuritySchemes[name]; !declared {
						t.Errorf("%s: security scheme %q is not declared", where, name)
					}
				}
			}
			if publicOperations[op.OperationID] && len(security) != 0 {
				t.Errorf("%s: public operation must have empty effective security", where)
			} else if !publicOperations[op.OperationID] && !requiresAuthentication(security, doc.Components.SecuritySchemes) {
				t.Errorf("%s: every security alternative must require a declared authenticated scheme; list deliberate anonymous operations in publicOperations", where)
			}
			if !publicOperations[op.OperationID] {
				for status := range authFailures {
					if _, declared := op.Responses[strconv.Itoa(status)]; !declared {
						t.Errorf("%s: declare authentication failure %d", where, status)
					}
				}
			}
			if _, declared := op.Responses["400"]; op.RequestBody != nil && !declared {
				t.Errorf("%s: a body can be unparseable; list 400 in Errors", where)
			}
			for status, response := range op.Responses {
				code, _ := strconv.Atoi(status)
				content, _ := response["content"].(map[string]any)
				if _, ok := content["application/problem+json"]; code >= 400 && !ok {
					t.Errorf("%s: %s response must be application/problem+json", where, status)
				}
			}
		}
	}
	if len(ids) == 0 {
		t.Error("document contains no HTTP operations")
	}
}

// Every OR alternative must include a configured authentication scheme; all named schemes
// must be declared. In particular [] and [{}] permit anonymous access and fail this check.
func requiresAuthentication(security []map[string][]string, declared map[string]json.RawMessage) bool {
	if len(security) == 0 {
		return false
	}
	for _, alternative := range security {
		authenticated := false
		for name := range alternative {
			if _, ok := declared[name]; !ok {
				return false
			}
			authenticated = authenticated || authenticatedSchemes[name]
		}
		if !authenticated {
			return false
		}
	}
	return true
}
