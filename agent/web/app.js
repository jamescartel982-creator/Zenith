'use strict';
const $ = id => document.getElementById(id);
let session = sessionStorage.getItem('zenith_session') || crypto.randomUUID();
sessionStorage.setItem('zenith_session', session);
$('token').value = sessionStorage.getItem('zenith_token') || '';
let busy = false;
let configuredTeam = null;
let knowledgeStatus = null;
let catalogPage = 1;
let catalogRequest = 0;
let catalogLoaded = false;

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
    if (response.status === 401) $('access').open = true;
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
  if (trace.synthesizer?.status === 'ok' && trace.answer_stage !== 'draft_fallback') {
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
  article.append(element('pre', 'content', text));
  if (turn) {
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
}
async function loadHistory() {
  const data = await api(`/api/history/${session}`);
  if (data.turns.length) {
    $('messages').replaceChildren();
    for (const turn of data.turns) { addMessage('user', turn.prompt); addMessage('assistant', turn.response, turn); }
  }
}
function renderCatalogCounts(counts = {}) {
  $('catalog-stats').replaceChildren();
  const stats = [['huggingface_models', 'Hugging Face models'], ['github_models', 'GitHub model repositories'], ['huggingface_datasets', 'Hugging Face datasets'], ['github_datasets', 'GitHub dataset sources']];
  for (const [key, label] of stats) {
    const item = element('div', 'catalog-stat');
    item.append(element('strong', '', number(counts[key])), element('span', '', label));
    $('catalog-stats').append(item);
  }
  if (counts.models !== undefined && counts.datasets !== undefined) $('catalog-count').textContent = `${number(counts.models)} models · ${number(counts.datasets)} datasets`;
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
    const data = await api(`/api/catalog?${params}`);
    if (request !== catalogRequest) return;
    catalogLoaded = true;
    renderCatalogCounts(data.counts);
    $('catalog-results').replaceChildren();
    for (const entry of data.entries || []) $('catalog-results').append(renderCatalogEntry(entry));
    const total = Number(data.total) || 0;
    const pageSize = Number(data.page_size) || 20;
    catalogPage = Number(data.page) || catalogPage;
    const pages = Math.max(1, Math.ceil(total / pageSize));
    const start = total ? (catalogPage - 1) * pageSize + 1 : 0;
    const end = Math.min(catalogPage * pageSize, total);
    $('catalog-results-label').textContent = `${number(start)}–${number(end)} of ${number(total)} matching ${$('catalog-kind').value === 'dataset' ? 'dataset sources' : 'model references'}`;
    $('catalog-page').textContent = `Page ${catalogPage} of ${pages}`;
    $('catalog-previous').disabled = catalogPage <= 1;
    $('catalog-next').disabled = catalogPage >= pages;
    if (!total) $('catalog-results').append(element('p', 'catalog-empty', 'No matching sources. Try a broader search or another filter.'));
    const generated = typeof data.generated_at === 'string' ? new Date(data.generated_at) : null;
    $('catalog-generated').textContent = generated && !Number.isNaN(generated.valueOf()) ? `Snapshot: ${generated.toLocaleDateString()}` : 'Sourced metadata snapshot';
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
    $('model').textContent = health.model;
    $('provider').textContent = health.provider === 'huggingface' ? 'Hugging Face · local inference' : health.provider === 'tiny' ? 'Zenith Tiny · experimental' : health.provider === 'ensemble' ? 'Model team · combined answers' : 'Ollama · local inference';
    $('status').textContent = health.model_loaded ? '● Model loaded' : '● Ready · loads on first message';
    if (health.counts) renderCatalogCounts(health.counts);
    if (health.authentication_required && !sessionStorage.getItem('zenith_token')) {
      $('access').open = true; $('status').textContent = 'Access token required'; return;
    }
    await Promise.all([loadHistory(), loadTeam()]);
    $('access').open = false;
    catalogLoaded = false;
  } catch (error) { showError(error.message); $('status').textContent = 'Connection needs attention'; }
}
$('connect').addEventListener('click', () => {sessionStorage.setItem('zenith_token', $('token').value.trim()); connect();});
$('new-chat').addEventListener('click', () => {
  if (busy) return;
  sessionStorage.setItem('zenith_session', crypto.randomUUID());
  location.reload();
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
$('catalog-filters').addEventListener('submit', event => {event.preventDefault(); catalogPage = 1; loadCatalog();});
for (const id of ['catalog-kind', 'catalog-source']) $(id).addEventListener('change', () => {catalogPage = 1; loadCatalog();});
$('catalog-previous').addEventListener('click', () => {if (catalogPage > 1) {catalogPage -= 1; loadCatalog();}});
$('catalog-next').addEventListener('click', () => {catalogPage += 1; loadCatalog();});
$('delete-chat').addEventListener('click', async () => {
  if (busy || !confirm('Delete this conversation and its training approvals from this server? Already exported datasets are separate files.')) return;
  try {await api(`/api/history/${session}`, {method: 'DELETE'}); $('new-chat').click();}
  catch (error) {showError(error.message);}
});
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => {$('prompt').value = button.dataset.prompt; $('prompt').focus();}));
$('prompt').addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {event.preventDefault(); $('composer').requestSubmit();}
});
$('composer').addEventListener('submit', async event => {
  event.preventDefault();
  const text = $('prompt').value.trim();
  if (busy || !text) return;
  busy = true; showError(''); $('send').disabled = true; $('new-chat').disabled = true; $('prompt').disabled = true;
  $('messages').setAttribute('aria-busy', 'true');
  addMessage('user', text);
  const pending = element('p', 'pending', configuredTeam?.mode === 'ensemble' ? 'Consulting the configured model team… Contributors respond before the final synthesis.' : 'Thinking… The first message may take a few minutes while the model downloads.');
  $('messages').append(pending); $('messages').scrollTop = $('messages').scrollHeight;
  try {
    const result = await api('/api/chat', {method: 'POST', body: JSON.stringify({session_id: session, message: text})});
    pending.remove(); addMessage('assistant', result.response, result); $('prompt').value = ''; $('status').textContent = '● Connected';
  } catch (error) {
    pending.remove(); $('messages').lastElementChild?.remove(); showError(error.message);
  } finally {
    busy = false; $('send').disabled = false; $('new-chat').disabled = false; $('prompt').disabled = false;
    $('messages').setAttribute('aria-busy', 'false'); $('prompt').focus();
  }
});
connect();
