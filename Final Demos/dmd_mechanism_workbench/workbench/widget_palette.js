/* ====================================================================
   DMD workbench — widget palette registry
   --------------------------------------------------------------------
   Every widget the mechanism dashboard (or a future generative-UI
   composer) can render lives here as one entry.

   An entry has:
     type          — stable string ID; used in layout specs
     desc          — one-line human description
     data_hint     — SQL / substrate hint for what data feeds the props
     props_schema  — LLM-facing prop shape (name → {type, desc, required?})
     example       — sample props that render meaningfully in isolation
     render(props) — returns HTML string; must be safe to concat

   Widgets read ONLY from their props (no globals). Palette entries are
   pure — the same render() called twice with the same props returns
   the same HTML.

   Currently registered (7):
     geneHeader · stackedBar · donutBreakdown · hbarList
     hypothesisTable · reasoningChain · hypothesisDetail

   TODO (variant-focused widgets we'll need for query-driven views):
     exonMap             — 79-exon strip with markers on affected exons
     isoformRibbon       — 7 isoform lanes, mark which are impacted
     frameShiftBadge     — Monaco-rule readout (in-frame / out-of-frame)
     variantEvidenceCard — per-variant evidence pack (ClinVar + LOVD + fold)
   ==================================================================== */

(function (root) {

  // ---------- shared helpers (kept small; identical to mechanism.html) ----------
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g,
    c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
  const fmtInt = (n) => Number(n).toLocaleString('en-US');
  const scoreTone = (v) => v >= 8 ? 'hi' : v >= 6.5 ? 'md' : 'lo';
  const confColor = (v) => v >= 80 ? 'var(--good)' : v >= 60 ? 'var(--warn)' : 'var(--bad)';

  const TIER_STYLE = {
    genotype:    { fill: '#eaf1fb', stroke: '#c3d6f0', text: '#1a2233' },
    cause:       { fill: '#fbf1e2', stroke: '#e9d0a4', text: '#1a2233' },
    consequence: { fill: '#fbe6e6', stroke: '#e9b7b7', text: '#1a2233' },
    outcome:     { fill: '#eef1f6', stroke: '#d1d7e0', text: '#1a2233' },
    therapeutic: { fill: '#e6f4ec', stroke: '#a9d3bd', text: '#1a2233' },
  };

  // ---- heatmap helpers (shared by heatmap + linkedHeatmap) -----
  const PALETTES = {
    // low → high
    blue:    [[234,241,251], [ 47,111,216]],  // --accent-soft → --accent
    warm:    [[255,241,222], [201, 74, 74]],  // pale amber → --bad
    diverge: [[ 47,111,216], [246,247,249], [201,74,74]],  // blue → neutral → red
  };
  function _heatColor(v, vmin, vmax, name) {
    if (vmax <= vmin) return 'rgb(234,241,251)';
    const t = Math.max(0, Math.min(1, (v - vmin) / (vmax - vmin)));
    const p = PALETTES[name] || PALETTES.blue;
    let a, b, u;
    if (p.length === 2) { a = p[0]; b = p[1]; u = t; }
    else {
      // 3-stop diverging: [0..0.5] a→b, [0.5..1] b→c
      if (t < 0.5) { a = p[0]; b = p[1]; u = t / 0.5; }
      else         { a = p[1]; b = p[2]; u = (t - 0.5) / 0.5; }
    }
    const c = a.map((v0, i) => Math.round(v0 + u * (b[i] - v0)));
    return `rgb(${c[0]},${c[1]},${c[2]})`;
  }
  function _wrapLabel(s, maxLen) {
    return s.length > maxLen ? s.slice(0, maxLen - 1) + '…' : s;
  }
  function _renderHeatmap(p) {
    const rows = p.rows, cols = p.cols;
    const { w: cw = 32, h: ch = 20 } = p.cellSize || {};
    const gap = 2;
    const leftMar = 110, topMar = 80;
    const weightW = p.rowWeight ? 60 : 0;
    const gridW = cols.length * (cw + gap) - gap;
    const gridH = rows.length * (ch + gap) - gap;
    const W = leftMar + gridW + (weightW ? 12 + weightW : 0) + 12;
    const H = topMar + gridH + 20;
    // scale
    const vmin = p.vmin ?? 0;
    const vmax = p.vmax ?? Math.max(...p.cells.map(x => x.v));
    // cells lookup
    const at = {};
    p.cells.forEach(c => { at[`${c.r}:${c.c}`] = c.v; });
    // col headers (rotated -45°)
    const colHdr = cols.map((label, c) => {
      const x = leftMar + c * (cw + gap) + cw / 2;
      const y = topMar - 6;
      return `<text x="${x}" y="${y}" transform="rotate(-45 ${x} ${y})"
                text-anchor="start" fill="var(--ink-2)" font-size="10">${esc(_wrapLabel(label, 20))}</text>`;
    }).join('');
    // row labels + cells
    let body = '';
    rows.forEach((label, r) => {
      const y = topMar + r * (ch + gap);
      body += `<text x="${leftMar - 6}" y="${y + ch / 2 + 3}" text-anchor="end" fill="var(--ink-2)" font-size="11">${esc(_wrapLabel(label, 18))}</text>`;
      cols.forEach((_, c) => {
        const x = leftMar + c * (cw + gap);
        const v = at[`${r}:${c}`];
        if (v === undefined) {
          body += `<rect x="${x}" y="${y}" width="${cw}" height="${ch}" fill="#f3f5f8" stroke="var(--line)"/>`;
        } else {
          const fill = _heatColor(v, vmin, vmax, p.palette);
          body += `<rect x="${x}" y="${y}" width="${cw}" height="${ch}" fill="${fill}"><title>${esc(rows[r])} × ${esc(cols[c])} = ${v}</title></rect>`;
        }
      });
    });
    // optional weight bar
    let weight = '';
    if (p.rowWeight) {
      const wmax = Math.max(...p.rowWeight);
      const bx = leftMar + gridW + 12;
      weight += `<text x="${bx}" y="${topMar - 6}" fill="var(--ink-3)" font-size="10" font-weight="600">${esc(p.weightLbl || '#')}</text>`;
      p.rowWeight.forEach((w, r) => {
        const y = topMar + r * (ch + gap);
        const bw = weightW * (w / wmax);
        weight += `<rect x="${bx}" y="${y + 2}" width="${bw}" height="${ch - 4}" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="0.5"/>
                   <text x="${bx + bw + 4}" y="${y + ch / 2 + 3}" fill="var(--ink-2)" font-size="10" font-variant-numeric="tabular-nums">${fmtInt(w)}</text>`;
      });
    }
    // legend (bottom-left, tiny)
    const legY = topMar + gridH + 8;
    let legend = '';
    for (let i = 0; i < 20; i++) {
      const v = vmin + (vmax - vmin) * (i / 19);
      legend += `<rect x="${leftMar + i * 8}" y="${legY}" width="8" height="8" fill="${_heatColor(v, vmin, vmax, p.palette)}"/>`;
    }
    legend += `<text x="${leftMar - 4}" y="${legY + 7}" text-anchor="end" fill="var(--ink-3)" font-size="10">${vmin}</text>
               <text x="${leftMar + 20 * 8 + 4}" y="${legY + 7}" fill="var(--ink-3)" font-size="10">${vmax}</text>`;
    return `
    <div class="panel" style="padding: 14px;">
      ${p.title ? `<div class="sub-h" style="margin-bottom:8px;">${esc(p.title)}</div>` : ''}
      <svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;">
        ${colHdr}
        ${body}
        ${weight}
        ${legend}
      </svg>
      ${p.footer ? `<div class="tile-foot" style="margin-top:6px;">${esc(p.footer)}</div>` : ''}
    </div>`;
  }
  function _renderExonArchitecture(p) {
    const { exons, domains = [], cellTypes: cts, psi, variants = [], colorLegend } = p;
    const nExons = exons.length;
    const cellW = 11, cellH = 22, gap = 0.5;
    const leftMar = 170, rightMar = 20, topMar = 20;
    const domainH  = 22;
    const rulerH   = 14;
    const variantH = 22;
    const gridW    = nExons * (cellW + gap) - gap;
    const gridH    = cts.length * cellH;
    const groupsW  = 22;   // left-side group bracket column
    const W = leftMar + gridW + rightMar;
    const H = topMar + domainH + rulerH + variantH + gridH + 24 + (p.footer ? 0 : 0);
    const xCol   = (n) => leftMar + (n - 1) * (cellW + gap);
    const colCtr = (n) => xCol(n) + cellW / 2;
    // ---- top: domain track ----
    const domainSvg = domains.map(d => {
      const x0 = xCol(d.start), x1 = xCol(d.end) + cellW;
      const w = x1 - x0;
      const cx = x0 + w / 2;
      const showLbl = w > 40;
      return `<rect x="${x0}" y="${topMar}" width="${w}" height="${domainH}" rx="3" fill="${d.color}" opacity="0.55" stroke="${d.color}" stroke-width="1"/>
              ${showLbl ? `<text x="${cx}" y="${topMar + domainH / 2 + 4}" text-anchor="middle" fill="white" font-size="10" font-weight="700">${esc(d.name)}</text>` : ''}
              <title>${esc(d.name)} (exons ${d.start}–${d.end})</title>`;
    }).join('');
    // ---- exon ruler (numbered ticks at 1, every 5, and last) ----
    const rulerY = topMar + domainH;
    let ruler = `<rect x="${leftMar}" y="${rulerY}" width="${gridW}" height="${rulerH}" fill="#f0f2f6" stroke="var(--line)"/>`;
    exons.forEach(({ n }) => {
      const x = xCol(n);
      // exon segment
      ruler += `<rect x="${x}" y="${rulerY}" width="${cellW}" height="${rulerH}" fill="${n % 2 ? '#fafbfd' : '#f0f2f6'}" stroke="none"/>`;
      if (n === 1 || n === nExons || n % 5 === 0) {
        ruler += `<line x1="${colCtr(n)}" y1="${rulerY + rulerH}" x2="${colCtr(n)}" y2="${rulerY + rulerH + 2}" stroke="var(--ink-3)" stroke-width="0.5"/>
                  <text x="${colCtr(n)}" y="${rulerY + rulerH - 3}" text-anchor="middle" fill="var(--ink-3)" font-size="8" font-weight="600">${n}</text>`;
      }
    });
    ruler += `<text x="${leftMar - 8}" y="${rulerY + rulerH / 2 + 3}" text-anchor="end" fill="var(--ink-3)" font-size="10" font-weight="600">exon</text>`;
    // ---- variant dot strip (above heatmap) ----
    const variantY = rulerY + rulerH;
    let variantsSvg = `<rect x="${leftMar}" y="${variantY}" width="${gridW}" height="${variantH}" fill="#fdfdff" stroke="var(--line)"/>`;
    variantsSvg += `<text x="${leftMar - 8}" y="${variantY + variantH / 2 + 3}" text-anchor="end" fill="var(--ink-3)" font-size="10" font-weight="600">variants</text>`;
    // Stack variants that share the same exon (offset y within the strip)
    const stack = {};
    variants.forEach(v => {
      stack[v.exon] = (stack[v.exon] || 0) + 1;
      const slot = stack[v.exon] - 1;
      const cy = variantY + variantH - 4 - slot * 6;   // stack upward
      const cx = colCtr(v.exon);
      variantsSvg += `<circle cx="${cx}" cy="${cy}" r="${v.r || 3}" fill="${v.color}" fill-opacity="0.75" stroke="${v.color}" stroke-width="0.8"><title>${esc(v.label || `exon ${v.exon}`)}</title></circle>`;
    });
    // ---- heatmap ----
    const gridY = variantY + variantH;
    const psiAt = {};
    psi.forEach(c => { psiAt[`${c.cellType}:${c.exon}`] = c.value; });
    let hm = '';
    cts.forEach((ct, r) => {
      const y = gridY + r * cellH;
      // row background zebra
      hm += `<rect x="${leftMar}" y="${y}" width="${gridW}" height="${cellH}" fill="${r % 2 ? '#fafbfd' : 'transparent'}"/>`;
      // row label
      hm += `<text x="${leftMar - 8}" y="${y + cellH / 2 + 3}" text-anchor="end" fill="var(--ink-2)" font-size="11">${esc(ct.label)}</text>`;
      // cells
      exons.forEach(({ n }) => {
        const v = psiAt[`${ct.id}:${n}`];
        const x = xCol(n);
        if (v === undefined) {
          hm += `<rect x="${x}" y="${y + 1}" width="${cellW}" height="${cellH - 2}" fill="#f3f5f8"/>`;
        } else {
          const fill = _heatColor(v, 0, 100, 'blue');
          hm += `<rect x="${x}" y="${y + 1}" width="${cellW}" height="${cellH - 2}" fill="${fill}"><title>${esc(ct.label)} × exon ${n}: PSI ${v}</title></rect>`;
        }
      });
    });
    // Group brackets on the far left (based on cts[i].group). Group column
    // is drawn to the LEFT of the row labels — we've reserved leftMar wide,
    // but labels use most of it. Draw compact vertical bars in the first 8px.
    let groups = '';
    let curGroup = null, groupStart = 0;
    cts.forEach((ct, r) => {
      if (ct.group !== curGroup) {
        if (curGroup !== null) {
          const y0 = gridY + groupStart * cellH;
          const y1 = gridY + r * cellH;
          groups += `<rect x="2" y="${y0}" width="4" height="${y1 - y0 - 2}" fill="var(--ink-3)" opacity="0.4" rx="2"/>
                     <text x="8" y="${(y0 + y1) / 2 + 3}" fill="var(--ink-3)" font-size="9" font-weight="700" text-transform="uppercase">${esc(curGroup || '')}</text>`;
        }
        curGroup = ct.group;
        groupStart = r;
      }
      if (r === cts.length - 1) {
        const y0 = gridY + groupStart * cellH;
        const y1 = gridY + (r + 1) * cellH;
        groups += `<rect x="2" y="${y0}" width="4" height="${y1 - y0 - 2}" fill="var(--ink-3)" opacity="0.4" rx="2"/>
                   <text x="8" y="${(y0 + y1) / 2 + 3}" fill="var(--ink-3)" font-size="9" font-weight="700" text-transform="uppercase">${esc(curGroup || '')}</text>`;
      }
    });
    // ---- bottom: legend row (PSI scale + variant colors) ----
    const legY = gridY + gridH + 12;
    let legend = `<text x="${leftMar}" y="${legY + 8}" fill="var(--ink-3)" font-size="10" font-weight="600">PSI:</text>`;
    for (let i = 0; i < 20; i++) {
      const v = (i / 19) * 100;
      legend += `<rect x="${leftMar + 32 + i * 8}" y="${legY}" width="8" height="10" fill="${_heatColor(v, 0, 100, 'blue')}"/>`;
    }
    legend += `<text x="${leftMar + 30}" y="${legY + 8}" text-anchor="end" fill="var(--ink-3)" font-size="10">0</text>
               <text x="${leftMar + 32 + 20 * 8 + 4}" y="${legY + 8}" fill="var(--ink-3)" font-size="10">100</text>`;
    // Variant color legend (right side of PSI legend)
    if (colorLegend) {
      const legStart = leftMar + 32 + 20 * 8 + 60;
      colorLegend.forEach((c, i) => {
        const x = legStart + i * 130;
        legend += `<circle cx="${x}" cy="${legY + 5}" r="4" fill="${c.color}" fill-opacity="0.75"/>
                   <text x="${x + 8}" y="${legY + 8}" fill="var(--ink-2)" font-size="10">${esc(c.label)}</text>`;
      });
    }
    return `
    <div class="panel" style="padding: 14px;">
      ${p.title ? `<div class="sub-h" style="margin-bottom:6px;">${esc(p.title)}</div>` : ''}
      <svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;">
        ${domainSvg}
        ${ruler}
        ${variantsSvg}
        ${groups}
        ${hm}
        ${legend}
      </svg>
      ${p.footer ? `<div class="tile-foot" style="margin-top:6px;">${esc(p.footer)}</div>` : ''}
    </div>`;
  }
  function _renderLollipop(p) {
    const { xAxis, yCategories: cats, variants: vs, exons, colorLegend } = p;
    const leftMar = 130, rightMar = 20, topMar = 30, rowH = 44;
    const exonH  = exons ? 12 : 0;
    const axisH  = 18;
    const plotH  = cats.length * rowH;
    const plotW  = 900;
    const W = leftMar + plotW + rightMar;
    const H = topMar + plotH + axisH + exonH + (xAxis.label ? 14 : 0) + 8;
    const xScale = (x) => leftMar + ((x - xAxis.min) / (xAxis.max - xAxis.min)) * plotW;
    const rowY   = (r) => topMar + r * rowH + rowH / 2;
    // Y row bands + labels + baselines
    let rows = '';
    cats.forEach((label, r) => {
      const yTop = topMar + r * rowH;
      const yBase = yTop + rowH - 4;
      rows += `<rect x="${leftMar}" y="${yTop}" width="${plotW}" height="${rowH}" fill="${r % 2 ? '#fafbfd' : 'transparent'}"/>
               <text x="${leftMar - 8}" y="${yTop + rowH / 2 + 3}" text-anchor="end" fill="var(--ink-2)" font-size="11" font-weight="500">${esc(label)}</text>
               <line x1="${leftMar}" y1="${yBase}" x2="${leftMar + plotW}" y2="${yBase}" stroke="var(--line)" stroke-width="1"/>`;
    });
    // X ticks / gridlines
    let ticks = '';
    const tickList = xAxis.ticks || [];
    tickList.forEach(t => {
      const x = xScale(t);
      ticks += `<line x1="${x}" y1="${topMar}" x2="${x}" y2="${topMar + plotH}" stroke="var(--line)" stroke-width="0.5"/>
                <text x="${x}" y="${topMar + plotH + 12}" text-anchor="middle" fill="var(--ink-3)" font-size="10" font-variant-numeric="tabular-nums">${t}</text>`;
    });
    // Lollipop markers: stem from row baseline to circle center, then circle.
    // If a variant has an `id`, the circle is tagged with data-variant-id so
    // callers can wire a click handler; the cursor changes to pointer.
    let marks = '';
    vs.forEach(v => {
      const x = xScale(v.x);
      const yBase = topMar + v.y * rowH + rowH - 4;
      const yCirc = rowY(v.y) - Math.min(rowH / 2 - 6, v.r + 2);
      const clickable = v.id != null;
      const cursor = clickable ? 'cursor:pointer;' : '';
      const idAttr = clickable ? ` data-variant-id="${esc(v.id)}"` : '';
      marks += `<line x1="${x}" y1="${yBase}" x2="${x}" y2="${yCirc}" stroke="${v.color}" stroke-width="0.8" opacity="0.55"/>
                <circle cx="${x}" cy="${yCirc}" r="${v.r}" fill="${v.color}" fill-opacity="0.55" stroke="${v.color}" stroke-width="1" style="${cursor}"${idAttr}><title>${esc(v.label || '')}</title></circle>`;
    });
    // Exon band strip (drawn under the X-axis tick labels)
    let exonBand = '';
    if (exons) {
      const bandY = topMar + plotH + axisH;
      exonBand = `<rect x="${leftMar}" y="${bandY}" width="${plotW}" height="${exonH}" fill="#eef1f6" stroke="var(--line)"/>`;
      // shade a hotspot region (exons 44-55) subtly
      const hotStart = xScale(44), hotEnd = xScale(56);
      exonBand += `<rect x="${hotStart}" y="${bandY}" width="${hotEnd - hotStart}" height="${exonH}" fill="var(--warn-soft)" opacity="0.8"/>
                   <text x="${(hotStart + hotEnd) / 2}" y="${bandY + exonH - 3}" text-anchor="middle" fill="var(--warn)" font-size="9" font-weight="700">Δex 44-55 hotspot</text>`;
      exonBand += `<text x="${leftMar - 8}" y="${bandY + exonH / 2 + 3}" text-anchor="end" fill="var(--ink-3)" font-size="10" font-weight="600">exons</text>`;
    }
    // X-axis label
    const xLbl = xAxis.label
      ? `<text x="${leftMar + plotW / 2}" y="${topMar + plotH + axisH + exonH + 10}" text-anchor="middle" fill="var(--ink-2)" font-size="11" font-weight="600">${esc(xAxis.label)}</text>`
      : '';
    // Color legend (top-right)
    let legend = '';
    if (colorLegend) {
      const items = colorLegend.map((c, i) => {
        const x = leftMar + plotW - 12 - (colorLegend.length - i) * 130;
        return `<circle cx="${x}" cy="${topMar - 12}" r="5" fill="${c.color}" fill-opacity="0.6" stroke="${c.color}"/>
                <text x="${x + 8}" y="${topMar - 9}" fill="var(--ink-2)" font-size="10">${esc(c.label)}</text>`;
      }).join('');
      legend = items;
    }
    return `
    <div class="panel" style="padding: 14px;">
      ${p.title ? `<div class="sub-h" style="margin-bottom:6px;">${esc(p.title)}</div>` : ''}
      <svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;">
        ${rows}
        ${ticks}
        ${marks}
        ${exonBand}
        ${xLbl}
        ${legend}
      </svg>
      ${p.footer ? `<div class="tile-foot" style="margin-top:6px;">${esc(p.footer)}</div>` : ''}
    </div>`;
  }
  function _renderLinkedHeatmap(p) {
    const ct = p.cellTypes, vt = p.variantTypes, pw = p.pathways;
    const cw = 30, ch = 22, gap = 2;
    const leftMar = 130, topMar = 80, weightW = 70, gutter = 24;
    const leftGridW  = vt.length * (cw + gap) - gap;
    const rightGridW = pw.length * (cw + gap) - gap;
    const gridH      = ct.length * (ch + gap) - gap;
    // x-offsets in the composed SVG
    const leftX   = leftMar;
    const weightX = leftX + leftGridW + gutter;
    const rightX  = weightX + weightW + gutter;
    const W = rightX + rightGridW + 14;
    const H = topMar + gridH + 24;
    const leftMax  = p.leftMax  ?? Math.max(...p.leftCells.map(c => c.v));
    const rightMax = p.rightMax ?? Math.max(...p.rightCells.map(c => c.v));
    const wmax = Math.max(...p.weight);
    // headers
    const hdr = (labels, offX) => labels.map((label, c) => {
      const x = offX + c * (cw + gap) + cw / 2;
      const y = topMar - 6;
      return `<text x="${x}" y="${y}" transform="rotate(-45 ${x} ${y})"
                text-anchor="start" fill="var(--ink-2)" font-size="10">${esc(_wrapLabel(label, 22))}</text>`;
    }).join('');
    // shared row labels (drawn once, to the left of the left grid)
    const rowLabels = ct.map((label, r) => {
      const y = topMar + r * (ch + gap);
      return `<text x="${leftX - 8}" y="${y + ch / 2 + 3}" text-anchor="end" fill="var(--ink-2)" font-size="11" font-weight="500">${esc(_wrapLabel(label, 18))}</text>`;
    }).join('');
    // cell renderers
    const renderCells = (cells, cols, offX, vmin, vmax, palette) => {
      const at = {};
      cells.forEach(c => { at[`${c.r}:${c.c}`] = c.v; });
      let out = '';
      ct.forEach((_, r) => {
        const y = topMar + r * (ch + gap);
        cols.forEach((__, c) => {
          const x = offX + c * (cw + gap);
          const v = at[`${r}:${c}`];
          if (v === undefined) {
            out += `<rect x="${x}" y="${y}" width="${cw}" height="${ch}" fill="#f3f5f8" stroke="var(--line)"/>`;
          } else {
            out += `<rect x="${x}" y="${y}" width="${cw}" height="${ch}" fill="${_heatColor(v, vmin, vmax, palette)}"><title>${v}</title></rect>`;
          }
        });
      });
      return out;
    };
    // weight bar column
    const weightHdr = `<text x="${weightX + weightW / 2}" y="${topMar - 6}" text-anchor="middle" fill="var(--ink-3)" font-size="10" font-weight="600"># path. variants</text>`;
    const weightBars = ct.map((_, r) => {
      const y = topMar + r * (ch + gap);
      const w = p.weight[r] || 0;
      const bw = Math.max(2, (weightW - 40) * (w / wmax));
      return `
        <rect x="${weightX}" y="${y + 2}" width="${bw}" height="${ch - 4}" fill="var(--accent)" opacity="0.8"/>
        <text x="${weightX + bw + 4}" y="${y + ch / 2 + 3}" fill="var(--ink-2)" font-size="10" font-variant-numeric="tabular-nums">${fmtInt(w)}</text>`;
    }).join('');
    // group titles (above headers)
    const titleLeft  = `<text x="${leftX + leftGridW / 2}"  y="${topMar - 58}" text-anchor="middle" fill="var(--ink-2)" font-size="11" font-weight="700" text-transform="uppercase">variant class → cell type</text>`;
    const titleRight = `<text x="${rightX + rightGridW / 2}" y="${topMar - 58}" text-anchor="middle" fill="var(--ink-2)" font-size="11" font-weight="700" text-transform="uppercase">cell type → pathway</text>`;
    // legend strip at bottom (shared: just the accent-blue scale)
    const legY = topMar + gridH + 8;
    let legend = '';
    for (let i = 0; i < 20; i++) {
      const v = i / 19;
      legend += `<rect x="${leftX + i * 8}" y="${legY}" width="8" height="8" fill="${_heatColor(v, 0, 1, 'blue')}"/>`;
    }
    legend += `<text x="${leftX - 4}" y="${legY + 7}" text-anchor="end" fill="var(--ink-3)" font-size="10">low</text>
               <text x="${leftX + 20 * 8 + 4}" y="${legY + 7}" fill="var(--ink-3)" font-size="10">high</text>`;
    return `
    <div class="panel" style="padding: 14px;">
      ${p.title ? `<div class="sub-h" style="margin-bottom:6px;">${esc(p.title)}</div>` : ''}
      <svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;">
        ${titleLeft}${titleRight}
        ${hdr(vt, leftX)}
        ${hdr(pw, rightX)}
        ${weightHdr}
        ${rowLabels}
        ${renderCells(p.leftCells,  vt, leftX,  0, leftMax,  'blue')}
        ${renderCells(p.rightCells, pw, rightX, 0, rightMax, 'warm')}
        ${weightBars}
        ${legend}
      </svg>
      ${p.footer ? `<div class="tile-foot" style="margin-top:6px;">${esc(p.footer)}</div>` : ''}
    </div>`;
  }

  // ============================================================
  //  W I D G E T S
  // ============================================================
  const WIDGETS = {

    // ---- 1. gene header banner ---------------------------------
    geneHeader: {
      type: 'geneHeader',
      desc: 'Top-of-page banner: gene name, aliases, isoform list, key counts, mechanism confidence score.',
      data_hint: 'SELECT * FROM gene_meta WHERE symbol=? ; plus header counts from lovd_variants + clinvar_phenotype + settings.',
      props_schema: {
        gene:   { type: 'object', required: true,
          desc: '{ symbol, fullName, uniprot, locus, nExons, locusSizeMb, isoformNames[] }' },
        header: { type: 'object', required: true,
          desc: '{ variantsAnalyzed, uniqueVariants, phenotyped, mechanismConfidence(0..100) }' },
      },
      example: {
        gene: { symbol: 'DMD', fullName: 'Duchenne Muscular Dystrophy',
                uniprot: 'P11532', locus: 'Xp21.2-p21.1', nExons: 79, locusSizeMb: 2.3,
                isoformNames: ['Dp427m','Dp427c','Dp427p','Dp260','Dp140','Dp116','Dp71'] },
        header: { variantsAnalyzed: 41566, uniqueVariants: 12831, phenotyped: 9491, mechanismConfidence: 82 },
      },
      render(p) {
        const { gene: g, header: h } = p;
        return `
        <div class="header">
          <div>
            <div class="h-title">${esc(g.fullName)}
              <span class="h-sub-inline">&nbsp;·&nbsp; Gene: ${esc(g.symbol)} &nbsp;·&nbsp; UniProt: ${esc(g.uniprot)}</span>
            </div>
            <div class="h-desc">${esc(g.locus)} · ${g.nExons} exons · ${g.locusSizeMb} Mb locus · ${g.isoformNames.length} tissue-specific isoforms (${g.isoformNames.join(', ')})</div>
            <div class="h-meta">
              <span><b>${fmtInt(h.variantsAnalyzed)}</b> LOVD entries analyzed</span>
              <span><b>${fmtInt(h.uniqueVariants)}</b> unique variants</span>
              <span><b>~${fmtInt(h.phenotyped)}</b> phenotyped</span>
            </div>
          </div>
          <div class="h-right">
            <div class="h-conf-lbl">Mechanism Confidence</div>
            <div class="h-conf" style="color:${confColor(h.mechanismConfidence)}">${h.mechanismConfidence}<small>/100</small></div>
          </div>
        </div>`;
      },
    },

    // ---- 2. stacked-bar tile -----------------------------------
    stackedBar: {
      type: 'stackedBar',
      desc: 'Tile with a hero number and a horizontal stacked bar with per-segment labels. Good for "total N split by category".',
      data_hint: 'GROUP BY <category>, COUNT(*) → segments; total → big.',
      props_schema: {
        title:     { type: 'string', required: true },
        big:       { type: 'string', desc: 'Hero number, pre-formatted.', required: true },
        bigSub:    { type: 'string', desc: 'Subtitle under the hero.' },
        breakdown: { type: 'array<{label, pct, color}>', required: true,
          desc: 'Segments sum to 100. Color is a CSS var like var(--accent).' },
        footer:    { type: 'string', desc: 'Small text at bottom.' },
      },
      example: {
        title: 'Genetic Evidence', big: '41,566', bigSub: 'LOVD variant reports',
        breakdown: [
          { label: 'Structural', pct: 62, color: 'var(--accent)' },
          { label: 'SNV',        pct: 25, color: 'var(--violet)' },
          { label: 'Other',      pct: 13, color: 'var(--teal)'   },
        ],
        footer: 'del 62% · sub 25% · dup 11% · delins 2%',
      },
      render(d) {
        let x = 10;
        const total = d.breakdown.reduce((a,b) => a + b.pct, 0);
        const segs = d.breakdown.map(seg => {
          const w = 140 * seg.pct / total;
          const s = `<rect x="${x}" y="24" width="${w}" height="16" fill="${seg.color}"/>`;
          x += w;
          return s;
        }).join('');
        const labels = d.breakdown.map((seg, i) => {
          const cx = 10 + (140 * (d.breakdown.slice(0,i).reduce((a,b)=>a+b.pct,0) + seg.pct/2) / total);
          return `<text x="${cx}" y="16" text-anchor="middle" fill="var(--ink-3)" font-size="9">${esc(seg.label)}</text>
                  <text x="${cx}" y="54" text-anchor="middle" fill="var(--ink-2)" font-size="9" font-weight="700">${seg.pct}%</text>`;
        }).join('');
        return `
        <div class="tile">
          <div class="tile-h">${esc(d.title)}</div>
          <div class="tile-big">${esc(d.big)}</div>
          <div class="tile-sub">${esc(d.bigSub || '')}</div>
          <div class="tile-body">
            <svg viewBox="0 0 160 60" width="100%" height="60" preserveAspectRatio="xMidYMid meet">
              <rect x="10" y="24" width="140" height="16" fill="var(--line)" rx="3"/>
              ${segs}${labels}
            </svg>
          </div>
          <div class="tile-foot">${esc(d.footer || '')}</div>
        </div>`;
      },
    },

    // ---- 3. donut breakdown tile -------------------------------
    donutBreakdown: {
      type: 'donutBreakdown',
      desc: 'Donut chart with center value + inline legend. Good for a "distribution of labels" tile.',
      data_hint: 'GROUP BY <label>, COUNT(*)/total*100 → segments; top segment → center.',
      props_schema: {
        title:    { type: 'string', required: true },
        segments: { type: 'array<{label, pct, color}>', required: true },
        center:   { type: '{value, label}', required: true,
          desc: 'What to write inside the donut hole.' },
        footer:   { type: 'string' },
      },
      example: {
        title: 'Phenotype Distribution',
        segments: [
          { label: 'DMD (Duchenne)',    pct: 98, color: 'var(--bad)'    },
          { label: 'BMD (Becker)',      pct:  1, color: 'var(--teal)'   },
          { label: 'DCM (cardiac)',     pct:  1, color: 'var(--violet)' },
        ],
        center: { value: '98%', label: 'DMD (Duchenne)' },
        footer: 'ClinVar submissions (stub)',
      },
      render(d) {
        const R = 38, C = 2 * Math.PI * R;
        let offset = 0;
        const arcs = d.segments.map(seg => {
          const len = C * seg.pct / 100;
          const a = `<circle cx="50" cy="50" r="${R}" fill="none" stroke="${seg.color}"
                     stroke-width="16" stroke-dasharray="${len} ${C - len}"
                     stroke-dashoffset="${-offset}" transform="rotate(-90 50 50)"/>`;
          offset += len;
          return a;
        }).join('');
        const legend = d.segments.map(s =>
          `<div class="legend-row"><span class="legend-sw" style="background:${s.color}"></span> ${esc(s.label)} (${s.pct}%)</div>`
        ).join('');
        const footer = d.footer ? `<div class="tile-foot">${esc(d.footer)}</div>` : '';
        return `
        <div class="tile">
          <div class="tile-h">${esc(d.title)}</div>
          <div class="tile-body" style="flex-direction: column; gap: 8px;">
            <svg viewBox="0 0 100 100" width="120" height="120">
              <circle cx="50" cy="50" r="${R}" fill="none" stroke="var(--line)" stroke-width="16"/>
              ${arcs}
              <text x="50" y="47" text-anchor="middle" fill="var(--ink)" font-size="16" font-weight="700">${esc(d.center.value)}</text>
              <text x="50" y="60" text-anchor="middle" fill="var(--ink-3)" font-size="7">${esc(d.center.label)}</text>
            </svg>
            <div class="legend">${legend}</div>
          </div>
          ${footer}
        </div>`;
      },
    },

    // ---- 4. horizontal-bar list tile ---------------------------
    hbarList: {
      type: 'hbarList',
      desc: 'Vertical stack of labeled horizontal bars, sized by value. Good for "top-N by score" lists.',
      data_hint: 'SELECT label, value, color_hint FROM <table> ORDER BY value DESC LIMIT N.',
      props_schema: {
        title:  { type: 'string', required: true },
        rows:   { type: 'array<{label, value, color, unit?}>', required: true },
        max:    { type: 'number', desc: 'Cap for the bar scale; defaults to max(value).' },
        footer: { type: 'string' },
      },
      example: {
        title: 'Isoform Impact',
        rows: [
          { label: 'Dp427m', value: 100, unit: '%', color: 'var(--bad)'  },
          { label: 'Dp427c', value: 100, unit: '%', color: 'var(--bad)'  },
          { label: 'Dp427p', value: 100, unit: '%', color: 'var(--bad)'  },
          { label: 'Dp260',  value:  85, unit: '%', color: 'var(--warn)' },
          { label: 'Dp140',  value:  67, unit: '%', color: 'var(--warn)' },
          { label: 'Dp116',  value:  49, unit: '%', color: 'var(--warn)' },
          { label: 'Dp71',   value:  22, unit: '%', color: 'var(--teal)' },
        ],
        max: 100,
        footer: 'Exon coverage of NM_004006.2 (79 exons)',
      },
      render(d) {
        const max = d.max ?? Math.max(...d.rows.map(r => r.value));
        const rows = d.rows.map(r => `
          <div class="hbar-row">
            <div class="hbar-lbl" title="${esc(r.label)}">${esc(r.label)}</div>
            <div class="hbar-track"><div class="hbar-fill" style="width:${(100 * r.value / max).toFixed(1)}%;background:${r.color}"></div></div>
            <div class="hbar-val">${r.unit === '%' ? r.value + '%' : r.value}</div>
          </div>`).join('');
        return `
        <div class="tile">
          <div class="tile-h">${esc(d.title)}</div>
          <div class="tile-body stretch"><div class="hbar-list">${rows}</div></div>
          <div class="tile-foot">${esc(d.footer || '')}</div>
        </div>`;
      },
    },

    // ---- 5. hypothesis table -----------------------------------
    hypothesisTable: {
      type: 'hypothesisTable',
      desc: 'Ranked table of candidate mechanistic hypotheses with supporting counts, odds ratio, evidence score, druggability dots.',
      data_hint: 'SELECT * FROM hypotheses ORDER BY rank; count denominator from meta.',
      props_schema: {
        rows: { type: 'array<Hypothesis>', required: true,
          desc: 'Hypothesis: { id, name, subtitle, supporting, oddsRatio, evidence(0..10), druggability(0..5), therapeutic, selected? }' },
        meta: { type: '{top, total, unit}', desc: 'Section subtitle: "top {top} of {total} {unit}"' },
      },
      example: {
        rows: [
          { id: '01', name: 'Out-of-frame deletions → truncated dystrophin', subtitle: 'Monaco rule; DGC loss; membrane tears',
            supporting: 18204, oddsRatio: 14.2, evidence: 9.4, druggability: 4,
            therapeutic: 'Exon-skipping ASOs; micro-dystrophin gene therapy', selected: true },
          { id: '02', name: 'Nonsense read-through failure', subtitle: 'Premature stop → NMD',
            supporting: 3271, oddsRatio: 5.8, evidence: 7.9, druggability: 3,
            therapeutic: 'Ataluren; ELX-02', selected: false },
        ],
        meta: { top: 4, total: 41566, unit: 'hypotheses shown' },
      },
      render(d) {
        const rowHtml = (h) => {
          const dots = Array.from({length: 5}, (_, i) =>
            `<span class="${i < h.druggability ? 'on' : ''}"></span>`).join('');
          return `
            <tr class="${h.selected ? 'sel' : ''}" data-hid="${esc(h.id)}">
              <td class="hyp-num">${esc(h.id)}</td>
              <td class="hyp-name">${esc(h.name)}<small>${esc(h.subtitle)}</small></td>
              <td class="hyp-num-cell">${fmtInt(h.supporting)}</td>
              <td class="hyp-num-cell">${h.oddsRatio.toFixed(1)}</td>
              <td class="hyp-num-cell"><span class="score-pill score-${scoreTone(h.evidence)}">${h.evidence.toFixed(1)}</span></td>
              <td><span class="drug-dots">${dots}</span></td>
              <td>${esc(h.therapeutic)}</td>
            </tr>`;
        };
        const countLbl = d.meta
          ? `<span class="section-count">top <b>${fmtInt(d.meta.top)}</b> of <b>${fmtInt(d.meta.total)}</b> ${esc(d.meta.unit || 'candidates')}</span>`
          : '';
        return `
        <div class="section-lbl">Mechanistic Hypotheses${countLbl}</div>
        <div class="panel">
          <table class="hyp">
            <thead><tr>
              <th></th>
              <th style="width: 34%;">Hypothesis</th>
              <th class="hyp-num-cell">Supporting<br>variants</th>
              <th class="hyp-num-cell">Odds<br>ratio</th>
              <th class="hyp-num-cell">Evidence<br>score</th>
              <th>Druggability</th>
              <th>Therapeutic rationale</th>
            </tr></thead>
            <tbody>${d.rows.map(rowHtml).join('')}</tbody>
          </table>
        </div>`;
      },
    },

    // ---- 6. reasoning chain SVG --------------------------------
    reasoningChain: {
      type: 'reasoningChain',
      desc: 'Node/edge SVG diagram on a 3×N grid, showing a causal chain from genotype → mechanism → phenotype → therapy. Edges are clickable when they carry evidence; hosting page listens for [data-edge-id] clicks and shows the edgeEvidenceBar for the selected edge.',
      data_hint: 'SELECT * FROM hypothesis_chain_nodes / hypothesis_chain_edges / hypothesis_therapeutic_node WHERE hypothesis_id=?. Attach per-edge evidence via hypothesis_chain_edge_evidence.',
      props_schema: {
        chain:         { type: 'object', required: true,
          desc: '{ nodes: [{id, col, row, tier(cause|mechanism|phenotype|therapeutic), label1, label2, meta}], edges: [{from, to, id?, evidence?: [{tone,text,cite}]}], therapeutic?: {label1, label2} }' },
        selectedEdgeId:{ type: 'string', desc: 'Optional: id of the edge to highlight (e.g. "v3-m1").' },
      },
      example: {
        chain: {
          nodes: [
            { id: 'g',  col: 0, row: 0, tier: 'cause',     label1: 'Δexon 45',            label2: 'out-of-frame',  meta: '~5% of DMD patients' },
            { id: 'c',  col: 1, row: 0, tier: 'cause',     label1: 'PTC in mRNA',         label2: 'NMD → no Dp427', meta: '' },
            { id: 'x',  col: 2, row: 0, tier: 'mechanism', label1: 'Sarcolemmal DGC loss',label2: 'membrane fragility', meta: '' },
            { id: 'p',  col: 1, row: 1, tier: 'phenotype', label1: 'Necrosis',            label2: 'fibrosis',      meta: 'progressive' },
          ],
          edges: [
            { from: 'g', to: 'c', id: 'g-c', evidence: [{tone:'good', text:'Reading frame ≡ 0 (mod 3) test', cite:'Monaco 1988'}] },
            { from: 'c', to: 'x', id: 'c-x', evidence: [{tone:'good', text:'PTC → NMD → protein absent',    cite:'Popp 2013'}] },
            { from: 'x', to: 'p', id: 'x-p', evidence: [{tone:'good', text:'DGC loss → Ca²⁺ → necrosis',    cite:'Petrof 1993'}] },
          ],
          therapeutic: { label1: 'Exon-44 skipping ASO', label2: 'restores reading frame' },
        },
      },
      render(p) {
        const chain = p.chain;
        if (!chain) return '';
        const nodeW = 150, nodeH = 52, gapX = 24, gapY = 46;
        const cols = 1 + Math.max(...chain.nodes.map(n => n.col));
        const rows = 1 + Math.max(...chain.nodes.map(n => n.row));
        const W = cols * nodeW + (cols - 1) * gapX + 28;
        const H = rows * nodeH + (rows - 1) * gapY + 24 + (chain.therapeutic ? 60 : 0);
        const nodeX = (c) => 14 + c * (nodeW + gapX);
        const nodeY = (r) => 14 + r * (nodeH + gapY);
        const centerX = (c) => nodeX(c) + nodeW / 2;
        const centerY = (r) => nodeY(r) + nodeH / 2;
        const byId = Object.fromEntries(chain.nodes.map(n => [n.id, n]));
        const nodeSvg = chain.nodes.map(n => {
          const st = TIER_STYLE[n.tier] || TIER_STYLE.cause;
          const x = nodeX(n.col), y = nodeY(n.row);
          return `
            <g>
              <rect x="${x}" y="${y}" width="${nodeW}" height="${nodeH}" rx="8" fill="${st.fill}" stroke="${st.stroke}"/>
              <text x="${x + nodeW/2}" y="${y + 20}" text-anchor="middle" fill="${st.text}" font-size="11" font-weight="700">${esc(n.label1)}</text>
              <text x="${x + nodeW/2}" y="${y + 34}" text-anchor="middle" fill="${st.text}" font-size="11" font-weight="700">${esc(n.label2)}</text>
              <text x="${x + nodeW/2}" y="${y + 46}" text-anchor="middle" fill="var(--ink-3)" font-size="9">${esc(n.meta || '')}</text>
            </g>`;
        }).join('');
        const edgeSvg = chain.edges.map(e => {
          const a = byId[e.from], b = byId[e.to];
          let x1, y1, x2, y2;
          if (a.row === b.row) {
            y1 = y2 = centerY(a.row);
            if (a.col < b.col) { x1 = nodeX(a.col) + nodeW; x2 = nodeX(b.col); }
            else               { x1 = nodeX(a.col);         x2 = nodeX(b.col) + nodeW; }
          } else if (a.col === b.col) {
            x1 = x2 = centerX(a.col);
            if (a.row < b.row) { y1 = nodeY(a.row) + nodeH; y2 = nodeY(b.row); }
            else               { y1 = nodeY(a.row);          y2 = nodeY(b.row) + nodeH; }
          } else {
            x1 = centerX(a.col); y1 = centerY(a.row);
            x2 = centerX(b.col); y2 = centerY(b.row);
          }
          const eid = e.id || `${e.from}-${e.to}`;
          const clickable = e.evidence && e.evidence.length > 0;
          const sel = eid === p.selectedEdgeId;
          const stroke = sel ? 'var(--accent)' : (clickable ? '#5a7fbe' : '#8892a6');
          const width  = sel ? 2.4 : (clickable ? 1.8 : 1.5);
          // Wider transparent overlay = larger hit target for the click.
          const hit = clickable
            ? `<line class="edge-hit" data-edge-id="${esc(eid)}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"
                     stroke="transparent" stroke-width="14" style="cursor:pointer;"/>`
            : '';
          return `${hit}<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}" marker-end="url(#arrowP)"/>`;
        }).join('');
        let therapy = '';
        if (chain.therapeutic) {
          const tx = 14 + (W - 28 - 286) / 2;
          const ty = rows * nodeH + (rows - 1) * gapY + 14 + 20;
          const anchorX = centerX(Math.max(0, Math.floor(cols / 2)));
          const anchorYtop = nodeY(rows - 1) + nodeH;
          const st = TIER_STYLE.therapeutic;
          therapy = `
            <line x1="${anchorX}" y1="${anchorYtop}" x2="${anchorX}" y2="${ty}" stroke="#8892a6" stroke-width="1.5" stroke-dasharray="3 3" marker-end="url(#arrowP)"/>
            <g>
              <rect x="${tx}" y="${ty}" width="286" height="42" rx="8" fill="${st.fill}" stroke="${st.stroke}"/>
              <text x="${tx + 143}" y="${ty + 19}" text-anchor="middle" fill="${st.text}" font-size="11" font-weight="700">${esc(chain.therapeutic.label1)}</text>
              <text x="${tx + 143}" y="${ty + 33}" text-anchor="middle" fill="var(--ink-3)" font-size="9">${esc(chain.therapeutic.label2)}</text>
            </g>`;
        }
        return `
          <svg viewBox="0 0 ${W} ${H}" width="100%" style="max-height: 460px;">
            <defs>
              <marker id="arrowP" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0,0 L10,5 L0,10 z" fill="#8892a6"/>
              </marker>
            </defs>
            ${edgeSvg}
            ${nodeSvg}
            ${therapy}
          </svg>`;
      },
    },

    // ---- 7. edge evidence bar ----------------------------------
    edgeEvidenceBar: {
      type: 'edgeEvidenceBar',
      desc: 'Compact evidence panel for a single selected edge in a reasoning chain. Shows the "why does A imply B" citation list.',
      data_hint: 'SELECT tone, text, citation FROM hypothesis_chain_edge_evidence WHERE hypothesis_id=? AND from_node=? AND to_node=? ORDER BY ord.',
      props_schema: {
        edge:     { type: 'object',
          desc: '{ id, from, to, fromLabel?, toLabel? } — surface only; comes from the reasoningChain edges array.' },
        evidence: { type: 'array<{tone(good|warn), text, cite}>', required: true,
          desc: 'Citation rows for this edge.' },
      },
      example: {
        edge: { id: 'v3-m1', from: 'v3', to: 'm1',
                fromLabel: 'Absent dystrophin', toLabel: 'Sarcolemma decouples from ECM' },
        evidence: [
          { tone: 'good', text: 'Dystrophin C-terminal domain binds β-dystroglycan, bridging cytoskeletal actin to sarcolemmal laminin via the DGC.', cite: 'Ervasti & Campbell 1993' },
          { tone: 'good', text: 'In mdx muscle, DGC components dissociate from the sarcolemma.', cite: 'Ohlendieck 1991' },
        ],
      },
      render(p) {
        const rows = (p.evidence || []).map(e => `
          <li class="${e.tone === 'warn' ? 'warn' : ''}">
            <span class="tick">${e.tone === 'warn' ? '!' : '✓'}</span>
            <span>${esc(e.text)}<span class="cite">${esc(e.cite || '')}</span></span>
          </li>`).join('');
        const arrow = (p.edge && (p.edge.fromLabel || p.edge.toLabel))
          ? `<div class="edge-arrow"><b>${esc(p.edge.fromLabel || p.edge.from)}</b> → <b>${esc(p.edge.toLabel || p.edge.to)}</b></div>`
          : '';
        const empty = rows ? '' :
          `<div class="edge-empty">No curated evidence for this edge yet.</div>`;
        return `
        <div class="edge-bar">
          <div class="edge-bar-h">
            <span class="edge-bar-lbl">Edge Evidence</span>
            <span class="edge-bar-eid">${esc(p.edge?.id || '')}</span>
          </div>
          ${arrow}
          ${empty}
          <ul class="evi">${rows}</ul>
        </div>`;
      },
    },

    // ---- 8. heatmap primitive ----------------------------------
    heatmap: {
      type: 'heatmap',
      desc: 'Generic rows × cols shaded-cell grid. Cell colors interpolate over a chosen palette between value_min → value_max. Good for enrichment tables, expression matrices, or any two-axis intensity map.',
      data_hint: 'Provide rows[], cols[], and cells: [{r, c, v}] with r/c indexing into rows/cols. Sparse OK (missing cells render blank).',
      props_schema: {
        title:      { type: 'string' },
        rows:       { type: 'array<string>', required: true, desc: 'Row labels (top to bottom).' },
        cols:       { type: 'array<string>', required: true, desc: 'Column labels (left to right).' },
        cells:      { type: 'array<{r,c,v}>', required: true,
          desc: 'r=row index, c=col index, v=value in [vmin,vmax].' },
        vmin:       { type: 'number', desc: 'Bottom of color scale. Default 0.' },
        vmax:       { type: 'number', desc: 'Top of color scale. Default max(cell.v).' },
        palette:    { type: 'string', desc: '"blue" | "warm" | "diverge". Default "blue".' },
        rowWeight:  { type: 'array<number>', desc: 'Optional per-row weight bar rendered to the right of the grid.' },
        weightLbl:  { type: 'string', desc: 'Header for the weight column.' },
        cellSize:   { type: '{w,h}', desc: 'Cell dims in px. Default {w:32, h:20}.' },
        footer:     { type: 'string' },
      },
      example: {
        title: 'Isoform × cell type (log CPM)',
        rows: ['Dp427m','Dp427c','Dp427p','Dp260','Dp140','Dp116','Dp71'],
        cols: ['Skel myocyte','Cardiomyo','Cortical N','Purkinje','Photorecep','Schwann','Podocyte'],
        cells: [
          {r:0,c:0,v:9.6},{r:0,c:1,v:8.2},{r:0,c:2,v:1.0},{r:0,c:3,v:0.8},{r:0,c:4,v:0.4},{r:0,c:5,v:0.3},{r:0,c:6,v:0.2},
          {r:1,c:0,v:1.1},{r:1,c:1,v:1.0},{r:1,c:2,v:8.4},{r:1,c:3,v:8.6},{r:1,c:4,v:2.1},{r:1,c:5,v:0.4},{r:1,c:6,v:0.3},
          {r:2,c:0,v:0.5},{r:2,c:1,v:0.4},{r:2,c:2,v:3.6},{r:2,c:3,v:2.8},{r:2,c:4,v:0.6},{r:2,c:5,v:0.7},{r:2,c:6,v:0.3},
          {r:3,c:0,v:0.9},{r:3,c:1,v:0.7},{r:3,c:2,v:1.3},{r:3,c:3,v:1.1},{r:3,c:4,v:9.1},{r:3,c:5,v:0.4},{r:3,c:6,v:0.5},
          {r:4,c:0,v:1.6},{r:4,c:1,v:1.4},{r:4,c:2,v:7.9},{r:4,c:3,v:5.5},{r:4,c:4,v:2.4},{r:4,c:5,v:0.8},{r:4,c:6,v:0.6},
          {r:5,c:0,v:0.6},{r:5,c:1,v:0.5},{r:5,c:2,v:1.2},{r:5,c:3,v:0.9},{r:5,c:4,v:0.3},{r:5,c:5,v:8.6},{r:5,c:6,v:1.1},
          {r:6,c:0,v:2.4},{r:6,c:1,v:2.1},{r:6,c:2,v:5.6},{r:6,c:3,v:4.2},{r:6,c:4,v:3.7},{r:6,c:5,v:3.9},{r:6,c:6,v:5.9},
        ],
        vmin: 0, vmax: 10, palette: 'blue',
        rowWeight: [12000, 2400, 800, 620, 460, 380, 220],
        weightLbl: '# path.',
        footer: 'STUB — real cellxgene bake pending',
      },
      render(p) {
        return _renderHeatmap(p);
      },
    },

    // ---- 9. linked heatmap (variants ↔ cell types ↔ pathways) -
    linkedHeatmap: {
      type: 'linkedHeatmap',
      desc: 'Composite: two heatmaps sharing a vertical cell-type axis, with a per-cell-type weight bar between them. Left = variant class × cell type; right = cell type × pathway. Reads left → right along each row: which variant classes hit this cell type, weighted by # pathogenic variants, and which pathways it participates in.',
      data_hint: 'left cells: JOIN clinvar_phenotype (pathogenic subset) → variant_isoform_impact → celltype_expression. right cells: pathway_enrichment JOIN celltype_expression. weight: per-cell-type pathogenic-variant count.',
      props_schema: {
        title:        { type: 'string' },
        cellTypes:    { type: 'array<string>', required: true, desc: 'Shared middle axis (rows for both grids).' },
        variantTypes: { type: 'array<string>', required: true, desc: 'Left grid columns.' },
        pathways:     { type: 'array<string>', required: true, desc: 'Right grid columns.' },
        leftCells:    { type: 'array<{r,c,v}>', required: true, desc: 'r=cellTypes index, c=variantTypes index. v ∈ [0,leftMax].' },
        rightCells:   { type: 'array<{r,c,v}>', required: true, desc: 'r=cellTypes index, c=pathways index. v ∈ [0,rightMax].' },
        weight:       { type: 'array<number>', required: true, desc: '# pathogenic variants per cell type (parallel to cellTypes).' },
        leftMax:      { type: 'number' },
        rightMax:     { type: 'number' },
        footer:       { type: 'string' },
      },
      example: {
        title: 'Variants → cell types → pathways',
        cellTypes:    ['Skeletal myocyte','Cardiomyocyte','Cortical neuron','Purkinje cell','Photoreceptor','Schwann cell','Kidney podocyte'],
        variantTypes: ['Frameshift del','In-frame del','Nonsense','Missense','Splice','Duplication'],
        pathways:     ['Muscle contraction','DGC assembly','Costamere','Ca²⁺ homeostasis','ECM organization','Fibrosis / TGF-β','NMD surveillance'],
        // Left = variant class × cell type (# pathogenic hits, log-ish)
        leftCells: [
          // skeletal myocyte hit by everything, hardest by frameshift dels
          {r:0,c:0,v:9.4},{r:0,c:1,v:6.1},{r:0,c:2,v:7.2},{r:0,c:3,v:3.3},{r:0,c:4,v:5.4},{r:0,c:5,v:4.7},
          // cardiomyocyte: mostly framshift + nonsense (DCM subset)
          {r:1,c:0,v:6.8},{r:1,c:1,v:4.4},{r:1,c:2,v:5.6},{r:1,c:3,v:2.2},{r:1,c:4,v:3.6},{r:1,c:5,v:3.1},
          // cortical neuron: Dp140/Dp71 losing distal-promoter or 5' variants
          {r:2,c:0,v:3.2},{r:2,c:1,v:2.4},{r:2,c:2,v:3.0},{r:2,c:3,v:1.6},{r:2,c:4,v:2.4},{r:2,c:5,v:1.9},
          {r:3,c:0,v:2.9},{r:3,c:1,v:2.1},{r:3,c:2,v:2.7},{r:3,c:3,v:1.4},{r:3,c:4,v:2.0},{r:3,c:5,v:1.7},
          {r:4,c:0,v:2.6},{r:4,c:1,v:1.8},{r:4,c:2,v:2.4},{r:4,c:3,v:1.2},{r:4,c:4,v:1.9},{r:4,c:5,v:1.4},
          {r:5,c:0,v:1.8},{r:5,c:1,v:1.3},{r:5,c:2,v:1.5},{r:5,c:3,v:0.9},{r:5,c:4,v:1.3},{r:5,c:5,v:1.1},
          {r:6,c:0,v:1.4},{r:6,c:1,v:1.1},{r:6,c:2,v:1.2},{r:6,c:3,v:0.7},{r:6,c:4,v:1.0},{r:6,c:5,v:0.8},
        ],
        // Right = cell type × pathway enrichment (-log10 FDR-ish)
        rightCells: [
          {r:0,c:0,v:9.2},{r:0,c:1,v:8.6},{r:0,c:2,v:8.1},{r:0,c:3,v:6.3},{r:0,c:4,v:5.4},{r:0,c:5,v:4.2},{r:0,c:6,v:3.1},
          {r:1,c:0,v:8.4},{r:1,c:1,v:7.9},{r:1,c:2,v:6.6},{r:1,c:3,v:7.7},{r:1,c:4,v:5.1},{r:1,c:5,v:4.4},{r:1,c:6,v:3.0},
          {r:2,c:0,v:2.2},{r:2,c:1,v:1.6},{r:2,c:2,v:1.3},{r:2,c:3,v:4.8},{r:2,c:4,v:2.1},{r:2,c:5,v:2.4},{r:2,c:6,v:4.4},
          {r:3,c:0,v:2.0},{r:3,c:1,v:1.4},{r:3,c:2,v:1.2},{r:3,c:3,v:5.9},{r:3,c:4,v:1.9},{r:3,c:5,v:2.1},{r:3,c:6,v:3.7},
          {r:4,c:0,v:1.3},{r:4,c:1,v:1.0},{r:4,c:2,v:0.9},{r:4,c:3,v:2.6},{r:4,c:4,v:1.7},{r:4,c:5,v:1.9},{r:4,c:6,v:3.3},
          {r:5,c:0,v:1.7},{r:5,c:1,v:1.2},{r:5,c:2,v:1.1},{r:5,c:3,v:2.4},{r:5,c:4,v:2.9},{r:5,c:5,v:2.6},{r:5,c:6,v:2.4},
          {r:6,c:0,v:1.1},{r:6,c:1,v:0.9},{r:6,c:2,v:0.8},{r:6,c:3,v:1.9},{r:6,c:4,v:2.7},{r:6,c:5,v:2.3},{r:6,c:6,v:2.0},
        ],
        weight: [12420, 2680, 940, 720, 510, 420, 260],
        leftMax: 10, rightMax: 10,
        footer: 'STUB — celltype_expression + pathway_enrichment substrate tables still stub. weight is illustrative.',
      },
      render(p) {
        return _renderLinkedHeatmap(p);
      },
    },

    // ---- 10. variant lollipop plot -----------------------------
    variantLollipop: {
      type: 'variantLollipop',
      desc: 'Domain-enrichment / lollipop plot. X = linear coordinate (exon index, nucleotide, or amino acid). Y = phenotype / tissue / pathway categories. Marker size = frequency; color = severity or category. Optional exon-band strip beneath X-axis for gene layout context.',
      data_hint: 'X: parse HGVS position from lovd_variants.position_mrna or clinvar_phenotype.variant_name. Y: clinvar_phenotype.phenotype_label. Size: times_reported / count. Color: ClinicalSignificance bucket.',
      props_schema: {
        title:       { type: 'string' },
        xAxis:       { type: '{min, max, label, ticks?}', required: true,
          desc: 'Coord range on X. `ticks` (optional array of x-positions) draws minor gridlines.' },
        yCategories: { type: 'array<string>', required: true, desc: 'Row labels top-to-bottom.' },
        variants:    { type: 'array<{x,y,r,color,label?}>', required: true,
          desc: 'x = coord, y = index into yCategories, r = circle radius (px), color = CSS color, label = hover text.' },
        exons:       { type: 'array<{n,start,end}>',
          desc: 'Optional exon band strip drawn under X-axis. start/end in the same units as x.' },
        colorLegend: { type: 'array<{label, color}>', desc: 'Rendered top-right.' },
        footer:      { type: 'string' },
      },
      example: (() => {
        // 79 exons in the DMD gene; use exon index as X coord (1..79).
        const exons = Array.from({ length: 79 }, (_, i) => ({ n: i + 1, start: i + 0.6, end: i + 1.4 }));
        // sub-phenotype rows
        const cats = ['DMD (Duchenne)', 'BMD (Becker)', 'IMD (intermediate)', 'DCM (cardiac)', 'Cognitive / CNS'];
        // color palette by severity/category
        const COL = { dmd: '#c94a4a', bmd: '#33a3a3', imd: '#d78a2b', dcm: '#7a5cd6', cog: '#4d96d1' };
        // curated illustrative distribution — hotspot at exons 44-55 (deletion hotspot);
        // secondary hotspot at exons 3-9 (proximal); Dp71 5'-UTR / distal at 63-79
        const V = [];
        const push = (x, y, r, color, label) => V.push({ x, y, r, color, label });
        // DMD (row 0) — big cluster in the 44-55 hotspot, smaller across
        [3,4,5,6,8,9,13,17,22,26,30,34,38,42,44,45,46,47,48,49,50,51,52,53,54,55,56,58,60,62,68,72,76]
          .forEach(x => push(x, 0, 4 + (x >= 44 && x <= 55 ? 6 * Math.random() + 4 : 2 * Math.random() + 1), COL.dmd, `Δexon ${x} · DMD (frameshift)`));
        // BMD (row 1) — sparser, central rod deletions
        [10,13,16,19,25,32,37,45,47,48,52,54,58,63]
          .forEach(x => push(x, 1, 3 + 2 * Math.random(), COL.bmd, `Δexon ${x} · BMD (in-frame)`));
        // IMD (row 2) — thin scatter
        [12,29,45,48,52,55,66].forEach(x => push(x, 2, 3, COL.imd, `Δexon ${x} · IMD`));
        // DCM (row 3) — proximal / 5' variants + a few C-term
        [1,2,3,5,7,10,14,18,29,43,66,74].forEach(x => push(x, 3, 3 + 2 * Math.random(), COL.dcm, `Δexon ${x} · DCM (cardiac)`));
        // Cognitive / CNS (row 4) — distal (Dp140 promoter around ex 45, Dp71 around 63-79)
        [45,46,47,48,52,60,62,63,64,65,66,68,71,74,79]
          .forEach(x => push(x, 4, 3 + 2 * Math.random(), COL.cog, `Δexon ${x} · CNS (Dp140/Dp71 loss)`));
        return {
          title: 'DMD variants by exon × sub-phenotype',
          xAxis: { min: 1, max: 79, label: 'Exon (NM_004006.2, 79 exons)',
                   ticks: [1, 10, 20, 30, 40, 45, 50, 55, 60, 70, 79] },
          yCategories: cats,
          variants: V,
          exons,
          colorLegend: [
            { label: 'DMD (Duchenne)',     color: COL.dmd },
            { label: 'BMD (Becker)',       color: COL.bmd },
            { label: 'IMD (intermediate)', color: COL.imd },
            { label: 'DCM (cardiac)',      color: COL.dcm },
            { label: 'Cognitive / CNS',    color: COL.cog },
          ],
          footer: 'STUB — illustrative distribution highlighting the exon 44-55 deletion hotspot. Real bake will source X + count from ClinVar variant_name parsing.',
        };
      })(),
      render(p) {
        return _renderLollipop(p);
      },
    },

    // ---- 11. exon architecture panel ---------------------------
    exonArchitecturePanel: {
      type: 'exonArchitecturePanel',
      desc: 'Two vertically-aligned panels sharing an exon X-axis. Top: linear gene diagram with protein-domain bands over an exon ruler. Bottom: cell-type × exon PSI (or isoform-inclusion) heatmap, with pathogenic variant dots overlaid on the top of each column. Lets the reader trace a variant\'s exon down to the tissues where that exon is included → tissue-specific phenotype rationale.',
      data_hint: 'domains: curated from UniProt features (e.g. UniProt P11532 for DMD). psi: per-exon PSI from a splicing atlas (e.g. VastDB, ASCOT) OR isoform-inclusion fraction from exon_usage joined with per-cell-type isoform expression. variants: clinvar_phenotype filtered to Pathogenic/Likely_pathogenic, exon parsed from HGVS.',
      props_schema: {
        title:      { type: 'string' },
        exons:      { type: 'array<{n, label?}>', required: true, desc: 'Exon numbers 1..N (order = column order).' },
        domains:    { type: 'array<{start, end, name, color}>', desc: 'Domain bands drawn over the exon ruler. start/end are exon indices (inclusive).' },
        cellTypes:  { type: 'array<{id, label, group?}>', required: true, desc: 'Rows for the heatmap.' },
        psi:        { type: 'array<{exon, cellType, value}>', required: true, desc: 'Sparse cell values in [0,100]. exon = exon number, cellType = cellTypes[i].id.' },
        variants:   { type: 'array<{exon, r, color, label?}>', desc: 'Pathogenic variant dots overlaid at top of columns.' },
        colorLegend:{ type: 'array<{label, color}>' },
        footer:     { type: 'string' },
      },
      example: (() => {
        const exons = Array.from({ length: 79 }, (_, i) => ({ n: i + 1 }));
        // DMD protein domain architecture (aa ranges from UniProt P11532;
        // approximated to exons by dividing 3685 aa evenly across 79 exons)
        const domains = [
          { start:  1, end:  8, name: 'Actin-binding (CH1-CH2)', color: '#4d96d1' },
          { start:  8, end: 30, name: 'Spectrin repeats 1-10',   color: '#7a5cd6' },
          { start: 30, end: 45, name: 'Spectrin repeats 11-18',  color: '#8f6dd9' },
          { start: 45, end: 63, name: 'Spectrin repeats 19-24',  color: '#a37ede' },
          { start: 63, end: 65, name: 'WW',                       color: '#33a3a3' },
          { start: 65, end: 68, name: 'EF-hand',                  color: '#2b9d6c' },
          { start: 68, end: 70, name: 'ZZ (β-DG bind)',           color: '#d78a2b' },
          { start: 70, end: 79, name: 'Cys-rich / C-term',        color: '#c94a4a' },
        ];
        const cellTypes = [
          { id: 'vcm',  label: 'Ventricular cardiomyocyte', group: 'Cardiac'  },
          { id: 'acm',  label: 'Atrial cardiomyocyte',      group: 'Cardiac'  },
          { id: 'fcm',  label: 'Fetal cardiomyocyte',       group: 'Cardiac'  },
          { id: 'skm',  label: 'Adult skeletal myocyte',    group: 'Skeletal' },
          { id: 'fskm', label: 'Fetal skeletal myocyte',    group: 'Skeletal' },
          { id: 'cn',   label: 'Cortical neuron',           group: 'CNS'      },
          { id: 'pk',   label: 'Cerebellar Purkinje cell',  group: 'CNS'      },
          { id: 'phot', label: 'Photoreceptor (retina)',    group: 'Retina'   },
          { id: 'schw', label: 'Schwann cell',              group: 'PNS'      },
          { id: 'pod',  label: 'Kidney podocyte',           group: 'Renal'    },
        ];
        // DMD isoform biology as a PSI story: promoters at exon 1 (Dp427m/c/p),
        // exon 30 (Dp260), exon 45 (Dp140), exon 63 (Dp71). Muscle uses Dp427m
        // full-length; retina adds Dp260 (30-79); CNS uses Dp140 (45-79);
        // ubiquitous Dp71 (63-79). Encoded as per-cell-type inclusion pattern.
        const RAMP = (start) => (e) => e < start ? 10 + Math.random() * 15 : 82 + Math.random() * 12;
        const patterns = {
          vcm:  RAMP( 1),  acm:  RAMP( 1),  fcm:  RAMP( 1),
          skm:  RAMP( 1),  fskm: RAMP( 1),
          phot: RAMP(30),
          cn:   RAMP(45),  pk:   RAMP(45),
          schw: RAMP(63),  pod:  RAMP(63),
        };
        const psi = [];
        cellTypes.forEach(ct => {
          const fn = patterns[ct.id];
          exons.forEach(({ n }) => psi.push({ exon: n, cellType: ct.id, value: Math.round(fn(n)) }));
        });
        // Pathogenic variants — hotspot at 44-55 + a few in ZZ (68-70) + N-term
        const V = [];
        const push = (exon, r, color, label) => V.push({ exon, r, color, label });
        [3, 7, 13, 22, 43].forEach(e => push(e, 3, '#c94a4a', `c.exon ${e} · frameshift del (proximal)`));
        [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55].forEach(e => push(e, 3.5, '#c94a4a', `Δexon ${e} · frameshift del (hotspot)`));
        [46, 48, 51, 52, 54].forEach(e => push(e, 2.5, '#33a3a3', `Δexon ${e} · in-frame del (BMD)`));
        [68, 69, 70].forEach(e => push(e, 3, '#d78a2b', `c.exon ${e} · β-DG binding disruption`));
        [72, 76].forEach(e => push(e, 3, '#c94a4a', `c.exon ${e} · nonsense (C-term)`));
        return {
          title: 'DMD exon architecture × tissue-specific inclusion',
          exons, domains, cellTypes, psi, variants: V,
          colorLegend: [
            { label: 'Frameshift (DMD)', color: '#c94a4a' },
            { label: 'In-frame (BMD)',   color: '#33a3a3' },
            { label: 'β-DG binding',     color: '#d78a2b' },
          ],
          footer: 'STUB — PSI matrix uses DMD promoter-driven isoform pattern (Dp427/Dp260/Dp140/Dp71 cascade) rather than true alternative splicing. Real bake will source PSI from VastDB / ASCOT and variants from ClinVar Pathogenic subset.',
        };
      })(),
      render(p) {
        return _renderExonArchitecture(p);
      },
    },

    // ---- 12. hypothesis detail card ----------------------------
    hypothesisDetail: {
      type: 'hypothesisDetail',
      desc: 'Full evidence pack for one hypothesis: lede + supporting-evidence bullet list + reasoning-chain SVG. When selectedEdgeId is set, embeds the edgeEvidenceBar for that edge under the chain.',
      data_hint: 'Compose from hypotheses + hypothesis_evidence + reasoningChain payload + hypothesis_chain_edge_evidence for the selected edge.',
      props_schema: {
        hypothesis:     { type: 'object', required: true,
          desc: 'Row from hypothesisTable, plus .detail = { lede, evidence: [{tone(good|warn), text, cite}], chain }' },
        selectedEdgeId: { type: 'string', desc: 'When set, highlights the edge in the chain + shows the edgeEvidenceBar below it.' },
      },
      example: {
        hypothesis: {
          id: '01', name: 'Out-of-frame deletions', evidence: 9.4, druggability: 4, supporting: 18204,
          detail: {
            lede: 'Most severe DMD variants are large deletions that disrupt the reading frame, producing a truncated protein that fails to anchor the dystrophin-glycoprotein complex to the sarcolemma.',
            evidence: [
              { tone: 'good', text: '75% of pathogenic ClinVar variants are frameshift or nonsense', cite: 'ClinVar 2026-07' },
              { tone: 'good', text: 'Monaco rule holds in 92% of cases',                              cite: 'Monaco 1988; Aartsma-Rus 2006' },
              { tone: 'warn', text: 'Δexon 5 is an in-frame exception with severe DMD phenotype',    cite: 'Winnard 1995' },
            ],
            chain: null,
          },
        },
      },
      render(p) {
        const h = p.hypothesis;
        const selectedEdgeId = p.selectedEdgeId || null;
        if (!h || !h.detail) {
          return `<div class="panel" style="margin-top:16px;color:var(--ink-3);font-style:italic;">
                    Select a hypothesis with a detail payload to see its evidence pack.</div>`;
        }
        const evi = h.detail.evidence.map(e => `
          <li class="${e.tone === 'warn' ? 'warn' : ''}">
            <span class="tick">${e.tone === 'warn' ? '!' : '✓'}</span>
            <span>${esc(e.text)}<span class="cite">${esc(e.cite)}</span></span>
          </li>`).join('');
        const chainHtml = h.detail.chain
          ? WIDGETS.reasoningChain.render({ chain: h.detail.chain, selectedEdgeId })
          : `<div style="color:var(--ink-3);font-style:italic;">No chain payload.</div>`;
        // Edge evidence bar (only when an edge is selected + resolvable in chain)
        let edgeBar = '';
        if (h.detail.chain && selectedEdgeId) {
          const chain = h.detail.chain;
          const edge = chain.edges.find(e => (e.id || `${e.from}-${e.to}`) === selectedEdgeId);
          if (edge) {
            const byId = Object.fromEntries(chain.nodes.map(n => [n.id, n]));
            const lbl = (id) => {
              const n = byId[id]; if (!n) return id;
              return [n.label1, n.label2].filter(Boolean).join(' ').trim();
            };
            edgeBar = WIDGETS.edgeEvidenceBar.render({
              edge: { id: edge.id || `${edge.from}-${edge.to}`,
                      from: edge.from, to: edge.to,
                      fromLabel: lbl(edge.from), toLabel: lbl(edge.to) },
              evidence: edge.evidence || [],
            });
          }
        }
        const chainSubH = h.detail.chain
          ? `<div class="sub-h">Reasoning Chain <span style="color:var(--ink-3);font-weight:400;text-transform:none;letter-spacing:0;font-size:11px;">— click an arrow for edge evidence</span></div>`
          : `<div class="sub-h">Reasoning Chain</div>`;
        return `
        <div class="panel" style="margin-top: 16px;">
          <div class="panel-h">
            <div><span class="detail-title">Hypothesis #${esc(h.id)}</span>
                 <span class="detail-tag">Selected</span></div>
            <div class="hint">Evidence ${h.evidence.toFixed(1)} · ${h.druggability}/5 druggability · ${fmtInt(h.supporting)} supporting variants</div>
          </div>
          <div class="detail-lede">${esc(h.detail.lede)}</div>
          <div class="detail">
            <div>
              <div class="sub-h">Supporting Evidence</div>
              <ul class="evi">${evi}</ul>
            </div>
            <div>
              ${chainSubH}
              ${chainHtml}
              ${edgeBar}
            </div>
          </div>
        </div>`;
      },
    },

  };

  // ============================================================
  //  M I S S I N G   —  the LLM knows these don't exist yet.
  // ============================================================
  const WIDGETS_TODO = [
    { type: 'exonMap',
      desc: 'Horizontal 79-exon strip; caller passes highlighted exon ranges + colors. Good for showing a variant\'s span.',
      data_hint: 'Position from lovd_variants.hgvs or clinvar_phenotype.variant_name; exon phasing from exon_usage.',
      blocking: 'Need to build the exon-coord → x-position mapping.' },
    { type: 'isoformRibbon',
      desc: '7-lane isoform track. Each lane is one isoform (Dp427m … Dp71); marks show where the variant intersects.',
      data_hint: 'JOIN exon_usage ON exon; mark lane if used=1 for that exon.',
      blocking: 'Need per-isoform first-exon start (partially in isoforms.first_shared_exon).' },
    { type: 'frameShiftBadge',
      desc: 'Small pill widget: computes in-frame / out-of-frame from a deletion span; shows Monaco-rule prediction (DMD vs BMD).',
      data_hint: 'Sum exon lengths across deleted range; mod 3.',
      blocking: 'Need per-exon length table (currently only have used/not-used).' },
    { type: 'variantEvidenceCard',
      desc: 'Per-variant composite card: HGVS, ClinVar significance, LOVD reports, isoformRibbon, frameShiftBadge, nearby-variant phenotype summary.',
      data_hint: 'Composition of several existing + missing widgets around one variant ID.',
      blocking: 'Depends on exonMap + isoformRibbon + frameShiftBadge.' },
  ];

  // ============================================================
  //  E X P O R T
  // ============================================================
  root.WIDGETS      = WIDGETS;
  root.WIDGETS_TODO = WIDGETS_TODO;

  // Small helper: LLM-facing catalog — one JSON blob describing all
  // widgets and their schemas (no render fn).
  root.WIDGET_CATALOG = () => ({
    widgets: Object.values(WIDGETS).map(w => ({
      type: w.type, desc: w.desc, data_hint: w.data_hint,
      props_schema: w.props_schema, example_props: w.example,
    })),
    todo: WIDGETS_TODO,
  });

})(typeof window !== 'undefined' ? window : globalThis);
