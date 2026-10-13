// Optional example-service tests: they drive the complete handler chain. Adapt the seed,
// requests and relevant assertions to the service's resource, identity and behavior. Preserve
// authentication, object-access and HTTP-contract checks for the behavior the service retains.
package main

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func authed(h http.Handler, t *testing.T, method, target string) reply {
	return call(t, h, method, target, "Authorization", "Bearer "+testToken)
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

func TestEmptyPageSizeMatchesTheDocument(t *testing.T) {
	r := authed(testHandler(t, seededStore(1)), t, "GET", "/v1/things?limit=")
	assertProblem(t, r, http.StatusUnprocessableEntity)
	errs, _ := r.body["errors"].([]any)
	if len(errs) == 0 {
		t.Fatal("empty limit must identify the invalid query parameter")
	}
	location, _ := errs[0].(map[string]any)["loc"].([]any)
	if len(location) != 2 || location[0] != "query" || location[1] != "limit" {
		t.Fatalf("empty limit location = %v, want [query limit]", location)
	}
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
		assertRequestID(t, call(t, h, "GET", target))
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

func TestFailedReadinessIsAProblem(t *testing.T) {
	store := seededStore(1)
	store.readyErr = errors.New("database unreachable")
	assertProblem(t, call(t, testHandler(t, store), "GET", "/health/ready"), http.StatusServiceUnavailable)
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
