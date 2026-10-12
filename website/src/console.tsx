import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  Plus,
  Save,
  Download,
  Copy,
  ArrowUp,
  ArrowDown,
  X,
} from "lucide-react";
import { api } from "./api";
import { Logo, Markdown } from "./ui";
import { MediaLibrary, MediaPreview } from "./media";
import { OperationsTools } from "./operations-tools";
import { ContentCalendar } from "./calendar";
import requirements from "./requirements.json";

export type Resource = {
  id?: string;
  kind: string;
  key: string;
  title: string;
  data: Record<string, any>;
  status?: string;
  version?: number;
  updated_at?: string;
  scheduled_at?: string | null;
  editorial_timezone?: string;
};
type Lead = {
  id: string;
  name: string;
  email: string;
  message: string;
  created_at: string;
  version: number;
  operations: { stage: string; assignee: string; note: string; tags: string[] };
};
const kinds: Record<string, string> = {
  page: "Pages",
  navigation: "Navigation",
  form: "Forms",
  redirect: "Redirects",
  campaign: "Campaign links",
  offer: "Offers & claims",
  collection: "Collections",
  entry: "Collection entries",
  workflow: "Workflows",
  experiment: "Experiments",
  brand: "Brand settings",
};
const download = (value: unknown, name: string) => {
  const href = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = href;
  a.download = name;
  a.click();
  URL.revokeObjectURL(href);
};
const initial = (kind: string): Resource => ({
  kind,
  key: "",
  title: "",
  data: (
    {
      page: {
        route: "/new-page",
        description: "",
        owner: "",
        audience: "",
        review_date: "",
        index: true,
        blocks: [
          {
            id: crypto.randomUUID(),
            type: "hero",
            title: "Your next useful page",
            body: "Explain the value clearly.",
            label: "Talk to us",
            href: "/contact",
          },
        ],
      },
      navigation: { items: [{ label: "Journal", href: "/blog" }] },
      form: {
        fields: [
          { key: "name", label: "Your name", type: "text", required: true },
          { key: "email", label: "Work email", type: "email", required: true },
          {
            key: "message",
            label: "How can we help?",
            type: "textarea",
            required: true,
          },
        ],
      },
      redirect: { source: "/old-page", target: "/contact", status: 301 },
      campaign: {
        destination: "/contact",
        source: "newsletter",
        medium: "email",
        campaign: "product-launch",
      },
      offer: {
        owner: "",
        audience: "",
        inclusions: "",
        exclusions: "",
        proof: "",
        terms: "",
        price: "",
        currency: "USD",
        review_date: "",
      },
      collection: {
        fields: [{ key: "description", label: "Description", type: "text" }],
      },
      entry: { collection_key: "", fields: {} },
      workflow: {
        trigger: "inquiry_accepted",
        action: "tag",
        value: "website",
      },
      experiment: {
        route: "/",
        hypothesis: "",
        unit: "session",
        variants: [
          "Build AI bots that work for your business.",
          "Put your business knowledge to work.",
        ],
        metric: "accepted_lead",
        baseline: 0.04,
        mde: 0.01,
        sample_per_arm: 6745,
        minimum_days: 14,
      },
      brand: {
        palette: "sage",
        tagline: "One AI assistant, built for real conversations.",
        company: "Northstar edtech",
        contact_email: "tech@northstaracad.com",
      },
    } as Record<string, Record<string, any>>
  )[kind],
});

function TextField({
  label,
  value,
  onChange,
  type = "text",
  multiline = false,
}: {
  label: string;
  value: any;
  onChange: (value: string) => void;
  type?: string;
  multiline?: boolean;
}) {
  return (
    <label>
      {label}
      {multiline ? (
        <textarea
          rows={4}
          value={value || ""}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          type={type}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}

export function OwnerConsole({ onLogout, roles }: { onLogout: () => void; roles: string[] }) {
  const canContent = roles.some(role => ['editor', 'publisher'].includes(role));
  const canLeads = roles.includes('lead_operator');
  const canPublish = roles.includes('publisher');
  const [tab, setTab] = useState("overview"),
    [rows, setRows] = useState<Resource[]>([]),
    [draft, setDraft] = useState<Resource | null>(null),
    [overview, setOverview] = useState<Record<string, any>>({}),
    [leads, setLeads] = useState<Lead[]>([]),
    [audit, setAudit] = useState<any[]>([]),
    [auditPage, setAuditPage] = useState(0),
    [filter, setFilter] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [history, setHistory] = useState<any[]>([]),
    [dirty, setDirty] = useState(false),
    [undo, setUndo] = useState<Resource[]>([]),
    [redo, setRedo] = useState<Resource[]>([]),
    [lead, setLead] = useState<Lead | null>(null),
    [reason, setReason] = useState("");
  const [resourceQuery, setResourceQuery] = useState(""),
    [showArchived, setShowArchived] = useState(false);
  const refresh = async () => {
    if (canContent) setRows(
      await api<Resource[]>("/platform-admin/website/resources", {}, true),
    );
    setOverview(await api("/platform-admin/website/overview", {}, true));
  };
  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Operation failed");
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    void run(refresh);
  }, []);
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  useEffect(() => {
    if (tab === "leads")
      void run(async () =>
        setLeads(await api("/platform-admin/website/leads", {}, true)),
      );
    if (tab === "audit")
      void run(async () => {
        const result = await api<{ items: any[] }>(
          `/platform-admin/website/audit?offset=${auditPage * 50}&kind=${encodeURIComponent(filter)}`,
          {},
          true,
        );
        setAudit(result.items);
      });
  }, [tab, auditPage, filter]);
  const change = (next: Resource) => {
    if (draft) setUndo((v) => [...v.slice(-29), draft]);
    setRedo([]);
    setDraft(next);
    setDirty(true);
    setNotice("Unsaved changes");
  };
  const currentDraft = useRef(draft);
  const [publishTime, setPublishTime] = useState("");
  const [media, setMedia] = useState<any[]>([]);
  useEffect(() => {
    if (tab === "page")
      void run(async () =>
        setMedia(await api("/platform-admin/website/media", {}, true)),
      );
  }, [tab]);
  currentDraft.current = draft;
  const [recover, setRecover] = useState<Resource | null>(null);
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("talktobot.website.owner-draft");
      if (raw) {
        const saved = JSON.parse(raw);
        if (saved.expires > Date.now()) setRecover(saved.draft);
        else sessionStorage.removeItem("talktobot.website.owner-draft");
      }
    } catch {
      /* Server saves remain authoritative. */
    }
  }, []);
  useEffect(() => {
    if (!draft || !dirty) return;
    try {
      sessionStorage.setItem(
        "talktobot.website.owner-draft",
        JSON.stringify({ draft, expires: Date.now() + 86400000 }),
      );
    } catch {
      setNotice("Local recovery storage unavailable. Save to the server.");
    }
  }, [draft, dirty]);
  const field = (key: string, value: any) =>
    draft && change({ ...draft, data: { ...draft.data, [key]: value } });
  const selectTab = (value: string) => {
    if (dirty) {
      setError("Save or discard your draft before changing sections.");
      return;
    }
    setTab(value);
    setDraft(null);
    setLead(null);
    setHistory([]);
    setError("");
    setNotice("");
    setResourceQuery("");
  };
  const save = async () => {
    if (!draft) return;
    const sent = JSON.stringify(draft);
    const saved = await api<Resource>(
      `/platform-admin/website/resources${draft.id ? "/" + draft.id : ""}`,
      {
        method: draft.id ? "PUT" : "POST",
        body: JSON.stringify({
          kind: draft.kind,
          key: draft.key,
          title: draft.title,
          data: draft.data,
          ...(draft.version ? { version: draft.version } : {}),
        }),
      },
      true,
    );
    if (JSON.stringify(currentDraft.current) === sent) {
      setDraft(saved);
      setDirty(false);
      sessionStorage.removeItem("talktobot.website.owner-draft");
      setRecover(null);
      setNotice("Draft saved on the server. Live content remains unchanged.");
    } else {
      setDraft((current) =>
        current
          ? {
              ...current,
              id: saved.id,
              version: saved.version,
              status: saved.status,
            }
          : current,
      );
      setNotice("Earlier changes saved. Your latest edits are still pending.");
    }
    await refresh();
  };
  useEffect(() => {
    if (!dirty || !draft?.id || busy || error) return;
    const timer = window.setTimeout(() => void run(save), 2000);
    return () => clearTimeout(timer);
  }, [draft, dirty, busy, error]);
  const action = async (value: string) => {
    if (value !== 'review' && !canPublish) throw new Error('Publishing access is required.');
    if (!draft?.id || dirty)
      throw new Error("Save your draft before changing its editorial state.");
    if (reason.trim().length < 3)
      throw new Error("Add a reason for this action.");
    const saved = await api<Resource>(
      `/platform-admin/website/resources/${draft.id}/actions`,
      {
        method: "POST",
        body: JSON.stringify({
          version: draft.version,
          action: value,
          reason,
          ...(value === "schedule"
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
    setDraft(saved);
    setReason("");
    setNotice(`Action committed: ${value}.`);
    await refresh();
  };
  const list = rows.filter(
    (r) =>
      r.kind === tab &&
      (showArchived || r.status !== "archived") &&
      `${r.title} ${r.key} ${r.status}`
        .toLowerCase()
        .includes(resourceQuery.toLowerCase()),
  );
  return (
    <div className="editor owner-console">
      <header className="editor-header">
        <Logo />
        <span className="studio-label">OWNER CONSOLE</span>
        <div>
          <Link className="button light small" to="/admin">
            Article studio
          </Link>
          <Link className="button light small" to="/">
            View website
          </Link>
          <button className="button light small" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>
      <div className="editor-shell">
        <aside className="editor-sidebar">
          <span className="subtle-label">OPERATE YOUR WEBSITE</span>
          {Object.entries({
            overview: "Overview",
            ...kinds,
            media: "Media library",
            leads: "Lead pipeline",
            audit: "Audit center",
            tools: "Import & export",
            calendar: "Content calendar",
            readiness: "Blueprint & launch gates",
            providers: "Provider readiness",
          }).filter(([key]) => key === 'overview' || key === 'readiness' || (key === 'leads' ? canLeads : canContent)).map(([key, label]) => (
            <button
              key={key}
              className={tab === key ? "active" : ""}
              onClick={() => selectTab(key)}
            >
              {label}
            </button>
          ))}
          <div className="editor-tip">
            <strong>Drafts stay private.</strong>
            <p>
              Review, approve, then publish. Every change keeps its version and
              actor.
            </p>
          </div>
        </aside>
        <main className="editor-main">
          <div className="editor-page-heading">
            <div>
              <span className="feature-index">TALKTOBOT.IO</span>
              <h1>
                {draft
                  ? draft.title || "Create a resource"
                  : (
                      {
                        overview: "Your website, connected.",
                        leads: "Turn enquiries into outcomes.",
                        audit: "An accountable history.",
                        readiness: "Nothing silently omitted.",
                        providers: "Configure before activation.",
                        media: "Your media, with provenance.",
                        tools: "Preserve and move your content.",
                        calendar: "Plan your next publication.",
                      } as Record<string, string>
                    )[tab] || kinds[tab]}
              </h1>
              <p>
                Manage content and operations with clear states, version checks,
                and preserved history.
              </p>
            </div>
            {kinds[tab] && !draft && (
              <button
                className="button dark"
                onClick={() => {
                  setDraft(initial(tab));
                  setDirty(false);
                  setUndo([]);
                  setRedo([]);
                }}
              >
                <Plus size={16} /> New {tab}
              </button>
            )}
          </div>
          {error && (
            <p role="alert" className="error-message">
              {error}
            </p>
          )}
          {notice && (
            <p role="status" className="console-notice">
              {notice}
            </p>
          )}
          {recover && !draft && (
            <div className="console-card">
              <h2>Recover your interrupted draft?</h2>
              <p>
                The copy expires after 24 hours and is cleared on logout.
                Recovery never publishes content.
              </p>
              <button
                className="button light small"
                onClick={() => {
                  setTab(recover.kind);
                  setDraft(recover);
                  setDirty(true);
                  setRecover(null);
                }}
              >
                Recover draft
              </button>
              <button
                className="button light small"
                onClick={() => {
                  sessionStorage.removeItem("talktobot.website.owner-draft");
                  setRecover(null);
                }}
              >
                Discard recovery copy
              </button>
            </div>
          )}
          {busy && <p role="status">Working…</p>}
          {tab === "overview" && (
            <>
              <div className="console-metrics">
                {[
                  "articles",
                  "published_articles",
                  "enquiries",
                  "resources",
                  "audit_records",
                ].map((k) => (
                  <article key={k}>
                    <span>{k.replaceAll("_", " ")}</span>
                    <strong>{overview[k] ?? "—"}</strong>
                  </article>
                ))}
              </div>
              <div className="console-card">
                <h2>Owner workflow</h2>
                <p>
                  Create approved sections, build a form, publish it, then
                  connect it to a page. Review enquiries in the lead pipeline
                  and inspect the audit trail.
                </p>
                <p>
                  Production domain: <strong>talktobot.io</strong>. Local health
                  is separate from production qualification.
                </p>
                <p>
                  External email, CRM and advertising delivery:{" "}
                  <strong>
                    {overview.external_delivery?.replaceAll("_", " ") ||
                      "not configured"}
                  </strong>
                  .
                </p>
              </div>
            </>
          )}
          {kinds[tab] && !draft && (
            <div className="console-card">
              <input
                aria-label="Search resources"
                placeholder="Search title, key or state"
                value={resourceQuery}
                onChange={(e) => setResourceQuery(e.target.value)}
              />
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={showArchived}
                  onChange={(e) => setShowArchived(e.target.checked)}
                />{" "}
                Include archived resources
              </label>
              {list.length ? (
                list.map((row) => (
                  <div className="console-list-row" key={row.id}>
                    <div>
                      <strong>{row.title}</strong>
                      <p>
                        {row.key} · {row.status} · revision {row.version}
                      </p>
                    </div>
                    <button
                      className="button light small"
                      onClick={() => {
                        setDraft(row);
                        setUndo([]);
                        setRedo([]);
                        setHistory([]);
                      }}
                    >
                      Edit
                    </button>
                  </div>
                ))
              ) : (
                <p>
                  No {kinds[tab].toLowerCase()} yet. Create your first resource.
                </p>
              )}
            </div>
          )}
          {draft && (
            <>
              <div className="console-toolbar">
                <button
                  className="button light small"
                  disabled={busy}
                  onClick={() => {
                    setDraft({
                      ...draft,
                      id: undefined,
                      version: undefined,
                      status: "draft",
                      scheduled_at: null,
                      key: `${draft.key.slice(0, 85)}-copy-${Date.now()}`,
                      title: `${draft.title.slice(0, 160)} (copy)`,
                    });
                    setDirty(true);
                    setError("");
                    setNotice(
                      "Copy created locally. Set a new page route if needed, then save and review it.",
                    );
                  }}
                >
                  Duplicate as new draft
                </button>
                {error && draft.id && (
                  <button
                    className="button light small"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        download(draft, "my-unsaved-draft.json");
                        const rows = await api<Resource[]>(
                          "/platform-admin/website/resources",
                          {},
                          true,
                        );
                        const latest = rows.find((row) => row.id === draft.id);
                        if (!latest)
                          throw new Error("Saved resource no longer found");
                        setDraft(latest);
                        setDirty(false);
                        setUndo([]);
                        setRedo([]);
                        sessionStorage.removeItem(
                          "talktobot.website.owner-draft",
                        );
                        setNotice(
                          "Your local changes were downloaded. The current server revision is loaded.",
                        );
                      })
                    }
                  >
                    Download my draft and reload server revision
                  </button>
                )}
                <button
                  className="button light small"
                  onClick={() => {
                    setDraft(null);
                    setDirty(false);
                    sessionStorage.removeItem("talktobot.website.owner-draft");
                    setRecover(null);
                    setHistory([]);
                    setNotice(
                      "Draft discarded in this editor; saved versions are preserved.",
                    );
                  }}
                >
                  <ArrowLeft size={15} /> Discard / back
                </button>
                <button
                  className="button light small"
                  disabled={!undo.length}
                  onClick={() => {
                    setRedo((v) => [...v, draft]);
                    setDraft(undo[undo.length - 1]);
                    setUndo((v) => v.slice(0, -1));
                    setDirty(true);
                  }}
                >
                  Undo
                </button>
                <button
                  className="button light small"
                  disabled={!redo.length}
                  onClick={() => {
                    setUndo((v) => [...v, draft]);
                    setDraft(redo[redo.length - 1]);
                    setRedo((v) => v.slice(0, -1));
                    setDirty(true);
                  }}
                >
                  Redo
                </button>
                <button
                  className="button light small"
                  onClick={() =>
                    download(draft, `${draft.key || "resource"}.json`)
                  }
                >
                  <Download size={15} /> Export
                </button>
                <button
                  className="button dark small"
                  disabled={busy}
                  onClick={() => void run(save)}
                >
                  <Save size={15} /> Save draft
                </button>
              </div>
              <div className="console-edit-grid">
                <section className="console-card console-fields">
                  <TextField
                    label="Resource title"
                    value={draft.title}
                    onChange={(value) => change({ ...draft, title: value })}
                  />
                  <TextField
                    label="Stable key"
                    value={draft.key}
                    onChange={(value) => {
                      if (!draft.id) change({ ...draft, key: value });
                    }}
                  />
                  <p className="form-note">
                    Keys use lowercase words and hyphens. Saved keys do not
                    change.
                  </p>
                  {draft.kind === "page" && (
                    <>
                      <TextField
                        label="Public route"
                        value={draft.data.route}
                        onChange={(v) => field("route", v)}
                      />
                      <TextField
                        label="SEO description"
                        value={draft.data.description}
                        onChange={(v) => field("description", v)}
                      />
                      <TextField
                        label="Content owner"
                        value={draft.data.owner}
                        onChange={(v) => field("owner", v)}
                      />
                      <TextField
                        label="Target audience"
                        value={draft.data.audience}
                        onChange={(v) => field("audience", v)}
                      />
                      <TextField
                        label="Next review date"
                        type="date"
                        value={draft.data.review_date}
                        onChange={(v) => field("review_date", v)}
                      />
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={draft.data.index !== false}
                          onChange={(e) => field("index", e.target.checked)}
                        />
                        Allow search indexing
                      </label>
                      <h3>Approved sections</h3>
                      {draft.data.blocks.map((b: any, i: number) => (
                        <fieldset className="console-block" key={b.id}>
                          <legend>
                            Section {i + 1}: {b.type}
                          </legend>
                          {b.type === "image" && (
                            <>
                              <label>
                                Uploaded asset
                                <select
                                  value={b.asset_id || ""}
                                  onChange={(e) =>
                                    field(
                                      "blocks",
                                      draft.data.blocks.map(
                                        (x: any, j: number) =>
                                          j === i
                                            ? {
                                                ...x,
                                                asset_id: e.target.value,
                                                alt:
                                                  media.find(
                                                    (m) =>
                                                      m.id === e.target.value,
                                                  )?.alt || "",
                                              }
                                            : x,
                                      ),
                                    )
                                  }
                                >
                                  <option value="">
                                    Choose validated media
                                  </option>
                                  {media.map((m) => (
                                    <option key={m.id} value={m.id}>
                                      {m.title}
                                    </option>
                                  ))}
                                </select>
                              </label>
                              <TextField
                                label="Alternative text for this use"
                                value={b.alt}
                                onChange={(v) =>
                                  field(
                                    "blocks",
                                    draft.data.blocks.map(
                                      (x: any, j: number) =>
                                        j === i ? { ...x, alt: v } : x,
                                    ),
                                  )
                                }
                              />
                            </>
                          )}
                          <div className="console-toolbar">
                            <button
                              aria-label={`Move section ${i + 1} up`}
                              disabled={!i}
                              onClick={() => {
                                const bs = [...draft.data.blocks];
                                [bs[i - 1], bs[i]] = [bs[i], bs[i - 1]];
                                field("blocks", bs);
                              }}
                            >
                              <ArrowUp size={15} />
                            </button>
                            <button
                              aria-label={`Move section ${i + 1} down`}
                              disabled={i === draft.data.blocks.length - 1}
                              onClick={() => {
                                const bs = [...draft.data.blocks];
                                [bs[i + 1], bs[i]] = [bs[i], bs[i + 1]];
                                field("blocks", bs);
                              }}
                            >
                              <ArrowDown size={15} />
                            </button>
                            <button
                              aria-label={`Remove section ${i + 1}`}
                              onClick={() =>
                                field(
                                  "blocks",
                                  draft.data.blocks.filter(
                                    (_: any, j: number) => i !== j,
                                  ),
                                )
                              }
                            >
                              <X size={15} />
                            </button>
                          </div>
                          {[
                            "title",
                            "body",
                            ...(b.type === "form"
                              ? ["form_key"]
                              : ["label", "href"]),
                          ].map((k) => (
                            <TextField
                              key={k}
                              label={k.replaceAll("_", " ")}
                              value={b[k]}
                              multiline={k === "body"}
                              onChange={(v) =>
                                field(
                                  "blocks",
                                  draft.data.blocks.map((x: any, j: number) =>
                                    j === i ? { ...x, [k]: v } : x,
                                  ),
                                )
                              }
                            />
                          ))}
                        </fieldset>
                      ))}
                      <label>
                        Add section
                        <select
                          defaultValue=""
                          onChange={(e) => {
                            if (e.target.value)
                              field("blocks", [
                                ...draft.data.blocks,
                                {
                                  id: crypto.randomUUID(),
                                  type: e.target.value,
                                  title: "",
                                  body: "",
                                },
                              ]);
                            e.target.value = "";
                          }}
                        >
                          <option value="">Choose a type</option>
                          {["hero", "text", "cta", "faq", "form", "image"].map(
                            (k) => (
                              <option key={k}>{k}</option>
                            ),
                          )}
                        </select>
                      </label>
                    </>
                  )}
                  {draft.kind === "navigation" && (
                    <>
                      {draft.data.items.map((item: any, i: number) => (
                        <fieldset className="console-block" key={i}>
                          <legend>Link {i + 1}</legend>
                          {["label", "href"].map((k) => (
                            <TextField
                              key={k}
                              label={k}
                              value={item[k]}
                              onChange={(v) =>
                                field(
                                  "items",
                                  draft.data.items.map((x: any, j: number) =>
                                    j === i ? { ...x, [k]: v } : x,
                                  ),
                                )
                              }
                            />
                          ))}
                          <button
                            className="text-link"
                            onClick={() =>
                              field(
                                "items",
                                draft.data.items.filter(
                                  (_: any, j: number) => j !== i,
                                ),
                              )
                            }
                          >
                            Remove link
                          </button>
                        </fieldset>
                      ))}
                      <button
                        className="button light small"
                        onClick={() =>
                          field("items", [
                            ...draft.data.items,
                            { label: "New link", href: "/contact" },
                          ])
                        }
                      >
                        Add link
                      </button>
                    </>
                  )}
                  {(draft.kind === "form" || draft.kind === "collection") && (
                    <>
                      {draft.data.fields.map((f: any, i: number) => (
                        <fieldset className="console-block" key={i}>
                          <legend>Field {i + 1}</legend>
                          {["key", "label"].map((k) => (
                            <TextField
                              key={k}
                              label={k}
                              value={f[k]}
                              onChange={(v) =>
                                field(
                                  "fields",
                                  draft.data.fields.map((x: any, j: number) =>
                                    j === i ? { ...x, [k]: v } : x,
                                  ),
                                )
                              }
                            />
                          ))}
                          <label>
                            Type
                            <select
                              value={f.type}
                              onChange={(e) =>
                                field(
                                  "fields",
                                  draft.data.fields.map((x: any, j: number) =>
                                    j === i
                                      ? { ...x, type: e.target.value }
                                      : x,
                                  ),
                                )
                              }
                            >
                              {(draft.kind === "form"
                                ? [
                                    "text",
                                    "email",
                                    "textarea",
                                    "select",
                                    "checkbox",
                                  ]
                                : ["text", "number", "boolean", "date"]
                              ).map((k) => (
                                <option key={k}>{k}</option>
                              ))}
                            </select>
                          </label>
                          {f.type === "select" && (
                            <TextField
                              label="Options (one per line)"
                              multiline
                              value={(f.options || []).join("\n")}
                              onChange={(v) =>
                                field(
                                  "fields",
                                  draft.data.fields.map((x: any, j: number) =>
                                    j === i
                                      ? { ...x, options: v.split("\n") }
                                      : x,
                                  ),
                                )
                              }
                            />
                          )}
                          <label className="checkbox-label">
                            <input
                              type="checkbox"
                              checked={!!f.required}
                              onChange={(e) =>
                                field(
                                  "fields",
                                  draft.data.fields.map((x: any, j: number) =>
                                    j === i
                                      ? { ...x, required: e.target.checked }
                                      : x,
                                  ),
                                )
                              }
                            />
                            Required
                          </label>
                          <button
                            className="text-link"
                            onClick={() =>
                              field(
                                "fields",
                                draft.data.fields.filter(
                                  (_: any, j: number) => j !== i,
                                ),
                              )
                            }
                          >
                            Remove field
                          </button>
                        </fieldset>
                      ))}
                      <button
                        className="button light small"
                        onClick={() =>
                          field("fields", [
                            ...draft.data.fields,
                            {
                              key: `field_${draft.data.fields.length + 1}`,
                              label: "New field",
                              type: "text",
                              required: false,
                            },
                          ])
                        }
                      >
                        Add field
                      </button>
                    </>
                  )}
                  {draft.kind === "redirect" && (
                    <>
                      <TextField
                        label="Old route"
                        value={draft.data.source}
                        onChange={(v) => field("source", v)}
                      />
                      <TextField
                        label="Destination route"
                        value={draft.data.target}
                        onChange={(v) => field("target", v)}
                      />
                      <label>
                        HTTP status
                        <select
                          value={draft.data.status}
                          onChange={(e) =>
                            field("status", Number(e.target.value))
                          }
                        >
                          {[301, 302, 308].map((v) => (
                            <option key={v}>{v}</option>
                          ))}
                        </select>
                      </label>
                    </>
                  )}
                  {draft.kind === "campaign" && (
                    <>
                      {["destination", "source", "campaign"].map((k) => (
                        <TextField
                          key={k}
                          label={k}
                          value={draft.data[k]}
                          onChange={(v) => field(k, v)}
                        />
                      ))}
                      <label>
                        Medium
                        <select
                          value={draft.data.medium}
                          onChange={(e) => field("medium", e.target.value)}
                        >
                          {[
                            "cpc",
                            "email",
                            "social",
                            "organic",
                            "referral",
                            "qr",
                            "partner",
                          ].map((v) => (
                            <option key={v}>{v}</option>
                          ))}
                        </select>
                      </label>
                      <p>
                        No customer names, emails, phone numbers or sensitive
                        audiences in campaign labels.
                      </p>
                      <code className="console-url">{`https://talktobot.io${draft.data.destination}?utm_source=${encodeURIComponent(draft.data.source)}&utm_medium=${encodeURIComponent(draft.data.medium)}&utm_campaign=${encodeURIComponent(draft.data.campaign)}`}</code>
                      <button
                        className="button light small"
                        onClick={() =>
                          void run(async () => {
                            await navigator.clipboard.writeText(
                              `https://talktobot.io${draft.data.destination}?utm_source=${encodeURIComponent(draft.data.source)}&utm_medium=${encodeURIComponent(draft.data.medium)}&utm_campaign=${encodeURIComponent(draft.data.campaign)}`,
                            );
                            setNotice("Campaign link copied.");
                          })
                        }
                      >
                        <Copy size={15} />
                        Copy link
                      </button>
                    </>
                  )}
                  {draft.kind === "entry" && (
                    <>
                      <label>
                        Collection
                        <select
                          value={draft.data.collection_key}
                          onChange={(e) =>
                            change({
                              ...draft,
                              data: {
                                collection_key: e.target.value,
                                fields: {},
                              },
                            })
                          }
                        >
                          <option value="">Choose a collection</option>
                          {rows
                            .filter(
                              (r) =>
                                r.kind === "collection" &&
                                r.status !== "archived",
                            )
                            .map((r) => (
                              <option value={r.key} key={r.key}>
                                {r.title}
                              </option>
                            ))}
                        </select>
                      </label>
                      {rows
                        .find(
                          (r) =>
                            r.kind === "collection" &&
                            r.key === draft.data.collection_key,
                        )
                        ?.data.fields.map((f: any) =>
                          f.type === "boolean" ? (
                            <label className="checkbox-label" key={f.key}>
                              <input
                                type="checkbox"
                                checked={!!draft.data.fields[f.key]}
                                onChange={(e) =>
                                  field("fields", {
                                    ...draft.data.fields,
                                    [f.key]: e.target.checked,
                                  })
                                }
                              />
                              {f.label || f.key}
                            </label>
                          ) : (
                            <TextField
                              key={f.key}
                              label={f.label || f.key}
                              multiline={f.type === "text"}
                              type={
                                f.type === "number"
                                  ? "number"
                                  : f.type === "date"
                                    ? "date"
                                    : "text"
                              }
                              value={draft.data.fields[f.key]}
                              onChange={(v) =>
                                field("fields", {
                                  ...draft.data.fields,
                                  [f.key]: f.type === "number" ? Number(v) : v,
                                })
                              }
                            />
                          ),
                        )}
                      <p>
                        Publish the collection first. Only published entries are
                        available at /collections/{draft.data.collection_key}/
                        {draft.key || "entry-key"}.
                      </p>
                    </>
                  )}
                  {draft.kind === "offer" && (
                    <>
                      {[
                        "owner",
                        "audience",
                        "inclusions",
                        "exclusions",
                        "proof",
                        "terms",
                        "price",
                        "currency",
                        "review_date",
                      ].map((k) => (
                        <TextField
                          key={k}
                          label={k.replaceAll("_", " ")}
                          value={draft.data[k]}
                          type={k === "review_date" ? "date" : "text"}
                          multiline={[
                            "inclusions",
                            "exclusions",
                            "proof",
                            "terms",
                          ].includes(k)}
                          onChange={(v) => field(k, v)}
                        />
                      ))}
                      <p>
                        Use verified business facts. Saving an offer does not
                        change application billing or create a contract.
                      </p>
                    </>
                  )}
                  {draft.kind === "workflow" && (
                    <>
                      <p>
                        Trigger: an enquiry is durably accepted. Approved local
                        actions commit in the same transaction.
                      </p>
                      <label>
                        Action
                        <select
                          value={draft.data.action}
                          onChange={(e) => field("action", e.target.value)}
                        >
                          <option value="tag">Tag lead</option>
                          <option value="assign">Assign lead</option>
                        </select>
                      </label>
                      <TextField
                        label="Tag or assignee"
                        value={draft.data.value}
                        onChange={(v) => field("value", v)}
                      />
                      <div className="console-card">
                        <h3>Simulation</h3>
                        <p>
                          A synthetic accepted enquiry would {draft.data.action}{" "}
                          “{draft.data.value}”. This preview sends nothing and
                          creates no lead.
                        </p>
                      </div>
                    </>
                  )}
                  {draft.kind === "experiment" && (
                    <>
                      <TextField
                        label="Destination route"
                        value={draft.data.route}
                        onChange={(v) => field("route", v)}
                      />
                      <TextField
                        label="Hypothesis"
                        multiline
                        value={draft.data.hypothesis}
                        onChange={(v) => field("hypothesis", v)}
                      />
                      {draft.data.variants.map((v: string, i: number) => (
                        <TextField
                          key={i}
                          label={i ? "Treatment headline" : "Control headline"}
                          value={v}
                          onChange={(value) =>
                            field(
                              "variants",
                              draft.data.variants.map((x: string, j: number) =>
                                j === i ? value : x,
                              ),
                            )
                          }
                        />
                      ))}
                      {["sample_per_arm", "minimum_days"].map((k) => (
                        <TextField
                          key={k}
                          label={k.replaceAll("_", " ")}
                          type="number"
                          value={draft.data[k]}
                          onChange={(v) => field(k, Number(v))}
                        />
                      ))}
                      <p>
                        Definitions can be reviewed and approved. Public
                        activation remains blocked until measurement approval
                        and A/A evidence are supplied. No statistical winner is
                        inferred from an empty dataset.
                      </p>
                    </>
                  )}
                  {draft.kind === "brand" && (
                    <>
                      <label>
                        Approved accent palette
                        <select
                          value={draft.data.palette}
                          onChange={(e) => field("palette", e.target.value)}
                        >
                          {["sage", "blue", "violet"].map((k) => (
                            <option key={k}>{k}</option>
                          ))}
                        </select>
                      </label>
                      <TextField
                        label="Tagline"
                        value={draft.data.tagline}
                        onChange={(v) => field("tagline", v)}
                      />
                      <TextField
                        label="Company / legal identity"
                        value={draft.data.company || ""}
                        onChange={(v) => field("company", v)}
                      />
                      <TextField
                        label="Contact and privacy email"
                        type="email"
                        value={draft.data.contact_email || ""}
                        onChange={(v) => field("contact_email", v)}
                      />
                    </>
                  )}
                </section>
                <aside>
                  <section className="console-card">
                    <span className="badge">
                      {draft.status || "unsaved"} · revision{" "}
                      {draft.version || "—"}
                    </span>
                    <h2>Editorial workflow</h2>
                    <TextField
                      label="Publish time (your device timezone)"
                      type="datetime-local"
                      value={publishTime}
                      onChange={setPublishTime}
                    />
                    {draft.scheduled_at && (
                      <p>
                        Scheduled:{" "}
                        {new Date(draft.scheduled_at).toLocaleString()} ·{" "}
                        {draft.editorial_timezone}
                      </p>
                    )}
                    <TextField
                      label="Action reason"
                      value={reason}
                      onChange={setReason}
                    />
                    <div className="console-actions">
                      {[
                        "review",
                        "approve",
                        "publish",
                        "schedule",
                        "unpublish",
                        "archive",
                        "restore",
                      ].map((value) => (
                        <button
                          key={value}
                          className="button light small"
                          disabled={
                            busy ||
                            dirty ||
                            !draft.id ||
                            (
                              {
                                review: ["draft"],
                                approve: ["in_review"],
                                publish: ["approved", "scheduled"],
                                schedule: ["approved"],
                                unpublish: [
                                  "scheduled",
                                  "published",
                                  "draft",
                                  "approved",
                                  "in_review",
                                ],
                                archive: [
                                  "scheduled",
                                  "published",
                                  "draft",
                                  "approved",
                                  "in_review",
                                ],
                                restore: ["archived"],
                              } as Record<string, string[]>
                            )[value].includes(draft.status || "") === false
                          }
                          onClick={() => void run(() => action(value))}
                        >
                          {value}
                        </button>
                      ))}
                    </div>
                    <p>
                      Publish uses the approved saved revision. Draft edits
                      remain private.
                    </p>
                    {draft.id && (
                      <button
                        className="text-link"
                        onClick={() =>
                          void run(async () =>
                            setHistory(
                              await api(
                                `/platform-admin/website/resources/${draft.id}/history`,
                                {},
                                true,
                              ),
                            ),
                          )
                        }
                      >
                        View saved revisions
                      </button>
                    )}
                  </section>
                  {draft.kind === "page" && (
                    <section className="console-card">
                      <span className="badge">Private preview</span>
                      {draft.data.blocks.map((b: any) => (
                        <section key={b.id}>
                          <h2>{b.title}</h2>
                          <Markdown text={b.body || ""} />
                          {b.type === "image" && b.asset_id && (
                            <MediaPreview id={b.asset_id} alt={b.alt || ""} />
                          )}
                          {b.label && (
                            <span className="button light small">
                              {b.label}
                            </span>
                          )}
                          {b.type === "form" && (
                            <p>
                              Form reference:{" "}
                              {b.form_key || "Choose a published form"}
                            </p>
                          )}
                        </section>
                      ))}
                    </section>
                  )}
                  {history.map((h) => (
                    <div className="console-card" key={h.id}>
                      <strong>
                        Revision {h.version} · {h.action}
                      </strong>
                      <p>{h.reason}</p>
                      <button
                        className="text-link"
                        onClick={() => change({ ...draft, ...h.snapshot })}
                      >
                        Load as an unsaved draft
                      </button>
                    </div>
                  ))}
                </aside>
              </div>
            </>
          )}
          {tab === "leads" && (
            <>
              {lead ? (
                <form
                  className="console-card console-fields"
                  onSubmit={(e: FormEvent) => {
                    e.preventDefault();
                    void run(async () => {
                      await api(
                        `/platform-admin/website/leads/${lead.id}`,
                        {
                          method: "PUT",
                          body: JSON.stringify({
                            ...lead.operations,
                            version: lead.version,
                            reason,
                          }),
                        },
                        true,
                      );
                      setLeads(
                        await api("/platform-admin/website/leads", {}, true),
                      );
                      setLead(null);
                      setReason("");
                      setNotice("Lead update committed.");
                    });
                  }}
                >
                  <h2>{lead.name}</h2>
                  <p>{lead.email}</p>
                  <p>{lead.message}</p>
                  <label>
                    Stage
                    <select
                      value={lead.operations.stage}
                      onChange={(e) =>
                        setLead({
                          ...lead,
                          operations: {
                            ...lead.operations,
                            stage: e.target.value,
                          },
                        })
                      }
                    >
                      {[
                        "new",
                        "assigned",
                        "contacted",
                        "qualified",
                        "won",
                        "closed",
                      ].map((k) => (
                        <option key={k}>{k}</option>
                      ))}
                    </select>
                  </label>
                  {["assignee", "note"].map((k) => (
                    <TextField
                      key={k}
                      label={k}
                      multiline={k === "note"}
                      value={(lead.operations as any)[k]}
                      onChange={(v) =>
                        setLead({
                          ...lead,
                          operations: { ...lead.operations, [k]: v },
                        })
                      }
                    />
                  ))}
                  <TextField
                    label="Tags (comma separated)"
                    value={lead.operations.tags.join(", ")}
                    onChange={(v) =>
                      setLead({
                        ...lead,
                        operations: {
                          ...lead.operations,
                          tags: v
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean),
                        },
                      })
                    }
                  />
                  <TextField
                    label="Reason for update"
                    value={reason}
                    onChange={setReason}
                  />
                  <button className="button dark" disabled={busy}>
                    Save lead
                  </button>
                  <button
                    type="button"
                    className="button light"
                    onClick={() => setLead(null)}
                  >
                    Back
                  </button>
                </form>
              ) : (
                <div className="console-card">
                  {leads.map((l) => (
                    <div className="console-list-row" key={l.id}>
                      <div>
                        <strong>{l.name}</strong>
                        <p>
                          {l.email} · {l.operations.stage} ·{" "}
                          {l.operations.assignee || "Unassigned"}
                        </p>
                        <p>{l.operations.tags.join(" · ")}</p>
                      </div>
                      <button
                        className="button light small"
                        onClick={() => setLead(l)}
                      >
                        Review lead
                      </button>
                    </div>
                  ))}
                  {!leads.length && <p>No accepted enquiries yet.</p>}
                </div>
              )}
            </>
          )}
          {tab === "audit" && (
            <div className="console-card">
              <label>
                Filter by resource type
                <select
                  value={filter}
                  onChange={(e) => {
                    setFilter(e.target.value);
                    setAuditPage(0);
                  }}
                >
                  <option value="">All</option>
                  {["article", "lead", ...Object.keys(kinds)].map((k) => (
                    <option key={k}>{k}</option>
                  ))}
                </select>
              </label>
              <div className="console-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Action</th>
                      <th>Resource</th>
                      <th>Revision</th>
                      <th>Actor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit.map((a) => (
                      <tr key={a.id}>
                        <td>{new Date(a.occurred_at).toLocaleString()}</td>
                        <td>
                          {a.action}
                          <small>{a.reason}</small>
                        </td>
                        <td>
                          {a.kind}
                          <small>{a.resource_id}</small>
                        </td>
                        <td>{a.version}</td>
                        <td>{a.actor_id}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="console-toolbar">
                <button
                  className="button light small"
                  disabled={!auditPage}
                  onClick={() => setAuditPage((v) => v - 1)}
                >
                  Previous
                </button>
                <span>Page {auditPage + 1}</span>
                <button
                  className="button light small"
                  disabled={audit.length < 50}
                  onClick={() => setAuditPage((v) => v + 1)}
                >
                  Next
                </button>
                <button
                  className="button light small"
                  onClick={() => download(audit, "redacted-audit-page.json")}
                >
                  Export visible page
                </button>
              </div>
              <p>
                Changes are locally append-only. Independent signed checkpoints
                and production audit retention remain launch gates.
              </p>
            </div>
          )}
          {tab === "media" && <MediaLibrary />}
          {tab === "tools" && <OperationsTools />}
          {tab === "calendar" && <ContentCalendar />}
          {tab === "readiness" && (
            <div className="console-card">
              <p>
                All 120 document capabilities are tracked. User-approved
                profile: AI SaaS marketing website and complete owner console. A
                configured screen alone is not a verified capability.
              </p>
              <input
                aria-label="Search blueprint requirements"
                placeholder="Search capability, ID or status"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
              <div className="console-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Capability</th>
                      <th>Applicability</th>
                      <th>Implementation</th>
                      <th>Activation</th>
                      <th>Verification</th>
                    </tr>
                  </thead>
                  <tbody>
                    {requirements
                      .filter((r) =>
                        `${r.id} ${r.capability} ${r.implementation}`
                          .toLowerCase()
                          .includes(filter.toLowerCase()),
                      )
                      .map((r) => (
                        <tr key={r.id}>
                          <td>{r.id}</td>
                          <td>
                            {r.capability}
                            <small>Chapters {r.chapters}</small>
                            <details>
                              <summary>Requirement details</summary>
                              <p>
                                Specification: {r.specification}. Owner:{" "}
                                {r.owner}. Edition: {r.edition}.
                              </p>
                              <p>
                                Dependencies:{" "}
                                {r.dependencies.join(", ") || "None recorded"}
                              </p>
                              <p>
                                Evidence:{" "}
                                {r.evidence.join(", ") || "Not yet recorded"}
                              </p>
                              <p>Reviewed {r.review_date}</p>
                            </details>
                          </td>
                          <td>{r.applicability}</td>
                          <td>
                            {r.implementation}
                            <small>{r.rationale}</small>
                          </td>
                          <td>{r.activation}</td>
                          <td>{r.verification}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
              <button
                className="button light small"
                onClick={() =>
                  download(requirements, "talktobot-blueprint-register.json")
                }
              >
                Export full register
              </button>
            </div>
          )}
          {tab === "providers" && (
            <div className="console-card">
              <h2>Activation checklist</h2>
              {[
                "Domain ownership, DNS, HTTPS and account recovery for talktobot.io",
                "Northstar edtech / tech@northstaracad.com recorded; jurisdiction, approved policies and retention decisions remain pending",
                "Transactional email provider and verified sender domain",
                "CRM account and enquiry delivery mapping",
                "Analytics purpose, consent policy and destination account",
                "Google / Meta accounts, conversion maps and spending authority",
                "Independent audit archive, backup and restore evidence",
                "MFA and explicit production editor permissions",
              ].map((s) => (
                <div className="console-list-row" key={s}>
                  <strong>{s}</strong>
                  <span className="badge">
                    Awaiting configuration / evidence
                  </span>
                </div>
              ))}
              <p>
                Saving website content does not activate advertising, send
                email, or modify external accounts.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
