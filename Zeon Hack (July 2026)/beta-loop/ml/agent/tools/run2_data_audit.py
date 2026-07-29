"""Agent tool: audit scattered Run 2 data and recommend consolidation."""

from __future__ import annotations

from typing import Any

from analysis.run2_data_audit import audit_run2_data, write_audit_report


def audit_run2_data_tool(write_report: bool = True) -> dict[str, Any]:
    """Scan the repo for disorganized Run 2 artifacts and recommend moves.

    Checks ``data/screens/2/post-run/``, ``pvjthomas/output/``,
    ``data/screens/2/v5/``, mastermix platereader captures) against the canonical
    Run 2 post-run layout under ``data/screens/2/post-run/``.

    Does **not** move files — returns structured recommendations only.

    Args:
        write_report: If True, write ``DATA_ORGANIZATION_AUDIT.md`` and
            ``data_organization_audit.json`` under post-run/.
    """
    report = audit_run2_data()
    out: dict[str, Any] = report.to_dict()
    out["status"] = "ok"

    if write_report:
        md_path = write_audit_report(report)
        out["report_path"] = str(md_path)

    out["recommendation_summary"] = (
        f"{len(report.move_recommendations)} file(s) recommended for post-run/; "
        f"{len(report.missing_for_decision_tree)} missing for decision-tree analysis; "
        f"see report for keep/dedupe/archive items"
    )
    return out
