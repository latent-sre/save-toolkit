// Replace this optional Things fixture with the real app and isolated test identity/store.
// Keep its function/variable names so document and Schemathesis gates need no edits.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"testing"
)

const testToken = "test-token"

func testVerify(_ context.Context, token string) (Principal, error) {
	if token != testToken {
		return Principal{}, ErrInvalidToken
	}
	return Principal{Subject: "tester", Scopes: []string{"team:sre"}}, nil
}

func seededStore(n int) *ThingStore {
	things := make([]Thing, 0, n+1)
	for i := 1; i <= n; i++ {
		things = append(things, Thing{ID: fmt.Sprintf("thing-%04d", i), Name: fmt.Sprintf("Thing %d", i), Team: "sre"})
	}
	return NewThingStore(append(things, Thing{ID: "thing-other", Name: "Other", Team: "payments"})...)
}

func testHandler(t *testing.T, store *ThingStore) http.Handler {
	t.Helper()
	handler, _ := newService(Config{Addr: "127.0.0.1:0"}, testVerify, store)
	return handler
}

// contractService returns the real handler chain and its generated document.
func contractService(t *testing.T) (http.Handler, []byte) {
	t.Helper()
	handler, api := newService(Config{Addr: "127.0.0.1:0"}, testVerify, seededStore(30))
	doc, err := json.MarshalIndent(api.OpenAPI(), "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	return handler, append(doc, '\n')
}

// Authentication must be real in the handler; these values only describe the test identity.
var contractHeaders = map[string]string{"Authorization": "Bearer " + testToken}
var authenticatedSchemes = map[string]bool{"bearer": true}
var authErrorStatuses = []int{401, 503} // actual adapter failures; protected routes always require 401

// Deliberate unauthenticated operation IDs; health routes outside OpenAPI need no entry.
var publicOperations = map[string]bool{}
