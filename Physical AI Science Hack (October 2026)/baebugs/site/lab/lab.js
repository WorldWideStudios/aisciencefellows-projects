// BioKEA sample-prep lab viewer: renders the repo's real printable parts (STL) in WebGL.
//
// Usage (the host page must provide an import map for "three" and "three/addons/", see index.html):
//   import { mountLab } from './lab/lab.js';
//   const lab = await mountLab(document.getElementById('lab'), { partsUrl: 'lab/parts.json' });
//
// parts.json is produced by build_parts.py. STL paths inside it are relative to the site root,
// i.e. the parent folder of parts.json (override with options.siteBase).
// Geometry concepts, not tested on hardware. Layout positions are illustrative.

import * as THREE from 'three';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const PALETTE = {
  light: ['#c2410c', '#1d4ed8', '#15803d', '#a21caf', '#0e7490', '#b45309', '#475569'],
  dark: ['#fb923c', '#60a5fa', '#4ade80', '#e879f9', '#22d3ee', '#fbbf24', '#cbd5e1'],
};

const CSS = `
.bl{--bl-bg:#f6f7f9;--bl-panel:#fff;--bl-fg:#1b1f24;--bl-mute:#5b6572;--bl-line:#d3d8df;--bl-accent:#1d4ed8;--bl-warn:#8a4b00;--bl-warnbg:#fff4e0;
  display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:0;border:1px solid var(--bl-line);border-radius:10px;overflow:hidden;
  background:var(--bl-panel);color:var(--bl-fg);font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif}
@media (prefers-color-scheme:dark){.bl{--bl-bg:#12161b;--bl-panel:#181d23;--bl-fg:#e6e9ee;--bl-mute:#9aa5b1;--bl-line:#2f3741;--bl-accent:#7fb0ff;--bl-warn:#ffd08a;--bl-warnbg:#3a2a10}}
.bl *{box-sizing:border-box}
.bl-stage{position:relative;min-width:0;background:var(--bl-bg)}
.bl-canvas{display:block;width:100%;height:560px;touch-action:none;outline:none}
.bl-canvas:focus-visible{outline:2px solid var(--bl-accent);outline-offset:-2px}
.bl-note{position:absolute;left:8px;right:8px;top:8px;padding:5px 9px;border-radius:6px;background:var(--bl-warnbg);color:var(--bl-warn);font-size:12px;pointer-events:none}
.bl-load{position:absolute;right:10px;bottom:10px;padding:4px 9px;border-radius:6px;background:var(--bl-panel);border:1px solid var(--bl-line);font-size:12px;color:var(--bl-mute)}
.bl-load[hidden]{display:none}
.bl-load i{display:inline-block;width:10px;height:10px;margin-right:6px;border:2px solid var(--bl-line);border-top-color:var(--bl-accent);border-radius:50%;vertical-align:-1px;animation:bl-spin .8s linear infinite}
@keyframes bl-spin{to{transform:rotate(360deg)}}
.bl-card{position:absolute;left:8px;bottom:8px;max-width:min(330px,calc(100% - 100px));padding:9px 11px;border-radius:8px;background:var(--bl-panel);border:1px solid var(--bl-line);box-shadow:0 2px 10px rgba(0,0,0,.18);font-size:12.5px}
.bl-card[hidden]{display:none}
.bl-card h3{margin:0 22px 4px 0;font-size:14px;word-break:break-all}
.bl-card dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:1px 8px}
.bl-card dt{color:var(--bl-mute)}.bl-card dd{margin:0;word-break:break-word}
.bl-card code{font-size:12px}
.bl-x{position:absolute;right:4px;top:4px;border:0;background:none;color:var(--bl-mute);font-size:18px;line-height:1;padding:2px 7px;cursor:pointer;border-radius:4px}
.bl-side{display:flex;flex-direction:column;min-width:0;max-height:560px;border-left:1px solid var(--bl-line)}
.bl-tools{padding:10px;border-bottom:1px solid var(--bl-line);display:grid;gap:8px}
.bl-seg{display:grid;grid-template-columns:1fr 1fr;border:1px solid var(--bl-line);border-radius:6px;overflow:hidden}
.bl-seg button{border:0;background:var(--bl-panel);color:var(--bl-fg);padding:6px;cursor:pointer;font:inherit}
.bl-seg button[aria-pressed=true]{background:var(--bl-accent);color:#fff}
@media (prefers-color-scheme:dark){.bl-seg button[aria-pressed=true]{color:#0b1220}}
.bl-input{width:100%;padding:6px 8px;border:1px solid var(--bl-line);border-radius:6px;background:var(--bl-panel);color:var(--bl-fg);font:inherit}
.bl button:focus-visible,.bl input:focus-visible{outline:2px solid var(--bl-accent);outline-offset:1px}
.bl-count{font-size:12px;color:var(--bl-mute)}
.bl-list{overflow:auto;padding:4px 0;margin:0;list-style:none;flex:1}
.bl-mod{padding:4px 10px}
.bl-mod>label{display:flex;gap:7px;align-items:center;font-weight:600;cursor:pointer}
.bl-sw{width:12px;height:12px;border-radius:3px;flex:none;border:1px solid rgba(0,0,0,.35)}
.bl-tag{margin-left:auto;font-size:10.5px;font-weight:600;color:var(--bl-mute);border:1px solid var(--bl-line);border-radius:4px;padding:0 4px}
.bl-parts{list-style:none;margin:2px 0 4px 26px;padding:0}
.bl-parts button{display:block;width:100%;text-align:left;border:0;background:none;color:var(--bl-fg);font:inherit;font-size:12.5px;padding:2px 6px;border-radius:4px;cursor:pointer;word-break:break-all}
.bl-parts button:hover,.bl-parts button[aria-pressed=true]{background:var(--bl-bg);color:var(--bl-accent)}
.bl-parts button[aria-pressed=true]{font-weight:600}
.bl-parts button[data-dim]{opacity:.45}
.bl-help{padding:8px 10px;border-top:1px solid var(--bl-line);font-size:11.5px;color:var(--bl-mute)}
.bl-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
@media (max-width:700px){
  .bl{grid-template-columns:minmax(0,1fr)}
  .bl-canvas{height:min(62vh,420px)}
  .bl-side{border-left:0;border-top:1px solid var(--bl-line);max-height:none}
  .bl-list{max-height:340px}
  .bl-card{max-width:calc(100% - 100px)}
}`;

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') n.className = v; else if (k === 'text') n.textContent = v;
    else if (v === true) n.setAttribute(k, ''); else if (v !== false && v != null) n.setAttribute(k, v);
  }
  for (const c of kids) n.append(c);
  return n;
}

export async function mountLab(root, opts = {}) {
  const partsUrl = new URL(opts.partsUrl || 'parts.json', document.baseURI);
  const siteBase = new URL(opts.siteBase || '../', partsUrl);
  const data = await (await fetch(partsUrl)).json();

  if (!document.getElementById('bl-style')) document.head.append(el('style', { id: 'bl-style', text: CSS }));
  root.textContent = '';
  const wrap = el('div', { class: 'bl' });
  const canvas = el('canvas', { class: 'bl-canvas', tabindex: '0', role: 'img',
    'aria-label': '3D view of the lab parts. Drag to orbit, scroll to zoom, click a part for details. Use the list to select parts with the keyboard.' });
  const note = el('div', { class: 'bl-note', text: 'Geometry concepts, not tested on hardware. Positions are illustrative, not a validated layout.' });
  const load = el('div', { class: 'bl-load', role: 'status', hidden: true });
  const card = el('div', { class: 'bl-card', hidden: true, 'aria-live': 'polite' });
  const stage = el('div', { class: 'bl-stage' }, canvas, note, load, card);

  const bBench = el('button', { type: 'button', 'aria-pressed': 'true', text: 'Bench' });
  const bFlex = el('button', { type: 'button', 'aria-pressed': 'false', text: 'Flex deck' });
  const filter = el('input', { class: 'bl-input', type: 'search', placeholder: 'Filter: trommel, flex, PETG, CONCEPT', 'aria-label': 'Filter parts' });
  const count = el('div', { class: 'bl-count', role: 'status' });
  const list = el('ul', { class: 'bl-list', 'aria-label': 'Modules and parts' });
  const side = el('div', { class: 'bl-side' },
    el('div', { class: 'bl-tools' }, el('div', { class: 'bl-seg', role: 'group', 'aria-label': 'Platform view' }, bBench, bFlex), filter, count),
    list,
    el('div', { class: 'bl-help', text: 'Drag: orbit. Right-drag: pan. Wheel/pinch: zoom. Click a part or press Enter on a name in the list.' }));
  wrap.append(stage, side);
  root.append(wrap);

  // ---- three.js scene
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 1, 8000);
  camera.up.set(0, 0, 1);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x667788, 1.0));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(-300, -500, 900); scene.add(sun);
  const fill = new THREE.DirectionalLight(0xffffff, 0.6); fill.position.set(500, 400, 300); scene.add(fill);
  const grid = new THREE.GridHelper(2400, 48); grid.rotation.x = Math.PI / 2; grid.position.z = -0.2; scene.add(grid);
  const deck = new THREE.Group(); scene.add(deck);

  let dirty = true;
  const invalidate = () => { dirty = true; };
  controls.addEventListener('change', invalidate);

  const modNames = Object.keys(data.modules);
  const modColor = {}; modNames.forEach((m, i) => { modColor[m] = i; });
  const isDark = () => matchMedia('(prefers-color-scheme: dark)').matches;
  const colorOf = (m) => PALETTE[isDark() ? 'dark' : 'light'][modColor[m] % 7];

  // entries: one per parts.json row
  const entries = data.parts.map((p, i) => {
    const mod = p.modules[0];
    const text = [p.name, p.modules.join(' '), p.platform, p.status, p.materials.join(' '), p.stages.join(' '), p.slot || '',
      ...p.modules.flatMap((m) => data.modules[m]?.platform || [])].join(' ').toLowerCase();
    return { p, i, mod, text, mesh: null, state: 'idle', checked: true, matches: true };
  });
  const state = { view: 'bench', selected: null, hover: null };
  const isIn = (e) => e.p.platform === state.view;
  const visible = (e) => isIn(e) && e.checked && e.matches;

  // ---- geometry loading (cached by url; duplicate rows share geometry)
  const loader = new STLLoader();
  const geoCache = new Map();
  let pending = 0, failed = 0;
  function status() {
    load.hidden = pending === 0;
    load.replaceChildren(el('i'), document.createTextNode(`Loading ${pending} model${pending === 1 ? '' : 's'}...`));
    const inView = entries.filter(isIn);
    const shown = inView.filter((e) => visible(e));
    count.textContent = `${shown.length} of ${inView.length} parts shown` + (failed ? `, ${failed} failed to load` : '');
    root.dataset.labParts = String(entries.filter((e) => e.mesh).length);
    root.dataset.labPending = String(pending);
  }
  function getGeo(url) {
    if (!geoCache.has(url)) {
      geoCache.set(url, new Promise((res, rej) => loader.load(url, (g) => {
        g.computeVertexNormals(); g.computeBoundingBox();
        const b = g.boundingBox; // centre in x/y, rest on z=0
        g.translate(-(b.min.x + b.max.x) / 2, -(b.min.y + b.max.y) / 2, -b.min.z);
        res(g);
      }, undefined, rej)));
    }
    return geoCache.get(url);
  }
  function ensure(e) {
    if (e.state !== 'idle') return;
    e.state = 'loading'; pending++; status();
    getGeo(new URL(e.p.stl, siteBase).href).then((g) => {
      const mat = new THREE.MeshStandardMaterial({ color: colorOf(e.mod), roughness: 0.55, metalness: 0.05, side: THREE.DoubleSide });
      e.mesh = new THREE.Mesh(g, mat);
      e.mesh.position.set(...e.p.pos);
      e.mesh.userData.entry = e;
      e.mesh.visible = visible(e);
      scene.add(e.mesh); e.state = 'done';
    }).catch((err) => { e.state = 'failed'; failed++; console.warn('STL load failed', e.p.name, err?.message || err); })
      .finally(() => { pending--; status(); applyVisibility(); invalidate(); });
  }

  // ---- Flex deck: slot outlines + labels
  function labelSprite(text) {
    const c = document.createElement('canvas'); c.width = 128; c.height = 64;
    const x = c.getContext('2d'); x.font = 'bold 40px system-ui,sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillStyle = isDark() ? '#cbd5e1' : '#334155'; x.fillText(text, 64, 32);
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false, transparent: true }));
    s.scale.set(40, 20, 1); s.renderOrder = 5; return s;
  }
  function buildDeck() {
    deck.clear();
    const [w, h] = data.sbs_mm;
    for (const [name, s] of Object.entries(data.slots)) {
      const used = entries.some((e) => e.p.slot === name);
      const g = new THREE.PlaneGeometry(w, h);
      const m = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: isDark() ? 0x334155 : 0xcbd5e1, transparent: true, opacity: used ? 0.55 : 0.28 }));
      m.position.set(s.x, s.y, -0.1); deck.add(m);
      const ln = new THREE.LineSegments(new THREE.EdgesGeometry(g), new THREE.LineBasicMaterial({ color: isDark() ? 0x94a3b8 : 0x64748b }));
      ln.position.copy(m.position); deck.add(ln);
      const sp = labelSprite(name); sp.position.set(s.x - w / 2 + 14, s.y - h / 2 + 8, 1); deck.add(sp);
    }
  }
  buildDeck();

  // ---- visibility, framing
  function applyVisibility() {
    for (const e of entries) if (e.mesh) e.mesh.visible = visible(e);
    deck.visible = state.view === 'flex';
    grid.visible = state.view === 'bench';
    status(); invalidate();
  }
  function ensureVisible() { entries.forEach((e) => { if (visible(e)) ensure(e); }); }
  function frame() {
    const box = new THREE.Box3();
    if (state.view === 'flex') {
      const [w, h] = data.sbs_mm;
      for (const s of Object.values(data.slots)) { box.expandByPoint(new THREE.Vector3(s.x - w / 2, s.y - h / 2, 0)); box.expandByPoint(new THREE.Vector3(s.x + w / 2, s.y + h / 2, 100)); }
    } else {
      for (const e of entries) if (isIn(e)) {
        const [bx, by, bz] = e.p.bbox_mm, [x, y, z] = e.p.pos;
        box.expandByPoint(new THREE.Vector3(x - bx / 2, y - by / 2, z)); box.expandByPoint(new THREE.Vector3(x + bx / 2, y + by / 2, z + bz));
      }
    }
    const c = box.getCenter(new THREE.Vector3()), r = box.getSize(new THREE.Vector3()).length() / 2;
    const dist = r / Math.sin((camera.fov * Math.PI) / 360) * (camera.aspect < 1 ? 1.05 : 0.8);
    controls.target.copy(c);
    camera.position.set(c.x + dist * 0.25, c.y - dist * 0.8, c.z + dist * 0.55);
    camera.near = Math.max(1, dist / 100); camera.far = dist * 10; camera.updateProjectionMatrix();
    controls.update(); invalidate();
  }

  // ---- side list
  const partBtns = new Map(), modBoxes = new Map(), modItems = new Map();
  for (const m of modNames) {
    const info = data.modules[m];
    const box = el('input', { type: 'checkbox', checked: true, 'aria-label': `Show module ${m}` });
    const sw = el('span', { class: 'bl-sw', 'aria-hidden': 'true' });
    const lab = el('label', {}, box, sw, el('span', { text: m }), el('span', { class: 'bl-tag', text: info.status }));
    const ul = el('ul', { class: 'bl-parts' });
    for (const e of entries.filter((x) => x.p.modules.includes(m) && !x.p.view_copy)) {
      const b = el('button', { type: 'button', 'aria-pressed': 'false', text: e.p.name });
      b.addEventListener('click', () => {
        if (e.p.platform !== state.view && e.p.platform) { /* a part lives on one platform view */ }
        selectEntry(e, true);
      });
      ul.append(el('li', {}, b)); partBtns.set(e, b);
    }
    const li = el('li', { class: 'bl-mod' }, lab, ul);
    box.addEventListener('change', () => {
      entries.filter((e) => e.p.modules.includes(m)).forEach((e) => { e.checked = box.checked; });
      refresh();
    });
    list.append(li); modBoxes.set(m, { box, sw }); modItems.set(m, li);
  }
  function paintColors() {
    for (const m of modNames) modBoxes.get(m).sw.style.background = colorOf(m);
    for (const e of entries) if (e.mesh) e.mesh.material.color.set(colorOf(e.mod));
    scene.background = new THREE.Color(getComputedStyle(wrap).getPropertyValue('--bl-bg').trim() || '#f6f7f9');
    grid.material.color.set(isDark() ? 0x3b4552 : 0xb8c0cc);
    buildDeck(); invalidate();
  }
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', paintColors);

  function refresh() {
    const q = filter.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    for (const e of entries) e.matches = q.every((t) => e.text.includes(t));
    for (const [e, b] of partBtns) {
      if (e.matches) b.removeAttribute('data-dim'); else b.setAttribute('data-dim', '');
    }
    for (const m of modNames) {
      const rel = entries.filter((e) => e.p.modules.includes(m) && !e.p.view_copy);
      modItems.get(m).hidden = q.length > 0 && !rel.some((e) => e.matches);
    }
    ensureVisible(); applyVisibility();
  }
  filter.addEventListener('input', refresh);

  // ---- selection + card
  function selectEntry(e, fromList) {
    if (e && e.p.platform !== state.view && !fromList) return;
    // list picks of a part that lives in the other view switch the view
    if (e && fromList) {
      const target = e.p.view_copy ? state.view : e.p.platform;
      if (target !== state.view) setView(target);
    }
    state.selected = e;
    for (const [x, b] of partBtns) b.setAttribute('aria-pressed', String(x === e || (e && x.p.name === e.p.name && x.p.platform !== e.p.platform && false)));
    entries.forEach((x) => { if (x.mesh) x.mesh.material.emissive.set(x === e ? (isDark() ? 0x555555 : 0x333333) : 0x000000); });
    if (!e) { card.hidden = true; invalidate(); return; }
    const p = e.p, m = data.modules[e.mod];
    const dl = el('dl');
    const row = (k, v) => { dl.append(el('dt', { text: k }), el('dd', {}, v)); };
    row('Module', p.modules.join(', '));
    row('Platform', p.platform + (p.slot ? ` (slot ${p.slot})` : ''));
    row('Size', `${p.bbox_mm.map((v) => +v.toFixed(1)).join(' x ')} mm`);
    row('SHA-256', el('code', { text: p.sha256.slice(0, 12), title: p.sha256 }));
    row('Status', `${p.status}  (not tested on hardware)`);
    row('Materials', p.materials.join(', ') || 'n/a');
    const close = el('button', { class: 'bl-x', type: 'button', 'aria-label': 'Close part card', text: '×' });
    close.addEventListener('click', () => selectEntry(null));
    card.replaceChildren(close, el('h3', { text: p.name }), dl);
    card.hidden = false;
    void m; invalidate();
  }
  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
  let down = null;
  canvas.addEventListener('pointerdown', (ev) => { down = [ev.clientX, ev.clientY]; });
  canvas.addEventListener('pointerup', (ev) => {
    if (!down || Math.hypot(ev.clientX - down[0], ev.clientY - down[1]) > 5) return;
    const r = canvas.getBoundingClientRect();
    ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObjects(entries.filter((e) => e.mesh && e.mesh.visible).map((e) => e.mesh), false)[0];
    selectEntry(hit ? hit.object.userData.entry : null);
  });
  canvas.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') selectEntry(null); });

  function setView(v) {
    state.view = v;
    bBench.setAttribute('aria-pressed', String(v === 'bench')); bFlex.setAttribute('aria-pressed', String(v === 'flex'));
    if (state.selected && state.selected.p.platform !== v) selectEntry(null);
    ensureVisible(); applyVisibility(); frame();
  }
  bBench.addEventListener('click', () => setView('bench'));
  bFlex.addEventListener('click', () => setView('flex'));

  // ---- sizing + loop
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    if (canvas.width !== Math.round(w * renderer.getPixelRatio()) || canvas.height !== Math.round(h * renderer.getPixelRatio())) {
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); invalidate();
    }
  }
  new ResizeObserver(() => { resize(); }).observe(canvas);
  let raf = 0;
  (function tick() {
    raf = requestAnimationFrame(tick);
    resize();
    if (controls.update()) dirty = true;
    if (dirty) { dirty = false; renderer.render(scene, camera); }
  })();

  resize(); paintColors(); refresh(); frame();
  root.dataset.labReady = '1';
  return {
    setView, select: (name) => selectEntry(entries.find((e) => e.p.name === name && e.p.platform === state.view) || null, true),
    entries, destroy() { cancelAnimationFrame(raf); renderer.dispose(); root.textContent = ''; },
  };
}
