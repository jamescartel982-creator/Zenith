import assert from "node:assert/strict";
import test from "node:test";
import { buildReplayPolicy } from "./policy.mjs";

const context = { provider: "zenith", modelId: "zenith", modelApi: "openai-completions",
  model: { baseUrl: "http://127.0.0.1:8781/v1", reasoning: false } };
test("retains native sanitation and changes only temporal context retention", () => {
  const native = { sanitizeToolCallIds: true, validateAnthropicTurns: true, dropReasoningFromHistory: true };
  assert.deepEqual(buildReplayPolicy(context, () => native), { ...native, appendOnlyRuntimeContext: false });
  assert.equal(native.appendOnlyRuntimeContext, undefined);
});
test("refuses unrelated models, remote endpoints and unsupported protocols", () => {
  for (const changed of [ { provider: "other" }, { modelId: "other" }, { modelApi: "openai-responses" },
    { model: { ...context.model, reasoning: true } },
    ...["https://example.com/v1", "http://127.0.0.1.evil.test/v1", "http://user@localhost/v1",
      "http://localhost/v1?override=true", "http://localhost/v1#fragment", "http://localhost/other"].map(baseUrl => ({ model: { baseUrl } })) ]) {
    assert.throws(() => buildReplayPolicy({ ...context, ...changed }, () => ({})));
  }
});
