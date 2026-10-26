import { createViewer } from './viewer.js';
import { JOINTS, HOME, label, samplePlan, timeLabel } from './motion.js';

const $ = selector => document.querySelector(selector);
const client = crypto.randomUUID();
let token, state, sequences = [], sequence, plan = null, online = false, busy = false;
let draft = { ...HOME }, dirty = false, selectedPoint = null, dragged = null;
let previewPlaying = false, previewTime = 0, previousFrame = 0, toastTimeout;
let discovery = null, discovering = false;
let viewer, modelReady = false;
try {
  viewer = createViewer($('#viewport'), (text, ready = false) => {
    modelReady = ready;
    $('#model-status').textContent = text;
    renderState();
  });
} catch (error) {
  $('#model-status').textContent = `3D view unavailable: ${error.message}`;
  viewer = { setLive() {}, showGhost() {}, setPlan() {}, fit() {}, setGrid() {}, setPath() {} };
}

function notify(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => { $('#toast').hidden = true; }, 7000);
}
async function api(route, body) {
  const response = await fetch(`/api/${route}`, body === undefined ? { cache: 'no-store', signal: AbortSignal.timeout(6000) } : {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Studio-Token': token },
    body: JSON.stringify(body), signal: AbortSignal.timeout(15000),
  });
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error('Start the Python studio server to use the recorder. See robot_viewer/README.md.');
  }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Server returned ${response.status}`);
  return data;
}
async function run(action) {
  if (busy) return;
  busy = true;
  renderState();
  try {
    await action();
    if (token) await refreshState(true);
  } catch (error) {
    notify(error.message);
    // Retain the last confirmed document. A failed write must never display as saved.
    renderSequence();
  } finally {
    busy = false;
    renderState();
  }
}
function invalidate() {
  plan = null;
  previewPlaying = false;
  previewTime = 0;
  selectedPoint = null;
  viewer.showGhost(null);
  viewer.setPlan(null);
  $('#ghost-legend').hidden = true;
  $('#plan-summary').textContent = 'No current plan · plan after your edits';
  $('#plan-summary').classList.remove('ready');
  renderTimeline();
  renderState();
}
function acceptSequence(value) {
  sequence = value;
  $('#save-status').textContent = 'Saved locally';
  const index = sequences.findIndex(item => item.id === value.id);
  if (index < 0) sequences.push(value); else sequences[index] = value;
  try { localStorage.setItem('so101.sequence', value.id); } catch { /* persistence also lives on the server */ }
  invalidate();
  renderSequence();
}
async function editSequence(change) {
  const edited = structuredClone(sequence);
  change(edited);
  $('#save-status').textContent = 'Saving…';
  invalidate();
  try {
    const result = await api('sequence/save', { sequence_id: sequence.id, revision: sequence.revision, sequence: edited });
    acceptSequence(result.sequence);
  } catch (error) {
    $('#save-status').textContent = 'Save failed';
    throw error;
  }
}
function iconButton(symbol, title, action, disabled = false) {
  const button = document.createElement('button');
  button.className = 'icon-button'; button.textContent = symbol;
  button.title = title; button.setAttribute('aria-label', title);
  button.disabled = disabled;
  button.onclick = event => { event.stopPropagation(); run(action); };
  return button;
}
function renderSequence() {
  if (!sequence) return;
  $('#sequence-select').replaceChildren(...sequences.map(doc => {
    const option = new Option(doc.name, doc.id); option.selected = doc.id === sequence.id; return option;
  }));
  $('#sequence-name').value = sequence.name;
  $('#point-count').textContent = `${sequence.points.length} step${sequence.points.length === 1 ? '' : 's'}`;
  const simulated = sequence.points.filter(point => point.source === 'simulation').length;
  const hardware = sequence.points.filter(point => point.source === 'hardware').length;
  $('#source-summary').hidden = !(simulated && hardware);
  $('#source-summary').textContent = `Mixed sequence: ${hardware} hardware, ${simulated} simulated. Preview in Simulation; follower playback requires every position to be recorded from the arm.`;
  $('#empty-sequence').hidden = Boolean(sequence.points.length);
  if ($('#save-status').textContent !== 'Save failed') $('#save-status').textContent = 'Saved locally';
  $('#sequence-list').replaceChildren(...sequence.points.map((point, index) => {
    const pickup = point.kind === 'pickup_tip';
    const row = document.createElement('li'); row.className = 'point-row'; row.draggable = true;
    row.dataset.id = point.id; row.tabIndex = 0;
    row.setAttribute('aria-label', `Step ${index + 1}: ${point.name}`);
    const top = document.createElement('div'); top.className = 'point-top';
    const number = document.createElement('span'); number.className = 'point-number'; number.textContent = String(index + 1).padStart(2, '0');
    const input = document.createElement('input'); input.className = 'point-name'; input.value = point.name; input.maxLength = 80;
    input.setAttribute('aria-label', `Name of step ${index + 1}`);
    input.onclick = event => event.stopPropagation();
    input.onchange = () => run(() => editSequence(doc => { doc.points[index].name = input.value; }));
    const actions = document.createElement('div'); actions.className = 'point-actions';
    const move = offset => editSequence(doc => {
      [doc.points[index], doc.points[index + offset]] = [doc.points[index + offset], doc.points[index]];
    });
    actions.append(
      iconButton('↑', `Move ${point.name} up`, () => move(-1), index === 0),
      iconButton('↓', `Move ${point.name} down`, () => move(1), index === sequence.points.length - 1),
      iconButton('⧉', `Duplicate ${point.name}`, () => editSequence(doc => { doc.points.splice(index + 1, 0, { ...structuredClone(point), id: crypto.randomUUID(), name: `${point.name.slice(0, 72)} copy` }); })),
      iconButton('×', `Remove ${point.name}`, () => editSequence(doc => { doc.points.splice(index, 1); })),
    );
    top.append(number, input, actions);
    const details = document.createElement('div'); details.className = 'point-details';
    const values = document.createElement('span'); values.className = 'pose-values';
    values.textContent = pickup ? 'Z ↓ 3 mm  ↑ 3 mm · Cartesian' : `${point.source === 'hardware' ? 'ARM' : 'SIM'} · ${JOINTS.slice(0, 3).map(j => point.pose[j].toFixed(0)).join(' / ')}°`;
    values.title = pickup ? 'Holds X/Y, tool orientation and gripper opening. Returns to the preceding pose. If first, starts from the current arm pose. Distance is in the model; physical accuracy depends on calibration and tracking.' : JOINTS.map(j => `${label(j)}: ${point.pose[j].toFixed(1)}${j === 'gripper' ? '%' : '°'}`).join('\n');
    details.append(values);
    if (!pickup) {
      const dwell = document.createElement('label'); dwell.className = 'dwell-field'; dwell.append('Hold');
      const duration = document.createElement('input'); duration.type = 'number'; duration.min = '0'; duration.max = '30'; duration.step = '0.1'; duration.value = point.dwell;
      duration.setAttribute('aria-label', `Hold time for ${point.name}`);
      duration.onclick = event => event.stopPropagation();
      duration.onchange = () => run(() => editSequence(doc => { doc.points[index].dwell = Number(duration.value); }));
      dwell.append(duration, 's'); details.append(dwell);
    }
    row.append(top, details);
    const inspect = () => {
      if (state?.activity === 'executing') return;
      const planned = pickup ? plan?.segments.find(segment => segment.step_index === index) : null;
      if (pickup && !planned) { notify('Plan the sequence to inspect this pickup at its position in the sequence.'); return; }
      previewPlaying = false; selectedPoint = point.id;
      if (pickup) { previewTime = planned.start + planned.move; renderTimeline(); }
      viewer.showGhost(pickup ? planned.to : point.pose); $('#ghost-legend').hidden = false;
      $('#stage-title').textContent = point.name;
      $('#stage-subtitle').textContent = pickup ? 'Pickup bottom · 3 mm below the preceding pose in base Z' : 'Saved position · visual inspection';
      renderState();
    };
    row.onclick = inspect;
    row.onkeydown = event => { if (event.target === row && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); inspect(); } };
    row.ondragstart = event => {
      if (busy || state?.activity === 'executing' || event.target.closest('input,button')) { event.preventDefault(); return; }
      dragged = point.id; event.dataTransfer.effectAllowed = 'move'; event.dataTransfer.setData('text/plain', point.id); row.classList.add('dragging');
    };
    row.ondragend = () => { dragged = null; row.classList.remove('dragging'); };
    row.ondragover = event => { if (dragged) event.preventDefault(); };
    row.ondrop = event => {
      event.preventDefault();
      if (!dragged || dragged === point.id) return;
      const from = sequence.points.findIndex(p => p.id === dragged);
      if (from < 0) return;
      run(() => editSequence(doc => { const [moved] = doc.points.splice(from, 1); doc.points.splice(index, 0, moved); }));
    };
    return row;
  }));
  renderState();
}
function renderTimeline() {
  $('#timeline').max = plan?.duration || 1;
  $('#timeline').value = previewTime;
  $('#preview-time').textContent = `${timeLabel(previewTime)} / ${timeLabel(plan?.duration || 0)}`;
  const segment = plan?.segments[samplePlan(plan, previewTime).index];
  $('#preview-label').textContent = segment ? `${segment.step_index + 1} / ${plan.step_count} · ${segment.name}` : 'Plan a sequence to preview its motion';
}
function renderState() {
  const idle = state?.activity === 'idle';
  const executing = state?.activity === 'executing';
  const teleop = state?.activity === 'teleop';
  const physical = state?.mode === 'hardware';
  const matchingMode = $('#mode').value === state?.mode;
  const usable = online && !busy;
  $('#connection-badge').textContent = !online ? 'Server offline' : state.activity === 'fault' ? 'Robot fault' : `${physical ? 'Hardware' : 'Simulation'}${teleop ? ' · Teleop' : executing ? ' · Running' : ''}`;
  $('#connection-badge').className = `badge ${!online || state?.error ? 'offline' : physical ? 'hardware' : ''}`;
  $('#hardware-controls').hidden = $('#mode').value !== 'hardware';
  const settings = state?.teleop_settings;
  $('#teleop-profile').textContent = settings ? `Control: ${state.control_fps} Hz target. Teleop: ${Math.round(settings.tau * 1000)} ms smoothing · ${settings.deadband} deadband · ${settings.speed} °/s slew (gripper %/s).` : '';
  $('#connection-note').textContent = physical ? 'Live follower feedback. Stop holds position; disconnect preserves torque.' : $('#mode').value === 'hardware' ? (state?.hardware_enabled ? 'Connect the configured USB arms to begin.' : 'Start the server with --enable-hardware to connect.') : 'Try the full workflow with a virtual follower.';
  const requiredArms = $('#use-leader').checked ? ['follower', 'leader'] : ['follower'];
  const devicesReady = !discovery || requiredArms.every(role => discovery.arms[role]?.detected && !discovery.arms[role]?.busy);
  $('#connect').disabled = !usable || !state?.hardware_enabled || physical || !idle || !devicesReady;
  $('#disconnect').disabled = !usable || !physical || teleop || executing;
  $('#use-leader').disabled = physical || busy;
  $('#teleop').disabled = !usable || !physical || !state.has_leader || !idle;
  $('#teleop').hidden = !physical;
  $('.connection-links').hidden = !physical;
  $('#teleop').textContent = teleop ? 'Teleoperation active' : 'Start teleoperation';
  $('#release').disabled = !usable || !physical;
  $('#mode').disabled = busy || teleop || executing;
  $('#pose-heading').textContent = physical ? 'Live follower pose' : 'Simulated pose';
  $('#pose-age').textContent = online && state ? state.age < 0.5 ? '● live' : `${state.age.toFixed(1)}s old` : 'offline';
  $('#joint-help').textContent = physical ? 'Joint feedback in degrees; gripper in percent.' : `Move the sliders to teach a position. ${state?.limits_source || 'Loading limits…'}.`;
  $('#zero').disabled = !usable || !idle || physical || !matchingMode;
  $('#record').disabled = !usable || !matchingMode || (!idle && !teleop) || !sequence;
  $('#pickup-tip').disabled = !usable || (!idle && !teleop) || !sequence || sequence.points.length >= 200;
  $('#record-name').disabled = executing || busy;
  $('#plan').disabled = !usable || !idle || !matchingMode || !sequence?.points.length;
  $('#preview').disabled = !usable || !plan || !idle || !modelReady;
  $('#preview').textContent = previewPlaying ? 'Ⅱ Pause' : '▶ Preview';
  $('#execute').disabled = !usable || !idle || !matchingMode || !plan || !modelReady || previewPlaying || state.plan_id !== plan.id;
  $('#execute').textContent = physical ? 'Execute on follower ↗' : 'Execute in simulation ↗';
  $('#timeline').disabled = !plan || !idle || !usable;
  for (const id of ['sequence-select', 'sequence-name', 'new-sequence', 'import', 'speed', 'acceleration']) $( '#' + id).disabled = busy || executing || !online;
  $('#export').disabled = !sequence || busy;
  for (const j of JOINTS) {
    const input = $(`[data-joint="${j}"]`);
    if (!input) continue;
    input.disabled = !usable || !idle || physical || !matchingMode;
    if (state?.limits[j]) {
      input.min = Math.ceil(state.limits[j][0] * 10) / 10;
      input.max = Math.floor(state.limits[j][1] * 10) / 10;
    }
    const value = !physical && dirty ? draft[j] : state?.pose[j] ?? draft[j];
    input.value = value;
    input.parentElement.querySelector('output').textContent = `${value.toFixed(1)}${j === 'gripper' ? '%' : '°'}`;
  }
  document.querySelectorAll('.point-row').forEach((row, index) => {
    row.classList.toggle('selected', row.dataset.id === selectedPoint);
    row.classList.toggle('executing', executing && index === state.step);
    row.draggable = !busy && !executing;
    row.querySelectorAll('input,button').forEach(control => {
      const boundary = (control.title?.startsWith('Move') && (control.title.endsWith(' up') && index === 0 || control.title.endsWith(' down') && index === sequence.points.length - 1));
      control.disabled = !usable || executing || Boolean(boundary);
    });
  });
  $('#live-label').textContent = physical ? 'Live follower' : 'Simulated arm';
  if (!selectedPoint && !previewPlaying) {
    $('#stage-title').textContent = executing ? 'Sequence in motion.' : teleop ? 'Teaching with the leader.' : plan ? 'Your path is ready.' : 'Teach a movement.';
    $('#stage-subtitle').textContent = executing ? 'Following the planned joint trajectory.' : teleop ? 'Record each position as you move.' : plan ? 'Plan ready. Execute or preview the motion.' : 'Build a sequence, one position at a time.';
  }
  if (online && state) {
    $('#status').textContent = state.message;
    $('#status').classList.toggle('error', Boolean(state.error));
  }
}
function applyState(next) {
  state = next;
  online = true;
  if (!dirty || state.mode === 'hardware') draft = { ...state.pose };
  viewer.setLive(state.mode === 'simulation' && dirty ? draft : state.pose);
  if (plan && state.plan_id !== plan.id) invalidate();
  if (state.activity === 'executing' && plan) { previewTime = Math.min(state.elapsed, plan.duration); renderTimeline(); }
  renderState();
}
async function refreshState(force = false) {
  const next = await api('state');
  if (force || !busy) applyState(next);
}
async function syncSimulation() {
  if (state.mode === 'simulation' && dirty) {
    const result = await api('simulation', { pose: draft }); dirty = false; applyState(result.state);
  }
}
for (const j of JOINTS) {
  const row = document.createElement('div'); row.className = 'joint';
  const title = document.createElement('div'); title.className = 'joint-title';
  const text = document.createElement('span'); text.textContent = label(j);
  const output = document.createElement('output'); output.textContent = '0.0°'; title.append(text, output);
  const input = document.createElement('input'); input.type = 'range'; input.dataset.joint = j;
  input.setAttribute('aria-label', label(j)); input.step = '0.1'; input.min = '-180'; input.max = j === 'gripper' ? '100' : '180';
  input.oninput = () => { draft[j] = Number(input.value); dirty = true; invalidate(); viewer.setLive(draft); renderState(); };
  row.append(title, input); $('#joints').append(row);
}
$('#record').onclick = () => run(async () => {
  await syncSimulation();
  const result = await api('record', { sequence_id: sequence.id, revision: sequence.revision, name: $('#record-name').value });
  acceptSequence(result.sequence);
  $('#record-name').value = `Position ${sequence.points.length + 1}`;
  $('#sequence-list').lastElementChild?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
});
$('#pickup-tip').onclick = () => run(async () => {
  await editSequence(doc => { doc.points.push({ id: crypto.randomUUID(), name: 'Pickup tip', kind: 'pickup_tip' }); });
  $('#sequence-list').lastElementChild?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
});
$('#sequence-name').onchange = () => run(() => editSequence(doc => { doc.name = $('#sequence-name').value; }));
$('#sequence-select').onchange = () => { const doc = sequences.find(s => s.id === $('#sequence-select').value); if (doc) acceptSequence(doc); };
$('#new-sequence').onclick = () => run(async () => {
  const result = await api('sequence/create', { sequence: { version: 1, units: 'degrees_gripper_percent', name: `Sequence ${sequences.length + 1}`, points: [] } });
  acceptSequence(result.sequence); $('#record-name').value = 'Position 1';
});
$('#import').onclick = () => $('#import-file').click();
$('#import-file').onchange = () => run(async () => {
  const file = $('#import-file').files[0]; if (!file) return;
  try {
    if (file.size > 1_000_000) throw new Error('Sequence file must be under 1 MB.');
    const result = await api('sequence/create', { sequence: JSON.parse(await file.text()) }); acceptSequence(result.sequence);
  } finally { $('#import-file').value = ''; }
});
$('#export').onclick = () => {
  const { id, revision, ...document } = sequence;
  const url = URL.createObjectURL(new Blob([JSON.stringify(document, null, 2)], { type: 'application/json' }));
  const link = window.document.createElement('a'); link.href = url; link.download = `${sequence.name.replace(/[^a-zA-Z0-9_-]/g, '_')}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
};
$('#plan').onclick = () => run(async () => {
  await syncSimulation(); invalidate();
  const result = await api('plan', { sequence_id: sequence.id, revision: sequence.revision, speed: Number($('#speed').value), acceleration: Number($('#acceleration').value) });
  plan = result.plan; viewer.setPlan(plan); previewTime = 0;
  const pickup = plan.segments.some(segment => segment.kind === 'pickup_tip');
  $('#plan-summary').textContent = `${plan.duration.toFixed(1)} s · ${plan.step_count} steps · ${pickup ? 'Includes Cartesian Z moves' : 'Quintic interpolation'}`;
  $('#plan-summary').classList.add('ready'); renderTimeline();
});
$('#speed').onchange = invalidate; $('#acceleration').onchange = invalidate;
$('#preview').onclick = () => {
  if (!plan) return;
  if (previewTime >= plan.duration) previewTime = 0;
  previewPlaying = !previewPlaying; selectedPoint = null; previousFrame = performance.now();
  $('#ghost-legend').hidden = false;
  $('#stage-title').textContent = 'Previewing your sequence.'; $('#stage-subtitle').textContent = 'The translucent arm follows the planned motion.';
  renderState();
};
$('#timeline').oninput = () => {
  if (!plan) return;
  previewPlaying = false; previewTime = Number($('#timeline').value);
  viewer.showGhost(samplePlan(plan, previewTime).pose); $('#ghost-legend').hidden = false;
  renderTimeline(); renderState();
};
$('#live-view').onclick = () => { previewPlaying = false; selectedPoint = null; viewer.showGhost(null); $('#ghost-legend').hidden = true; renderState(); };
$('#execute').onclick = () => run(async () => {
  const result = await api('execute', { plan_id: plan.id, client }); viewer.showGhost(null); $('#ghost-legend').hidden = true; applyState(result.state);
});
$('#teleop').onclick = () => run(async () => { invalidate(); applyState((await api('teleop', { client })).state); });
// Stop bypasses the UI action queue; a pending save or preview must never delay this request.
$('#stop').onclick = async () => {
  invalidate();
  try { applyState((await api('stop', {})).state); }
  catch (error) { notify(`Stop could not be confirmed: ${error.message}`); }
};
$('#mode').onchange = () => {
  invalidate();
  if ($('#mode').value === 'simulation' && state.mode === 'hardware') run(async () => { dirty = false; applyState((await api('connect', { mode: 'simulation' })).state); });
  renderState();
  if ($('#mode').value === 'hardware') refreshDevices();
};
async function refreshDevices() {
  if (discovering || !online) return;
  discovering = true;
  $('#refresh-usb').disabled = true;
  try {
    discovery = await api('ports');
    const messages = ['follower', 'leader'].map(role => {
      const arm = discovery.arms[role];
      const status = !arm?.detected ? 'not detected' : arm.busy ? 'detected · busy in another controller' : arm.users.length ? 'connected to Studio' : 'detected · ready';
      return `${label(role)}: ${status}`;
    });
    if (Object.values(discovery.arms).some(arm => !arm.detected) && discovery.ports.length) {
      messages.push(`USB serials found: ${discovery.ports.map(port => port.usb_serial).join(', ')}. Check arms.json.`);
    }
    $('#usb-status').textContent = messages.join(' / ');
    renderState();
  } catch (error) {
    discovery = null;
    $('#usb-status').textContent = `USB check failed: ${error.message}`;
  } finally {
    discovering = false;
    $('#refresh-usb').disabled = false;
  }
}
$('#refresh-usb').onclick = refreshDevices;
$('#use-leader').onchange = renderState;
$('#connect').onclick = () => run(async () => {
  dirty = false; invalidate();
  applyState((await api('connect', { mode: 'hardware', leader: $('#use-leader').checked })).state);
  refreshDevices();
});
$('#disconnect').onclick = () => run(async () => { dirty = false; applyState((await api('connect', { mode: 'simulation' })).state); $('#mode').value = 'simulation'; });
$('#release').onclick = () => $('#release-dialog').showModal();
$('#cancel-release').onclick = () => $('#release-dialog').close();
$('#confirm-release').onclick = () => run(async () => { $('#release-dialog').close(); applyState((await api('release', {})).state); });
$('#zero').onclick = () => { draft = { ...HOME }; dirty = true; invalidate(); viewer.setLive(draft); renderState(); };
$('#fit').onclick = viewer.fit;
$('#grid').onchange = () => viewer.setGrid($('#grid').checked);
$('#path-toggle').onchange = () => viewer.setPath($('#path-toggle').checked);
window.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !$('#release-dialog').open) { event.preventDefault(); $('#stop').click(); }
  if (event.key.toLowerCase() === 'r' && !event.repeat && !event.ctrlKey && !event.metaKey && !event.altKey && !event.target.closest('input,select,textarea,button')) { event.preventDefault(); $('#record').click(); }
});
window.addEventListener('pagehide', () => {
  if (state?.owner === client) fetch('/api/stop', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Studio-Token': token }, body: '{}', keepalive: true }).catch(() => {});
});

function animate(now) {
  if (previewPlaying && plan) {
    const activePlan = plan;
    previewTime = Math.min(plan.duration, previewTime + Math.min((now - previousFrame) / 1000, 0.1));
    viewer.showGhost(samplePlan(plan, previewTime).pose); renderTimeline();
    if (previewTime >= plan.duration) {
      previewPlaying = false;
      run(async () => { if (plan?.id === activePlan.id) applyState((await api('review', { plan_id: activePlan.id })).state); });
    }
  }
  previousFrame = now;
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);

async function bootstrap() {
  const data = await api('bootstrap'); token = data.token; sequences = data.sequences;
  $('#mode').value = data.state.mode;
  $('#arm-identities').textContent = `Follower ${data.arms.follower.usb_serial} · Leader ${data.arms.leader.usb_serial}`;
  applyState(data.state);
  let previous;
  try { previous = localStorage.getItem('so101.sequence'); } catch { /* optional */ }
  acceptSequence(sequences.find(doc => doc.id === previous) || sequences[0]);
  $('#record-name').value = `Position ${sequence.points.length + 1}`;
  refreshDevices();
}
let polling = false;
async function poll() {
  if (polling || busy) return;
  polling = true;
  try { if (!token) await bootstrap(); else await refreshState(); }
  catch (error) {
    online = false; previewPlaying = false; renderState();
    $('#status').textContent = `Server unavailable. ${error.message}`;
    $('#status').classList.add('error');
  } finally { polling = false; }
}
let heartbeatPending = false;
setInterval(async () => {
  if (!token || state?.owner !== client || heartbeatPending) return;
  heartbeatPending = true;
  try { await api('heartbeat', { client }); } catch { /* control watchdog stops motion */ }
  finally { heartbeatPending = false; }
}, 800);
setInterval(poll, 200);
setInterval(() => { if ($('#mode').value === 'hardware') refreshDevices(); }, 5000);
renderState();
poll();
