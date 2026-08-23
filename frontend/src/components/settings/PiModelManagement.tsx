"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  ExternalLink,
  KeyRound,
  LockKeyhole,
  Plus,
  Search,
  Server,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { piCatalogApi, piEndpoints, piOAuthApi } from "@/lib/api";
import type { PiCatalogModel, PiCatalogProvider, PiEndpoint, PiOAuthFlow } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";

function modelApiKind(model: PiCatalogModel): string {
  if (model.api === "openai-codex-responses") return "Codex Responses";
  if (model.api.includes("anthropic")) return "Claude Messages";
  if (model.api.includes("google")) return "Gemini";
  return "OpenAI-compatible";
}

function modelCapabilityLabel(model: PiCatalogModel): string {
  const parts: string[] = [];
  if (model.reasoning) parts.push("reasoning");
  if (model.contextWindow) parts.push(`${Math.round(model.contextWindow / 1000)}k context`);
  if (model.input?.includes("image")) parts.push("vision");
  return parts.join(" · ") || "standard chat";
}

function endpointAuthLabel(endpoint: PiEndpoint): string {
  if (endpoint.auth_method?.startsWith("oauth")) return "OAuth connected";
  return "API key / configured secret";
}

function normaliseEndpointId(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 100);
}

interface CatalogPickerProps<T> {
  id: string;
  label: string;
  hint: string;
  placeholder: string;
  query: string;
  selected: T | null;
  open: boolean;
  setOpen: (open: boolean) => void;
  setQuery: (query: string) => void;
  options: T[];
  total: number;
  getKey: (item: T) => string;
  getLabel: (item: T) => string;
  getDescription: (item: T) => string;
  onSelect: (item: T) => void;
  renderMeta?: (item: T) => React.ReactNode;
  emptyLabel: string;
  browseLabel: string;
}

function CatalogPicker<T>({
  id,
  label,
  hint,
  placeholder,
  query,
  selected,
  open,
  setOpen,
  setQuery,
  options,
  total,
  getKey,
  getLabel,
  getDescription,
  onSelect,
  renderMeta,
  emptyLabel,
  browseLabel,
}: CatalogPickerProps<T>) {
  const [activeIndex, setActiveIndex] = useState(0);
  const inputValue = selected ? getLabel(selected) : query;

  useEffect(() => {
    setActiveIndex(0);
  }, [query, open]);

  const chooseActive = () => {
    const item = options[activeIndex];
    if (item) onSelect(item);
  };

  return (
    <div className="min-w-0">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-sm font-semibold text-slate-900 dark:text-white">{label}</label>
        <span className="text-xs text-slate-500 dark:text-slate-400">{hint}</span>
      </div>
      <div className="relative">
        <div className="flex rounded-[10px] border border-slate-300 bg-white shadow-sm focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-blue-600 dark:border-slate-600 dark:bg-slate-900">
          <Search size={17} className="ml-3 mt-3.5 shrink-0 text-slate-400" aria-hidden="true" />
          <input
            id={id}
            role="combobox"
            aria-expanded={open}
            aria-controls={`${id}-listbox`}
            aria-autocomplete="list"
            aria-haspopup="listbox"
            value={inputValue}
            placeholder={placeholder}
            onFocus={() => setOpen(true)}
            onChange={(event) => {
              setQuery(event.target.value);
              if (selected) onSelect(null as T);
              setOpen(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setOpen(true);
                setActiveIndex((index) => Math.min(index + 1, Math.max(options.length - 1, 0)));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActiveIndex((index) => Math.max(index - 1, 0));
              } else if (event.key === "Enter") {
                event.preventDefault();
                chooseActive();
              } else if (event.key === "Escape") {
                setOpen(false);
              }
            }}
            className="min-h-[44px] min-w-0 flex-1 bg-transparent px-3 text-sm text-slate-900 outline-none placeholder:text-slate-400 dark:text-white"
          />
          {selected && (
            <button
              type="button"
              className="ui-icon-button mr-1 my-0.5"
              onClick={() => { onSelect(null as T); setQuery(""); setOpen(true); }}
              aria-label={`Clear ${label.toLowerCase()}`}
            >
              <X size={16} />
            </button>
          )}
          <button
            type="button"
            className="ui-icon-button my-0.5 mr-0.5"
            onClick={() => setOpen(!open)}
            aria-label={`${open ? "Close" : "Browse"} ${label.toLowerCase()}`}
            aria-controls={`${id}-listbox`}
            aria-expanded={open}
          >
            <ChevronDown size={18} className={open ? "rotate-180 transition-transform" : "transition-transform"} />
          </button>
        </div>
        {open && (
          <div id={`${id}-listbox`} role="listbox" aria-label={`${label} options`} className="ui-menu absolute inset-x-0 top-[calc(100%+8px)] z-[100] overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
              <span>{query ? `${options.length} matches` : browseLabel}</span>
              <span>↑↓ navigate · Enter select</span>
            </div>
            <div className="max-h-72 overflow-y-auto p-2">
              {options.length === 0 ? (
                <div className="px-3 py-6 text-center text-sm text-slate-500">
                  <p>{emptyLabel}</p>
                  <p className="mt-1 text-xs">Try a shorter search or open the full list.</p>
                </div>
              ) : options.map((item, index) => {
                const key = getKey(item);
                const isSelected = selected ? getKey(selected) === key : false;
                return (
                  <button
                    key={key}
                    type="button"
                    role="option"
                    aria-selected={isSelected}
                    data-active={index === activeIndex}
                    className="ui-option px-3 py-2.5"
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => onSelect(item)}
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span className="flex min-w-0 items-center gap-2">
                        <span className="truncate text-sm font-semibold">{getLabel(item)}</span>
                        {isSelected && <Check size={15} className="shrink-0 text-istara-600" aria-hidden="true" />}
                      </span>
                      <span className="truncate text-xs text-slate-500 dark:text-slate-400">{getDescription(item)}</span>
                    </span>
                    {renderMeta?.(item)}
                  </button>
                );
              })}
            </div>
            {!query && total > options.length && (
              <div className="border-t border-slate-200 px-3 py-2 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
                Showing {options.length} of {total}. Type to search the full catalog.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function PiModelManagement() {
  const { user, teamMode } = useAuthStore();
  const [endpoints, setEndpoints] = useState<PiEndpoint[]>([]);
  const [retirementNote, setRetirementNote] = useState("");
  const [providers, setProviders] = useState<PiCatalogProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [providerQuery, setProviderQuery] = useState("");
  const [modelQuery, setModelQuery] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<PiCatalogProvider | null>(null);
  const [selectedModel, setSelectedModel] = useState<PiCatalogModel | null>(null);
  const [providerOpen, setProviderOpen] = useState(false);
  const [modelOpen, setModelOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"api_key" | "oauth">("api_key");
  const [oauthMethod, setOauthMethod] = useState<"browser" | "device_code">("browser");
  const [apiKey, setApiKey] = useState("");
  const [activeOAuth, setActiveOAuth] = useState<PiOAuthFlow | null>(null);
  const [credentialReady, setCredentialReady] = useState(false);
  const [oauthError, setOauthError] = useState<string | null>(null);
  const [addError, setAddError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const canManage = !teamMode || user?.role === "admin";

  const fetchAll = useCallback(async () => {
    if (!canManage) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [catalog, configured] = await Promise.all([piCatalogApi.get(), piEndpoints.list()]);
      setProviders(catalog.providers || []);
      setEndpoints(configured.endpoints || []);
      setRetirementNote(configured.retirement_note || "");
    } catch {
      setProviders([]);
      setEndpoints([]);
    } finally {
      setLoading(false);
    }
  }, [canManage]);

  useEffect(() => { void fetchAll(); }, [fetchAll]);

  useEffect(() => {
    if (!activeOAuth) return;
    const poll = async () => {
      try {
        const response = await piOAuthApi.poll(activeOAuth.provider);
        const latest = (response.flows || []).find((flow: PiOAuthFlow) => flow.provider === activeOAuth.provider);
        if (!latest) return;
        setActiveOAuth(latest);
        if (latest.status === "approved") {
          setCredentialReady(true);
          setActiveOAuth(null);
        } else if (latest.status === "failed" || latest.status === "expired") {
          setOauthError(latest.error || "The login did not complete.");
          setActiveOAuth(null);
        }
      } catch (error) {
        setOauthError(error instanceof Error ? error.message : "Could not check login status.");
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 4000);
    return () => window.clearInterval(timer);
  }, [activeOAuth]);

  const providerMatches = useMemo(() => {
    const query = providerQuery.trim().toLowerCase();
    const matches = query
      ? providers.filter((provider) => `${provider.display_name} ${provider.id}`.toLowerCase().includes(query))
      : providers;
    return matches.slice(0, 80);
  }, [providers, providerQuery]);

  const modelMatches = useMemo(() => {
    const models = selectedProvider?.models || [];
    const query = modelQuery.trim().toLowerCase();
    const matches = query
      ? models.filter((model) => `${model.name} ${model.id}`.toLowerCase().includes(query))
      : models;
    return matches.slice(0, 80);
  }, [selectedProvider, modelQuery]);

  const selectProvider = (provider: PiCatalogProvider | null) => {
    setSelectedProvider(provider);
    setSelectedModel(null);
    setProviderOpen(false);
    setModelOpen(false);
    setModelQuery("");
    setCredentialReady(false);
    setActiveOAuth(null);
    setOauthError(null);
    if (provider?.login_methods.includes("api_key")) setAuthMode("api_key");
    else setAuthMode("oauth");
    const methods = provider?.oauth_methods || [];
    setOauthMethod(methods.includes("browser") ? "browser" : "device_code");
  };

  const selectModel = (model: PiCatalogModel | null) => {
    setSelectedModel(model);
    setModelOpen(false);
    setCredentialReady(false);
    setActiveOAuth(null);
    setOauthError(null);
    if (selectedProvider && authMode === "oauth" && selectedProvider.oauth_model_ids?.length && !selectedProvider.oauth_model_ids.includes(model?.id || "")) {
      setAuthMode("api_key");
    }
  };

  const oauthSupportedForModel = Boolean(
    selectedProvider?.login_methods.includes("oauth") &&
    selectedModel &&
    (!selectedProvider.oauth_model_ids?.length || selectedProvider.oauth_model_ids.includes(selectedModel.id))
  );

  const startOAuth = async () => {
    if (!selectedProvider || !selectedModel || !oauthSupportedForModel) return;
    setOauthError(null);
    setCredentialReady(false);
    try {
      const provider = selectedProvider.oauth_provider || selectedProvider.id;
      const flow = await piOAuthApi.start(provider, oauthMethod);
      setActiveOAuth({ ...flow, provider: flow.provider || provider, method: oauthMethod });
    } catch (error) {
      setOauthError(error instanceof Error ? error.message : "Could not start the Pi login.");
    }
  };

  const addModel = async () => {
    if (!selectedProvider || !selectedModel) {
      setAddError("Choose a provider and model first.");
      return;
    }
    if (authMode === "oauth" && !credentialReady) {
      setAddError("Complete the Pi login before adding this model.");
      return;
    }
    setAdding(true);
    setAddError(null);
    try {
      const oauthProvider = selectedProvider.oauth_provider || selectedProvider.id;
      const catalogProviderId = authMode === "oauth" && selectedProvider.oauth_model_ids?.includes(selectedModel.id)
        ? oauthProvider
        : selectedProvider.id;
      const selectedAuthMethod = authMode === "oauth" ? `oauth_${oauthMethod}` : "api_key";
      const endpointId = normaliseEndpointId(`${catalogProviderId}-${selectedModel.id}-${selectedAuthMethod}`);
      await piEndpoints.add({
        endpoint_id: endpointId,
        provider_kind: "openai_compat",
        base_url: "",
        model: "",
        pi_provider: catalogProviderId,
        pi_model: selectedModel.id,
        keychain_service: authMode === "oauth" ? `istara-pi-oauth-${oauthProvider}` : `istara-pi-${selectedProvider.id}`,
        auth_provider: oauthProvider,
        auth_method: selectedAuthMethod,
        api_key: authMode === "api_key" ? apiKey.trim() : "",
      });
      setShowAdd(false);
      setSelectedProvider(null);
      setSelectedModel(null);
      setProviderQuery("");
      setModelQuery("");
      setApiKey("");
      setCredentialReady(false);
      await fetchAll();
    } catch (error) {
      setAddError(error instanceof Error ? error.message : "Could not add this model.");
    } finally {
      setAdding(false);
    }
  };

  const deleteModel = async (endpointId: string) => {
    setDeleting(endpointId);
    try {
      await piEndpoints.delete(endpointId);
      await fetchAll();
    } catch (error) {
      window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type: "error", title: "Could not remove model", message: error instanceof Error ? error.message : "Try again." } }));
    } finally {
      setDeleting(null);
    }
  };

  if (!canManage) {
    return (
      <section className="ui-panel p-5" aria-labelledby="pi-model-management-title">
        <div className="flex items-start gap-3">
          <LockKeyhole className="mt-1 text-slate-400" size={20} aria-hidden="true" />
          <div>
            <h2 id="pi-model-management-title" className="text-lg font-semibold text-slate-900 dark:text-white">Pi Model Management</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">A global administrator manages provider credentials and model connections. Project members can use the models enabled here.</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="ui-panel overflow-visible" aria-labelledby="pi-model-management-title">
      <div className="border-b border-slate-200 px-5 py-5 dark:border-slate-700 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-istara-100 text-istara-700 dark:bg-istara-950/60 dark:text-istara-300">
              <Server size={20} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-istara-700 dark:text-istara-300">Pi model management</p>
              <h2 id="pi-model-management-title" className="mt-1 text-xl font-semibold tracking-tight text-slate-950 dark:text-white">Providers, models, and sign-in</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                Browse the complete Pi catalog or search it. Pick a provider, choose a model, then use the authentication method Pi supports for that model — no endpoint URLs to copy.
              </p>
            </div>
          </div>
          <button type="button" className="primary-action min-h-[44px] shrink-0" onClick={() => { setShowAdd((open) => !open); setAddError(null); }}>
            {showAdd ? <X size={17} /> : <Plus size={17} />}
            {showAdd ? "Close" : "Add a model"}
          </button>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-500 dark:text-slate-400">
          <span className="inline-flex items-center gap-1.5"><ShieldCheck size={15} className="text-istara-600" /> {providers.length} providers · {providers.reduce((sum, provider) => sum + provider.models.length, 0)} models</span>
          <span className="inline-flex items-center gap-1.5"><KeyRound size={15} className="text-istara-600" /> Credentials stay in server custody</span>
          {retirementNote && <span>{retirementNote}</span>}
        </div>
      </div>

      {showAdd && (
        <div className="border-b border-slate-200 px-5 py-5 dark:border-slate-700 sm:px-6">
          <div className="mb-5 flex items-start gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-istara-600 text-sm font-semibold text-white">1</span>
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-white">Choose from the Pi catalog</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Click the arrow to browse. Type at any time to autocomplete and narrow the list.</p>
            </div>
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <CatalogPicker
              id="pi-provider-picker"
              label="Provider"
              hint={`${providers.length} available`}
              placeholder="Browse or search providers"
              query={providerQuery}
              selected={selectedProvider}
              open={providerOpen}
              setOpen={setProviderOpen}
              setQuery={setProviderQuery}
              options={providerMatches}
              total={providers.length}
              getKey={(provider) => provider.id}
              getLabel={(provider) => provider.display_name}
              getDescription={(provider) => provider.id}
              onSelect={selectProvider}
              renderMeta={(provider) => <span className="shrink-0 text-xs text-slate-400">{provider.models.length}</span>}
              emptyLabel="No providers match that search."
              browseLabel="Browse every Pi provider"
            />
            <CatalogPicker
              id="pi-model-picker"
              label="Model"
              hint={selectedProvider ? `${selectedProvider.models.length} available` : "Choose a provider first"}
              placeholder={selectedProvider ? "Browse or search models" : "Choose a provider first"}
              query={modelQuery}
              selected={selectedModel}
              open={modelOpen && Boolean(selectedProvider)}
              setOpen={setModelOpen}
              setQuery={setModelQuery}
              options={modelMatches}
              total={selectedProvider?.models.length || 0}
              getKey={(model) => model.id}
              getLabel={(model) => model.name || model.id}
              getDescription={(model) => model.id}
              onSelect={selectModel}
              renderMeta={(model) => <span className="shrink-0 text-right text-[11px] text-slate-500">{modelCapabilityLabel(model)}</span>}
              emptyLabel={selectedProvider ? "No models match that search." : "Select a provider to see its models."}
              browseLabel={selectedProvider ? `Browse ${selectedProvider.models.length} models` : "Choose a provider first"}
            />
          </div>

          {selectedProvider && selectedModel && (
            <div className="mt-5 rounded-xl border border-istara-200 bg-istara-50/60 p-4 dark:border-istara-900 dark:bg-istara-950/30">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.1em] text-istara-700 dark:text-istara-300">Selected model</p>
                  <h3 className="mt-1 truncate text-base font-semibold text-slate-950 dark:text-white">{selectedModel.name || selectedModel.id}</h3>
                  <p className="mt-1 break-all font-mono text-xs text-slate-600 dark:text-slate-300">{selectedProvider.id} / {selectedModel.id}</p>
                </div>
                <div className="flex flex-wrap justify-end gap-2 text-xs text-slate-600 dark:text-slate-300">
                  <span className="rounded-full bg-white px-2.5 py-1 dark:bg-slate-900">{modelApiKind(selectedModel)}</span>
                  {selectedModel.reasoning && <span className="rounded-full bg-white px-2.5 py-1 dark:bg-slate-900">Reasoning supported</span>}
                  {selectedModel.thinkingLevels?.length ? <span className="rounded-full bg-white px-2.5 py-1 dark:bg-slate-900">{selectedModel.thinkingLevels.length} effort levels</span> : null}
                </div>
              </div>
            </div>
          )}

          {selectedProvider && selectedModel && (
            <div className="mt-5 border-t border-slate-200 pt-5 dark:border-slate-700">
              <div className="mb-3 flex items-start gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-istara-600 text-sm font-semibold text-white">2</span>
                <div>
                  <h3 className="font-semibold text-slate-900 dark:text-white">Choose how to sign in</h3>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">The available choices come from Pi&apos;s provider definition for this model.</p>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {selectedProvider.login_methods.includes("api_key") && (
                  <button type="button" className={`rounded-xl border p-4 text-left ${authMode === "api_key" ? "border-istara-500 bg-istara-50 dark:border-istara-400 dark:bg-istara-950/40" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900/40"}`} onClick={() => { setAuthMode("api_key"); setCredentialReady(false); }}>
                    <span className="flex items-center gap-2 text-sm font-semibold text-slate-950 dark:text-white"><KeyRound size={17} /> API key</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500 dark:text-slate-400">Use the provider key already configured on the server, or add one to encrypted custody below.</span>
                  </button>
                )}
                {oauthSupportedForModel && (
                  <button type="button" className={`rounded-xl border p-4 text-left ${authMode === "oauth" ? "border-istara-500 bg-istara-50 dark:border-istara-400 dark:bg-istara-950/40" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900/40"}`} onClick={() => { setAuthMode("oauth"); setApiKey(""); }}>
                    <span className="flex items-center gap-2 text-sm font-semibold text-slate-950 dark:text-white"><ShieldCheck size={17} /> Sign in with Pi OAuth</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500 dark:text-slate-400">No API key is copied into the browser. The server completes Pi&apos;s OAuth flow and stores the credential.</span>
                  </button>
                )}
              </div>
              {selectedProvider.auth_description && <p className="mt-3 text-xs leading-5 text-slate-500 dark:text-slate-400">{selectedProvider.auth_description}</p>}
              {selectedProvider.id === "openai" && !oauthSupportedForModel && selectedProvider.oauth_model_ids?.length ? (
                <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                  ChatGPT subscription OAuth is available for the OpenAI Codex models in Pi&apos;s catalog. This selected OpenAI API model is API-key only; choose <strong>OpenAI Codex — ChatGPT subscription</strong> if you want browser or headless OAuth.
                </p>
              ) : null}

              {authMode === "api_key" && selectedProvider.login_methods.includes("api_key") && (
                <div className="mt-4 max-w-xl">
                  <label htmlFor="pi-api-key" className="mb-2 block text-sm font-medium text-slate-900 dark:text-white">API key <span className="font-normal text-slate-500">(optional if already configured)</span></label>
                  <input id="pi-api-key" type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={selectedProvider.env_var || "Paste a provider key"} className="ui-control w-full px-3 text-sm" autoComplete="off" />
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Stored by the server in Keychain or encrypted local custody. It is never returned to the UI.</p>
                </div>
              )}

              {authMode === "oauth" && oauthSupportedForModel && (
                <div className="mt-4 max-w-2xl">
                  <p className="mb-2 text-sm font-medium text-slate-900 dark:text-white">Pi login method</p>
                  <div className="flex flex-wrap gap-2">
                    {(selectedProvider.oauth_methods || []).map((method) => (
                      <button key={method} type="button" className={`ui-control px-3 text-sm font-medium ${oauthMethod === method ? "border-istara-500 bg-istara-50 text-istara-700 dark:border-istara-400 dark:bg-istara-950/40 dark:text-istara-200" : "text-slate-700 dark:text-slate-200"}`} onClick={() => { setOauthMethod(method as "browser" | "device_code"); setCredentialReady(false); }}>
                        {method === "browser" ? "Browser login" : "Device code (headless)"}
                      </button>
                    ))}
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">
                    {oauthMethod === "browser" ? "A secure provider page opens in another tab. After approval, return here; the connection status updates automatically." : "Ideal for a server without a graphical browser. Open the provider URL and enter the one-time code shown below."}
                  </p>
                  {!credentialReady && !activeOAuth && (
                    <button type="button" className="secondary-action mt-3" onClick={() => void startOAuth()}>
                      <ShieldCheck size={16} /> Start {oauthMethod === "browser" ? "browser" : "headless"} login
                    </button>
                  )}
                  {activeOAuth && (
                    <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/30" role="status" aria-live="polite">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-blue-950 dark:text-blue-100">Waiting for Pi authentication</p>
                          {activeOAuth.auth_url && (
                            <a href={activeOAuth.auth_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-blue-700 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700">
                              Continue in browser <ExternalLink size={15} />
                            </a>
                          )}
                          {activeOAuth.verification_uri && (
                            <p className="mt-3 break-all text-xs text-blue-900 dark:text-blue-200">Open: <span className="font-mono">{activeOAuth.verification_uri}</span></p>
                          )}
                          {activeOAuth.user_code && <p className="mt-2 text-sm text-blue-900 dark:text-blue-200">Code: <strong className="font-mono text-lg tracking-wider">{activeOAuth.user_code}</strong></p>}
                          <p className="mt-2 text-xs text-blue-800 dark:text-blue-300">Checking approval automatically. Tokens remain on the server.</p>
                        </div>
                        <button type="button" className="ui-icon-button shrink-0 text-blue-800 dark:text-blue-200" onClick={() => { void piOAuthApi.cancel(activeOAuth.provider); setActiveOAuth(null); }} aria-label="Cancel Pi login"><X size={17} /></button>
                      </div>
                    </div>
                  )}
                  {credentialReady && <p className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-green-700 dark:text-green-300"><Check size={17} /> Credential connected. Add the model below.</p>}
                </div>
              )}
            </div>
          )}

          {selectedProvider && selectedModel && (
            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-5 dark:border-slate-700">
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-white">3. Add this model to Istara</p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Pi resolves the endpoint URL, protocol, capabilities, effort levels, and pricing from the catalog.</p>
              </div>
              <button type="button" className="primary-action" disabled={adding || (authMode === "oauth" && !credentialReady)} onClick={() => void addModel()}>
                <Plus size={17} /> {adding ? "Adding…" : "Add model"}
              </button>
            </div>
          )}
          {addError && <p role="alert" className="mt-3 text-sm font-medium text-red-700 dark:text-red-300">{addError}</p>}
          {oauthError && <p role="alert" className="mt-3 text-sm font-medium text-red-700 dark:text-red-300">{oauthError}</p>}
        </div>
      )}

      <div className="px-5 py-5 sm:px-6">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Connected models</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Only connections enabled here appear as usable choices in Chat.</p>
          </div>
          {loading && <span className="text-xs text-slate-500">Loading catalog…</span>}
        </div>
        {endpoints.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-center dark:border-slate-700">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">No additional models connected yet.</p>
            <p className="mt-1 text-xs text-slate-500">The built-in Pi endpoint remains available; add a provider above to make another model selectable in Chat.</p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 dark:divide-slate-700 dark:border-slate-700">
            {endpoints.map((endpoint) => (
              <li key={endpoint.endpoint_id} className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-950 dark:text-white">{endpoint.pi_model || endpoint.model}</p>
                  <p className="mt-1 truncate font-mono text-xs text-slate-500 dark:text-slate-400">{endpoint.pi_provider || endpoint.provider_kind} · {endpoint.endpoint_id}</p>
                  <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                    <span>{endpoint.context_window ? `${Math.round(endpoint.context_window / 1000)}k context` : "Context unknown"}</span>
                    <span>{endpointAuthLabel(endpoint)}</span>
                    {endpoint.auth_method?.includes("device") && <span>Headless OAuth</span>}
                    {endpoint.auth_method === "oauth_browser" && <span>Browser OAuth</span>}
                  </div>
                </div>
                <button type="button" className="ui-icon-button shrink-0 self-end text-slate-500 hover:text-red-700 sm:self-center" disabled={deleting === endpoint.endpoint_id} onClick={() => void deleteModel(endpoint.endpoint_id)} aria-label={`Remove ${endpoint.pi_model || endpoint.model}`}>
                  <Trash2 size={17} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
