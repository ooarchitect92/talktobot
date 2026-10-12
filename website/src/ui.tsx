import {
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleHelp,
  Database,
  FileText,
  Globe,
  MessageCircle,
  Plug,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { APP_URL } from "./api";
export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <Link
      className={`logo ${dark ? "inverted" : ""}`}
      to="/"
      aria-label="TalkToBot home"
    >
      <span className="logo-mark">✦</span>
      <span>
        talktobot<span className="logo-dot">.</span>
      </span>
    </Link>
  );
}
export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="eyebrow">
      <span />
      {children}
    </div>
  );
}
export function Actions({ demo = true }: { demo?: boolean }) {
  return (
    <div className="actions">
      <a className="button dark" href={`${APP_URL}/signup`}>
        Get started <ArrowUpRight size={17} />
      </a>
      {demo && (
        <Link className="button light" to="/contact">
          Book a demo <ChevronRight size={16} />
        </Link>
      )}
    </div>
  );
}
export function Panel({ kind }: { kind: string }) {
  return (
    <div className={`product-panel panel-${kind}`}>
      <div className="panel-top">
        <span>
          <span className="tiny-led" />
          {
            (
              {
                capture: "CONVERSATION → CUSTOMER",
                health: "AI OBSERVABILITY & HEALTH CENTER",
                knowledge: "KNOWLEDGE CONNECTORS",
                integrations: "BUSINESS ORCHESTRATION",
                channels: "MULTI-CHANNEL GATEWAY",
                brand: "WHITE LABEL CONTROL CENTER",
              } as Record<string, string>
            )[kind]
          }
        </span>
        <span className="panel-top-right">Illustrative preview</span>
      </div>
      {kind === "capture" && (
        <>
          <div className="capture-grid">
            <div className="mini-chat">
              <div className="mini-chat-header">
                <Sparkles size={16} /> Your business assistant{" "}
                <span className="online">Online</span>
              </div>
              <p className="bubble visitor">
                I’d love to learn more about your platform.
              </p>
              <p className="bubble bot">
                Of course. What does your team need help with?
              </p>
              <p className="bubble visitor">
                Customer support and qualifying new leads.
              </p>
              <p className="bubble bot">
                I can help with that. May I share your details with the team?
              </p>
              <div className="chat-input">
                Type your message… <ArrowUpRight size={15} />
              </div>
            </div>
            <div className="lead-preview">
              <span className="subtle-label">LIVE LEAD CAPTURE</span>
              <h4>Meet your next customer.</h4>
              <div className="lead-field">
                INTEREST<strong>Customer support</strong>
              </div>
              <div className="lead-field">
                WORK EMAIL<strong>hello@example.com</strong>
              </div>
              <div className="lead-field">
                TEAM<strong>Growing business</strong>
              </div>
              <div className="success-block">
                <Check size={16} />
                <span>
                  Details confirmed<small>Ready for your connected CRM</small>
                </span>
              </div>
            </div>
          </div>
          <div className="panel-bottom">
            <span>CRM</span>
            <span>Customer profile</span>
            <span>Analytics</span>
            <span>Webhooks</span>
          </div>
        </>
      )}
      {kind === "health" && (
        <>
          <div className="metric-grid">
            {[
              ["87%", "AI resolution"],
              ["92%", "Knowledge coverage"],
              ["8%", "Human handoffs"],
              ["248", "Conversations"],
            ].map(([value, label]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
                <small>Example data</small>
              </div>
            ))}
          </div>
          <div className="health-grid">
            <div>
              <h5>TOP CUSTOMER QUESTIONS</h5>
              {[
                "What can your product do?",
                "How do I get started?",
                "Can I connect my CRM?",
              ].map((q, i) => (
                <div className="health-line" key={q}>
                  {q}
                  <span>{98 - i * 3}% match</span>
                </div>
              ))}
            </div>
            <div>
              <h5>KNOWLEDGE GAPS</h5>
              {[
                "New return policy",
                "Integration setup",
                "Account permissions",
              ].map((q) => (
                <div className="gap-line" key={q}>
                  <CircleHelp size={12} />
                  {q}
                  <span>Review</span>
                </div>
              ))}
            </div>
          </div>
          <div className="dark-strip">
            MONITOR <span>→</span> IDENTIFY <span>→</span> IMPROVE
          </div>
        </>
      )}
      {kind === "knowledge" && (
        <>
          <div className="source-grid">
            {[
              [Globe, "Website", "Your published pages"],
              [FileText, "Documents", "PDF & Word sources"],
              [CircleHelp, "FAQs", "Questions and answers"],
              [Database, "Business knowledge", "Policies and product guides"],
            ].map(([Icon, name, sub], i) => {
              const I = Icon as typeof Globe;
              return (
                <div className="source-tile" key={i}>
                  <I size={19} />
                  <strong>{name as string}</strong>
                  <small>{sub as string}</small>
                  <span className="source-status">Ready to connect</span>
                </div>
              );
            })}
          </div>
          <div className="grounding">
            <h5>GROUNDED ANSWER PREVIEW</h5>
            <p>What is your refund policy?</p>
            <div>
              <Sparkles size={16} />
              <span>
                Your assistant looks for an answer in your approved business
                knowledge.
              </span>
            </div>
            <small>
              <ShieldCheck size={12} /> Source citations help you review the
              answer.
            </small>
          </div>
          <div className="panel-bottom">
            <span>Documents</span>
            <span>Website content</span>
            <span>FAQs</span>
          </div>
        </>
      )}
      {kind === "integrations" && (
        <>
          <div className="core-node">
            <span className="node-icon">
              <Sparkles size={22} />
            </span>
            <strong>YOUR AI BOT</strong>
            <small>Knowledge + conversation + tools</small>
          </div>
          <div className="connector-lines" />
          <div className="integration-grid">
            {[
              [Users, "CRM", "Create a lead"],
              [Plug, "Business API", "Retrieve information"],
              [Globe, "Website", "Answer a question"],
              [ArrowUpRight, "Webhooks", "Send an event"],
            ].map(([Icon, name, sub], i) => {
              const I = Icon as typeof Users;
              return (
                <div key={i}>
                  <I size={17} />
                  <strong>{name as string}</strong>
                  <small>{sub as string}</small>
                  <span className="source-status">Provider configured</span>
                </div>
              );
            })}
          </div>
          <div className="panel-bottom">
            <span>Scoped credentials</span>
            <span>Delivery history</span>
            <span>Auditable actions</span>
          </div>
        </>
      )}
      {kind === "channels" && (
        <>
          <div className="channel-core">
            <Sparkles size={20} />
            <div>
              <strong>ONE BUSINESS ASSISTANT</strong>
              <small>Shared knowledge. A connected experience.</small>
            </div>
          </div>
          <div className="channels-grid">
            {[
              [Globe, "Website", "Embed on your site"],
              [MessageCircle, "WhatsApp", "Business Cloud API"],
              [Plug, "API", "Connect your product"],
            ].map(([Icon, name, sub], i) => {
              const I = Icon as typeof Globe;
              return (
                <div key={i}>
                  <span className="channel-icon">
                    <I size={23} />
                  </span>
                  <h4>{name as string}</h4>
                  <p>{sub as string}</p>
                  <span className="source-status">
                    Connect in your workspace
                  </span>
                </div>
              );
            })}
          </div>
          <div className="channel-note">
            Manage conversations and handoffs in one place{" "}
            <ArrowUpRight size={14} />
          </div>
        </>
      )}
      {kind === "brand" && (
        <>
          <div className="brand-grid">
            <div>
              <h5>CUSTOM BRAND IDENTITY</h5>
              <div className="lead-field">
                YOUR DOMAIN<strong>ai.yourbusiness.com</strong>
              </div>
              <div className="lead-field">
                BRAND COLORS
                <div className="swatches">
                  <i />
                  <i />
                  <i />
                  <i />
                </div>
              </div>
              <div className="lead-field">
                CLIENT WORKSPACES<strong>Organized. Separate. Yours.</strong>
              </div>
            </div>
            <div className="branded-preview">
              <span className="branded-logo">✦ Apex AI</span>
              <p>Client workspace</p>
              <h4>An experience with your identity.</h4>
              <div className="brand-sparkline">
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
                <i />
              </div>
              <small>Logo, palette, and bot appearance</small>
            </div>
          </div>
          <div className="panel-bottom">
            <span>Your knowledge</span>
            <span>Your brand</span>
            <span>Your clients</span>
          </div>
        </>
      )}
    </div>
  );
}
export function Dashboard() {
  return (
    <div
      className="dashboard-preview"
      aria-label="Illustrative TalkToBot dashboard"
    >
      <aside>
        <Logo />
        <div className="workspace-badge">
          ✦ Your workspace <span>⌄</span>
        </div>
        <span className="subtle-label">WORKSPACE</span>
        {[
          [Globe, "Overview"],
          [Sparkles, "AI agents"],
          [MessageCircle, "Conversations"],
          [Database, "Knowledge"],
          [Users, "Leads"],
          [Plug, "Integrations"],
        ].map(([Icon, label], i) => {
          const I = Icon as typeof Globe;
          return (
            <div className={`dash-nav ${i === 0 ? "active" : ""}`} key={i}>
              <I size={14} />
              {label as string}
            </div>
          );
        })}
        <div className="dash-help">
          <CircleHelp size={15} /> Help center
        </div>
      </aside>
      <div className="dashboard-main">
        <div className="dashboard-bar">
          <span>
            Overview <ChevronRight size={12} />
          </span>
          <span className="search-preview">⌕ Search your workspace</span>
          <span className="avatar">JD</span>
        </div>
        <div className="welcome-banner">
          <div>
            <span className="subtle-label">YOUR BUSINESS. CONNECTED.</span>
            <h3>Hello, Workspace!</h3>
            <p>Good conversations start with great knowledge.</p>
            <span className="mini-button">
              Create your first agent <ArrowUpRight size={12} />
            </span>
          </div>
          <div className="orb">
            <Sparkles size={60} />
            <span />
            <i />
          </div>
        </div>
        <div className="dashboard-metrics">
          {[
            ["12", "Active agents"],
            ["248", "Conversations"],
            ["32", "Captured leads"],
            ["92%", "Knowledge coverage"],
          ].map(([value, label]) => (
            <div key={label}>
              <span className="metric-icon">
                <TrendingUp size={15} />
              </span>
              <strong>{value}</strong>
              <span>{label}</span>
              <small>Illustrative data</small>
            </div>
          ))}
        </div>
        <div className="dashboard-lower">
          <div>
            <h5>Conversation activity</h5>
            <div className="chart-bars">
              {[
                25, 40, 35, 68, 54, 72, 48, 85, 70, 90, 60, 96, 74, 80, 98, 65,
                88, 72, 94, 82,
              ].map((h, i) => (
                <i key={i} style={{ height: `${h}%` }} />
              ))}
            </div>
          </div>
          <div className="agent-preview">
            <h5>Your AI assistants</h5>
            <div>
              <span>✦</span>
              <p>
                Customer support<small>Website · Knowledge connected</small>
              </p>
              <b>Ready</b>
            </div>
            <div>
              <span>✦</span>
              <p>
                Sales assistant<small>Lead capture · CRM configured</small>
              </p>
              <b>Ready</b>
            </div>
          </div>
        </div>
      </div>
      <span className="preview-label">Product illustration · sample data</span>
    </div>
  );
}
export function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown">
      {text.split(/\n\s*\n/).map((block, i) => {
        if (block.startsWith("### ")) return <h3 key={i}>{block.slice(4)}</h3>;
        if (block.startsWith("## ")) return <h2 key={i}>{block.slice(3)}</h2>;
        if (block.startsWith("# ")) return <h2 key={i}>{block.slice(2)}</h2>;
        if (block.split("\n").every((line) => line.startsWith("- ")))
          return (
            <ul key={i}>
              {block.split("\n").map((line, j) => (
                <li key={j}>{line.slice(2)}</li>
              ))}
            </ul>
          );
        if (block.startsWith("> "))
          return <blockquote key={i}>{block.slice(2)}</blockquote>;
        return (
          <p key={i}>
            {block.split("\n").map((line, j) => (
              <span key={j}>
                {j > 0 && <br />}
                {line}
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
