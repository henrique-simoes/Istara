/**
 * Competitive analysis generator for ReClaw simulation.
 * Produces realistic markdown competitor profile documents with
 * company overview, feature comparison, pricing, and market analysis.
 */

import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const corporaDir = join(__dirname, "..", "corpora");

const names = JSON.parse(readFileSync(join(corporaDir, "names.json"), "utf-8"));
const painPoints = JSON.parse(readFileSync(join(corporaDir, "pain-points.json"), "utf-8"));
const quotes = JSON.parse(readFileSync(join(corporaDir, "quotes.json"), "utf-8"));
const topics = JSON.parse(readFileSync(join(corporaDir, "research-topics.json"), "utf-8"));
const companies = JSON.parse(readFileSync(join(corporaDir, "companies.json"), "utf-8"));

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function pick(array) {
  return array[Math.floor(Math.random() * array.length)];
}

function pickN(array, n) {
  const shuffled = [...array].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, Math.min(n, shuffled.length));
}

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function recentDate() {
  const now = new Date();
  const daysAgo = randInt(1, 60);
  const d = new Date(now.getTime() - daysAgo * 86400000);
  return d.toISOString().split("T")[0];
}

/* ------------------------------------------------------------------ */
/*  Competitive analysis data pools                                   */
/* ------------------------------------------------------------------ */

const fundingStages = [
  "Seed",
  "Series A",
  "Series B",
  "Series C",
  "Series D",
  "Bootstrapped",
  "Pre-IPO",
  "Public (recently IPO'd)",
];

const coreFeatures = [
  "Real-time collaboration workspace",
  "Role-based access control (RBAC)",
  "Custom workflow automation",
  "Native mobile app (iOS & Android)",
  "API-first architecture with public REST endpoints",
  "Single sign-on (SSO) via SAML/OIDC",
  "Advanced search with full-text indexing",
  "Interactive dashboard builder",
  "Third-party integrations marketplace",
  "Audit logging and compliance reports",
  "Multi-language / i18n support",
  "White-label / custom branding options",
  "Built-in analytics and reporting engine",
  "AI-powered recommendations",
  "Offline mode with background sync",
  "Granular notification preferences",
  "Drag-and-drop interface builder",
  "Version history and rollback",
  "Embedded help and in-app tutorials",
  "Bulk import / export (CSV, Excel, JSON)",
  "Webhooks and event-driven triggers",
  "Team activity feed and change log",
  "Multi-tenant architecture",
  "Custom fields and metadata schemas",
];

const uniqueSellingPoints = [
  "Industry-leading onboarding experience — average time to first value under 3 minutes",
  "AI copilot embedded in every workflow surface, reducing manual data entry by ~40%",
  "Vertically integrated analytics — no need for third-party BI tools",
  "Enterprise-grade security certifications: SOC 2 Type II, ISO 27001, HIPAA",
  "Fully open-source core with a managed cloud offering",
  "Zero-downtime deployment pipeline visible to customers via a public status page",
  "Deep native integrations with the top 50 SaaS tools (Slack, Jira, Salesforce, etc.)",
  "Freemium model with generous free tier — up to 10 users with full feature access",
  "Purpose-built for regulated industries with built-in compliance guardrails",
  "Plugin marketplace with 200+ community-contributed extensions",
  "Real-time multiplayer editing with conflict resolution, similar to Google Docs",
  "Dedicated customer success manager included in all paid plans",
];

const comparisonFeatures = [
  "Real-time collaboration",
  "Custom workflows",
  "Mobile app",
  "SSO / SAML",
  "API access",
  "Audit logging",
  "AI features",
  "Offline support",
  "Custom branding",
  "Analytics / reporting",
  "Bulk import/export",
  "Webhook integrations",
  "Granular permissions",
  "In-app help / tutorials",
  "Version history",
  "Multi-language support",
];

const pricingFeaturesFree = [
  "Up to 3 users",
  "Up to 5 users",
  "1 project / workspace",
  "3 projects / workspaces",
  "Basic reporting",
  "Community support only",
  "5 GB storage",
  "2 GB storage",
  "Limited API access (100 calls/day)",
  "Standard templates",
  "Email notifications only",
];

const pricingFeaturesPro = [
  "Up to 25 users",
  "Up to 50 users",
  "Unlimited projects",
  "Advanced reporting and dashboards",
  "Priority email and chat support",
  "50 GB storage",
  "100 GB storage",
  "Full API access",
  "Custom workflows",
  "SSO via Google / Microsoft",
  "Integrations with 20+ tools",
  "Version history (90 days)",
  "Custom fields",
];

const pricingFeaturesEnterprise = [
  "Unlimited users",
  "Dedicated account manager",
  "SAML / OIDC SSO",
  "Unlimited storage",
  "99.99% uptime SLA",
  "Advanced audit logging",
  "Custom contracts and invoicing",
  "On-premises deployment option",
  "SOC 2 and HIPAA compliance",
  "Priority phone support (24/7)",
  "Custom onboarding and training",
  "Dedicated infrastructure",
  "Data residency options",
];

const marketPositionDescriptions = [
  "positions itself as a premium, enterprise-first solution with a strong emphasis on security and compliance. Their go-to-market strategy relies heavily on outbound sales and long-term contracts, which limits their penetration in the SMB segment but creates high switching costs among enterprise clients.",
  "occupies the 'affordable alternative' slot in the market, targeting teams that are priced out of incumbent solutions. Their growth has been organic and community-driven, with a strong presence on review sites and developer forums. However, their feature depth lags behind more established players.",
  "has carved out a niche by focusing exclusively on a single vertical, allowing them to offer highly tailored workflows that horizontal competitors cannot match. This focus is both a strength (deep domain knowledge) and a limitation (small addressable market).",
  "is a VC-backed challenger growing aggressively through a product-led growth (PLG) motion. Their generous free tier drives top-of-funnel acquisition, and their in-product upsell mechanics are among the best in the space. The risk is burn rate — profitability remains uncertain.",
  "competes primarily on design and user experience, earning strong word-of-mouth from individual contributors. However, they struggle with enterprise adoption because their permissions model and admin tooling are underdeveloped relative to what IT buyers expect.",
  "leverages a platform approach, positioning their core product as a hub with an extensive ecosystem of plugins and integrations. This strategy creates network effects but also introduces quality inconsistency across the third-party ecosystem.",
];

const opportunityInsights = [
  "Their onboarding flow includes a guided interactive tour that reduces time-to-first-value. We should evaluate a similar pattern for our own first-run experience.",
  "They surface contextual help tooltips directly within complex forms — an approach that could significantly reduce our support ticket volume for the reporting module.",
  "Their pricing page uses an interactive calculator that lets prospects estimate cost by team size — this transparency likely contributes to their higher conversion rate.",
  "The competitor's mobile app prioritizes read/notification use cases and explicitly deprioritizes editing, which aligns with how our own users describe their mobile behavior.",
  "They offer a public product roadmap with voting, which creates community engagement and reduces 'when will you build X' support requests.",
  "Their empty states are richly designed with sample data and one-click templates, which could inspire improvements to our own zero-state experiences.",
  "They have invested in a self-service migration tool that imports data from competitors in under 5 minutes — a major switching-cost reducer we should consider replicating.",
  "Their notification system uses AI-powered batching to reduce alert volume by ~60% while maintaining relevance scores — worth investigating for our own notification overhaul.",
  "They publish detailed benchmark reports for their industry vertical, which positions them as a thought leader and drives inbound leads through SEO.",
  "Their freemium model includes full feature access (limited by usage, not capability), which lets users experience the full product before hitting a paywall.",
];

/* ------------------------------------------------------------------ */
/*  Main generator                                                    */
/* ------------------------------------------------------------------ */

/**
 * Generates a synthetic competitor analysis profile in markdown.
 *
 * @returns {{ filename: string, content: string }}
 */
export function generateCompetitorProfile() {
  const company = pick(companies);
  const analyst = pick(names);
  const date = recentDate();
  const foundingYear = randInt(2010, 2022);
  const fundingStage = pick(fundingStages);

  const lines = [];

  // ----- Header -----
  lines.push(`# Competitive Analysis — ${company.name}`);
  lines.push("");
  lines.push(`**Analysis Date:** ${date}`);
  lines.push(`**Analyst:** ${analyst.name} (${analyst.role})`);
  lines.push(`**Industry:** ${company.industry}`);
  lines.push(`**Competitor Product:** ${company.product}`);
  lines.push("");

  // ----- Company Overview -----
  lines.push("## Company Overview");
  lines.push("");
  lines.push(`| Field | Detail |`);
  lines.push(`|-------|--------|`);
  lines.push(`| **Company Name** | ${company.name} |`);
  lines.push(`| **Industry** | ${company.industry} |`);
  lines.push(`| **Core Product** | ${company.product} |`);
  lines.push(`| **Target Market** | ${company.target} |`);
  lines.push(`| **Founded** | ${foundingYear} |`);
  lines.push(`| **Funding Stage** | ${fundingStage} |`);
  lines.push(`| **Company Culture** | ${company.culture} |`);
  lines.push("");

  // ----- Product Description -----
  lines.push("## Product Description");
  lines.push("");
  lines.push(`${company.name} offers a ${company.product.toLowerCase()} aimed at ${company.target.toLowerCase()}. The platform reflects a ${company.culture.toLowerCase()} philosophy and has been on the market since ${foundingYear}.`);
  lines.push("");

  // Core Features (8-12 items)
  const featureCount = randInt(8, 12);
  const selectedFeatures = pickN(coreFeatures, featureCount);

  lines.push("### Core Features");
  lines.push("");
  for (const feature of selectedFeatures) {
    lines.push(`- ${feature}`);
  }
  lines.push("");

  // Unique Selling Points (2-4 items)
  const uspCount = randInt(2, 4);
  const selectedUSPs = pickN(uniqueSellingPoints, uspCount);

  lines.push("### Unique Selling Points");
  lines.push("");
  for (const usp of selectedUSPs) {
    lines.push(`- ${usp}`);
  }
  lines.push("");

  // ----- Feature Comparison Matrix -----
  lines.push("## Feature Comparison Matrix");
  lines.push("");
  lines.push("Comparison of key capabilities between our product and the competitor.");
  lines.push("");

  const matrixFeatureCount = randInt(8, 12);
  const matrixFeatures = pickN(comparisonFeatures, matrixFeatureCount);
  const ratings = ["Yes", "No", "Partial"];
  const ratingWeights = [0.5, 0.2, 0.3]; // Competitor slightly favored to create realistic analysis

  lines.push("| Feature | Our Product | Competitor |");
  lines.push("|---------|-------------|------------|");

  for (const feature of matrixFeatures) {
    // Our product rating
    const ourRating = pick(ratings);
    // Competitor rating — weighted toward "Yes" to make it a credible competitor
    const r = Math.random();
    let competitorRating;
    if (r < ratingWeights[0]) competitorRating = "Yes";
    else if (r < ratingWeights[0] + ratingWeights[1]) competitorRating = "No";
    else competitorRating = "Partial";

    lines.push(`| ${feature} | ${ourRating} | ${competitorRating} |`);
  }
  lines.push("");

  // ----- UX Strengths -----
  lines.push("## UX Strengths");
  lines.push("");
  lines.push(`Based on user feedback and product review analysis, ${company.name} demonstrates the following UX strengths:`);
  lines.push("");

  const strengthCount = randInt(3, 5);
  const strengthQuotes = pickN(quotes, strengthCount);

  const strengthFramings = [
    "Users consistently praise",
    "A standout quality noted by reviewers:",
    "Power users highlight that",
    "Compared to alternatives, users appreciate that",
    "New users frequently mention",
    "Across review platforms, a recurring positive theme:",
    "Analyst observation:",
  ];

  for (const q of strengthQuotes) {
    lines.push(`- **${pick(strengthFramings)}** "${q}"`);
  }
  lines.push("");

  // ----- UX Weaknesses -----
  lines.push("## UX Weaknesses");
  lines.push("");
  lines.push(`Common pain points reported by ${company.name} users in public reviews and forum discussions:`);
  lines.push("");

  const weaknessCount = randInt(3, 5);
  const weaknessPainPoints = pickN(painPoints, weaknessCount);

  const weaknessFramings = [
    "Recurring complaint:",
    "Multiple users report that",
    "A frequent source of friction:",
    "Noted across several review platforms:",
    "Power users flag that",
    "Support forums frequently reference:",
    "Churned users cite that",
  ];

  for (const pp of weaknessPainPoints) {
    lines.push(`- **${pick(weaknessFramings)}** "${pp}"`);
  }
  lines.push("");

  // ----- Pricing Tiers -----
  lines.push("## Pricing");
  lines.push("");

  const freePrice = "Free";
  const proPrice = `$${randInt(8, 25)}/user/month`;
  const enterprisePrice = "Custom (contact sales)";

  // Free tier
  lines.push("### Free Tier");
  lines.push(`**Price:** ${freePrice}`);
  lines.push("");
  const freeFeatures = pickN(pricingFeaturesFree, randInt(3, 5));
  for (const f of freeFeatures) {
    lines.push(`- ${f}`);
  }
  lines.push("");

  // Pro tier
  lines.push("### Pro Tier");
  lines.push(`**Price:** ${proPrice}`);
  lines.push("");
  const proFeatures = pickN(pricingFeaturesPro, randInt(4, 6));
  for (const f of proFeatures) {
    lines.push(`- ${f}`);
  }
  lines.push("");

  // Enterprise tier
  lines.push("### Enterprise Tier");
  lines.push(`**Price:** ${enterprisePrice}`);
  lines.push("");
  const entFeatures = pickN(pricingFeaturesEnterprise, randInt(4, 6));
  for (const f of entFeatures) {
    lines.push(`- ${f}`);
  }
  lines.push("");

  // ----- User Sentiment -----
  lines.push("## User Sentiment");
  lines.push("");
  lines.push(`Aggregated user feedback from G2, Capterra, and community forums attributed to ${company.name} users:`);
  lines.push("");

  // Positive sentiment (2-3 quotes)
  lines.push("### Positive");
  lines.push("");
  const positiveCount = randInt(2, 3);
  const positiveQuotes = pickN(quotes, positiveCount);
  const positiveSources = pickN(names, positiveCount);

  for (let i = 0; i < positiveCount; i++) {
    lines.push(`> "${positiveQuotes[i]}"`);
    lines.push(`> — ${positiveSources[i].name}, ${positiveSources[i].role} (${positiveSources[i].company_size} employees)`);
    lines.push("");
  }

  // Negative sentiment (2-3 pain points)
  lines.push("### Negative");
  lines.push("");
  const negativeCount = randInt(2, 3);
  const negativePainPoints = pickN(painPoints, negativeCount);
  const negativeSources = pickN(names, negativeCount);

  for (let i = 0; i < negativeCount; i++) {
    lines.push(`> "${negativePainPoints[i]}"`);
    lines.push(`> — ${negativeSources[i].name}, ${negativeSources[i].role} (${negativeSources[i].company_size} employees)`);
    lines.push("");
  }

  // ----- Market Position -----
  lines.push("## Market Position");
  lines.push("");
  lines.push(`${company.name} ${pick(marketPositionDescriptions)}`);
  lines.push("");

  // ----- Opportunities -----
  lines.push("## Opportunities");
  lines.push("");
  lines.push(`Key takeaways from this analysis — areas where our product could learn from or differentiate against ${company.name}:`);
  lines.push("");

  const opportunityCount = randInt(3, 5);
  const selectedOpportunities = pickN(opportunityInsights, opportunityCount);

  for (let i = 0; i < selectedOpportunities.length; i++) {
    lines.push(`${i + 1}. ${selectedOpportunities[i]}`);
  }
  lines.push("");

  // ----- Footer -----
  lines.push("---");
  lines.push(`*Competitive analysis prepared by ${analyst.name} on ${date}.*`);
  lines.push(`*Sources: public product pages, G2/Capterra reviews, community forums, and hands-on product evaluation.*`);
  lines.push(`*This document is for internal use only and should not be shared externally.*`);

  const slug = company.name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  const filename = `competitor-${slug}-${date}.md`;

  return { filename, content: lines.join("\n") };
}

export default { generateCompetitorProfile };
