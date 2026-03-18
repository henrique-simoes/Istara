/**
 * Survey CSV generator for ReClaw simulation.
 * Produces realistic survey response data in CSV format with both
 * quantitative (Likert, NPS) and qualitative (open-ended) questions.
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

/**
 * Generate a Likert score (1-5) with a bias.
 * bias: "positive" skews 3-5, "negative" skews 1-3, "neutral" is uniform.
 */
function likert(bias = "neutral") {
  if (bias === "positive") {
    const weights = [0.05, 0.1, 0.2, 0.35, 0.3];
    return weightedPick(weights);
  } else if (bias === "negative") {
    const weights = [0.25, 0.3, 0.25, 0.15, 0.05];
    return weightedPick(weights);
  }
  return randInt(1, 5);
}

function weightedPick(weights) {
  const r = Math.random();
  let cumulative = 0;
  for (let i = 0; i < weights.length; i++) {
    cumulative += weights[i];
    if (r <= cumulative) return i + 1;
  }
  return weights.length;
}

/**
 * Generate an NPS score (0-10) with a correlated profile.
 */
function npsScore(overallSatisfaction) {
  if (overallSatisfaction >= 4) {
    return randInt(7, 10);
  } else if (overallSatisfaction === 3) {
    return randInt(5, 8);
  } else {
    return randInt(0, 6);
  }
}

/**
 * Escape a string for CSV embedding.
 */
function csvEscape(str) {
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

/* ------------------------------------------------------------------ */
/*  Qualitative response generators                                   */
/* ------------------------------------------------------------------ */

const elaborations = [
  " I've mentioned this to support a few times.",
  " Other people on my team feel the same way.",
  " It's been like this for months.",
  " I think this is a dealbreaker for some users.",
  " This is something I bring up in every feedback survey.",
  " I've seen competitors handle this much better.",
  " My team has developed workarounds but they're not ideal.",
  " I know it's a small thing but it matters to us.",
  " This directly impacts our daily productivity.",
  " I hope the team is aware of this because it's important.",
];

const transitionPhrases = [
  "On top of that, ",
  "Additionally, ",
  "I'd also mention that ",
  "Another thing — ",
  "Related to that, ",
  "Also worth noting: ",
  "Beyond that, ",
  "Something else I've noticed is ",
];

function generateOpenResponse(overallSatisfaction, minSentences = 1, maxSentences = 4) {
  const sentenceCount = randInt(minSentences, maxSentences);
  const parts = [];

  for (let i = 0; i < sentenceCount; i++) {
    let sentence;
    if (overallSatisfaction >= 4) {
      sentence = Math.random() < 0.7 ? pick(quotes) : pick(painPoints);
    } else if (overallSatisfaction <= 2) {
      sentence = Math.random() < 0.7 ? pick(painPoints) : pick(quotes);
    } else {
      sentence = Math.random() < 0.5 ? pick(quotes) : pick(painPoints);
    }

    if (i > 0) {
      sentence = pick(transitionPhrases) + sentence.charAt(0).toLowerCase() + sentence.slice(1);
    }

    if (Math.random() < 0.3) {
      sentence += pick(elaborations);
    }

    parts.push(sentence);
  }

  return parts.join(" ");
}

function generateFeedback(overallSatisfaction) {
  return generateOpenResponse(overallSatisfaction, 1, 3);
}

/* ------------------------------------------------------------------ */
/*  Open-ended question templates per survey theme                    */
/* ------------------------------------------------------------------ */

const openEndedQuestionSets = [
  {
    label: "onboarding",
    questions: [
      "biggest_challenge_getting_started",
      "what_almost_made_you_quit",
      "advice_for_new_users",
      "missing_from_onboarding",
    ],
  },
  {
    label: "features",
    questions: [
      "most_valuable_feature",
      "feature_you_wish_existed",
      "feature_you_never_use_and_why",
      "workflow_improvement_suggestion",
    ],
  },
  {
    label: "comparison",
    questions: [
      "what_competitor_does_better",
      "reason_you_chose_us",
      "what_would_make_you_switch",
      "describe_product_in_three_words",
    ],
  },
  {
    label: "experience",
    questions: [
      "most_frustrating_experience",
      "most_delightful_moment",
      "what_you_tell_colleagues",
      "one_thing_you_would_change",
    ],
  },
  {
    label: "support",
    questions: [
      "last_support_experience",
      "unanswered_question",
      "documentation_gap",
      "help_resource_you_wish_existed",
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Persona-based profiles for realistic correlation                  */
/* ------------------------------------------------------------------ */

const profiles = [
  { label: "happy_power_user", signupBias: "positive", onboardBias: "positive", featureBias: "positive", timeRange: [1, 8] },
  { label: "frustrated_new_user", signupBias: "negative", onboardBias: "negative", featureBias: "neutral", timeRange: [15, 30] },
  { label: "neutral_regular", signupBias: "neutral", onboardBias: "neutral", featureBias: "neutral", timeRange: [5, 20] },
  { label: "mixed_feelings", signupBias: "positive", onboardBias: "negative", featureBias: "positive", timeRange: [8, 18] },
  { label: "churning_user", signupBias: "negative", onboardBias: "negative", featureBias: "negative", timeRange: [20, 30] },
  { label: "quiet_satisfied", signupBias: "positive", onboardBias: "positive", featureBias: "neutral", timeRange: [3, 12] },
  { label: "vocal_critic", signupBias: "neutral", onboardBias: "negative", featureBias: "negative", timeRange: [10, 25] },
  { label: "enthusiastic_advocate", signupBias: "positive", onboardBias: "positive", featureBias: "positive", timeRange: [2, 6] },
];

/* ------------------------------------------------------------------ */
/*  Main generator                                                    */
/* ------------------------------------------------------------------ */

/**
 * Generates a synthetic survey CSV with quantitative and qualitative data.
 *
 * @param {number} respondentCount - Number of survey respondents (default 50).
 * @returns {{ filename: string, content: string }}
 */
export function generateSurveyCSV(respondentCount = 50) {
  const topic = pick(topics);
  const date = recentDate();
  const questionSet = pick(openEndedQuestionSets);

  // Build header: quant columns + open-ended columns + general feedback
  const quantColumns = [
    "respondent_id",
    "age",
    "role",
    "company_size",
    "signup_ease",
    "onboarding_satisfaction",
    "feature_usefulness",
    "overall_satisfaction",
    "time_to_first_task_min",
    "would_recommend",
  ];
  const qualColumns = questionSet.questions;
  const header = [...quantColumns, ...qualColumns, "open_feedback"].join(",");

  const rows = [header];
  const respondents = pickN(names, Math.min(respondentCount, names.length));

  // If we need more respondents than names, cycle with suffixes
  const allRespondents = [];
  for (let i = 0; i < respondentCount; i++) {
    if (i < respondents.length) {
      allRespondents.push(respondents[i]);
    } else {
      const base = pick(names);
      allRespondents.push({
        ...base,
        id: `${base.id}-${i}`,
        age: randInt(22, 58),
      });
    }
  }

  for (let i = 0; i < allRespondents.length; i++) {
    const person = allRespondents[i];
    const profile = pick(profiles);

    const signupEase = likert(profile.signupBias);
    const onboardSat = likert(profile.onboardBias);
    const featureUse = likert(profile.featureBias);
    const overallSat = Math.round((signupEase + onboardSat + featureUse) / 3);
    const timeToTask = randInt(profile.timeRange[0], profile.timeRange[1]);
    const wouldRecommend = npsScore(overallSat);

    // Quantitative values
    const quantValues = [
      person.id,
      person.age,
      csvEscape(person.role),
      csvEscape(person.company_size),
      signupEase,
      onboardSat,
      featureUse,
      overallSat,
      timeToTask,
      wouldRecommend,
    ];

    // Qualitative open-ended responses (2-5 sentences each)
    const qualValues = qualColumns.map(() =>
      csvEscape(generateOpenResponse(overallSat, 2, 5))
    );

    // General open feedback
    const feedback = csvEscape(generateFeedback(overallSat));

    const row = [...quantValues, ...qualValues, feedback].join(",");
    rows.push(row);
  }

  const slug = topic.topic.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
  const filename = `survey-${slug}-${date}.csv`;

  return { filename, content: rows.join("\n") };
}

export default { generateSurveyCSV };
