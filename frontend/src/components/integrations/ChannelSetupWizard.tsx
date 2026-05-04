"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, CheckCircle2, AlertCircle, X, Send, Hash, MessageCircle, MessageSquare } from "lucide-react";
import { channels as channelsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const STEPS = ["platform", "credentials", "name", "test", "done"] as const;
type Step = (typeof STEPS)[number];

const PLATFORMS = [
  { id: "telegram", label: "Telegram", color: "#0088cc", icon: Send, description: "Connect via Telegram Bot API" },
  { id: "slack", label: "Slack", color: "#4A154B", icon: Hash, description: "Connect via Slack App with OAuth" },
  { id: "whatsapp", label: "WhatsApp", color: "#25D366", icon: MessageCircle, description: "Connect via WhatsApp Business API" },
  { id: "google_chat", label: "Google Chat", color: "#00AC47", icon: MessageSquare, description: "Connect via Google Workspace" },
] as const;

type CredentialField = {
  key: string;
  label: string;
  placeholder: string;
  type: "text" | "password";
  required?: boolean;
};

const CREDENTIAL_FIELDS: Record<string, CredentialField[]> = {
  telegram: [{ key: "bot_token", label: "Bot Token", placeholder: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", type: "password", required: true }],
  slack: [
    { key: "bot_token", label: "Bot Token", placeholder: "xoxb-...", type: "password", required: true },
    { key: "signing_secret", label: "Signing Secret", placeholder: "Slack signing secret", type: "password", required: true },
    { key: "app_token", label: "App Token", placeholder: "xapp-... (optional Socket Mode)", type: "password" },
  ],
  whatsapp: [
    { key: "phone_number_id", label: "Phone Number ID", placeholder: "Your phone number ID", type: "text", required: true },
    { key: "access_token", label: "Access Token", placeholder: "WhatsApp Business API token", type: "password", required: true },
    { key: "verify_token", label: "Verify Token", placeholder: "Webhook verification token", type: "password", required: true },
    { key: "app_secret", label: "App Secret", placeholder: "Meta app secret for webhook signatures", type: "password", required: true },
  ],
  google_chat: [
    { key: "webhook_url", label: "Webhook URL", placeholder: "https://chat.googleapis.com/v1/spaces/...", type: "text", required: true },
    { key: "webhook_token", label: "Webhook Token", placeholder: "Shared secret for inbound events", type: "password", required: true },
    { key: "service_account_json", label: "Service Account JSON", placeholder: "Optional service account credentials JSON", type: "password" },
  ],
};

interface ChannelSetupWizardProps {
  onClose: () => void;
}

export default function ChannelSetupWizard({ onClose }: ChannelSetupWizardProps) {
  const [currentStep, setCurrentStep] = useState<Step>("platform");
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [channelName, setChannelName] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [createdInstanceId, setCreatedInstanceId] = useState<string | null>(null);

  const stepIndex = STEPS.indexOf(currentStep);

  const goBack = () => {
    if (stepIndex > 0) setCurrentStep(STEPS[stepIndex - 1]);
  };
  const goNext = () => {
    if (stepIndex < STEPS.length - 1) setCurrentStep(STEPS[stepIndex + 1]);
  };

  const handleTest = async () => {
    if (!selectedPlatform) return;
    setTesting(true);
    setTestResult(null);
    setTestError(null);
    let instanceId: string | null = null;
    try {
      const instance = await channelsApi.create({
        platform: selectedPlatform,
        name: channelName || `${selectedPlatform}-channel`,
        config: credentials,
      });
      instanceId = instance.id;
      const start = await channelsApi.start(instance.id);
      if (!["started", "already_running"].includes(start?.status)) {
        throw new Error(start?.detail || "Channel could not be started with the supplied credentials.");
      }
      const health = await channelsApi.health(instance.id);
      if (health?.status !== "healthy") {
        throw new Error(health?.error || health?.detail || `Health check returned ${health?.status || "unknown"}.`);
      }
      setCreatedInstanceId(instance.id);
      setTestResult("success");
      goNext();
    } catch (e: any) {
      if (instanceId) {
        try {
          await channelsApi.stop(instanceId);
          await channelsApi.delete(instanceId);
        } catch {
          // Best-effort cleanup: the visible error below is the connection failure.
        }
      }
      setTestError(e.message);
      setTestResult("error");
    } finally {
      setTesting(false);
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case "platform": return !!selectedPlatform;
      case "credentials": {
        if (!selectedPlatform) return false;
        const fields = CREDENTIAL_FIELDS[selectedPlatform] || [];
        return fields
          .filter((field) => field.required)
          .every((field) => (credentials[field.key] || "").trim().length > 0);
      }
      case "name": return channelName.trim().length > 0;
      case "test": return testResult === "success" && !!createdInstanceId;
      default: return true;
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center p-6 overflow-y-auto">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-lg overflow-hidden">
        {/* Progress bar */}
        <div className="h-1 bg-slate-100 dark:bg-slate-800">
          <div
            className="h-full bg-istara-500 transition-all duration-300"
            style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        {/* Close button */}
        <div className="flex justify-end px-4 pt-3">
          <button onClick={onClose} aria-label="Close wizard" className="p-1 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 pt-2">
          {/* Step: Platform selection */}
          {currentStep === "platform" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Select Platform</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">Choose a messaging platform to connect.</p>
              <div className="grid grid-cols-2 gap-3">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPlatform(p.id)}
                    className={cn(
                      "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all text-center",
                      selectedPlatform === p.id
                        ? "border-istara-500 bg-istara-50 dark:bg-istara-900/20"
                        : "border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600"
                    )}
                  >
                    <p.icon size={24} style={{ color: p.color }} />
                    <span className="text-sm font-medium text-slate-900 dark:text-white">{p.label}</span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">{p.description}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step: Credentials */}
          {currentStep === "credentials" && selectedPlatform && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Enter Credentials</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Provide your {PLATFORMS.find((p) => p.id === selectedPlatform)?.label} API credentials.
              </p>
              <div className="space-y-3">
                {(CREDENTIAL_FIELDS[selectedPlatform] || []).map((field, i) => (
                  <div key={i}>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                      {field.label}
                    </label>
                    <input
                      type={field.type}
                      placeholder={field.placeholder}
                      value={credentials[field.key] || ""}
                      onChange={(e) => setCredentials({ ...credentials, [field.key]: e.target.value })}
                      className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step: Name */}
          {currentStep === "name" && (
            <div>
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-1">Name Your Channel</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Give this channel instance a recognizable name.
              </p>
              <input
                type="text"
                placeholder="e.g., Research Telegram Bot"
                value={channelName}
                onChange={(e) => setChannelName(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
                autoFocus
              />
            </div>
          )}

          {/* Step: Test */}
          {currentStep === "test" && (
            <div className="text-center py-4">
              <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Test Connection</h2>
              {testResult === "success" ? (
                <div className="space-y-3">
                  <CheckCircle2 size={48} className="mx-auto text-green-500" />
                  <p className="text-sm text-green-600 dark:text-green-400 font-medium">Connection successful!</p>
                </div>
              ) : testResult === "error" ? (
                <div className="space-y-3">
                  <AlertCircle size={48} className="mx-auto text-red-500" />
                  <p className="text-sm text-red-600 dark:text-red-400">{testError || "Connection failed"}</p>
                  <button
                    onClick={handleTest}
                    disabled={testing}
                    className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 transition-colors"
                  >
                    {testing ? "Testing..." : "Retry"}
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <button
                    onClick={handleTest}
                    disabled={testing}
                    className="px-6 py-2.5 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 transition-colors"
                  >
                    {testing ? "Testing Connection..." : "Test Connection"}
                  </button>
                  <p className="text-xs text-slate-400 dark:text-slate-500">
                    This will create the channel and verify the connection.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step: Done */}
          {currentStep === "done" && (
            <div className="text-center py-4">
              <CheckCircle2 size={48} className="mx-auto mb-4 text-istara-500" />
              <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Channel Connected!</h2>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Your {PLATFORMS.find((p) => p.id === selectedPlatform)?.label} channel &ldquo;{channelName}&rdquo; is ready.
                You can now use it for research deployments.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-800">
          <div>
            {stepIndex > 0 && currentStep !== "done" && (
              <button onClick={goBack} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors">
                <ChevronLeft size={14} /> Back
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={cn(
                  "w-2 h-2 rounded-full transition-colors",
                  i === stepIndex ? "bg-istara-500" : i < stepIndex ? "bg-istara-300" : "bg-slate-200 dark:bg-slate-700"
                )}
              />
            ))}
          </div>

          <div>
            {currentStep === "done" ? (
              <button onClick={onClose} className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors">
                Done
              </button>
            ) : currentStep === "test" ? null : (
              <button
                onClick={goNext}
                disabled={!canProceed()}
                className="flex items-center gap-1 px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next <ChevronRight size={14} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
