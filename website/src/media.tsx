import { useEffect, useState, type FormEvent } from "react";
import { api, editorToken } from "./api";

export function MediaPreview({ id, alt }: { id: string; alt: string }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let owned = "",
      active = true;
    fetch(`/api/v1/platform-admin/website/media/${id}/preview`, {
      headers: { Authorization: `Bearer ${editorToken()}` },
      cache: "no-store",
    })
      .then((response) => {
        if (!response.ok) throw new Error("Preview unavailable");
        return response.blob();
      })
      .then((blob) => {
        if (active) {
          owned = URL.createObjectURL(blob);
          setUrl(owned);
        }
      })
      .catch(() => setUrl(""));
    return () => {
      active = false;
      if (owned) URL.revokeObjectURL(owned);
    };
  }, [id]);
  return url ? (
    <img className="media-preview" src={url} alt={alt} />
  ) : (
    <p>Private preview unavailable.</p>
  );
}
export function MediaLibrary() {
  const [rows, setRows] = useState<any[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  const load = () =>
    api<any[]>("/platform-admin/website/media", {}, true).then(setRows);
  useEffect(() => {
    void load().catch((e) => setError(e.message));
  }, []);
  async function upload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget,
      data = new FormData(form),
      file = data.get("image") as File;
    if (!file?.size || file.size > 2_000_000) {
      setError("Upload PNG, JPEG or WebP below 2 MB.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const image = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      await api(
        "/platform-admin/website/media",
        {
          method: "POST",
          body: JSON.stringify({
            image,
            title: data.get("title"),
            alt: data.get("alt"),
            rights: data.get("rights"),
            ai_generated: data.get("ai_generated") === "on",
            provenance: data.get("provenance") || "",
          }),
        },
        true,
      );
      await load();
      form.reset();
      setNotice(
        "Image validated and stored. It remains private until used in published content.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <form className="console-card console-fields" onSubmit={upload}>
        <h2>Upload a licensed image</h2>
        <label>
          Image file
          <input
            type="file"
            name="image"
            accept="image/png,image/jpeg,image/webp"
            required
          />
        </label>
        <label>
          Media title
          <input name="title" required minLength={3} maxLength={180} />
        </label>
        <label>
          Default alternative text
          <input name="alt" required maxLength={250} />
        </label>
        <label>
          Rights and permission record
          <textarea
            name="rights"
            required
            minLength={5}
            maxLength={1000}
            placeholder="Source, licence or permission, and accountable owner"
          />
        </label>
        <label className="checkbox-label">
          <input name="ai_generated" type="checkbox" />
          AI-generated source
        </label>
        <label>
          Provenance
          <input
            name="provenance"
            maxLength={1000}
            placeholder="Creation/source reference and required disclosures"
          />
        </label>
        <button className="button dark" disabled={busy}>
          {busy ? "Validating and storing…" : "Upload image"}
        </button>
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
        <p>
          Actual image bytes are checked and re-encoded into bounded WebP
          versions with private metadata stripped. Rights and AI provenance are
          retained separately. Source files are never executed.
        </p>
      </form>
      <div className="media-grid">
        {rows.map((row) => (
          <article className="console-card" key={row.id}>
            <MediaPreview id={row.id} alt={row.alt} />
            <h3>{row.title}</h3>
            <p>
              {row.width} × {row.height} · {row.status}
            </p>
            <p>{row.rights}</p>
            <small>
              {row.ai_generated
                ? "AI-generated source"
                : "Source provenance recorded"}
            </small>
            <code className="console-url">{row.id}</code>
            <button
              className="button light small"
              onClick={() =>
                void navigator.clipboard
                  .writeText(row.url)
                  .then(() =>
                    setNotice(
                      "Media URL copied. Add it as an article cover, or select this asset in an image section.",
                    ),
                  )
              }
            >
              Copy cover URL
            </button>
          </article>
        ))}
      </div>
      {!rows.length && <p>No media assets uploaded yet.</p>}
    </>
  );
}
