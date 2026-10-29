'use strict';
const $ = id => document.getElementById(id);
let session = sessionStorage.getItem('zenith_session') || crypto.randomUUID();
sessionStorage.setItem('zenith_session', session);
$('token').value = sessionStorage.getItem('zenith_token') || '';
let busy = false;
let chatController = null;
let showingServerMetrics = false;
let activeUser = null;
let registering = false;
let adminState = null;
let adminExpiry = null;
const welcomeTemplate = $('welcome').cloneNode(true);
let configuredTeam = null;
let knowledgeStatus = null;
let catalogPage = 1;
let discoveryCursors = [''];
let catalogRequest = 0;
let catalogLoaded = false;
let skillLibrary = null;
let skillLoadRequest = 0;
let skillStateReady = false;
let savedPreferences = {};
let preferenceLoadRequest = 0;
let importedSkillRequest = 0;
let importedSkillCursor = null;
let analysisRequest = 0;
let importedSkillTimer = null;

function showError(message) {
  $('error').textContent = message;
  $('error').hidden = !message;
}
async function api(path, options = {}) {
  const headers = {'Content-Type': 'application/json'};
  const token = sessionStorage.getItem('zenith_token');
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, {...options, headers});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && data.detail?.includes('server access token')) $('access').open = true;
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Request rejected. Check your input.');
  }
  return data;
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function sourceName(source) { return source === 'huggingface' ? 'Hugging Face' : source === 'github' ? 'GitHub' : String(source || 'Unknown source'); }
function displayValue(value, fallback = 'Not recorded') {
  if (Array.isArray(value)) return value.join(', ') || fallback;
  if (value && typeof value === 'object') return value.name || value.id || fallback;
  return value === undefined || value === null || value === '' ? fallback : String(value);
}
function number(value) { return Number.isFinite(Number(value)) ? Number(value).toLocaleString() : '—'; }
function teamMembers() {
  return [...(configuredTeam?.members || []), ...(configuredTeam?.synthesizer ? [configuredTeam.synthesizer] : [])];
}
function isConfigured(entry) {
  return entry.kind === 'model' && entry.source === 'huggingface' && teamMembers().some(member => member.model === entry.id && member.provider === 'huggingface');
}
function modelDescription(member) {
  const item = element('div', 'team-member');
  item.append(element('strong', '', member.name || member.id || 'Model'));
  item.append(element('span', '', member.model || 'Model not specified'));
  item.append(element('small', '', `${member.role || 'Contributor'} · ${member.provider || 'Configured endpoint'}`));
  if (member.available === false) item.append(element('small', 'team-warning', 'Currently unavailable'));
  return item;
}
function renderTeam() {
  $('team-members').replaceChildren();
  $('team-overview').replaceChildren();
  if (!configuredTeam) {
    $('team-label').textContent = 'Team status unavailable';
    $('team-members').append(element('p', '', 'The server did not provide a model-team configuration.'));
    $('team-overview').append(element('p', '', 'Team status is unavailable. Check the server configuration.'));
    return;
  }
  const members = configuredTeam.members || [];
  const ensemble = configuredTeam.mode === 'ensemble';
  $('team-label').textContent = ensemble ? `${members.length} configured contributors` : 'Single-model chat';
  $('open-team').textContent = ensemble ? `TEAM · ${members.length} MODELS` : 'SINGLE MODEL';
  $('team-overview').append(element('h3', '', ensemble ? 'A bounded team, one combined answer.' : 'One model is configured for chat.'));
  $('team-overview').append(element('p', '', ensemble ? 'Configured contributors draft responses, then a synthesizer combines the available answers. A failed contributor is reported with the answer. More models do not guarantee a better result.' : 'The catalog offers many model references. This server currently answers with one configured model.'));
  for (const member of members) {
    $('team-members').append(modelDescription(member));
    $('team-overview').append(modelDescription(member));
  }
  if (configuredTeam.synthesizer) {
    $('team-overview').append(element('h4', '', 'Final synthesis'));
    $('team-overview').append(modelDescription({...configuredTeam.synthesizer, role: 'Synthesizer'}));
  }
  if (configuredTeam.limits && Object.keys(configuredTeam.limits).length) {
    const limits = element('dl', 'team-limits');
    for (const [key, value] of Object.entries(configuredTeam.limits)) {
      if (value !== null && typeof value !== 'object') {
        const labels = {max_experts: 'Drafts per answer', max_parallel: 'Concurrent calls', max_cached_models: 'Models retained', max_calls: 'Call limit', round_timeout_seconds: 'Time budget (seconds)', deadline_semantics: 'Deadline behavior', model_loading: 'Model loading'};
        const descriptions = {soft_between_calls: 'Checked between model calls', lazy_configured_roster_only: 'Configured models load when needed'};
        limits.append(element('dt', '', labels[key] || key.replaceAll('_', ' ')), element('dd', '', descriptions[value] || displayValue(value)));
      }
    }
    $('team-overview').append(limits);
  }
  if (knowledgeStatus) $('team-overview').append(element('p', 'catalog-note', `${number(knowledgeStatus.documents)} locally imported documents from ${number(knowledgeStatus.total_sources)} sources are available for retrieval.`));
  $('team-overview').append(element('p', 'catalog-note', 'Server configuration selects the active team. Browsing a model or dataset does not download, execute, train on, or add it to the team.'));
}
async function loadTeam() {
  try { configuredTeam = await api('/api/team'); }
  catch (_) { configuredTeam = null; }
  try { knowledgeStatus = await api('/api/knowledge'); }
  catch (_) { knowledgeStatus = null; }
  renderTeam();
}
function renderDeliberation(turn) {
  let trace = turn.deliberation;
  if (typeof trace === 'string') { try { trace = JSON.parse(trace); } catch (_) { return null; } }
  if (!trace || trace.mode !== 'ensemble') return null;
  const details = element('details', 'deliberation');
  const members = trace.members || [];
  const successful = members.filter(member => member.status === 'ok').length;
  details.append(element('summary', '', `Model calls · ${successful}/${members.length} completed${trace.degraded ? ' · partial team' : ''}`));
  const list = element('ul');
  for (const member of members) {
    const label = member.status === 'ok' ? 'Contributed' : member.status === 'skipped' ? 'Skipped' : 'Unavailable';
    const stage = ({draft: 'Draft', cross_review: 'Cross-review', synthesis: 'Synthesis'})[member.stage] || displayValue(member.stage, 'Contribution');
    const timing = Number.isFinite(member.latency_ms) ? ` · ${(member.latency_ms / 1000).toFixed(1)}s` : '';
    const item = element('li');
    item.append(element('strong', '', member.name || member.id || member.model || 'Contributor'));
    item.append(element('span', '', `${member.model || ''} · ${stage} · ${label}${timing}`));
    list.append(item);
  }
  details.append(list);
  if (trace.response_mode === 'fast') {
    details.append(element('p', '', 'Fast mode answers with the first successful routed contributor. Full review and synthesis were intentionally skipped.'));
  } else if (trace.synthesizer?.status === 'ok' && trace.answer_stage !== 'draft_fallback') {
    details.append(element('p', '', `Combined by ${trace.synthesizer.name || trace.synthesizer.model || trace.synthesizer.id || 'configured synthesizer'}.`));
  } else {
    const fallbackId = trace.fallback_member || trace.answer_member;
    const fallback = members.find(member => member.id === fallbackId);
    const fallbackName = fallback?.name || fallback?.model || displayValue(fallbackId, 'an available contributor');
    details.append(element('p', '', `Synthesis unavailable; using draft from ${fallbackName}.`));
  }
  details.append(element('p', 'catalog-note', 'Contributor agreement is not proof of accuracy. Verify important claims.'));
  return details;
}
function renderSources(turn) {
  let sources = turn.sources;
  if (typeof sources === 'string') { try { sources = JSON.parse(sources); } catch (_) { return null; } }
  if (!Array.isArray(sources) || !sources.length) return null;
  const details = element('details', 'retrieval-sources');
  details.append(element('summary', '', `Retrieved context · ${sources.length} source${sources.length === 1 ? '' : 's'}`));
  const list = element('ul');
  for (const source of sources) {
    const item = element('li');
    const link = element('a', '', source.source_id || source.id || 'Imported document');
    try {
      const url = new URL(source.url);
      if (url.protocol === 'https:' || url.protocol === 'http:') { link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; }
    } catch (_) { /* Preserve source text without linking unsupported URLs. */ }
    item.append(link);
    if (source.excerpt) item.append(element('blockquote', '', source.excerpt));
    list.append(item);
  }
  details.append(list, element('p', 'catalog-note', 'Retrieved passages provide context; they do not by themselves verify the answer.'));
  return details;
}
function addMessage(role, text, turn = null) {
  $('welcome')?.remove();
  const article = element('article', `message ${role}`);
  article.append(element('div', 'who', role === 'user' ? 'YOU' : 'ZENITH'));
  article.append(role === 'assistant' ? renderMarkdown(text) : element('pre', 'content', text));
  if (turn) {
    const performance = turn.performance;
    if (performance) {
      const usage = performance.usage || {}; const pieces = [];
      if (usage.output_tokens !== undefined && usage.output_tokens !== null) pieces.push(`${number(usage.output_tokens)} output tokens`);
      if (usage.input_tokens !== undefined && usage.input_tokens !== null) pieces.push(`${number(usage.input_tokens)} input tokens`);
      if (performance.first_text_ms !== undefined && performance.first_text_ms !== null) pieces.push(`${(performance.first_text_ms / 1000).toFixed(2)}s to first text`);
      if (usage.model_calls === 0) pieces.push('Built-in check · model not called');
      if (!pieces.length) pieces.push('Token counts not supplied by this provider');
      article.append(element('p', 'usage-note', pieces.join(' · ')));
      if (usage.finish_reason === 'length') {
        const next = element('button', 'human-review-button', 'Output cap reached · continue with Full'); next.type = 'button';
        next.addEventListener('click', () => {$('reply-style').value = 'full'; $('prompt').value = 'Continue your previous answer from where it stopped, without repeating earlier text.'; $('prompt').focus();});
        article.append(next);
      }
    }
    if (turn.quality) {
      const q = turn.quality;
      const label = q.verification === 'deterministic' ? 'Verified arithmetic' : q.abstained ? 'Evidence unavailable · abstained' : q.calibration === 'validation-method-group' ? 'Model answer · validation group estimate; individual confidence unknown' : 'Model answer · confidence not calibrated';
      const note = element('p', 'quality-note', label + (turn.latency_ms !== undefined ? ` · ${(turn.latency_ms / 1000).toFixed(2)}s` : '') + (q.needs_human_review ? ' · human review recommended' : ''));
      article.append(note);
    }
    if (activeUser) {
      const handoff = element('button', 'human-review-button', 'Request human review'); handoff.type = 'button';
      handoff.addEventListener('click', async () => {
        if (!confirm('Share this question and answer with the local server administrator for review? No external notification is sent.')) return;
        try {await api('/api/review-requests', {method: 'POST', body: JSON.stringify({session_id: session, turn_id: turn.id})}); handoff.textContent = 'Queued for administrator review'; handoff.disabled = true;}
        catch (error) {showError(error.message);}
      }); article.append(handoff);
    }
    const deliberation = renderDeliberation(turn);
    if (deliberation) article.append(deliberation);
    const sources = renderSources(turn);
    if (sources) article.append(sources);
    const details = element('details', 'review');
    const summary = element('summary', '', turn.approved ? 'Approved for training · edit review' : turn.rating ? 'Review saved · edit review' : 'Review this answer');
    const select = element('select');
    select.setAttribute('aria-label', 'Answer rating');
    for (const [value, label] of [['good', 'Good answer'], ['bad', 'Needs improvement']]) {
      const option = element('option', '', label); option.value = value; select.append(option);
    }
    select.value = turn.rating || 'good';
    const correction = element('textarea');
    correction.placeholder = 'Optional: write a corrected answer for training';
    correction.setAttribute('aria-label', 'Corrected answer');
    correction.rows = 3; correction.maxLength = 24000; correction.value = turn.correction || '';
    const approve = element('input'); approve.type = 'checkbox'; approve.checked = !!turn.approved;
    const label = element('label'); label.append(approve, document.createTextNode('Approve this answer and its context for training'));
    const save = element('button', '', 'Save review'); save.type = 'button';
    const saved = element('span', 'saved'); saved.setAttribute('role', 'status');
    save.addEventListener('click', async () => {
      save.disabled = true; saved.textContent = '';
      try {
        await api('/api/feedback', {method: 'POST', body: JSON.stringify({session_id: session, turn_id: turn.id, rating: select.value, approved: approve.checked, correction: correction.value || null})});
        saved.textContent = 'Saved'; summary.textContent = approve.checked ? 'Approved for training · edit review' : 'Review saved · edit review';
        showError('');
      } catch (error) { showError(error.message); }
      finally { save.disabled = false; }
    });
    const row = element('div', 'actions'); row.append(select, label);
    const controls = element('div', 'actions'); controls.append(save, saved);
    details.append(summary, row, correction, controls); article.append(details);
  }
  $('messages').append(article);
  $('messages').scrollTop = $('messages').scrollHeight;
  return article;
}
async function loadHistory() {
  const data = await api(`/api/history/${session}`);
  if (data.turns.length) {
    $('messages').replaceChildren();
    for (const turn of data.turns) { addMessage('user', turn.prompt); addMessage('assistant', turn.response, turn); }
  }
}
function renderCatalogCounts() {
  $('catalog-stats').replaceChildren();
  $('catalog-count').textContent = 'Hugging Face · GitHub';
}
function renderCatalogEntry(entry) {
  const article = element('article', 'catalog-entry');
  const heading = element('div', 'catalog-entry-heading');
  const link = element('a', '', entry.name || entry.id);
  try {
    const url = new URL(entry.url);
    if (url.protocol === 'https:' || url.protocol === 'http:') { link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; }
  } catch (_) { /* An invalid source URL remains unlinked text. */ }
  heading.append(link, element('span', 'source-tag', sourceName(entry.source)));
  article.append(heading);
  if (entry.id && entry.id !== entry.name) article.append(element('p', 'catalog-id', entry.id));
  const description = displayValue(entry.description, 'No description provided by the source.');
  article.append(element('p', 'catalog-description', description));
  const status = entry.kind === 'dataset' ? 'Dataset source · not ingested' : isConfigured(entry) ? 'Configured for chat' : 'Catalog reference';
  const meta = element('div', 'catalog-entry-meta');
  meta.append(element('span', isConfigured(entry) ? 'runtime-tag active' : 'runtime-tag', status));
  meta.append(element('span', '', displayValue(entry.task, entry.kind === 'dataset' ? 'Dataset' : 'Task not recorded')));
  meta.append(element('span', '', `License: ${displayValue(entry.license, 'Unknown — review source')}`));
  if (entry.stars !== undefined) meta.append(element('span', '', `${number(entry.stars)} stars`));
  if (entry.downloads !== undefined) meta.append(element('span', '', `${number(entry.downloads)} downloads`));
  if (entry.likes !== undefined) meta.append(element('span', '', `${number(entry.likes)} likes`));
  if (entry.popularity_rank !== undefined) meta.append(element('span', '', `Source rank #${number(entry.popularity_rank)}`));
  if (entry.fine_tuned) meta.append(element('span', 'runtime-tag', 'Fine-tuned model'));
  if (entry.base_models?.length) article.append(element('p', 'catalog-note', 'Base: ' + entry.base_models.join(', ')));
  if (entry.gated) meta.append(element('span', '', 'Source access approval required'));
  article.append(meta);
  return article;
}
async function loadCatalog() {
  const request = ++catalogRequest;
  $('catalog-results').setAttribute('aria-busy', 'true');
  $('catalog-results-label').textContent = 'Loading sourced catalog records…';
  $('catalog-error').hidden = true;
  $('catalog-previous').disabled = true; $('catalog-next').disabled = true;
  const params = new URLSearchParams({kind: $('catalog-kind').value, q: $('catalog-query').value.trim(), page: String(catalogPage), page_size: '20'});
  if ($('catalog-source').value) params.set('source', $('catalog-source').value);
  try {
    const online = $('catalog-scope').value === 'online';
    if (online && !$('catalog-source').value) params.set('source', 'huggingface');
    if (online && discoveryCursors[catalogPage - 1]) params.set('cursor', discoveryCursors[catalogPage - 1]);
    const data = await api(`/api/${online ? 'discovery' : 'catalog'}?${params}`);
    if (request !== catalogRequest) return;
    catalogLoaded = true;
    renderCatalogCounts(data.counts);
    $('catalog-results').replaceChildren();
    for (const entry of data.entries || []) $('catalog-results').append(renderCatalogEntry(entry));
    const total = Number(data.total) || 0;
    const pageSize = Number(data.page_size) || 20;
    catalogPage = Number(data.page) || catalogPage;
    const pages = Math.max(1, Math.ceil(total / pageSize));
    $('catalog-results-label').textContent = online ? data.notice : 'Local model and dataset references, including your saved imports.';
    $('catalog-page').textContent = `Page ${catalogPage}`;
    $('catalog-previous').disabled = catalogPage <= 1;
    $('catalog-next').disabled = online ? !data.has_more : catalogPage >= pages;
    if (online) discoveryCursors[catalogPage] = data.next_cursor || '';
    if (!data.entries?.length) $('catalog-results').append(element('p', 'catalog-empty', 'No matching sources. Try a broader search or another filter.'));
    const generated = typeof data.generated_at === 'string' ? new Date(data.generated_at) : null;
    $('catalog-generated').textContent = online ? 'Live public source metadata' : generated && !Number.isNaN(generated.valueOf()) ? `Snapshot: ${generated.toLocaleDateString()}` : 'Sourced metadata snapshot';
  } catch (error) {
    if (request !== catalogRequest) return;
    $('catalog-error').textContent = error.message;
    $('catalog-error').hidden = false;
    $('catalog-results-label').textContent = 'Catalog unavailable. Check access and retry.';
  } finally {
    if (request === catalogRequest) $('catalog-results').setAttribute('aria-busy', 'false');
  }
}
function selectCatalogTab(view) {
  const resources = view !== 'team';
  $('catalog-resources').hidden = !resources; $('catalog-team').hidden = resources;
  for (const [id, selected] of [['catalog-resources-tab', resources], ['catalog-team-tab', !resources]]) {
    $(id).setAttribute('aria-selected', String(selected)); $(id).tabIndex = selected ? 0 : -1;
  }
}
function openCatalog(view = 'resources') {
  selectCatalogTab(view);
  if (!$('catalog-dialog').open) $('catalog-dialog').showModal();
  if (view === 'resources' && !catalogLoaded) loadCatalog();
  if (view === 'team') loadTeam();
}
async function connect() {
  showError('');
  try {
    const health = await api('/healthz');
    $('model').textContent = health.display_name || 'Zenith';
    $('provider').textContent = health.provider === 'huggingface' ? 'Hugging Face · local inference' : health.provider === 'tiny' ? 'Zenith Tiny · experimental' : health.provider === 'ensemble' ? 'Model team · combined answers' : health.provider === 'localserver' ? 'Local model server · no API key' : 'Ollama · local inference';
    $('status').textContent = health.provider === 'localserver' ? '● Local runtime · check with doctor' : health.model_loaded ? '● Model loaded' : '● Ready · loads on first message';
    if (health.counts) renderCatalogCounts(health.counts);
    if (health.authentication_required && !sessionStorage.getItem('zenith_token')) {
      $('access').open = true; $('status').textContent = 'Access token required'; return;
    }
    await loadAccount();
    await Promise.all([loadHistory(), loadTeam(), loadConversations(), loadAdmin()]);
    $('access').open = false;
    catalogLoaded = false;
  } catch (error) { showError(error.message); $('status').textContent = 'Connection needs attention'; }
}
$('connect').addEventListener('click', () => {sessionStorage.setItem('zenith_token', $('token').value.trim()); connect();});
$('new-chat').addEventListener('click', () => {
  if (busy) return;
  switchConversation(crypto.randomUUID());
});
$('open-catalog').addEventListener('click', () => openCatalog());
$('open-team').addEventListener('click', () => openCatalog('team'));
$('close-catalog').addEventListener('click', () => $('catalog-dialog').close());
$('catalog-resources-tab').addEventListener('click', () => {selectCatalogTab('resources'); if (!catalogLoaded) loadCatalog();});
$('catalog-team-tab').addEventListener('click', () => {selectCatalogTab('team'); loadTeam();});
document.querySelector('.catalog-tabs').addEventListener('keydown', event => {
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault();
    const team = $('catalog-team-tab').getAttribute('aria-selected') !== 'true';
    const target = team ? $('catalog-team-tab') : $('catalog-resources-tab');
    target.click(); target.focus();
  }
});
$('catalog-filters').addEventListener('submit', event => {event.preventDefault(); catalogPage = 1; discoveryCursors = ['']; loadCatalog();});
for (const id of ['catalog-kind', 'catalog-source', 'catalog-scope']) $(id).addEventListener('change', () => {
  const online = $('catalog-scope').value === 'online';
  $('catalog-source').options[0].disabled = online;
  if (online && !$('catalog-source').value) $('catalog-source').value = 'huggingface';
  catalogPage = 1; discoveryCursors = ['']; loadCatalog();
});
$('catalog-previous').addEventListener('click', () => {if (catalogPage > 1) {catalogPage -= 1; loadCatalog();}});
$('catalog-next').addEventListener('click', () => {catalogPage += 1; loadCatalog();});
$('delete-chat').addEventListener('click', async () => {
  if (busy || !confirm('Delete this conversation and its training approvals from this server? Already exported datasets are separate files.')) return;
  try {await api(`/api/history/${session}`, {method: 'DELETE'}); $('new-chat').click();}
  catch (error) {showError(error.message);}
});
$('messages').addEventListener('click', event => {const button = event.target.closest('[data-prompt]'); if (button) {$('prompt').value = button.dataset.prompt; $('prompt').focus();}});
$('prompt').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {event.preventDefault(); $('composer').requestSubmit();}
});
$('composer').addEventListener('submit', async event => {
  event.preventDefault();
  const text = $('prompt').value.trim();
  if (busy || !text) return;
  if (/^\/skills?(?:\s|$)/i.test(text)) {
    $('prompt').value = '';
    try {await runSkillCommand(text);} catch (error) {showError(error.message);}
    return;
  }
  if (/^\/admin(?:\s|$)/i.test(text)) {
    $('prompt').value = '';
    try {
      if (text.toLowerCase() === '/admin lock') {
        await api('/api/admin/lock', {method: 'POST'}); await loadAdmin();
      } else if (text.toLowerCase() === '/admin unlock') {
        if (!activeUser) {openAccount(); return;}
        await loadAdmin(); $('admin-dialog').showModal();
      } else showError('Use /admin unlock or /admin lock. Enter your private code only in the masked Admin field.');
    } catch (error) {showError(error.message);}
    return;
  }
  if (/^zenith-admin-[A-Za-z0-9_-]{43}$/.test(text)) {
    $('prompt').value = '';
    if (!activeUser) {showError('Sign in as your owner account before unlocking Admin. The code was not saved.'); return;}
    try {await unlockAdmin(text); $('admin-dialog').showModal();} catch (error) {showError(error.message);}
    return;
  }
  if (!skillStateReady) {showError('Reconnect to confirm the active skill before sending a message.'); return;}
  busy = true; chatController = new AbortController(); showError(''); $('send').hidden = true; $('stop').hidden = false; $('send').disabled = true; $('new-chat').disabled = true; $('prompt').disabled = true;
  $('messages').setAttribute('aria-busy', 'true');
  const userMessage = addMessage('user', text);
  let partial = null; let buffer = '';
  const pending = element('p', 'pending', configuredTeam?.mode === 'ensemble' && $('response-mode').value === 'thorough' ? 'Consulting the configured model team… Contributors respond before the final synthesis.' : 'Preparing your answer… The first model load may take longer.');
  $('messages').append(pending); $('messages').scrollTop = $('messages').scrollHeight;
  try {
    const result = await streamChat({session_id: session, message: text, response_mode: $('response-mode').value, reply_style: $('reply-style').value}, chunk => {
      buffer += chunk; pending.remove();
      if (!partial) partial = addMessage('assistant', '');
      partial.querySelector('.content').replaceWith(renderMarkdown(buffer));
      $('messages').scrollTop = $('messages').scrollHeight;
    }, chatController.signal);
    pending.remove(); partial?.remove(); addMessage('assistant', result.response, result); $('prompt').value = ''; $('status').textContent = '● Connected'; loadConversations();
  } catch (error) {
    pending.remove(); partial?.remove(); userMessage.remove(); showError(error.name === 'AbortError' ? 'Stopped. Incomplete replies are discarded; completed replies remain in history.' : error.message);
  } finally {
    busy = false; chatController = null; $('send').hidden = false; $('stop').hidden = true; $('send').disabled = false; $('new-chat').disabled = false; $('prompt').disabled = false;
    $('messages').setAttribute('aria-busy', 'false'); $('prompt').focus();
  }
});
$('stop').addEventListener('click', () => chatController?.abort());

// Markdown is built with text nodes; model output never enters innerHTML.
function inlineText(parent, text) {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g;
  let previous = 0;
  for (const match of text.matchAll(pattern)) {
    parent.append(document.createTextNode(text.slice(previous, match.index)));
    const value = match[0];
    if (value.startsWith('`')) parent.append(element('code', '', value.slice(1, -1)));
    else if (value.startsWith('**')) parent.append(element('strong', '', value.slice(2, -2)));
    else {
      const cut = value.indexOf('](');
      const link = element('a', '', value.slice(1, cut));
      try {
        const url = new URL(value.slice(cut + 2, -1));
        link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; parent.append(link);
      } catch (_) {parent.append(document.createTextNode(value));}
    }
    previous = match.index + value.length;
  }
  parent.append(document.createTextNode(text.slice(previous)));
}
function renderMarkdown(text) {
  const root = element('div', 'content');
  const lines = text.split('\n');
  for (let i = 0; i < lines.length;) {
    const line = lines[i];
    if (line.startsWith('```')) {
      const language = line.slice(3).trim().slice(0, 30) || 'code';
      const code = [];
      for (i += 1; i < lines.length && !lines[i].startsWith('```'); i++) code.push(lines[i]);
      i += 1;
      const block = element('div', 'code-block'); const toolbar = element('div', 'code-toolbar');
      const copy = element('button', '', 'Copy'); copy.type = 'button';
      copy.addEventListener('click', async () => {try {await navigator.clipboard.writeText(code.join('\n')); copy.textContent = 'Copied';} catch (_) {copy.textContent = 'Select code to copy';}});
      toolbar.append(element('span', '', language), copy);
      const pre = element('pre'); pre.append(element('code', '', code.join('\n'))); block.append(toolbar, pre); root.append(block); continue;
    }
    if (!line.trim()) {i++; continue;}
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {const node = element(heading[1].length < 3 ? 'h3' : 'h4'); inlineText(node, heading[2]); root.append(node); i++; continue;}
    if (/^\s*[-*]\s+/.test(line)) {
      const list = element('ul');
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {const item = element('li'); inlineText(item, lines[i].replace(/^\s*[-*]\s+/, '')); list.append(item); i++;}
      root.append(list); continue;
    }
    const paragraph = element('p'); inlineText(paragraph, line); root.append(paragraph); i++;
  }
  return root;
}
function showWelcome() { $('messages').replaceChildren(welcomeTemplate.cloneNode(true)); }
function rememberConversation() {
  sessionStorage.setItem('zenith_session', session);
  if (activeUser) localStorage.setItem('zenith_last_' + activeUser.id, session);
}
async function switchConversation(identifier) {
  if (busy) return;
  skillStateReady = false;
  session = identifier; rememberConversation(); showWelcome(); showError('');
  try {await Promise.all([loadHistory(), loadConversations(), loadSkills()]);} catch (error) {showError(error.message);}
}
async function loadAccount() {
  const data = await api('/api/account');
  const previous = activeUser?.id;
  activeUser = data.user;
  if (previous !== activeUser?.id) {
    savedPreferences = {}; preferenceLoadRequest += 1;
    analysisRequest += 1; importedSkillRequest += 1;
    $('imported-skill-results')?.replaceChildren(); $('skills-results').replaceChildren(); $('skills-taxonomy').replaceChildren();
    $('analysis-csv').value = ''; $('analysis-result').replaceChildren(); $('analysis-status').textContent = '';
    $('analysis-submit').disabled = false;
    skillLoadRequest += 1; skillLibrary = null; skillStateReady = false;
    $('skill-select').replaceChildren(new Option('General reasoning', 'general'));
    $('skill-command-status').textContent = 'Active skill: General reasoning';
    adminState = null; renderAdmin(); $('admin-code').value = ''; $('admin-tool-text').value = ''; $('admin-tool-result').textContent = '';
    $('admin-review-list').replaceChildren(); $('my-review-list').replaceChildren(); $('admin-error').textContent = '';
    $('performance-summary').replaceChildren(); $('performance-scope').textContent = ''; $('performance-note').textContent = ''; $('server-metrics').hidden = true;
    $('system-components').replaceChildren(); showingServerMetrics = false;
    $('memory-list').replaceChildren(); $('memory-content').value = ''; $('conversation-summary').textContent='';
    $('memory-count').textContent = 'Your saved context'; $('memory-error').textContent = '';
  }
  $('greeting').textContent = data.greeting;
  $('open-account').textContent = activeUser ? activeUser.display_name : 'Sign in';
  $('account-name').textContent = activeUser ? 'Signed in as ' + activeUser.display_name + ' (@' + activeUser.username + ')' : '';
  $('signed-in-panel').hidden = !activeUser; $('account-form').hidden = !!activeUser;
  if (activeUser && previous !== activeUser.id) {
    const saved = localStorage.getItem('zenith_last_' + activeUser.id);
    session = saved && /^[0-9a-f-]{36}$/i.test(saved) ? saved : crypto.randomUUID();
    rememberConversation(); showWelcome();
  } else if (!activeUser && previous) {session = crypto.randomUUID(); rememberConversation(); showWelcome();}
  if (activeUser) await loadPreferenceControls();
}
async function loadConversations() {
  const list = $('conversation-list'); list.replaceChildren();
  if (!activeUser) {list.append(element('p', '', 'Sign in to keep your conversations together.')); return;}
  try {
    const data = await api('/api/conversations');
    for (const item of data.conversations) {
      const button = element('button', '', item.title); button.type = 'button'; button.title = item.title;
      button.setAttribute('aria-current', item.session_id === session ? 'true' : 'false');
      button.addEventListener('click', () => switchConversation(item.session_id)); list.append(button);
    }
    if (!data.conversations.length) list.append(element('p', '', 'Your next conversation starts here.'));
  } catch (error) {showError(error.message);}
}
function openAccount() { if (busy) return; $('account-error').textContent = ''; $('account-dialog').showModal(); }
$('open-account').addEventListener('click', openAccount);
for (const button of document.querySelectorAll('[data-close]')) button.addEventListener('click', () => $(button.dataset.close).close());
function setRegistration(value) {
  registering = value; $('register-fields').hidden = !registering;
  $('display-name').required = registering; $('password').minLength = registering ? 12 : 1;
  $('password').autocomplete = registering ? 'new-password' : 'current-password';
  $('account-submit').textContent = registering ? 'Create account' : 'Sign in';
  $('toggle-register').textContent = registering ? 'I already have an account' : 'Create an account';
}
$('toggle-register').addEventListener('click', () => setRegistration(!registering));
$('account-form').addEventListener('submit', async event => {
  event.preventDefault(); $('account-submit').disabled = true; $('account-error').textContent = '';
  try {
    await api('/api/account/' + (registering ? 'register' : 'login'), {method: 'POST', body: JSON.stringify({username: $('username').value, password: $('password').value, ...(registering ? {display_name: $('display-name').value} : {})})});
    $('password').value = ''; setRegistration(false); $('account-dialog').close(); await connect();
  } catch (error) {$('account-error').textContent = error.message;}
  finally {$('account-submit').disabled = false;}
});
$('logout').addEventListener('click', async () => {
  if (busy) return;
  try {await api('/api/account/logout', {method: 'POST'}); $('account-dialog').close(); await connect();}
  catch (error) {$('account-error').textContent = error.message;}
});
async function loadMemories() {
  const data = await api('/api/memories'); const list = $('memory-list'); list.replaceChildren();
  $('memory-count').textContent = data.memories.length + ' saved notes';
  for (const note of data.memories) {
    const item = element('article', 'memory-note'); const remove = element('button', '', 'Forget'); remove.type = 'button';
    remove.addEventListener('click', async () => {try {await api('/api/memories/' + note.id, {method: 'DELETE'}); await loadMemories();} catch (error) {$('memory-error').textContent = error.message;}});
    item.append(element('p', '', note.content), remove); list.append(item);
  }
  if (!data.memories.length) list.append(element('p', 'dialog-description', 'No saved memories yet. You choose what stays.'));
  const owner=activeUser?.id, conversation=session;
  const summary=await api(`/api/conversations/${conversation}/summary`);
  if (activeUser?.id===owner && session===conversation) $('conversation-summary').textContent=summary.summary?.summary || '';
}
$('open-memory').addEventListener('click', async () => {
  if (!activeUser) {openAccount(); return;}
  $('memory-dialog').showModal(); $('memory-error').textContent = '';
  try {await loadMemories();} catch (error) {$('memory-error').textContent = error.message;}
});
$('memory-form').addEventListener('submit', async event => {
  event.preventDefault(); $('memory-error').textContent = '';
  const button = event.currentTarget.querySelector('button'); button.disabled = true;
  try {await api('/api/memories', {method: 'POST', body: JSON.stringify({content: $('memory-content').value})}); $('memory-content').value = ''; await loadMemories();}
  catch (error) {$('memory-error').textContent = error.message;} finally {button.disabled = false;}
});
$('forget-all').addEventListener('click', async () => {
  if (!confirm('Forget all your saved memories? Existing chats and exported files are separate.')) return;
  try {await api('/api/memories', {method: 'DELETE'}); await loadMemories();} catch (error) {$('memory-error').textContent = error.message;}
});
$('open-packs').addEventListener('click', async () => {
  $('packs-dialog').showModal(); const list = $('pack-list'); list.replaceChildren();
  try {
    const data = await api('/api/model-packs');
    for (const pack of data.packs) {
      const card = element('article', 'pack-card');
      card.append(element('h3', '', pack.name), element('p', '', pack.runtime_requirements));
      card.append(element('p', '', `${pack.file_count} inventoried files · ${(pack.total_bytes / 2**30).toFixed(1)} GiB for every variant · ${pack.license}`));
      card.append(element('pre', '', 'zenith packs files ' + pack.id + '\nzenith packs download ' + pack.id + (pack.recommended_file ? '' : ' --all')));
      const source = element('a', '', 'Source and attribution'); source.href = pack.source_url; source.target = '_blank'; source.rel = 'noopener noreferrer';
      card.append(source, element('small', '', 'Pinned integration; this model has not been benchmarked in Zenith. Full variants need substantial disk space.')); list.append(card);
    }
  } catch (error) {list.append(element('p', '', error.message));}
});

async function loadSkills() {
  const request = ++skillLoadRequest; const activeSession = session;
  skillStateReady = false;
  try {
    const [data, current] = await Promise.all([api('/api/skills'), api('/api/skills/current?session_id=' + encodeURIComponent(activeSession))]);
    if (request !== skillLoadRequest || activeSession !== session) return;
    skillStateReady = true;
    $('skill-select').replaceChildren();
    skillLibrary = data;
    for (const category of data.categories) {
      const group = element('optgroup'); group.label = category.name;
      for (const skill of data.skills.filter(item => item.category === category.id)) {
        const option = element('option', '', skill.name); option.value = skill.id; group.append(option);
      }
      $('skill-select').append(group);
    }
    if (!data.skills.some(skill => skill.id === current.skill) && current.skill !== 'general') {
      const profile = await api('/api/skills/profile/' + encodeURIComponent(current.skill));
      if (request !== skillLoadRequest || activeSession !== session) return;
      $('skill-select').append(new Option(profile.name, profile.id));
    }
    $('skill-select').value = current.skill;
    $('skill-command-status').textContent = current.message;
    $('skills-category').replaceChildren(new Option('All available skills', ''));
    for (const category of data.categories) $('skills-category').append(new Option(category.name, category.id));
    $('skills-access-note').textContent = data.security_unlocked ? 'Owner unlocked. Security skills require explicit activation and expire with this admin login.' : 'Security skills are locked. Only the configured owner can unlock Admin and activate them.';
    document.querySelector('.skills-taxonomy').hidden = !data.security_unlocked;
    $('response-mode').value = localStorage.getItem(responseKey('zenith_response_mode')) || data.default_response_mode || 'fast';
    $('reply-style').value = localStorage.getItem(responseKey('zenith_reply_style')) || savedPreferences.reply_style || data.default_reply_style || 'auto';
    if ($('skills-dialog').open) renderSkillLibrary();
  } catch (_) {
    if (request === skillLoadRequest) {
      skillLibrary = null; $('skill-select').replaceChildren(new Option('General reasoning', 'general'));
      $('skill-command-status').textContent = 'Skill state unavailable. Reconnect before changing skills.';
    }
  }
}

async function runSkillCommand(command) {
  if (busy) throw new Error('Wait for the current answer before changing skills.');
  showError('');
  const result = await api('/api/skills/command', {method: 'POST', body: JSON.stringify({session_id: session, command})});
  await loadSkills();
  $('skill-command-status').textContent = result.message;
  if (result.type === 'skill-list') {$('skills-dialog').showModal(); renderSkillLibrary();}
  return result;
}
$('skill-select').addEventListener('change', async () => {
  try {await runSkillCommand('/skill ' + $('skill-select').value);}
  catch (error) {showError(error.message); await loadSkills();}
});

function renderSkillLibrary() {
  const results = $('skills-results'); results.replaceChildren();
  const taxonomy = $('skills-taxonomy'); taxonomy.replaceChildren();
  if (!skillLibrary) return;
  const query = $('skills-query').value.trim().toLocaleLowerCase();
  const category = $('skills-category').value;
  const skills = skillLibrary.skills.filter(skill => (!category || skill.category === category) &&
    `${skill.id} ${skill.name} ${skill.instruction} ${skill.deliverable}`.toLocaleLowerCase().includes(query));
  $('skills-count').textContent = `${skills.length} matching profiles · ${skillLibrary.skills.length} profiles and ${skillLibrary.resources.length} references in this library`;
  for (const skill of skills) {
    const card = element('article', 'skill-card'); card.dataset.skill = skill.id;
    card.append(element('span', 'eyebrow', skillLibrary.categories.find(item => item.id === skill.category)?.name || skill.category));
    card.append(element('h3', '', skill.name), element('p', '', skill.deliverable));
    const choose = element('button', '', 'Use ' + skill.name); choose.type = 'button';
    choose.addEventListener('click', async () => {
      try {await runSkillCommand('/skill ' + skill.id); $('skills-dialog').close(); $('prompt').focus();}
      catch (error) {$('skills-error').textContent = error.message;}
    });
    card.append(choose, element('p', 'skill-command-hint', '/skill ' + skill.id));
    const details = element('details'); details.append(element('summary', '', 'Workflow, checks, and resources'));
    for (const [label, rows] of [['Workflow', skill.workflow], ['Review checklist', skill.checklist]]) {
      details.append(element('h4', '', label)); const list = element('ol');
      for (const text of rows) list.append(element('li', '', text)); details.append(list);
    }
    details.append(element('h4', '', 'Practice'), element('p', '', skill.practice), element('h4', '', 'Learning references'));
    const resources = element('ul', 'skill-references');
    for (const reference of skillLibrary.resources.filter(item => skill.resource_ids.includes(item.id))) {
      try {
        const url = new URL(reference.url); if (url.protocol !== 'https:' || url.username || url.password) continue;
        const item = element('li'); const link = element('a', '', reference.title); link.href = url.href;
        link.target = '_blank'; link.rel = 'noopener noreferrer';
        item.append(link, element('small', '', `${reference.publisher} · ${reference.verification.status === 'retrieved' ? 'retrieved' : 'retrieval unconfirmed'} ${reference.verification.checked_on}`));
        resources.append(item);
      } catch (_) { /* A malformed external link must not affect the rest of the library. */ }
    }
    details.append(resources); card.append(details); results.append(card);
  }
  if (!skills.length) results.append(element('p', 'dialog-description', 'No matching profiles. Try a broader subject or clear the search.'));
  for (const item of skillLibrary.taxonomy) {
    const row = element('section', 'skill-taxonomy-row');
    row.append(element('h3', '', item.name), element('p', '', item.meaning), element('p', '', item.professional_alternative));
    taxonomy.append(row);
  }
  importedSkillRequest += 1; clearTimeout(importedSkillTimer);
  importedSkillTimer = setTimeout(() => loadImportedSkills(true), 150);
}
$('open-skills').addEventListener('click', async () => {
  $('skills-dialog').showModal(); $('skills-error').textContent = '';
  if (!skillLibrary) await loadSkills();
  if (!skillLibrary) {$('skills-error').textContent = 'Connect to the server to load the skill library.'; return;}
  renderSkillLibrary();
});
$('skills-filters').addEventListener('submit', event => {event.preventDefault(); renderSkillLibrary();});
$('skills-query').addEventListener('input', renderSkillLibrary);
$('skills-category').addEventListener('change', renderSkillLibrary);
$('response-mode').addEventListener('change', () => localStorage.setItem(responseKey('zenith_response_mode'), $('response-mode').value));
$('reply-style').addEventListener('change', () => localStorage.setItem(responseKey('zenith_reply_style'), $('reply-style').value));
function renderAdmin() {
  const elevated = !!adminState?.elevated;
  $('server-metrics').hidden = !elevated;
  if (!elevated && showingServerMetrics) {$('performance-summary').replaceChildren(); $('performance-scope').textContent = 'Admin locked. Refresh to view your account totals.'; $('performance-note').textContent = ''; showingServerMetrics = false;}
  $('admin-controls').hidden = !elevated; $('admin-unlock').hidden = elevated;
  $('devil-mode').checked = !!adminState?.devil_mode;
  $('mfa-status').textContent = adminState?.mfa_configured ? 'Authenticator configured. Restricted tools require a current MFA-verified owner session.' : 'Configure an authenticator before activating restricted tools.';
  $('mfa-setup-form').hidden = !!adminState?.mfa_configured;
  if (!elevated || adminState?.mfa_configured) { $('mfa-secret').textContent = ''; $('mfa-enrollment').hidden = true; $('mfa-password').value = ''; $('mfa-confirm-code').value = ''; }
  if (!elevated) { $('admin-otp').value = ''; $('execution-result').textContent = ''; $('execution-log').textContent = ''; $('execution-arguments').value = '{"text":""}'; $('execution-status').textContent = 'Restricted tools locked.'; }
  $('admin-status').textContent = !activeUser ? 'Sign in as your local owner account.' : elevated ? 'Administrator recognized. Access expires after 15 minutes.' : adminState?.eligible ? 'Owner account recognized. Enter your local code to unlock.' : 'This account has not been configured as the owner in the server terminal.';
  document.body.classList.toggle('devil-workspace', elevated && !!adminState?.devil_mode);
  clearTimeout(adminExpiry);
  if (adminState?.expires_at) adminExpiry = setTimeout(() => loadAdmin(), Math.max(1000, adminState.expires_at * 1000 - Date.now() + 300));
}
async function loadAdmin() {
  if (!activeUser) {adminState = null; renderAdmin(); await loadSkills(); return;}
  try {adminState = await api('/api/admin/status');} catch (_) {adminState = null;}
  renderAdmin();
  if (adminState?.elevated) { try { await refreshExecution(); } catch (error) { $('admin-error').textContent = error.message; } }
  await loadSkills();
}
async function unlockAdmin(code, otp = '') {
  adminState = await api('/api/admin/unlock', {method: 'POST', body: JSON.stringify({code,otp})});
  renderAdmin(); $('admin-error').textContent = ''; await refreshExecution(); await loadSkills();
}
$('open-admin').addEventListener('click', async () => {
  if (busy) return;
  if (!activeUser) {openAccount(); return;}
  await loadAdmin(); $('admin-dialog').showModal();
});
$('admin-unlock').addEventListener('submit', async event => {
  event.preventDefault(); const code = $('admin-code').value; $('admin-code').value = '';
  const otp = $('admin-otp').value; $('admin-otp').value = '';
  try {await unlockAdmin(code, otp);} catch (error) {$('admin-error').textContent = error.message;}
});
$('devil-mode').addEventListener('change', async () => {
  try {adminState = await api('/api/admin/mode', {method: 'POST', body: JSON.stringify({enabled: $('devil-mode').checked})}); renderAdmin();}
  catch (error) {$('admin-error').textContent = error.message; await loadAdmin();}
});
$('lock-admin').addEventListener('click', async () => {
  try {await api('/api/admin/lock', {method: 'POST'}); await loadAdmin();} catch (error) {$('admin-error').textContent = error.message;}
});
$('admin-tool-form').addEventListener('submit', async event => {
  event.preventDefault(); $('admin-error').textContent = ''; const button = event.currentTarget.querySelector('button'); button.disabled = true;
  try {const data = await api('/api/admin/tools', {method: 'POST', body: JSON.stringify({tool: $('admin-tool').value, text: $('admin-tool-text').value})}); $('admin-tool-result').textContent = JSON.stringify(data.result, null, 2);}
  catch (error) {$('admin-error').textContent = error.message; await loadAdmin();}
  finally {button.disabled = false;}
});

$('open-my-reviews').addEventListener('click', async () => {
  $('account-dialog').close(); $('human-review-dialog').showModal(); const list = $('my-review-list'); list.replaceChildren();
  try {const data = await api('/api/review-requests');
    for (const item of data.requests) {const card = element('article', 'memory-note'); card.append(element('strong', '', item.status === 'closed' ? 'Reviewed' : 'Waiting for administrator'), element('p', '', item.prompt), element('p', '', item.resolution || 'No response yet.')); list.append(card);}
    if (!data.requests.length) list.append(element('p', 'dialog-description', 'No human-review requests yet.'));
  } catch (error) {list.append(element('p', '', error.message));}
});
$('refresh-admin-reviews').addEventListener('click', async () => {
  const list = $('admin-review-list'); list.replaceChildren();
  try {const data = await api('/api/admin/reviews');
    for (const item of data.requests) {
      const card = element('article', 'memory-note'); card.append(element('strong', '', item.status), element('p', '', item.prompt), element('p', '', item.response));
      const reply = element('textarea'); reply.maxLength = 4000; reply.rows = 3; reply.value = item.resolution; reply.setAttribute('aria-label', 'Administrator review response');
      const save = element('button', '', 'Send review response'); save.type = 'button';
      save.addEventListener('click', async () => {try {await api('/api/admin/reviews/' + item.id, {method: 'POST', body: JSON.stringify({resolution: reply.value})}); save.textContent = 'Review saved';} catch (error) {$('admin-error').textContent = error.message;}});
      card.append(reply, save); list.append(card);
    }
    if (!data.requests.length) list.append(element('p', 'dialog-description', 'No review requests.'));
  } catch (error) {$('admin-error').textContent = error.message;}
});

async function streamChat(body, onText, signal) {
  const headers = {'Content-Type': 'application/json', 'Accept': 'text/event-stream'};
  const token = sessionStorage.getItem('zenith_token'); if (token) headers.Authorization = 'Bearer ' + token;
  const response = await fetch('/api/chat/stream', {method: 'POST', headers, body: JSON.stringify(body), signal});
  if (!response.ok) {const data = await response.json(); throw new Error(typeof data.detail === 'string' ? data.detail : 'Chat request was rejected.');}
  if (!response.body) throw new Error('Streaming is unavailable in this browser.');
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let pending = ''; let result = null;
  try {
    for (;;) {
      const item = await reader.read(); pending += decoder.decode(item.value || new Uint8Array(), {stream: !item.done});
      const frames = pending.split('\n\n'); pending = frames.pop();
      for (const frame of frames) {
        if (!frame.startsWith('data: ')) continue;
        const event = JSON.parse(frame.slice(6));
        if (event.type === 'delta') onText(event.text);
        else if (event.type === 'result') result = event.result;
        else if (event.type === 'error') throw new Error(event.message);
      }
      if (item.done) break;
    }
  } finally {try {await reader.cancel();} finally {reader.releaseLock();}}
  if (!result) throw new Error('The answer was interrupted and was not completed. Please retry.');
  return result;
}
async function loadSystem(server = false) {
  $('system-error').textContent = '';
  try {
    const data = await api('/api/system'); const list = $('system-components'); list.replaceChildren();
    for (const component of data.components) {
      const card = element('article', 'system-component'); const heading = element('div', 'catalog-top');
      heading.append(element('h3', '', component.name), element('span', 'source-tag', component.status));
      card.append(heading, element('p', '', component.summary)); const details = element('details'); details.append(element('summary', '', 'Configuration and behavior'));
      const items = element('ul'); for (const line of component.details) items.append(element('li', '', line)); details.append(items); card.append(details); list.append(card);
    }
    $('server-metrics').hidden = !adminState?.elevated;
    if (!activeUser) {$('performance-scope').textContent = 'Sign in to view your private response metrics.'; $('performance-summary').replaceChildren(); $('performance-note').textContent = 'Auto keeps simple fast replies concise. Brief cap: ' + data.limits.brief_max_new_tokens + ' tokens; Full cap: ' + data.limits.max_new_tokens + ' tokens. The cap is a maximum, not measured usage.'; return;}
    const metrics = await api(server ? '/api/admin/metrics' : '/api/metrics'); renderMetrics(metrics);
  } catch (error) {$('system-error').textContent = error.message;}
}
function renderMetrics(data) {
  showingServerMetrics = data.scope === 'server';
  $('performance-summary').replaceChildren();
  const model = data.model_generated;
  const seconds = value => value === null || value === undefined ? '—' : (value / 1000).toFixed(2) + 's';
  for (const [label,value] of [['Completed replies',number(data.completed)],['First text · model median',seconds(model.first_text_p50_ms)],['Full reply · model median',seconds(model.total_p50_ms)],['Reported output tokens',number(data.reported_output_tokens)],['Stopped / failed',`${data.cancelled} / ${data.failed}`],['Replies at output cap',number(data.capped_replies)]]) {
    const card = element('div', 'performance-stat'); card.append(element('strong', '', value), element('span', '', label)); $('performance-summary').append(card);
  }
  $('performance-scope').textContent = data.scope === 'server' ? 'Server totals · administrator access' : 'Your account only · local performance records';
  $('performance-note').textContent = `${data.retention} First-text and full-reply medians above exclude built-in checks. ${data.reported_token_requests} replies supplied token counts (including zero-call checks); missing counts are not estimated. ${data.signals.map(item => item.note).join(' ')} Performance changes alone do not establish factual accuracy or quality drift.`;
}
$('open-system').addEventListener('click', async () => {$('system-dialog').showModal(); await loadAdmin(); await loadSystem();});
$('refresh-system').addEventListener('click', () => loadSystem());
$('server-metrics').addEventListener('click', () => loadSystem(true));
connect();

async function refreshExecution() {
  const state = await api('/api/admin/execution');
  $('execution-status').textContent = state.stopped ? 'Emergency shutdown active. No restricted tools can execute.' : state.active_grants.length ? 'Active: ' + state.active_grants.map(g => g.capability).join(', ') : 'All restricted capabilities disabled.';
}
$('mfa-setup-form').addEventListener('submit', async event => {
  event.preventDefault(); $('admin-error').textContent = ''; const password = $('mfa-password').value; $('mfa-password').value = '';
  const owner = activeUser?.id;
  try { const setup = await api('/api/admin/mfa/setup', {method:'POST',body:JSON.stringify({password})}); if (activeUser?.id !== owner || !adminState?.elevated) return; $('mfa-secret').textContent = setup.secret; $('mfa-enrollment').hidden = false; }
  catch (error) { $('admin-error').textContent = error.message; }
});
$('mfa-confirm-form').addEventListener('submit', async event => {
  event.preventDefault(); $('admin-error').textContent = ''; const otp = $('mfa-confirm-code').value; $('mfa-confirm-code').value = '';
  try { adminState = await api('/api/admin/mfa/confirm', {method:'POST',body:JSON.stringify({otp})}); renderAdmin(); await refreshExecution(); }
  catch (error) { $('admin-error').textContent = error.message; }
});
$('execution-capability').addEventListener('change', () => {
  const network = ['tcp-connect','tls-certificate'].includes($('execution-capability').value);
  $('execution-scope').value = JSON.stringify(network ? {kind:'network',cidrs:[],ports:[],authorization_reference:''} : {kind:'offline'},null,2);
  $('execution-arguments').value = JSON.stringify(network ? {host:'',port:443} : {text:''},null,2);
});
$('execution-grant-form').addEventListener('submit', async event => {
  event.preventDefault(); $('admin-error').textContent = '';
  try { await api('/api/admin/execution/grant', {method:'POST',body:JSON.stringify({capability:$('execution-capability').value,scope:JSON.parse($('execution-scope').value),seconds:300})}); await refreshExecution(); }
  catch (error) { $('admin-error').textContent = error.message; }
});
$('execution-run-form').addEventListener('submit', async event => {
  event.preventDefault(); $('admin-error').textContent = '';
  const owner=activeUser?.id;
  try { const value = await api('/api/admin/execution/run', {method:'POST',body:JSON.stringify({capability:$('execution-capability').value,arguments:JSON.parse($('execution-arguments').value)})}); if (activeUser?.id!==owner || !adminState?.elevated) return; $('execution-result').textContent = JSON.stringify(value.result,null,2); }
  catch (error) { $('admin-error').textContent = error.message; }
});
for (const [id,path,method] of [['execution-stop','stop','POST'],['execution-resume','resume','POST'],['execution-revoke','grants','DELETE']]) $(id).addEventListener('click', async () => {
  try { await api('/api/admin/execution/'+path,{method}); await loadAdmin(); }
  catch (error) { $('admin-error').textContent = error.message; }
});
$('execution-history').addEventListener('click', async () => {
  try { $('execution-log').textContent = JSON.stringify(await api('/api/admin/execution/history'),null,2); }
  catch (error) { $('admin-error').textContent = error.message; }
});

$('save-summary').addEventListener('click', async () => {
  const owner=activeUser?.id, conversation=session;
  try { const value=await api(`/api/conversations/${conversation}/summary`,{method:'POST'}); if (activeUser?.id!==owner || session!==conversation) return; $('conversation-summary').textContent=value.summary?.summary || ''; }
  catch(error) { $('memory-error').textContent=error.message; }
});
$('forget-summary').addEventListener('click', async () => {
  try { await api(`/api/conversations/${session}/summary`,{method:'DELETE'}); $('conversation-summary').textContent=''; }
  catch(error) { $('memory-error').textContent=error.message; }
});

function responseKey(name) { return activeUser ? name + '_' + activeUser.id : name; }
async function loadPreferenceControls() {
  const owner = activeUser?.id, request = ++preferenceLoadRequest;
  if (!owner) return;
  const result = await api('/api/preferences');
  if (activeUser?.id !== owner || request !== preferenceLoadRequest) return;
  savedPreferences = result.values;
  for (const [key, fallback] of Object.entries({reply_style: 'auto', tone: 'neutral', detail: 'standard', language: 'default'})) {
    $('preference-' + key).value = result.values[key] || fallback;
  }
  $('preferences-status').textContent = '';
}
$('preferences-form').addEventListener('submit', async event => {
  event.preventDefault(); const owner = activeUser?.id, request = ++preferenceLoadRequest;
  try {
    const values = Object.fromEntries(['reply_style', 'tone', 'detail', 'language'].map(key => [key, $('preference-' + key).value]));
    const result = await api('/api/preferences', {method: 'PUT', body: JSON.stringify({values})});
    if (activeUser?.id !== owner || request !== preferenceLoadRequest) return;
    savedPreferences = result.values; localStorage.removeItem(responseKey('zenith_reply_style'));
    $('reply-style').value = result.values.reply_style || 'auto';
    $('preferences-status').textContent = 'Saved for future answers. You can override the length in the composer.';
  } catch (error) { if (activeUser?.id === owner) $('preferences-status').textContent = error.message; }
});
$('clear-preferences').addEventListener('click', async () => {
  const owner = activeUser?.id, request = ++preferenceLoadRequest;
  try {
    await api('/api/preferences', {method: 'DELETE'});
    if (activeUser?.id !== owner || request !== preferenceLoadRequest) return;
    savedPreferences = {}; localStorage.removeItem(responseKey('zenith_reply_style'));
    await loadPreferenceControls(); if (owner !== activeUser?.id) return;
    $('reply-style').value = skillLibrary?.default_reply_style || 'auto';
    $('preferences-status').textContent = 'Preferences cleared for future answers.';
  } catch (error) { if (activeUser?.id === owner) $('preferences-status').textContent = error.message; }
});
$('open-analysis').addEventListener('click', () => {
  if (!activeUser) {openAccount(); return;}
  $('analysis-dialog').showModal(); $('analysis-status').textContent = '';
});
$('analysis-form').addEventListener('submit', async event => {
  event.preventDefault(); const owner = activeUser?.id, request = ++analysisRequest;
  $('analysis-result').replaceChildren();
  $('analysis-submit').disabled = true; $('analysis-status').textContent = 'Analyzing…';
  try {
    const delimiter = $('analysis-delimiter').value;
    const result = await api('/api/analysis/csv', {method: 'POST', body: JSON.stringify({csv_text: $('analysis-csv').value, delimiter: delimiter === 'tab' ? '\t' : delimiter})});
    if (owner !== activeUser?.id || request !== analysisRequest) return;
    const view = $('analysis-result'); view.replaceChildren();
    view.append(element('p', '', `${result.rows} records · ${result.columns} columns · ${result.duplicate_rows} exact duplicate records · ${result.elapsed_ms} ms`));
    view.append(element('p', '', `${result.formula_like_cells} formula-like cells detected; none executed. Dataset not saved.`));
    const table = element('table'); const head = element('tr');
    for (const text of ['Column', 'Kind', 'Present', 'Missing', 'Excluded text', 'Sum', 'Mean', 'Minimum', 'Maximum', 'Median']) head.append(element('th', '', text));
    table.append(head);
    for (const column of result.column_summaries) {
      const row = element('tr');
      for (const key of ['name', 'kind', 'present', 'missing', 'excluded_non_numeric', 'sum', 'mean', 'minimum', 'maximum', 'median']) row.append(element('td', '', String(column[key] ?? '—')));
      table.append(row);
    }
    const scroll = element('div', 'analysis-table'); scroll.append(table); view.append(scroll);
    $('analysis-status').textContent = 'Complete. Review missing values and exclusions before interpreting the results.';
  } catch (error) { if (owner === activeUser?.id && request === analysisRequest) $('analysis-status').textContent = error.message; }
  finally { if (request === analysisRequest) $('analysis-submit').disabled = false; }
});
async function loadImportedSkills(reset) {
  let view = $('imported-skill-results');
  if (!view) {
    view = element('section'); view.id = 'imported-skill-results'; $('skills-results').after(view);
  }
  if (reset) { view.replaceChildren(); importedSkillCursor = null; }
  const request = ++importedSkillRequest, owner = activeUser?.id;
  if (!owner) {view.append(element('p', '', 'Sign in to search operator-imported skill packs.')); return;}
  const query = $('skills-query').value, category = $('skills-category').value;
  try {
    const params = new URLSearchParams({query, limit: '25', after: reset ? '' : importedSkillCursor || ''});
    if (category) params.set('category', category);
    const result = await api('/api/skills/search?' + params);
    if (request !== importedSkillRequest || owner !== activeUser?.id || query !== $('skills-query').value || category !== $('skills-category').value) return;
    $('imported-skill-next')?.remove();
    if (!result.skills.length && reset) view.append(element('p', '', 'No matching imported profiles installed. Built-in profiles are shown above.'));
    for (const profile of result.skills) {
      const card = element('article', 'skill-card');
      card.append(element('span', 'eyebrow', 'Imported instruction profile'), element('h3', '', profile.name), element('p', '', profile.deliverable));
      const choose = element('button', '', 'Use ' + profile.name); choose.type = 'button';
      choose.addEventListener('click', async () => {
        try {await runSkillCommand('/skill ' + profile.id); $('skills-dialog').close();}
        catch (error) {$('skills-error').textContent = error.message;}
      });
      const details = element('button', '', 'Inspect workflow'); details.type = 'button';
      details.addEventListener('click', async () => {
        try {
          const full = await api('/api/skills/profile/' + encodeURIComponent(profile.id));
          if (owner !== activeUser?.id) return;
          const text = element('pre', '', full.instruction + '\n\n' + [...full.workflow, ...full.checklist].join('\n'));
          details.replaceWith(text);
        } catch (error) {$('skills-error').textContent = error.message;}
      });
      card.append(choose, details); view.append(card);
    }
    importedSkillCursor = result.next;
    if (result.next) {
      const next = element('button', '', 'Next imported profiles'); next.id = 'imported-skill-next'; next.type = 'button';
      next.addEventListener('click', () => { next.disabled = true; loadImportedSkills(false); }); view.append(next);
    }
  } catch (error) {if (request === importedSkillRequest && owner === activeUser?.id) $('skills-error').textContent = error.message;}
}
