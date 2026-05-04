"use client";

import { useState } from "react";
import { X, CheckCircle2, AlertCircle, Server, RefreshCw } from "lucide-react";
import { mcp as mcpApi } from "@/lib/api";

interface MCPServerSetupProps {
  onClose: () => void;
}

export default function MCPServerSetup({ onClose }: MCPServerSetupProps) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [transport] = useState("http");
  const [headers, setHeaders] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [createdServerId, setCreatedServerId] = useState<string | null>(null);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    setTestError(null);
    let serverId: string | null = null;
    try {
      let parsedHeaders: any = undefined;
      if (headers.trim()) {
        try {
          parsedHeaders = JSON.parse(headers);
        } catch {
          setTestError("Invalid JSON in headers field");
          setTestResult("error");
          setTesting(false);
          return;
        }
      }

      const server = await mcpApi.clients.create({
        name: name || "New MCP Server",
        url,
        transport,
        headers: parsedHeaders,
      });
      serverId = server.id;

      // Try discovery
      const discovery = await mcpApi.clients.discover(server.id);
      if (discovery?.count === 0) {
        throw new Error("Connected, but no MCP tools were discovered.");
      }
      setCreatedServerId(server.id);
      setTestResult("success");
    } catch (e: any) {
      if (serverId) {
        try {
          await mcpApi.clients.delete(serverId);
        } catch {
          // Best-effort cleanup. The connection error remains the useful signal.
        }
      }
      setTestError(e.message);
      setTestResult("error");
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    if (testResult === "success" && createdServerId) {
      // Already created during test
      setSaved(true);
      return;
    }

    setSaving(true);
    try {
      let parsedHeaders: any = undefined;
      if (headers.trim()) {
        parsedHeaders = JSON.parse(headers);
      }

      await mcpApi.clients.create({
        name: name || "New MCP Server",
        url,
        transport,
        headers: parsedHeaders,
      });
      setSaved(true);
    } catch (e: any) {
      setTestError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (saved) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center">
          <CheckCircle2 size={48} className="mx-auto mb-4 text-istara-500" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Server Added!</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
            &ldquo;{name || "New MCP Server"}&rdquo; has been connected. Tools have been discovered and are ready to use.
          </p>
          <button onClick={onClose} className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors">
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-lg overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Server size={18} className="text-istara-500" />
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">Add MCP Server</h2>
          </div>
          <button onClick={onClose} aria-label="Close" className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Server Name</label>
            <input
              type="text"
              placeholder="e.g., My MCP Server"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
            />
          </div>

          {/* URL */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Server URL</label>
            <input
              type="text"
              placeholder="http://localhost:3001/mcp"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
            />
          </div>

          {/* Transport */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Transport</label>
            <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2">
              <span className="text-xs font-medium text-slate-900 dark:text-white">HTTP</span>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Istara currently connects to external MCP servers through HTTP. Run stdio or WebSocket servers behind an HTTP MCP bridge before adding them here.
              </p>
            </div>
          </div>

          {/* Headers */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Custom Headers <span className="text-slate-400 font-normal">(optional, JSON)</span>
            </label>
            <textarea
              placeholder='{"Authorization": "Bearer ..."}'
              value={headers}
              onChange={(e) => setHeaders(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500 font-mono"
            />
          </div>

          {/* Test result */}
          {testResult === "success" && (
            <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <CheckCircle2 size={16} className="text-green-500" />
              <span className="text-sm text-green-700 dark:text-green-400">Connection successful! Tools discovered.</span>
            </div>
          )}
          {testResult === "error" && (
            <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <AlertCircle size={16} className="text-red-500" />
              <span className="text-sm text-red-700 dark:text-red-400">{testError || "Connection failed"}</span>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-slate-200 dark:border-slate-800">
          <button
            onClick={handleTest}
            disabled={!url.trim() || testing}
            className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={14} className={testing ? "animate-spin" : ""} />
            {testing ? "Testing..." : "Test Connection"}
          </button>
          <button
            onClick={handleSave}
            disabled={!url.trim() || saving}
            className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save Server"}
          </button>
        </div>
      </div>
    </div>
  );
}
