import type { Post } from "./api";
export const sections = [
  {
    id: "bots",
    n: "01",
    label: "AI BOTS",
    title: "Turn every conversation into useful business data.",
    text: "Ask the right questions, collect customer information, and turn conversations into structured leads—without making people fill out another long form.",
    bullets: [
      "Conversational lead capture with clear confirmation",
      "Keep customer context together with the conversation",
      "Route qualified enquiries to your connected CRM",
    ],
    panel: "capture",
    accent: "mint",
  },
  {
    id: "health",
    n: "02",
    label: "AI HEALTH",
    title: "See how your AI is performing.",
    text: "Review real conversations, find unanswered questions, and see where your assistant needs better knowledge or a human handoff.",
    bullets: [
      "Find knowledge gaps in customer questions",
      "Review answers, sentiment, and conversation outcomes",
      "Give your team a clear path to improve",
    ],
    panel: "health",
    accent: "blue",
  },
  {
    id: "knowledge",
    n: "03",
    label: "AI TRAINING",
    title: "One hub for all your knowledge.",
    text: "Bring your website, documents, FAQs, and policies together so your AI bot can answer with information specific to your business.",
    bullets: [
      "Upload PDF, Word, and text documents",
      "Add website content and question-and-answer pairs",
      "Review source citations and keep content current",
    ],
    panel: "knowledge",
    accent: "violet",
  },
  {
    id: "integrations",
    n: "04",
    label: "API + INTEGRATIONS",
    title: "Connect your AI to the systems you already use.",
    text: "Bring your assistant into your existing products. Connect conversations to the tools that keep your business moving.",
    bullets: [
      "Connect CRM records and lead workflows",
      "Use supported APIs and signed webhooks",
      "Review delivery status and integration failures",
    ],
    panel: "integrations",
    accent: "blue",
  },
  {
    id: "channels",
    n: "05",
    label: "CHANNELS",
    title: "One AI bot. Multiple channels.",
    text: "Meet customers where they communicate. Connect your business knowledge to your website and supported messaging channels.",
    bullets: [
      "Website widget and hosted chat experience",
      "WhatsApp Business Cloud API integration",
      "Manage supported channels from one workspace",
    ],
    panel: "channels",
    accent: "mint",
  },
  {
    id: "white-label",
    n: "06",
    label: "WHITE LABEL",
    title: "Your AI platform. Your brand.",
    text: "Create an experience that feels like your business, with your identity, bot appearance, and client workspaces.",
    bullets: [
      "Customize logos, colors, and bot identity",
      "Organize your clients into separate workspaces",
      "Discuss domain and partner requirements with us",
    ],
    panel: "brand",
    accent: "violet",
  },
];
export const faqs = [
  [
    "What is TalkToBot?",
    "TalkToBot is a platform for building AI assistants from your business knowledge, managing conversations, capturing leads, and connecting supported business tools.",
  ],
  [
    "What channels can I connect?",
    "The platform includes a website widget and WhatsApp integration, with additional supported messaging connectors in the app. Each channel needs its own provider configuration and permissions.",
  ],
  [
    "Can I connect my CRM?",
    "Yes. CRM workflows can route qualified leads to supported connectors. Your provider account, credentials, and field mapping determine which actions are available.",
  ],
  [
    "How much does it cost?",
    "We have not published verified plan prices on this website. Tell us about your channels, message volume, and team so we can discuss the right setup.",
  ],
  [
    "Can I use TalkToBot under my own brand?",
    "Branding controls let you customize the bot experience. Contact us to discuss agency workspaces, custom domains, and white-label requirements.",
  ],
  [
    "Can I review answers before going live?",
    "You can test your assistant, inspect its knowledge sources, and review conversations in your workspace before deploying it to customers.",
  ],
];
export const starterPosts: Omit<
  Post,
  "id" | "status" | "version" | "updated_at" | "published_at" | "workflow_status" | "scheduled_at" | "editorial_timezone"
>[] = [
  {
    slug: "build-a-bot-from-your-business-knowledge",
    title: "Start with your knowledge. Build a better bot.",
    excerpt:
      "A practical checklist for turning your documents and FAQs into a useful business assistant.",
    author: "TalkToBot editorial",
    category: "Getting started",
    tags: ["Knowledge", "AI bots"],
    cover: "",
    cover_alt: "",
    seo_title: "Build a bot from your business knowledge",
    seo_description:
      "Prepare your knowledge, configure your assistant, and test answers before deployment.",
    body: "# Start with a clear job\nDecide what your assistant should help people do. A useful first scope is answering product questions, explaining a service, or helping customers find the right next step.\n\n## Prepare reliable sources\nUse current documents and FAQs with clear ownership. Remove obsolete policies and conflicting answers before uploading. A bot is easier to review when every important answer has a recognizable source.\n\n## Test before you deploy\nAsk real questions your customers use. Include questions the assistant should not answer. Review citations, unclear responses, and the route to a human colleague.\n\n## Keep improving\nReview conversations regularly. Update your sources when your business changes, and re-test important journeys after each significant update.",
  },
  {
    slug: "design-a-conversation-that-captures-leads",
    title: "Make lead capture feel like a conversation.",
    excerpt:
      "Ask for the information you need, at the moment it helps the customer move forward.",
    author: "TalkToBot editorial",
    category: "Conversations",
    tags: ["Leads", "CRM"],
    cover: "",
    cover_alt: "",
    seo_title: "",
    seo_description: "",
    body: "# Help first, ask second\nA useful conversation starts with the visitor’s question. Explain the next step before requesting contact details.\n\n## Collect only what you need\nA name, work email, and a short description may be enough to route an enquiry. Avoid requesting private information that your sales or support team does not need.\n\n## Confirm the details\nShow customers what will be submitted and how their team will respond. A model’s guess about someone’s contact information is not a confirmed lead.\n\n## Review the handoff\nCheck both the conversation and CRM delivery status. A recorded enquiry is different from a verified update in an external system.",
  },
  {
    slug: "review-your-ai-assistant-before-launch",
    title: "Your before-launch AI assistant checklist.",
    excerpt:
      "Knowledge, boundaries, channels, and human handoffs: the checks worth doing before your first customer chat.",
    author: "TalkToBot editorial",
    category: "Guides",
    tags: ["Launch", "Testing"],
    cover: "",
    cover_alt: "",
    seo_title: "",
    seo_description: "",
    body: "# A considered launch\nStart with a small set of real customer tasks. Verify those tasks end to end before expanding the assistant’s responsibilities.\n\n## Check the knowledge\nConfirm that key policies and answers are current. Ask questions with missing evidence and check that the assistant communicates uncertainty.\n\n## Check the channel\nTest the actual website or messaging integration, including permissions, incoming messages, and outgoing delivery failures.\n\n## Check the human handoff\nMake it clear when and how a person can help. Confirm your team can find the conversation and act on it.\n\n## Review after launch\nKeep a regular review of unanswered questions and customer feedback. Treat your bot’s knowledge as an evolving business resource.",
  },
];
