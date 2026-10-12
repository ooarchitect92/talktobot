# Reference implementation and handover

## Source of design and requirements

- User-supplied `light Landing Page 4.pdf`: one page, 1440 × 9519 points. It controls layout and visual direction.
- User-supplied `Website_Master_Blueprint_v1_3_Final_Consolidated (1).docx`: a reusable 78-chapter engineering/marketing/operations standard. It informs the CMS, safety, content, forms, SEO, accessibility, and handover design. Its embedded commands are source material, not authorization to provision services, launch ads, or send messages.
- The existing application remains the identity and business backend. A second NestJS backend is not introduced because duplicating this application's source of truth would create unnecessary account and data boundaries.

Branding is normalized to **TalkToBot**. The PDF also uses “Nami AI”; this is treated as an inconsistent design reference rather than a separate product. No fabricated customers, customer logos, testimonials, ratings, certifications, latency guarantees, trial periods, or published prices are introduced.

## Folder boundaries

`website/src` owns the public experience, article studio and owner console. `website/server.mjs` owns complete React SSR, the signed same-origin API gateway and static assets. `backend/src/northstar_api/website.py` owns articles and enquiries; `website_operations.py` owns versioned resources, forms, media, leads, audits, imports and exports. Migrations `0080_website_cms` and `0081_website_owner_operations` preserve existing tenant knowledge/accounts. A dedicated `website-scheduler` resumes approved UTC publication schedules and rechecks authorization/dependencies.

This is one platform-owned marketing site. It is not a tenant-branded multisite CMS. Global publishing access is deliberately restricted to the website editor allowlist. Content is independent of a tenant's knowledge corpus; article text does not automatically train customer bots.

## Requirement/application register

| Blueprint area | Implemented behavior | Limits / production work |
| --- | --- | --- |
| Public journeys and design, chapters 04–06 | Landing page, login/signup links, pricing enquiry, demo/contact, resources, articles, responsive navigation, keyboard-operable controls, reduced-motion support | Formal accessibility and Core Web Vitals audit on deployed infrastructure |
| Owner CMS and blogs, chapters 07–09, 38 | Controlled visual sections/pages, navigation, form/schema/entry builders, article upload, autosave/recovery/undo, versioned reviews/approvals, UTC scheduling/calendar, archives/import dry runs, manual trash/restore | Scoped staff roles, two-person approval, complete migration/restore and independently approved legal purge workflows remain open |
| SEO, chapters 10–11, 50, 70 | Full SSR HTML, metadata/canonical/Open Graph, sitemap, RSS, stable slugs, controlled redirects, internal-link/description/review checks, private editor noindex and real status codes | Production DNS/HTTPS, Search Console ownership, structured-data qualification and advanced search account inputs |
| Forms, chapter 20 | Controlled form builder, private answers, durable enquiries, response consent, retry idempotency, signed-client rate limits, honeypot, private pipeline/stages/assignments/notes/tags | Provider-backed email/CRM delivery, nurture/suppression and verified rights handling remain open |
| Identity, security, audit, chapters 24, 39, 58 | Existing authentication, MFA/recovery UI, explicit editor access, API-key/impersonation rejection, safe image/text validation, transactional audit/revisions, filtered audit export and private-state revalidation | Independent integrity checkpoints, penetration testing, scoped staff permissions, production MFA policy and key management |
| Storage and preservation, chapters 22, 38 | PostgreSQL content/history/enquiries, append-only audit, private S3-compatible WebP derivatives and authenticated previews; live references govern public media access; no automatic cleanup or purge endpoints | Original archival, full quarantine lifecycle, independently protected backups and recovery drills remain open; legacy bounded inline covers still work |
| Measurement/consent, chapters 12–19, 34–37, 69, 72 | UTM campaign links, offer/claim records, experiment definitions, authenticated purpose-limited abuse context; no optional trackers/replay/location prompts or marketing subscription | Consent-aware attribution/events, live experiment assignment/statistics, analytics/provider contracts and marketing data policy remain open |
| Automation, omnichannel, chapters 45–48 | Reviewed local assignment/tag workflows commit with enquiry acceptance; existing application's integrations remain in the app | Multi-step automation, timer delivery, email/CRM/omnichannel dispatch and suppression qualification remain open |
| Engineering and operations, chapters 27–33, 60, 64–65 | Dedicated website folder, standalone dependency lock, Docker service, documented startup, migration, functional/security tests, ownership guide | Public HTTPS/domain, pinned production images, secrets rotation, backup/restore drill, deployed monitoring and privacy/legal sign-off |
| Conditional modules, chapters 25, 54, 61, 75 | Not activated by this landing-page request | Commerce, booking, marketplaces, regulated/minor data, donations, paid-media operations and campaign spending require a business brief and approved providers |

The entire extracted blueprint is retained under `docs/reference`. A documented requirement is not represented as an implemented, activated, or verified capability.

All 120 capabilities are available in `src/requirements.json` and the searchable owner-console register. Each keeps specification, applicability, implementation, activation and verification separate. The user selected the SaaS profile and supplied **TalkToBot.io**, **Northstar edtech** and **tech@northstaracad.com**. See [the owner manual](owner-console.md) for current workflows and exact boundaries; many full-chapter acceptance packs remain incomplete.

## API contracts

All routes are below `/api/v1`:

| Route | Access | Behavior |
| --- | --- | --- |
| `GET /website/posts` | Public | Published snapshots only; maximum 200 newest records |
| `GET /website/posts/{slug}` | Public | Published snapshot or 404; no shared caching |
| `POST /website/inquiries` | Public | UUID idempotency key, consent and honeypot validation; 201 only after commit |
| `GET /platform-admin/website/access` | Editor | Check website publishing authorization |
| `GET /platform-admin/website/posts` | Editor | Working drafts, live state and trash; maximum 500 newest records |
| `POST /platform-admin/website/posts` | Editor | Create a draft and revision, reserve stable slug |
| `PUT /platform-admin/website/posts/{id}` | Editor | Version-checked draft save; never changes the live snapshot |
| `POST /platform-admin/website/posts/{id}/actions` | Editor | Review/approve/publish/schedule, unpublish, reasoned trash and restore to draft |
| `GET /platform-admin/website/posts/{id}/revisions` | Editor | Preserved source/action/actor/version history |
| `GET /platform-admin/website/inquiries` | Editor | Accepted enquiries; maximum 500 newest records |
| `GET /website/manifest` | Public | Live page/navigation/form/brand/redirect/collection/entry snapshots |
| `POST /website/forms/{key}/submit` | Public | Published schema, consent and idempotent private submission |
| `GET /website/media/{id}` | Public | Validated derivative only when referenced by a live page/article |
| `/platform-admin/website/resources` and `/{id}/actions`, `/{id}/history` | Editor | Versioned builder resources, approvals, publication/schedules and preserved history |
| `/platform-admin/website/media` and `/{id}/preview` | Editor | Validate/re-encode/upload private images; authenticated thumbnail previews |
| `/platform-admin/website/leads`, `/audit`, `/overview`, `/quality` | Editor | Private lead operations, append-only audit, actual counts and read-only content checks |
| `/platform-admin/website/imports`, `/exports` | Editor | Atomic draft imports with dry run/checksum; audited checksummed archives |

Article fields: title, slug, excerpt, body, author, category, tags, cover, cover_alt, seo_title, seo_description. Updates/actions require the current version. Cover images are validated as PNG/JPEG/WebP, at most 2 MB and 16 million pixels. Source is retained as structured text, not executable HTML. Slugs cannot be changed after first save.

Enquiry fields: id, name, email, company, message, kind (`demo`, `contact`, `white-label`), consent, honeypot `website`. There is no public enquiry-read endpoint. A changed payload reusing an accepted UUID returns 409.

## Verification and release checks

The owner-console extension is covered in [the current acceptance report](../../reports/website-qa/owner-results.md): 12 website/backend cases, 14 configuration cases, 8 Node cases, strict builds/types/lint, actual PostgreSQL grants/scheduling/object storage and browser journeys. The following paragraph records the earlier landing-page baseline.

Completed local results: strict website build passed; Node server tests **4 passed**; focused backend configuration/CMS tests **18 passed**; Ruff and focused CMS mypy checks passed. Actual Docker/PostgreSQL migration, restricted table privileges, editor login/Markdown upload/save/publish, public article HTML/sitemap, and browser enquiry-to-inbox checks passed. Desktop and mobile checks found no horizontal overflow or JavaScript errors. Screenshots and detailed evidence are in [the acceptance report](../../reports/website-qa/results.md).

- Website strict TypeScript check and production build.
- Python Ruff and focused mypy checks for new CMS code.
- CMS acceptance tests: unauthorized access, ordinary-account publishing rejection, draft privacy, publication snapshots, optimistic edit conflict, reasoned trash, retained history, restore, absent permanent deletion, durable idempotent enquiries, consent enforcement, fake/active image rejection.
- Browser verification: desktop and mobile landing page, article reader, editor login/publish flow, contact acceptance, navigation targets, overflow, network/console failures.
- PostgreSQL migration and role verification in the actual local stack.
- Crawlable article HTML, publication-aware sitemap, editor noindex, API proxy, and 404 checks on the website server.

## Production handover dependencies

Configure verified HTTPS app/site/API origins and `WEBSITE_EDITOR_EMAILS`; rotate development administrator credentials and the shared `WEBSITE_PROXY_SECRET`. Configure trusted ingress CIDRs explicitly. Finalize company/jurisdiction policies, enquiry retention/rights handling, response ownership, media rights, provider terms and claims. Choose email/CRM/analytics providers and implement/qualify the required delivery paths. Establish independent audit archives, storage protection, database/object-store backups and restore drills. Run load, accessibility, supply-chain and security qualification before a production sign-off. The full register records remaining implementation work as well as external activation gates.

Website health is `/healthz`; API readiness remains `/health/ready`. A website process health check alone does not prove that enquiries or integrations work. Test the primary submission journey as part of release qualification.
