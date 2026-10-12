"""Versioned owner-controlled website resources and attributable operations.

Public reads use immutable publication snapshots. External advertising and
communication are never dispatched by saving a resource.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from PIL import Image
from pydantic import BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, field_validator, model_validator
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from northstar_api.database import Base
from northstar_api.dependencies import DBSession
from northstar_api.services.object_store import ObjectStoreUnavailable, object_store
from northstar_api.services.rate_limit import redis_services
from northstar_api.website import EditorPrincipal, PostInput, WebsiteInquiry, WebsitePost, website_no_store
from northstar_api.website_request_context import website_client_address

KINDS = (
    "page",
    "navigation",
    "form",
    "redirect",
    "campaign",
    "offer",
    "collection",
    "entry",
    "workflow",
    "experiment",
    "brand",
)


class WebsiteResource(Base):
    __tablename__ = "website_resources"
    __table_args__ = (UniqueConstraint("kind", "key", name="uq_website_resource_key"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    kind: Mapped[str] = mapped_column(String(30))
    key: Mapped[str] = mapped_column(String(120))
    document: Mapped[dict[str, Any]] = mapped_column(JSON)
    published_document: Mapped[dict[str, Any] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    editorial_timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")


class WebsiteOperation(Base):
    __tablename__ = "website_operations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    resource_id: Mapped[str] = mapped_column(String(100), index=True)
    resource_kind: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), default="")
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


class WebsiteLeadState(Base):
    __tablename__ = "website_lead_states"
    inquiry_id: Mapped[UUID] = mapped_column(
        ForeignKey("website_inquiries.id", ondelete="RESTRICT"), primary_key=True
    )
    document: Mapped[dict[str, Any]] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)


class WebsiteFormSubmission(Base):
    __tablename__ = "website_form_submissions"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    form_id: Mapped[UUID] = mapped_column(ForeignKey("website_resources.id", ondelete="RESTRICT"))
    form_version: Mapped[int] = mapped_column(Integer)
    answers: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class WebsiteMedia(Base):
    __tablename__ = "website_media"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    document: Mapped[dict[str, Any]] = mapped_column(JSON)
    storage: Mapped[dict[str, str]] = mapped_column(JSON)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


def audit(
    session: DBSession,
    resource_id: str,
    kind: str,
    action: str,
    version: int,
    actor_id: UUID | None,
    snapshot: dict[str, Any],
    reason: str = "",
) -> None:
    session.add(
        WebsiteOperation(
            resource_id=resource_id,
            resource_kind=kind,
            action=action,
            version=version,
            actor_id=actor_id,
            snapshot=snapshot,
            reason=reason,
        )
    )


def safe_route(value: str) -> str:
    if not re.fullmatch(r"/(?:[a-z0-9]+(?:-[a-z0-9]+)*/?)*", value) or value.startswith("//"):
        raise ValueError("Use a local route with lowercase letters, numbers and hyphens")
    if value.split("/")[1] in {"api", "admin", "assets", "fonts", "images"}:
        raise ValueError("This route is reserved")
    return value


class ResourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "page",
        "navigation",
        "form",
        "redirect",
        "campaign",
        "offer",
        "collection",
        "entry",
        "workflow",
        "experiment",
        "brand",
    ]
    key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    title: str = Field(min_length=3, max_length=180)
    data: dict[str, Any] = Field(default_factory=dict)
    version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def controlled_schema(self) -> ResourceInput:
        if len(json.dumps(self.data)) > 150_000:
            raise ValueError("Resource is too large")
        d = self.data
        if self.kind == "page":
            safe_route(str(d.get("route", "")))
            if d["route"] == "/blog" or d["route"].startswith("/blog/"):
                raise ValueError("Blog routes are owned by the article publishing workflow")
            blocks = d.get("blocks", [])
            if not isinstance(blocks, list) or not 1 <= len(blocks) <= 30:
                raise ValueError("Add between 1 and 30 approved sections")
            ids = set()
            for block in blocks:
                if not isinstance(block, dict) or block.get("type") not in {
                    "hero",
                    "text",
                    "cta",
                    "faq",
                    "form",
                    "image",
                }:
                    raise ValueError("Unknown section type")
                if not isinstance(block.get("id"), str) or block["id"] in ids:
                    raise ValueError("Sections require unique stable IDs")
                ids.add(block["id"])
                if block.get("href"):
                    safe_route(block["href"])
                for field in ("title", "body", "label", "form_key"):
                    if field in block and (not isinstance(block[field], str) or len(block[field]) > 20_000):
                        raise ValueError("Invalid section text")
                if block["type"] == "image":
                    try:
                        UUID(str(block.get("asset_id", "")))
                    except ValueError:
                        raise ValueError("Choose an uploaded media asset") from None
                    if not isinstance(block.get("alt"), str) or not 1 <= len(block["alt"]) <= 250:
                        raise ValueError("Image sections require alternative text")
        elif self.kind == "navigation":
            items = d.get("items", [])
            if not isinstance(items, list) or len(items) > 12:
                raise ValueError("Navigation supports at most 12 links")
            for item in items:
                if (
                    not isinstance(item, dict)
                    or not isinstance(item.get("label"), str)
                    or not 1 <= len(item["label"]) <= 60
                ):
                    raise ValueError("Each link needs a label")
                safe_route(str(item.get("href", "")))
        elif self.kind == "redirect":
            safe_route(str(d.get("source", "")))
            safe_route(str(d.get("target", "")))
            if d["source"] == d["target"] or d["source"] in {
                "/",
                "/contact",
                "/blog",
                "/pricing",
                "/privacy",
                "/terms",
                "/security",
            }:
                raise ValueError("Redirect cannot loop or replace a built-in route")
            if d.get("status", 301) not in {301, 302, 308}:
                raise ValueError("Use 301, 302 or 308")
        elif self.kind == "campaign":
            safe_route(str(d.get("destination", "")))
            for key in ("source", "medium", "campaign"):
                if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", str(d.get(key, ""))):
                    raise ValueError("Campaign fields use approved non-personal lowercase labels")
            if d["medium"] not in {"cpc", "email", "social", "organic", "referral", "qr", "partner"}:
                raise ValueError("Choose an approved campaign medium")
        elif self.kind == "form":
            fields = d.get("fields", [])
            if not isinstance(fields, list) or not 1 <= len(fields) <= 12:
                raise ValueError("Forms need 1 to 12 fields")
            keys = set()
            for field in fields:
                if not isinstance(field, dict) or field.get("type") not in {
                    "text",
                    "email",
                    "textarea",
                    "select",
                    "checkbox",
                }:
                    raise ValueError("Unknown form field type")
                if (
                    not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", str(field.get("key", "")))
                    or field["key"] in keys
                ):
                    raise ValueError("Fields need unique stable keys")
                keys.add(field["key"])
                if not isinstance(field.get("label"), str) or not 1 <= len(field["label"]) <= 100:
                    raise ValueError("Fields need accessible labels")
                if field["type"] == "select" and (
                    not isinstance(field.get("options"), list)
                    or not 1 <= len(field["options"]) <= 20
                    or any(not isinstance(x, str) or len(x) > 100 for x in field["options"])
                ):
                    raise ValueError("Select fields need bounded options")
            if "name" not in keys or not any(f["key"] == "email" and f["type"] == "email" for f in fields):
                raise ValueError("Contact forms require name and email fields")
            if not any(f["key"] == "name" and f["type"] == "text" for f in fields):
                raise ValueError("The contact name must use a text field")
            for field in fields:
                if field["key"] in {"name", "email"}:
                    field["required"] = True
        elif self.kind == "workflow":
            if d.get("trigger") != "inquiry_accepted" or d.get("action") not in {"assign", "tag"}:
                raise ValueError(
                    "Local workflows support enquiry assignment or tagging; external delivery needs a configured connector"
                )
            if not isinstance(d.get("value"), str) or not 1 <= len(d["value"]) <= 100:
                raise ValueError("Provide an assignee or tag")
        elif self.kind == "experiment":
            safe_route(str(d.get("route", "")))
            if not isinstance(d.get("hypothesis"), str) or not d["hypothesis"].strip():
                raise ValueError("Define the hypothesis")
            if d.get("unit", "session") != "session":
                raise ValueError("The local profile uses consented session assignment")
            if (
                not isinstance(d.get("variants"), list)
                or len(d["variants"]) != 2
                or any(not isinstance(v, str) or not 3 <= len(v) <= 180 for v in d["variants"])
            ):
                raise ValueError("Provide two headline variants")
        elif self.kind == "collection":
            fields = d.get("fields", [])
            if not isinstance(fields, list) or not 1 <= len(fields) <= 20:
                raise ValueError("Collections need approved fields")
            for f in fields:
                if (
                    not isinstance(f, dict)
                    or f.get("type") not in {"text", "number", "boolean", "date"}
                    or not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", str(f.get("key", "")))
                ):
                    raise ValueError("Use controlled collection field types")
            collection_keys = [f["key"] for f in fields]
            if len(set(collection_keys)) != len(collection_keys):
                raise ValueError("Collection field keys must be unique")
        elif self.kind == "entry":
            if not isinstance(d.get("collection_key"), str) or not isinstance(d.get("fields"), dict):
                raise ValueError("Choose a collection and provide its fields")
        elif self.kind == "brand":
            if d.get("palette", "sage") not in {"sage", "blue", "violet"}:
                raise ValueError("Choose an accessible approved palette")
            if "company" in d and (not isinstance(d["company"], str) or not 1 <= len(d["company"]) <= 180):
                raise ValueError("Provide a bounded company name")
            if d.get("contact_email"):
                TypeAdapter(EmailStr).validate_python(d["contact_email"])
        return self


class ResourceAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    action: Literal["review", "approve", "publish", "schedule", "unpublish", "archive", "restore"]
    reason: str = Field(min_length=3, max_length=500)
    scheduled_at: datetime | None = None
    editorial_timezone: str = Field(default="Asia/Kolkata", max_length=64)

    @model_validator(mode="after")
    def schedule_contract(self) -> ResourceAction:
        if self.action == "schedule":
            if (
                not self.scheduled_at
                or self.scheduled_at.tzinfo is None
                or self.scheduled_at <= datetime.now(UTC)
            ):
                raise ValueError("Schedule a future instant with an explicit timezone")
            try:
                ZoneInfo(self.editorial_timezone)
            except ZoneInfoNotFoundError:
                raise ValueError("Choose a valid editorial timezone") from None
        return self


class LeadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=0)
    stage: Literal["new", "assigned", "contacted", "qualified", "won", "closed"]
    assignee: str = Field(default="", max_length=100)
    note: str = Field(default="", max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=12)
    reason: str = Field(min_length=3, max_length=500)


admin = APIRouter(
    prefix="/platform-admin/website", tags=["website operations"], dependencies=[Depends(website_no_store)]
)
public = APIRouter(prefix="/website", tags=["public website"], dependencies=[Depends(website_no_store)])


def project(row: WebsiteResource, published: bool = False) -> dict[str, Any]:
    document = row.published_document if published else row.document
    return {
        **(document or {}),
        "id": str(row.id),
        "kind": row.kind,
        "key": row.key,
        "status": "published" if published else row.status,
        "version": (document or {}).get("published_version", row.version) if published else row.version,
        "updated_at": (document or {}).get("published_updated_at", "")
        if published
        else row.updated_at.isoformat(),
        "scheduled_at": row.scheduled_at.isoformat() if row.scheduled_at and not published else None,
        "editorial_timezone": "UTC" if published else row.editorial_timezone,
    }


async def resources(session: DBSession, published: bool = False) -> list[WebsiteResource]:
    query = select(WebsiteResource).order_by(WebsiteResource.updated_at.desc()).limit(500)
    if published:
        query = query.where(
            WebsiteResource.published_document.is_not(None), WebsiteResource.status != "archived"
        )
    rows = list(await session.scalars(query))
    return [row for row in rows if row.published_document] if published else rows


async def validate_entry(session: DBSession, payload: ResourceInput, published: bool = False) -> None:
    if payload.kind != "entry":
        return
    collection = await session.scalar(
        select(WebsiteResource).where(
            WebsiteResource.kind == "collection",
            WebsiteResource.key == payload.data["collection_key"],
            WebsiteResource.status != "archived",
        )
    )
    document = (
        collection.published_document
        if collection and published
        else collection.document
        if collection
        else None
    )
    if not document:
        raise HTTPException(422, "Choose an available collection; publish it before publishing entries")
    fields = document["data"]["fields"]
    values = payload.data["fields"]
    if set(values) - {f["key"] for f in fields}:
        raise HTTPException(422, "Entry contains unknown collection fields")
    for field in fields:
        value = values.get(field["key"])
        if field.get("required") and (value is None or value == ""):
            raise HTTPException(422, f"{field.get('label', field['key'])} is required")
        if value is None or value == "":
            continue
        valid = {
            "text": isinstance(value, str) and len(value) <= 20_000,
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "date": isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None,
        }
        if not valid[field["type"]]:
            raise HTTPException(422, f"Invalid {field['key']} value")


async def accepted_inquiry(session: DBSession, inquiry_id: UUID) -> None:
    """Local approved workflow effects and audit commit with the accepted enquiry."""
    assignee = ""
    tags: list[str] = []
    for row in await resources(session, True):
        if row.kind != "workflow":
            continue
        data = (row.published_document or {})["data"]
        if data["action"] == "assign":
            assignee = data["value"]
        elif data["value"] not in tags and len(tags) < 12:
            tags.append(data["value"])
        audit(
            session,
            str(inquiry_id),
            "workflow",
            "executed",
            row.version,
            None,
            {"workflow_id": str(row.id), "action": data["action"]},
        )
    if assignee or tags:
        session.add(
            WebsiteLeadState(
                inquiry_id=inquiry_id,
                document={
                    "stage": "assigned" if assignee else "new",
                    "assignee": assignee,
                    "tags": tags,
                    "note": "",
                },
                version=1,
            )
        )
    audit(session, str(inquiry_id), "lead", "accepted", 1, None, {"accepted": True})


class FormSubmissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    answers: dict[str, str | bool]
    consent: bool
    website: str = Field(default="", max_length=200)


@public.post("/forms/{key}/submit", status_code=201)
async def submit_form(
    key: str, payload: FormSubmissionInput, session: DBSession, request: Request
) -> dict[str, Any]:
    address = website_client_address(request)
    limit = await redis_services.check_rate_limit(
        f"website:form:{hashlib.sha256(address.encode()).hexdigest()}", 10, scope="website"
    )
    if not limit.allowed:
        raise HTTPException(
            429, "Please wait before submitting another form", headers={"Retry-After": str(limit.retry_after)}
        )
    if not payload.consent or payload.website:
        raise HTTPException(422, "Response consent is required; check the form")
    row = await session.scalar(
        select(WebsiteResource).where(
            WebsiteResource.kind == "form",
            WebsiteResource.key == key,
            WebsiteResource.published_document.is_not(None),
            WebsiteResource.status != "archived",
        )
    )
    if row is None or not row.published_document:
        raise HTTPException(404, "Form is not available")
    fields = (row.published_document or {})["data"]["fields"]
    name = payload.answers.get("name", "")
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 120:
        raise HTTPException(422, "Provide a contact name of 2 to 120 characters")
    try:
        email = str(TypeAdapter(EmailStr).validate_python(payload.answers.get("email", "")))
    except ValueError:
        raise HTTPException(422, "Provide a valid contact email") from None
    if set(payload.answers) - {f["key"] for f in fields}:
        raise HTTPException(422, "Unknown form fields")
    for f in fields:
        value = payload.answers.get(f["key"], "")
        if f.get("required") and not value:
            raise HTTPException(422, f"{f['label']} is required")
        if len(str(value)) > 4000:
            raise HTTPException(422, "Answer is too long")
        if f["type"] == "checkbox" and not isinstance(value, bool):
            raise HTTPException(422, "Checkbox value is invalid")
        if f["type"] != "checkbox" and not isinstance(value, str):
            raise HTTPException(422, "Text value is invalid")
        if value and f["type"] == "email":
            try:
                TypeAdapter(EmailStr).validate_python(value)
            except ValueError:
                raise HTTPException(422, "Use a valid email address") from None
        if value and f["type"] == "select" and value not in f["options"]:
            raise HTTPException(422, "Choose an available option")
    existing = await session.get(WebsiteFormSubmission, payload.id)
    if existing:
        if existing.form_id != row.id or existing.answers != payload.answers:
            raise HTTPException(409, "Submission identifier already used")
        return {"id": str(payload.id), "accepted": True}
    # Durable submission, contact inbox and local workflow effects form one transaction.
    session.add(
        WebsiteFormSubmission(
            id=payload.id,
            form_id=row.id,
            form_version=(row.published_document or {})["published_version"],
            answers=payload.answers,
        )
    )
    session.add(
        WebsiteInquiry(
            id=payload.id,
            document={
                "name": name.strip(),
                "email": email,
                "company": str(payload.answers.get("company", "")),
                "message": str(payload.answers.get("message", "Custom form submission")),
                "kind": "contact",
                "consent": True,
                "form_key": key,
            },
        )
    )
    await accepted_inquiry(session, payload.id)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.get(WebsiteFormSubmission, payload.id)
        if existing is None or existing.form_id != row.id or existing.answers != payload.answers:
            raise HTTPException(409, "Submission identifier already used") from None
    return {"id": str(payload.id), "accepted": True}


class MediaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image: str = Field(max_length=2_900_000)
    title: str = Field(min_length=3, max_length=180)
    alt: str = Field(min_length=1, max_length=250)
    rights: str = Field(min_length=5, max_length=1000)
    ai_generated: bool = False
    provenance: str = Field(default="", max_length=1000)

    @field_validator("image")
    @classmethod
    def checked_image(cls, value: str) -> str:
        if not value.startswith("data:"):
            raise ValueError("Upload PNG, JPEG or WebP image bytes")
        return PostInput.validate_cover(value)


@admin.post("/media", status_code=201)
async def upload_media(payload: MediaInput, session: DBSession, principal: EditorPrincipal) -> dict[str, Any]:
    PostInput.validate_cover(payload.image)
    if not payload.image.startswith("data:"):
        raise HTTPException(422, "Upload image bytes")
    raw = base64.b64decode(payload.image.split(",", 1)[1])
    with Image.open(io.BytesIO(raw)) as source:
        image = source.convert("RGB")
        image.thumbnail((2400, 2400))
        output = io.BytesIO()
        image.save(output, format="WEBP", quality=85, exif=b"")
        width, height = image.size
        image.thumbnail((480, 480))
        thumb = io.BytesIO()
        image.save(thumb, format="WEBP", quality=80, exif=b"")
    asset_id = uuid4()
    try:
        key, thumb_key = await object_store.put_website_image(asset_id, output.getvalue(), thumb.getvalue())
    except ObjectStoreUnavailable:
        raise HTTPException(503, "Media storage is unavailable; no usable asset was created") from None
    document = payload.model_dump(exclude={"image"}) | {
        "checksum": hashlib.sha256(raw).hexdigest(),
        "width": width,
        "height": height,
        "status": "validated",
        "mime": "image/webp",
    }
    row = WebsiteMedia(
        id=asset_id,
        document=document,
        storage={"image": key, "thumbnail": thumb_key},
        actor_id=principal.user_id,
    )
    session.add(row)
    audit(
        session,
        str(asset_id),
        "media",
        "upload",
        1,
        principal.user_id,
        {"checksum": document["checksum"], "rights_recorded": True, "ai_generated": payload.ai_generated},
    )
    await session.commit()
    return {**document, "id": str(asset_id), "url": f"/api/v1/website/media/{asset_id}"}


@admin.get("/media")
async def media_list(session: DBSession, principal: EditorPrincipal) -> list[dict[str, Any]]:
    rows = await session.scalars(select(WebsiteMedia).order_by(WebsiteMedia.created_at.desc()).limit(200))
    return [{**r.document, "id": str(r.id), "url": f"/api/v1/website/media/{r.id}"} for r in rows]


@admin.get("/media/{asset_id}/preview")
async def preview_media(asset_id: UUID, session: DBSession, principal: EditorPrincipal) -> Response:
    row = await session.get(WebsiteMedia, asset_id)
    if not row:
        raise HTTPException(404, "Asset not found")
    try:
        body, _ = await object_store.download(row.storage["thumbnail"], limit_bytes=2_000_000)
    except ObjectStoreUnavailable:
        raise HTTPException(503, "Media storage unavailable") from None
    return Response(
        body,
        media_type="image/webp",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@public.get("/media/{asset_id}")
async def public_media(asset_id: UUID, session: DBSession) -> Response:
    row = await session.get(WebsiteMedia, asset_id)
    path = f"/api/v1/website/media/{asset_id}"
    post_reference = await session.scalar(
        select(WebsitePost.id)
        .where(WebsitePost.status == "published", WebsitePost.published_document["cover"].as_string() == path)
        .limit(1)
    )
    used = bool(post_reference)
    if not used:
        used = any(
            r.kind == "page"
            and any(
                b.get("type") == "image" and b.get("asset_id") == str(asset_id)
                for b in (r.published_document or {})["data"]["blocks"]
            )
            for r in await resources(session, True)
        )
    if not row or not used:
        raise HTTPException(404, "Published asset not found")
    try:
        body, _ = await object_store.download(row.storage["image"], limit_bytes=3_000_000)
    except ObjectStoreUnavailable:
        raise HTTPException(503, "Media storage unavailable") from None
    return Response(
        body,
        media_type="image/webp",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@admin.get("/form-submissions")
async def submissions(session: DBSession, principal: EditorPrincipal) -> list[dict[str, Any]]:
    rows = await session.scalars(
        select(WebsiteFormSubmission).order_by(WebsiteFormSubmission.created_at.desc()).limit(500)
    )
    return [
        {
            "id": str(r.id),
            "form_id": str(r.form_id),
            "form_version": r.form_version,
            "answers": r.answers,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@public.get("/manifest")
async def manifest(session: DBSession, response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    rows = await resources(session, True)
    # Workflows, offers, experiments and private collection definitions are not exposed.
    live_collections = {r.key for r in rows if r.kind == "collection"}
    return {
        "resources": [
            project(r, True)
            for r in rows
            if r.kind in {"page", "navigation", "form", "redirect", "brand", "collection", "entry"}
            and (
                r.kind != "entry"
                or (r.published_document or {})["data"]["collection_key"] in live_collections
            )
        ]
    }


@admin.get("/resources")
async def list_resources(session: DBSession, principal: EditorPrincipal) -> list[dict[str, Any]]:
    return [project(r) for r in await resources(session)]


@admin.post("/resources", status_code=201)
async def create_resource(
    payload: ResourceInput, session: DBSession, principal: EditorPrincipal
) -> dict[str, Any]:
    await validate_entry(session, payload)
    row = WebsiteResource(
        id=uuid4(),
        kind=payload.kind,
        key=payload.key,
        document=payload.model_dump(exclude={"version", "kind", "key"}),
        version=1,
    )
    session.add(row)
    audit(session, str(row.id), row.kind, "create", 1, principal.user_id, row.document)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "This resource key already exists") from None
    return project(row)


async def locked(session: DBSession, resource_id: UUID, version: int) -> WebsiteResource:
    row = await session.scalar(
        select(WebsiteResource)
        .where(WebsiteResource.id == resource_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise HTTPException(404, "Resource not found")
    if row.version != version:
        raise HTTPException(409, "Another editor changed this resource. Reload or duplicate your draft.")
    return row


@admin.put("/resources/{resource_id}")
async def update_resource(
    resource_id: UUID, payload: ResourceInput, session: DBSession, principal: EditorPrincipal
) -> dict[str, Any]:
    if payload.version is None:
        raise HTTPException(422, "Expected version is required")
    row = await locked(session, resource_id, payload.version)
    if row.key != payload.key or row.kind != payload.kind:
        raise HTTPException(422, "Resource kind and key are immutable")
    if row.status == "archived":
        raise HTTPException(409, "Restore this resource before editing")
    await validate_entry(session, payload)
    if row.kind == "collection":
        previous = {f["key"]: f for f in row.document["data"]["fields"]}
        changed = {f["key"]: f for f in payload.data["fields"]}
        if any(
            key not in changed
            or changed[key]["type"] != f["type"]
            or (not f.get("required") and changed[key].get("required"))
            for key, f in previous.items()
        ):
            raise HTTPException(
                409, "Breaking schema changes require a reviewed migration; existing entry data is preserved"
            )
    row.document = payload.model_dump(exclude={"version", "kind", "key"})
    row.status = "draft"
    row.scheduled_at = None
    row.scheduled_actor_id = None
    row.version += 1
    row.updated_at = datetime.now(UTC)
    audit(session, str(row.id), row.kind, "save", row.version, principal.user_id, row.document)
    await session.commit()
    return project(row)


@admin.post("/resources/{resource_id}/actions")
async def resource_action(
    resource_id: UUID, payload: ResourceAction, session: DBSession, principal: EditorPrincipal
) -> dict[str, Any]:
    # Serialize site publication checks across replicas, including route collision checks.
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(74193081)"))
    row = await locked(session, resource_id, payload.version)
    transitions = {
        "review": {"draft"},
        "approve": {"in_review"},
        "publish": {"approved", "scheduled"},
        "schedule": {"approved"},
        "unpublish": {"draft", "in_review", "approved", "scheduled", "published"},
        "archive": {"draft", "in_review", "approved", "scheduled", "published"},
        "restore": {"archived"},
    }
    if row.status not in transitions[payload.action]:
        raise HTTPException(409, "This action is not available in the current state")
    if payload.action in {"publish", "schedule"}:
        others = [r for r in await resources(session, True) if r.id != row.id]
        data = row.document["data"]
        if row.kind in {"navigation", "brand"} and any(r.kind == row.kind for r in others):
            raise HTTPException(409, "Unpublish the existing site-wide resource before replacing it")
        if row.kind == "entry":
            await validate_entry(
                session,
                ResourceInput(kind="entry", key=row.key, title=row.document["title"], data=data),
                True,
            )
        if row.kind == "page":
            if any(
                r.kind == "page" and (r.published_document or {})["data"]["route"] == data["route"]
                for r in others
            ):
                raise HTTPException(409, "Another live page uses this route")
            forms = {r.key for r in others if r.kind == "form"}
            if any(b["type"] == "form" and b.get("form_key") not in forms for b in data["blocks"]):
                raise HTTPException(422, "Publish every referenced form first")
            for block in data["blocks"]:
                if block["type"] == "image" and not await session.get(WebsiteMedia, UUID(block["asset_id"])):
                    raise HTTPException(422, "Referenced media is not available")
        if row.kind == "redirect":
            if any(
                r.kind == "redirect" and (r.published_document or {})["data"]["source"] == data["source"]
                for r in others
            ):
                raise HTTPException(409, "Another redirect owns this source route")
            if any(
                r.kind == "page" and (r.published_document or {})["data"]["route"] == data["source"]
                for r in others
            ):
                raise HTTPException(409, "Unpublish the page at this route before redirecting it")
            redirects = {
                (r.published_document or {})["data"]["source"]: (r.published_document or {})["data"]["target"]
                for r in others
                if r.kind == "redirect"
            }
            redirects[data["source"]] = data["target"]
            for source in redirects:
                seen = set()
                current = source
                while current in redirects:
                    if current in seen:
                        raise HTTPException(422, "Redirect cycle detected")
                    seen.add(current)
                    current = redirects[current]
        if row.kind == "experiment":
            raise HTTPException(
                422,
                "Live experiments require measurement approval and A/A qualification; definitions can be reviewed and approved without public activation",
            )
        if row.kind in {"page", "navigation", "redirect", "campaign"}:
            await validate_destinations(session, row, others)
        if payload.action == "schedule":
            row.scheduled_at = payload.scheduled_at
            row.scheduled_actor_id = principal.user_id
            row.editorial_timezone = payload.editorial_timezone
            row.status = "scheduled"
        else:
            row.published_document = {
                **row.document,
                "published_version": row.version + 1,
                "published_updated_at": datetime.now(UTC).isoformat(),
            }
            row.status = "published"
    else:
        row.status = {
            "review": "in_review",
            "approve": "approved",
            "unpublish": "draft",
            "archive": "archived",
            "restore": "draft",
        }[payload.action]
        if payload.action in {"unpublish", "archive", "restore"}:
            row.published_document = None
    if payload.action != "schedule":
        row.scheduled_at = None
        row.scheduled_actor_id = None
    row.version += 1
    row.updated_at = datetime.now(UTC)
    audit(
        session,
        str(row.id),
        row.kind,
        payload.action,
        row.version,
        principal.user_id,
        row.document,
        payload.reason,
    )
    await session.commit()
    return project(row)


async def live_routes(session: DBSession, rows: list[WebsiteResource]) -> set[str]:
    routes = {"/", "/blog", "/contact", "/pricing", "/privacy", "/terms", "/security"}
    routes.update(
        f"/blog/{slug}"
        for slug in await session.scalars(select(WebsitePost.slug).where(WebsitePost.status == "published"))
    )
    routes.update(
        (r.published_document or {})["data"]["route"]
        for r in rows
        if r.kind == "page" and r.published_document
    )
    collections = {r.key for r in rows if r.kind == "collection" and r.published_document}
    routes.update(f"/collections/{key}" for key in collections)
    routes.update(
        f"/collections/{(r.published_document or {})['data']['collection_key']}/{r.key}"
        for r in rows
        if r.kind == "entry"
        and r.published_document
        and (r.published_document or {})["data"]["collection_key"] in collections
    )
    return routes


async def validate_destinations(
    session: DBSession, row: WebsiteResource, others: list[WebsiteResource], live: bool = False
) -> None:
    routes = await live_routes(session, others)
    document = row.published_document if live else row.document
    data = (document or {})["data"]
    redirects = {
        (r.published_document or {})["data"]["source"]: (r.published_document or {})["data"]["target"]
        for r in others
        if r.kind == "redirect" and r.published_document
    }
    if row.kind == "page":
        routes.add(data["route"])
        if data["route"] in redirects:
            raise HTTPException(409, "Remove the live redirect at this route before publishing a page")
        links = [b["href"] for b in data["blocks"] if b.get("href")]
    elif row.kind == "navigation":
        links = [item["href"] for item in data["items"]]
    elif row.kind == "redirect":
        links = [data["target"]]
        redirects[data["source"]] = data["target"]
    elif row.kind == "campaign":
        links = [data["destination"]]
    else:
        return
    for destination in links:
        seen: set[str] = set()
        while destination in redirects:
            if destination in seen:
                raise HTTPException(422, "Redirect cycle detected")
            seen.add(destination)
            destination = redirects[destination]
        if destination not in routes:
            raise HTTPException(422, f"Publish the destination first: {destination}")


@admin.get("/quality")
async def quality_report(session: DBSession, principal: EditorPrincipal) -> dict[str, Any]:
    rows = await resources(session, True)
    issues = []
    for row in rows:
        document = row.published_document or {}
        try:
            await validate_destinations(
                session, row, [other for other in rows if other.id != row.id], live=True
            )
        except HTTPException as error:
            issues.append(
                {
                    "resource_id": str(row.id),
                    "title": document["title"],
                    "code": "broken_destination",
                    "message": error.detail,
                }
            )
        if row.kind == "page" and not document["data"].get("description"):
            issues.append(
                {
                    "resource_id": str(row.id),
                    "title": document["title"],
                    "code": "missing_description",
                    "message": "Add a search description",
                }
            )
        review_date = document["data"].get("review_date")
        if (
            isinstance(review_date, str)
            and review_date
            and review_date < datetime.now(UTC).date().isoformat()
        ):
            issues.append(
                {
                    "resource_id": str(row.id),
                    "title": document["title"],
                    "code": "review_due",
                    "message": "The declared content review date has passed",
                }
            )
    # A read-only diagnostic must never save temporary publication projections.
    await session.rollback()
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "published_resources_checked": len(rows),
        "issues": issues,
        "scope": "Internal destinations, search descriptions and declared review dates; not a production security or accessibility audit",
    }


@admin.get("/audit")
async def audit_list(
    session: DBSession,
    principal: EditorPrincipal,
    kind: str = "",
    action: str = "",
    resource_id: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    query = select(WebsiteOperation)
    for field, value in (
        (WebsiteOperation.resource_kind, kind),
        (WebsiteOperation.action, action),
        (WebsiteOperation.resource_id, resource_id),
    ):
        if value:
            query = query.where(field == value)
    rows = await session.scalars(
        query.order_by(WebsiteOperation.occurred_at.desc()).offset(offset).limit(limit)
    )
    return {
        "items": [
            {
                "id": str(r.id),
                "resource_id": r.resource_id,
                "kind": r.resource_kind,
                "action": r.action,
                "version": r.version,
                "actor_id": str(r.actor_id) if r.actor_id else "system",
                "reason": r.reason,
                "occurred_at": r.occurred_at.isoformat(),
                "changed_fields": list(r.snapshot),
            }
            for r in rows
        ],
        "offset": offset,
        "limit": limit,
    }


@admin.get("/resources/{resource_id}/history")
async def history(resource_id: UUID, session: DBSession, principal: EditorPrincipal) -> list[dict[str, Any]]:
    rows = await session.scalars(
        select(WebsiteOperation)
        .where(WebsiteOperation.resource_id == str(resource_id))
        .order_by(WebsiteOperation.occurred_at.desc())
        .limit(100)
    )
    return [
        {
            "id": str(r.id),
            "version": r.version,
            "action": r.action,
            "reason": r.reason,
            "snapshot": r.snapshot,
            "occurred_at": r.occurred_at.isoformat(),
        }
        for r in rows
    ]


@admin.get("/leads")
async def leads(session: DBSession, principal: EditorPrincipal) -> list[dict[str, Any]]:
    rows = await session.execute(
        select(WebsiteInquiry, WebsiteLeadState)
        .outerjoin(WebsiteLeadState, WebsiteLeadState.inquiry_id == WebsiteInquiry.id)
        .order_by(WebsiteInquiry.created_at.desc())
        .limit(500)
    )
    return [
        {
            **inquiry.document,
            "id": str(inquiry.id),
            "created_at": inquiry.created_at.isoformat(),
            "operations": state.document
            if state
            else {"stage": "new", "assignee": "", "note": "", "tags": []},
            "version": state.version if state else 0,
        }
        for inquiry, state in rows
    ]


@admin.put("/leads/{inquiry_id}")
async def update_lead(
    inquiry_id: UUID, payload: LeadInput, session: DBSession, principal: EditorPrincipal
) -> dict[str, Any]:
    inquiry = await session.scalar(
        select(WebsiteInquiry).where(WebsiteInquiry.id == inquiry_id).with_for_update()
    )
    if inquiry is None:
        raise HTTPException(404, "Enquiry not found")
    state = await session.get(WebsiteLeadState, inquiry_id)
    if payload.version != (state.version if state else 0):
        raise HTTPException(409, "Lead changed; reload before saving")
    document = payload.model_dump(exclude={"version", "reason"})
    if state:
        state.document = document
        state.version += 1
    else:
        state = WebsiteLeadState(inquiry_id=inquiry_id, document=document, version=1)
        session.add(state)
    # Audit keys and stage only; never duplicate contact answers or private notes.
    audit(
        session,
        str(inquiry_id),
        "lead",
        "update",
        state.version,
        principal.user_id,
        {"stage": payload.stage, "fields": ["stage", "assignee", "note", "tags"]},
        payload.reason,
    )
    await session.commit()
    return {"id": str(inquiry_id), "version": state.version, "operations": state.document}


@admin.get("/overview")
async def overview(session: DBSession, principal: EditorPrincipal) -> dict[str, Any]:
    return {
        "articles": await session.scalar(select(func.count()).select_from(WebsitePost)),
        "published_articles": await session.scalar(
            select(func.count()).select_from(WebsitePost).where(WebsitePost.status == "published")
        ),
        "enquiries": await session.scalar(select(func.count()).select_from(WebsiteInquiry)),
        "resources": await session.scalar(select(func.count()).select_from(WebsiteResource)),
        "audit_records": await session.scalar(select(func.count()).select_from(WebsiteOperation)),
        "domain": "talktobot.com",
        "external_delivery": "not_configured",
    }


class ImportInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resources: list[ResourceInput] = Field(min_length=1, max_length=200)
    action: Literal["dry-run", "apply"] = "dry-run"
    reason: str = Field(default="", max_length=500)
    checksum: str = Field(default="", max_length=64)


@admin.post("/imports")
async def import_resources(
    payload: ImportInput, session: DBSession, principal: EditorPrincipal
) -> dict[str, Any]:
    documents = [row.model_dump(exclude={"version"}) for row in payload.resources]
    checksum = hashlib.sha256(
        json.dumps(documents, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    keys = [(row.kind, row.key) for row in payload.resources]
    diagnostics: list[str] = []
    if len(set(keys)) != len(keys):
        diagnostics.append("Duplicate resource keys in this file")
    existing = set(await session.execute(select(WebsiteResource.kind, WebsiteResource.key)))
    for kind, key in keys:
        if (kind, key) in existing:
            diagnostics.append(f"{kind}/{key} already exists; imports never overwrite existing content")
    result: dict[str, Any] = {
        "checksum": checksum,
        "count": len(keys),
        "diagnostics": diagnostics,
        "can_apply": not diagnostics,
        "created": [],
    }
    if payload.action == "dry-run":
        return result
    if len(payload.reason.strip()) < 3 or payload.checksum != checksum:
        raise HTTPException(422, "Run validation first and provide its checksum and an import reason")
    if diagnostics:
        raise HTTPException(409, diagnostics)
    try:
        for item in payload.resources:
            row = WebsiteResource(
                kind=item.kind,
                key=item.key,
                document={"title": item.title, "data": item.data},
                status="draft",
                version=1,
            )
            session.add(row)
            await session.flush()
            audit(
                session,
                str(row.id),
                row.kind,
                "import_draft",
                1,
                principal.user_id,
                row.document,
                payload.reason,
            )
            result["created"].append(str(row.id))
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "Resource keys changed since validation; validate this file again") from None
    return result


@admin.get("/exports")
async def export_content(
    session: DBSession, principal: EditorPrincipal, include_contacts: bool = False
) -> dict[str, Any]:
    from northstar_api.website import WebsiteRevision

    tables = {
        "resources": WebsiteResource,
        "posts": WebsitePost,
        "post_revisions": WebsiteRevision,
        "operations": WebsiteOperation,
        "media": WebsiteMedia,
    }
    if include_contacts:
        tables.update(
            {
                "inquiries": WebsiteInquiry,
                "lead_states": WebsiteLeadState,
                "form_submissions": WebsiteFormSubmission,
            }
        )
    content: dict[str, list[dict[str, Any]]] = {}
    for name, model in tables.items():
        count = await session.scalar(select(func.count()).select_from(model))
        if count and count > 10_000:
            raise HTTPException(413, "Use a database backup for datasets larger than 10,000 rows per table")
        rows = await session.scalars(select(model))
        content[name] = [
            {column.name: getattr(row, column.name) for column in model.__table__.columns} for row in rows
        ]
    # Serialization has no secrets, session tokens, passwords or infrastructure credentials.
    serializable = json.loads(json.dumps(content, default=str))
    checksum = hashlib.sha256(
        json.dumps(serializable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    audit(
        session,
        "website-export",
        "export",
        "export",
        1,
        principal.user_id,
        {"checksum": checksum, "includes_contacts": include_contacts},
        "Owner-requested content export",
    )
    await session.commit()
    return {
        "format": "talktobot.website.archive.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "domain": "talktobot.com",
        "sha256": checksum,
        "includes_contacts": include_contacts,
        "media_bytes_included": False,
        "content": serializable,
    }
