import {
  createContext,
  useContext,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import { Link, useLocation } from "react-router-dom";
import { api, SITE_URL } from "./api";
import { Markdown, Eyebrow } from "./ui";
import type { Resource } from "./console";

const ManifestContext = createContext<{
  resources: Resource[];
  loading: boolean;
  failed: boolean;
}>({ resources: [], loading: true, failed: false });
export function useWebsiteIdentity() {
  const { resources } = useContext(ManifestContext);
  const brand = resources.find((r) => r.kind === "brand");
  return {
    company: brand?.data.company || "Northstar edtech",
    email: brand?.data.contact_email || "tech@northstaracad.com",
    tagline: brand?.data.tagline || "Your knowledge. Your AI.",
  };
}
export function ManagedSite({
  children,
  initialResources,
}: {
  children: ReactNode;
  initialResources?: Resource[];
}) {
  const [state, setState] = useState({
    resources: initialResources || ([] as Resource[]),
    loading: !initialResources,
    failed: false,
  });
  const location = useLocation();
  useEffect(() => {
    let current = true;
    api<{ resources: Resource[] }>("/website/manifest")
      .then((result) => {
        if (current) {
          setState({ ...result, loading: false, failed: false });
          const brand = result.resources.find((r) => r.kind === "brand");
          document.documentElement.dataset.palette =
            brand?.data.palette || "sage";
        }
      })
      .catch(() => {
        if (current) setState({ resources: [], loading: false, failed: true });
      });
    return () => {
      current = false;
    };
  }, [location.pathname]);
  return (
    <ManifestContext.Provider value={state}>
      {children}
    </ManifestContext.Provider>
  );
}
export function ManagedNavigation({ children }: { children?: ReactNode }) {
  const { resources } = useContext(ManifestContext);
  const menu = resources.find((r) => r.kind === "navigation");
  return menu ? (
    <>
      {menu.data.items.map((item: any) => (
        <Link key={item.href} to={item.href}>
          {item.label}
        </Link>
      ))}
    </>
  ) : (
    <>{children}</>
  );
}
export function ManagedForm({ formKey }: { formKey: string }) {
  const identity = useWebsiteIdentity();
  const [enhanced, setEnhanced] = useState(false);
  useEffect(() => setEnhanced(true), []);
  const { resources } = useContext(ManifestContext);
  const form = resources.find((r) => r.kind === "form" && r.key === formKey);
  const [id, setId] = useState(() => crypto.randomUUID()),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [accepted, setAccepted] = useState(false);
  if (!form)
    return (
      <p role="status">
        This form is currently unavailable.{" "}
        <Link to="/contact">Contact the team</Link>.
      </p>
    );
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const answers = Object.fromEntries(
      form!.data.fields.map((f: any) => [
        f.key,
        f.type === "checkbox"
          ? data.get(f.key) === "on"
          : String(data.get(f.key) || ""),
      ]),
    );
    setBusy(true);
    setError("");
    try {
      await api(`/website/forms/${encodeURIComponent(formKey)}/submit`, {
        method: "POST",
        body: JSON.stringify({
          id,
          answers,
          consent: data.get("response_consent") === "on",
          website: data.get("website") || "",
        }),
      });
      setAccepted(true);
      setId(crypto.randomUUID());
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Submission failed. Your answers are preserved.",
      );
    } finally {
      setBusy(false);
    }
  }
  return accepted ? (
    <div role="status" className="console-card">
      <h2>Your request is saved.</h2>
      <p>
        The team can now review your enquiry. This does not confirm a meeting or
        subscribe you to marketing.
      </p>
    </div>
  ) : (
    <form
      className="managed-form console-fields"
      method="post"
      action={`/api/v1/website/forms/${encodeURIComponent(formKey)}/submit`}
      onSubmit={submit}
    >
      <noscript>
        Enable JavaScript to submit, or email {identity.email} directly.
      </noscript>
      <h2>{form.title}</h2>
      {form.data.fields.map((f: any) => (
        <label
          key={f.key}
          className={f.type === "checkbox" ? "checkbox-label" : ""}
        >
          {f.type !== "checkbox" && f.label}
          {f.type === "textarea" ? (
            <textarea
              name={f.key}
              required={!!f.required}
              maxLength={4000}
              rows={4}
            />
          ) : f.type === "select" ? (
            <select name={f.key} required={!!f.required}>
              <option value="">Choose an option</option>
              {f.options.map((v: string) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          ) : (
            <input
              type={
                f.type === "checkbox"
                  ? "checkbox"
                  : f.type === "email"
                    ? "email"
                    : "text"
              }
              name={f.key}
              required={!!f.required}
              maxLength={f.type === "checkbox" ? undefined : 4000}
            />
          )}{" "}
          {f.type === "checkbox" && f.label}
        </label>
      ))}
      <label className="form-trap" aria-hidden="true">
        Website
        <input name="website" tabIndex={-1} autoComplete="off" />
      </label>
      <label className="checkbox-label">
        <input type="checkbox" name="response_consent" required />I agree that
        TalkToBot may use these details to respond to this enquiry.{" "}
        <Link to="/privacy">Privacy notice</Link>
      </label>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      <button className="button dark" disabled={busy || !enhanced}>
        {busy ? "Saving your enquiry…" : "Send enquiry"}
      </button>
    </form>
  );
}
export function ManagedPage({ fallback }: { fallback?: ReactNode }) {
  const { resources, loading, failed } = useContext(ManifestContext);
  const location = useLocation();
  let page = resources.find(
    (r) => r.kind === "page" && r.data.route === location.pathname,
  );
  const collectionMatch = location.pathname.match(
    /^\/collections\/([a-z0-9-]+)(?:\/([a-z0-9-]+))?$/,
  );
  const collection =
    collectionMatch &&
    resources.find(
      (r) => r.kind === "collection" && r.key === collectionMatch[1],
    );
  if (!page && collection) {
    const entries = resources.filter(
      (r) => r.kind === "entry" && r.data.collection_key === collection.key,
    );
    const entry =
      collectionMatch![2] && entries.find((r) => r.key === collectionMatch![2]);
    if (entry)
      page = {
        ...entry,
        data: {
          blocks: [
            { id: "entry-title", type: "hero", title: entry.title, body: "" },
            ...collection.data.fields.map((f: any) => ({
              id: f.key,
              type: "text",
              title: f.label || f.key,
              body: String(entry.data.fields[f.key] ?? ""),
            })),
          ],
        },
      };
    else if (!collectionMatch![2])
      page = {
        ...collection,
        data: {
          blocks: [
            {
              id: "collection-title",
              type: "hero",
              title: collection.title,
              body: "",
            },
            ...entries.map((r) => ({
              id: r.id,
              type: "cta",
              title: r.title,
              body: "",
              label: "Read more",
              href: `/collections/${collection.key}/${r.key}`,
            })),
          ],
        },
      };
  }
  useEffect(() => {
    if (page) {
      document.title = `${page.title} | TalkToBot`;
      document
        .querySelector('link[rel="canonical"]')
        ?.setAttribute("href", `${SITE_URL}${location.pathname}`);
      document
        .querySelector('meta[property="og:title"]')
        ?.setAttribute("content", `${page.title} | TalkToBot`);
      document
        .querySelector('meta[property="og:description"]')
        ?.setAttribute("content", page.data.description || "");
      document
        .querySelector('meta[property="og:url"]')
        ?.setAttribute("content", `${SITE_URL}${location.pathname}`);
      document
        .querySelector('meta[name="description"]')
        ?.setAttribute("content", page.data.description || "");
      let meta = document.querySelector('meta[name="robots"]');
      if (!meta) {
        meta = document.createElement("meta");
        meta.setAttribute("name", "robots");
        document.head.append(meta);
      }
      meta.setAttribute(
        "content",
        page.data.index === false ? "noindex, follow" : "index, follow",
      );
    }
  }, [page, location.pathname]);
  if (!page && fallback) return <>{fallback}</>;
  if (loading)
    return (
      <main className="section-shell policy-page">
        <p role="status">Loading this page…</p>
      </main>
    );
  if (!page)
    return (
      <main className="section-shell policy-page">
        <Eyebrow>{failed ? "TEMPORARILY UNAVAILABLE" : "404"}</Eyebrow>
        <h1>
          {failed ? "Please try again shortly." : "That page isn’t here."}
        </h1>
        <Link className="button dark" to="/">
          Back to the website
        </Link>
      </main>
    );
  return (
    <main className="managed-page">
      {page.data.blocks.map((b: any) => (
        <section
          key={b.id}
          className={`managed-section section-shell managed-${b.type}`}
        >
          <Eyebrow>{page.title}</Eyebrow>
          {b.title &&
            (b.type === "hero" ? <h1>{b.title}</h1> : <h2>{b.title}</h2>)}
          {b.type === "faq" ? (
            <details>
              <summary>{b.title || "More information"}</summary>
              <Markdown text={b.body || ""} />
            </details>
          ) : (
            <Markdown text={b.body || ""} />
          )}{" "}
          {b.type === "form" && <ManagedForm formKey={b.form_key} />}{" "}
          {b.type === "image" && (
            <img
              className="managed-image"
              src={`/api/v1/website/media/${b.asset_id}`}
              alt={b.alt}
              loading="lazy"
            />
          )}
          {b.label && b.href && (
            <Link className="button dark" to={b.href}>
              {b.label}
            </Link>
          )}
        </section>
      ))}
    </main>
  );
}
