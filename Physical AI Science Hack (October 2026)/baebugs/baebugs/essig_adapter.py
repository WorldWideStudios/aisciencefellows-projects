"""Essig Museum adapters -> FCOs -> context for the vision model.

Three sources, each its own FCO:
  * essigdb home (https://essigdb.berkeley.edu/)          - collection overview
  * gaps page   (https://essigdb.berkeley.edu/gaps.html)   - what the collection lacks
  * label tool  (https://essigdb.berkeley.edu/cgi/eme_label?form=yes)
        collecting-event labels: lat/long, locality, collector, ecology, date
        identification labels:   sci. name, author, det. by
        specimen-number labels:  EMEC number
plus the GBIF copy of the collection (dataset 5d283bb6-...) for structured records.

Access rules: the home and gaps pages disallow automated fetching (robots.txt),
so their adapters parse a page YOU saved from a browser; nothing here scrapes
them. Live fetches go through `polite_get`, which checks robots.txt first and
returns a 'blocked' FCO instead of working around a refusal.

Gap filling, in order: Essig label text -> GBIF record -> label read from the
specimen image by a vision model (Claude) -> 'unknown'. Hybridization records
which source supplied each field and every disagreement between sources.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path

from .fco import FCO, hybridize

ESSIG = "https://essigdb.berkeley.edu"
PAGES = {"home": f"{ESSIG}/", "gaps": f"{ESSIG}/gaps.html",
         "label": f"{ESSIG}/cgi/eme_label?form=yes"}
UA = "baebugs/0.1 (+https://github.com/biobitworks/baebugs)"


def polite_get(url: str, timeout=30) -> tuple[str | None, str]:
    rp = urllib.robotparser.RobotFileParser()
    parts = urllib.parse.urlsplit(url)
    rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        rp.read()
        if not rp.can_fetch(UA, url):
            return None, "blocked"
    except Exception:  # noqa: BLE001,S110 - best-effort, nothing to record
        pass  # robots unreachable -> proceed as a normal browser would
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), "observed"


def _text(page_html: str) -> str:
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", page_html)
    t = re.sub(r"(?s)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", t)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    return "\n".join(l.strip() for l in t.splitlines() if l.strip())


# ---------- page FCOs ----------

def page_fco(name: str, saved_html_path: str | None = None, live=False) -> FCO:
    url = PAGES[name]
    if saved_html_path:
        txt = _text(Path(saved_html_path).read_text(errors="replace"))
        status = "observed"
    elif live:
        raw, status = polite_get(url)
        txt = _text(raw) if raw else ""
    else:
        txt, status = "", "unknown"
    fields = {"url": url, "text": txt[:20000]}
    if name == "home":
        m = re.search(r"([\d,]{5,})\s+(?:specimen\s+)?records", txt, re.IGNORECASE)
        fields["record_count"] = int(m.group(1).replace(",", "")) if m else None
        fields["links"] = re.findall(r"https?://\S+", txt)[:200]
    if name == "gaps":
        fields["gap_items"] = parse_gaps(txt)
    return FCO(f"essig_page:{name}", url, fields, status=status if txt else
               ("blocked" if status == "blocked" else "unknown"))


def parse_gaps(text: str) -> list[str]:
    """Taxon/region names listed as collection gaps. Heuristic: list-like lines
    with a capitalised first word (Order/Family/genus or place names)."""
    items = []
    for line in text.splitlines():
        line = line.strip(" -•*\t")
        if 2 < len(line) < 120 and re.match(r"^[A-Z][a-zA-Z\-]+", line) and \
                not re.search(r"(?i)copyright|essig museum|email|back to", line):
            items.append(line)
    return items


# ---------- label FCOs ----------

LABEL_PATTERNS = {
    "lat_long": r"(-?\d{1,2}\.\d+)\s*[,;]?\s*(-?\d{1,3}\.\d+)",
    "date": r"\b(\d{1,2}[\s\-\.]?[IVX]{1,4}[\s\-\.]?\d{2,4}|\d{1,2}\s+[A-Z][a-z]{2}\.?\s+\d{4}|\d{4}-\d{2}-\d{2})\b",
    "collector": r"(?i)\b(?:coll\.?|leg\.?|col\.?)\s*[:.]?\s*([A-Z][\w.\-' ]{2,40})",
    "det_by": r"(?i)\bdet\.?\s*(?:by)?\s*[:.]?\s*([A-Z][\w.\-' ]{2,40})",
    "specimen_no": r"\b(EMEC\d{3,8})\b",
    "elevation": r"(?i)\b(\d{2,4})\s*(m|ft)\b",
    "method": r"(?i)\b(malaise|pitfall|sweep|beat(?:ing)?|light trap|uv light|berlese|pan trap|net|hand)\b",
}


def parse_label(text: str) -> dict:
    out = {}
    for k, pat in LABEL_PATTERNS.items():
        m = re.search(pat, text)
        if m:
            out[k] = [float(m.group(1)), float(m.group(2))] if k == "lat_long" else m.group(1).strip()
    lines = [l for l in text.splitlines() if l.strip()]
    if lines:
        out.setdefault("locality", lines[0][:160])
    return out


def label_fco(label_text: str, specimen_no: str | None = None, source="essig:eme_label") -> FCO:
    f = parse_label(label_text)
    if specimen_no:
        f["specimen_no"] = specimen_no
    f["raw"] = label_text
    return FCO("essig_label", source, f)


def gbif_fco(record: dict) -> FCO:
    """FCO from one GBIF occurrence (Essig dataset). Fetch with
    calbug._get('occurrence/search', datasetKey=..., catalogNumber='EMEC...')."""
    keep = ["catalogNumber", "scientificName", "order", "family", "genus",
            "stateProvince", "county", "locality", "decimalLatitude", "decimalLongitude",
            "eventDate", "recordedBy", "identifiedBy", "preparations", "lifeStage",
            "habitat", "samplingProtocol", "individualCount"]
    f = {k: record.get(k) for k in keep if record.get(k) not in (None, "")}
    if "catalogNumber" in f:
        f["specimen_no"] = f["catalogNumber"]
    if "decimalLatitude" in f and "decimalLongitude" in f:
        f["lat_long"] = [f["decimalLatitude"], f["decimalLongitude"]]
    return FCO("gbif_record", f"gbif:{record.get('key', '?')}", f, license=record.get("license"))


def vision_label_fco(fields: dict, model: str, image_sha: str) -> FCO:
    """Fields read off a specimen-label photo by a vision model. Status
    'inferred' so it never outranks the museum's own record."""
    return FCO("vision_label", f"{model}:{image_sha[:16]}", fields, status="inferred")


def read_label_with_claude(image_bgr, model=None) -> dict:
    """OCR + structure a pinned-specimen label via Claude (optional)."""
    import base64
    import os

    import anthropic
    import cv2
    _ok, buf = cv2.imencode(".jpg", image_bgr)
    msg = anthropic.Anthropic().messages.create(
        model=model or os.environ.get("BAEBUGS_CLAUDE_MODEL", "claude-opus-5-5"),
        max_tokens=600, messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.b64encode(buf.tobytes()).decode()}},
            {"type": "text", "text": "Transcribe this insect specimen label. Reply JSON only with keys "
             "locality, lat_long [lat,lon], date, collector, method, elevation, det_by, specimen_no, "
             "scientificName. Use null when unreadable; never guess."}]}])
    t = msg.content[0].text
    return json.loads(t[t.find("{"): t.rfind("}") + 1])


# ---------- context for the vision model ----------

PRIORITY = ["vision_label", "gbif_record", "essig_label"]  # last = highest priority


def specimen_context(*fcos: FCO, gaps: FCO | None = None) -> FCO:
    ctx = hybridize("specimen_context", *fcos, prefer=PRIORITY)
    if gaps and gaps.fields.get("gap_items"):
        taxa = {str(ctx.fields.get(k, "")).lower() for k in ("order", "family", "genus", "scientificName")}
        hits = [g for g in gaps.fields["gap_items"] if any(t and t in g.lower() for t in taxa)]
        ctx.fields["collection_gap_hits"] = hits
        ctx.fields["gap_novelty_boost"] = bool(hits)
        ctx.parents.append(gaps.id)
    f = ctx.fields   # map sampling-event vocab onto specimen vocab
    if "date" not in f and f.get("sampled_at"):
        f["date"] = f["sampled_at"]
    if "method" not in f and f.get("sample_type"):
        f["method"] = f["sample_type"]
    wanted = ["family", "scientificName", "lat_long", "date", "method", "preparations", "lifeStage"]
    ctx.fields["missing"] = [k for k in wanted if k not in ctx.fields]
    return ctx


def vision_prompt_context(ctx: FCO) -> str:
    """Compact grounding text for the Claude QA step / any VLM."""
    f = ctx.fields
    keys = ["scientificName", "family", "order", "lifeStage", "preparations", "method",
            "sample_type", "habitat_type", "soil_moisture", "ecoregion", "locality", "county",
            "date", "prep_hint", "collection_gap_hits", "missing"]
    lines = [f"{k}: {f[k]}" for k in keys if f.get(k) not in (None, [], "")]
    return f"Specimen context (FCO {ctx.id[:16]}):\n" + "\n".join(lines)
