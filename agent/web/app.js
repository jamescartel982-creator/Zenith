'use strict';
const $ = id => document.getElementById(id);
let session = sessionStorage.getItem('zenith_session') || crypto.randomUUID();
sessionStorage.setItem('zenith_session', session);
$('token').value = sessionStorage.getItem('zenith_token') || '';
let busy = false;

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
function addMessage(role, text, turn = null) {
  $('welcome')?.remove();
  const article = element('article', `message ${role}`);
  article.append(element('div', 'who', role === 'user' ? 'YOU' : 'ZENITH'));
  article.append(element('pre', 'content', text));
  if (turn) {
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
async function connect() {
  showError('');
  try {
    const health = await api('/healthz');
    $('model').textContent = health.model;
    $('provider').textContent = health.provider === 'huggingface' ? 'Hugging Face · local inference' : health.provider === 'tiny' ? 'Zenith Tiny · experimental' : 'Ollama · local inference';
    $('status').textContent = health.model_loaded ? '● Model loaded' : '● Ready · loads on first message';
    if (health.authentication_required && !sessionStorage.getItem('zenith_token')) {
      $('access').open = true; $('status').textContent = 'Access token required'; return;
    }
    await loadHistory();
    $('access').open = false;
  } catch (error) { showError(error.message); $('status').textContent = 'Connection needs attention'; }
}
$('connect').addEventListener('click', () => {sessionStorage.setItem('zenith_token', $('token').value.trim()); connect();});
$('new-chat').addEventListener('click', () => {
  if (busy) return;
  sessionStorage.setItem('zenith_session', crypto.randomUUID());
  location.reload();
});
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
  const pending = element('p', 'pending', 'Thinking… The first message may take a few minutes while the model downloads.');
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
