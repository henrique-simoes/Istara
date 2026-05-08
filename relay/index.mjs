#!/usr/bin/env node
/**
 * Istara Relay — Donate LLM compute to the Istara network.
 *
 * Connects outbound via WebSocket (NAT-friendly — no inbound ports needed).
 * Reports hardware stats and forwards LLM requests to local or compatible model servers.
 *
 * Usage:
 *   istara-relay --server ws://your-server:8000/ws/relay --token <jwt>
 */

import fs from "fs";
import { program } from "commander";
import { createConnection } from "./lib/connection.mjs";
import { StateMachine } from "./lib/state-machine.mjs";
import { buildRegistrationPayload, startHeartbeat, getSystemStats } from "./lib/heartbeat.mjs";
import { LLMProxy, detectLocalLLM } from "./lib/llm-proxy.mjs";
import { decodeConnectionString } from "./lib/connection-string.mjs";

program
  .name("istara-relay")
  .description("Istara Relay — donate LLM compute to the network")
  .version((() => { try { return fs.readFileSync(new URL('../VERSION', import.meta.url), 'utf8').trim(); } catch { return 'dev'; } })())
  .option("-s, --server <url>", "Istara server WebSocket URL", "ws://localhost:8000/ws/relay")
  .option("-t, --token <jwt>", "JWT authentication token", "")
  .option("-c, --connection-string <string>", "Connection string (replaces --server and --token)")
  .option("-p, --provider <type>", "LLM provider: ollama, lmstudio, openai_compat, vllm, sglang, llamacpp, mlx, anthropic", "ollama")
  .option("-h, --llm-host <url>", "Local LLM server URL", "http://localhost:11434")
  .option("-k, --llm-api-key <key>", "API key for local LLM server (if auth required)", "")
  .option("-i, --heartbeat-interval <seconds>", "Heartbeat interval", "30")
  .parse();

const opts = program.opts();
const optionSource = (name) => program.getOptionValueSource?.(name) || "default";

// Load config from ~/.istara/config.json if it exists
const configPath = `${process.env.HOME || process.env.USERPROFILE}/.istara/config.json`;
let config = {};
if (fs.existsSync(configPath)) {
  try {
    config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  } catch (err) {
    console.warn(`⚠️  Failed to read config from ${configPath}:`, err.message);
  }
}

// Preference order: CLI arg > config.json > default
const connStr = opts.connectionString || config.connection_string;

// If connection string provided (CLI or config), decode and override
if (connStr) {
  const decoded = decodeConnectionString(connStr);
  if (!decoded) {
    console.error("❌ Invalid or expired connection string.");
    if (!opts.connectionString) process.exit(1);
    // If it came from config, maybe continue with other opts? 
    // Usually better to fail if a saved string is broken.
    process.exit(1);
  }
  opts.server = decoded.wsUrl || decoded.serverUrl;
  opts.token = decoded.jwt;
  opts.networkToken = decoded.networkToken;
  console.log(`🔗 Istara Relay starting (from connection string)...`);
  console.log(`   Server: ${opts.server}`);
  console.log(`   Label: ${decoded.label || "unnamed"}`);
} else {
  // Use config values for individual opts if available
  if (optionSource("server") === "default" && config.ws_url) opts.server = config.ws_url;
  if (!opts.token && config.token) opts.token = config.token;
  
  console.log("🔗 Istara Relay starting...");
  console.log(`   Server: ${opts.server}`);
}

const stateMachine = new StateMachine();

const configProvider = config.provider || config.llm_provider || "";
const configHost = config.llm_host || config.llmHost || "";
const configApiKey = config.llm_api_key || config.llmApiKey || "";
const providerWasConfigured = optionSource("provider") !== "default" || Boolean(configProvider);
const hostWasConfigured = optionSource("llmHost") !== "default" || Boolean(configHost);

if (optionSource("provider") === "default" && configProvider) {
  opts.provider = configProvider;
}
if (optionSource("llmHost") === "default" && configHost) {
  opts.llmHost = configHost;
}
if (optionSource("llmApiKey") === "default" && configApiKey) {
  opts.llmApiKey = configApiKey;
}
if (!hostWasConfigured && providerWasConfigured) {
  const defaultHosts = {
    ollama: "http://localhost:11434",
    lmstudio: "http://localhost:1234",
    llamacpp: "http://localhost:8080",
    vllm: "http://localhost:8000",
    sglang: "http://localhost:30000",
    mlx: "http://localhost:8080",
    anthropic: "https://api.anthropic.com",
  };
  opts.llmHost = defaultHosts[String(opts.provider || "").toLowerCase()] || opts.llmHost;
}

let initialProbe = null;
if (!providerWasConfigured && !hostWasConfigured) {
  const detected = await detectLocalLLM({ apiKey: opts.llmApiKey });
  if (detected) {
    opts.provider = detected.providerType;
    opts.llmHost = detected.host;
    initialProbe = detected;
    console.log(`   Detected local LLM: ${detected.providerType} at ${detected.host}`);
  } else {
    console.warn(
      "⚠️  No local model server detected yet. The relay will connect in idle mode.",
    );
    console.warn(
      "   Install/start LM Studio, Ollama, llama.cpp, vLLM, SGLang, or MLX, "
      + "then keep this relay running; heartbeats will advertise models once reachable.",
    );
  }
}

const llmProxy = new LLMProxy(opts.provider, opts.llmHost, opts.llmApiKey);
console.log(
  `   Provider: ${llmProxy.providerType}`
  + (llmProxy.providerType !== opts.provider ? ` (inferred from ${opts.llmHost})` : "")
);
console.log(`   LLM Host: ${llmProxy.host}`);

// Gather initial system info for registration
const stats = await getSystemStats();

const ws = createConnection(opts.server, {
  token: opts.token,
  networkToken: opts.networkToken || "",
  onOpen: async () => {
    console.log("✅ Connected to Istara server");
    stateMachine.transition("idle");

    // Register with server
    const modelProbe = initialProbe ?? await llmProxy.probeModels();
    ws.send(JSON.stringify(buildRegistrationPayload({
      stats,
      modelProbe,
      providerType: llmProxy.providerType,
      providerHost: llmProxy.host,
      userId: opts.token ? "authenticated" : "anonymous",
    })));

    // Start heartbeat
    startHeartbeat(ws, parseInt(opts.heartbeatInterval) * 1000, llmProxy);
  },
  onMessage: async (data) => {
    try {
      const msg = JSON.parse(data);

      if (msg.type === "registered") {
        console.log(`📋 Registered as node: ${msg.node_id}`);
      } else if (msg.type === "llm_request") {
        stateMachine.transition("donating");
        try {
          const result = await llmProxy.handleRequest(msg);
          ws.send(JSON.stringify({
            type: "llm_response",
            request_id: msg.request_id,
            result,
          }));
        } catch (err) {
          ws.send(JSON.stringify({
            type: "llm_response",
            request_id: msg.request_id,
            error: err.message,
          }));
        }
        stateMachine.transition("idle");
      } else if (msg.type === "embed_request") {
        stateMachine.transition("donating");
        try {
          const result = await llmProxy.handleEmbedding(msg);
          ws.send(JSON.stringify({
            type: "embed_response",
            request_id: msg.request_id,
            result,
          }));
        } catch (err) {
          ws.send(JSON.stringify({
            type: "embed_response",
            request_id: msg.request_id,
            error: err.message,
          }));
        }
        stateMachine.transition("idle");
      } else if (msg.type === "load_model_request") {
        stateMachine.transition("donating");
        try {
          const result = await llmProxy.loadModel(msg.model, {
            contextLength: msg.context_length,
            allowUnload: msg.allow_unload === true,
          });
          ws.send(JSON.stringify({
            type: "load_model_response",
            request_id: msg.request_id,
            result,
          }));
        } catch (err) {
          ws.send(JSON.stringify({
            type: "load_model_response",
            request_id: msg.request_id,
            error: err.message,
          }));
        }
        stateMachine.transition("idle");
      }
    } catch {
      // Ignore malformed messages
    }
  },
  onClose: () => {
    console.log("❌ Disconnected from server");
    stateMachine.transition("disconnected");
  },
  onError: (err) => {
    console.error("WebSocket error:", err.message);
  },
});

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("\n🛑 Shutting down relay...");
  ws.close();
  process.exit(0);
});

process.on("SIGTERM", () => {
  ws.close();
  process.exit(0);
});
