"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  HardDrive,
  Users,
} from "lucide-react";
import { useAgentStore } from "@/stores/agentStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";
import type { AgentCapacityCheck, AgentCapability, AgentRole } from "@/lib/types";
import { ALL_CAPABILITIES, ROLE_COLORS, ROLE_LABELS } from "./agentViewConfig";
import {
  AGENT_HEARTBEAT_MAX_SECONDS,
  AGENT_HEARTBEAT_MIN_SECONDS,
  agentHeartbeatError,
  isAgentHeartbeatValid,
} from "@/lib/agentWizardForm";

function formatCapacityGb(value?: number | null): string {
  return Number.isFinite(value) && Number(value) > 0
    ? `${Number(value).toFixed(1)}GB`
    : "Unknown";
}

function ramUsedPct(available?: number | null, total?: number | null): number | null {
  if (!Number.isFinite(available) || !Number.isFinite(total) || Number(total) <= 0) {
    return null;
  }
  const pct = ((Number(total) - Number(available)) / Number(total)) * 100;
  return Math.min(100, Math.max(0, Math.round(pct)));
}

function AgentIdentityStep({ name, onNameChange }: { name: string; onNameChange: (value: string) => void }) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Agent Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="e.g. Research Assistant, Interview Analyst..."
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500"
          autoFocus
        />
      </div>
      <p className="text-xs text-slate-400">
        You can upload an avatar after creation from the agent detail panel.
      </p>
    </div>
  );
}

function AgentRolePromptStep({
  role,
  prompt,
  onRoleChange,
  onPromptChange,
}: {
  role: AgentRole;
  prompt: string;
  onRoleChange: (value: AgentRole) => void;
  onPromptChange: (value: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Role</label>
        <select
          value={role}
          onChange={(e) => onRoleChange(e.target.value as AgentRole)}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500"
        >
          {Object.entries(ROLE_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">System Prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder="Describe what this agent should do, its personality, and any specific instructions..."
          rows={6}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-istara-500 resize-none"
        />
      </div>
    </div>
  );
}

function AgentCapabilitiesStep({
  capabilities,
  onToggleCapability,
  heartbeatInterval,
  onHeartbeatChange,
  heartbeatError,
}: {
  capabilities: AgentCapability[];
  onToggleCapability: (capability: AgentCapability) => void;
  heartbeatInterval: number | "";
  onHeartbeatChange: (value: number | "") => void;
  heartbeatError: string | null;
}) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">Toggle which capabilities this agent has access to.</p>
      {ALL_CAPABILITIES.map((cap) => (
        <label key={cap.id} className="flex items-center justify-between p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer">
          <div>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{cap.label}</p>
            <p className="text-xs text-slate-400">{cap.description}</p>
          </div>
          <input
            type="checkbox"
            checked={capabilities.includes(cap.id)}
            onChange={() => onToggleCapability(cap.id)}
            className="w-4 h-4 rounded border-slate-300 text-istara-600 focus:ring-istara-500"
          />
        </label>
      ))}
      <div className="pt-2">
        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
          Heartbeat Interval (seconds)
        </label>
        <input
          type="number"
          value={heartbeatInterval}
          onChange={(e) => onHeartbeatChange(e.target.value === "" ? "" : Number(e.target.value))}
          min={AGENT_HEARTBEAT_MIN_SECONDS}
          max={AGENT_HEARTBEAT_MAX_SECONDS}
          aria-invalid={heartbeatError ? true : undefined}
          aria-describedby={heartbeatError ? "agent-heartbeat-error" : undefined}
          className="w-32 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm"
        />
        {heartbeatError && (
          <p id="agent-heartbeat-error" role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
            {heartbeatError}
          </p>
        )}
      </div>
    </div>
  );
}

function AgentHardwareStep({ capacity, memoryUsedPct }: { capacity: AgentCapacityCheck | null; memoryUsedPct: number | null }) {
  return (
    <div className="space-y-4">
      {capacity ? (
        <div className={cn(
          "p-4 rounded-lg border",
          capacity.can_create
            ? "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20"
            : "border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20"
        )}>
          <div className="flex items-center gap-2 mb-2">
            {capacity.can_create ? (
              <CheckCircle2 size={18} className="text-green-600" />
            ) : (
              <AlertTriangle size={18} className="text-yellow-600" />
            )}
            <span className="font-medium text-sm">{capacity.reason}</span>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
              <Users size={14} />
              <span>{capacity.current_agents}/{capacity.max_agents} agents</span>
            </div>
            <div className="text-xs text-slate-600 dark:text-slate-400">
              <div className="flex items-center gap-2 mb-1">
                <HardDrive size={14} />
                <span>
                  {formatCapacityGb(capacity.ram_available_gb)} free of {formatCapacityGb(capacity.ram_total_gb)} RAM
                </span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all", {
                    "bg-green-500": memoryUsedPct !== null && memoryUsedPct < 70,
                    "bg-yellow-500": memoryUsedPct !== null && memoryUsedPct >= 70 && memoryUsedPct < 90,
                    "bg-red-500": memoryUsedPct !== null && memoryUsedPct >= 90,
                    "bg-slate-300 dark:bg-slate-600": memoryUsedPct === null,
                  })}
                  style={{ width: `${memoryUsedPct ?? 0}%` }}
                />
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">
                {memoryUsedPct === null ? "RAM usage unavailable" : `${memoryUsedPct}% used`}
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
              <Cpu size={14} />
              <span>{capacity.cpu_cores} CPU cores</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
              <Activity size={14} />
              <span>Pressure: {capacity.pressure}</span>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-400">Checking hardware capacity...</p>
      )}
      {capacity && !capacity.can_create && (
        <p className="text-xs text-yellow-600 dark:text-yellow-400">
          You can still create the agent, but it may not run optimally. Consider pausing unused agents first.
        </p>
      )}
    </div>
  );
}

function AgentReviewStep({
  name,
  role,
  capabilities,
  prompt,
  heartbeatInterval,
}: {
  name: string;
  role: AgentRole;
  capabilities: AgentCapability[];
  prompt: string;
  heartbeatInterval: number | "";
}) {
  return (
    <div className="space-y-3">
      <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Name</span>
          <span className="font-medium text-slate-900 dark:text-white">{name || "-"}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Role</span>
          <span className={cn("text-xs px-2 py-0.5 rounded-full", ROLE_COLORS[role])}>{ROLE_LABELS[role]}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Capabilities</span>
          <span className="text-slate-700 dark:text-slate-300">{capabilities.length} enabled</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Heartbeat</span>
          <span className="text-slate-700 dark:text-slate-300">
            {isAgentHeartbeatValid(heartbeatInterval) ? `every ${heartbeatInterval}s` : "-"}
          </span>
        </div>
      </div>
      {prompt && (
        <div>
          <p className="text-xs text-slate-500 mb-1">System Prompt</p>
          <p className="text-xs text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/50 p-2 rounded line-clamp-4">{prompt}</p>
        </div>
      )}
    </div>
  );
}

function AgentWizardStepIndicator({ step, steps }: { step: number; steps: string[] }) {
  return (
    <div className="flex items-center gap-2">
      {steps.map((label, index) => (
        <div key={label} className="flex items-center gap-2">
          <span
            className={cn(
              "w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-colors",
              index === step
                ? "bg-istara-600 text-white"
                : index < step
                ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                : "bg-slate-100 text-slate-400 dark:bg-slate-800"
            )}
            aria-current={index === step ? "step" : undefined}
          >
            {index + 1}
          </span>
          {index < steps.length - 1 && (
            <div className={cn("w-6 h-0.5", index < step ? "bg-istara-400" : "bg-slate-200 dark:bg-slate-700")} />
          )}
        </div>
      ))}
    </div>
  );
}

function AgentWizardContent({
  step,
  name,
  role,
  prompt,
  capabilities,
  heartbeatInterval,
  heartbeatError,
  capacity,
  memoryUsedPct,
  onNameChange,
  onRoleChange,
  onPromptChange,
  onToggleCapability,
  onHeartbeatChange,
}: {
  step: number;
  name: string;
  role: AgentRole;
  prompt: string;
  capabilities: AgentCapability[];
  heartbeatInterval: number | "";
  heartbeatError: string | null;
  capacity: AgentCapacityCheck | null;
  memoryUsedPct: number | null;
  onNameChange: (value: string) => void;
  onRoleChange: (value: AgentRole) => void;
  onPromptChange: (value: string) => void;
  onToggleCapability: (capability: AgentCapability) => void;
  onHeartbeatChange: (value: number | "") => void;
}) {
  switch (step) {
    case 0:
      return <AgentIdentityStep name={name} onNameChange={onNameChange} />;
    case 1:
      return (
        <AgentRolePromptStep
          role={role}
          prompt={prompt}
          onRoleChange={onRoleChange}
          onPromptChange={onPromptChange}
        />
      );
    case 2:
      return (
        <AgentCapabilitiesStep
          capabilities={capabilities}
          onToggleCapability={onToggleCapability}
          heartbeatInterval={heartbeatInterval}
          onHeartbeatChange={onHeartbeatChange}
          heartbeatError={heartbeatError}
        />
      );
    case 3:
      return <AgentHardwareStep capacity={capacity} memoryUsedPct={memoryUsedPct} />;
    case 4:
      return (
        <AgentReviewStep
          name={name}
          role={role}
          capabilities={capabilities}
          prompt={prompt}
          heartbeatInterval={heartbeatInterval}
        />
      );
    default:
      return null;
  }
}

function AgentWizardNavigation({
  step,
  name,
  activeProjectId,
  heartbeatError,
  creating,
  onBack,
  onNext,
  onCreate,
}: {
  step: number;
  name: string;
  activeProjectId: string | null;
  heartbeatError: string | null;
  creating: boolean;
  onBack: () => void;
  onNext: () => void;
  onCreate: () => void;
}) {
  const canAdvance = step !== 0 || Boolean(name.trim());
  const heartbeatStepValid = step !== 2 || !heartbeatError;
  return (
    <div className="flex justify-between pt-2">
      <button
        onClick={onBack}
        className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
      >
        {step === 0 ? "Cancel" : "Back"}
      </button>
      {step < 4 ? (
        <button
          onClick={onNext}
          disabled={!canAdvance || !heartbeatStepValid}
          className="flex items-center gap-1 px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50"
        >
          Next <ArrowRight size={14} />
        </button>
      ) : (
        <button
          onClick={onCreate}
          disabled={creating || !name.trim() || !activeProjectId || Boolean(heartbeatError)}
          className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 disabled:opacity-50"
        >
          {creating ? "Creating..." : "Create Agent"}
        </button>
      )}
    </div>
  );
}

export default function CreateAgentWizard({ onDone }: { onDone: () => void }) {
  const { createAgent, fetchCapacity, capacity } = useAgentStore();
  const { activeProjectId } = useProjectStore();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [role, setRole] = useState<AgentRole>("custom");
  const [prompt, setPrompt] = useState("");
  const [capabilities, setCapabilities] = useState<AgentCapability[]>([
    "skill_execution",
    "task_creation",
    "findings_write",
    "chat",
    "rag_retrieval",
    "a2a_messaging",
  ]);
  const [heartbeatInterval, setHeartbeatInterval] = useState<number | "">(60);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (step === 3) fetchCapacity();
  }, [step, fetchCapacity]);

  const toggleCapability = (cap: AgentCapability) => {
    setCapabilities((prev) =>
      prev.includes(cap) ? prev.filter((c) => c !== cap) : [...prev, cap]
    );
  };

  const memoryUsedPct = ramUsedPct(capacity?.ram_available_gb, capacity?.ram_total_gb);
  const heartbeatError = agentHeartbeatError(heartbeatInterval);

  const handleCreate = async () => {
    if (!name.trim() || !activeProjectId || !isAgentHeartbeatValid(heartbeatInterval)) return;
    setCreating(true);
    try {
      await createAgent(
        {
          name: name.trim(),
          role,
          system_prompt: prompt,
          capabilities,
          heartbeat_interval: heartbeatInterval,
        },
        activeProjectId
      );
      onDone();
    } catch (e: any) {
      alert(e.message);
    }
    setCreating(false);
  };

  const steps = ["Identity", "Role & Prompt", "Capabilities", "Hardware Check", "Review"];

  return (
    <div className="space-y-6">
      <AgentWizardStepIndicator step={step} steps={steps} />
      <p className="text-xs text-slate-500">{steps[step]}</p>

      <AgentWizardContent
        step={step}
        name={name}
        role={role}
        prompt={prompt}
        capabilities={capabilities}
        heartbeatInterval={heartbeatInterval}
        heartbeatError={heartbeatError}
        capacity={capacity}
        memoryUsedPct={memoryUsedPct}
        onNameChange={setName}
        onRoleChange={setRole}
        onPromptChange={setPrompt}
        onToggleCapability={toggleCapability}
        onHeartbeatChange={setHeartbeatInterval}
      />

      <AgentWizardNavigation
        step={step}
        name={name}
        activeProjectId={activeProjectId}
        heartbeatError={heartbeatError}
        creating={creating}
        onBack={() => step > 0 ? setStep(step - 1) : onDone()}
        onNext={() => setStep(step + 1)}
        onCreate={handleCreate}
      />
    </div>
  );
}
