/** Scenario 65 — Laws of UX: tests for the knowledge base, API, matching, and compliance scoring.
 *
 *  Exercises: /api/laws/*
 */

export const name = "Laws of UX Knowledge Layer";
export const id = "65-laws-of-ux";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. GET /api/laws — returns all 30 laws ──
  let allLaws = [];
  try {
    allLaws = await api.get("/api/laws");
    checks.push({
      name: "GET /api/laws returns 30 laws",
      passed: Array.isArray(allLaws) && allLaws.length === 30,
      detail: `${allLaws.length} laws returned`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/laws returns 30 laws", passed: false, detail: e.message });
  }

  // ── 2. All 4 categories represented ──
  if (allLaws.length) {
    const categories = new Set(allLaws.map((l) => l.category));
    checks.push({
      name: "All 4 categories present (perception, cognitive, behavioral, principles)",
      passed: categories.size === 4 && categories.has("perception") && categories.has("cognitive") && categories.has("behavioral") && categories.has("principles"),
      detail: `Categories: ${[...categories].join(", ")}`,
    });
  }

  // ── 3. Category filter works ──
  try {
    const perception = await api.get("/api/laws?category=perception");
    const list = Array.isArray(perception) ? perception : [];
    checks.push({
      name: "Category filter: perception returns 6 laws",
      passed: list.length === 6,
      detail: `${list.length} perception laws`,
    });
  } catch (e) {
    checks.push({ name: "Category filter: perception returns 6 laws", passed: false, detail: e.message });
  }

  // ── 4. Get single law by ID ──
  try {
    const law = await api.get("/api/laws/proximity");
    checks.push({
      name: "GET /api/laws/proximity returns Law of Proximity",
      passed: law.id === "proximity" && law.name.includes("Proximity"),
      detail: `name=${law.name}, category=${law.category}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/laws/proximity returns Law of Proximity", passed: false, detail: e.message });
  }

  // ── 5. Law has all required fields ──
  if (allLaws.length) {
    const law = allLaws[0];
    const requiredFields = ["id", "name", "category", "description", "origin", "key_takeaways", "related_nielsen_heuristics", "detection_keywords"];
    const hasAll = requiredFields.every((f) => law[f] !== undefined);
    checks.push({
      name: "Laws have all required fields",
      passed: hasAll,
      detail: `Checked: ${requiredFields.join(", ")}`,
    });
  }

  // ── 6. Nielsen heuristic mapping works ──
  try {
    const h4Laws = await api.get("/api/laws/by-heuristic/H4");
    const list = Array.isArray(h4Laws) ? h4Laws : [];
    checks.push({
      name: "Heuristic H4 maps to laws (Jakob's Law, Similarity)",
      passed: list.length >= 1,
      detail: `${list.length} laws related to H4: ${list.map((l) => l.name).join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "Heuristic H4 maps to laws", passed: false, detail: e.message });
  }

  // ── 7. Keyword matching — Fitts's Law ──
  try {
    const matches = await api.get("/api/laws/match?query=button+too+small+hard+to+click+target&top_k=3");
    const list = Array.isArray(matches) ? matches : [];
    const hasFitts = list.some((m) => m.law_id === "fitts-law");
    checks.push({
      name: "Keyword match: 'button too small hard to click' → Fitts's Law",
      passed: hasFitts,
      detail: `Top matches: ${list.map((m) => m.law_id).join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "Keyword match returns Fitts's Law", passed: false, detail: e.message });
  }

  // ── 8. Keyword matching — Hick's Law ──
  try {
    const matches = await api.get("/api/laws/match?query=too+many+options+in+dropdown+menu+choices&top_k=3");
    const list = Array.isArray(matches) ? matches : [];
    const hasHicks = list.some((m) => m.law_id === "hicks-law" || m.law_id === "choice-overload");
    checks.push({
      name: "Keyword match: 'too many options dropdown' → Hick's Law or Choice Overload",
      passed: hasHicks,
      detail: `Top matches: ${list.map((m) => m.law_id).join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "Keyword match returns Hick's Law", passed: false, detail: e.message });
  }

  // ── 9. Compliance endpoint works (empty project) ──
  try {
    const compliance = await api.get("/api/laws/compliance/nonexistent-project-id");
    checks.push({
      name: "Compliance endpoint works for empty project",
      passed: compliance.overall_score !== undefined,
      detail: `overall_score=${compliance.overall_score}`,
    });
  } catch (e) {
    checks.push({ name: "Compliance endpoint works for empty project", passed: false, detail: e.message });
  }

  // ── 10. Radar endpoint works ──
  try {
    const radar = await api.get("/api/laws/compliance/nonexistent-project-id/radar");
    checks.push({
      name: "Radar chart endpoint returns valid structure",
      passed: radar.categories !== undefined && radar.detailed_axes !== undefined,
      detail: `categories=${radar.categories?.length}, axes=${radar.detailed_axes?.length}`,
    });
  } catch (e) {
    checks.push({ name: "Radar chart endpoint returns valid structure", passed: false, detail: e.message });
  }

  // ── 11. Unknown law returns 404 ──
  try {
    await api.get("/api/laws/nonexistent-law-id");
    checks.push({ name: "Unknown law ID returns 404", passed: false, detail: "Should have thrown" });
  } catch (e) {
    checks.push({
      name: "Unknown law ID returns 404",
      passed: e.message.includes("404") || e.message.includes("not found"),
      detail: e.message.slice(0, 80),
    });
  }

  // ── 12. Each law has detection keywords ──
  if (allLaws.length) {
    const allHaveKeywords = allLaws.every((l) => l.detection_keywords && l.detection_keywords.length >= 5);
    checks.push({
      name: "All laws have 5+ detection keywords",
      passed: allHaveKeywords,
      detail: `Min keywords: ${Math.min(...allLaws.map((l) => (l.detection_keywords || []).length))}`,
    });
  }

  // ── 13. UX Law Compliance skill exists ──
  try {
    const skills = await api.get("/api/skills");
    const list = Array.isArray(skills) ? skills : skills?.skills || [];
    const lawSkill = list.find((s) => s.name === "ux-law-compliance");
    checks.push({
      name: "UX Law Compliance Audit skill registered",
      passed: !!lawSkill,
      detail: lawSkill ? `${lawSkill.display_name} (${lawSkill.phase})` : "NOT FOUND",
    });
  } catch (e) {
    checks.push({ name: "UX Law Compliance Audit skill registered", passed: false, detail: e.message });
  }

  // ── 14. Perception cluster has exactly 6 laws ──
  if (allLaws.length) {
    const counts = { perception: 0, cognitive: 0, behavioral: 0, principles: 0 };
    allLaws.forEach((l) => { if (counts[l.category] !== undefined) counts[l.category]++; });
    checks.push({
      name: "Law cluster counts correct (6/7/9/8)",
      passed: counts.perception === 6 && counts.cognitive === 7 && counts.behavioral === 9 && counts.principles === 8,
      detail: `P=${counts.perception}, C=${counts.cognitive}, B=${counts.behavioral}, Pr=${counts.principles}`,
    });
  }

  // ── 15. Attribution present ──
  if (allLaws.length && allLaws[0].origin) {
    checks.push({
      name: "Laws include origin/attribution data",
      passed: true,
      detail: `First law origin: ${allLaws[0].origin.author} (${allLaws[0].origin.year})`,
    });
  }

  return checks;
}
