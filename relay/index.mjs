#!/usr/bin/env node
/**
 * Istara Relay — Donate LLM compute to the Istara network.
 *
 * Connects outbound via WebSocket (NAT-friendly — no inbound ports needed).
 * Reports hardware stats and forwards LLM requests to local Ollama/LM Studio.
 *
 * Usage:
 *   istara-relay --server ws://your-server:8000/ws/relay --token <jwt>
 */

import fs from "fs";
import { program } from "commander";
import { createConnection } from "./lib/connection.mjs";
import { StateMachine } from "./lib/state-machine.mjs";
import { startHeartbeat, getSystemStats } from "./lib/heartbeat.mjs";
import { LLMProxy } from "./lib/llm-proxy.mjs";
import { decodeConnectionString } from "./lib/connection-string.mjs";

program
  .name("istara-relay")
  .description("Istara Relay — donate LLM compute to the network")
  .version((() => { try { return fs.readFileSync(new URL('../VERSION', import.meta.url), 'utf8').trim(); } catch { return 'dev'; } })())
  .option("-s, --server <url>", "Istara server WebSocket URL", "ws://localhost:8000/ws/relay")
  .option("-t, --token <jwt>", "JWT authentication token", "")
  .option("-c, --connection-string <string>", "Connection string (replaces --server and --token)")
  .option("-p, --provider <type>", "LLM provider: ollama or lmstudio", "ollama")
  .option("-h, --llm-host <url>", "Local LLM server URL", "http://localhost:11434")
  .option("-k, --llm-api-key <key>", "API key for local LLM server (if auth required)", "")
  .option("-i, --heartbeat-interval <seconds>", "Heartbeat interval", "30")
  .parse();

const opts = program.opts();

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
  if (!opts.server && config.ws_url) opts.server = config.ws_url;
  if (!opts.token && config.token) opts.token = config.token;
  
  console.log("🔗 Istara Relay starting...");
  console.log(`   Server: ${opts.server}`);
}
console.log(`   Provider: ${opts.provider}`);
console.log(`   LLM Host: ${opts.llmHost}`);

const stateMachine = new StateMachine();
const llmProxy = new LLMProxy(opts.provider, opts.llmHost, opts.llmApiKey);

// Gather initial system info for registration
const stats = await getSystemStats();

const ws = createConnection(opts.server, {
  token: opts.token,
  networkToken: opts.networkToken || "",
  onOpen: async () => {
    console.log("✅ Connected to Istara server");
    stateMachine.transition("idle");

    // Register with server
    const models = await llmProxy.listModels();
    ws.send(JSON.stringify({
      type: "register",
      hostname: stats.hostname,
      user_id: opts.token ? "authenticated" : "anonymous",
      ram_total_gb: stats.ram_total_gb,
      cpu_cores: stats.cpu_cores,
      gpu_name: stats.gpu_name,
      gpu_vram_mb: stats.gpu_vram_mb,
      loaded_models: models,
      provider_type: opts.provider,
      provider_host: opts.llmHost,
    }));

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
