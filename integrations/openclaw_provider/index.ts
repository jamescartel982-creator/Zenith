import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { buildProviderReplayFamilyHooks } from "openclaw/plugin-sdk/provider-model-shared";
import { buildReplayPolicy, wrapStreamFn } from "./policy.mjs";

const replay = buildProviderReplayFamilyHooks({ family: "openai-compatible" });

// Host-supported provider hooks; no upstream source or model artifact patches.
export default definePluginEntry({
  id: "zenith-local-context",
  name: "Zenith local context compatibility",
  description: "Current-turn runtime context for the preserved local Zenith model",
  register(api) {
    api.registerProvider({
      id: "zenith",
      label: "Zenith",
      auth: [],
      buildReplayPolicy: (context) => buildReplayPolicy(context, replay.buildReplayPolicy),
      wrapStreamFn,
    });
  },
});
