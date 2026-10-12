// A plausible solution without backend-craft: plain net/http, ad-hoc JSON errors, every row in one
// response, the stored struct serialized as-is, no committed document, no server timeouts.
package main

import (
	"encoding/json"
	"net/http"
	"os"
	"strings"
)

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func authed(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		token := strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
		if _, ok := VerifyToken(r.Context(), token); !ok {
			writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "unauthorized"})
			return
		}
		next(w, r)
	}
}

func routes() *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /v1/incidents", authed(func(w http.ResponseWriter, r *http.Request) {
		status := r.URL.Query().Get("status")
		rows := []Incident{}
		for _, i := range Incidents {
			if status == "" || i.Status == status {
				rows = append(rows, i)
			}
		}
		writeJSON(w, http.StatusOK, map[string]any{"data": rows, "next_cursor": nil})
	}))
	mux.HandleFunc("GET /v1/incidents/{id}", authed(func(w http.ResponseWriter, r *http.Request) {
		for _, i := range Incidents {
			if i.ID == r.PathValue("id") {
				writeJSON(w, http.StatusOK, i)
				return
			}
		}
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "not found"})
	}))
	return mux
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	_ = http.ListenAndServe(":"+port, routes())
}
