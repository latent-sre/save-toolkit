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
	_, api := newService(Config{Addr: "127.0.0.1:0"}, testVerify, NewThingStore())
	doc, err := json.MarshalIndent(api.OpenAPI(), "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	return append(doc, '\n')
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
	var doc struct {
		OpenAPI string `json:"openapi"`
		Paths   map[string]map[string]struct {
			OperationID string                    `json:"operationId"`
			Security    []map[string][]string     `json:"security"`
			Responses   map[string]map[string]any `json:"responses"`
			RequestBody map[string]any            `json:"requestBody"`
		} `json:"paths"`
	}
	if err := json.Unmarshal(generatedDocument(t), &doc); err != nil {
		t.Fatal(err)
	}
	if doc.OpenAPI != "3.1.0" {
		t.Errorf("openapi %q: emit 3.1.0, valid as 3.2", doc.OpenAPI)
	}
	ids := map[string]bool{}
	for path, ops := range doc.Paths {
		for method, op := range ops {
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
			if !publicOperations[op.OperationID] && !requiresBearer(op.Security) {
				t.Errorf("%s: declare Security: Bearer, or list it in publicOperations with Metadata: Public", where)
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
}

// publicOperations lists the operation IDs that deliberately need no authentication.
var publicOperations = map[string]bool{}

// requiresBearer reports whether every security alternative demands the bearer scheme: an empty
// alternative ({}) would allow anonymous access.
func requiresBearer(security []map[string][]string) bool {
	if len(security) == 0 {
		return false
	}
	for _, alternative := range security {
		if _, ok := alternative["bearer"]; !ok {
			return false
		}
	}
	return true
}
