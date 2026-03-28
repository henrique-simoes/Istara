/** Scenario 69 — User Management UI: tests for team member management via API.
 *
 *  Exercises: /api/auth/users (CRUD), role changes
 */

export const name = "User Management";
export const id = "69-user-management-ui";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const cleanup = { userIds: [] };

  // ── 1. List users — admin can see all ──
  try {
    const users = await api.get("/api/auth/users");
    const list = Array.isArray(users) ? users : users?.users || [];
    checks.push({
      name: "Admin can list team members",
      passed: list.length >= 1,
      detail: `${list.length} team member(s)`,
    });
  } catch (e) {
    checks.push({ name: "List team members", passed: false, detail: e.message });
  }

  // ── 2. Invite (create) a new member ──
  let newUser = null;
  try {
    newUser = await api.post("/api/auth/users", {
      username: "sim-researcher",
      email: "researcher@sim.test",
      password: "temp-password-123",
      display_name: "SIM Researcher",
    });
    cleanup.userIds.push(newUser.id);
    checks.push({
      name: "Invite new team member",
      passed: !!newUser.id && newUser.username === "sim-researcher",
      detail: `Created ${newUser.username} (${newUser.role})`,
    });
  } catch (e) {
    checks.push({ name: "Invite new member", passed: false, detail: e.message });
  }

  // ── 3. New user has researcher role by default ──
  if (newUser) {
    checks.push({
      name: "New member defaults to researcher role",
      passed: newUser.role === "researcher",
      detail: `role=${newUser.role}`,
    });
  }

  // ── 4. Change role to viewer ──
  if (newUser) {
    try {
      const updated = await api.patch(`/api/auth/users/${newUser.id}/role`, { role: "viewer" });
      checks.push({
        name: "Change member role to viewer",
        passed: updated.role === "viewer",
        detail: `role changed to ${updated.role}`,
      });
    } catch (e) {
      checks.push({ name: "Change role", passed: false, detail: e.message });
    }
  }

  // ── 5. Change role to admin ──
  if (newUser) {
    try {
      const updated = await api.patch(`/api/auth/users/${newUser.id}/role`, { role: "admin" });
      checks.push({
        name: "Change member role to admin",
        passed: updated.role === "admin",
        detail: `role changed to ${updated.role}`,
      });
    } catch (e) {
      checks.push({ name: "Promote to admin", passed: false, detail: e.message });
    }
  }

  // ── 6. Duplicate username rejected ──
  try {
    await api.post("/api/auth/users", {
      username: "admin",
      email: "dup@sim.test",
      password: "test",
    });
    checks.push({ name: "Duplicate username rejected", passed: false, detail: "Should have failed" });
  } catch (e) {
    checks.push({
      name: "Duplicate username rejected",
      passed: true,
      detail: e.message.slice(0, 60),
    });
  }

  // ── 7. Invalid role rejected ──
  if (newUser) {
    try {
      await api.patch(`/api/auth/users/${newUser.id}/role`, { role: "superadmin" });
      checks.push({ name: "Invalid role rejected", passed: false, detail: "Should have failed" });
    } catch (e) {
      checks.push({
        name: "Invalid role rejected",
        passed: true,
        detail: e.message.slice(0, 60),
      });
    }
  }

  // ── 8. Delete member ──
  if (newUser) {
    try {
      await api.delete(`/api/auth/users/${newUser.id}`);
      cleanup.userIds = cleanup.userIds.filter((id) => id !== newUser.id);
      checks.push({
        name: "Delete team member",
        passed: true,
        detail: `Deleted ${newUser.username}`,
      });
    } catch (e) {
      checks.push({ name: "Delete member", passed: false, detail: e.message });
    }
  }

  // ── 9. Deleted member gone from list ──
  try {
    const users = await api.get("/api/auth/users");
    const list = Array.isArray(users) ? users : users?.users || [];
    const found = list.find((u) => u.username === "sim-researcher");
    checks.push({
      name: "Deleted member removed from list",
      passed: !found,
      detail: found ? "STILL FOUND" : "Correctly removed",
    });
  } catch (e) {
    checks.push({ name: "Deletion verified", passed: false, detail: e.message });
  }

  // ── 10. New member can log in ──
  let loginUser = null;
  try {
    loginUser = await api.post("/api/auth/users", {
      username: "sim-login-test",
      email: "login@sim.test",
      password: "login-test-pass",
    });
    cleanup.userIds.push(loginUser.id);

    const loginRes = await fetch("http://localhost:8000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "sim-login-test", password: "login-test-pass" }),
    });
    checks.push({
      name: "New member can log in with temp password",
      passed: loginRes.ok,
      detail: `login status=${loginRes.status}`,
    });
  } catch (e) {
    checks.push({ name: "New member login", passed: false, detail: e.message });
  }

  // ── Cleanup ──
  for (const id of cleanup.userIds) {
    try { await api.delete(`/api/auth/users/${id}`); } catch {}
  }

  return checks;
}
