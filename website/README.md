# TalkToBot public website

This dedicated folder contains the public website, blog reader, owner editor, assets, and production website server. It uses the existing FastAPI/PostgreSQL application for identity, durable content, revisions, and enquiries. It does not create another competing account system.

## Open the local website

- Website: http://localhost:3300
- Blog: http://localhost:3300/blog
- Blog upload/editor: http://localhost:3300/admin
- Owner console: http://localhost:3300/admin/console
- Existing application/login: http://localhost:3100/login

The local seed administrator can access the website editor in development. Production requires an explicit comma-separated `WEBSITE_EDITOR_EMAILS` allowlist. An ordinary tenant owner cannot publish global marketing content. API keys and impersonated sessions cannot edit it.

## Start and build

From the repository root:

```powershell
npm run website:install
npm run website:dev
```

Development uses Vite at port 3300 and proxies `/api` to port 8200. Put overrides in `website/.env.local`, based on `.env.example`.

For the crawlable server:

```powershell
npm run website:build
node website/server.mjs
```

Docker operation:

```powershell
docker compose build api website
docker compose run --rm migrate
docker compose up -d api website website-scheduler
```

The existing launcher starts the new `website` service as part of the stack. Website URL variables in the root environment are `WEBSITE_PORT`, `WEBSITE_APP_URL`, and `WEBSITE_PUBLIC_URL`. The local stack serves the app on port 3100; set `WEBSITE_APP_URL` when running a different app port or public domain.

## What is included

The PDF's light grid background, monochrome navigation, centered headline, dashboard preview, connected four-step workflow, six alternating feature sections, industry examples, FAQ accordions, final CTA, and dark footer are implemented with responsive layouts. Retail and business photographs are extracted from the supplied PDF. UI previews are native components with explicitly illustrative data.

Additional routes include a searchable/category-filtered blog, published article pages, a contact/demo form, pricing enquiry, privacy/terms/security disclosures, 404 responses, and an owner content studio. Header and footer login/signup links use the existing app.

The website server returns crawlable HTML, page-specific descriptions/canonicals/Open Graph metadata, a dynamic publication-aware sitemap, robots.txt, noindex editor pages, and appropriate 404/503 statuses. Client navigation enhances that HTML. API content is not shared-cached, so unpublishing immediately removes public article access.

## Upload and publish a blog

1. Sign in at `/admin` with an authorized editor.
2. Choose **New article** or a starter guide. Upload `.md`, `.txt`, or `.json` from the article toolbar. Article files are limited to 500 KB; the stored body is limited to 100,000 characters.
3. Add title, stable URL slug, excerpt, author, category, tags, and optional SEO text.
4. Upload a PNG/JPEG/WebP cover below 2 MB and add alternative text. The API verifies the image bytes; SVG and arbitrary remote images are rejected.
5. Preview, then **Save draft**. A browser-tab recovery copy protects unsaved work but is not a server save.
6. Enter an editorial reason, **Submit for review**, then **Approve draft**. **Publish** switches the approved saved revision atomically. Alternatively choose a future publication time and **Schedule publication**. Saving further changes cancels approval and the schedule; the previous public revision remains live.
7. **Unpublish** hides the public article. **Trash** requires a reason and preserves source/history. **Restore** returns it to draft. There is no permanent purge or automatic expiry.
8. **View revision history** to load an old revision into a draft. Save and publish after review. **Export article** downloads portable JSON.

Simple Markdown headings, paragraphs, lists, and blockquotes are supported. HTML is rendered as text; code and embedded scripts are not executed. A slug is locked after first save to avoid silently breaking inbound URLs. Conflicting versions return HTTP 409 instead of overwriting another editor.

Original guide content is provided in `src/content.ts`. To explicitly seed local drafts, run `node --experimental-strip-types website/scripts/bootstrap.mjs`. Add `--publish` to publish those guides. The script skips existing slugs and never prints account credentials.

## Enquiry handling

The form records explicit permission to respond and commits a durable enquiry before acknowledging receipt. Retries preserve the original submission identifier. Editors review accepted enquiries in the **Enquiries** section. No meeting or external email delivery is falsely acknowledged. Marketing subscription, advertising pixels, third-party analytics, location collection, and session replay are not activated.

## Owner console

The console manages pages and reorderable approved sections, navigation, forms, redirects, campaign links, offer/claim records, schemas and collection entries, local lead workflows, experiment definitions, brand/company/contact settings, and object-storage-backed media. It includes an enquiry pipeline, publication/review calendar, audit search, validated JSON imports, checksummed archives, internal link/SEO checks, provider readiness, and all 120 blueprint capability records.

Saved content follows draft → review → approved → published/scheduled. Public readers receive publication snapshots. The resource editor supports autosave, undo/redo, recovery copies that expire after 24 hours, duplicate drafts, and downloading local work before loading a newer server version. Uploaded images have rights/alt/provenance records and remain private until referenced by published content. External email, advertising, live experiments, and analytics are not activated by editing a resource.

Operator: **Northstar edtech**, **tech@northstaracad.com**. Requested production domain: **TalkToBot.io**. Local canonical URLs remain localhost; build with production origin variables only when deploying to the verified domain.

See [the owner manual](docs/owner-console.md) and [the complete capability register](src/requirements.json). The register distinguishes specified, applicable, implemented, activated and verified states. Several blueprint modules still require implementation or provider qualification; the register exposes those gaps instead of marking configuration screens as completed features.

Set the same random `WEBSITE_PROXY_SECRET` of at least 32 characters on the website gateway and API. Only configure `WEBSITE_TRUSTED_PROXY_CIDRS` for known ingress proxies. Public submissions use verified client context for abuse limits; raw client addresses are not persisted in enquiries.

## Reference and readiness evidence

See [implementation.md](docs/implementation.md) for scope, API contracts, blueprint applicability, verification, and outstanding production requirements. Full extracted reference text is retained in `docs/reference` for follow-up work. This implementation is not a claim that the blueprint's entire 78-chapter marketing/operations platform is production-qualified.
