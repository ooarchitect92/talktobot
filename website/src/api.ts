export interface Post {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  body: string;
  author: string;
  category: string;
  tags: string[];
  cover: string;
  cover_alt: string;
  status: "draft" | "published" | "trashed";
  version: number;
  published_at: string | null;
  updated_at: string;
  seo_title: string;
  seo_description: string;
  workflow_status: string;
  scheduled_at: string | null;
  editorial_timezone: string;
}
export interface Inquiry {
  id: string;
  name: string;
  email: string;
  company: string;
  message: string;
  kind: string;
  created_at: string;
}
function runtimeOrigins(): { appUrl?: string; siteUrl?: string } {
  if (typeof document === 'undefined') return {};
  try { return JSON.parse(document.getElementById('website-runtime')?.textContent || '{}'); }
  catch { return {}; }
}
const runtime = runtimeOrigins();
export let APP_URL = (
  runtime.appUrl ||
  import.meta.env.VITE_APP_URL || "http://localhost:3100"
).replace(/\/$/, "");
export let SITE_URL = (
  runtime.siteUrl ||
  import.meta.env.VITE_SITE_URL || (typeof window !== "undefined" ? window.location.origin : "http://localhost:3300")
).replace(/\/$/, "");
export function configureWebsiteOrigins(appUrl: string, siteUrl: string) {
  APP_URL = appUrl.replace(/\/$/, '');
  SITE_URL = siteUrl.replace(/\/$/, '');
}
const KEY = "talktobot.website.editor";
let inMemoryEditor: string | null = null;
let staffRoles: string[] = [];
export function editorRoles(): string[] { return staffRoles; }
export async function checkEditorAccess(): Promise<string[]> {
  const access = await api<{ allowed: boolean; roles: string[] }>('/platform-admin/website/access', {}, true);
  staffRoles = Array.isArray(access.roles) ? access.roles : [];
  return staffRoles;
}
export function editorToken() {
  if (import.meta.env.PROD) return inMemoryEditor;
  return sessionStorage.getItem(KEY);
}
export function setEditorToken(token: string | null) {
  if (!token) staffRoles = [];
  if (import.meta.env.PROD) {
    inMemoryEditor = token;
    sessionStorage.removeItem(KEY);
    return;
  }
  if (token) sessionStorage.setItem(KEY, token);
  else sessionStorage.removeItem(KEY);
}
let refreshFlight: Promise<boolean> | null = null;
export function resumeEditor(): Promise<boolean> {
  if (refreshFlight) return refreshFlight;
  refreshFlight = (async () => {
    try {
      const response = await fetch('/api/v1/auth/refresh', { method: 'POST', credentials: 'include', cache: 'no-store' });
      if (!response.ok) return false;
      const session = await response.json();
      if (typeof session.accessToken !== 'string') return false;
      setEditorToken(session.accessToken);
      return true;
    } catch { return false; }
    finally { refreshFlight = null; }
  })();
  return refreshFlight;
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  admin = false,
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (admin && editorToken())
    headers.set("Authorization", `Bearer ${editorToken()}`);
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    cache: "no-store",
    credentials: "include",
  });
  if (admin && response.status === 401 && retry && await resumeEditor()) {
    return api<T>(path, options, admin, false);
  }
  if (!response.ok) {
    let detail = "Something went wrong. Please try again.";
    try {
      const value = await response.json();
      if (typeof value.detail === "string") detail = value.detail;
      else if (response.status === 422)
        detail = "Check the required fields and file format.";
    } catch {
      /* Non-JSON proxy error */
    }
    if (admin && response.status === 401) {
      setEditorToken(null);
      window.dispatchEvent(new Event("website-auth-expired"));
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
