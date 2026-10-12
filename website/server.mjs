// Same-origin API proxy and crawlable, publication-aware HTML for public pages.
// No analytics SDKs, advertising tags, or shared authenticated cache.
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { render, configureWebsiteOrigins } from "./dist/server/entry-server.mjs";
import { gatewayContext } from "./proxy-context.mjs";
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "dist");
const apiOrigin = process.env.API_ORIGIN || "http://127.0.0.1:8200";
const publicOrigin = (
  process.env.WEBSITE_PUBLIC_URL || "http://localhost:3300"
).replace(/\/$/, "");
const appOrigin = (process.env.WEBSITE_APP_URL || 'http://localhost:3100').replace(/\/$/, '');
const stagingWebsite = process.env.APP_ENV === 'staging';
configureWebsiteOrigins(appOrigin, publicOrigin);
const runtimeOrigins = JSON.stringify({ appUrl: appOrigin, siteUrl: publicOrigin }).replace(/</g, '\\u003c');
const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const csp =
  "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'";
const headers = {
  ...(stagingWebsite ? { "X-Robots-Tag": "noindex, nofollow" } : {}),
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "X-Frame-Options": "DENY",
  "Content-Security-Policy": csp,
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
};
const types = {
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
};
async function getPosts(limit = 200, offset = 0) {
  const response = await fetch(
    `${apiOrigin}/api/v1/website/posts?limit=${limit}&offset=${offset}`,
    {
      signal: AbortSignal.timeout(8000),
    },
  );
  if (!response.ok) throw new Error("Content unavailable");
  return response.json();
}
async function allPosts() {
  const posts = [];
  for (let offset = 0; offset < 20000; offset += 200) {
    const batch = await getPosts(200, offset);
    posts.push(...batch);
    if (batch.length < 200) return posts;
  }
  throw new Error("Sitemap requires partitioning beyond 20,000 articles");
}
async function getManifest() {
  const response = await fetch(`${apiOrigin}/api/v1/website/manifest`, {
    signal: AbortSignal.timeout(8000),
  });
  if (response.status === 404) return { resources: [] };
  if (!response.ok) throw new Error("Website configuration unavailable");
  return response.json();
}
function pageSections(resource) {
  return resource.data.blocks
    .map(
      (block) =>
        `<section>${block.title ? `<${block.type === "hero" ? "h1" : "h2"}>${escape(block.title)}</${block.type === "hero" ? "h1" : "h2"}>` : ""}${paragraphs(block.body || "")}${block.type === "image" ? `<img src="/api/v1/website/media/${escape(block.asset_id)}" alt="${escape(block.alt)}" loading="lazy"/>` : ""}${block.label && block.href ? `<a href="${escape(block.href)}">${escape(block.label)}</a>` : ""}${block.type === "form" ? "<p>Use the enquiry form on this page to contact the team.</p>" : ""}</section>`,
    )
    .join("");
}
function paragraphs(text) {
  return String(text)
    .split(/\n\s*\n/)
    .map((block) => {
      if (block.startsWith("### ")) return `<h3>${escape(block.slice(4))}</h3>`;
      if (block.startsWith("## ")) return `<h2>${escape(block.slice(3))}</h2>`;
      if (block.startsWith("# ")) return `<h2>${escape(block.slice(2))}</h2>`;
      if (block.split("\n").every((l) => l.startsWith("- ")))
        return `<ul>${block
          .split("\n")
          .map((l) => `<li>${escape(l.slice(2))}</li>`)
          .join("")}</ul>`;
      return `<p>${escape(block).replace(/\n/g, "<br>")}</p>`;
    })
    .join("");
}
const staticPages = {
  "/": {
    title: "Build AI bots that work for your business",
    description:
      "Build AI assistants with your knowledge, connected channels, and business tools.",
    body: "<h1>Build AI bots that work for your business.</h1><p>Your knowledge. Your systems. Your channels. One AI assistant, built for real conversations.</p><h2>How TalkToBot works</h2><p>Add knowledge. Build your AI. Connect your channels. Monitor and improve.</p><h2>Turn conversations into useful business data</h2><p>Capture leads, review AI health, manage your knowledge, connect integrations, and customize your brand.</p>",
  },
  "/contact": {
    title: "Book a demo",
    description: "Discuss your business AI assistant with TalkToBot.",
    body: "<h1>Let’s connect.</h1><p>Tell us about your customers, knowledge, and channels. Use the website enquiry form to ask for a product walkthrough.</p>",
  },
  "/pricing": {
    title: "Find your fit",
    description: "Discuss your channels, team, and workload with TalkToBot.",
    body: "<h1>A platform that fits your business.</h1><p>Public plan prices and trial terms are not currently published. Contact us to discuss your setup.</p>",
  },
  "/privacy": {
    title: "Website privacy notice",
    description: "How the TalkToBot website handles enquiry and editor data.",
    body: "<h1>Website privacy notice</h1><p>Enquiries collect name, email, optional company, and message to let the team respond. No advertising pixels, analytics SDKs, or session replay are loaded. Company-specific legal review is required before production launch.</p>",
  },
  "/terms": {
    title: "Website terms",
    description: "Website information and commercial terms.",
    body: "<h1>Website terms</h1><p>Illustrative examples are not live customer results. Pricing and contractual terms are agreed separately. Legal review is required before production launch.</p>",
  },
  "/security": {
    title: "Website security",
    description: "Content access and editorial integrity controls.",
    body: "<h1>Security at the website boundary</h1><p>Only published articles are public. Website editors must be explicitly authorized. Source and revision history do not automatically expire.</p>",
  },
};
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", "http://localhost");
  const send = (
    status,
    body,
    type = "text/html; charset=utf-8",
    extra = {},
  ) => {
    res.writeHead(status, {
      ...headers,
      "Content-Type": type,
      "Cache-Control": "no-store",
      ...extra,
    });
    res.end(body);
  };
  try {
    if (url.pathname === "/healthz") return send(200, "ok", "text/plain");
    if (url.pathname.startsWith("/api/")) {
      let size = 0;
      const chunks = [];
      for await (const chunk of req) {
        size += chunk.length;
        if (size > 3_200_000)
          return send(
            413,
            JSON.stringify({ detail: "Request is too large" }),
            "application/json",
          );
        chunks.push(chunk);
      }
      const upstreamHeaders = new Headers();
      for (const [name, value] of Object.entries(
        gatewayContext(
          req,
          url.pathname,
          process.env.WEBSITE_PROXY_SECRET,
          process.env.WEBSITE_TRUSTED_PROXY_CIDRS,
        ),
      ))
        upstreamHeaders.set(name, value);
      for (const name of [
        "content-type",
        "authorization",
        "cookie",
        "origin",
        "idempotency-key",
        "x-request-id",
      ])
        if (req.headers[name])
          upstreamHeaders.set(name, String(req.headers[name]));
      const response = await fetch(`${apiOrigin}${url.pathname}${url.search}`, {
        method: req.method,
        headers: upstreamHeaders,
        body: ["GET", "HEAD"].includes(req.method || "GET")
          ? undefined
          : Buffer.concat(chunks),
        signal: AbortSignal.timeout(30000),
        redirect: "manual",
      });
      const extra = {};
      for (const name of ["set-cookie", "retry-after"])
        if (response.headers.get(name))
          extra[name] = response.headers.get(name);
      return send(
        response.status,
        Buffer.from(await response.arrayBuffer()),
        response.headers.get("content-type") || "application/json",
        extra,
      );
    }
    if (url.pathname === "/robots.txt")
      return send(
        200,
        stagingWebsite
          ? "User-agent: *\nDisallow: /\n"
          : `User-agent: *\nDisallow: /admin\nDisallow: /api/\nSitemap: ${publicOrigin}/sitemap.xml\n`,
        "text/plain",
      );
    if (url.pathname === "/sitemap.xml") {
      const posts = await allPosts();
      const manifest = await getManifest();
      const routes = [
        ...Object.keys(staticPages),
        "/blog",
        ...posts.map((p) => `/blog/${p.slug}`),
        ...manifest.resources
          .filter((r) => r.kind === "page" && r.data.index !== false)
          .map((r) => r.data.route),
        ...manifest.resources
          .filter((r) => r.kind === "collection")
          .map((r) => `/collections/${r.key}`),
        ...manifest.resources
          .filter((r) => r.kind === "entry")
          .map((r) => `/collections/${r.data.collection_key}/${r.key}`),
      ];
      return send(
        200,
        `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${[
          ...new Set(routes),
        ]
          .filter(
            (route) =>
              !manifest.resources.some(
                (r) =>
                  r.kind === "page" &&
                  r.data.route === route &&
                  r.data.index === false,
              ),
          )
          .map(
            (route) => `<url><loc>${escape(publicOrigin + route)}</loc></url>`,
          )
          .join("")}</urlset>`,
        "application/xml",
      );
    }
    if (url.pathname === "/feed.xml") {
      const posts = await getPosts(50);
      return send(
        200,
        `<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>TalkToBot journal</title><link>${escape(publicOrigin + "/blog")}</link><description>Published TalkToBot guides and product stories</description>${posts.map((post) => `<item><title>${escape(post.title)}</title><link>${escape(publicOrigin + "/blog/" + post.slug)}</link><guid isPermaLink="true">${escape(publicOrigin + "/blog/" + post.slug)}</guid><description>${escape(post.excerpt)}</description>${post.published_at ? `<pubDate>${escape(new Date(post.published_at).toUTCString())}</pubDate>` : ""}</item>`).join("")}</channel></rss>`,
        "application/rss+xml",
      );
    }
    if (
      url.pathname.startsWith("/assets/") ||
      url.pathname.startsWith("/fonts/") ||
      url.pathname.startsWith("/images/") ||
      url.pathname === "/favicon.svg"
    ) {
      const relative = decodeURIComponent(url.pathname).replace(/^\//, "");
      const file = path.resolve(root, relative);
      if (!file.startsWith(root + path.sep))
        return send(404, "Not found", "text/plain");
      const content = await readFile(file);
      return send(
        200,
        content,
        types[path.extname(file)] || "application/octet-stream",
        {
          "Cache-Control": url.pathname.startsWith("/assets/")
            ? "public, max-age=31536000, immutable"
            : "public, max-age=86400",
        },
      );
    }
    let page = staticPages[url.pathname],
      status = 200,
      noindex = stagingWebsite;
    const boot = {};
    let manifest = { resources: [] };
    if (!url.pathname.startsWith("/admin")) {
      try {
        manifest = await getManifest();
      } catch (error) {
        if (!page && !url.pathname.startsWith("/blog")) throw error;
      }
    }
    const redirect = manifest.resources.find(
      (r) => r.kind === "redirect" && r.data.source === url.pathname,
    );
    if (redirect) {
      const target = new URL(redirect.data.target, publicOrigin);
      for (const key of [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
      ]) {
        const value = url.searchParams.get(key);
        if (value && /^[a-z0-9][a-z0-9_-]{0,79}$/.test(value))
          target.searchParams.set(key, value);
      }
      return send(redirect.data.status || 301, "Redirecting", "text/plain", {
        Location: target.pathname + target.search,
      });
    }
    const managed = manifest.resources.find(
      (r) => r.kind === "page" && r.data.route === url.pathname,
    );
    const collectionMatch = url.pathname.match(
      /^\/collections\/([a-z0-9-]+)(?:\/([a-z0-9-]+))?$/,
    );
    const collection =
      collectionMatch &&
      manifest.resources.find(
        (r) => r.kind === "collection" && r.key === collectionMatch[1],
      );
    if (collection) {
      const entries = manifest.resources.filter(
        (r) => r.kind === "entry" && r.data.collection_key === collection.key,
      );
      const entry =
        collectionMatch[2] && entries.find((r) => r.key === collectionMatch[2]);
      if (entry)
        page = {
          title: entry.title,
          description: `Read ${entry.title} from TalkToBot.`,
          body: `<h1>${escape(entry.title)}</h1>${collection.data.fields.map((f) => `<h2>${escape(f.label || f.key)}</h2>${paragraphs(String(entry.data.fields[f.key] ?? ""))}`).join("")}`,
        };
      else if (!collectionMatch[2])
        page = {
          title: collection.title,
          description: `Explore ${collection.title} from TalkToBot.`,
          body: `<h1>${escape(collection.title)}</h1>${entries.map((r) => `<article><h2><a href="/collections/${escape(collection.key)}/${escape(r.key)}">${escape(r.title)}</a></h2></article>`).join("")}`,
        };
    }
    if (managed) {
      page = {
        title: managed.title,
        description: managed.data.description || "",
        body: pageSections(managed),
      };
      noindex = stagingWebsite || managed.data.index === false;
    }
    if (url.pathname === "/blog") {
      const posts = await getPosts();
      boot.posts = posts;
      page = {
        title: "The TalkToBot journal",
        description: "Practical guides and ideas for useful business AI.",
        body: `<h1>The TalkToBot journal</h1>${posts.map((p) => `<article><h2><a href="/blog/${escape(p.slug)}">${escape(p.title)}</a></h2><p>${escape(p.excerpt)}</p></article>`).join("")}`,
      };
    }
    if (url.pathname.startsWith("/blog/")) {
      const response = await fetch(
        `${apiOrigin}/api/v1/website/posts/${encodeURIComponent(url.pathname.slice(6))}`,
        { signal: AbortSignal.timeout(8000) },
      );
      if (response.ok) {
        const p = await response.json();
        boot.post = p;
        page = {
          title: p.seo_title || p.title,
          description: p.seo_description || p.excerpt,
          body: `<article><h1>${escape(p.title)}</h1><p>${escape(p.excerpt)}</p><p>By ${escape(p.author)}</p>${paragraphs(p.body)}</article>`,
        };
      } else if (response.status === 404) {
        status = 404;
      } else throw new Error("Content unavailable");
    }
    if (url.pathname.startsWith("/admin")) {
      page = {
        title: "Website editor",
        description: "Protected website owner editor.",
        body: "<h1>Website owner editor</h1><p>Sign in with an authorized editor account to manage content.</p>",
      };
      noindex = true;
    }
    if (!page) {
      status = 404;
      noindex = true;
      page = {
        title: "Page not found",
        description: "This page is not available.",
        body: '<h1>Page not found</h1><a href="/">Back to TalkToBot</a>',
      };
    }
    let html = await readFile(path.join(root, "index.html"), "utf8");
    html = html
      .replace(
        /<title>.*?<\/title>/,
        `<title>${escape(page.title)} | TalkToBot</title>`,
      )
      .replace(
        /<meta name="description" content="[^"]*"\/>/,
        `<meta name="description" content="${escape(page.description)}"/>`,
      );
    html = html.replace(
      "</head>",
      `<link rel="canonical" href="${escape(publicOrigin + url.pathname)}"/><meta property="og:title" content="${escape(page.title)}"/><meta property="og:description" content="${escape(page.description)}"/><meta property="og:url" content="${escape(publicOrigin + url.pathname)}"/>${noindex ? '<meta name="robots" content="noindex, nofollow"/>' : ""}</head>`,
    );
    if (url.pathname === "/") {
      try {
        boot.posts = await getPosts(3);
      } catch {
        /* Core homepage stays available during a content outage. */
      }
    }
    boot.resources = manifest.resources;
    if (status === 404) boot.failedPath = url.pathname;
    const isPublic = !url.pathname.startsWith("/admin");
    const body = isPublic
      ? render(url.pathname + url.search, boot)
      : `<main class="section-shell">${page.body}</main>`;
    const bootstrap = JSON.stringify(boot).replace(/</g, "\\u003c");
    html = html.replace(
      '<div id="root"></div>',
      `<script type="application/json" id="website-runtime">${runtimeOrigins}</script><div id="root"${isPublic ? ' data-ssr="true"' : ""}>${body}</div>${isPublic ? `<script type="application/json" id="website-bootstrap">${bootstrap}</script>` : ""}`,
    );
    send(
      status,
      html,
      "text/html; charset=utf-8",
      noindex ? { "X-Robots-Tag": "noindex, nofollow" } : {},
    );
  } catch (error) {
    if (error.code === "ENOENT") return send(404, "Not found", "text/plain");
    console.error("Website request failed:", error.name);
    send(
      503,
      "The website is temporarily unavailable. Please try again.",
      "text/plain",
    );
  }
});
server.requestTimeout = 35000;
server.headersTimeout = 10000;
server.listen(Number(process.env.PORT || 3300), "0.0.0.0", () =>
  console.log(
    `TalkToBot website: http://localhost:${process.env.PORT || 3300}`,
  ),
);
