package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestViewerHTTP(t *testing.T) {
	handler, err := newHandler()
	if err != nil {
		t.Fatal(err)
	}
	request := func(method, target string, headers map[string]string) *httptest.ResponseRecorder {
		t.Helper()
		r := httptest.NewRequest(method, target, nil)
		for name, value := range headers {
			r.Header.Set(name, value)
		}
		w := httptest.NewRecorder()
		handler.ServeHTTP(w, r)
		return w
	}

	t.Run("viewer and health", func(t *testing.T) {
		for target, contentType := range map[string]string{
			"/":                         "text/html",
			"/app.js":                   "text/javascript",
			"/style.css":                "text/css",
			"/vendor/three.module.js":   "text/javascript",
			"/assets/niulai.glb":        "model/gltf-binary",
			"/assets/dialogue.m4a":      "audio/mp4",
			"/assets/cameras.json":      "application/json",
			"/vendor/THREE-LICENSE.txt": "text/plain",
			"/healthz":                  "text/plain",
		} {
			w := request("GET", target, nil)
			if w.Code != http.StatusOK || !strings.HasPrefix(w.Header().Get("Content-Type"), contentType) {
				t.Errorf("%s: status %d, type %q", target, w.Code, w.Header().Get("Content-Type"))
			}
		}
		if strings.Contains(request("GET", "/", nil).Body.String(), ".mp4") {
			t.Error("viewer must not link to MP4 videos")
		}
	})

	t.Run("only public viewer files are served", func(t *testing.T) {
		for _, target := range []string{
			"/reference/movie-excerpt.mp4", "/output/niulai-twitter.mp4",
			"/src/build_scene.py", "/main.go", "/.git/config", "/README.md",
			"/assets/", "/vendor/", "/assets/../main.go", "/%2e%2e/main.go",
		} {
			if w := request("GET", target, nil); w.Code != http.StatusNotFound {
				t.Errorf("%s returned %d, want 404", target, w.Code)
			}
		}
	})

	t.Run("old preview bookmarks redirect", func(t *testing.T) {
		for _, target := range []string{"/web?shared=1", "/web/?shared=1"} {
			w := request("GET", target, nil)
			if w.Code != http.StatusPermanentRedirect || w.Header().Get("Location") != "/?shared=1" {
				t.Errorf("%s: status %d, location %q", target, w.Code, w.Header().Get("Location"))
			}
		}
	})

	t.Run("cached models revalidate without a body", func(t *testing.T) {
		first := request("GET", "/assets/niulai.glb", nil)
		etag := first.Header().Get("ETag")
		if etag == "" {
			t.Fatal("missing ETag")
		}
		cached := request("GET", "/assets/niulai.glb", map[string]string{"If-None-Match": etag})
		if cached.Code != http.StatusNotModified || cached.Body.Len() != 0 {
			t.Errorf("cached model: status %d, body %d bytes", cached.Code, cached.Body.Len())
		}
		head := request("HEAD", "/assets/niulai.glb", nil)
		if head.Code != http.StatusOK || head.Body.Len() != 0 || head.Header().Get("Content-Length") != first.Header().Get("Content-Length") {
			t.Error("HEAD must report the model size without sending its body")
		}
	})

	t.Run("audio supports seeking with byte ranges", func(t *testing.T) {
		full := request("GET", "/assets/dialogue.m4a", nil)
		part := request("GET", "/assets/dialogue.m4a", map[string]string{"Range": "bytes=16-31"})
		if part.Code != http.StatusPartialContent || part.Body.String() != full.Body.String()[16:32] {
			t.Errorf("audio range: status %d, body %d bytes", part.Code, part.Body.Len())
		}
	})

	t.Run("read only", func(t *testing.T) {
		w := request("POST", "/", nil)
		if w.Code != http.StatusMethodNotAllowed || w.Header().Get("Allow") != "GET, HEAD" {
			t.Error("POST must be rejected with the allowed methods")
		}
	})
}
