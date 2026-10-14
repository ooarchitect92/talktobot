"""Exercise the built website with intercepted synthetic auth; never contact live accounts.

Run after `npm run build --prefix website`, using the backend development venv.
"""

import json
import os
import socket
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
origin = f"http://127.0.0.1:{port}"
report_dir = ROOT / "reports/readiness"
report_dir.mkdir(parents=True, exist_ok=True)
environment = dict(
    os.environ,
    PORT=str(port),
    HOST="127.0.0.1",
    APP_ENV="test",
    API_ORIGIN="http://127.0.0.1:9",
    WEBSITE_PUBLIC_URL=origin,
    WEBSITE_APP_URL=origin,
)
password = "Synthetic-sign-in-only-2026!"
secret = "JBSWY3DPEHPK3PXP"  # Public fixture, never a deployed factor.
uri = f"otpauth://totp/TalkToBot:synthetic%40example.com?secret={secret}&issuer=TalkToBot"
state = {"confirmed": False, "setupCalls": 0, "approvals": 0, "rejectSetup": False, "denyAccess": False, "verifyCalls": []}
post = dict(
    id="11111111-1111-4111-8111-111111111111", slug="synthetic-review",
    title="Synthetic review article", excerpt="Synthetic acceptance content", body="A synthetic article.",
    author="Synthetic author", category="Guides", tags=[], cover="", cover_alt="",
    status="draft", version=1, published_at=None, updated_at=datetime.now(UTC).isoformat(),
    seo_title="", seo_description="", workflow_status="in_review", scheduled_at=None,
    editorial_timezone="UTC",
)


def intercept(route):
    request = route.request
    path = request.url.split("/api/v1", 1)[1]
    status, value = 200, {}
    if path == "/auth/refresh":
        status = 401
    elif path == "/auth/login":
        if state["confirmed"]:
            value = {"challengeToken": "synthetic-challenge"}
        else:
            value = {"mfaEnrollmentRequired": True, "enrollmentToken": "synthetic-enrollment",
                     "expiresAt": (datetime.now(UTC) + timedelta(minutes=5)).isoformat()}
    elif path == "/auth/mfa/setup":
        state["setupCalls"] += 1
        assert request.headers.get("authorization") == "Bearer synthetic-enrollment"
        assert request.post_data_json["currentPassword"] == password
        if state["rejectSetup"]:
            status, value = 503, {"error": {"message": "Unable to email recovery codes. Retry setup shortly."}}
        else:
            value = {"secret": secret, "otpauthUri": uri, "recoveryCodesEmailed": True}
    elif path == "/auth/mfa/confirm":
        assert request.post_data_json["code"] == "123456"
        state["confirmed"] = True
        value = {"accessToken": "synthetic-session"}
    elif path == "/auth/mfa/verify":
        assert request.post_data_json["challengeToken"] == "synthetic-challenge"
        state["verifyCalls"].append(request.post_data_json)
        value = {"accessToken": "synthetic-session"}
    elif path == "/platform-admin/website/access":
        value = {"allowed": True, "roles": ["editor", "publisher", "lead_operator"]}
        if state["denyAccess"]:
            status, value = 428, {"error": {"message": "Verify your email address before continuing"}}
    elif path == "/platform-admin/website/posts":
        value = [post]
    elif path.endswith("/actions") and request.post_data_json.get("action") == "approve":
        state["approvals"] += 1
        post["workflow_status"] = "approved"
        post["version"] += 1
        value = post
    elif path == "/platform-admin/website/starter-guides":
        value = []
    route.fulfill(status=status, content_type="application/json", body=json.dumps(value))


def login(page):
    page.goto(origin + "/admin")
    page.get_by_label("Email", exact=True).fill("synthetic@example.com")
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_role("button", name="Sign in to the editor").click()


with (report_dir / "website-mfa-local-server.log").open("wb") as output:
    process = subprocess.Popen(
        ["node", "server.mjs"], cwd=ROOT / "website", env=environment,
        stdout=output, stderr=output,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError("Owned website preview exited")
            try:
                with urlopen(origin + "/admin", timeout=1):
                    break
            except OSError:
                time.sleep(0.25)
        else:
            raise RuntimeError("Owned website preview did not start")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            context.route("**/api/v1/**", intercept)
            page = context.new_page()
            login(page)
            image = page.get_by_alt_text("Scan to add TalkToBot to your authenticator")
            expect(image).to_be_visible()
            assert image.get_attribute("src").startswith("data:image/png;base64,")
            page.wait_for_function("document.querySelector('img[alt^=\"Scan to add\"]')?.naturalWidth === 240")
            assert state["setupCalls"] == 1
            expect(page.get_by_label("Verify your sign-in password")).to_have_count(0)
            confirm = page.get_by_role("button", name="Verify code and finish setup")
            expect(confirm).to_be_disabled()
            page.get_by_label("I received my recovery codes by email.").check()
            page.get_by_label("Six-digit code", exact=True).fill("123456")
            confirm.click()
            page.get_by_text(post["title"], exact=True).click()
            page.get_by_label("Editorial action reason").fill("Reviewed synthetic acceptance article")
            approve = page.get_by_role("button", name="Approve draft", exact=True)
            expect(approve).to_be_enabled()
            approve.click()
            expect(page.get_by_role("button", name="Publish", exact=True)).to_be_enabled()
            assert state["approvals"] == 1
            login(page)
            expect(page.get_by_label("Six-digit authenticator code")).to_be_visible()
            assert state["setupCalls"] == 1
            page.get_by_label("Six-digit authenticator code").fill("1234")
            page.get_by_role("button", name="Verify and sign in").click()
            expect(page.get_by_role("alert")).to_contain_text("exactly six digits")
            assert not state["verifyCalls"]
            page.get_by_label("Six-digit authenticator code").fill("654 321")
            page.get_by_role("button", name="Verify and sign in").click()
            expect(page.get_by_text(post["title"], exact=True)).to_be_visible()
            assert state["verifyCalls"][-1]["code"] == "654321"
            assert "recoveryCode" not in state["verifyCalls"][-1]
            login(page)
            page.get_by_role("button", name="Use a recovery code instead").click()
            page.get_by_label("Recovery code", exact=True).fill("synthetic-recovery-code")
            page.get_by_role("button", name="Verify and sign in").click()
            expect(page.get_by_text(post["title"], exact=True)).to_be_visible()
            assert state["verifyCalls"][-1]["recoveryCode"] == "synthetic-recovery-code"
            assert "code" not in state["verifyCalls"][-1]
            stored = page.evaluate("[...Object.values(localStorage), ...Object.values(sessionStorage)]")
            assert all(password not in value and secret not in value for value in stored)
            context.close()
            state.update(confirmed=False, rejectSetup=True)
            context = browser.new_context()
            context.route("**/api/v1/**", intercept)
            page = context.new_page()
            login(page)
            expect(page.get_by_role("alert")).to_be_visible()
            expect(page.get_by_role("alert")).to_contain_text("Unable to email recovery codes")
            page.get_by_label("Verify your sign-in password").fill("123456")
            page.get_by_role("button", name="Verify password and show QR").click()
            expect(page.get_by_role("alert")).to_contain_text("full sign-in password")
            assert state["setupCalls"] == 2
            context.close()
            state.update(confirmed=False, rejectSetup=False, denyAccess=True)
            context = browser.new_context()
            context.route("**/api/v1/**", intercept)
            page = context.new_page()
            login(page)
            expect(page.get_by_alt_text("Scan to add TalkToBot to your authenticator")).to_be_visible()
            page.get_by_label("I received my recovery codes by email.").check()
            page.get_by_label("Six-digit code", exact=True).fill("123456")
            page.get_by_role("button", name="Verify code and finish setup").click()
            expect(page.get_by_role("alert")).to_contain_text("Authenticator connected")
            expect(page.get_by_role("alert")).to_contain_text("Verify your email address")
            expect(page.get_by_label("Password", exact=True)).to_be_visible()
            login(page)
            expect(page.get_by_label("Six-digit authenticator code")).to_be_visible()
            assert state["setupCalls"] == 3
            context.close()
            browser.close()
        result = {"automaticQrVisible": True, "qrPngLoaded": True, "confirmationVisible": True, "explicitCodeModesVerified": True,
                  "editorialApprovalVisibleAndWorking": True, "subsequentLoginUsesChallenge": True,
                  "shortPasswordErrorVisible": True, "credentialsNotPersisted": True,
                  "confirmedFactorRetainedAfterAccessFailure": True,
                  "scope": "Built website; intercepted synthetic API, not live provider acceptance"}
        (report_dir / "website-mfa-browser.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
    finally:
        process.terminate()
        process.wait(timeout=15)
