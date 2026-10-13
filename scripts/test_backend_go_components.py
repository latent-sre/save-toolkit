"""Run Go backend components independently and retain the optional starter's security checks."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parents[1] / "skills/backend-craft/assets/go"


@pytest.mark.parametrize("component, files", [
    ("common", ["house.go", "core_test.go", "contract_helpers_test.go"]),
    ("bearer", ["house.go", "auth.go", "auth_test.go"]),
    ("starter", ["house.go", "auth.go", "main.go", "things.go", "house_test.go",
                 "auth_test.go", "core_test.go", "openapi_test.go",
                 "contract_helpers_test.go", "example_fixture_test.go", "schemathesis_test.go"]),
    ("cookie", ["house.go", "contract_helpers_test.go", "openapi_test.go",
                "schemathesis_test.go"]),
])
def test_go_components(tmp_path, component, files):
    go = shutil.which("go")
    if go is None:
        pytest.skip("Go is unavailable; backend Go component behavior was not exercised")
    for name in files:
        shutil.copy2(ASSETS / name, tmp_path / name)
    (tmp_path / "go.mod").write_text(
        "module backend-component-probe\n\ngo 1.25.0\n\n"
        "require github.com/danielgtaylor/huma/v2 v2.39.1\n", encoding="utf-8",
    )

    if component == "cookie":
        (tmp_path / "cookie_fixture_test.go").write_text(COOKIE_FIXTURE, encoding="utf-8")

    def run(*args, fault="", public=False, succeeds=True):
        result = subprocess.run(
            [go, *args], cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=180,
            env={**os.environ, "GOWORK": "off", "CONTRACT_FAULT": fault,
                 "CONTRACT_PUBLIC": "1" if public else "",
                 "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")},
        )
        assert (result.returncode == 0) == succeeds, f"{result.args}\n{result.stdout}\n{result.stderr}"
        return result

    run("mod", "download", "github.com/danielgtaylor/huma/v2")
    if component in {"starter", "cookie"}:
        run("test", "-run", "^TestOpenAPIDocument$", "-update")
    result = run("test", "-count=1", "-v", "./...")
    assert "PASS" in result.stdout, result.stdout

    if component == "cookie":
        # The positive run covers inherited cookie-session security and path-item metadata.
        # Each mutation must make a reusable gate fail for its named contract violation.
        for fault, check, diagnostic in [
            ("absent-security", "TestOpenAPIHouseRules", "every security alternative"),
            ("anonymous-alternative", "TestOpenAPIHouseRules", "every security alternative"),
            ("anonymous-override", "TestOpenAPIHouseRules", "every security alternative"),
            ("anonymous-object-override", "TestOpenAPIHouseRules", "every security alternative"),
            ("wrong-scheme-override", "TestOpenAPIHouseRules", "every security alternative"),
            ("undeclared-scheme", "TestOpenAPIHouseRules", "every security alternative"),
            ("missing-scheme", "TestOpenAPIHouseRules", "is not declared"),
            ("document-drift", "TestOpenAPIDocument", "differs from the code"),
            ("problem-type", "TestCookieHTTPContract", "want application/problem+json"),
            ("problem-status", "TestCookieHTTPContract", "problem status"),
            ("request-id", "TestCookieHTTPContract", "no X-Request-ID"),
            ("mismatched-id", "TestCookieHTTPContract", "does not match X-Request-ID"),
        ]:
            result = run("test", "-count=1", "-run", f"^{check}$", "./...", fault=fault, succeeds=False)
            assert diagnostic in result.stdout + result.stderr, result.stdout + result.stderr
        # An explicitly public-only service needs neither fake auth schemes nor fake headers.
        run("test", "-run", "^TestOpenAPIDocument$", "-update", public=True)
        run("test", "-count=1", "-v", "./...", public=True)


# A different service and cookie-session integration, deliberately with no bearer/domain files.
# The fixture replaces only app-specific wiring, identity and selected HTTP requests.
COOKIE_FIXTURE = r'''package main

import (
    "context"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "os"
    "testing"

    "github.com/danielgtaylor/huma/v2"
    "github.com/danielgtaylor/huma/v2/adapters/humago"
)

var contractHeaders = map[string]string{"Cookie": "corp_session=local-reader"}
var authenticatedSchemes = map[string]bool{"corporateSession": true}
var publicOperations = map[string]bool{}

func init() {
    if os.Getenv("CONTRACT_PUBLIC") == "1" {
        contractHeaders = map[string]string{}
        authenticatedSchemes = map[string]bool{}
        publicOperations = map[string]bool{"readReport": true}
    }
}

type reportInput struct { Empty bool `query:"empty"` }

func (in *reportInput) Resolve(ctx huma.Context) []error {
    u := ctx.URL()
    query := u.Query()
    if query.Has("empty") && query.Get("empty") == "" {
        return []error{&huma.ErrorDetail{Location: "query.empty", Message: "expected a boolean"}}
    }
    return nil
}

func contractService(t *testing.T) (http.Handler, []byte) {
    t.Helper()
    mux := http.NewServeMux()
    config := HouseConfig("Internal report", "2.0.0")
    if len(authenticatedSchemes) > 0 {
        config.Components.SecuritySchemes = map[string]*huma.SecurityScheme{
            "corporateSession": {Type: "apiKey", In: "cookie", Name: "corp_session"},
        }
        config.Security = []map[string][]string{{"corporateSession": {}}}
    }
    api := humago.New(mux, config)
    api.UseMiddleware(func(ctx huma.Context, next func(huma.Context)) {
        if len(authenticatedSchemes) > 0 && ctx.Header("Cookie") != "corp_session=local-reader" {
            _ = huma.WriteErr(api, ctx, 401, "Authentication required.")
            return
        }
        next(ctx)
    })
    huma.Register(api, huma.Operation{
        Method: "GET", Path: "/v1/report", OperationID: "readReport", Errors: []int{401, 404, 422},
    }, func(_ context.Context, input *reportInput) (*struct{Body struct{Status string `json:"status"`}}, error) {
        if input.Empty { return nil, huma.Error404NotFound("No report available.") }
        out := &struct{Body struct{Status string `json:"status"`}}{}
        out.Body.Status = "ready"
        return out, nil
    })
    var handler http.Handler = WithRequestID(WithProblemFallback(mux), "")
    data, err := json.Marshal(api.OpenAPI())
    if err != nil { t.Fatal(err) }
    var doc map[string]any
    if err := json.Unmarshal(data, &doc); err != nil { t.Fatal(err) }
    item := doc["paths"].(map[string]any)["/v1/report"].(map[string]any)
    item["summary"] = "Report path"
    item["parameters"] = []any{}
    op := item["get"].(map[string]any)
    switch os.Getenv("CONTRACT_FAULT") {
    case "absent-security": delete(doc, "security")
    case "anonymous-alternative": doc["security"] = []any{map[string]any{"corporateSession": []any{}}, map[string]any{}}
    case "anonymous-override": op["security"] = []any{}
    case "anonymous-object-override": op["security"] = []any{map[string]any{}}
    case "wrong-scheme-override":
        doc["components"].(map[string]any)["securitySchemes"].(map[string]any)["other"] = map[string]any{"type": "apiKey", "in": "header", "name": "X-Other"}
        op["security"] = []any{map[string]any{"other": []any{}}}
    case "undeclared-scheme": op["security"] = []any{map[string]any{"corporateSession": []any{}, "unknown": []any{}}}
    case "missing-scheme": delete(doc["components"].(map[string]any)["securitySchemes"].(map[string]any), "corporateSession")
    case "document-drift": doc["info"].(map[string]any)["title"] = "Drifted title"
    }
    data, err = json.MarshalIndent(doc, "", "  ")
    if err != nil { t.Fatal(err) }
    if fault := os.Getenv("CONTRACT_FAULT"); fault == "problem-type" || fault == "problem-status" || fault == "request-id" || fault == "mismatched-id" {
        original := handler
        handler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            rec := httptest.NewRecorder()
            original.ServeHTTP(rec, r)
            for name, values := range rec.Header() { w.Header()[name] = values }
            body := rec.Body.Bytes()
            if fault == "request-id" { w.Header().Del("X-Request-ID") }
            if rec.Code >= 400 {
                if fault == "problem-type" { w.Header().Set("Content-Type", "application/json") }
                var problem map[string]any
                if err := json.Unmarshal(body, &problem); err != nil { t.Fatal(err) }
                if fault == "problem-status" { problem["status"] = "wrong" }
                if fault == "mismatched-id" { problem["request_id"] = "mismatch" }
                body, _ = json.Marshal(problem)
            }
            w.WriteHeader(rec.Code)
            _, _ = w.Write(body)
        })
    }
    return handler, append(data, '\n')
}

func TestCookieHTTPContract(t *testing.T) {
    handler, _ := contractService(t)
    allowed := call(t, handler, "GET", "/v1/report", "Cookie", contractHeaders["Cookie"])
    if allowed.status != 200 || allowed.body["status"] != "ready" { t.Fatalf("allowed report: %v", allowed) }
    assertRequestID(t, allowed)
    for _, cookie := range []string{"", "corp_session=invalid"} {
        if len(authenticatedSchemes) > 0 {
            assertProblem(t, call(t, handler, "GET", "/v1/report", "Cookie", cookie), 401)
        }
    }
    assertProblem(t, call(t, handler, "GET", "/v1/report?empty=true", "Cookie", contractHeaders["Cookie"]), 404)
    assertProblem(t, call(t, handler, "GET", "/v1/report?empty=not-a-boolean", "Cookie", contractHeaders["Cookie"]), 422)
    assertProblem(t, call(t, handler, "GET", "/v1/report?empty=", "Cookie", contractHeaders["Cookie"]), 422)
    assertProblem(t, call(t, handler, "GET", "/v1/absent", "Cookie", contractHeaders["Cookie"]), 404)
}
'''
