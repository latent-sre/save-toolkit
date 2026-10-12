// House contract tests: they drive the real handler chain, so a change that breaks the error,
// request-ID, page or authentication contract fails here. Adapt the seed and the requests to the
// service's resource; keep every assertion.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
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

type reply struct {
	status int
	header http.Header
	body   map[string]any
}

func call(t *testing.T, h http.Handler, method, target string, headers ...string) reply {
	t.Helper()
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

func authed(h http.Handler, t *testing.T, method, target string) reply {
	return call(t, h, method, target, "Authorization", "Bearer "+testToken)
}

// assertProblem checks the house error shape on any non-2xx answer.
func assertProblem(t *testing.T, r reply, status int) {
	t.Helper()
	if r.status != status {
		t.Fatalf("status %d, want %d: %v", r.status, status, r.body)
	}
	if ct := r.header.Get("Content-Type"); !strings.HasPrefix(ct, "application/problem+json") {
		t.Fatalf("Content-Type %q, want application/problem+json", ct)
	}
	for _, field := range []string{"type", "title", "status", "request_id"} {
		if _, ok := r.body[field]; !ok {
			t.Fatalf("problem lacks %q: %v", field, r.body)
		}
	}
	if int(r.body["status"].(float64)) != status {
		t.Fatalf("problem status %v, want %d", r.body["status"], status)
	}
	if r.body["request_id"] != r.header.Get("X-Request-ID") || r.body["request_id"] == "" {
		t.Fatalf("request_id %v does not match X-Request-ID %q", r.body["request_id"], r.header.Get("X-Request-ID"))
	}
	if _, ok := r.body["$schema"]; ok {
		t.Fatalf("problem carries $schema: %v", r.body)
	}
}

func TestErrorsAreProblems(t *testing.T) {
	h := testHandler(t, seededStore(3))
	assertProblem(t, call(t, h, "GET", "/v1/things"), http.StatusUnauthorized)
	assertProblem(t, call(t, h, "GET", "/v1/things", "Authorization", "Bearer wrong"), http.StatusUnauthorized)
	assertProblem(t, authed(h, t, "GET", "/v1/things/missing"), http.StatusNotFound)
	assertProblem(t, authed(h, t, "GET", "/v1/no-such-route"), http.StatusNotFound)
	assertProblem(t, authed(h, t, "GET", "/v1/things?limit=0"), http.StatusUnprocessableEntity)
	assertProblem(t, authed(h, t, "GET", "/v1/things?cursor=%21%21"), http.StatusUnprocessableEntity)
	assertProblem(t, authed(h, t, "GET", "/v1/things?cursor="), http.StatusUnprocessableEntity)

	r := authed(h, t, "DELETE", "/v1/things")
	assertProblem(t, r, http.StatusMethodNotAllowed)
	if !strings.Contains(r.header.Get("Allow"), "GET") {
		t.Fatalf("405 without Allow: %v", r.header)
	}
}

func TestVerifierOutageIsNotAnAuthFailure(t *testing.T) {
	down := func(context.Context, string) (Principal, error) {
		return Principal{}, errors.New("identity provider unreachable")
	}
	handler, _ := newService(Config{Addr: "127.0.0.1:0"}, down, seededStore(1))
	assertProblem(t, authed(handler, t, "GET", "/v1/things"), http.StatusServiceUnavailable)
}

func TestUnauthorizedNamesTheScheme(t *testing.T) {
	r := call(t, testHandler(t, seededStore(1)), "GET", "/v1/things")
	if r.header.Get("WWW-Authenticate") == "" {
		t.Fatal("401 without WWW-Authenticate")
	}
}

func TestValidationErrorsLocateTheInput(t *testing.T) {
	r := authed(testHandler(t, seededStore(1)), t, "GET", "/v1/things?limit=0")
	errs, _ := r.body["errors"].([]any)
	if len(errs) == 0 {
		t.Fatalf("422 without errors[]: %v", r.body)
	}
	first := errs[0].(map[string]any)
	loc, _ := first["loc"].([]any)
	if len(loc) != 2 || loc[0] != "query" || loc[1] != "limit" || first["msg"] == "" {
		t.Fatalf("errors[0] = %v, want loc [query limit] and a msg", first)
	}
	if _, echoed := first["value"]; echoed {
		t.Fatalf("errors[0] echoes the submitted value: %v", first)
	}
}

func TestEveryResponseCarriesARequestID(t *testing.T) {
	h := testHandler(t, seededStore(1))
	for _, target := range []string{"/health/live", "/v1/things", "/v1/nope"} {
		if call(t, h, "GET", target).header.Get("X-Request-ID") == "" {
			t.Fatalf("GET %s: no X-Request-ID", target)
		}
	}
	// A client-sent ID is not trusted unless the ingress header is configured.
	r := call(t, h, "GET", "/health/live", "X-Request-ID", "spoofed")
	if r.header.Get("X-Request-ID") == "spoofed" {
		t.Fatal("echoed an untrusted client request ID")
	}
}

func TestCursorPagesWalkTheCollectionOnce(t *testing.T) {
	h := testHandler(t, seededStore(501))
	seen := map[string]bool{}
	target := "/v1/things?limit=1000" // above the maximum: lowered, not rejected
	for pages := 0; ; pages++ {
		if pages > 10 {
			t.Fatal("pagination did not end")
		}
		r := authed(h, t, "GET", target)
		if r.status != http.StatusOK {
			t.Fatalf("GET %s: %d %v", target, r.status, r.body)
		}
		data, ok := r.body["data"].([]any)
		if !ok {
			t.Fatalf("data is not an array: %v", r.body["data"])
		}
		if len(data) > maxPageSize {
			t.Fatalf("page of %d exceeds the %d cap", len(data), maxPageSize)
		}
		for _, item := range data {
			id := item.(map[string]any)["id"].(string)
			if seen[id] {
				t.Fatalf("%s returned twice", id)
			}
			seen[id] = true
		}
		next, present := r.body["next_cursor"]
		if !present {
			t.Fatal("next_cursor missing; it must be present and null on the last page")
		}
		if next == nil {
			break
		}
		target = "/v1/things?limit=1000&cursor=" + next.(string)
	}
	if len(seen) != 501 {
		t.Fatalf("walked %d things, want 501", len(seen))
	}
	if seen["thing-other"] {
		t.Fatal("listed a thing outside the caller's teams")
	}
}

func TestEmptyPageIsAnEmptyArray(t *testing.T) {
	r := authed(testHandler(t, NewThingStore()), t, "GET", "/v1/things")
	if data, ok := r.body["data"].([]any); !ok || len(data) != 0 || r.body["next_cursor"] != nil {
		t.Fatalf("empty collection = %v, want data [] and next_cursor null", r.body)
	}
}

func TestObjectAuthorization(t *testing.T) {
	h := testHandler(t, seededStore(1))
	if r := authed(h, t, "GET", "/v1/things/thing-0001"); r.status != http.StatusOK {
		t.Fatalf("own team's thing: %d %v", r.status, r.body)
	}
	assertProblem(t, authed(h, t, "GET", "/v1/things/thing-other"), http.StatusNotFound)
}

func TestLoopbackServiceRefusesForeignHosts(t *testing.T) {
	h := testHandler(t, seededStore(1))
	req := httptest.NewRequest("GET", "/v1/things", nil)
	req.Host = "attacker.example:8080" // a DNS-rebinding page sends its own name
	req.Header.Set("Authorization", "Bearer "+testToken)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusMisdirectedRequest {
		t.Fatalf("foreign Host answered %d, want 421", rec.Code)
	}
}

func TestCrossSiteWritesAreRefused(t *testing.T) {
	r := call(t, testHandler(t, seededStore(1)), "POST", "/v1/things",
		"Authorization", "Bearer "+testToken, "Sec-Fetch-Site", "cross-site")
	assertProblem(t, r, http.StatusForbidden)
}

func TestConfigComesFromTheEnvironment(t *testing.T) {
	env := func(vars map[string]string) func(string) string { return func(k string) string { return vars[k] } }
	if cfg, err := loadConfig(env(nil)); err != nil || cfg.Addr != "127.0.0.1:8080" {
		t.Fatalf("default = %+v, %v; want loopback", cfg, err)
	}
	if cfg, err := loadConfig(env(map[string]string{"PORT": "8081"})); err != nil || cfg.Addr != ":8081" {
		t.Fatalf("PORT = %+v, %v", cfg, err)
	}
	if _, err := loadConfig(env(map[string]string{"PORT": "eighty"})); err == nil {
		t.Fatal("an invalid PORT must stop startup")
	}
}
