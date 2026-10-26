#!/usr/bin/env node
// npx github:biobitworks/baebugs get <root|module:x|leaf:path|hash|text>  — same pack, same answers as the Python CLI.
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RAW = 'https://raw.githubusercontent.com/biobitworks/baebugs/main/site/mvp/mvp.json';
const local = join(dirname(fileURLToPath(import.meta.url)), '..', 'site', 'mvp', 'mvp.json');

async function load() {
  if (existsSync(local)) return JSON.parse(readFileSync(local, 'utf8'));
  return (await fetch(RAW)).json();
}

function get(P, q) {
  q = q.trim();
  if (q === 'root' || q === P.root) return { address: 'root', root: P.root, roots: P.roots };
  if (q.startsWith('module:') && P.modules[q.slice(7)]) {
    const m = q.slice(7);
    return { address: q, ...P.modules[m], leaves: P.leaves.filter((x) => x.module === m).map((x) => x.path) };
  }
  const key = q.startsWith('leaf:') ? q.slice(5) : q;
  for (const x of P.leaves) if ([x.path, x.leaf, x.sha256].includes(key)) return { address: `leaf:${x.path}`, ...x };
  for (const e of P.external) if ([e.id, e.leaf].includes(q)) return { address: e.id, ...e };
  const ql = q.toLowerCase();
  const hits = P.leaves.filter((x) => JSON.stringify(x).toLowerCase().includes(ql)).map((x) => `leaf:${x.path}`);
  return { query: q, hits: hits.slice(0, 50), n: hits.length };
}

function prove(P, fco) {
  const by = new Map(P.leaves.map((x) => [x.path, x]));
  const rows = (fco.leaves || []).map((l) => { const x = by.get(l.path);
    return { path: l.path, yours: l.sha256, graph: x ? x.sha256 : null, verdict: !x ? 'NOT IN GRAPH' : l.sha256 === x.sha256 ? 'MATCH' : 'DIFFERS' }; });
  return { type: 'baebugs-attestation', graph_root: P.root, compared: rows.length, match: rows.filter((r) => r.verdict === 'MATCH').length, rows };
}

const [cmd = 'get', ...rest] = process.argv.slice(2);
const P = await load();
let out;
if (cmd === 'get') out = get(P, rest.join(' ') || 'root');
else if (cmd === 'prove') out = prove(P, JSON.parse(readFileSync(rest[0], 'utf8')));
else if (cmd === 'fco') out = { type: 'fco', leaves: rest.map((p) => ({ path: p, sha256: createHash('sha256').update(readFileSync(p)).digest('hex') })) };
else { console.error('usage: baebugs get <address|text> | prove <fco.json> | fco <files...>'); process.exit(2); }
console.log(JSON.stringify(out, null, 1));
