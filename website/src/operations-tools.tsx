import { useState, type ChangeEvent } from "react";
import { api } from "./api";

function download(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
export function OperationsTools() {
  const [resources, setResources] = useState<unknown[]>([]),
    [result, setResult] = useState<any>(null),
    [quality, setQuality] = useState<any>(null),
    [reason, setReason] = useState(""),
    [contacts, setContacts] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState("");
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Operation failed");
    } finally {
      setBusy(false);
    }
  }
  async function readFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    setResult(null);
    setResources([]);
    if (!file) return;
    await run(async () => {
      if (file.size > 4_000_000)
        throw new Error("Import files must be under 4 MB.");
      const data = JSON.parse(await file.text());
      const rows = Array.isArray(data) ? data : data.resources;
      if (!Array.isArray(rows) || !rows.length)
        throw new Error(
          "Use a JSON array of resources, or an object with a resources array.",
        );
      // Remove server-managed publication and identity fields. Every imported row becomes a new private draft.
      const inputs = rows.map((row: any) => ({
        kind: row.kind,
        key: row.key,
        title: row.title || row.document?.title,
        data: row.data || row.document?.data,
      }));
      setResources(inputs);
      setResult(
        await api(
          "/platform-admin/website/imports",
          {
            method: "POST",
            body: JSON.stringify({ resources: inputs, action: "dry-run" }),
          },
          true,
        ),
      );
    });
    e.target.value = "";
  }
  return (
    <div className="console-card">
      <h2>Published content checks</h2>
      <p>
        Check internal destinations, missing search descriptions and overdue
        editorial reviews.
      </p>
      <button
        className="button light small"
        disabled={busy}
        onClick={() =>
          void run(async () =>
            setQuality(await api("/platform-admin/website/quality", {}, true)),
          )
        }
      >
        Run content checks
      </button>
      {quality && (
        <>
          <p>
            {quality.published_resources_checked} published resources checked;{" "}
            {quality.issues.length} issues found.
          </p>
          {quality.issues.map((item: any, i: number) => (
            <p key={i}>
              <strong>{item.title}:</strong> {item.message}
            </p>
          ))}
          <p className="form-note">{quality.scope}</p>
          <button
            className="button light small"
            onClick={() => download(quality, "talktobot-content-checks.json")}
          >
            Export report
          </button>
        </>
      )}
      <hr />
      <h2>Content archives and validated imports</h2>
      <p>
        Exports preserve drafts, publication snapshots, revisions, schedules,
        audit records and media metadata. Store the resulting file securely.
        Media bytes and infrastructure backups require a separate
        object-store/database backup.
      </p>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={contacts}
          onChange={(e) => setContacts(e.target.checked)}
        />{" "}
        Include private enquiries and form answers in this export
      </label>
      <button
        className="button light small"
        disabled={busy}
        onClick={() =>
          void run(async () => {
            download(
              await api(
                `/platform-admin/website/exports?include_contacts=${contacts}`,
                {},
                true,
              ),
              `talktobot-content-${new Date().toISOString().slice(0, 10)}.json`,
            );
            setNotice("Archive downloaded with a SHA-256 integrity checksum.");
          })
        }
      >
        Export content archive
      </button>
      <hr />
      <h3>Import new resources as drafts</h3>
      <p>
        Validation checks schemas and duplicate keys before any write. Importing
        never overwrites or publishes existing content. Review dependencies
        before approval.
      </p>
      <label>
        Resource JSON file
        <input
          type="file"
          accept=".json,application/json"
          disabled={busy}
          onChange={(e) => void readFile(e)}
        />
      </label>
      {result && (
        <>
          <p>
            {result.count} resources validated.{" "}
            {result.can_apply
              ? "Ready to import as private drafts."
              : "Resolve the following conflicts."}
          </p>
          {result.diagnostics.map((message: string) => (
            <p key={message} role="alert">
              {message}
            </p>
          ))}
          <label>
            Import reason
            <input
              value={reason}
              maxLength={500}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <button
            className="button dark small"
            disabled={busy || !result.can_apply || reason.trim().length < 3}
            onClick={() =>
              void run(async () => {
                const outcome = await api<any>(
                  "/platform-admin/website/imports",
                  {
                    method: "POST",
                    body: JSON.stringify({
                      resources,
                      action: "apply",
                      checksum: result.checksum,
                      reason,
                    }),
                  },
                  true,
                );
                setNotice(
                  `${outcome.created.length} private drafts imported. Open their console sections to review them.`,
                );
                setResult(null);
                setResources([]);
              })
            }
          >
            Import validated drafts
          </button>
        </>
      )}
      {busy && <p role="status">Working…</p>}
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="console-notice" role="status">
          {notice}
        </p>
      )}
    </div>
  );
}
