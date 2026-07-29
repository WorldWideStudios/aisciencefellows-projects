"""Let the agents read a protocol document — a dosing table, a dilution scheme,
a kit insert — instead of planning only from the constants baked into
`plan_agent.py`.

Deliberately a *reader*, not a parser. Extracting "which column is enzyme_vol"
from an arbitrary lab PDF is exactly the kind of thing the LLM is good at and a
regex is not; what must not be left to the LLM is whether the transcribed numbers
are physically runnable. So the split is:

    read_document()  -> text, verbatim, for the model to read
    plan_agent.plan_kinetics_round_by_volume() -> validates every number it's
                                                  handed against the pipette's
                                                  real limits before it becomes a
                                                  workflow default

A model that misreads a row gets a raised error naming the offending leg, not a
plate that pipettes 14 uL with a 10 uL pipette.
"""

from __future__ import annotations

from pathlib import Path

# Text formats worth handing to a model verbatim. Anything else (a mesh, a
# spreadsheet binary) needs its own converter and shouldn't be guessed at.
READABLE_SUFFIXES = {".pdf", ".txt", ".md", ".csv", ".json", ".yaml", ".yml"}

# A protocol doc is a handful of pages. Well past that and something's wrong with
# the path, and a whole book would swamp the model's context.
MAX_CHARS = 200_000


class DocumentError(RuntimeError):
    """The document can't be read as text. Raised, not returned."""


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on the env
        raise DocumentError(
            "reading PDFs needs pypdf — run `uv add pypdf` in the project root"
        ) from exc

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        pages.append(f"=== page {i} ===\n{page.extract_text() or ''}")
    text = "\n\n".join(pages)
    if not text.strip():
        raise DocumentError(
            f"{path.name} has no extractable text — it's probably a scan. "
            "The numbers would have to be read off the image or retyped by hand."
        )
    return text


def read_document(path: str) -> dict:
    """Return the text of a protocol document, plus what it took to get it."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise DocumentError(f"no file at {p}")
    suffix = p.suffix.lower()
    if suffix not in READABLE_SUFFIXES:
        raise DocumentError(
            f"can't read {suffix or 'a file with no extension'} as text "
            f"(supported: {', '.join(sorted(READABLE_SUFFIXES))})"
        )

    text = _read_pdf(p) if suffix == ".pdf" else p.read_text(errors="replace")
    truncated = len(text) > MAX_CHARS
    return {
        "path": str(p),
        "format": suffix.lstrip("."),
        "characters": len(text),
        "truncated": truncated,
        "text": text[:MAX_CHARS],
    }
