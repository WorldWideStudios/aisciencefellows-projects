import marimo

__generated_with = "0.23.15"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import sys
    from pathlib import Path

    import marimo as mo

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
    import beads_writer as bw

    INPUTS_DIR = PROJECT_ROOT / "inputs"
    return INPUTS_DIR, bw, json, mo


@app.cell
def _(mo):
    mo.md("""
    # Approve

    Rounds that passed Simulate and are waiting on a human go/no-go before the
    operator runs anything in the Zeon app. Approving here creates a beads
    human gate, resolves it, and moves the round to `stage=approved` — it does
    **not** run the workflow. You still take the printed input values into the
    Zeon app's run-setup canvas yourself.
    """)
    return


@app.cell
def _(bw, mo):
    candidates = bw.list_rounds(stage="simulated")
    round_picker = mo.ui.dropdown(
        options={f"{r['id']} — {r['title']}": r["id"] for r in candidates},
        label="Round awaiting approval",
    )
    mo.vstack([mo.md(f"**{len(candidates)}** round(s) simulated and awaiting approval."), round_picker])
    return (round_picker,)


@app.cell
def _(INPUTS_DIR, bw, json, mo, round_picker):
    if not round_picker.value:
        mo.stop(True, mo.md("Pick a round above to review it."))

    round_id = round_picker.value
    detail = bw.show_round(round_id)

    preset_path = INPUTS_DIR / f"{round_id}.json"
    preset = json.loads(preset_path.read_text()) if preset_path.exists() else None

    mo.vstack(
        [
            mo.md(f"## {round_id} — {detail.get('title', '')}"),
            mo.md(f"assay: `{detail.get('_assay_type', '?')}` · stage: `{detail.get('_stage', '?')}`"),
            mo.md("### Input preset") if preset else mo.md("_No input preset on disk for this round (e.g. a cfps_expression round — set up via the Zeon app's own canvas instead)._"),
            mo.plain_text(json.dumps(preset, indent=2)) if preset else mo.md(""),
        ]
    )
    return (round_id,)


@app.cell
def _(mo):
    approve_button = mo.ui.run_button(label="Approve")
    reject_button = mo.ui.run_button(label="Reject")
    reason = mo.ui.text(label="Reason (recorded either way)", placeholder="looks right / needs another look because...")
    mo.vstack([reason, mo.hstack([approve_button, reject_button])])
    return approve_button, reason, reject_button


@app.cell
def _(approve_button, bw, mo, reason, reject_button, round_id):
    if approve_button.value:
        gate_id = bw.create_human_gate(round_id, reason=reason.value or "operator approved")
        bw.resolve_gate(gate_id, reason=reason.value or "approved via marimo")
        bw.set_stage(round_id, "approved", reason=reason.value or "operator approved")
        mo.md(f"✅ **{round_id} approved.** Take the input preset above into the Zeon app's run-setup canvas and press Run there.")
    elif reject_button.value:
        bw.set_stage(round_id, "deviated", reason=reason.value or "operator rejected")
        mo.md(f"❌ **{round_id} rejected** — logged to beads as deviated. Re-plan with different conditions.")
    else:
        mo.md("_Waiting for Approve or Reject._")
    return


if __name__ == "__main__":
    app.run()
