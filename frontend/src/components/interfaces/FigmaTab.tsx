"use client";

import { useState } from "react";
import { ExternalLink, Save, Loader2, CheckCircle2, XCircle, Download, Layers } from "lucide-react";
import { interfaces as interfacesApi } from "@/lib/api";
import { useInterfacesStore } from "@/stores/interfacesStore";
import { useProjectStore } from "@/stores/projectStore";
import PrivacyWarningBanner from "./PrivacyWarningBanner";

export default function FigmaTab() {
  const { status, privacyAcknowledged, acknowledgePrivacy } = useInterfacesStore();
  const { activeProjectId } = useProjectStore();

  // Configuration
  const [apiToken, setApiToken] = useState("");
  const [savingToken, setSavingToken] = useState(false);
  const [tokenSaved, setTokenSaved] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);

  // Import
  const [figmaUrl, setFigmaUrl] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Design System
  const [fileKey, setFileKey] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [designSystem, setDesignSystem] = useState<any>(null);
  const [dsError, setDsError] = useState<string | null>(null);

  // Stitch/Google API
  const [stitchKey, setStitchKey] = useState("");
  const [savingStitch, setSavingStitch] = useState(false);
  const [stitchSaved, setStitchSaved] = useState(false);
  const [stitchError, setStitchError] = useState<string | null>(null);

  const figmaConfigured = status?.figma_configured;
  const stitchConfigured = status?.stitch_configured;

  const handleSaveStitch = async () => {
    if (!stitchKey.trim()) return;
    setSavingStitch(true);
    setStitchError(null);
    setStitchSaved(false);
    try {
      await interfacesApi.configure.stitch({ api_key: stitchKey.trim() });
      setStitchSaved(true);
      setStitchKey("");
      useInterfacesStore.getState().fetchStatus();
    } catch (e: any) {
      setStitchError(e.message);
    } finally {
      setSavingStitch(false);
    }
  };

  const handleSaveToken = async () => {
    if (!apiToken.trim()) return;
    setSavingToken(true);
    setTokenError(null);
    setTokenSaved(false);
    try {
      await interfacesApi.configure.figma({ api_token: apiToken.trim() });
      setTokenSaved(true);
      setApiToken("");
      useInterfacesStore.getState().fetchStatus();
    } catch (e: any) {
      setTokenError(e.message);
    } finally {
      setSavingToken(false);
    }
  };

  const handleImport = async () => {
    if (!figmaUrl.trim() || !activeProjectId || importing) return;
    setImporting(true);
    setImportError(null);
    setImportResult(null);
    try {
      const result = await interfacesApi.figma.import({ project_id: activeProjectId, figma_url: figmaUrl.trim() });
      setImportResult(result);
    } catch (e: any) {
      setImportError(e.message);
    } finally {
      setImporting(false);
    }
  };

  const handleExtractDS = async () => {
    if (!fileKey.trim() || extracting) return;
    setExtracting(true);
    setDsError(null);
    setDesignSystem(null);
    try {
      const result = await interfacesApi.figma.designSystem(fileKey.trim());
      setDesignSystem(result);
    } catch (e: any) {
      setDsError(e.message);
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Privacy warning */}
        {!privacyAcknowledged && (
          <PrivacyWarningBanner service="Figma" onAcknowledge={acknowledgePrivacy} />
        )}

        {/* Configuration Section */}
        <section>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">Figma Configuration</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Connect your Figma account to import designs and extract design systems.
          </p>

          <div className="flex items-center gap-2 mb-3">
            {figmaConfigured ? (
              <span className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
                <CheckCircle2 size={14} /> Connected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-sm text-slate-400">
                <XCircle size={14} /> Not configured
              </span>
            )}
          </div>

          <div className="flex gap-2">
            <input
              type="password"
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              placeholder="Figma API token"
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            />
            <button
              onClick={handleSaveToken}
              disabled={!apiToken.trim() || savingToken}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {savingToken ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save
            </button>
          </div>

          {tokenSaved && (
            <p className="text-sm text-green-600 dark:text-green-400 mt-2">Token saved successfully.</p>
          )}
          {tokenError && (
            <p className="text-sm text-red-600 dark:text-red-400 mt-2">{tokenError}</p>
          )}

          <a
            href="https://www.figma.com/developers/api#access-tokens"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400 mt-2"
          >
            <ExternalLink size={12} /> Get your Figma API token
          </a>
        </section>

        {/* Google Stitch Configuration */}
        <section>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">Google Stitch (Generative AI)</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Connect Google Generative AI to enable AI-powered screen generation via the Stitch MCP protocol.
          </p>

          <div className="flex items-center gap-2 mb-3">
            {stitchConfigured ? (
              <span className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
                <CheckCircle2 size={14} /> Connected
              </span>
            ) : (
              <span className="flex items-center gap-1 text-sm text-slate-400">
                <XCircle size={14} /> Not configured
              </span>
            )}
          </div>

          <div className="flex gap-2">
            <input
              type="password"
              value={stitchKey}
              onChange={(e) => setStitchKey(e.target.value)}
              placeholder="Google API key"
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
            />
            <button
              onClick={handleSaveStitch}
              disabled={!stitchKey.trim() || savingStitch}
              className="flex items-center gap-1.5 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {savingStitch ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save
            </button>
          </div>

          {stitchSaved && (
            <p className="text-sm text-green-600 dark:text-green-400 mt-2">Google API key saved successfully.</p>
          )}
          {stitchError && (
            <p className="text-sm text-red-600 dark:text-red-400 mt-2">{stitchError}</p>
          )}

          <a
            href="https://aistudio.google.com/app/apikey"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-reclaw-600 hover:text-reclaw-700 dark:text-reclaw-400 mt-2"
          >
            <ExternalLink size={12} /> Get your Google AI API key
          </a>
        </section>

        {/* Import Section */}
        <section>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">Import from Figma</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Paste a Figma file or frame URL to import designs into your project.
          </p>

          {!figmaConfigured ? (
            <p className="text-sm text-slate-400 bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4">
              Configure your Figma API token above to enable imports.
            </p>
          ) : (
            <>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={figmaUrl}
                  onChange={(e) => setFigmaUrl(e.target.value)}
                  placeholder="https://www.figma.com/file/..."
                  className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />
                <button
                  onClick={handleImport}
                  disabled={!figmaUrl.trim() || importing}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {importing ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                  Import
                </button>
              </div>

              {importResult && (
                <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-sm text-green-700 dark:text-green-400">
                  Import successful. {importResult.screens_imported || 0} screen(s) imported.
                </div>
              )}
              {importError && (
                <p className="text-sm text-red-600 dark:text-red-400 mt-2">{importError}</p>
              )}
            </>
          )}
        </section>

        {/* Design System Section */}
        <section>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">Design System</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
            Extract design tokens, colors, and components from a Figma file.
          </p>

          {!figmaConfigured ? (
            <p className="text-sm text-slate-400 bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4">
              Configure your Figma API token above to extract design systems.
            </p>
          ) : (
            <>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={fileKey}
                  onChange={(e) => setFileKey(e.target.value)}
                  placeholder="Figma file key (from URL)"
                  className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
                />
                <button
                  onClick={handleExtractDS}
                  disabled={!fileKey.trim() || extracting}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm bg-reclaw-600 text-white rounded-lg hover:bg-reclaw-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {extracting ? <Loader2 size={14} className="animate-spin" /> : <Layers size={14} />}
                  Extract
                </button>
              </div>

              {designSystem && (
                <div className="mt-3 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                  <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Extracted Design System</h4>
                  <pre className="text-xs text-slate-600 dark:text-slate-400 overflow-auto max-h-60">
                    {JSON.stringify(designSystem, null, 2)}
                  </pre>
                </div>
              )}
              {dsError && (
                <p className="text-sm text-red-600 dark:text-red-400 mt-2">{dsError}</p>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
