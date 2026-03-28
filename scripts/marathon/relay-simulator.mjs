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
 */

import WebSocket from "ws";

const SERVER = process.env.RECLAW_SERVER || "ws://localhost:8000/ws/relay";
const args = process.argv.slice(2);
const duration = args.includes("--duration") ? parseInt(args[args.indexOf("--duration") + 1]) || 30 : 30;
const nodeCount = args.includes("--nodes") ? parseInt(args[args.indexOf("--nodes") + 1]) || 1 : 1;

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
    const ws = new WebSocket(SERVER);
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
              content: "[Simulated response from relay node]",
              model: nodeConfig.loaded_models[0],
            }));
          }, 500);
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
  console.log(`\n🖥️  ReClaw Relay Node Simulator`);
  console.log(`   Server: ${SERVER}`);
  console.log(`   Nodes: ${Math.min(nodeCount, SIMULATED_NODES.length)}`);
  console.log(`   Duration: ${duration}s\n`);

  const nodes = SIMULATED_NODES.slice(0, nodeCount);
  const promises = nodes.map((config, i) => connectNode(config, i + 1));
  await Promise.all(promises);
  console.log(`\n✅ Simulation complete.\n`);
}

main().catch(console.error);
