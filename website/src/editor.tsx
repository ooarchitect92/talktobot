import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  Download,
  Eye,
  FileText,
  History,
  Inbox,
  LogOut,
  Plus,
  Save,
  Send,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";
import { OwnerConsole } from "./console";
import { MediaPreview } from "./media";
import { AuthenticatorEnrollment, type Enrollment } from './enrollment';
import {
  api,
  APP_URL,
  editorToken,
  setEditorToken,
  resumeEditor,
  checkEditorAccess,
  editorRoles,
  type Inquiry,
  type Post,
} from "./api";
import { starterPosts } from "./content";
import { Logo, Markdown } from "./ui";

type Draft = Omit<
  Post,
  | "id"
  | "status"
  | "version"
  | "updated_at"
  | "published_at"
  | "workflow_status"
  | "scheduled_at"
  | "editorial_timezone"
> &
  Partial<
    Pick<
      Post,
      | "id"
      | "status"
      | "version"
      | "updated_at"
      | "published_at"
      | "workflow_status"
      | "scheduled_at"
      | "editorial_timezone"
    >
  >;
type Revision = {
  id: string;
  version: number;
  action: string;
  reason: string;
  actor_id: string;
  created_at: string;
  document: Draft;
};
const EMPTY: Draft = {
  slug: "",
  title: "",
  excerpt: "",
  body: "",
  author: "TalkToBot editorial",
  category: "Guides",
  tags: [],
  cover: "",
  cover_alt: "",
  seo_title: "",
  seo_description: "",
};
const DRAFT_KEY = "talktobot.website.unsaved-draft";
const slugify = (text: string) =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 120);
function exportJson(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
export function Editor() {
  const location = useLocation();
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(import.meta.env.PROD || !!editorToken());
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [posts, setPosts] = useState<Post[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [preview, setPreview] = useState(false);
  const [tab, setTab] = useState<"posts" | "trash" | "inquiries">("posts");
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [history, setHistory] = useState<Revision[] | null>(null);
  const [reason, setReason] = useState("");
  const [trashTarget, setTrashTarget] = useState<Post | null>(null);
  const [recover, setRecover] = useState<Draft | null>(null);
  const [dirty, setDirty] = useState(false);
  const [mfaChallenge, setMfaChallenge] = useState("");
  const [editorialReason, setEditorialReason] = useState("");
  const [publishTime, setPublishTime] = useState("");
  useEffect(() => {
    const expire = () => {
      setAuthenticated(false);
      setDraft(null);
      setPosts([]);
      setInquiries([]);
      setHistory(null);
      setRecover(null);
      sessionStorage.removeItem(DRAFT_KEY);
      sessionStorage.removeItem("talktobot.website.owner-draft");
    };
    let rechecking = false;
    const recheck = () => {
      if (
        !editorToken() ||
        document.visibilityState !== "visible" ||
        rechecking
      )
        return;
      rechecking = true;
      document.body.dataset.websiteChecking = "true";
      checkEditorAccess()
        .then(async () => { await refresh(); })
        .catch(expire)
        .finally(() => {
          rechecking = false;
          delete document.body.dataset.websiteChecking;
        });
    };
    window.addEventListener("website-auth-expired", expire);
    window.addEventListener("pageshow", recheck);
    document.addEventListener("visibilitychange", recheck);
    return () => {
      delete document.body.dataset.websiteChecking;
      window.removeEventListener("website-auth-expired", expire);
      window.removeEventListener("pageshow", recheck);
      document.removeEventListener("visibilitychange", recheck);
    };
  }, []);
  async function refresh() {
    const nextRoles = editorRoles();
    setRoles(nextRoles);
    if (!nextRoles.includes('lead_operator')) setInquiries([]);
    if (!nextRoles.some(role => ['editor', 'publisher'].includes(role))) {
      setPosts([]); setDraft(null); setHistory(null); setRecover(null);
      sessionStorage.removeItem(DRAFT_KEY);
      return;
    }
    const values = await api<Post[]>("/platform-admin/website/posts", {}, true);
    setPosts(values);
  }
  useEffect(() => {
    document.title = "Website editor | TalkToBot";
    void (async () => {
      if (!editorToken() && !(import.meta.env.PROD && await resumeEditor())) return;
      await checkEditorAccess();
      setAuthenticated(true);
      await refresh();
    })()
      .catch((e) => {
        setError(e.message);
        setEditorToken(null);
      })
      .finally(() => setChecking(false));
  }, []);
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(DRAFT_KEY);
      if (saved) {
        const envelope = JSON.parse(saved);
        if (envelope.expires > Date.now() && envelope.draft)
          setRecover(envelope.draft);
        else sessionStorage.removeItem(DRAFT_KEY);
      }
    } catch {
      /* Invalid draft is ignored. */
    }
  }, []);
  useEffect(() => {
    if (!draft || !dirty) return;
    try {
      sessionStorage.setItem(
        DRAFT_KEY,
        JSON.stringify({ draft, expires: Date.now() + 86400000 }),
      );
    } catch {
      setNotice(
        "Browser recovery storage is unavailable. Save to the server to protect your changes.",
      );
    }
  }, [draft, dirty]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  useEffect(() => {
    if (!trashTarget) return;
    const previous = document.activeElement as HTMLElement | null;
    const modal = document.querySelector(".confirm-modal");
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") setTrashTarget(null);
      if (event.key !== "Tab" || !modal) return;
      const nodes = Array.from(
        modal.querySelectorAll<HTMLElement>(
          "button:not(:disabled), textarea, input, a[href]",
        ),
      );
      const first = nodes[0],
        last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    window.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [trashTarget]);
  async function logout() {
    if (
      dirty &&
      !window.confirm("Sign out and remove the unsaved recovery draft?")
    )
      return;
    setBusy(true);
    try {
      await api("/auth/logout", { method: "POST" }, true);
    } catch {
      /* Clear local private state even if the server is temporarily unavailable. */
    } finally {
      setEditorToken(null);
      sessionStorage.removeItem(DRAFT_KEY);
      sessionStorage.removeItem("talktobot.website.owner-draft");
      setRecover(null);
      setDraft(null);
      setDirty(false);
      setAuthenticated(false);
      setBusy(false);
    }
  }
  function edit(value: Draft | null) {
    if (
      dirty &&
      !window.confirm(
        "Leave unsaved changes? A recovery copy remains in this tab.",
      )
    )
      return;
    setDraft(value);
    setDirty(false);
    setPreview(false);
    setHistory(null);
    setError("");
    setNotice("");
  }
  function field<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
    setDirty(true);
    setNotice("Unsaved changes · recovery copy in this browser tab");
  }
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const response = await api<{
        accessToken?: string;
        challengeToken?: string;
        mfaEnrollmentRequired?: boolean;
        enrollmentToken?: string;
        expiresAt?: string;
      }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: data.get("email"),
          password: data.get("password"),
        }),
      });
      if (!response.accessToken) {
        if (response.mfaEnrollmentRequired && response.enrollmentToken && response.expiresAt) {
          setEnrollment({ enrollmentToken: response.enrollmentToken, expiresAt: response.expiresAt });
          return;
        }
        if (response.challengeToken) {
          setMfaChallenge(response.challengeToken);
          return;
        }
        throw new Error("Unable to complete sign in.");
      }
      setEditorToken(response.accessToken);
      await checkEditorAccess();
      setAuthenticated(true);
      await refresh();
    } catch (e) {
      setEditorToken(null);
      setError(e instanceof Error ? e.message : "Unable to sign in");
    } finally {
      setBusy(false);
    }
  }
  async function appSession() {
    setError("");
    try {
      if (!(await resumeEditor()))
        throw new Error(
          "No app session is available on this website origin. Sign in below, or host the app and website on the same origin to share a session.",
        );
      await checkEditorAccess();
      setAuthenticated(true);
      await refresh();
    } catch (e) {
      setEditorToken(null);
      setError(e instanceof Error ? e.message : "Unable to use session");
    }
  }
  async function save(): Promise<Post> {
    if (!draft) throw new Error("No article selected");
    const {
      id,
      status,
      updated_at,
      published_at,
      workflow_status,
      scheduled_at,
      editorial_timezone,
      ...payload
    } = draft;
    void status;
    void updated_at;
    void published_at;
    void workflow_status;
    void scheduled_at;
    void editorial_timezone;
    const saved = await api<Post>(
      id
        ? `/platform-admin/website/posts/${id}`
        : "/platform-admin/website/posts",
      { method: id ? "PUT" : "POST", body: JSON.stringify(payload) },
      true,
    );
    setDraft(saved);
    setDirty(false);
    sessionStorage.removeItem(DRAFT_KEY);
    setRecover(null);
    setNotice(
      saved.status === "published"
        ? "Draft saved. The live article stays unchanged until you publish this revision."
        : "Draft saved to the server.",
    );
    await refresh();
    return saved;
  }
  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to complete action");
      if (!editorToken()) setAuthenticated(false);
    } finally {
      setBusy(false);
    }
  }
  async function action(
    post: Post | Draft,
    name:
      | "review"
      | "approve"
      | "schedule"
      | "publish"
      | "unpublish"
      | "trash"
      | "restore",
    why = "",
  ) {
    let saved = post;
    if (name === "review" && (dirty || !post.id)) saved = await save();
    const updated = await api<Post>(
      `/platform-admin/website/posts/${saved.id}/actions`,
      {
        method: "POST",
        body: JSON.stringify({
          version: saved.version,
          action: name,
          reason: why,
          ...(name === "schedule"
            ? {
                scheduled_at: publishTime
                  ? new Date(publishTime).toISOString()
                  : null,
                editorial_timezone:
                  Intl.DateTimeFormat().resolvedOptions().timeZone,
              }
            : {}),
        }),
      },
      true,
    );
    if (draft?.id === updated.id || name === "publish" || name === "review") {
      setDraft(updated);
      setDirty(false);
    }
    setNotice(
      name === "review"
        ? "Draft submitted for editorial review."
        : name === "approve"
          ? "Draft approved. Publish it now or schedule publication."
          : name === "schedule"
            ? "Publication scheduled. The approved draft stays private until it runs."
            : name === "publish"
              ? "Published. The public article is now available."
              : name === "restore"
                ? "Restored to draft. Review it before publishing."
                : name === "trash"
                  ? "Moved to trash. Source and history are preserved."
                  : "Unpublished. The public article is no longer available.",
    );
    await refresh();
  }
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError("");
    try {
      if (file.size > 500_000)
        throw new Error("Article files must be below 500 KB.");
      if (/\.(md|txt)$/i.test(file.name)) {
        field("body", await file.text());
        if (!draft?.title)
          field("title", file.name.replace(/\.(md|txt)$/i, ""));
      } else if (/\.json$/i.test(file.name)) {
        const value = JSON.parse(await file.text());
        if (typeof value.title !== "string" || typeof value.body !== "string")
          throw new Error("JSON needs a title and body.");
        const imported: Draft = {
          ...EMPTY,
          title: value.title,
          body: value.body,
          slug: slugify(value.slug || value.title),
          excerpt: typeof value.excerpt === "string" ? value.excerpt : "",
          author:
            typeof value.author === "string" ? value.author : EMPTY.author,
          category:
            typeof value.category === "string" ? value.category : "Guides",
          tags: Array.isArray(value.tags)
            ? value.tags.filter((t: unknown) => typeof t === "string")
            : [],
          seo_title: typeof value.seo_title === "string" ? value.seo_title : "",
          seo_description:
            typeof value.seo_description === "string"
              ? value.seo_description
              : "",
          cover: typeof value.cover === "string" ? value.cover : "",
          cover_alt: typeof value.cover_alt === "string" ? value.cover_alt : "",
        };
        setDraft(imported);
        setDirty(true);
      } else throw new Error("Upload a Markdown, text, or JSON article.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to import");
    }
  }
  async function cover(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError("");
    if (
      !["image/png", "image/jpeg", "image/webp"].includes(file.type) ||
      file.size > 2_000_000
    ) {
      setError("Choose a PNG, JPEG, or WebP image below 2 MB.");
      return;
    }
    const data = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    field("cover", data);
  }
  async function revisions(post: Draft) {
    if (!post.id) return;
    setHistory(
      await api<Revision[]>(
        `/platform-admin/website/posts/${post.id}/revisions`,
        {},
        true,
      ),
    );
  }
  if (checking)
    return (
      <main className="editor-login">
        <p role="status">Checking your editor access…</p>
      </main>
    );
  if (!authenticated)
    return (
      <main className="editor-login">
        <Logo />
        <div className="editor-login-card">
          <span className="feature-index">OWNER CONTENT STUDIO</span>
          <h1>
            Your stories.
            <br />
            Your website.
          </h1>
          <p>
            Sign in with an authorized website editor account to upload, edit,
            and publish articles.
          </p>
          {enrollment ? <AuthenticatorEnrollment enrollment={enrollment} onCancel={() => setEnrollment(null)} onComplete={async (token) => {
            setEditorToken(token);
            await checkEditorAccess();
            setEnrollment(null); setAuthenticated(true); await refresh();
          }} /> : <form
            onSubmit={
              mfaChallenge
                ? (event) => {
                    event.preventDefault();
                    const data = new FormData(event.currentTarget);
                    void run(async () => {
                      const code = String(data.get("code") || "").trim();
                      const response = await api<{ accessToken: string }>(
                        "/auth/mfa/verify",
                        {
                          method: "POST",
                          body: JSON.stringify({
                            challengeToken: mfaChallenge,
                            ...(/^\d{6}$/.test(code)
                              ? { code }
                              : { recoveryCode: code }),
                          }),
                        },
                      );
                      setEditorToken(response.accessToken);
                      await checkEditorAccess();
                      setAuthenticated(true);
                      setMfaChallenge("");
                      await refresh();
                    });
                  }
                : login
            }
          >
            {mfaChallenge ? (
              <label>
                Authenticator or recovery code
                <input name="code" required autoComplete="one-time-code" />
              </label>
            ) : (
              <>
                <label>
                  Email
                  <input
                    type="email"
                    name="email"
                    required
                    autoComplete="username"
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    name="password"
                    required
                    autoComplete="current-password"
                  />
                </label>
              </>
            )}
            {error && (
              <p className="error-message" role="alert">
                {error}
              </p>
            )}
            <button className="button dark" disabled={busy}>
              {busy ? "Signing in…" : "Sign in to the editor"}
              <ArrowUpRight size={17} />
            </button>
          </form>}
          <button className="text-link" onClick={() => void appSession()}>
            Continue with app session <ArrowUpRight size={15} />
          </button>
          <a className="text-link" href={`${APP_URL}/login`}>
            App login <ArrowUpRight size={15} />
          </a>
        </div>
        <Link className="text-link" to="/">
          ← Back to website
        </Link>
      </main>
    );
  if (location.pathname.startsWith("/admin/console") || !roles.some(role => ['editor', 'publisher'].includes(role)))
    return <OwnerConsole key={roles.join(',')} roles={roles} onLogout={() => void logout()} />;
  return (
    <div className="editor">
      <header className="editor-header">
        <Logo />
        <span className="studio-label">CONTENT STUDIO</span>
        <div>
          <Link className="button light small" to="/admin/console">
            Owner console
          </Link>
          <Link className="button light small" to="/">
            View website <ArrowUpRight size={14} />
          </Link>
          <button
            className="icon-button"
            aria-label="Sign out of editor"
            onClick={() => void logout()}
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <div className="editor-shell">
        <aside className="editor-sidebar">
          <span className="subtle-label">YOUR WEBSITE</span>
          <button
            className={tab === "posts" ? "active" : ""}
            onClick={() => {
              edit(null);
              setTab("posts");
            }}
          >
            <FileText size={17} />
            Articles
            <span>{posts.filter((p) => p.status !== "trashed").length}</span>
          </button>
          <button
            className={tab === "trash" ? "active" : ""}
            onClick={() => {
              edit(null);
              setTab("trash");
            }}
          >
            <Trash2 size={17} />
            Trash
            <span>{posts.filter((p) => p.status === "trashed").length}</span>
          </button>
          <button
            className={tab === "inquiries" ? "active" : ""}
            disabled={!roles.includes('lead_operator')}
            onClick={() =>
              void run(async () => {
                edit(null);
                setTab("inquiries");
                setInquiries(
                  await api<Inquiry[]>(
                    "/platform-admin/website/inquiries",
                    {},
                    true,
                  ),
                );
              })
            }
          >
            <Inbox size={17} />
            Enquiries
          </button>
          <div className="editor-tip">
            <History size={20} />
            <strong>Your content stays yours.</strong>
            <p>
              Source and revisions never expire automatically. Trash is
              reversible. Published articles stay live while you edit a draft.
            </p>
          </div>
        </aside>
        <main className="editor-main">
          <div className="editor-page-heading">
            <div>
              <EyebrowLocal />
              <h1>
                {draft
                  ? "Write something useful."
                  : tab === "inquiries"
                    ? "Real conversations start here."
                    : tab === "trash"
                      ? "Preserved, not forgotten."
                      : "A home for your ideas."}
              </h1>
              <p>
                {draft
                  ? "Markdown content, your voice, and a considered publishing workflow."
                  : tab === "trash"
                    ? "Restore articles to draft whenever you need them."
                    : tab === "inquiries"
                      ? "Accepted requests saved by the website enquiry form."
                      : "Create, upload, and publish stories your customers can use."}
              </p>
            </div>
            {!draft && tab === "posts" && (
              <button
                className="button dark"
                onClick={() => edit({ ...EMPTY })}
              >
                <Plus size={17} />
                New article
              </button>
            )}
          </div>
          {error && (
            <div className="error-message" role="alert">
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={15} />
              </button>
            </div>
          )}
          {notice && (
            <div className="notice-message" role="status">
              {notice}
            </div>
          )}
          {recover && !draft && (
            <div className="recovery-banner">
              <span>
                <History size={18} /> Unsaved article recovered from this
                browser tab.
              </span>
              <button
                onClick={() => {
                  setDraft(recover);
                  setDirty(true);
                }}
              >
                Recover draft
              </button>
              <button
                onClick={() => {
                  setRecover(null);
                  sessionStorage.removeItem(DRAFT_KEY);
                }}
              >
                Discard
              </button>
            </div>
          )}
          {draft ? (
            <>
              <div className="editor-toolbar">
                <button className="text-link" onClick={() => edit(null)}>
                  <ArrowLeft size={15} />
                  All articles
                </button>
                <div>
                  <label className="button light small file-label">
                    <Upload size={15} />
                    Upload article
                    <input
                      type="file"
                      accept=".md,.txt,.json"
                      onChange={(e) => void upload(e)}
                    />
                  </label>
                  <button
                    className="button light small"
                    onClick={() => setPreview(!preview)}
                  >
                    <Eye size={15} />
                    {preview ? "Edit" : "Preview"}
                  </button>
                  <button
                    className="button light small"
                    disabled={busy}
                    onClick={() => void run(save)}
                  >
                    <Save size={15} />
                    Save draft
                  </button>
                  <button
                    className="button dark small"
                    disabled={
                      busy || dirty || draft.workflow_status !== "approved"
                    }
                    onClick={() =>
                      void run(() =>
                        action(
                          draft,
                          "publish",
                          editorialReason || "Publish approved article",
                        ),
                      )
                    }
                  >
                    <Send size={14} />
                    {busy ? "Working…" : "Publish"}
                  </button>
                </div>
              </div>
              <div className="editorial-controls">
                <p>
                  Working revision:{" "}
                  {dirty ? "unsaved changes" : draft.workflow_status || "draft"}
                  . Live content changes only after approval and publication.
                </p>
                <label>
                  Editorial action reason
                  <input
                    value={editorialReason}
                    maxLength={500}
                    onChange={(e) => setEditorialReason(e.target.value)}
                  />
                </label>
                <div className="actions">
                  <button
                    className="button light small"
                    disabled={
                      busy ||
                      editorialReason.trim().length < 3 ||
                      (!dirty &&
                        !!draft.workflow_status &&
                        draft.workflow_status !== "draft")
                    }
                    onClick={() =>
                      void run(() => action(draft, "review", editorialReason))
                    }
                  >
                    Submit for review
                  </button>
                  <button
                    className="button light small"
                    disabled={
                      busy ||
                      dirty ||
                      editorialReason.trim().length < 3 ||
                      draft.workflow_status !== "in_review"
                    }
                    onClick={() =>
                      void run(() => action(draft, "approve", editorialReason))
                    }
                  >
                    Approve draft
                  </button>
                </div>
                <label>
                  Publish at ({Intl.DateTimeFormat().resolvedOptions().timeZone}
                  )
                  <input
                    type="datetime-local"
                    value={publishTime}
                    onChange={(e) => setPublishTime(e.target.value)}
                  />
                </label>
                <button
                  className="button light small"
                  disabled={
                    busy ||
                    dirty ||
                    !publishTime ||
                    editorialReason.trim().length < 3 ||
                    draft.workflow_status !== "approved"
                  }
                  onClick={() =>
                    void run(() => action(draft, "schedule", editorialReason))
                  }
                >
                  Schedule publication
                </button>
                {draft.scheduled_at && (
                  <p>
                    Scheduled for{" "}
                    {new Date(draft.scheduled_at).toLocaleString()}. Saving
                    changes cancels this schedule.
                  </p>
                )}
              </div>
              {preview ? (
                <div className="editor-preview">
                  <span className="badge">
                    Private editor preview · not published
                  </span>
                  <h1>{draft.title || "Untitled article"}</h1>
                  <p className="article-excerpt">{draft.excerpt}</p>
                  {draft.cover &&
                    (draft.cover.startsWith("/api/v1/website/media/") ? (
                      <MediaPreview
                        id={draft.cover.split("/").pop()!}
                        alt={draft.cover_alt}
                      />
                    ) : (
                      <img src={draft.cover} alt={draft.cover_alt} />
                    ))}
                  <Markdown text={draft.body} />
                </div>
              ) : (
                <div className="editor-form-grid">
                  <div className="editor-form">
                    <label>
                      Article title
                      <input
                        value={draft.title}
                        maxLength={180}
                        onChange={(e) => {
                          field("title", e.target.value);
                          if (!draft.id) field("slug", slugify(e.target.value));
                        }}
                        placeholder="An idea worth sharing"
                      />
                    </label>
                    <label>
                      URL slug
                      <input
                        value={draft.slug}
                        disabled={!!draft.id}
                        maxLength={120}
                        onChange={(e) => field("slug", slugify(e.target.value))}
                      />
                      <small>
                        /blog/{draft.slug || "your-article"} · URLs remain
                        stable after first save
                      </small>
                    </label>
                    <label>
                      Excerpt
                      <textarea
                        value={draft.excerpt}
                        maxLength={500}
                        rows={3}
                        onChange={(e) => field("excerpt", e.target.value)}
                        placeholder="A short introduction for the article card."
                      />
                    </label>
                    <label>
                      Article body{" "}
                      <span className="field-helper">
                        Markdown: # heading, ## subheading, - list, &gt; quote
                      </span>
                      <textarea
                        className="body-editor"
                        value={draft.body}
                        maxLength={100000}
                        rows={22}
                        onChange={(e) => field("body", e.target.value)}
                        placeholder="# Begin your story…"
                      />
                    </label>
                    <p className="form-note">
                      Text is rendered safely. HTML and executable content are
                      never interpreted.
                    </p>
                  </div>
                  <div className="editor-details">
                    <div className="editor-detail-card">
                      <h3>Publication</h3>
                      <span className={`badge ${draft.status || "draft"}`}>
                        {draft.status || "Unsaved draft"}
                      </span>
                      <p>
                        {dirty
                          ? "Unsaved changes"
                          : draft.id
                            ? `Saved revision ${draft.version}`
                            : "Save your first draft to create a revision."}
                      </p>
                      <label>
                        Author
                        <input
                          value={draft.author}
                          maxLength={100}
                          onChange={(e) => field("author", e.target.value)}
                        />
                      </label>
                      <label>
                        Category
                        <input
                          value={draft.category}
                          maxLength={60}
                          onChange={(e) => field("category", e.target.value)}
                        />
                      </label>
                      <label>
                        Tags
                        <input
                          value={draft.tags.join(", ")}
                          onChange={(e) =>
                            field(
                              "tags",
                              e.target.value.split(",").map((t) => t.trim()),
                            )
                          }
                          placeholder="Knowledge, Getting started"
                        />
                      </label>
                    </div>
                    <div className="editor-detail-card">
                      <h3>Cover image</h3>
                      {draft.cover &&
                        (draft.cover.startsWith("/api/v1/website/media/") ? (
                          <MediaPreview
                            id={draft.cover.split("/").pop()!}
                            alt={draft.cover_alt}
                          />
                        ) : (
                          <img
                            className="cover-upload-preview"
                            src={draft.cover}
                            alt={draft.cover_alt}
                          />
                        ))}
                      <label className="upload-zone">
                        <Upload size={20} />
                        <strong>
                          {draft.cover ? "Replace cover" : "Upload a cover"}
                        </strong>
                        <small>PNG, JPEG, WebP · under 2 MB</small>
                        <input
                          type="file"
                          accept="image/png,image/jpeg,image/webp"
                          onChange={(e) => void cover(e)}
                        />
                      </label>
                      <label>
                        Alternative text
                        <input
                          value={draft.cover_alt}
                          maxLength={250}
                          onChange={(e) => field("cover_alt", e.target.value)}
                          placeholder="Describe what the image shows"
                        />
                      </label>
                      <label>
                        Media library cover URL
                        <input
                          placeholder="/api/v1/website/media/…"
                          value={
                            draft.cover.startsWith("/api/v1/website/media/")
                              ? draft.cover
                              : ""
                          }
                          onChange={(e) => field("cover", e.target.value)}
                        />
                        <small>
                          Upload an image in the owner console’s media library
                          and paste its public URL. It becomes public only when
                          this article is published.
                        </small>
                      </label>
                      {draft.cover && (
                        <button
                          className="text-link"
                          onClick={() => field("cover", "")}
                        >
                          Remove image
                        </button>
                      )}
                    </div>
                    <div className="editor-detail-card">
                      <h3>Search appearance</h3>
                      <label>
                        SEO title
                        <input
                          value={draft.seo_title}
                          maxLength={180}
                          onChange={(e) => field("seo_title", e.target.value)}
                          placeholder="Defaults to article title"
                        />
                      </label>
                      <label>
                        Meta description
                        <textarea
                          value={draft.seo_description}
                          maxLength={320}
                          rows={3}
                          onChange={(e) =>
                            field("seo_description", e.target.value)
                          }
                          placeholder="Defaults to excerpt"
                        />
                      </label>
                    </div>
                    <div className="editor-detail-card">
                      <h3>History & portability</h3>
                      <button
                        className="text-link"
                        onClick={() =>
                          exportJson(draft, `${draft.slug || "article"}.json`)
                        }
                      >
                        <Download size={15} />
                        Export article
                      </button>
                      {draft.id && (
                        <button
                          className="text-link"
                          onClick={() => void run(() => revisions(draft))}
                        >
                          <History size={15} />
                          View revision history
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
              {history && (
                <div className="revision-history">
                  <h3>Preserved revision history</h3>
                  {history.map((r) => (
                    <div key={r.id}>
                      <span>
                        <strong>
                          Revision {r.version} · {r.action}
                        </strong>
                        <small>
                          {new Date(r.created_at).toLocaleString()} · Actor{" "}
                          {r.actor_id}
                          {r.reason && ` · ${r.reason}`}
                        </small>
                      </span>
                      <button
                        className="button light small"
                        onClick={() => {
                          setDraft({
                            ...draft,
                            ...r.document,
                            id: draft.id,
                            version: draft.version,
                            status: draft.status,
                          });
                          setDirty(true);
                          setNotice(
                            "Historical content loaded into an unsaved draft. Save and publish to make it live.",
                          );
                        }}
                      >
                        Use content
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : tab === "inquiries" ? (
            <div className="inquiry-list">
              {inquiries.length ? (
                inquiries.map((i) => (
                  <article key={i.id}>
                    <span className="badge">{i.kind}</span>
                    <h3>{i.name}</h3>
                    <a href={`mailto:${i.email}`}>{i.email}</a>
                    <small>
                      {i.company} · {new Date(i.created_at).toLocaleString()}
                    </small>
                    <p>{i.message}</p>
                    <span className="form-note">
                      Reference: {i.id} · Received, not a confirmed meeting
                    </span>
                  </article>
                ))
              ) : (
                <div className="empty-blog">
                  <Inbox size={30} />
                  <h3>No enquiries yet.</h3>
                  <p>Requests submitted on the website will appear here.</p>
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="article-table">
                <div className="article-table-header">
                  <span>ARTICLE</span>
                  <span>STATUS / UPDATED</span>
                  <span>ACTIONS</span>
                </div>
                {posts
                  .filter((p) =>
                    tab === "trash"
                      ? p.status === "trashed"
                      : p.status !== "trashed",
                  )
                  .map((p) => (
                    <div className="article-table-row" key={p.id}>
                      <div>
                        <button
                          className="article-title-button"
                          onClick={() => edit(p)}
                        >
                          {p.title}
                        </button>
                        <small>
                          /blog/{p.slug} · {p.category}
                        </small>
                      </div>
                      <div>
                        <span className={`badge ${p.status}`}>{p.status}</span>
                        <small>Working revision: {p.workflow_status}</small>
                        <small>
                          {new Date(p.updated_at).toLocaleDateString()}
                        </small>
                      </div>
                      <div className="table-actions">
                        {p.status === "trashed" ? (
                          <button
                            className="text-link"
                            disabled={busy}
                            onClick={() => void run(() => action(p, "restore"))}
                          >
                            <History size={15} />
                            Restore
                          </button>
                        ) : (
                          <>
                            <button
                              className="text-link"
                              onClick={() => edit(p)}
                            >
                              Edit <ArrowUpRight size={14} />
                            </button>
                            {p.status === "published" && (
                              <button
                                className="text-link"
                                disabled={busy}
                                onClick={() =>
                                  void run(() => action(p, "unpublish"))
                                }
                              >
                                Unpublish
                              </button>
                            )}
                            <button
                              className="icon-button"
                              aria-label={`Move ${p.title} to trash`}
                              onClick={() => {
                                setTrashTarget(p);
                                setReason("");
                              }}
                            >
                              <Trash2 size={16} />
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
              {!posts.some((p) =>
                tab === "trash"
                  ? p.status === "trashed"
                  : p.status !== "trashed",
              ) && (
                <div className="empty-blog">
                  <FileText size={32} />
                  <h3>
                    {tab === "trash"
                      ? "Nothing in trash."
                      : "Your first story starts here."}
                  </h3>
                  <p>
                    {tab === "trash"
                      ? "Articles remain preserved when manually trashed."
                      : "Write an article, upload Markdown, or begin with an editable guide."}
                  </p>
                </div>
              )}
              {tab === "posts" && (
                <div className="starter-guides">
                  <h3>Start with a useful guide.</h3>
                  <p>
                    Original starter content. Review, customize, and publish
                    when ready.
                  </p>
                  <div>
                    {starterPosts.map((p) => (
                      <button
                        key={p.slug}
                        onClick={() => {
                          edit({ ...p });
                          setDirty(true);
                        }}
                      >
                        <FileText size={18} />
                        <span>{p.title}</span>
                        <Plus size={16} />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
      {trashTarget && (
        <div className="modal-backdrop">
          <div
            className="confirm-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="trash-title"
          >
            <h2 id="trash-title">Move this article to trash?</h2>
            <p>
              “{trashTarget.title}” will be removed from the public website.
              Source and revision history stay preserved, and you can restore it
              to draft.
            </p>
            <label>
              Reason
              <textarea
                autoFocus
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                maxLength={500}
              />
            </label>
            <div className="actions">
              <button
                className="button light"
                onClick={() => setTrashTarget(null)}
              >
                Cancel
              </button>
              <button
                className="button dark"
                disabled={busy || !reason.trim()}
                onClick={() =>
                  void run(async () => {
                    await action(trashTarget, "trash", reason);
                    setTrashTarget(null);
                  })
                }
              >
                Move to trash
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
function EyebrowLocal() {
  return <span className="feature-index">WEBSITE / OWNER EDITOR</span>;
}
