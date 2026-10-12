// TestSchemathesis drives the real handler from its own document with Schemathesis (the st
// command): every operation, with valid and invalid inputs, must answer as the document says,
// never with a 500. The test token lives in testVerify; the service never accepts a static token.
// Locally it skips without st (uv tool install schemathesis); in CI a missing st fails.
package main

import (
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
)

func TestSchemathesis(t *testing.T) {
	st, err := exec.LookPath("st")
	if err != nil {
		if os.Getenv("CI") != "" {
			t.Fatal("st (Schemathesis) must be installed in CI")
		}
		t.Skip("st not installed: uv tool install schemathesis")
	}
	handler, _ := newService(Config{Addr: "127.0.0.1:0"}, testVerify, seededStore(30))
	server := httptest.NewServer(handler)
	defer server.Close()
	// The test supplies the token, so Schemathesis does not generate the security header; the
	// service ignores query parameters it does not declare, so an extra one is not invalid input.
	config := filepath.Join(t.TempDir(), "schemathesis.toml")
	settings := "[generation]\nallow-extra-parameters = false\nwith-security-parameters = false\n"
	if err := os.WriteFile(config, []byte(settings), 0o644); err != nil {
		t.Fatal(err)
	}
	cmd := exec.Command(st, "--config-file", config, "run", documentPath, "--url", server.URL,
		"-H", "Authorization: Bearer "+testToken, "--max-examples", "25")
	cmd.Env = append(os.Environ(), "PYTHONUTF8=1") // Windows pipes otherwise default to cp1252
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("Schemathesis found responses that break the document:\n%s", out)
	}
}
