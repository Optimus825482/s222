// Wrapper around Next.js standalone server that serves public/ and _next/static/ files.
// Next.js standalone mode does NOT serve these directories by default.
const http = require("http");
const { parse } = require("url");
const path = require("path");
const fs = require("fs");

const MIME = {
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".ogg": "audio/ogg",
  ".ico": "image/x-icon",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".json": "application/json",
  ".js": "application/javascript",
  ".css": "text/css",
  ".html": "text/html",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".map": "application/json",
  ".webmanifest": "application/manifest+json",
};

const PUBLIC_DIR = path.join(__dirname, "public");
const STATIC_DIR = path.join(__dirname, ".next", "static");

function tryServeFile(filePath, res) {
  try {
    const stat = fs.statSync(filePath);
    if (stat.isFile()) {
      const ext = path.extname(filePath).toLowerCase();
      res.setHeader("Content-Type", MIME[ext] || "application/octet-stream");
      res.setHeader("Cache-Control", "public, max-age=31536000, immutable");
      fs.createReadStream(filePath).pipe(res);
      return true;
    }
  } catch {
    // file not found
  }
  return false;
}

// Import the Next.js request handler from standalone output
const nextApp = require("next/dist/server/next-server");
const conf = require("./.next/required-server-files.json");

const nextServer = new nextApp.default({
  hostname: "0.0.0.0",
  port: 3000,
  dir: __dirname,
  dev: false,
  customServer: true,
  conf: conf.config,
});

const handler = nextServer.getRequestHandler();

nextServer.prepare().then(() => {
  http
    .createServer((req, res) => {
      const parsedUrl = parse(req.url, true);
      const pathname = decodeURIComponent(parsedUrl.pathname || "/");

      // Serve _next/static/* files directly from .next/static/
      if (pathname.startsWith("/_next/static/")) {
        const relativePath = pathname.replace("/_next/static/", "");
        const filePath = path.join(STATIC_DIR, relativePath);
        if (tryServeFile(filePath, res)) return;
      }

      // Serve public/ files (voices, icons, manifest, etc.)
      if (
        pathname !== "/" &&
        !pathname.startsWith("/_next") &&
        !pathname.startsWith("/api")
      ) {
        const filePath = path.join(PUBLIC_DIR, pathname);
        if (tryServeFile(filePath, res)) return;
      }

      // Everything else goes to Next.js handler (SSR, API rewrites)
      handler(req, res, parsedUrl);
    })
    .listen(3000, "0.0.0.0", () => {
      console.log("> Ready on http://0.0.0.0:3000");
    });
});
