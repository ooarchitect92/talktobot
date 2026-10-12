import {
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  FileText,
  Menu,
  MessageCircle,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { Link, Route, Routes, useLocation, useParams } from "react-router-dom";
import { api, APP_URL, SITE_URL, type Post } from "./api";
import { faqs, sections } from "./content";
import { Actions, Dashboard, Eyebrow, Logo, Markdown, Panel } from "./ui";
import {
  ManagedSite,
  ManagedNavigation,
  ManagedPage,
  useWebsiteIdentity,
} from "./managed";
import type { Resource } from "./console";
export type WebsiteBoot = {
  resources?: Resource[];
  posts?: Post[];
  post?: Post | null;
  failedPath?: string;
};
const WebsiteData = createContext<WebsiteBoot>({});

function Metadata({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  const location = useLocation();
  useEffect(() => {
    document.title = `${title} | TalkToBot`;
    document
      .querySelector('meta[name="robots"]')
      ?.setAttribute(
        "content",
        title === "Page not found" ? "noindex, follow" : "index, follow",
      );
    const meta = document.querySelector('meta[name="description"]');
    meta?.setAttribute(
      "content",
      description ||
        "Build AI bots powered by your business knowledge with TalkToBot.",
    );
    let canonical = document.querySelector(
      'link[rel="canonical"]',
    ) as HTMLLinkElement | null;
    if (!canonical) {
      canonical = document.createElement("link");
      canonical.rel = "canonical";
      document.head.append(canonical);
    }
    canonical.href = `${SITE_URL}${location.pathname}`;
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [title, description, location.pathname]);
  return null;
}
function Header() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location]);
  return (
    <header className="site-header">
      <div className="nav-wrap">
        <Logo />
        <button
          className="mobile-toggle"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
        <nav className={open ? "open" : ""} aria-label="Main navigation">
          <ManagedNavigation>
            <a href="/#product">Product</a>
            <a href="/#industries">Solutions</a>
            <a href="/#features">Features</a>
            <Link to="/pricing">Pricing</Link>
            <a href="/#white-label">White label</a>
            <Link to="/blog">
              Resources <ChevronDown size={12} />
            </Link>
          </ManagedNavigation>
          <div className="nav-auth">
            <a href={`${APP_URL}/login`}>
              Log in <ArrowUpRight size={13} />
            </a>
            <a className="button dark small" href={`${APP_URL}/signup`}>
              Get started <ArrowUpRight size={14} />
            </a>
          </div>
        </nav>
      </div>
    </header>
  );
}
function Footer() {
  const identity = useWebsiteIdentity();
  return (
    <footer className="site-footer">
      <div className="footer-top">
        <div className="footer-brand">
          <Logo dark />
          <p>
            {identity.tagline}
            <br />
            Bring better conversations to your business, wherever your customers
            are.
          </p>
          <Link className="button footer-button" to="/contact">
            Let’s talk <ArrowUpRight size={16} />
          </Link>
        </div>
        <div>
          <h4>Product</h4>
          <a href="/#bots">Bots & workspace</a>
          <a href="/#channels">WhatsApp channel</a>
          <a href="/#knowledge">Knowledge & RAG</a>
          <a href="/#health">Analytics</a>
          <Link to="/pricing">Pricing</Link>
        </div>
        <div>
          <h4>Resources</h4>
          <Link to="/blog">Blog & guides</Link>
          <a href="/feed.xml">Journal RSS</a>
          <a href={`${APP_URL}/help`}>Help center</a>
          <Link to="/contact">Book a demo</Link>
          <Link to="/admin">Website editor</Link>
        </div>
        <div>
          <h4>Company</h4>
          <span>{identity.company}</span>
          <a href={`mailto:${identity.email}`}>{identity.email}</a>
          <Link to="/privacy">Privacy</Link>
          <Link to="/terms">Terms</Link>
          <Link to="/security">Security</Link>
          <Link to="/contact">Contact us</Link>
          <a href={`${APP_URL}/login`}>Log in</a>
        </div>
      </div>
      <div className="footer-bottom">
        <span>
          © {new Date().getFullYear()} {identity.company}. TalkToBot. All rights
          reserved.
        </span>
        <span>
          Made for useful conversations. <span className="footer-star">✦</span>
        </span>
      </div>
    </footer>
  );
}
function ChatPreview() {
  const [question, setQuestion] = useState("");
  const answers: Record<string, string> = {
    "What is TalkToBot?":
      "TalkToBot helps you create AI assistants powered by your business documents and FAQs. You can manage conversations, collect leads, and connect supported channels.",
    "Which channels can I use?":
      "Start with the website widget or WhatsApp. Additional channels need provider configuration in your workspace.",
    "Can I connect my CRM?":
      "Yes. Configure a supported CRM connector in your workspace, map your fields, and review lead delivery status.",
  };
  return (
    <div className="site-chat">
      <div className="site-chat-top">
        <span className="chat-avatar">✦</span>
        <div>
          <strong>Meet your next assistant</strong>
          <small>
            <span className="tiny-led" /> Product walkthrough · illustrative
            demo
          </small>
        </div>
      </div>
      <p className="bubble bot">
        Hi! I’m a TalkToBot example assistant. What would you like to explore?
      </p>
      <div className="suggestions">
        {Object.keys(answers).map((q) => (
          <button
            key={q}
            className={q === question ? "selected" : ""}
            onClick={() => setQuestion(q)}
          >
            {q}
            <ArrowUpRight size={13} />
          </button>
        ))}
      </div>
      {question && (
        <div className="demo-answer" aria-live="polite">
          <Sparkles size={16} />
          <p>{answers[question]}</p>
        </div>
      )}
      <Link to="/contact" className="chat-demo-link">
        See a demo with your knowledge <ArrowRight size={14} />
      </Link>
    </div>
  );
}
function Home() {
  const [industry, setIndustry] = useState("Retail & e-commerce");
  return (
    <>
      <Metadata title="Build AI bots that work for your business" />
      <section className="hero">
        <Eyebrow>AI BOT PLATFORM</Eyebrow>
        <h1>
          BUILD AI BOTS THAT WORK
          <br />
          FOR <span>YOUR BUSINESS.</span>
        </h1>
        <p className="hero-copy">
          Your knowledge. Your systems. Your channels.
          <br />
          One AI assistant, built for real conversations.
        </p>
        <Actions />
        <div className="hero-proof">
          <span>
            <ShieldCheck size={14} /> Grounded in your knowledge
          </span>
          <i />
          <span>Built around your business</span>
        </div>
        <Dashboard />
        <div className="hero-caption">
          <span>LESS REPETITION. MORE CONVERSATION.</span>
          <span>
            Everything your team needs, in one workspace{" "}
            <ArrowUpRight size={13} />
          </span>
        </div>
      </section>
      <section className="workflow section-shell" id="product">
        <div className="section-heading centered">
          <Eyebrow>FROM KNOWLEDGE TO CONVERSATION</Eyebrow>
          <h2>
            How TalkToBot works<span>.</span>
          </h2>
          <p>
            Give your knowledge a voice.
            <br />
            Build, connect, and improve in four considered steps.
          </p>
        </div>
        <div className="workflow-path">
          {[
            [
              "Add knowledge",
              "Bring your documents, website content, policies, and FAQs into one place.",
              "YOUR SOURCES",
            ],
            [
              "Build your AI",
              "Set its purpose, voice, boundaries, and the knowledge it should use.",
              "YOUR ASSISTANT",
            ],
            [
              "Connect your channels",
              "Deploy to your website or a supported messaging channel.",
              "YOUR CUSTOMERS",
            ],
            [
              "Monitor & improve",
              "Review conversations, find knowledge gaps, and refine the experience.",
              "YOUR FEEDBACK",
            ],
          ].map(([title, text, label], i) => (
            <div className={`workflow-step step-${i}`} key={title}>
              <span className="step-dot" />
              <div>
                <div className="step-heading">
                  <h3>{title}</h3>
                  <span>{label}</span>
                </div>
                <p>{text}</p>
              </div>
              <strong>0{i + 1}</strong>
            </div>
          ))}
        </div>
      </section>
      <section className="features section-shell" id="features">
        <div className="section-heading centered">
          <Eyebrow>THE BUSINESS CONVERSATION PLATFORM</Eyebrow>
          <h2>
            Intelligent bots.
            <br />
            Connected business.
            <br />
            <span>Considered experiences.</span>
          </h2>
          <p>The building blocks for an assistant that works with your team.</p>
        </div>
        {sections.map((s, i) => (
          <div
            className={`feature-row ${i % 2 ? "reverse" : ""}`}
            id={s.id}
            key={s.id}
          >
            <div className="feature-copy">
              <div className={`feature-index ${s.accent}`}>
                {s.n} / {s.label}
              </div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
              <ul>
                {s.bullets.map((b) => (
                  <li key={b}>
                    <Check size={15} />
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
              {s.id === "white-label" ? (
                <Link className="text-link" to="/contact?type=white-label">
                  Explore the partner program <ArrowUpRight size={15} />
                </Link>
              ) : (
                <a className="text-link" href={`${APP_URL}/signup`}>
                  Explore in your workspace <ArrowUpRight size={15} />
                </a>
              )}
            </div>
            <Panel kind={s.panel} />
          </div>
        ))}
      </section>
      <section className="industries section-shell" id="industries">
        <div className="section-heading centered">
          <Eyebrow>MADE FOR YOUR WORLD</Eyebrow>
          <h2>
            Built for your industry<span>.</span>
          </h2>
          <p>Different businesses. The same need for better conversations.</p>
        </div>
        <div className="industry-tabs" aria-label="Industry examples">
          {[
            "Retail & e-commerce",
            "Education & coaching",
            "Services & agencies",
          ].map((name) => (
            <button
              className={industry === name ? "active" : ""}
              key={name}
              onClick={() => setIndustry(name)}
            >
              {name}
            </button>
          ))}
        </div>
        <div className="industry-showcase">
          <div
            className={`industry-art ${industry.startsWith("Retail") ? "retail" : industry.startsWith("Education") ? "education" : "agency"}`}
          >
            <div className="industry-art-lines" />
            <div className="industry-art-object">
              <span>✦</span>
              <strong>
                {industry.startsWith("Retail")
                  ? "A better customer experience."
                  : industry.startsWith("Education")
                    ? "Knowledge, ready to teach."
                    : "Your expertise. Always available."}
              </strong>
            </div>
            <div className="industry-chat">
              <span>EXAMPLE CONVERSATION</span>
              <p>
                {industry.startsWith("Retail")
                  ? "How do I find your return policy?"
                  : industry.startsWith("Education")
                    ? "Where can I review the course material?"
                    : "Can you help me choose the right service?"}
              </p>
              <div>
                <span>✦</span>
                {industry.startsWith("Retail")
                  ? "Let me find the answer in the store’s approved policies."
                  : industry.startsWith("Education")
                    ? "I can help you find the relevant lesson in your approved course content."
                    : "Tell me what you’re looking for. I’ll help you find the right next step."}
              </div>
            </div>
            <span className="industry-label">
              {industry}
              <ArrowUpRight size={19} />
            </span>
          </div>
          <div className="industry-detail">
            <span className="feature-index">KNOWLEDGE WITH A PURPOSE</span>
            <h3>
              {industry.startsWith("Retail")
                ? "Help customers shop with confidence."
                : industry.startsWith("Education")
                  ? "An assistant trained on your institute’s content."
                  : "Be there for your next customer."}
            </h3>
            <p>
              {industry.startsWith("Retail")
                ? "Answer product questions, explain policies, and hand customers over to your team when they need a person."
                : industry.startsWith("Education")
                  ? "Help students navigate approved learning material while keeping content ownership and access in your workspace."
                  : "Answer service questions, understand customer needs, and capture qualified enquiries for your team."}
            </p>
            <Link className="text-link" to="/contact">
              Discuss your use case <ArrowUpRight size={16} />
            </Link>
          </div>
        </div>
      </section>
      <BlogPreview />
      <section className="faq section-shell" id="faq">
        <div className="section-heading centered">
          <Eyebrow>A FEW GOOD QUESTIONS</Eyebrow>
          <h2>
            Frequently asked questions<span>.</span>
          </h2>
        </div>
        <div className="faq-list">
          {faqs.map(([q, a]) => (
            <details key={q}>
              <summary>
                {q}
                <Plus size={18} />
              </summary>
              <p>{a}</p>
            </details>
          ))}
        </div>
      </section>
      <section className="final-cta section-shell">
        <Eyebrow>READY FOR A BETTER CONVERSATION?</Eyebrow>
        <h2>
          YOUR KNOWLEDGE IS ALREADY
          <br />
          VALUABLE.
          <br />
          <span>MAKE IT INTELLIGENT.</span>
        </h2>
        <p>
          Turn what your organization knows into an assistant
          <br />
          that helps your customers—and your team—move forward.
        </p>
        <Actions />
        <div className="hero-proof">
          <span>Your sources</span>
          <i />
          <span>Your voice</span>
          <i />
          <span>Your business</span>
        </div>
      </section>
    </>
  );
}
function BlogPreview() {
  const boot = useContext(WebsiteData);
  const [posts, setPosts] = useState<Post[]>(boot.posts || []);
  useEffect(() => {
    api<Post[]>("/website/posts?limit=3")
      .then(setPosts)
      .catch(() => {});
  }, []);
  return (
    <section className="blog-preview section-shell">
      <div className="split-heading">
        <div>
          <Eyebrow>THE CONVERSATION CONTINUES</Eyebrow>
          <h2>
            Ideas worth sharing<span>.</span>
          </h2>
        </div>
        <Link className="text-link" to="/blog">
          Explore the journal <ArrowUpRight size={17} />
        </Link>
      </div>
      {posts.length ? (
        <div className="post-grid">
          {posts.slice(0, 3).map((p, i) => (
            <PostCard key={p.id} post={p} index={i} />
          ))}
        </div>
      ) : (
        <div className="empty-blog">
          <FileText size={26} />
          <h3>A home for guides, ideas, and product stories.</h3>
          <p>Our editorial team is preparing the first articles.</p>
          <Link className="text-link" to="/blog">
            Visit the journal <ArrowUpRight size={16} />
          </Link>
        </div>
      )}
    </section>
  );
}
function PostCard({ post, index = 0 }: { post: Post; index?: number }) {
  return (
    <Link className="post-card" to={`/blog/${post.slug}`}>
      <div className={`post-cover cover-${index % 3}`}>
        {post.cover ? (
          <img src={post.cover} alt={post.cover_alt} />
        ) : (
          <>
            <span>{post.category}</span>
            <Sparkles size={64} strokeWidth={1} />
            <span className="cover-caption">THE TALKTOBOT JOURNAL</span>
          </>
        )}
      </div>
      <div className="post-meta">
        {post.category}
        <span>·</span>
        {Math.max(1, Math.ceil(post.body.split(/\s+/).length / 200))} min read
      </div>
      <h3>{post.title}</h3>
      <p>{post.excerpt}</p>
      <span className="text-link">
        Read the story <ArrowUpRight size={16} />
      </span>
    </Link>
  );
}
function Blog() {
  const boot = useContext(WebsiteData);
  const [posts, setPosts] = useState<Post[]>(boot.posts || []);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All stories");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(!boot.posts);
  const [more, setMore] = useState((boot.posts?.length || 0) >= 200),
    [loadingMore, setLoadingMore] = useState(false);
  useEffect(() => {
    api<Post[]>("/website/posts")
      .then((rows) => {
        setPosts(rows);
        setMore(rows.length === 200);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  const filtered = posts.filter(
    (p) =>
      (category === "All stories" || p.category === category) &&
      `${p.title} ${p.excerpt} ${p.tags.join(" ")}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <main className="blog-page section-shell">
      <Metadata
        title="The journal"
        description="Guides, ideas, and practical advice for building business AI assistants."
      />
      <div className="section-heading">
        <Eyebrow>THE TALKTOBOT JOURNAL</Eyebrow>
        <h1>
          Better questions.
          <br />
          <span>Better conversations.</span>
        </h1>
        <p>
          Practical guides, thoughtful ideas, and the knowledge behind useful
          AI.
        </p>
      </div>
      <div className="blog-controls">
        <div className="industry-tabs">
          {["All stories", ...new Set(posts.map((p) => p.category))].map(
            (c) => (
              <button
                key={c}
                className={category === c ? "active" : ""}
                onClick={() => setCategory(c)}
              >
                {c}
              </button>
            ),
          )}
        </div>
        <label className="blog-search">
          <Search size={16} />
          <input
            aria-label="Search articles"
            placeholder="Find a story…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>
      {loading ? (
        <p className="state-message" role="status">
          Loading the journal…
        </p>
      ) : error ? (
        <p className="error-message" role="alert">
          The journal is temporarily unavailable. Please try again later.
        </p>
      ) : filtered.length ? (
        <div className="post-grid">
          {filtered.map((p, i) => (
            <PostCard post={p} index={i} key={p.id} />
          ))}
        </div>
      ) : (
        <div className="empty-blog">
          <FileText size={30} />
          <h3>
            {posts.length
              ? "No stories match your search."
              : "The first stories are on their way."}
          </h3>
          <p>
            {posts.length
              ? "Try another topic or clear your search."
              : "Come back for practical guides and product updates."}
          </p>
        </div>
      )}
      {more && (
        <button
          className="button light"
          disabled={loadingMore}
          onClick={() => {
            setLoadingMore(true);
            void api<Post[]>(`/website/posts?limit=200&offset=${posts.length}`)
              .then((rows) => {
                setPosts((current) => [
                  ...current,
                  ...rows.filter(
                    (row) =>
                      !current.some((existing) => existing.id === row.id),
                  ),
                ]);
                setMore(rows.length === 200);
              })
              .catch((e) => setError(e.message))
              .finally(() => setLoadingMore(false));
          }}
        >
          {loadingMore ? "Loading more stories…" : "Load more stories"}
        </button>
      )}
    </main>
  );
}
function Article() {
  const { slug } = useParams();
  const boot = useContext(WebsiteData);
  const location = useLocation();
  const [post, setPost] = useState<Post | null>(
    boot.post && boot.post.slug === slug ? boot.post : null,
  );
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    if (post?.slug !== slug) setPost(null);
    setError("");
    api<Post>(`/website/posts/${encodeURIComponent(slug || "")}`)
      .then((value) => {
        if (current) setPost(value);
      })
      .catch((e) => {
        if (current) setError(e.message);
      });
    return () => {
      current = false;
    };
  }, [slug]);
  if (error || boot.failedPath === location.pathname) return <NotFound />;
  if (!post)
    return (
      <main className="article section-shell">
        <p role="status">Loading article…</p>
      </main>
    );
  return (
    <main className="article section-shell">
      <Metadata
        title={post.seo_title || post.title}
        description={post.seo_description || post.excerpt}
      />
      <Link className="text-link" to="/blog">
        ← Back to the journal
      </Link>
      <div className="article-heading">
        <Eyebrow>{post.category.toUpperCase()}</Eyebrow>
        <h1>{post.title}</h1>
        <p>{post.excerpt}</p>
        <div className="article-byline">
          <span className="chat-avatar">✦</span>
          <span>
            {post.author}
            <small>
              {post.published_at
                ? new Date(post.published_at).toLocaleDateString("en-IN", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })
                : ""}{" "}
              · {Math.max(1, Math.ceil(post.body.split(/\s+/).length / 200))}{" "}
              min read
            </small>
          </span>
        </div>
      </div>
      {post.cover && (
        <img className="article-cover" src={post.cover} alt={post.cover_alt} />
      )}
      <Markdown text={post.body} />
      <div className="article-tags">
        {post.tags.map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
      <div className="article-cta">
        <h3>Put your knowledge to work.</h3>
        <Actions />
      </div>
    </main>
  );
}
function Contact() {
  const identity = useWebsiteIdentity();
  const [enhanced, setEnhanced] = useState(false);
  useEffect(() => setEnhanced(true), []);
  const location = useLocation();
  const kind =
    new URLSearchParams(location.search).get("type") === "white-label"
      ? "white-label"
      : "demo";
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [accepted, setAccepted] = useState("");
  const id = useRef(crypto.randomUUID());
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(e.currentTarget);
    try {
      const result = await api<{ id: string }>("/website/inquiries", {
        method: "POST",
        body: JSON.stringify({
          id: id.current,
          name: data.get("name"),
          email: data.get("email"),
          company: data.get("company"),
          message: data.get("message"),
          kind,
          consent: data.get("consent") === "on",
          website: data.get("website"),
        }),
      });
      setAccepted(result.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to submit");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="contact-page section-shell">
      <Metadata title="Let’s talk" />
      <div className="contact-copy">
        <Eyebrow>A CONVERSATION STARTS HERE</Eyebrow>
        <h1>
          Your business.
          <br />
          Your knowledge.
          <br />
          <span>Let’s connect.</span>
        </h1>
        <p>
          Tell us what you’re building. We’ll help you explore how an assistant
          can fit your customers, channels, and team.
        </p>
        <div className="contact-points">
          <span>
            <Check size={17} /> Discuss your use case
          </span>
          <span>
            <Check size={17} /> Explore a product walkthrough
          </span>
          <span>
            <Check size={17} /> Plan your channel and CRM connections
          </span>
        </div>
        <ChatPreview />
        <p>
          Contact {identity.company} directly at{" "}
          <a href={`mailto:${identity.email}`}>{identity.email}</a>.
        </p>
      </div>
      <div className="contact-form-wrap">
        {accepted ? (
          <div className="accepted" role="status">
            <span>
              <Check size={28} />
            </span>
            <h2>Your enquiry is saved.</h2>
            <p>
              The team can now review your request. This confirms receipt; a
              meeting has not yet been scheduled.
            </p>
            <small>Reference: {accepted}</small>
            <Link className="button dark" to="/">
              Back to the website <ArrowUpRight size={16} />
            </Link>
          </div>
        ) : (
          <form
            method="post"
            action="/api/v1/website/inquiries"
            onSubmit={submit}
          >
            <noscript>
              Enable JavaScript to submit this form, or email {identity.email}{" "}
              directly.
            </noscript>
            <span className="feature-index">
              {kind === "white-label" ? "PARTNER ENQUIRY" : "BOOK A DEMO"}
            </span>
            <h2>Let’s find your next step.</h2>
            <p>A few details help us make the conversation useful.</p>
            <label>
              Your name
              <input
                name="name"
                required
                minLength={2}
                maxLength={100}
                autoComplete="name"
                placeholder="Your full name"
              />
            </label>
            <label>
              Work email
              <input
                name="email"
                type="email"
                required
                maxLength={254}
                autoComplete="email"
                placeholder="you@company.com"
              />
            </label>
            <label>
              Company
              <input
                name="company"
                maxLength={150}
                autoComplete="organization"
                placeholder="Your company or organization"
              />
            </label>
            <label>
              What would you like to do?
              <textarea
                name="message"
                required
                minLength={10}
                maxLength={4000}
                rows={5}
                placeholder="Tell us about your customers, knowledge, and channels…"
              />
            </label>
            <label className="honeypot" aria-hidden="true">
              Website
              <input name="website" tabIndex={-1} autoComplete="off" />
            </label>
            <label className="checkbox-label">
              <input name="consent" type="checkbox" required />
              <span>
                I agree that TalkToBot may use these details to respond to this
                enquiry. Read the <Link to="/privacy">privacy notice</Link>.
              </span>
            </label>
            {error && (
              <p className="error-message" role="alert">
                {error}
              </p>
            )}
            <button disabled={busy || !enhanced} className="button dark">
              {busy ? "Saving your enquiry…" : "Send enquiry"}
              <ArrowUpRight size={17} />
            </button>
            <small className="form-note">
              We store your request for the team. This form does not subscribe
              you to marketing emails.
            </small>
          </form>
        )}
      </div>
    </main>
  );
}
function Pricing() {
  return (
    <main className="pricing-page section-shell">
      <Metadata title="Find your fit" />
      <div className="section-heading centered">
        <Eyebrow>A PLATFORM THAT FITS YOUR BUSINESS</Eyebrow>
        <h1>
          Start with what
          <br />
          <span>you need.</span>
        </h1>
        <p>
          Talk to us about your workload and channels.
          <br />
          Public plan prices and trial terms are not currently published.
        </p>
      </div>
      <div className="pricing-grid">
        {[
          [
            "For your business",
            "Build an assistant for your customers.",
            [
              "Business knowledge sources",
              "Website chat experience",
              "Conversation review",
              "Lead capture",
            ],
          ],
          [
            "For your team",
            "Connect your tools and conversations.",
            [
              "Supported messaging channels",
              "CRM workflows",
              "Workspace permissions",
              "Operational visibility",
            ],
          ],
          [
            "For your brand",
            "Explore a partner experience.",
            [
              "Bot branding controls",
              "Separate client workspaces",
              "Agency use-case review",
              "Domain requirements discussion",
            ],
          ],
        ].map(([title, subtitle, bullets], i) => (
          <div
            className={i === 1 ? "pricing-card featured" : "pricing-card"}
            key={title as string}
          >
            {i === 1 && (
              <span className="pricing-label">CONNECTED BUSINESS</span>
            )}
            <span className="feature-index">0{i + 1}</span>
            <h3>{title as string}</h3>
            <p>{subtitle as string}</p>
            <ul>
              {(bullets as string[]).map((b) => (
                <li key={b}>
                  <Check size={16} />
                  {b}
                </li>
              ))}
            </ul>
            <Link
              className={`button ${i === 1 ? "dark" : "light"}`}
              to={i === 2 ? "/contact?type=white-label" : "/contact"}
            >
              Discuss your setup <ArrowUpRight size={16} />
            </Link>
          </div>
        ))}
      </div>
    </main>
  );
}
function Policy({ kind }: { kind: "privacy" | "terms" | "security" }) {
  const identity = useWebsiteIdentity();
  const text = {
    privacy:
      "# Website privacy notice\nThis notice describes the current website implementation. Company legal details and jurisdiction-specific policy review must be completed before a public production launch.\n\n## Information you submit\nThe enquiry form collects your name, email, optional company, and message so the team can respond. A consent checkbox records your permission for that response. It does not subscribe you to marketing.\n\n## Cookies and measurement\nThis website does not load advertising pixels, third-party analytics, or session replay. The editor uses browser session storage for its sign-in token. Essential server and security logs may be generated when you visit.\n\n## Content and enquiries\nEnquiries are stored in the application database and accessible to authorized website editors. Blog drafts and revisions are not available through the public API. Do not include confidential or regulated information in an enquiry.\n\n## Your requests\nUse the contact form to request access, correction, or removal of enquiry data. Production retention periods, a named privacy contact, and formal rights-handling procedures require business approval before launch.",
    terms:
      "# Website terms\nThis website introduces TalkToBot and provides product guides and an enquiry form. These are implementation-stage terms, pending legal and company review before a public production launch.\n\n## Product information\nIllustrative dashboard numbers and conversations are examples. They do not represent live customer results or service guarantees. Provider integrations require suitable accounts, configuration, and permissions.\n\n## Accounts and commercial terms\nLogin and signup link to the TalkToBot application. Pricing, service commitments, and contractual terms must be agreed separately. Submitting a demo enquiry does not create a purchase or schedule a confirmed meeting.\n\n## Published material\nEditorial content is general product guidance. Do not submit unlawful material, unauthorized personal information, credentials, or content you do not have permission to share.\n\n## Questions\nUse the contact form for questions about the website, commercial terms, or content.",
    security:
      "# Security at the website boundary\nThis page describes implemented controls, not a certification or a guarantee. No SOC 2 certification claim is made.\n\n## Content access\nOnly published blog revisions are returned to public readers. Website editing requires an authenticated, explicitly authorized editor account. Tenant users do not gain publishing access merely by signing up.\n\n## Editorial integrity\nArticle changes use version checks to detect concurrent edits. Saved revisions retain the actor, action, and time. Trash removes an article from public access; restore returns it to draft. There is no automatic blog expiry or permanent purge button.\n\n## Enquiry handling\nRequests are validated, rate limited, and acknowledged only after database commit. Retries with the same submission identifier return the original accepted result.\n\n## Production requirements\nHTTPS, secret rotation, formal data retention, recovery drills, security review, and provider qualification remain required production gates. Contact the team to report a concern without including secrets or exploit payloads in public content.",
  };
  return (
    <main className="policy-page section-shell">
      <Metadata title={kind[0].toUpperCase() + kind.slice(1)} />
      <Eyebrow>TRANSPARENCY MATTERS</Eyebrow>
      <p>
        TalkToBot.io is operated by {identity.company}. For privacy requests,
        commercial questions or security reports, contact{" "}
        <a href={`mailto:${identity.email}`}>{identity.email}</a>.
      </p>
      <Markdown text={text[kind]} />
      <Link className="button light" to="/contact">
        Contact the team <ArrowUpRight size={16} />
      </Link>
    </main>
  );
}
function NotFound() {
  return (
    <main className="not-found section-shell">
      <Metadata title="Page not found" />
      <Eyebrow>404</Eyebrow>
      <h1>
        That conversation
        <br />
        isn’t here.
      </h1>
      <p>The page may have moved, or the article may no longer be published.</p>
      <Link className="button dark" to="/">
        Back to the website <ArrowUpRight size={17} />
      </Link>
    </main>
  );
}
export function Site({ boot = {} }: { boot?: WebsiteBoot }) {
  return (
    <WebsiteData.Provider value={boot}>
      <ManagedSite initialResources={boot.resources}>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <Header />
        <div id="main-content">
          <Routes>
            <Route
              path="/"
              element={
                <ManagedPage
                  fallback={
                    <main>
                      <Home />
                    </main>
                  }
                />
              }
            />
            <Route path="/blog" element={<Blog />} />
            <Route path="/blog/:slug" element={<Article />} />
            <Route
              path="/contact"
              element={<ManagedPage fallback={<Contact />} />}
            />
            <Route
              path="/pricing"
              element={<ManagedPage fallback={<Pricing />} />}
            />
            <Route
              path="/privacy"
              element={<ManagedPage fallback={<Policy kind="privacy" />} />}
            />
            <Route
              path="/terms"
              element={<ManagedPage fallback={<Policy kind="terms" />} />}
            />
            <Route
              path="/security"
              element={<ManagedPage fallback={<Policy kind="security" />} />}
            />
            <Route path="*" element={<ManagedPage />} />
          </Routes>
        </div>
        <Footer />
      </ManagedSite>
    </WebsiteData.Provider>
  );
}
