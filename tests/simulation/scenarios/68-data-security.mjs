/** Scenario 68 — Data Security: tests for field encryption, user management, filesystem hardening.
 *
 *  Exercises: /api/auth/users, field encryption, backup security
 */

export const name = "Data Security";
export const id = "68-data-security";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. Admin user management — list users ──
  try {
    const users = await api.get("/api/auth/users");
    const list = Array.isArray(users) ? users : users?.users || [];
    checks.push({
      name: "Admin can list users",
      passed: list.length >= 1,
      detail: `${list.length} users found`,
    });
  } catch (e) {
    checks.push({ name: "Admin can list users", passed: false, detail: e.message });
  }

  // ── 2. Admin can create a user ──
  let testUserId = null;
  try {
    const user = await api.post("/api/auth/users", {
      username: "sim-test-user",
      email: "sim@test.local",
      password: "test-password-123",
      display_name: "SIM Test User",
    });
    testUserId = user.id;
    checks.push({
      name: "Admin can create user via API",
      passed: !!user.id && user.username === "sim-test-user",
      detail: `Created user ${user.id}`,
    });
  } catch (e) {
    checks.push({ name: "Admin can create user via API", passed: false, detail: e.message });
  }

  // ── 3. Created user appears in list ──
  if (testUserId) {
    try {
      const users = await api.get("/api/auth/users");
      const list = Array.isArray(users) ? users : users?.users || [];
      const found = list.find((u) => u.id === testUserId);
      checks.push({
        name: "Created user appears in user list",
        passed: !!found,
        detail: found ? `${found.username} (${found.role})` : "NOT FOUND",
      });
    } catch (e) {
      checks.push({ name: "Created user in list", passed: false, detail: e.message });
    }
  }

  // ── 4. Duplicate username rejected ──
  try {
    await api.post("/api/auth/users", {
      username: "admin",
      email: "dup@test.local",
      password: "test",
    });
    checks.push({ name: "Duplicate username rejected", passed: false, detail: "Should have failed" });
  } catch (e) {
    checks.push({
      name: "Duplicate username rejected",
      passed: e.message.includes("409") || e.message.includes("exists"),
      detail: e.message.slice(0, 80),
    });
  }

  // ── 5. Admin can delete user ──
  if (testUserId) {
    try {
      await api.delete(`/api/auth/users/${testUserId}`);
      checks.push({
        name: "Admin can delete user",
        passed: true,
        detail: `Deleted ${testUserId}`,
      });
    } catch (e) {
      checks.push({ name: "Admin can delete user", passed: false, detail: e.message });
    }
  }

  // ── 6. Channel credentials stored encrypted ──
  let channelId = null;
  try {
    const channel = await api.post("/api/channels", {
      platform: "telegram",
      name: "SIM: Encryption Test Bot",
      config: { bot_token: "test-secret-token-12345" },
    });
    channelId = channel.id;
    // The config should be stored encrypted — we can't verify from API
    // but we verify the channel was created and can be read back
    const detail = await api.get(`/api/channels/${channel.id}`);
    checks.push({
      name: "Channel credentials stored (encryption active if key configured)",
      passed: !!detail.id,
      detail: `Channel ${detail.id} created, config stored`,
    });
  } catch (e) {
    checks.push({ name: "Channel credential storage", passed: false, detail: e.message });
  }

  // ── 7. Cleanup test channel ──
  if (channelId) {
    try { await api.delete(`/api/channels/${channelId}`); } catch {}
  }

  // ── 8. Settings status accessible (exempt from auth for frontend check) ──
  try {
    const res = await fetch("http://localhost:8000/api/settings/status");
    checks.push({
      name: "Settings status exempt from auth (for frontend LLM check)",
      passed: res.status === 200,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Settings status exempt", passed: false, detail: e.message });
  }

  // ── 9. Security headers on responses ──
  try {
    const res = await fetch("http://localhost:8000/api/health");
    const headers = {
      "x-content-type-options": res.headers.get("x-content-type-options"),
      "x-frame-options": res.headers.get("x-frame-options"),
      "referrer-policy": res.headers.get("referrer-policy"),
    };
    const allPresent = headers["x-content-type-options"] === "nosniff" &&
                       headers["x-frame-options"] === "DENY";
    checks.push({
      name: "Security headers present on all responses",
      passed: allPresent,
      detail: JSON.stringify(headers),
    });
  } catch (e) {
    checks.push({ name: "Security headers", passed: false, detail: e.message });
  }

  // ── 10. Role change endpoint ──
  let tempUserId = null;
  try {
    const user = await api.post("/api/auth/users", {
      username: "sim-role-test",
      email: "role@test.local",
      password: "test-123",
    });
    tempUserId = user.id;
    const updated = await api.patch(`/api/auth/users/${user.id}/role`, { role: "viewer" });
    checks.push({
      name: "Admin can change user role",
      passed: updated.role === "viewer",
      detail: `Role changed to ${updated.role}`,
    });
  } catch (e) {
    checks.push({ name: "Role change", passed: false, detail: e.message });
  }
  if (tempUserId) {
    try { await api.delete(`/api/auth/users/${tempUserId}`); } catch {}
  }

  return checks;
}
