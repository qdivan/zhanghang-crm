import { createReadStream, existsSync, statSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";

const apiProxyOrigin = process.env.API_PROXY_ORIGIN || "http://api:8000";
const port = Number(process.env.PORT || 80);
const root = join(process.cwd(), "dist");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".gif": "image/gif",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function resolvePath(urlPath) {
  const normalized = normalize(decodeURIComponent(urlPath)).replace(/^(\.\.[/\\])+/, "");
  const candidate = join(root, normalized);
  if (existsSync(candidate) && statSync(candidate).isFile()) {
    return candidate;
  }
  return join(root, "index.html");
}

async function readRequestBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return chunks.length > 0 ? Buffer.concat(chunks) : undefined;
}

async function proxyApiRequest(req, res) {
  const targetUrl = new URL(req.url || "/", apiProxyOrigin);
  const headers = new Headers();

  for (const [key, value] of Object.entries(req.headers)) {
    if (value == null) continue;
    if (["host", "connection", "content-length"].includes(key.toLowerCase())) continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        headers.append(key, item);
      }
      continue;
    }
    headers.set(key, value);
  }

  const method = req.method || "GET";
  const body = ["GET", "HEAD"].includes(method) ? undefined : await readRequestBody(req);
  const upstream = await fetch(targetUrl, {
    method,
    headers,
    body,
    redirect: "manual",
  });

  const responseHeaders = {};
  upstream.headers.forEach((value, key) => {
    if (["connection", "content-length", "transfer-encoding"].includes(key.toLowerCase())) {
      return;
    }
    responseHeaders[key] = value;
  });

  res.writeHead(upstream.status, responseHeaders);
  if (method === "HEAD" || upstream.body == null) {
    res.end();
    return;
  }

  for await (const chunk of upstream.body) {
    res.write(chunk);
  }
  res.end();
}

createServer(async (req, res) => {
  const rawUrl = req.url || "/";
  const rawPath = rawUrl.split("?")[0];

  try {
    if (rawPath.startsWith("/api/")) {
      await proxyApiRequest(req, res);
      return;
    }

    if (!["GET", "HEAD"].includes(req.method || "GET")) {
      res.writeHead(405, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Method Not Allowed");
      return;
    }

    const filePath = resolvePath(rawPath === "/" ? "/index.html" : rawPath);
    const ext = extname(filePath).toLowerCase();
    const contentType = contentTypes[ext] || "application/octet-stream";

    if (ext === ".html") {
      const html = await readFile(filePath);
      res.writeHead(200, {
        "Cache-Control": "no-cache",
        "Content-Type": contentType,
      });
      if (req.method === "HEAD") {
        res.end();
        return;
      }
      res.end(html);
      return;
    }

    res.writeHead(200, {
      "Cache-Control": "public, max-age=31536000, immutable",
      "Content-Type": contentType,
    });
    if (req.method === "HEAD") {
      res.end();
      return;
    }
    createReadStream(filePath).pipe(res);
  } catch (error) {
    const statusCode = rawPath.startsWith("/api/") ? 502 : 404;
    const message = statusCode === 502 ? "Bad Gateway" : "Not Found";
    console.error(error);
    res.writeHead(statusCode, { "Content-Type": "text/plain; charset=utf-8" });
    res.end(message);
  }
}).listen(port, "0.0.0.0", () => {
  console.log(`Static server listening on ${port}`);
});
