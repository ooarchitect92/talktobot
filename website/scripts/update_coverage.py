"""Update the retained 120-row source register without inventing qualification."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "src/requirements.json"
rows = json.loads(path.read_text(encoding="utf-8"))
implemented = {
    1: "Confirmed SaaS profile, domain, company/contact and honest enquiry outcome are recorded in docs/business-brief.md; pricing, personas and legal review remain open.",
    2: "Public marketing, contact, pricing, article and collection routes; managed navigation and sitemap. Full customer-journey qualification remains open.",
    3: "Responsive PDF-derived design, semantic forms, keyboard section reordering and reduced-motion styling. Formal accessibility qualification remains open.",
    4: "Controlled section/page builder, navigation, form builder, brand settings and media library work locally. Delegated permissions and extension governance remain open.",
    5: "Resource autosave, 24-hour recovery, undo/redo, duplicate drafts and download-before-reload conflict handling. Complete multi-operator evidence remains open.",
    6: "Controlled informational schemas and entries, publication templates and breaking-schema rejection. Migration tooling and specialist templates remain open.",
    7: "Blog/resource reviews, approvals, versions, private previews, UTC durable schedules and a review calendar. Two-person release approvals remain open.",
    8: "Atomic draft-only imports with dry-run/checksum and duplicate validation; checksummed content/history archives. Full database/media restore and legacy migration remain open.",
    9: "Reasoned manual trash/restore, no automatic expiry and no permanent purge endpoint. Approved legal purge/hold/restore-reconciliation workflows remain open.",
    10: "Validated raster re-encoding, private previews, public-reference authorization, derivatives, rights/alt/AI provenance records. Original archival and quarantine lifecycle remain open.",
    11: "Complete server-rendered public HTML, status codes, canonical/OG metadata and index policies. Deployed infrastructure checks remain open.",
    12: "Publication-aware paginated sitemap retrieval, RSS and load-more blog access. Feed-scale partitioning and complete URL-facet tests remain open.",
    14: "Declared editorial review dates, publication calendar and internal-link checks. Search-intent mapping and a broader content plan remain open.",
    19: "Private offer/claim records include audience, inclusions/exclusions, proof, terms, price and review date. Cross-channel enforcement remains open.",
    20: "Rights/provenance media metadata and draft previews. Full creative variant and claim approval lifecycle remains open.",
    30: "Approved nonpersonal UTM campaign-link builder and safe redirect preservation. Consent-aware click-ID attribution is not implemented.",
    35: "Gateway purpose-limited HMAC context verifies observed/trusted-proxy addresses for abuse limits; rejects spoofing, stale signatures and mismatched paths. Coarse-location collection is disabled.",
    37: "Illustrative on-page assistant and existing application help/knowledge links. A live public contextual chatbot and verified handoff are not implemented.",
    38: "Controlled form fields, server validation, consent, honeypot, rate limiting, private answers and durable UUID idempotency.",
    39: "Private enquiry pipeline, explicit stage/assignment/notes/tags and local routing. CRM provider delivery, merge and escalation remain open.",
    40: "Human-reviewed local enquiry assignment/tag workflows and a non-writing simulation. Multi-step timers, messaging and dispatch gates remain open.",
    48: "QR/partner campaign UTM labels can be generated. QR asset generation, offline conversion provenance and reconciliation remain open.",
    51: "Real owner content/enquiry counts and content-quality reports. Marketing/spend warehouse and reconciliation remain open.",
    52: "Authenticated redacted audit exports and contact-excluding content archives; contact inclusion requires an explicit selection. Scheduled report delivery remains open.",
    54: "Requested domain is recorded as TalkToBot.io. Registrar ownership, production DNS/TLS, renewal and recovery remain unverified.",
    55: "Existing account auth, explicit editor allowlist, MFA/recovery challenge UI, logout/private-state clearing and session revalidation. Scoped staff roles and production MFA policy remain open.",
    57: "Server authority, version checks, bounded raster uploads, controlled local links and safe text rendering. Formal penetration/abuse qualification remains open.",
    58: "Restrictive CSP and no optional external scripts. A consent-aware script registry and approved optional measurement are not implemented.",
    59: "Separate lockfiles and strict builds. Production SBOM, license review and protected dependency/security release evidence remain open.",
    60: "Consent/field checks, honeypots, per-client signed abuse context and server rate limits. Provider messaging/fraud budgets remain open.",
    61: "Response consent is distinct from marketing enrollment; no optional trackers, replay or browser location collection. A full purpose/GPC policy engine remains open.",
    62: "Named privacy email/contact path and private operator records. Verified rights cases, retention/holds, processor deletion and restore reconciliation are not implemented.",
    64: "Transactional attributable operations and retained revisions, role-protected append-only tables, redacted audit views. Independent integrity checkpoints remain open.",
    65: "SQLAlchemy models, uniqueness/FKs, PostgreSQL migration and constrained table grants. Production pooling/load/isolation qualification remains open.",
    66: "Private object-store derivatives, authenticated previews, no-store public-reference media and immediate unpublish revocation. CDN qualification remains open.",
    67: "Existing versioned FastAPI/OpenAPI contracts expose website operations. Formal external event contract qualification remains open.",
    69: "Durable approved schedules restart safely and recheck actor/dependencies; enquiries are idempotent and local effects are atomic. External delivery outbox is not implemented.",
    70: "Dedicated website native build/server plus Docker website/API/scheduler profile. Public cloud deployment remains pending.",
    72: "Website process health, existing API readiness, worker error logs and operator content checks. Production SLO/alert/incident qualification remains open.",
    73: "Checksummed content/history export separates image bytes and infrastructure backup needs. PITR, independent backups and restore drills remain open.",
    78: "Subscriptions, usage/entitlements and the customer portal belong to the existing SaaS application; website links reuse that identity. Billing/provider qualification is separate.",
    79: "Partner/white-label enquiries and private offer records support the SaaS profile. Quote/org/partner transaction workflows remain open.",
    88: "Local article search/category filters and informational collection routes. AI public search/relevance rebuild workflows remain open.",
    89: "Owner manual, retained source references, independent website folder and portable draft/archive formats. Second-team handover exercise remains open.",
    90: "Focused backend/gateway/browser evidence and the 120-capability register are retained. Full launch, cost, restore and operating evidence remains open.",
    95: "AI generation provenance is stored separately from stripped image metadata. Full chain-of-custody qualification remains open.",
    106: "Full HTML SSR, same-origin metadata/status and real 404/503 handling. Production CDN/streamed status tests remain open.",
    107: "robots/sitemap routes and gateway upstream failures return honest status. External discovery-failure alerting remains open.",
    108: "Local route/redirect/dependency validation and publication snapshot tests. Complete multi-locale/migration acceptance packs remain open.",
    112: "Owner visibility/back-forward revalidation hides private UI while checking access. Full cross-tab/recovery qualification remains open.",
    116: "Keyboard-operable builders, owner manual and recoverable drafts. Formal second-operator accessibility completion remains open.",
    120: "All source CAP rows are retained with five distinct dimensions and explicit gaps. Production release sign-off is not granted.",
}
tests = ["backend/tests/test_website_cms.py", "backend/tests/test_website_operations.py", "backend/tests/test_website_request_context.py", "website/tests/server.test.mjs", "website/tests/proxy-context.test.mjs"]
optional = {75, 76, 77, 80, 81, 82, 83, 84, 85, 86, 87, 118}
for row in rows:
    number = int(row["id"].split("-")[1])
    row["review_date"] = "2026-10-12"
    row["ui_route"] = "/admin/console"
    row["owner"] = "Northstar edtech website owner / engineering"
    row["dependencies"] = ["Chapter-specific acceptance pack", "Production release evidence"]
    row["activation"] = "not activated in production"
    row["verification"] = "full capability qualification not executed"
    row["tests"] = []
    row["evidence"] = ["website/docs/business-brief.md", "website/docs/owner-console.md"]
    if number in implemented:
        row["applicability"] = "applicable"
        row["implementation"] = "partial"
        row["rationale"] = implemented[number]
        row["tests"] = tests
        row["activation"] = "local implemented subset; production pending"
        row["verification"] = "focused local checks; full chapter qualification pending"
    elif number in optional:
        row["applicability"] = "outside selected SaaS marketing profile"
        row["implementation"] = "not implemented"
        row["activation"] = "not selected"
        row["rationale"] = "The user selected the AI SaaS website and owner console rather than commerce, booking, specialist industry and other conditional transaction portals. Requires a separate business activation brief."
    else:
        row["applicability"] = "applicable / activation decision pending"
        row["implementation"] = "not implemented"
        row["rationale"] = "Retained as an explicit implementation/release gap. A readiness panel or saved definition does not implement the chapter workflow."
    if 21 <= number <= 29 or 97 <= number <= 105 or number == 119:
        row["dependencies"] += ["Approved provider/account contracts", "Advertising data/consent policy", "Explicit spending/write authority"]
    if number in {31, 32, 33, 34, 41, 42, 43, 44, 46, 47, 51, 52, 53, 61, 62, 110, 111, 113, 114, 115}:
        row["dependencies"] += ["Approved measurement/delivery purpose", "Consent/retention decisions", "Provider selection where required"]
assert len(rows) == 120 and len({row["id"] for row in rows}) == 120
path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("Updated all 120 capability records; no full-capability production qualification claimed.")
