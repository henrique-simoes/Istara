export type RealtimeToastClassification = {
  type: "success" | "warning" | "info" | "agent";
  title: string;
  message: string;
};

type TaskProgressEvent = {
  progress: number;
  notes?: string;
  outcome?: string;
};

export function classifyTaskProgressToast(
  event: TaskProgressEvent
): RealtimeToastClassification | null {
  if (Math.round((event.progress || 0) * 100) !== 100) return null;

  const message = event.notes?.trim() || "Task execution reached a terminal update.";
  const outcome = event.outcome?.trim().toLowerCase();
  const verificationFailed =
    outcome === "verification_failed" || /^verification failed\b/i.test(message);

  if (verificationFailed) {
    return {
      type: "warning",
      title: "⚠️ Task Needs Attention",
      message,
    };
  }

  if (outcome === "ready_for_review") {
    return {
      type: "success",
      title: "✅ Ready for Review",
      message,
    };
  }

  return {
    type: "info",
    title: "ℹ️ Task Update",
    message,
  };
}

export function classifyAgentStatusToast(
  status: string,
  details: string
): RealtimeToastClassification | null {
  if (status === "working") {
    return { type: "agent", title: "🤖 Agent Working", message: details };
  }
  if (status === "warning") {
    return { type: "warning", title: "⚠️ Agent Needs Attention", message: details };
  }
  if (status === "error") {
    return { type: "warning", title: "⚠️ Agent Error", message: details };
  }
  return null;
}
