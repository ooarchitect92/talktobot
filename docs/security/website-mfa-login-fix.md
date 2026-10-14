# Website MFA login correction

The website previously discarded the password accepted by login before authenticator enrollment. Users reached a second password form without a QR; a short password was stopped by native browser validation before actionable feedback. The website now prepares the QR with that just-verified password once, in memory only, then exposes the authenticator confirmation control. Manual fallback shows an explicit short-password error in both frontends.

The API adapter now displays standardized error-envelope messages. After successful factor confirmation, an access/verification failure returns to sign-in with an explicit connected-authenticator message instead of presenting a new setup form. No factor is reset, no verification is bypassed, and later logins still require a code. Existing article approval behavior is unchanged.

Local verification: production website client/SSR build; 11 website server tests; eight customer MFA/login/challenge tests; frontend lint and types; real Chromium acceptance against the built website with intercepted synthetic API responses. Browser acceptance verifies actual PNG loading, visible confirmation, editorial approval for a reviewed draft, subsequent code challenge, actionable failed-setup/short-password feedback, and no credentials in browser storage. It does not qualify SMTP delivery or a real user's phone.

The staging manifest retains the explicitly authorized Irfat owner/editor access and full-access tenant ID, so deploying this fix will not remove the new account's configuration. Production billing remains disabled; no broad SaaS/catalog/monitoring worktree changes are included.

Review status: local candidate only. The user's production directive section 5 requires approval before merge/deployment. Exact-commit CI and release scanning remain required before staging rollout. A live synthetic browser check must follow rollout; users' factor material must not be inspected or reset.
