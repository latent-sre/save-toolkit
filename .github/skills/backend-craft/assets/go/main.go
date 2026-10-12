// A Huma service with the house operating surface: configuration read and validated at startup,
// a loopback default address, server timeouts, health endpoints outside the API contract, a
// request ID on every log line, and graceful shutdown inside the platform's grace period.
package main

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"strconv"
	"syscall"
	"time"

	"github.com/danielgtaylor/huma/v2"
)

// Config comes from the environment once, at startup; an invalid value stops the process.
type Config struct {
	// Addr is ":$PORT" when the platform sets PORT (PCF, Cloud Run), otherwise LISTEN_ADDR,
	// otherwise 127.0.0.1:8080: a desktop or host tool never listens beyond loopback by default.
	Addr string
	// TrustedRequestIDHeader is a header only the ingress sets, such as X-Vcap-Request-Id on PCF.
	TrustedRequestIDHeader string
}

func loadConfig(getenv func(string) string) (Config, error) {
	cfg := Config{Addr: "127.0.0.1:8080", TrustedRequestIDHeader: getenv("TRUSTED_REQUEST_ID_HEADER")}
	if addr := getenv("LISTEN_ADDR"); addr != "" {
		cfg.Addr = addr
	}
	if port := getenv("PORT"); port != "" {
		if n, err := strconv.Atoi(port); err != nil || n < 1 || n > 65535 {
			return Config{}, fmt.Errorf("PORT %q is not a TCP port", port)
		}
		cfg.Addr = ":" + port
	}
	if _, _, err := net.SplitHostPort(cfg.Addr); err != nil {
		return Config{}, fmt.Errorf("listen address %q: %w", cfg.Addr, err)
	}
	return cfg, nil
}

// newService wires the handler chain and the API. Tests call it; main serves it.
func newService(cfg Config, verify TokenVerifier, store *ThingStore) (http.Handler, huma.API) {
	mux := http.NewServeMux()
	// Health stays outside the contract and authentication; no health path ends in "z".
	mux.HandleFunc("GET /health/live", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK) // process-local: never a dependency check
	})
	mux.HandleFunc("GET /health/ready", func(w http.ResponseWriter, r *http.Request) {
		if err := store.Ready(r.Context()); err != nil {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		w.WriteHeader(http.StatusOK)
	})

	api := NewAPI(mux, "Things API", "1.0.0", verify)
	registerThings(api, store)

	var handler http.Handler = WithProblemFallback(mux)
	// Refuse cross-site browser writes (Sec-Fetch-Site / Origin); reads and non-browser clients pass.
	crossOrigin := http.NewCrossOriginProtection()
	crossOrigin.SetDenyHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		WriteProblem(w, r, newProblem(http.StatusForbidden, "Cross-origin requests are not accepted."))
	}))
	handler = crossOrigin.Handler(handler)
	if host, _, _ := net.SplitHostPort(cfg.Addr); isLoopback(host) {
		handler = allowLoopbackHosts(handler)
	}
	handler = withAccessLog(handler)
	return WithRequestID(handler, cfg.TrustedRequestIDHeader), api
}

func isLoopback(host string) bool {
	if host == "localhost" {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
}

// allowLoopbackHosts refuses a request whose Host is not a loopback name: a web page that
// rebinds its own DNS name to 127.0.0.1 still sends its own name as Host.
func allowLoopbackHosts(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		host, _, err := net.SplitHostPort(r.Host)
		if err != nil {
			host = r.Host
		}
		if !isLoopback(host) {
			WriteProblem(w, r, newProblem(http.StatusMisdirectedRequest, "This service answers only on its loopback address."))
			return
		}
		next.ServeHTTP(w, r)
	})
}

type statusWriter struct {
	http.ResponseWriter
	status int
}

func (s *statusWriter) WriteHeader(status int) {
	s.status = status
	s.ResponseWriter.WriteHeader(status)
}

// Unwrap lets http.ResponseController reach the real writer, for flushing and stream deadlines.
func (s *statusWriter) Unwrap() http.ResponseWriter { return s.ResponseWriter }

func withAccessLog(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		sw := &statusWriter{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(sw, r)
		slog.InfoContext(r.Context(), "request", "method", r.Method, "route", r.Pattern,
			"status", sw.status, "duration_ms", time.Since(start).Milliseconds())
	})
}

// requestIDLogs adds request_id to every record logged with a request's context.
type requestIDLogs struct{ slog.Handler }

func (h requestIDLogs) Handle(ctx context.Context, record slog.Record) error {
	if id := RequestIDFrom(ctx); id != "" {
		record.AddAttrs(slog.String("request_id", id))
	}
	return h.Handler.Handle(ctx, record)
}
func (h requestIDLogs) WithAttrs(attrs []slog.Attr) slog.Handler {
	return requestIDLogs{h.Handler.WithAttrs(attrs)}
}
func (h requestIDLogs) WithGroup(name string) slog.Handler {
	return requestIDLogs{h.Handler.WithGroup(name)}
}

func main() {
	slog.SetDefault(slog.New(requestIDLogs{slog.NewJSONHandler(os.Stdout, nil)}))
	if err := run(context.Background(), os.Getenv); err != nil {
		slog.Error("service stopped", "error", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, getenv func(string) string) error {
	cfg, err := loadConfig(getenv)
	if err != nil {
		return err
	}
	store := NewThingStore()
	// Replace with the identity provider's verifier; this one refuses every token.
	verify := func(context.Context, string) (Principal, error) {
		return Principal{}, ErrInvalidToken
	}
	handler, _ := newService(cfg, verify, store)

	srv := &http.Server{
		Addr:              cfg.Addr,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      60 * time.Second, // a stream handler lifts it with http.ResponseController
		IdleTimeout:       120 * time.Second,
	}

	// SIGTERM from PCF, Cloud Run and systemd; os.Interrupt for Ctrl+C. On Windows, closing the
	// console window arrives as SIGTERM.
	ctx, stop := signal.NotifyContext(ctx, os.Interrupt, syscall.SIGTERM)
	defer stop()
	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.ListenAndServe() }()
	slog.Info("listening", "addr", cfg.Addr)

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
	}
	// PCF and Cloud Run send SIGKILL 10 s after SIGTERM; a closed Windows console allows 5 s.
	grace := 8 * time.Second
	if runtime.GOOS == "windows" {
		grace = 4 * time.Second
	}
	shutdownCtx, cancel := context.WithTimeout(context.Background(), grace)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown: %w", err)
	}
	return nil
}
