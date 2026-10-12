package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestListIncidents(t *testing.T) {
	t.Setenv("ONCALL_TEST_TOKEN", "t")
	req := httptest.NewRequest("GET", "/v1/incidents", nil)
	req.Header.Set("Authorization", "Bearer t")
	rec := httptest.NewRecorder()
	routes().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d", rec.Code)
	}
}
