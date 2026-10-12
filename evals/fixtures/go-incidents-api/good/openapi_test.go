package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"os"
	"testing"
)

var update = flag.Bool("update", false, "rewrite openapi.json from the code")

func TestOpenAPIDocument(t *testing.T) {
	_, api := newService("127.0.0.1:0")
	got, err := json.MarshalIndent(api.OpenAPI(), "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	got = append(got, '\n')
	if *update {
		if err := os.WriteFile("openapi.json", got, 0o644); err != nil {
			t.Fatal(err)
		}
		return
	}
	want, err := os.ReadFile("openapi.json")
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(bytes.ReplaceAll(want, []byte("\r\n"), []byte("\n")), got) {
		t.Fatal("openapi.json differs from the code: go test -run TestOpenAPIDocument -update")
	}
}
