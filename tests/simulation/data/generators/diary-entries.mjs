/**
 * Diary study generator for Istara simulation.
 * Produces realistic markdown diary study entries with daily logs,
 * mood tracking, weekly reflections, and end-of-study summaries.
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
/*  Date arithmetic                                                   */
/* ------------------------------------------------------------------ */

function addDays(dateStr, days) {
  const d = new Date(dateStr + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().split("T")[0];
}

function formatDateLong(dateStr) {
  const d = new Date(dateStr + "T00:00:00Z");
  const options = { weekday: "long", year: "numeric", month: "long", day: "numeric", timeZone: "UTC" };
  return d.toLocaleDateString("en-US", options);
}

function weekdayName(dateStr) {
  const d = new Date(dateStr + "T00:00:00Z");
  return d.toLocaleDateString("en-US", { weekday: "long", timeZone: "UTC" });
}

/* ------------------------------------------------------------------ */
/*  Mood system                                                       */
/* ------------------------------------------------------------------ */

const moodLabels = [
  { rating: 1, emoji: "1/5 - Frustrated", descriptor: "Very frustrated" },
  { rating: 2, emoji: "2/5 - Disappointed", descriptor: "Somewhat disappointed" },
  { rating: 3, emoji: "3/5 - Neutral", descriptor: "Neutral" },
  { rating: 4, emoji: "4/5 - Satisfied", descriptor: "Fairly satisfied" },
  { rating: 5, emoji: "5/5 - Delighted", descriptor: "Very pleased" },
];

function generateMood(bias) {
  let rating;
  if (bias === "positive") {
    rating = pick([3, 4, 4, 5, 5]);
  } else if (bias === "negative") {
    rating = pick([1, 1, 2, 2, 3]);
  } else {
    rating = pick([1, 2, 3, 3, 4, 4, 5]);
  }
  return moodLabels[rating - 1];
}

/* ------------------------------------------------------------------ */
/*  Activity templates                                                */
/* ------------------------------------------------------------------ */

const morningActivities = [
  "Opened the product first thing to check on overnight updates and team activity.",
  "Started my day by reviewing the dashboard for any urgent items.",
  "Logged in from my phone while commuting to skim through notifications.",
  "Sat down at my desk and launched the app alongside email and Slack.",
  "Had a quick stand-up meeting, then opened the product to update task statuses.",
  "Checked the mobile app briefly over breakfast to see if anything needed attention.",
  "Opened the desktop version and spent about 10 minutes organizing my workspace.",
  "Tried to catch up on changes teammates made yesterday before my first meeting.",
  "Started a new task and needed to set up the workspace from scratch this morning.",
  "Logged in to prep for a client presentation using data from the product.",
];

const afternoonActivities = [
  "Spent about an hour working through a complex workflow in the product.",
  "Had to export data for a report and struggled with the formatting options.",
  "Collaborated with a teammate on a shared document inside the product.",
  "Tried to find a feature I know exists but couldn't locate it through navigation.",
  "Used the product during a live meeting to demonstrate progress to stakeholders.",
  "Needed to set up a new integration and followed the documentation step by step.",
  "Spent most of the afternoon in the product, switching between multiple views.",
  "Attempted to complete a bulk action and ran into unexpected behavior.",
  "Had to onboard a new team member and walked them through the product.",
  "Used the search feature extensively to track down an older project artifact.",
  "Tried to customize my dashboard but couldn't figure out how to save the layout.",
  "Ran a report that took longer than expected to generate.",
];

const eveningActivities = [
  "Checked the mobile app one last time before wrapping up for the day.",
  "Reviewed tomorrow's tasks and made some quick notes in the product.",
  "Noticed a notification about a teammate's comment and responded briefly.",
  "Spent a few minutes reorganizing my workspace for tomorrow.",
  "Tried to quickly update a status from my phone but the mobile experience was clunky.",
  "Reflected on today's workflow and jotted down a few thoughts about what went well.",
  "Received an alert notification on my phone and checked it out of curiosity.",
  "Reviewed the day's progress in the analytics view before logging off.",
];

const frictionDescriptions = [
  "I hit a wall when the interface didn't respond the way I expected.",
  "The workflow required more steps than it should have for such a simple task.",
  "I had to context-switch between three different screens to complete one action.",
  "Something about the layout felt off today — I kept looking in the wrong place.",
  "I wasted time trying to figure out an error message that wasn't helpful.",
  "The product was noticeably slower than usual, which broke my flow.",
  "I discovered that a feature I relied on had changed without any notice.",
  "Navigation felt confusing today, especially when trying to get back to where I started.",
  "I accidentally triggered an action I didn't intend and couldn't easily undo it.",
  "The mobile and desktop experiences felt inconsistent, which tripped me up.",
  "A notification pulled me out of a focused workflow for something that wasn't urgent.",
  "I needed help from documentation but the relevant article was outdated.",
];

const emotionalReactions = [
  "Felt a small sense of accomplishment when I finally completed the task.",
  "Got genuinely frustrated — I almost closed the tab and walked away.",
  "Felt confident using this part of the product today. It just clicked.",
  "Felt a bit anxious about making changes because there's no clear way to undo.",
  "Mild annoyance, nothing major, but it adds up over time.",
  "Relieved that the workflow worked as expected for once.",
  "Felt overwhelmed by the number of options on screen.",
  "Pleasantly surprised — something that used to be painful was noticeably better.",
  "Indifferent. It did the job, nothing more, nothing less.",
  "Slightly confused but managed to muddle through eventually.",
  "Excited to discover a feature I didn't know about.",
  "Deflated. This should not be this hard.",
];

const photoDescriptions = [
  "screenshot of the confusing navigation menu",
  "photo of my desk setup while using the product on dual monitors",
  "screenshot of the error message I encountered",
  "screenshot showing the cluttered dashboard view",
  "photo of my handwritten notes trying to map out the workflow",
  "screenshot of the mobile app notification center",
  "screenshot comparing the old and new interface side by side",
  "photo of the sticky note I keep with workaround steps",
  "screenshot of the search results that didn't match my query",
  "screenshot showing the slow loading spinner I stared at for 20 seconds",
  "photo of a teammate pointing at the screen asking how to do something",
  "screenshot of the successful export that finally worked after three attempts",
];

/* ------------------------------------------------------------------ */
/*  Weekly reflection templates                                       */
/* ------------------------------------------------------------------ */

const weeklyHighlights = [
  "Got noticeably faster at the core workflow compared to the start of the study.",
  "Found a workaround for the export issue that had been bothering me all week.",
  "Successfully onboarded a colleague, which forced me to articulate my own understanding.",
  "Discovered the keyboard shortcuts panel, which changed my daily experience significantly.",
  "Managed to complete a complex project entirely within the product for the first time.",
  "Had a smooth collaboration session with a remote teammate inside the product.",
  "The dashboard started to feel more intuitive after customizing it to my needs.",
  "Noticed a performance improvement mid-week that made the experience more pleasant.",
];

const weeklyFrustrations = [
  "Still struggling with the same navigation issue from Day 1 — it hasn't gotten easier.",
  "The notification volume became genuinely disruptive to my work this week.",
  "Lost work twice due to unclear save behavior. This eroded my trust in the product.",
  "The mobile experience remains a pain point — I avoid it when I can.",
  "Search continues to be unreliable. I've started bookmarking everything manually.",
  "The learning curve for advanced features feels unnecessarily steep.",
  "Inconsistency between different sections of the product keeps tripping me up.",
  "I spent too much time this week on tasks that should take minutes, not hours.",
];

const weeklyPatterns = [
  "I notice I use the product most heavily on Tuesday and Wednesday, then it tapers off.",
  "My usage is shifting from desktop-only to a mix of desktop and mobile throughout the day.",
  "I'm relying less on help docs and more on muscle memory, which is a good sign.",
  "I tend to batch my product usage into two focused sessions rather than using it continuously.",
  "I'm starting to develop personal shortcuts and workflows that aren't officially supported.",
  "My frustration peaks mid-afternoon when I'm trying to do complex tasks under time pressure.",
  "I notice I'm more patient with issues in the morning and less tolerant by end of day.",
  "I've started using the product in meetings more, which changes how I interact with it.",
];

/* ------------------------------------------------------------------ */
/*  Summary themes and recommendations                                */
/* ------------------------------------------------------------------ */

const summaryThemes = [
  "**Learning curve trajectory** — Initial confusion gave way to competence, but several interaction patterns remained unintuitive throughout the entire study period.",
  "**Mobile as second-class experience** — Mobile usage was limited to quick checks and never evolved into substantive work sessions, despite daily availability.",
  "**Notification fatigue arc** — Participant started engaged with notifications, then progressively muted channels until only critical alerts remained.",
  "**Workaround accumulation** — Over the study period, the participant developed 4-5 personal workarounds for product gaps, suggesting unmet feature needs.",
  "**Trust erosion through data loss** — Instances of lost or unsaved work had a disproportionate impact on product trust that persisted for days afterward.",
  "**Social learning dependency** — Participant relied heavily on coworkers for feature discovery, suggesting organic discoverability is insufficient.",
  "**Peak-end pattern** — Overall satisfaction was most influenced by the best and worst individual experiences, not the average daily experience.",
  "**Context-switching tax** — Time lost transitioning between the product and complementary tools (Slack, email, docs) was a recurring theme.",
  "**Emotional habituation** — Strong initial reactions (positive and negative) faded over time, replaced by pragmatic acceptance.",
  "**Feature depth vs. breadth** — Participant used a narrow set of features deeply rather than exploring the full product surface.",
];

const summaryRecommendations = [
  "Invest in progressive onboarding that introduces advanced features after core workflows are established, not during initial setup.",
  "Redesign the mobile experience as a first-class companion app rather than a miniaturized desktop port.",
  "Implement intelligent notification grouping and quiet hours to reduce alert fatigue without losing important signals.",
  "Add auto-save with visible version history to eliminate the anxiety around data loss.",
  "Create an in-product discovery mechanism (e.g., tips, contextual suggestions) to reduce dependency on social learning.",
  "Standardize interaction patterns across product sections to reduce the cognitive load of context-switching within the app.",
  "Prioritize undo/redo functionality for destructive actions — this was a consistent source of anxiety throughout the study.",
  "Consider a 'quick actions' or command palette feature to reduce the navigation overhead participants experienced daily.",
  "Improve search relevance and surface recent items more prominently to support the 'find, don't navigate' behavior observed.",
  "Invest in performance optimization — even small delays compounded into significant frustration over a multi-week usage period.",
];

/* ------------------------------------------------------------------ */
/*  Main generator                                                    */
/* ------------------------------------------------------------------ */

/**
 * Generates a synthetic diary study document in markdown.
 *
 * @param {number} dayCount - Number of diary days (default 14).
 * @returns {{ filename: string, content: string }}
 */
export function generateDiaryStudy(dayCount = 14) {
  const topic = pick(topics);
  const company = pick(companies);
  const participant = pick(names);
  const startDate = recentDate();
  const endDate = addDays(startDate, dayCount - 1);

  const lines = [];

  // ----- Header -----
  lines.push(`# Diary Study — ${topic.topic}`);
  lines.push("");
  lines.push(`**Participant:** ${participant.name} (${participant.id})`);
  lines.push(`**Role:** ${participant.role}, ${participant.company_size} employees`);
  lines.push(`**Product:** ${company.product} (${company.name})`);
  lines.push(`**Study Topic:** ${topic.topic}`);
  lines.push(`**Research Goal:** ${topic.goal}`);
  lines.push(`**Date Range:** ${startDate} to ${endDate} (${dayCount} days)`);
  lines.push(`**Methodology:** Longitudinal self-reported diary study with daily prompts`);
  lines.push("");

  // ----- Study Instructions (brief) -----
  lines.push("## Study Protocol");
  lines.push("");
  lines.push("Participant was asked to log their interactions with the product at least once daily,");
  lines.push("noting activities performed, emotional reactions, friction points encountered, and");
  lines.push("overall mood. Photo/screenshot attachments were encouraged. Weekly reflections were");
  lines.push("prompted every 7 days.");
  lines.push("");
  lines.push("---");
  lines.push("");

  // Track mood ratings for summary
  const moodRatings = [];

  // ----- Daily Entries -----
  for (let day = 0; day < dayCount; day++) {
    const currentDate = addDays(startDate, day);
    const dayNum = day + 1;
    const dayName = weekdayName(currentDate);
    const isWeekend = dayName === "Saturday" || dayName === "Sunday";

    lines.push(`## Day ${dayNum} of ${dayCount} — ${formatDateLong(currentDate)}`);
    lines.push("");

    // Weekends have lighter usage
    if (isWeekend && Math.random() < 0.4) {
      lines.push("*No entry logged — weekend.*");
      lines.push("");
      moodRatings.push(null);
      if (day < dayCount - 1) {
        lines.push("---");
        lines.push("");
      }
      continue;
    }

    // Determine which sections appear today
    const hasMorning = Math.random() < (isWeekend ? 0.4 : 0.85);
    const hasAfternoon = Math.random() < (isWeekend ? 0.3 : 0.8);
    const hasEvening = Math.random() < (isWeekend ? 0.2 : 0.5);

    // Early days trend negative, later days trend more varied/positive
    const dayBias = dayNum <= 3 ? "negative" : dayNum >= dayCount - 2 ? "positive" : "neutral";

    // --- Morning ---
    if (hasMorning) {
      lines.push("### Morning");
      lines.push("");
      lines.push(pick(morningActivities));
      lines.push("");

      // Occasional friction or quote
      if (Math.random() < 0.4) {
        lines.push(`> "${pick(quotes)}"`);
        lines.push("");
      }

      // Photo placeholder (30% chance)
      if (Math.random() < 0.3) {
        lines.push(`[Photo: ${pick(photoDescriptions)}]`);
        lines.push("");
      }
    }

    // --- Afternoon ---
    if (hasAfternoon) {
      lines.push("### Afternoon");
      lines.push("");
      lines.push(pick(afternoonActivities));
      lines.push("");

      // Friction point
      if (Math.random() < 0.6) {
        lines.push(`**Friction point:** ${pick(frictionDescriptions)}`);
        lines.push("");
      }

      // Pain point quote
      if (Math.random() < 0.5) {
        lines.push(`> "${pick(painPoints)}"`);
        lines.push("");
      }

      // Photo placeholder (25% chance)
      if (Math.random() < 0.25) {
        lines.push(`[Photo: ${pick(photoDescriptions)}]`);
        lines.push("");
      }
    }

    // --- Evening ---
    if (hasEvening) {
      lines.push("### Evening");
      lines.push("");
      lines.push(pick(eveningActivities));
      lines.push("");

      // Emotional reaction
      if (Math.random() < 0.5) {
        lines.push(`*${pick(emotionalReactions)}*`);
        lines.push("");
      }
    }

    // If no sections were generated (rare), add a minimal entry
    if (!hasMorning && !hasAfternoon && !hasEvening) {
      lines.push("Minimal usage today. Only checked a notification briefly and closed the app.");
      lines.push("");
    }

    // --- Daily Mood ---
    const mood = generateMood(dayBias);
    moodRatings.push(mood.rating);
    lines.push(`**Mood:** ${mood.emoji}`);
    lines.push("");

    // --- Weekly Reflection (every 7 days) ---
    if (dayNum % 7 === 0 && dayNum < dayCount) {
      const weekNum = dayNum / 7;
      lines.push(`### Week ${weekNum} Reflection`);
      lines.push("");

      lines.push("**What went well this week:**");
      lines.push(`- ${pick(weeklyHighlights)}`);
      if (Math.random() < 0.5) {
        lines.push(`- ${pick(weeklyHighlights)}`);
      }
      lines.push("");

      lines.push("**What was frustrating:**");
      lines.push(`- ${pick(weeklyFrustrations)}`);
      if (Math.random() < 0.5) {
        lines.push(`- ${pick(weeklyFrustrations)}`);
      }
      lines.push("");

      lines.push("**Usage patterns noticed:**");
      lines.push(`- ${pick(weeklyPatterns)}`);
      lines.push("");

      lines.push("**Notable quote from this week:**");
      lines.push(`> "${pick(quotes)}"`);
      lines.push("");
    }

    // Separator between days
    if (day < dayCount - 1) {
      lines.push("---");
      lines.push("");
    }
  }

  // ----- End-of-Study Summary -----
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push("## End-of-Study Summary");
  lines.push("");

  // Mood trend
  const validMoods = moodRatings.filter((m) => m !== null);
  const avgMood = validMoods.length > 0 ? (validMoods.reduce((a, b) => a + b, 0) / validMoods.length).toFixed(1) : "N/A";
  const firstHalf = validMoods.slice(0, Math.ceil(validMoods.length / 2));
  const secondHalf = validMoods.slice(Math.ceil(validMoods.length / 2));
  const firstHalfAvg = firstHalf.length > 0 ? (firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length).toFixed(1) : "N/A";
  const secondHalfAvg = secondHalf.length > 0 ? (secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length).toFixed(1) : "N/A";

  lines.push("### Mood Trend");
  lines.push("");
  lines.push(`- **Average mood:** ${avgMood} / 5`);
  lines.push(`- **First half average:** ${firstHalfAvg} / 5`);
  lines.push(`- **Second half average:** ${secondHalfAvg} / 5`);
  lines.push(`- **Days logged:** ${validMoods.length} of ${dayCount}`);
  const trend = parseFloat(secondHalfAvg) > parseFloat(firstHalfAvg) ? "Upward" : parseFloat(secondHalfAvg) < parseFloat(firstHalfAvg) ? "Downward" : "Stable";
  lines.push(`- **Overall trend:** ${trend}`);
  lines.push("");

  // Themes
  lines.push("### Emerging Themes");
  lines.push("");

  const themeCount = randInt(3, 5);
  const selectedThemes = pickN(summaryThemes, themeCount);
  for (let i = 0; i < selectedThemes.length; i++) {
    lines.push(`${i + 1}. ${selectedThemes[i]}`);
  }
  lines.push("");

  // Key quotes
  lines.push("### Key Participant Quotes");
  lines.push("");

  const summaryQuoteCount = randInt(3, 5);
  const summaryQuotes = pickN([...quotes, ...painPoints], summaryQuoteCount);
  for (const q of summaryQuotes) {
    lines.push(`> "${q}" — ${participant.name}, ${pick(["Day " + randInt(1, dayCount), "Week " + Math.ceil(dayCount / 7) + " reflection", "mid-study check-in"])}`);
    lines.push("");
  }

  // Recommendations
  lines.push("### Recommendations");
  lines.push("");

  const recCount = randInt(3, 5);
  const selectedRecs = pickN(summaryRecommendations, recCount);
  for (let i = 0; i < selectedRecs.length; i++) {
    lines.push(`${i + 1}. ${selectedRecs[i]}`);
  }
  lines.push("");

  // ----- Footer -----
  lines.push("---");
  lines.push(`*Diary study conducted over ${dayCount} days (${startDate} to ${endDate}).*`);
  lines.push(`*Participant: ${participant.name} (${participant.role}, ${participant.company_size} employees).*`);
  lines.push(`*All entries are self-reported and should be interpreted alongside behavioral analytics data.*`);

  const slug = topic.topic.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  const filename = `diary-study-${slug}-${startDate}.md`;

  return { filename, content: lines.join("\n") };
}

export default { generateDiaryStudy };
