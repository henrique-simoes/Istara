import { beforeEach, describe, expect, it, vi } from "vitest";

const create = vi.fn();

vi.mock("@/lib/api", () => ({
  tasks: {
    create,
    list: vi.fn(),
    move: vi.fn(),
    update: vi.fn(),
    approve: vi.fn(),
    requestRevision: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("task store quick-create", () => {
  beforeEach(() => {
    create.mockReset();
  });

  it("requests an atomic editing lock before exposing a new task", async () => {
    const task = { id: "task-1", project_id: "project-1", title: "Configure me" };
    create.mockResolvedValue(task);
    const { useTaskStore } = await import("./taskStore");

    await expect(
      useTaskStore.getState().createTask("project-1", "Configure me", undefined, { lockForEdit: true })
    ).resolves.toEqual(task);

    expect(create).toHaveBeenCalledWith({
      project_id: "project-1",
      title: "Configure me",
      description: undefined,
      lock_for_edit: true,
    });
  });
});
