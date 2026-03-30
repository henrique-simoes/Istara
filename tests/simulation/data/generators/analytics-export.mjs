/**
 * Analytics export generator for Istara simulation.
 * Produces realistic analytics CSV data: daily metrics, funnel data,
 * and A/B test results.
 */

import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const corporaDir = join(__dirname, "..", "corpora");

const topics = JSON.parse(readFileSync(join(corporaDir, "research-topics.json"), "utf-8"));

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function pick(array) {
  return array[Math.floor(Math.random() * array.length)];
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
 * Escape a string for CSV embedding (double-quote wrapping if needed).
 */
function csvEscape(str) {
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return '"' + str.replace(/"/g, '""') + '"';
  }
  return str;
}

/**
 * Generate a date string offset by a number of days from a base date.
 */
function dateOffset(baseDate, daysBack) {
  const d = new Date(baseDate.getTime() - daysBack * 86400000);
  return d.toISOString().split("T")[0];
}

/**
 * Weighted random pick from an array using a parallel weights array.
 * Returns the selected item.
 */
function weightedPick(items, weights) {
  const r = Math.random();
  let cumulative = 0;
  for (let i = 0; i < weights.length; i++) {
    cumulative += weights[i];
    if (r <= cumulative) return items[i];
  }
  return items[items.length - 1];
}

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const pages = ["homepage", "dashboard", "settings", "pricing", "onboarding", "help"];

const deviceTypes = ["desktop", "mobile", "tablet"];
const deviceWeights = [0.6, 0.3, 0.1];

const trafficSources = ["organic", "direct", "referral", "social", "email"];
const trafficWeights = [0.35, 0.25, 0.2, 0.12, 0.08];

const funnelStages = [
  "landing_page",
  "signup_start",
  "email_verification",
  "profile_setup",
  "first_action",
  "activation",
];

const abVariants = ["control", "variant_a", "variant_b"];

const abMetrics = [
  "click_through_rate",
  "signup_rate",
  "time_on_page_sec",
  "bounce_rate",
  "task_completion_rate",
];

/* ------------------------------------------------------------------ */
/*  Page-level baseline profiles                                      */
/* ------------------------------------------------------------------ */

const pageProfiles = {
  homepage:   { baseSessions: 1200, bounceBase: 0.45, avgDuration: 35,  convBase: 0.04, pvMultiplier: 1.3 },
  dashboard:  { baseSessions: 800,  bounceBase: 0.20, avgDuration: 180, convBase: 0.12, pvMultiplier: 2.5 },
  settings:   { baseSessions: 200,  bounceBase: 0.15, avgDuration: 90,  convBase: 0.08, pvMultiplier: 1.8 },
  pricing:    { baseSessions: 500,  bounceBase: 0.50, avgDuration: 60,  convBase: 0.06, pvMultiplier: 1.2 },
  onboarding: { baseSessions: 350,  bounceBase: 0.25, avgDuration: 120, convBase: 0.15, pvMultiplier: 2.0 },
  help:       { baseSessions: 300,  bounceBase: 0.35, avgDuration: 75,  convBase: 0.03, pvMultiplier: 1.6 },
};

/* ------------------------------------------------------------------ */
/*  Generator: Daily Metrics                                          */
/* ------------------------------------------------------------------ */

/**
 * Generates a daily analytics metrics CSV.
 *
 * @param {number} days - Number of days to generate (default 90).
 * @returns {{ filename: string, content: string }}
 */
export function generateDailyMetrics(days = 90) {
  const now = new Date();
  const date = recentDate();

  const header =
    "date,page_name,sessions,unique_visitors,bounce_rate,avg_session_duration_sec,pageviews,conversions,conversion_rate,device_type,traffic_source";

  const rows = [header];

  for (let d = 0; d < days; d++) {
    const rowDate = dateOffset(now, d);
    const dayOfWeek = new Date(now.getTime() - d * 86400000).getDay(); // 0=Sun, 6=Sat
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
    const weekdayMultiplier = isWeekend ? 0.55 + Math.random() * 0.15 : 0.9 + Math.random() * 0.2;

    for (const page of pages) {
      const profile = pageProfiles[page];

      // Apply seasonality and some daily noise
      const noiseFactor = 0.8 + Math.random() * 0.4; // 0.8 - 1.2
      const sessions = Math.round(profile.baseSessions * weekdayMultiplier * noiseFactor);
      const uniqueVisitors = Math.round(sessions * (0.7 + Math.random() * 0.15));

      const bounceRate = Math.min(
        0.95,
        Math.max(0.05, profile.bounceBase + (Math.random() - 0.5) * 0.1)
      );

      const avgDuration = Math.max(
        5,
        Math.round(profile.avgDuration + (Math.random() - 0.5) * profile.avgDuration * 0.3)
      );

      const pageviews = Math.round(sessions * profile.pvMultiplier * (0.9 + Math.random() * 0.2));

      const conversionRate = Math.min(
        0.5,
        Math.max(0.001, profile.convBase + (Math.random() - 0.5) * profile.convBase * 0.4)
      );
      const conversions = Math.round(sessions * conversionRate);

      const deviceType = weightedPick(deviceTypes, deviceWeights);
      const trafficSource = weightedPick(trafficSources, trafficWeights);

      const row = [
        rowDate,
        page,
        sessions,
        uniqueVisitors,
        bounceRate.toFixed(4),
        avgDuration,
        pageviews,
        conversions,
        conversionRate.toFixed(4),
        deviceType,
        trafficSource,
      ].join(",");

      rows.push(row);
    }
  }

  const filename = `analytics-daily-metrics-${date}.csv`;

  return { filename, content: rows.join("\n") };
}

/* ------------------------------------------------------------------ */
/*  Generator: Funnel Data                                            */
/* ------------------------------------------------------------------ */

/**
 * Generates a funnel analytics CSV with realistic stage-by-stage drop-off.
 *
 * @returns {{ filename: string, content: string }}
 */
export function generateFunnelData() {
  const date = recentDate();
  const now = new Date();

  const header = "date,funnel_stage,users,drop_off_rate,avg_time_in_stage_sec";

  const rows = [header];

  // Base time-in-stage per funnel step (seconds)
  const stageTimeBase = {
    landing_page: 25,
    signup_start: 45,
    email_verification: 120,
    profile_setup: 90,
    first_action: 60,
    activation: 30,
  };

  for (let d = 0; d < 30; d++) {
    const rowDate = dateOffset(now, d);
    const dayOfWeek = new Date(now.getTime() - d * 86400000).getDay();
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
    const dayMultiplier = isWeekend ? 0.6 + Math.random() * 0.15 : 0.9 + Math.random() * 0.2;

    // Starting users for the day (landing page)
    let users = Math.round((randInt(800, 1500)) * dayMultiplier);

    for (let s = 0; s < funnelStages.length; s++) {
      const stage = funnelStages[s];

      // Drop-off rate: 15-40% per stage (first stage has 0 drop-off — it's the entry)
      let dropOffRate;
      if (s === 0) {
        dropOffRate = 0;
      } else {
        // Later stages tend to have lower drop-off (committed users)
        const baseDropOff = 0.15 + Math.random() * 0.25;
        // email_verification typically has higher drop-off
        const stageAdjust = stage === "email_verification" ? 0.08 : 0;
        dropOffRate = Math.min(0.40, baseDropOff + stageAdjust);
      }

      if (s > 0) {
        users = Math.max(1, Math.round(users * (1 - dropOffRate)));
      }

      const avgTime = Math.max(
        5,
        Math.round(stageTimeBase[stage] + (Math.random() - 0.5) * stageTimeBase[stage] * 0.4)
      );

      const row = [
        rowDate,
        stage,
        users,
        dropOffRate.toFixed(4),
        avgTime,
      ].join(",");

      rows.push(row);
    }
  }

  const filename = `analytics-funnel-${date}.csv`;

  return { filename, content: rows.join("\n") };
}

/* ------------------------------------------------------------------ */
/*  Generator: A/B Test Results                                       */
/* ------------------------------------------------------------------ */

/**
 * Generates an A/B test results CSV with realistic statistical data.
 *
 * @returns {{ filename: string, content: string }}
 */
export function generateABTestResults() {
  const date = recentDate();
  const topic = pick(topics);

  const header =
    "variant,metric,value,sample_size,confidence_interval_lower,confidence_interval_upper,p_value,significant";

  const rows = [header];

  // Baseline values for control group per metric
  const controlBaselines = {
    click_through_rate: { value: 0.12, scale: 0.03 },
    signup_rate: { value: 0.08, scale: 0.02 },
    time_on_page_sec: { value: 65, scale: 15 },
    bounce_rate: { value: 0.42, scale: 0.06 },
    task_completion_rate: { value: 0.71, scale: 0.08 },
  };

  // variant_a shows improvement on some metrics, variant_b is mixed
  const variantEffects = {
    variant_a: {
      click_through_rate: 0.03,      // positive lift
      signup_rate: 0.015,            // positive lift
      time_on_page_sec: 8,          // more time = engagement
      bounce_rate: -0.06,           // lower bounce = better
      task_completion_rate: 0.05,   // positive lift
    },
    variant_b: {
      click_through_rate: 0.005,    // marginal
      signup_rate: -0.005,          // slightly worse
      time_on_page_sec: -3,         // slightly less
      bounce_rate: -0.02,           // slightly better
      task_completion_rate: 0.02,   // marginal improvement
    },
  };

  // Metrics where variant_a should show statistical significance
  const significantMetrics = new Set([
    "click_through_rate",
    "bounce_rate",
    "task_completion_rate",
  ]);

  for (const variant of abVariants) {
    const sampleSize = randInt(2500, 5000);

    for (const metric of abMetrics) {
      const baseline = controlBaselines[metric];
      let value;
      let pValue;
      let significant;

      if (variant === "control") {
        // Control values with small noise
        value = baseline.value + (Math.random() - 0.5) * baseline.scale * 0.2;
        // Control vs. itself — p-value is high (not significant)
        pValue = 0.5 + Math.random() * 0.49;
        significant = false;
      } else {
        const effect = variantEffects[variant][metric];
        // Apply effect with some noise
        value = baseline.value + effect + (Math.random() - 0.5) * baseline.scale * 0.3;

        if (variant === "variant_a" && significantMetrics.has(metric)) {
          // Significant result
          pValue = Math.random() * 0.04 + 0.001; // 0.001 - 0.041
          significant = true;
        } else if (variant === "variant_a") {
          // Trending but not significant
          pValue = 0.05 + Math.random() * 0.25; // 0.05 - 0.30
          significant = false;
        } else {
          // variant_b — mostly not significant
          pValue = 0.1 + Math.random() * 0.85; // 0.10 - 0.95
          significant = pValue < 0.05;
        }
      }

      // Ensure non-negative for rate metrics
      if (metric !== "time_on_page_sec") {
        value = Math.max(0.001, Math.min(0.99, value));
      } else {
        value = Math.max(5, value);
      }

      // Confidence interval: width proportional to noise and sample size
      const ciHalfWidth = baseline.scale / Math.sqrt(sampleSize / 1000) * (0.8 + Math.random() * 0.4);
      const ciLower = value - ciHalfWidth;
      const ciUpper = value + ciHalfWidth;

      // Format values: rates to 4 decimals, time_on_page_sec to 1 decimal
      let formattedValue, formattedCILower, formattedCIUpper;
      if (metric === "time_on_page_sec") {
        formattedValue = value.toFixed(1);
        formattedCILower = ciLower.toFixed(1);
        formattedCIUpper = ciUpper.toFixed(1);
      } else {
        formattedValue = value.toFixed(4);
        formattedCILower = ciLower.toFixed(4);
        formattedCIUpper = ciUpper.toFixed(4);
      }

      const row = [
        variant,
        metric,
        formattedValue,
        sampleSize,
        formattedCILower,
        formattedCIUpper,
        pValue.toFixed(4),
        significant ? "true" : "false",
      ].join(",");

      rows.push(row);
    }
  }

  const filename = `analytics-ab-test-${date}.csv`;

  return { filename, content: rows.join("\n") };
}

export default { generateDailyMetrics, generateFunnelData, generateABTestResults };
