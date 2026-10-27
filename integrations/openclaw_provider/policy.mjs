/** Explicit, narrow compatibility policy. No credentials, tools or model fallback. */
export function buildReplayPolicy(context, nativePolicy) {
  const url = new URL(context.model?.baseUrl ?? "");
  if (context.provider !== "zenith" || context.modelId !== "zenith" ||
      context.modelApi !== "openai-completions" || context.model?.reasoning === true ||
      url.protocol !== "http:" || !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) ||
      url.username || url.password || url.search || url.hash || url.pathname.replace(/\/$/, "") !== "/v1") {
    throw new Error("Zenith context compatibility requires the configured local non-reasoning Zenith endpoint");
  }
  // Keep the host's normal tool/history sanitation. This model does not use
  // exact-entry prefix caching or prefix-bound thinking. Its current request
  // should not be followed by empty historical runtime-context snapshots.
  return { ...nativePolicy(context), appendOnlyRuntimeContext: false };
}
