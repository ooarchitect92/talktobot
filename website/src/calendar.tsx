import { useEffect, useState } from "react";
import { api, type Post } from "./api";
import type { Resource } from "./console";
type Item = {
  id: string;
  title: string;
  kind: string;
  state: string;
  at: string;
  task: string;
};
export function ContentCalendar() {
  const [items, setItems] = useState<Item[]>([]),
    [error, setError] = useState(""),
    [filter, setFilter] = useState("");
  useEffect(() => {
    let current = true;
    Promise.all([
      api<Resource[]>("/platform-admin/website/resources", {}, true),
      api<Post[]>("/platform-admin/website/posts", {}, true),
    ])
      .then(([resources, posts]) => {
        if (!current) return;
        setItems(
          [
            ...resources.flatMap((row) => [
              ...(row.scheduled_at
                ? [
                    {
                      id: row.id!,
                      title: row.title,
                      kind: row.kind,
                      state: row.status!,
                      at: row.scheduled_at,
                      task: "Scheduled publication",
                    },
                  ]
                : []),
              ...(row.data.review_date
                ? [
                    {
                      id: `${row.id}-review`,
                      title: row.title,
                      kind: row.kind,
                      state: row.status!,
                      at: row.data.review_date,
                      task: "Editorial review due",
                    },
                  ]
                : []),
            ]),
            ...posts
              .filter((row) => row.scheduled_at)
              .map((row) => ({
                id: row.id,
                title: row.title,
                kind: "article",
                state: row.workflow_status,
                at: row.scheduled_at!,
                task: "Scheduled publication",
              })),
          ].sort((a, b) => a.at.localeCompare(b.at)),
        );
      })
      .catch((e) => {
        if (current) setError(e.message);
      });
    return () => {
      current = false;
    };
  }, []);
  return (
    <div className="console-card">
      <h2>Publication and review calendar</h2>
      <p>
        Dates are displayed in your device timezone. The worker stores instants
        in UTC and rechecks authorization and dependencies when each publication
        runs. Editorial review dates are reminders, never automatic expiry.
      </p>
      <input
        aria-label="Filter content calendar"
        placeholder="Search title, state or date"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      {error ? (
        <p role="alert" className="error-message">
          {error}
        </p>
      ) : (
        <div className="console-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Content</th>
                <th>Task</th>
                <th>Working state</th>
              </tr>
            </thead>
            <tbody>
              {items
                .filter((row) =>
                  `${row.title} ${row.state} ${row.at}`
                    .toLowerCase()
                    .includes(filter.toLowerCase()),
                )
                .map((row) => (
                  <tr key={row.id}>
                    <td>
                      {row.at.length === 10
                        ? row.at
                        : new Date(row.at).toLocaleString()}
                    </td>
                    <td>
                      {row.title}
                      <small>{row.kind}</small>
                    </td>
                    <td>{row.task}</td>
                    <td>{row.state}</td>
                  </tr>
                ))}
            </tbody>
          </table>
          {!items.length && (
            <p>
              No scheduled publications or review dates. Set them in the article
              studio or page and offer editors.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
