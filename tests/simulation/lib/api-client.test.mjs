import assert from "node:assert/strict";
import test from "node:test";

import { authHeaders, setAuthToken } from "./api-client.mjs";

test("shared API client headers follow the harness auth token", () => {
  setAuthToken("simulation-token");
  assert.equal(authHeaders().Authorization, "Bearer simulation-token");

  setAuthToken("");
  assert.equal(authHeaders().Authorization, undefined);
});
