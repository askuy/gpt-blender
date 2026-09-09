package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"embed"
	"errors"
	"flag"
	"fmt"
	"io/fs"
	"log"
	"mime"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path"
	"strings"
	"syscall"
	"time"
)

// Only viewer assets are shipped; source files and rendered videos are excluded.
//
//go:embed web/index.html web/style.css web/app.js web/assets/*.glb web/assets/*.json web/assets/*.m4a web/vendor/*.js web/vendor/THREE-LICENSE.txt
var webFiles embed.FS

type asset struct {
	body        []byte
	etag        string
	contentType string
}

func newHandler() (http.Handler, error) {
	files, err := fs.Sub(webFiles, "web")
	if err != nil {
		return nil, err
	}
	assets := make(map[string]asset)
	err = fs.WalkDir(files, ".", func(name string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() {
			return nil
		}
		body, err := fs.ReadFile(files, name)
		if err != nil {
			return err
		}
		contentType := mime.TypeByExtension(path.Ext(name))
		switch path.Ext(name) {
		case ".glb":
			contentType = "model/gltf-binary"
		case ".m4a":
			contentType = "audio/mp4"
		case ".js":
			contentType = "text/javascript; charset=utf-8"
		}
		assets["/"+name] = asset{body, fmt.Sprintf(`"%x"`, sha256.Sum256(body)), contentType}
		return nil
	})
	if err != nil {
		return nil, err
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		if r.Method != http.MethodGet && r.Method != http.MethodHead {
			w.Header().Set("Allow", "GET, HEAD")
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		name := r.URL.Path
		switch name {
		case "/healthz":
			w.Header().Set("Cache-Control", "no-store")
			w.Header().Set("Content-Type", "text/plain; charset=utf-8")
			if r.Method == http.MethodGet {
				fmt.Fprintln(w, "ok")
			}
			return
		case "/web", "/web/":
			target := *r.URL
			target.Path = "/"
			target.RawPath = ""
			http.Redirect(w, r, target.RequestURI(), http.StatusPermanentRedirect)
			return
		case "/":
			name = "/index.html"
		}
		file, ok := assets[name]
		if !ok {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", file.contentType)
		w.Header().Set("Cache-Control", "public, max-age=0, must-revalidate")
		w.Header().Set("ETag", file.etag)
		http.ServeContent(w, r, name, time.Time{}, bytes.NewReader(file.body))
	}), nil
}

func run(addr string) error {
	handler, err := newHandler()
	if err != nil {
		return err
	}
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	server := &http.Server{
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	done := make(chan error, 1)
	go func() { done <- server.Serve(listener) }()
	host, port, _ := net.SplitHostPort(listener.Addr().String())
	if host == "" || host == "::" || host == "0.0.0.0" {
		host = "127.0.0.1"
	}
	fmt.Printf("Niu Lai preview: http://%s/ (listening on %s)\n", net.JoinHostPort(host, port), listener.Addr())
	select {
	case err := <-done:
		return err
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			server.Close()
			return err
		}
		err := <-done
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return err
	}
}

func main() {
	addr := flag.String("addr", "127.0.0.1:8766", "HTTP listen address (use :8080 to accept remote connections)")
	flag.Parse()
	if strings.TrimSpace(*addr) == "" {
		log.Fatal("addr must not be empty")
	}
	if err := run(*addr); err != nil {
		log.Fatal(err)
	}
}
