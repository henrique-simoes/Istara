"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { useLoopsStore } from "@/stores/loopsStore";
import { useProjectStore } from "@/stores/projectStore";
import { skills as skillsApi } from "@/lib/api";
import CustomLoopList from "./CustomLoopList";
import CustomLoopFormPanel, { EMPTY_CUSTOM_LOOP_FORM, type CustomLoopForm } from "./CustomLoopFormPanel";

export default function CustomLoopsTab() {
  const { health, loading, error, createCustomLoop, fetchHealth } = useLoopsStore();
  const { activeProjectId } = useProjectStore();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CustomLoopForm>({ ...EMPTY_CUSTOM_LOOP_FORM });
  const [availableSkills, setAvailableSkills] = useState<{ id: string; name: string }[]>([]);

  useEffect(() => {
    fetchHealth(activeProjectId);
    skillsApi.list().then((res: any) => {
      const list = Array.isArray(res) ? res : (res?.skills ?? []);
      setAvailableSkills(list.map((skill: any) => ({ id: skill.skill_id || skill.id, name: skill.name || skill.skill_id || skill.id })));
    }).catch(() => {});
  }, [activeProjectId, fetchHealth]);

  const customLoops = health.filter((loop) => loop.source_type === "custom");
  const handleCreate = async () => {
    if (!activeProjectId || !form.name.trim() || !form.skill_name.trim()) return;
    const data: Parameters<typeof createCustomLoop>[0] = {
      name: form.name,
      skill_name: form.skill_name,
      project_id: activeProjectId,
      description: form.description,
      ...(form.mode === "cron"
        ? { cron_expression: form.cron_expression }
        : { interval_seconds: typeof form.interval_seconds === "number" ? form.interval_seconds : 300 }),
    };
    if (!await createCustomLoop(data)) return;
    setForm({ ...EMPTY_CUSTOM_LOOP_FORM });
    setShowForm(false);
  };
  const closeForm = () => {
    setShowForm(false);
    setForm({ ...EMPTY_CUSTOM_LOOP_FORM });
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Custom Loops</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium bg-istara-600 text-white hover:bg-istara-700 transition-colors"
        >
          <Plus size={14} />
          Create Loop
        </button>
      </div>

      {showForm && (
        <CustomLoopFormPanel
          form={form}
          availableSkills={availableSkills}
          activeProjectId={activeProjectId}
          loading={loading}
          error={error}
          onChange={setForm}
          onCreate={handleCreate}
          onCancel={closeForm}
        />
      )}
      <CustomLoopList loops={customLoops} loading={loading} />
    </div>
  );
}
