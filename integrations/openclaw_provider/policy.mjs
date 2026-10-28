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

/** Keep native facts, but finish the model projection with the actual user turn. */
export function projectCurrentTurn(context) {
  const messages = context.messages;
  if (!Array.isArray(messages) || context.tools?.length) return context;
  const runtime = (message) => message?.role === "user" &&
    (message.runtimeContext !== undefined || message.runtimeContextCarrier === true);
  const current = messages.findLastIndex((message) => message?.role === "user" &&
    !runtime(message) && !message.operatorMessage);
  if (current < 0 || current === messages.length - 1) return context;
  const trailing = messages.slice(current + 1);
  // Never cross an assistant turn, a tool result, or an operator instruction.
  // Text markers cannot manufacture runtime provenance.
  if (!trailing.every(runtime)) return context;
  return { ...context, messages: [
    ...messages.slice(0, current), ...trailing, messages[current],
  ] };
}

export function wrapStreamFn({ streamFn }) {
  if (!streamFn) return undefined;
  const wrapped = (model, context, options) => streamFn(model, projectCurrentTurn(context), options);
  wrapped.preservesGenericCompatibility = true;
  return wrapped;
}
