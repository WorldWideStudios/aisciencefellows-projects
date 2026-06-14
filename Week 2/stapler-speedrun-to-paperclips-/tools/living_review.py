from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Bio import Entrez
from dotenv import load_dotenv


load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DB_DIR = ROOT / "review_db"
DB_PATH = DB_DIR / "topics.db"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _configure_entrez() -> None:
    Entrez.email = os.getenv("NCBI_EMAIL", "")
    api_key = os.getenv("NCBI_API_KEY", "").strip()
    if api_key:
        Entrez.api_key = api_key


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = _db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                last_checked_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                pmid TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                UNIQUE(topic_id, pmid),
                FOREIGN KEY(topic_id) REFERENCES topics(id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _search_pubmed_pmids(query: str, max_results: int = 50) -> list[str]:
    _configure_entrez()
    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=max_results,
        sort="pub+date",
    )
    data = Entrez.read(handle)
    handle.close()
    return [str(pmid) for pmid in data.get("IdList", [])]


def _fetch_pubmed_summaries(pmids: list[str]) -> list[dict[str, Any]]:
    if not pmids:
        return []

    _configure_entrez()
    handle = Entrez.esummary(db="pubmed", id=",".join(pmids), retmode="xml")
    summaries = Entrez.read(handle)
    handle.close()

    papers: list[dict[str, Any]] = []
    for item in summaries:
        pmid = str(item.get("Id", ""))
        papers.append(
            {
                "pmid": pmid,
                "title": str(item.get("Title", "")),
                "journal": str(item.get("FullJournalName", "")),
                "year": str(item.get("PubDate", ""))[:4],
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    return papers


def track_topic(query: str, label: str, max_results: int = 50) -> dict[str, Any]:
    """Track a PubMed topic by creating a baseline snapshot of currently seen papers."""
    _init_db()
    conn = _db()

    try:
        existing = conn.execute(
            "SELECT id, label, query FROM topics WHERE query = ? OR label = ?",
            (query, label),
        ).fetchone()
        if existing:
            return {
                "message": "This topic is already being tracked.",
                "label": existing["label"],
                "query": existing["query"],
            }

        pmids = _search_pubmed_pmids(query, max_results=max_results)
        now = _now_iso()

        cur = conn.execute(
            "INSERT INTO topics (query, label, created_at, last_checked_at) VALUES (?, ?, ?, ?)",
            (query, label, now, now),
        )
        topic_id = cur.lastrowid

        for pmid in pmids:
            conn.execute(
                "INSERT OR IGNORE INTO seen_papers (topic_id, pmid, first_seen_at) VALUES (?, ?, ?)",
                (topic_id, pmid, now),
            )

        conn.commit()
        return {
            "message": "Topic tracking started.",
            "label": label,
            "query": query,
            "baseline_papers_recorded": len(pmids),
            "tracked_at": now,
        }
    finally:
        conn.close()


def check_topic(label: str, max_results: int = 50) -> dict[str, Any]:
    """Check a tracked topic for newly published PubMed papers since last check."""
    _init_db()
    conn = _db()

    try:
        topic = conn.execute(
            "SELECT id, label, query, last_checked_at FROM topics WHERE label = ?",
            (label,),
        ).fetchone()
        if not topic:
            return {
                "error": f"No tracked topic found with label '{label}'.",
                "hint": "Use track_topic(query, label) first.",
            }

        topic_id = int(topic["id"])
        query = str(topic["query"])
        old_last_checked = str(topic["last_checked_at"])

        current_pmids = _search_pubmed_pmids(query, max_results=max_results)
        seen_rows = conn.execute(
            "SELECT pmid FROM seen_papers WHERE topic_id = ?",
            (topic_id,),
        ).fetchall()
        seen_pmids = {str(row["pmid"]) for row in seen_rows}

        new_pmids = [pmid for pmid in current_pmids if pmid not in seen_pmids]
        new_papers = _fetch_pubmed_summaries(new_pmids)

        now = _now_iso()
        for pmid in new_pmids:
            conn.execute(
                "INSERT OR IGNORE INTO seen_papers (topic_id, pmid, first_seen_at) VALUES (?, ?, ?)",
                (topic_id, pmid, now),
            )

        conn.execute(
            "UPDATE topics SET last_checked_at = ? WHERE id = ?",
            (now, topic_id),
        )
        conn.commit()

        if not new_papers:
            return {
                "topic_label": label,
                "last_checked_at": old_last_checked,
                "checked_at": now,
                "new_papers_count": 0,
                "message": "No new papers found. The literature snapshot is up to date.",
                "new_papers": [],
            }

        return {
            "topic_label": label,
            "last_checked_at": old_last_checked,
            "checked_at": now,
            "new_papers_count": len(new_papers),
            "new_papers": new_papers,
        }
    finally:
        conn.close()


def list_tracked_topics() -> list[dict[str, Any]] | dict[str, str]:
    """List all tracked topics with timestamps and total seen paper counts."""
    _init_db()
    conn = _db()

    try:
        rows = conn.execute(
            """
            SELECT
                t.label,
                t.query,
                t.created_at,
                t.last_checked_at,
                COUNT(sp.id) AS seen_papers
            FROM topics t
            LEFT JOIN seen_papers sp ON sp.topic_id = t.id
            GROUP BY t.id
            ORDER BY t.created_at DESC
            """
        ).fetchall()

        if not rows:
            return {
                "message": "No tracked topics yet. Call track_topic(query, label) to start."
            }

        return [
            {
                "label": str(row["label"]),
                "query": str(row["query"]),
                "created_at": str(row["created_at"]),
                "last_checked_at": str(row["last_checked_at"]),
                "seen_papers": int(row["seen_papers"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def untrack_topic(label: str) -> dict[str, str]:
    """Remove a tracked topic and all associated seen-paper records."""
    _init_db()
    conn = _db()

    try:
        topic = conn.execute("SELECT id, label FROM topics WHERE label = ?", (label,)).fetchone()
        if not topic:
            return {
                "error": f"No tracked topic found with label '{label}'.",
            }

        topic_id = int(topic["id"])
        conn.execute("DELETE FROM seen_papers WHERE topic_id = ?", (topic_id,))
        conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        conn.commit()

        return {
            "message": "Topic untracked successfully.",
            "label": label,
        }
    finally:
        conn.close()


_init_db()
