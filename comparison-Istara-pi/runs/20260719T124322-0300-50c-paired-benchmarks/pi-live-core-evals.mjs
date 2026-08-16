
import { createModels } from "file:///Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement/node_modules/@earendil-works/pi-ai/dist/index.js";
import { deepseekProvider } from "file:///Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement/node_modules/@earendil-works/pi-ai/dist/providers/deepseek.js";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";

function textFromAssistant(message) {
  return (message?.content ?? []).filter((block) => block.type === "text").map((block) => block.text).join("\n");
}
function readKey() {
  const result = spawnSync("security", ["find-generic-password", "-a", "openclaw", "-s", "istara-pi-deepseek", "-w"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  return result.status === 0 ? result.stdout.trim() : "";
}
const cases = JSON.parse(readFileSync(process.argv[2], "utf8")).live_cases.slice(0, 3);
const key = readKey();
const results = [];
if (!key) {
  console.log(JSON.stringify({ ok: false, error: "DeepSeek key unavailable", results }, null, 2));
  process.exit(2);
}
try {
  process.env.DEEPSEEK_API_KEY = key;
  const models = createModels();
  models.setProvider(deepseekProvider());
  const model = models.getModel("deepseek", "deepseek-v4-pro");
  if (!model) throw new Error("deepseek-v4-pro missing from Pi provider");
  for (const item of cases) {
    const started = Date.now();
    const systemPrompt = item.messages.filter((m) => m.role === "system").map((m) => m.content).join("\n");
    const messages = item.messages.filter((m) => m.role !== "system").map((m) => ({ role: m.role, content: m.content, timestamp: Date.now() }));
    try {
      const response = await models.completeSimple(model, { systemPrompt, messages }, { reasoning: "high", maxTokens: Math.min(item.max_tokens ?? 128, 180), timeoutMs: 35000, maxRetries: 0, cacheRetention: "none" });
      results.push({ case_id: item.id, ok: response.stopReason === "stop", provider: response.provider, responseModel: response.responseModel, stopReason: response.stopReason, latency_ms: Date.now() - started, usage: response.usage ?? {}, capped_text: textFromAssistant(response).slice(0, 500) });
    } catch (error) {
      results.push({ case_id: item.id, ok: false, latency_ms: Date.now() - started, error: error?.name ?? "Error", capped_text: "" });
    }
  }
} finally {
  delete process.env.DEEPSEEK_API_KEY;
}
console.log(JSON.stringify({ ok: results.every((r) => r.ok), results }, null, 2));
