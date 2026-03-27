"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Shield, Plug, Plus, Server, RefreshCw, Trash2, Wrench, Activity } from "lucide-react";
import { mcp as mcpApi } from "@/lib/api";
import { useIntegrationsStore } from "@/stores/integrationsStore";
import { cn } from "@/lib/utils";
import MCPAccessPolicyEditor from "./MCPAccessPolicyEditor";
import MCPAuditLog from "./MCPAuditLog";
import MCPServerSetup from "./MCPServerSetup";
import type { MCPServerConfig } from "@/lib/types";

export default function MCPTab() {
  const { mcpServerStatus, mcpClients, mcpLoading, fetchMCPStatus, fetchMCPClients } = useIntegrationsStore();
  const [showServerSetup, setShowServerSetup] = useState(false);
  const [showPolicyEditor, setShowPolicyEditor] = useState(false);
  const [showAuditLog, setShowAuditLog] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [confirmToggle, setConfirmToggle] = useState(false);
  const [discovering, setDiscovering] = useState<string | null>(null);

  useEffect(() => {
    fetchMCPStatus();
    fetchMCPClients();
  }, [fetchMCPStatus, fetchMCPClients]);

  const handleToggleServer = async () => {
    if (!confirmToggle) {
      setConfirmToggle(true);
      return;
    }
    setToggling(true);
    try {
      const enabled = !mcpServerStatus?.enabled;
      await mcpApi.server.toggle(enabled);
      await fetchMCPStatus();
    } catch {
      // silent
    } finally {
      setToggling(false);
      setConfirmToggle(false);
    }
  };

  const handleDiscover = async (clientId: string) => {
    setDiscovering(clientId);
    try {
      await mcpApi.clients.discover(clientId);
      await fetchMCPClients();
    } catch {
      // silent
    } finally {
      setDiscovering(null);
    }
  };

  const handleDeleteClient = async (clientId: string) => {
    try {
      await mcpApi.clients.delete(clientId);
      await fetchMCPClients();
    } catch {
      // silent
    }
  };

  const serverEnabled = mcpServerStatus?.enabled;

  if (showServerSetup) {
    return (
      <MCPServerSetup
        onClose={() => {
          setShowServerSetup(false);
          fetchMCPClients();
        }}
      />
    );
  }

  if (showPolicyEditor) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-800">
          <button onClick={() => setShowPolicyEditor(false)} className="text-sm text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400 transition-colors">
            &larr; Back to MCP
          </button>
        </div>
        <MCPAccessPolicyEditor />
      </div>
    );
  }

  if (showAuditLog) {
    return (
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-3 border-b border-slate-200 dark:border-slate-800">
          <button onClick={() => setShowAuditLog(false)} className="text-sm text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400 transition-colors">
            &larr; Back to MCP
          </button>
        </div>
        <MCPAuditLog />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      {/* Section 1: ReClaw as MCP Server */}
      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">ReClaw as MCP Server</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Expose ReClaw&apos;s tools and findings to external MCP clients.
        </p>

        {/* Warning banner */}
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-1">Security Warning</p>
              <p className="text-sm text-amber-700 dark:text-amber-300">
                Enabling the MCP server exposes your research data to external tools. Ensure you configure
                access policies before activating. Only enable this if you understand the implications.
              </p>
            </div>
          </div>
        </div>

        {/* Toggle */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={cn(
                "w-3 h-3 rounded-full",
                serverEnabled ? "bg-green-500" : "bg-slate-300 dark:bg-slate-600"
              )} />
              <div>
                <span className="text-sm font-medium text-slate-900 dark:text-white">
                  MCP Server: {serverEnabled ? "Enabled" : "Disabled"}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {confirmToggle && (
                <span className="text-xs text-amber-600 dark:text-amber-400">Click again to confirm</span>
              )}
              <button
                onClick={handleToggleServer}
                disabled={toggling}
                className={cn(
                  "px-3 py-1.5 text-xs rounded-lg transition-colors disabled:opacity-50",
                  serverEnabled
                    ? "bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400"
                    : "bg-green-50 text-green-600 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400"
                )}
              >
                {toggling ? "..." : serverEnabled ? "Disable" : "Enable"}
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowPolicyEditor(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              <Shield size={12} /> Access Policy
            </button>
            <button
              onClick={() => setShowAuditLog(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              <Activity size={12} /> Audit Log
            </button>
          </div>
        </div>
      </section>

      {/* Section 2: Connected MCP Servers */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Connected MCP Servers</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Connect to external MCP servers to extend ReClaw with additional tools.
            </p>
          </div>
          <button
            onClick={() => setShowServerSetup(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
          >
            <Plus size={14} />
            Add Server
          </button>
        </div>

        {mcpLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="h-20 rounded-xl bg-slate-100 dark:bg-slate-800 animate-pulse" />
            ))}
          </div>
        ) : mcpClients.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
            <Server size={32} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">No MCP servers connected</p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mb-4">
              Add an MCP server to discover and use external tools.
            </p>
            <button
              onClick={() => setShowServerSetup(true)}
              className="px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 transition-colors"
            >
              Add First Server
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {mcpClients.map((client) => (
              <MCPClientCard
                key={client.id}
                client={client}
                onDiscover={handleDiscover}
                onDelete={handleDeleteClient}
                discovering={discovering === client.id}
              />
            ))}
          </div>
        )}
      </section>

      {/* Section 3: Connection Guide */}
      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-3">Connection Guide</h2>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5">
          <div className="space-y-4 text-sm text-slate-600 dark:text-slate-400">
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white mb-1">As MCP Server</h3>
              <p>
                When enabled, ReClaw exposes its research tools (findings search, document access, skill execution)
                via the MCP protocol. External tools like Claude Desktop can connect and use ReClaw&apos;s capabilities.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white mb-1">As MCP Client</h3>
              <p>
                Connect to external MCP servers to give ReClaw access to additional tools. After adding a server,
                use &ldquo;Discover Tools&rdquo; to see available capabilities. ReClaw agents can then call these tools during task execution.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white mb-1">Supported Transports</h3>
              <p>HTTP (recommended), WebSocket, and stdio are supported. HTTP is the most reliable for remote servers.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

// --- MCP Client Card ---

function MCPClientCard({
  client,
  onDiscover,
  onDelete,
  discovering,
}: {
  client: MCPServerConfig;
  onDiscover: (id: string) => void;
  onDelete: (id: string) => void;
  discovering: boolean;
}) {
  const healthColor = client.health_status === "healthy" ? "bg-green-500" :
    client.health_status === "unhealthy" ? "bg-red-500" : "bg-yellow-500";

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={cn("w-2 h-2 rounded-full shrink-0", healthColor)} />
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white">{client.name}</h3>
          <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 uppercase">
            {client.transport}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onDiscover(client.id)}
            disabled={discovering}
            aria-label="Discover tools"
            className="p-1.5 rounded-lg text-slate-400 hover:text-reclaw-600 hover:bg-reclaw-50 dark:hover:bg-reclaw-900/20 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={discovering ? "animate-spin" : ""} />
          </button>
          <button
            onClick={() => onDelete(client.id)}
            aria-label="Remove server"
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-500 dark:text-slate-400 mb-2 truncate">{client.url}</p>

      {client.tools && client.tools.length > 0 ? (
        <div className="flex items-center gap-1 flex-wrap mt-2">
          <Wrench size={12} className="text-slate-400 mr-1" />
          {client.tools.slice(0, 5).map((tool) => (
            <span key={tool.name} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
              {tool.name}
            </span>
          ))}
          {client.tools.length > 5 && (
            <span className="text-[10px] text-slate-400">+{client.tools.length - 5} more</span>
          )}
        </div>
      ) : (
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
          No tools discovered yet. Click refresh to discover.
        </p>
      )}

      {client.last_discovery_at && (
        <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-2">
          Last discovered: {new Date(client.last_discovery_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
