const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const S = __dirname, THREE = path.join(S, 'node_modules/three');
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: path.join(S, 'video'), size: { width: 1280, height: 720 } }, colorScheme: 'light' });
  await ctx.route('https://cdn.jsdelivr.net/npm/three@0.160.0/**', (r) => {
    const rel = r.request().url().split('three@0.160.0/')[1];
    r.fulfill({ path: path.join(THREE, rel), contentType: 'application/javascript' });
  });
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.fulfill({ status: 200, body: '', contentType: 'text/css' }));
  const p = await ctx.newPage();
  const cap = async (t, ms = 2600) => {
    await p.evaluate((t) => { let d = document.getElementById('cap'); if (!d) { d = document.createElement('div'); d.id = 'cap';
      d.style.cssText = 'position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:rgba(20,22,20,.88);color:#fff;font:600 19px system-ui;padding:10px 18px;border-radius:10px;z-index:99;max-width:90%;text-align:center';
      document.body.append(d); } d.textContent = t; }, t);
    await p.waitForTimeout(ms);
  };
  await p.goto('http://localhost:8811/site/mvp/'); await p.waitForSelector('#g-rows tr');
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
  await cap('baebugs: the whole project as one graph, root to leaf', 3200);
  await cap('Custody is enforced: weights referenced by hash but never stored = recorded BREAK', 3400);
  await p.fill('#g-q', 'Coccinellidae'); await cap('Search any bug, part, file or hash', 2200);
  await p.click('#g-rows tr'); await cap('Every leaf: claim, licence in context, status, sha256, leaf hash', 2800);
  await p.click('#d-verify'); await p.waitForTimeout(800); await cap('Check this hash: your browser recomputes sha256 and it matches', 2800);
  await p.click('#t-claims'); await cap('What is ours (MIT), what adds terms (AGPL weights, CC BY photos), what is not ours', 3600);
  await p.click('#t-bugs'); await p.selectOption('#b-tray', 'HEX-2'); await cap('91 printable toy bugs sized from museum data + 278 taxa from training photos', 3200);
  await p.click('#t-parts'); await p.evaluate(() => document.querySelector('#p-parts iframe').scrollIntoView({ block: 'center' }));
  await cap('Modular lab in WebGL: trommel, sieves, Opentrons adapters, hand-off carrier', 5200);
  await p.click('#t-twin'); await p.waitForTimeout(1500); await cap('Bench digital twin: swap arms, filters, trays, water, heat, reagents', 4200);
  await p.click('#t-prove'); await p.click('#pv-go'); await cap('Bring your own FCO/FCG: compare leaf by leaf, copy an attestation, contest', 3600);
  await p.click('#t-agents'); await cap('Agents get the same root: CLI, MCP, npx, Claude plugin', 3400);
  await p.click('#t-graph'); await p.fill('#g-q', ''); await cap('github.com/biobitworks/baebugs', 2600);
  const v = p.video(); await ctx.close(); fs.renameSync(await v.path(), path.join(S, 'demo.webm')); await b.close();
})();
