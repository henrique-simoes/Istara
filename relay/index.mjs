#!/usr/bin/env node
/**
 * ReClaw Relay — Donate LLM compute to the ReClaw network.
 *
 * Connects outbound via WebSocket (NAT-friendly — no inbound ports needed).
 * Reports hardware stats and forwards LLM requests to local Ollama/LM Studio.
 *
 * Usage:
 *   reclaw-relay --server ws://your-server:8000/ws/relay --token <jwt>
 */

import { program } from "commander";
import { createConnection } from "./lib/connection.mjs";
import { StateMachine } from "./lib/state-machine.mjs";
import { startHeartbeat, getSystemStats } from "./lib/heartbeat.mjs";
import { LLMProxy } from "./lib/llm-proxy.mjs";
import { decodeConnectionString } from "./lib/connection-string.mjs";

program
  .name("reclaw-relay")
  .description("ReClaw Relay — donate LLM compute to the network")
  .version("0.1.0")
  .option("-s, --server <url>", "ReClaw server WebSocket URL", "ws://localhost:8000/ws/relay")
  .option("-t, --token <jwt>", "JWT authentication token", "")
  .option("-c, --connection-string <string>", "Connection string (replaces --server and --token)")
  .option("-p, --provider <type>", "LLM provider: ollama or lmstudio", "ollama")
  .option("-h, --llm-host <url>", "Local LLM server URL", "http://localhost:11434")
  .option("-i, --heartbeat-interval <seconds>", "Heartbeat interval", "30")
  .parse();

const opts = program.opts();

// If connection string provided, decode and override server/token
if (opts.connectionString) {
  const decoded = decodeConnectionString(opts.connectionString);
  if (!decoded) {
    console.error("❌ Invalid or expired connection string.");
    process.exit(1);
  }
  opts.server = decoded.wsUrl || decoded.serverUrl;
  opts.token = decoded.jwt;
  // Store network token for X-Access-Token header
  opts.networkToken = decoded.networkToken;
  console.log(`🔗 ReClaw Relay starting (from connection string)...`);
  console.log(`   Server: ${opts.server}`);
  console.log(`   Label: ${decoded.label || "unnamed"}`);
} else {
  console.log("🔗 ReClaw Relay starting...");
  console.log(`   Server: ${opts.server}`);
}
console.log(`   Provider: ${opts.provider}`);
console.log(`   LLM Host: ${opts.llmHost}`);

const stateMachine = new StateMachine();
const llmProxy = new LLMProxy(opts.provider, opts.llmHost);

// Gather initial system info for registration
const stats = await getSystemStats();

const ws = createConnection(opts.server, {
  token: opts.token,
  networkToken: opts.networkToken || "",
  onOpen: async () => {
    console.log("✅ Connected to ReClaw server");
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
