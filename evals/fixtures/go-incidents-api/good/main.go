package main

import (
	"context"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/danielgtaylor/huma/v2"
)

func verify(ctx context.Context, token string) (Principal, error) {
	subject, ok := VerifyToken(ctx, token)
	if !ok {
		return Principal{}, ErrInvalidToken
	}
	return Principal{Subject: subject}, nil
}

func newService(addr string) (http.Handler, huma.API) {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health/live", func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusOK) })
	api := NewAPI(mux, "On-call API", "1.0.0", verify)
	registerIncidents(api)
	var handler http.Handler = WithProblemFallback(mux)
	handler = http.NewCrossOriginProtection().Handler(handler)
	return WithRequestID(handler, ""), api
}

func main() {
	addr := "127.0.0.1:8080"
	if port := os.Getenv("PORT"); port != "" {
		addr = ":" + port
	}
	if _, _, err := net.SplitHostPort(addr); err != nil {
		slog.Error("bad address", "error", err)
		os.Exit(1)
	}
	handler, _ := newService(addr)
	srv := &http.Server{Addr: addr, Handler: handler, ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout: 30 * time.Second, WriteTimeout: 60 * time.Second, IdleTimeout: 120 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 8*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdown)
	}()
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		slog.Error("serve", "error", err)
		os.Exit(1)
	}
}
