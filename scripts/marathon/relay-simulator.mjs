#!/usr/bin/env node
/**
 * Relay Node Simulator — simulates a remote compute node for testing.
 *
 * Sends registration and heartbeat messages via WebSocket to test:
 * - WebSocket connection acceptance
 * - Node registration in compute pool
 * - Heartbeat tracking and scoring
 * - Node disconnect/reconnect behavior
 *
 * Usage:
 *   node scripts/marathon/relay-simulator.mjs                    # Default settings
 *   node scripts/marathon/relay-simulator.mjs --duration 60      # Run for 60 seconds
 *   node scripts/marathon/relay-simulator.mjs --nodes 3          # Simulate 3 nodes
 *   node scripts/marathon/relay-simulator.mjs --connection-string rcl_...
 */

import WebSocket from "ws";
import { decodeConnectionString } from "../../relay/lib/connection-string.mjs";

const args = process.argv.slice(2);

function argValue(name, fallback = "") {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] || fallback : fallback;
}

const connectionString = argValue("--connection-string", process.env.ISTARA_CONNECTION_STRING || "");
const decodedConnection = connectionString ? decodeConnectionString(connectionString) : null;

function deriveRelayWsUrl(url) {
  if (!url) return "";
  let relayUrl = url.replace(/^https:\/\//, "wss://").replace(/^http:\/\//, "ws://");
  if (!relayUrl.endsWith("/ws/relay")) relayUrl = `${relayUrl.replace(/\/+$/, "")}/ws/relay`;
  return relayUrl;
}

const SERVER = decodedConnection?.wsUrl
  || deriveRelayWsUrl(decodedConnection?.serverUrl || "")
  || process.env.ISTARA_SERVER
  || "ws://localhost:8000/ws/relay";
const networkToken = argValue(
  "--network-token",
  decodedConnection?.networkToken || process.env.ISTARA_NETWORK_TOKEN || "",
);
const jwtToken = argValue("--token", decodedConnection?.jwt || process.env.ISTARA_RELAY_JWT || "");
const duration = parseInt(argValue("--duration", "30"), 10) || 30;
const nodeCount = parseInt(argValue("--nodes", "1"), 10) || 1;

const SIMULATED_NODES = [
  {
    hostname: "sim-workstation-01.local",
    ram_total_gb: 32,
    cpu_cores: 12,
    gpu_name: "NVIDIA RTX 4080",
    gpu_vram_mb: 16384,
    loaded_models: ["google/gemma-3-12b", "nomic-embed-text"],
    provider_type: "lmstudio",
    provider_host: "http://192.168.1.50:1234",
  },
  {
    hostname: "sim-laptop-02.local",
    ram_total_gb: 16,
    cpu_cores: 8,
    gpu_name: "Apple M3 Pro",
    gpu_vram_mb: 18432,
    loaded_models: ["qwen3:latest"],
    provider_type: "ollama",
    provider_host: "http://192.168.1.51:11434",
  },
  {
    hostname: "sim-server-03.local",
    ram_total_gb: 64,
    cpu_cores: 24,
    gpu_name: "NVIDIA A100",
    gpu_vram_mb: 40960,
    loaded_models: ["llama-3.1-70b", "nomic-embed-text"],
    provider_type: "ollama",
    provider_host: "http://192.168.1.52:11434",
  },
];

function connectNode(nodeConfig, nodeIndex) {
  return new Promise((resolve) => {
    console.log(`  [Node ${nodeIndex}] Connecting to ${SERVER}...`);
    const headers = {};
    if (networkToken) headers["X-Access-Token"] = networkToken;
    if (jwtToken) headers.Authorization = `Bearer ${jwtToken}`;
    const ws = new WebSocket(SERVER, { headers });
    let heartbeatInterval = null;
    let nodeId = null;

    ws.on("open", () => {
      console.log(`  [Node ${nodeIndex}] Connected! Sending registration...`);
      ws.send(JSON.stringify({
        type: "register",
        user_id: `sim-node-${nodeIndex}`,
        ...nodeConfig,
      }));
    });

    ws.on("message", (data) => {
      try {
        const msg = JSON.parse(data.toString());
        if (msg.type === "registered" || msg.node_id) {
          nodeId = msg.node_id || `sim-${nodeIndex}`;
          console.log(`  [Node ${nodeIndex}] Registered as ${nodeId}`);

          // Start heartbeats
          heartbeatInterval = setInterval(() => {
            const ramUsed = Math.random() * nodeConfig.ram_total_gb * 0.6;
            ws.send(JSON.stringify({
              type: "heartbeat",
              node_id: nodeId,
              ram_available_gb: Math.round((nodeConfig.ram_total_gb - ramUsed) * 10) / 10,
              cpu_load_pct: Math.round(Math.random() * 60 + 10),
              loaded_models: nodeConfig.loaded_models,
              state: "idle",
            }));
          }, 5000); // Heartbeat every 5s (faster than real 30s for testing)
        } else if (msg.type === "llm_request") {
          console.log(`  [Node ${nodeIndex}] Received LLM request: ${msg.request_id}`);
          // Simulate processing delay
          setTimeout(() => {
            ws.send(JSON.stringify({
              type: "llm_response",
              request_id: msg.request_id,
              result: {
                message: {
                  role: "assistant",
                  content: "[Simulated response from relay node]",
                },
                model: nodeConfig.loaded_models[0],
              },
            }));
          }, 500);
        } else if (msg.type === "embed_request") {
          ws.send(JSON.stringify({
            type: "embed_response",
            request_id: msg.request_id,
            result: [0.1, 0.2, 0.3],
          }));
        } else if (msg.type === "load_model_request") {
          const loaded = Array.from(new Set([...nodeConfig.loaded_models, msg.model].filter(Boolean)));
          nodeConfig.loaded_models = loaded;
          ws.send(JSON.stringify({
            type: "load_model_response",
            request_id: msg.request_id,
            result: {
              models: loaded,
              model_capabilities: {},
            },
          }));
        }
      } catch { /* ignore parse errors */ }
    });

    ws.on("error", (err) => {
      console.log(`  [Node ${nodeIndex}] Error: ${err.message}`);
    });

    ws.on("close", () => {
      console.log(`  [Node ${nodeIndex}] Disconnected`);
      if (heartbeatInterval) clearInterval(heartbeatInterval);
      resolve();
    });

    // Auto-disconnect after duration
    setTimeout(() => {
      console.log(`  [Node ${nodeIndex}] Duration reached, disconnecting...`);
      if (heartbeatInterval) clearInterval(heartbeatInterval);
      ws.close();
      resolve();
    }, duration * 1000);
  });
}

async function main() {
  console.log(`\n🖥️  Istara Relay Node Simulator`);
  console.log(`   Server: ${SERVER}`);
  console.log(`   Nodes: ${Math.min(nodeCount, SIMULATED_NODES.length)}`);
  console.log(`   Duration: ${duration}s\n`);
  console.log(`   Auth: ${networkToken ? "network token" : jwtToken ? "JWT" : "none"}\n`);

  const nodes = SIMULATED_NODES.slice(0, nodeCount);
  const promises = nodes.map((config, i) => connectNode(config, i + 1));
  await Promise.all(promises);
  console.log(`\n✅ Simulation complete.\n`);
}

main().catch(console.error);
