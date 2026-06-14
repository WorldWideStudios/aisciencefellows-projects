from __future__ import annotations

from typing import Any

import requests


API_URL = "https://clinicaltrials.gov/api/v2/studies"
ALLOWED_STATUSES = {
    "RECRUITING",
    "COMPLETED",
    "ACTIVE_NOT_RECRUITING",
    "ALL",
}


def _cap(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def search_trials(
    condition: str,
    status: str = "RECRUITING",
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Search ClinicalTrials.gov for studies by condition and recruitment status."""
    normalized_status = (status or "RECRUITING").strip().upper()
    if normalized_status not in ALLOWED_STATUSES:
        normalized_status = "RECRUITING"

    params: dict[str, Any] = {
        "query.cond": condition,
        "pageSize": max_results,
    }
    if normalized_status != "ALL":
        params["filter.overallStatus"] = normalized_status

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    studies = payload.get("studies", [])
    results: list[dict[str, Any]] = []

    for study in studies[:max_results]:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        description = protocol.get("descriptionModule", {})
        conditions_module = protocol.get("conditionsModule", {})

        nct_id = identification.get("nctId", "")
        title = identification.get("briefTitle", "")
        phase_list = design.get("phases", []) or []
        phase = ", ".join(phase_list) if phase_list else "N/A"

        overall_status = status_module.get("overallStatus", "")
        start_date = (status_module.get("startDateStruct", {}) or {}).get("date", "")
        enrollment_info = design.get("enrollmentInfo", {}) or {}
        enrollment = enrollment_info.get("count", None)
        brief = _cap(description.get("briefSummary", ""), 300)

        results.append(
            {
                "nct_id": nct_id,
                "title": title,
                "phase": phase,
                "status": overall_status,
                "start_date": start_date,
                "enrollment": enrollment,
                "brief_summary": brief,
                "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
                "condition": ", ".join(conditions_module.get("conditions", []) or []),
            }
        )

    return results
