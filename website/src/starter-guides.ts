import type { Post } from "./api";

export type GuideDraft = Omit<Post, "id" | "status" | "version" | "updated_at" | "published_at" | "workflow_status" | "scheduled_at" | "editorial_timezone">;
export type StarterGuide = { key: string; title: string; data: Omit<GuideDraft, "title"> };

export function copyStarterGuide(guide: StarterGuide, posts: Pick<Post, "slug">[]): GuideDraft {
  const used = new Set(posts.map(post => post.slug));
  const base = guide.data.slug;
  let slug = base;
  for (let copy = 1; used.has(slug); copy += 1) {
    const suffix = copy === 1 ? "-copy" : `-copy-${copy}`;
    slug = base.slice(0, 120 - suffix.length).replace(/-+$/, "") + suffix;
  }
  return { ...guide.data, title: guide.title, slug, tags: [...guide.data.tags] };
}
