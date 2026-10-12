# TalkToBot owner console

Open `/admin/console` after signing in to the article studio. Identity comes from the existing TalkToBot application. An explicitly authorized website editor can manage the platform website; a customer account or API key cannot. MFA challenges and recovery codes are supported when enabled in the application account. Production editor enrollment and scoped staff permissions remain release work.

## Content and publishing

**Pages:** choose a stable key and local route, title, description, audience, owner, review date and index policy. Add and reorder hero, text, CTA, FAQ, form and image sections. Buttons move sections without requiring drag gestures. Uploaded images need contextual alternative text. Draft preview is private. Built-in marketing/legal pages can be overridden through an approved page; article routes remain owned by the article studio.

**Navigation:** publish up to twelve labeled local links. **Redirects:** publish 301/302/308 mappings; loops, duplicate sources and missing destinations are rejected. **Brand:** choose an approved palette and edit tagline, company and contact email. Only one navigation and brand resource can be live at a time.

**Forms:** define named, labeled fields with approved types and bounded choices. Every contact form includes name/email and response consent. Publish the form before placing it on a page. Submissions are private, validated on the server, idempotent and acknowledged after commit. Acceptance confirms storage, not an email, purchase or meeting. Honeypots and rate limits apply.

**Collections:** define controlled text, number, boolean and date fields. Create entries against the schema, then publish the collection before its entries. They appear under `/collections/{collection}/{entry}`. Removing a collection from publication hides its entries. Breaking schema changes with existing entries require a reviewed migration.

**Article studio:** upload Markdown, text or JSON; save, review, approve, publish or schedule. Changes to a live article remain private until the next publication. Trash always requires a reason and retains source/revisions. Restore returns to draft. Publication has no automatic expiry. No permanent purge action is provided.

**Review workflow:** every save uses an optimistic version check. Review and approval apply to the saved revision. Any subsequent save cancels approval and scheduled publication. Previous live content remains available. Single-operator review/approval is supported; this is not a two-person approval policy.

**Scheduling:** choose a device-local future time. The stored execution instant is UTC; the editorial timezone is retained. A durable worker resumes due schedules after restarts, rechecks the actor and publication dependencies, and switches the live snapshot transactionally. Failed schedules preserve the previous live revision. The content calendar also displays declared review dates; reminders never expire or delete content.

**Recovery:** resource drafts autosave after a short idle period once created. New resources need an initial save. Undo/redo affects local edits. Browser recovery copies expire after 24 hours and are cleared on logout. Conflicts stop saving. Download local work and reload the current server revision, or duplicate it under a new key and resolve route/dependency collisions. Session storage is a convenience, not a backup.

## Media and operations

**Media:** upload PNG/JPEG/WebP below 2 MB with title, alt text, rights record and optional AI provenance. The server validates actual bytes, limits pixels, re-encodes a bounded WebP and thumbnail, and strips embedded metadata. Metadata/provenance are stored separately. Uploaded originals are not retained. Derivatives live in the private application object store. Private previews require authentication; public reads require a live page/article reference. Use a copied media URL as a blog cover. Content archives contain metadata, not image bytes.

**Lead pipeline:** inspect accepted enquiries, assign an operator, add private notes/tags and update stage with a reason. Qualification is an explicit operator decision. Workflows may assign or tag a lead in the same transaction that accepts an enquiry. There is no email/CRM dispatch, timer graph, automated qualification or subscription enrollment.

**Campaign links and offers:** build links with approved nonpersonal UTM labels; record offer audience, inclusions, exclusions, proof, terms and review date. This does not launch ads, change billing or imply visitor attribution. Current offers are private registry records; marketing page copy must be reviewed separately for consistency.

**Experiments:** save hypotheses, control/treatment headlines and planned sample/window. Public activation is deliberately blocked. Consent-aware assignment, exposure measurement, A/A qualification and statistical decision controls still require implementation and release evidence.

**Audit:** search append-only operation records by kind/action and paginate or export the visible redacted page. Dedicated history views contain protected revision snapshots. The application database role cannot update/delete operations or delete revision/enquiry records. This is not an independent tamper-proof audit archive.

**Import/export:** validate a JSON array of `{kind,key,title,data}` resources, or a `resources` envelope. Dry runs write nothing. Apply requires the validation checksum and an import reason; all rows become new private drafts in one transaction. Duplicate keys reject the batch. Imports never overwrite existing resources or restore publication state. A content archive preserves content, revisions, metadata and operations with a SHA-256 checksum. Private contact data is excluded unless explicitly selected. Larger datasets require database backups; exports are limited to 10,000 rows per table. Protect downloaded files. Back up object storage separately.

**Content checks:** run a read-only scan of live internal destinations, missing page descriptions and overdue declared reviews. It reports dependencies removed after publication. It does not certify accessibility, security, search eligibility or production availability.

## Production ownership and full-document status

Domain: TalkToBot.io. Company: Northstar edtech. Contact/privacy email: tech@northstaracad.com. Jurisdiction, registration details, final policies, retention periods, email/CRM/analytics providers and public DNS/HTTPS are not confirmed.

The searchable/exportable blueprint register includes all CAP-001–CAP-120 rows from the source document, with chapter references and separate specification/applicability/implementation/activation/verification states. Applicable modules not built or fully qualified remain visible. Conditional commerce, bookings, marketplaces and specialist industry portals are outside the user-selected SaaS marketing profile. The existing application's subscription and customer portal capability remains relevant; it is not duplicated in the website.

External providers, consent-aware marketing measurement, live experiments, advanced automation/scoring, scoped editorial roles, independent audit protection, formal privacy/purge workflows, production monitoring and recovery qualification remain explicit gaps. Completion of this local website must not be represented as completion of every applicable blueprint acceptance pack or a public production sign-off.
