"""Public marketing content and a separately authorized, single-site owner CMS.

Website content is global platform content, never a tenant's knowledge library.
No age-based deletion or permanent-purge endpoint is provided.
"""

from __future__ import annotations

import base64
import hashlib
import io
import re
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from northstar_api.config import get_settings
from northstar_api.database import Base
from northstar_api.dependencies import CurrentPrincipal, DBSession
from northstar_api.models import User
from northstar_api.security import Principal
from northstar_api.services.email_verification import email_is_verified
from northstar_api.services.rate_limit import redis_services
from northstar_api.website_request_context import website_client_address


class WebsitePost(Base):
    __tablename__ = "website_posts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    document: Mapped[dict[str, Any]] = mapped_column(JSON)
    published_document: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    workflow_status: Mapped[str] = mapped_column(String(30), default="draft")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    editorial_timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")


class WebsiteRevision(Base):
    __tablename__ = "website_revisions"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    post_id: Mapped[UUID] = mapped_column(ForeignKey("website_posts.id", ondelete="RESTRICT"))
    version: Mapped[int] = mapped_column(Integer)
    document: Mapped[dict[str, Any]] = mapped_column(JSON)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class WebsiteInquiry(Base):
    __tablename__ = "website_inquiries"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    document: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PostInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=180)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    excerpt: str = Field(default="", max_length=500)
    body: str = Field(min_length=10, max_length=100_000)
    author: str = Field(default="TalkToBot editorial", min_length=1, max_length=100)
    category: str = Field(default="Guides", min_length=1, max_length=60)
    tags: list[str] = Field(default_factory=list, max_length=12)
    cover: str = Field(default="", max_length=2_900_000)
    cover_alt: str = Field(default="", max_length=250)
    seo_title: str = Field(default="", max_length=180)
    seo_description: str = Field(default="", max_length=320)
    version: int | None = Field(default=None, ge=1)

    @field_validator("cover")
    @classmethod
    def validate_cover(cls, value: str) -> str:
        if not value:
            return value
        if re.fullmatch(r"/api/v1/website/media/[0-9a-f-]{36}", value):
            return value
        if not re.fullmatch(r"data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+", value):
            raise ValueError("Upload a PNG, JPEG or WebP cover")
        try:
            raw = base64.b64decode(value.split(",", 1)[1], validate=True)
            if len(raw) > 2_000_000:
                raise ValueError("Cover must be below 2 MB")
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 16_000_000:
                    raise ValueError("Cover dimensions are too large")
                if image.format not in {"PNG", "JPEG", "WEBP"}:
                    raise ValueError("Invalid cover format")
                image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Invalid image") from exc
        return value

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        if any(len(value) > 60 for value in values):
            raise ValueError("Tags must be below 60 characters")
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class ActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    action: str = Field(pattern=r"^(review|approve|schedule|publish|unpublish|trash|restore)$")
    reason: str = Field(default="", max_length=500)
    scheduled_at: datetime | None = None
    editorial_timezone: str = Field(default="Asia/Kolkata", max_length=64)


class InquiryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    company: str = Field(default="", max_length=150)
    message: str = Field(min_length=10, max_length=4000)
    kind: str = Field(default="demo", pattern=r"^(demo|contact|white-label)$")
    consent: bool
    website: str = Field(default="", max_length=200)


def editor_roles(email: str) -> set[str]:
    settings = get_settings()
    if not settings.is_production and not settings.website_editor_roles:
        return {"editor", "publisher", "lead_operator"}
    return {
        role
        for key, roles in settings.website_editor_roles.items()
        if key.strip().lower() == email.strip().lower()
        for role in roles
    }


async def require_editor(
    principal: CurrentPrincipal,
    session: DBSession,
    request: Request,
    include_contacts: Annotated[bool, Query()] = False,
) -> Principal:
    settings = get_settings()
    if principal.token_id.startswith("api_key:") or principal.impersonation_id:
        raise HTTPException(403, "A website editor account is required")
    user = await session.get(User, principal.user_id)
    allowed = {email.strip().lower() for email in settings.website_editor_emails.split(",") if email.strip()}
    # Local operator convenience only; production always needs an explicit allowlist.
    if not settings.is_production and settings.seed_admin_email:
        allowed.add(str(settings.seed_admin_email).lower())
    if not user or not user.is_active or user.email.lower() not in allowed:
        raise HTTPException(403, "This account cannot edit the public website")
    if not await email_is_verified(session, user.id):
        raise HTTPException(403, "Verify your email before accessing the owner console")
    roles = editor_roles(user.email)
    if not roles:
        raise HTTPException(403, "Website staff role is required")
    request.state.website_roles = sorted(roles)
    path = request.url.path
    if path.endswith(("/access", "/overview")):
        return principal
    is_lead = any(segment in path.split("/") for segment in ("leads", "inquiries", "submissions"))
    if path.endswith("/exports") and include_contacts:
        is_lead = True
    if is_lead:
        if "lead_operator" not in roles:
            raise HTTPException(403, "Lead access is required")
    elif not roles.intersection({"editor", "publisher"}):
        raise HTTPException(403, "Content access is required")
    if request.method == "POST" and path.endswith("/actions"):
        payload = await request.json()
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("action"), str)
            and payload.get("action")
            in {
                "approve",
                "publish",
                "schedule",
                "unpublish",
                "archive",
                "trash",
                "restore",
            }
        ):
            if "publisher" not in roles:
                raise HTTPException(403, "Publishing access is required")
    return principal


EditorPrincipal = Annotated[Principal, Depends(require_editor)]


def website_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


public = APIRouter(prefix="/website", tags=["public website"], dependencies=[Depends(website_no_store)])
admin = APIRouter(
    prefix="/platform-admin/website", tags=["website CMS"], dependencies=[Depends(website_no_store)]
)


def project_post(post: WebsitePost, *, published: bool = False) -> dict[str, Any]:
    document = post.published_document if published else post.document
    return {
        **(document or {}),
        "id": str(post.id),
        "slug": post.slug,
        "status": post.status,
        "workflow_status": "published" if published else post.workflow_status,
        "scheduled_at": None if published or not post.scheduled_at else post.scheduled_at.isoformat(),
        "editorial_timezone": "UTC" if published else post.editorial_timezone,
        "version": (document or {}).get("_published_version", post.version) if published else post.version,
        "updated_at": (document or {}).get("_published_updated_at", post.updated_at.isoformat())
        if published
        else post.updated_at.isoformat(),
        "published_at": post.published_at.isoformat() if post.published_at else None,
    }


async def find_post(session: DBSession, post_id: UUID, version: int) -> WebsitePost:
    post = await session.scalar(
        select(WebsitePost)
        .where(WebsitePost.id == post_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if post is None:
        raise HTTPException(404, "Article not found")
    if post.version != version:
        raise HTTPException(409, "Another editor changed this article. Reload before saving.")
    return post


def revision(session: DBSession, post: WebsitePost, actor: Principal, action: str, reason: str = "") -> None:
    from northstar_api.website_operations import audit

    audit(
        session,
        str(post.id),
        "article",
        action,
        post.version,
        actor.user_id,
        {"title": post.document.get("title"), "fields": list(post.document)},
        reason,
    )
    session.add(
        WebsiteRevision(
            post_id=post.id,
            version=post.version,
            document=dict(post.document),
            actor_id=actor.user_id,
            action=action,
            reason=reason,
        )
    )


@public.get("/posts")
async def public_posts(
    session: DBSession,
    response: Response,
    limit: int = Query(200, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    response.headers["Cache-Control"] = "no-store"
    posts = await session.scalars(
        select(WebsitePost)
        .where(WebsitePost.status == "published")
        .order_by(WebsitePost.published_at.desc(), WebsitePost.id)
        .offset(offset)
        .limit(limit)
    )
    return [project_post(post, published=True) for post in posts]


@public.get("/posts/{slug}")
async def public_post(slug: str, session: DBSession, response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    post = await session.scalar(
        select(WebsitePost).where(WebsitePost.slug == slug, WebsitePost.status == "published")
    )
    if not post:
        raise HTTPException(404, "Article not found")
    return project_post(post, published=True)


@public.post("/inquiries", status_code=201)
async def submit_inquiry(payload: InquiryInput, request: Request, session: DBSession) -> dict[str, Any]:
    if payload.website:
        raise HTTPException(400, "Unable to accept this submission")
    if not payload.consent:
        raise HTTPException(422, "Consent to respond to your enquiry is required")
    address = website_client_address(request)
    limit = await redis_services.check_rate_limit(
        f"website:inquiry:{hashlib.sha256(address.encode()).hexdigest()}", 5, scope="website"
    )
    if not limit.allowed:
        raise HTTPException(
            429,
            "Please wait before submitting another enquiry",
            headers={"Retry-After": str(limit.retry_after)},
        )
    existing = await session.get(WebsiteInquiry, payload.id)
    document = payload.model_dump(mode="json", exclude={"id", "website"})
    if existing:
        if existing.document != document:
            raise HTTPException(409, "This submission ID was already used")
        return {"id": str(existing.id), "accepted": True}
    session.add(WebsiteInquiry(id=payload.id, document=document))
    from northstar_api.website_operations import accepted_inquiry

    await accepted_inquiry(session, payload.id)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.get(WebsiteInquiry, payload.id)
        if existing is None or existing.document != document:
            raise HTTPException(409, "This submission ID was already used") from None
    return {"id": str(payload.id), "accepted": True}


@admin.get("/access")
async def editor_access(principal: EditorPrincipal, request: Request) -> dict[str, Any]:
    return {"allowed": True, "roles": request.state.website_roles}


@admin.get("/posts")
async def editor_posts(session: DBSession, principal: EditorPrincipal) -> list[dict[str, Any]]:
    posts = await session.scalars(select(WebsitePost).order_by(WebsitePost.updated_at.desc()).limit(500))
    return [project_post(post) for post in posts]


@admin.post("/posts", status_code=201)
async def create_post(payload: PostInput, session: DBSession, principal: EditorPrincipal) -> dict[str, Any]:
    if await session.scalar(select(WebsitePost.id).where(WebsitePost.slug == payload.slug)):
        raise HTTPException(409, "This article URL already exists")
    post = WebsitePost(
        id=uuid4(), slug=payload.slug, document=payload.model_dump(exclude={"version"}), version=1
    )
    session.add(post)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "This article URL already exists") from None
    revision(session, post, principal, "create")
    await session.commit()
    return project_post(post)


@admin.put("/posts/{post_id}")
async def update_post(
    post_id: UUID, payload: PostInput, session: DBSession, principal: EditorPrincipal
) -> dict[str, Any]:
    if payload.version is None:
        raise HTTPException(422, "An article version is required")
    post = await find_post(session, post_id, payload.version)
    if post.status == "trashed":
        raise HTTPException(409, "Restore the article before editing")
    if payload.slug != post.slug:
        raise HTTPException(409, "Article URLs are permanent; create a new article to use another URL")
    post.document = payload.model_dump(exclude={"version"})
    post.workflow_status = "draft"
    post.scheduled_at = None
    post.scheduled_actor_id = None
    post.version += 1
    post.updated_at = datetime.now(UTC)
    revision(session, post, principal, "save")
    await session.commit()
    return project_post(post)


@admin.post("/posts/{post_id}/actions")
async def act_on_post(
    post_id: UUID, payload: ActionInput, session: DBSession, principal: EditorPrincipal
) -> dict[str, Any]:
    post = await find_post(session, post_id, payload.version)
    if payload.action in {"review", "approve", "schedule"} and not payload.reason.strip():
        raise HTTPException(422, "Provide a reason for this editorial action")
    if payload.action in {"publish", "schedule"}:
        if post.status == "trashed":
            raise HTTPException(409, "Restore the article before publishing")
        if post.workflow_status not in {"approved", "scheduled"}:
            raise HTTPException(409, "Review and approve this draft before publication")
        if post.document.get("cover") and not post.document.get("cover_alt"):
            raise HTTPException(422, "Add alternative text to the cover image")
        if str(post.document.get("cover", "")).startswith("/api/v1/website/media/"):
            from northstar_api.website_operations import WebsiteMedia

            try:
                asset_id = UUID(post.document["cover"].rsplit("/", 1)[1])
            except ValueError:
                raise HTTPException(422, "Choose a valid uploaded cover") from None
            if not await session.get(WebsiteMedia, asset_id):
                raise HTTPException(422, "Uploaded cover does not exist")
        if payload.action == "schedule":
            if (
                not payload.scheduled_at
                or not payload.scheduled_at.tzinfo
                or payload.scheduled_at <= datetime.now(UTC)
            ):
                raise HTTPException(422, "Choose a future time with an explicit timezone")
            try:
                ZoneInfo(payload.editorial_timezone)
            except ZoneInfoNotFoundError:
                raise HTTPException(422, "Choose a valid editorial timezone") from None
            post.scheduled_at = payload.scheduled_at
            post.scheduled_actor_id = principal.user_id
            post.editorial_timezone = payload.editorial_timezone
            post.workflow_status = "scheduled"
        else:
            post.published_document = {
                **post.document,
                "_published_version": post.version + 1,
                "_published_updated_at": datetime.now(UTC).isoformat(),
            }
            post.status = "published"
            post.workflow_status = "published"
            post.published_at = post.published_at or datetime.now(UTC)
    elif payload.action in {"review", "approve"}:
        expected = "draft" if payload.action == "review" else "in_review"
        if post.status == "trashed" or post.workflow_status != expected:
            raise HTTPException(409, "Editorial state changed; reload this article")
        post.workflow_status = "in_review" if payload.action == "review" else "approved"
    elif payload.action == "unpublish":
        if post.status == "trashed":
            raise HTTPException(409, "Restore this article first")
        post.status = "draft"
        post.workflow_status = "draft"
    elif payload.action == "trash":
        if not payload.reason.strip():
            raise HTTPException(422, "Provide a reason for moving this article to trash")
        post.status = "trashed"
        post.workflow_status = "trashed"
    else:
        if post.status != "trashed":
            raise HTTPException(409, "Only trashed articles can be restored")
        post.status = "draft"
        post.workflow_status = "draft"
    if payload.action != "schedule":
        post.scheduled_at = None
        post.scheduled_actor_id = None
    post.version += 1
    post.updated_at = datetime.now(UTC)
    revision(session, post, principal, payload.action, payload.reason)
    await session.commit()
    return project_post(post)


@admin.get("/posts/{post_id}/revisions")
async def post_revisions(
    post_id: UUID, session: DBSession, principal: EditorPrincipal
) -> list[dict[str, Any]]:
    rows = await session.scalars(
        select(WebsiteRevision)
        .where(WebsiteRevision.post_id == post_id)
        .order_by(WebsiteRevision.created_at.desc())
    )
    return [
        {
            "id": str(row.id),
            "version": row.version,
            "action": row.action,
            "reason": row.reason,
            "actor_id": str(row.actor_id),
            "created_at": row.created_at.isoformat(),
            "document": row.document,
        }
        for row in rows
    ]


@admin.get("/inquiries")
async def editor_inquiries(session: DBSession, principal: EditorPrincipal) -> list[dict[str, Any]]:
    rows = await session.scalars(select(WebsiteInquiry).order_by(WebsiteInquiry.created_at.desc()).limit(500))
    return [{**row.document, "id": str(row.id), "created_at": row.created_at.isoformat()} for row in rows]
