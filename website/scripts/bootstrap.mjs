// Explicit, idempotent local content bootstrap. Credentials never leave memory.
import { readFile } from "node:fs/promises";
import { starterPosts } from "../src/content.ts";
const settings = Object.fromEntries(
  (await readFile(new URL("../../.env", import.meta.url), "utf8"))
    .split(/\r?\n/)
    .filter((l) => l && !l.startsWith("#") && l.includes("="))
    .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]),
);
const origin =
  process.env.API_ORIGIN || `http://127.0.0.1:${settings.API_PORT || 8200}`;
const login = await fetch(`${origin}/api/v1/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: settings.SEED_ADMIN_EMAIL,
    password: settings.SEED_ADMIN_PASSWORD,
  }),
});
if (!login.ok)
  throw new Error("Local admin login failed. No articles were created.");
const session = await login.json();
if (!session.accessToken)
  throw new Error("Complete MFA through the editor before seeding content.");
const headers = {
  "Content-Type": "application/json",
  Authorization: `Bearer ${session.accessToken}`,
};
const existingResponse = await fetch(
  `${origin}/api/v1/platform-admin/website/posts`,
  { headers },
);
if (!existingResponse.ok)
  throw new Error("Website editor access is not authorized.");
const existing = await existingResponse.json();
for (const article of starterPosts) {
  if (existing.some((p) => p.slug === article.slug)) {
    console.log(`Already exists: ${article.slug}`);
    continue;
  }
  const response = await fetch(
    `${origin}/api/v1/platform-admin/website/posts`,
    { method: "POST", headers, body: JSON.stringify(article) },
  );
  if (!response.ok)
    throw new Error(`Unable to create ${article.slug}: ${response.status}`);
  let post = await response.json();
  if (process.argv.includes("--publish")) {
    for (const action of ["review", "approve", "publish"]) {
      const published = await fetch(
        `${origin}/api/v1/platform-admin/website/posts/${post.id}/actions`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({
            version: post.version,
            action,
            reason: "Reviewed original starter guide",
          }),
        },
      );
      if (!published.ok) throw new Error(`Unable to publish ${article.slug}`);
      post = await published.json();
    }
    console.log(`Published: ${article.slug}`);
  } else console.log(`Draft created: ${article.slug}`);
}
