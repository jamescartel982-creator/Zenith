// Optional edge transport only. Zenith inference and state remain in Python.
const MAX_BODY = 512 * 1024;
const METHODS = new Set(['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']);
const HOP = ['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailer', 'transfer-encoding', 'upgrade', 'content-length'];
const validSecret = value => typeof value === 'string' && value.length >= 32 && value.length <= 256 && !/[^A-Za-z0-9_-]/.test(value);
class Rejection extends Error {
  constructor(status, message, code, settings) {
    super(message); this.status = status; this.code = code; this.settings = settings;
  }
}

function protect(headers, secure) {
  headers.set('Cache-Control', 'no-store'); headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('Referrer-Policy', 'no-referrer'); headers.set('X-Frame-Options', 'DENY');
  headers.set('Cross-Origin-Opener-Policy', 'same-origin'); headers.set('Cross-Origin-Resource-Policy', 'same-origin');
  headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=()');
  headers.set('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
  if (secure) headers.set('Strict-Transport-Security', 'max-age=31536000');
  return headers;
}
function json(status, value, secure) {
  return new Response(JSON.stringify(value), {status, headers: protect(new Headers({'Content-Type':'application/json'}), secure)});
}
function backend(env, incoming) {
  // Report names only: never echo settings, URLs, credentials or parse errors.
  const missing = ['ZENITH_BACKEND_URL', 'ZENITH_ORIGIN_SECRET'].filter(name =>
    typeof env[name] !== 'string' || !env[name].trim());
  if (missing.length) throw new Rejection(503, 'Zenith origin is not configured', 'origin_not_configured', missing);
  if (!validSecret(env.ZENITH_ORIGIN_SECRET)) throw new Rejection(503, 'Invalid Zenith origin secret configuration', 'origin_secret_invalid', ['ZENITH_ORIGIN_SECRET']);
  let url; try { url = new URL(env.ZENITH_BACKEND_URL); } catch {
    throw new Rejection(503, 'Invalid Zenith origin URL configuration', 'origin_url_invalid', ['ZENITH_BACKEND_URL']);
  }
  const local = env.ZENITH_TEST_LOOPBACK === '1' && ['127.0.0.1', '[::1]', 'localhost'].includes(url.hostname);
  if ((url.protocol !== 'https:' && !(local && url.protocol === 'http:')) || url.username || url.password ||
      url.pathname !== '/' || url.search || url.hash) throw new Rejection(503, 'Invalid Zenith origin configuration', 'origin_url_invalid', ['ZENITH_BACKEND_URL']);
  // A different port or DNS trailing dot does not make this a different service.
  if (url.hostname.replace(/\.$/, '') === incoming.hostname.replace(/\.$/, '') &&
      !(local && url.host !== incoming.host)) {
    throw new Rejection(503, 'Zenith origin points to this gateway', 'origin_loop', ['ZENITH_BACKEND_URL']);
  }
  return url;
}
async function boundedBody(request) {
  if (!request.body) return undefined;
  const declared = request.headers.get('content-length');
  if (declared && (!/^\d+$/.test(declared) || Number(declared) > MAX_BODY)) throw new Rejection(413, 'Request body is too large');
  const reader = request.body.getReader(), buffer = new Uint8Array(MAX_BODY);
  let length = 0, timedOut = false;
  const timer = setTimeout(() => { timedOut = true; reader.cancel().catch(() => {}); }, 15000);
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (timedOut) throw new Rejection(408, 'Request body timed out');
      if (done) return buffer.slice(0, length);
      if (length + value.length > MAX_BODY) { void reader.cancel().catch(() => {}); throw new Rejection(413, 'Request body is too large'); }
      buffer.set(value, length); length += value.length;
    }
  } finally { clearTimeout(timer); reader.releaseLock(); }
}

export async function handle(request, env, fetchOrigin = fetch) {
  const incoming = new URL(request.url), secure = incoming.protocol === 'https:';
  try {
    if (!secure) throw new Rejection(426, 'Use HTTPS to access Zenith');
    if (!METHODS.has(request.method)) throw new Rejection(405, 'Method is not supported');
    // Liveness is deliberately independent of origin configuration/readiness.
    if (incoming.pathname === '/_edge/livez' && ['GET', 'HEAD'].includes(request.method)) {
      return json(200, {status:'edge-alive', backend_verified:false, inference_verified:false}, secure);
    }
    // Detect an origin alias routed back to this Worker, before making another
    // fetch. Unauthenticated client-supplied proxy headers are still stripped.
    if (validSecret(env.ZENITH_ORIGIN_SECRET) &&
        request.headers.get('X-Zenith-Origin-Secret') === env.ZENITH_ORIGIN_SECRET) {
      throw new Rejection(508, 'Zenith origin routes back to this gateway', 'origin_loop');
    }
    const target = backend(env, incoming);
    const configured = Number(env.ZENITH_BACKEND_TIMEOUT_MS || 120000);
    if (!Number.isInteger(configured) || configured < 1000 || configured > 120000) throw new Rejection(503, 'Invalid Zenith timeout configuration');
    if (incoming.pathname === '/_edge/healthz') return json(200, {status:'edge-ready', backend_configured:true, backend_verified:false, inference_verified:false}, secure);
    const origin = request.headers.get('origin');
    if (origin && origin !== incoming.origin) throw new Rejection(403, 'Cross-site requests are not allowed');
    if (request.headers.get('sec-fetch-site')?.toLowerCase() === 'cross-site' && incoming.pathname.startsWith('/api/')) throw new Rejection(403, 'Cross-site API requests are not allowed');
    target.pathname = incoming.pathname; target.search = incoming.search; // Never resolve a client-controlled host.
    const headers = new Headers(request.headers);
    for (const key of [...headers.keys()]) if (HOP.includes(key) || key === 'host' || key === 'forwarded' || key.startsWith('x-forwarded-') || key.startsWith('x-zenith-')) headers.delete(key);
    headers.set('X-Zenith-Origin-Secret', env.ZENITH_ORIGIN_SECRET);
    headers.set('X-Zenith-Public-Origin', incoming.origin);
    const clientIP = request.headers.get('CF-Connecting-IP');
    if (clientIP) headers.set('X-Zenith-Client-IP', clientIP);
    const body = await boundedBody(request);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), configured);
    const cancel = () => controller.abort(); request.signal.addEventListener('abort', cancel, {once:true});
    let upstream;
    try {
      upstream = await fetchOrigin(new Request(target, {method:request.method, headers, body, redirect:'manual', signal:controller.signal}));
    } catch {
      throw new Rejection(controller.signal.aborted ? 504 : 502, 'Zenith backend is unavailable', controller.signal.aborted ? 'origin_timeout' : 'origin_unreachable');
    } finally { clearTimeout(timer); request.signal.removeEventListener('abort', cancel); }
    if (upstream.status >= 300 && upstream.status < 400) {
      await upstream.body?.cancel();
      throw new Rejection(502, 'Zenith backend must serve requests without redirects', 'origin_redirect');
    }
    // Preserve host-only account/access cookies and the native streaming body.
    const output = protect(new Headers(upstream.headers), secure);
    for (const key of HOP) output.delete(key);
    return new Response(upstream.body, {status:upstream.status, statusText:upstream.statusText, headers:output});
  } catch (error) {
    return json(error instanceof Rejection ? error.status : 502,
      {detail:error instanceof Rejection ? error.message : 'Zenith gateway could not complete this request',
        ...(error instanceof Rejection && error.code ? {code:error.code} : {}),
        ...(error instanceof Rejection && error.settings ? {required_settings:error.settings} : {})}, secure);
  }
}

export default {
  async fetch(request, env) {
    const started = Date.now(), id = crypto.randomUUID();
    const response = await handle(request, env);
    console.log(JSON.stringify({event:'zenith.edge', id, method:request.method, status:response.status, duration_ms:Date.now()-started}));
    return response;
  }
};
