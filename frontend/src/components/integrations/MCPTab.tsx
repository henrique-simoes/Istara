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
          <button onClick={() => setShowPolicyEditor(false)} className="text-sm text-istara-600 hover:text-istara-700 dark:text-istara-400 transition-colors">
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
          <button onClick={() => setShowAuditLog(false)} className="text-sm text-istara-600 hover:text-istara-700 dark:text-istara-400 transition-colors">
            &larr; Back to MCP
          </button>
        </div>
        <MCPAuditLog />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">
      {/* Section 1: Istara as MCP Server */}
      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Istara as MCP Server</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Expose Istara&apos;s tools and findings to external MCP clients.
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
              Connect to external MCP servers to extend Istara with additional tools.
            </p>
          </div>
          <button
            onClick={() => setShowServerSetup(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors"
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
              className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors"
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

      {/* Section 3: Featured MCP Servers */}
      <FeaturedServersSection onConnect={async () => { await fetchMCPClients(); }} />

      {/* Section 4: Connection Guide */}
      <section>
        <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-3">Connection Guide</h2>
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5">
          <div className="space-y-4 text-sm text-slate-600 dark:text-slate-400">
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white mb-1">As MCP Server</h3>
              <p>
                When enabled, Istara exposes its research tools (findings search, document access, skill execution)
                via the MCP protocol. External tools like Claude Desktop can connect and use Istara&apos;s capabilities.
              </p>
            </div>
            <div>
              <h3 className="font-medium text-slate-900 dark:text-white mb-1">As MCP Client</h3>
              <p>
                Connect to external MCP servers to give Istara access to additional tools. After adding a server,
                use &ldquo;Discover Tools&rdquo; to see available capabilities. Istara agents can then call these tools during task execution.
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

// --- Featured Servers Section ---

function FeaturedServersSection({ onConnect }: { onConnect: () => Promise<void> }) {
  const [featured, setFeatured] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [connectResult, setConnectResult] = useState<{ id: string; message: string } | null>(null);

  useEffect(() => {
    mcpApi.featured.list().then((list) => { setFeatured(list); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const handleConnect = async (serverId: string) => {
    setConnecting(serverId);
    try {
      const result = await mcpApi.featured.connect(serverId);
      setConnectResult({ id: serverId, message: result.message || "Connected!" });
      await onConnect();
    } catch (e: any) {
      setConnectResult({ id: serverId, message: `Setup needed: ${e.message}` });
    } finally {
      setConnecting(null);
    }
  };

  if (loading) return null;
  if (featured.length === 0) return null;

  return (
    <section>
      <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Featured MCP Servers</h2>
      <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
        Pre-configured servers you can connect with one click.
      </p>
      <div className="space-y-3">
        {featured.map((server) => (
          <div
            key={server.id}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden"
          >
            <div className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">🇧🇷</span>
                    <h3 className="font-semibold text-slate-900 dark:text-white">{server.name}</h3>
                    <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                      {server.tool_count} tools
                    </span>
                    <span className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 rounded-full">
                      MIT
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">{server.description}</p>
                  <div className="flex flex-wrap gap-1 mb-2">
                    {(server.categories || []).slice(0, 6).map((cat: string) => (
                      <span key={cat} className="px-1.5 py-0.5 text-[10px] bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400 rounded">
                        {cat}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => setExpanded(expanded === server.id ? null : server.id)}
                    className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  >
                    {expanded === server.id ? "Less" : "Details"}
                  </button>
                  <button
                    onClick={() => handleConnect(server.id)}
                    disabled={connecting === server.id}
                    className={cn(
                      "px-4 py-1.5 text-xs font-medium rounded-lg transition-colors",
                      connecting === server.id
                        ? "bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
                        : "bg-istara-600 text-white hover:bg-istara-700"
                    )}
                  >
                    {connecting === server.id ? "Connecting..." : "Connect"}
                  </button>
                </div>
              </div>

              {connectResult && connectResult.id === server.id && (
                <div className={cn(
                  "mt-2 px-3 py-2 rounded-lg text-xs",
                  connectResult.message.includes("Setup") || connectResult.message.includes("error")
                    ? "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
                    : "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300"
                )}>
                  {connectResult.message}
                  {server.http_command && connectResult.message.includes("Setup") && (
                    <div className="mt-1 font-mono text-[10px] bg-slate-100 dark:bg-slate-800 p-1.5 rounded">
                      pip install {server.package} && {server.http_command}
                    </div>
                  )}
                </div>
              )}
            </div>

            {expanded === server.id && (
              <div className="border-t border-slate-200 dark:border-slate-800 p-4 space-y-3 bg-slate-50 dark:bg-slate-800/50">
                <div>
                  <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 uppercase tracking-wider">Data Sources ({server.features?.length || 0})</h4>
                  <div className="grid grid-cols-2 gap-1">
                    {(server.features || []).map((f: any) => (
                      <div key={f.name} className="text-xs text-slate-600 dark:text-slate-400">
                        <span className="font-medium text-slate-800 dark:text-slate-200">{f.name}</span> — {f.description}
                      </div>
                    ))}
                  </div>
                </div>
                {server.ux_research_applications && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 uppercase tracking-wider">UX Research Applications</h4>
                    <ul className="space-y-1">
                      {server.ux_research_applications.map((app: string, i: number) => (
                        <li key={i} className="text-xs text-slate-600 dark:text-slate-400 flex items-start gap-1.5">
                          <span className="text-istara-500 mt-0.5 shrink-0">+</span>
                          {app}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {server.env_vars && server.env_vars.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 uppercase tracking-wider">Optional API Keys</h4>
                    {server.env_vars.map((v: any) => (
                      <div key={v.name} className="text-xs text-slate-600 dark:text-slate-400">
                        <code className="text-[10px] bg-slate-200 dark:bg-slate-700 px-1 py-0.5 rounded">{v.name}</code> — {v.description}
                        {!v.required && <span className="text-slate-400 ml-1">(optional)</span>}
                      </div>
                    ))}
                  </div>
                )}
                <div className="flex items-center gap-3 pt-1">
                  <a href={server.repository} target="_blank" rel="noopener noreferrer" className="text-xs text-istara-600 hover:text-istara-700 dark:text-istara-400 underline">
                    GitHub Repository
                  </a>
                  <span className="text-xs text-slate-400">Install: pip install {server.package}</span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
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
            className="p-1.5 rounded-lg text-slate-400 hover:text-istara-600 hover:bg-istara-50 dark:hover:bg-istara-900/20 transition-colors disabled:opacity-50"
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
