# watch_agent_run

Tools for reading what an agent actually did, out of the log it already writes.

Claude Code appends every tool call and every result to a session `.jsonl`. That file
is a complete, ordered, append-only record of a run — and it is unreadable. These
scripts turn it into things a person can look at, without a model in the loop.

Nothing here interprets. Every column, square, and count is either a verbatim
substring of the log or a number derived by structural parsing. If you want a
human-readable *interpretation* of a result, that is a separate layer this repo
deliberately does not provide.

**Video walkthrough:** [`watch_agent_run_demo.mov`](https://github.com/drjlgross/watch_agent_run/releases/download/v0.1/watch_agent_run_demo.mov) — the loop end to end, on a real run. (Hosted as a release asset; too large for the repo tree.)

---

## Why

An agent's own summary of a long run is not a reliable account of it. It is
generated from the same context that produced the work, and it will describe
what the agent believes it did. Sometimes that matches. There is no way to
tell which case you are in by reading the summary.

The log is the only record not written by the part of the system you are
checking. These scripts make it cheap enough to read that you actually will.

---

## The loop

Two commands per run, with the agent session in between.

```bash
./infra/newrun.sh 3                 # scaffold run_3/
cd run_3 && claude                  # paste the prompt, let it work, exit
cd .. && ./infra/finishrun.sh 3     # pull the log, render everything
```

`newrun.sh` creates the folder with a prompt stub, a runtime stub, and an
environment snapshot taken *now* — server, CLI version, skill file size — so the
run's conditions are recorded before they drift. Add a suffix for variants:
`./infra/newrun.sh 3 no_search` makes `run_3_no_search/`.

`finishrun.sh` finds the session log, copies it into the run folder verbatim, and
runs every reader over it.

Both scripts need the executable bit on a fresh clone: `chmod +x infra/*.sh`.

---

## What lands in a run folder

| file | from | what it tells you |
|---|---|---|
| `session_N.jsonl` | Claude Code | the raw log, copied verbatim — the substrate everything else is derived from |
| `spec_N.md` | you | the prompt, pasted in before the run |
| `env_N.txt` | `newrun` + `finishrun` | environment at start and finish, so drift is visible |
| `trace_N.md` | `cc_trace.py` | every call paired with its result, in order |
| `strip_N.svg` | `strip_one.py` | one square per call: what kind, and whether the result carried a locator |
| `artifact_trace_N.md` | `artifact_trace.py` | where the bytes in each output file came from |
| `SKILL_N.md` | `extract_skill.py` | the skill text this run actually loaded |

---

## The readers

**`cc_trace.py`** — the ordered list of tool calls, each paired with its result.
Order falls out of reading the file top to bottom; a `.jsonl` is append-only, so
chronology is free and exact. Compact mode shows the first line of each result
plus a line count; `--full` prints everything verbatim.

Two error signals, never conflated: `exec-error` is the log's own `is_error` flag
on the result, which means the call itself failed. `out-signature` means the result
*text* contained an error-like token, which is a convenience flag and not a verdict —
a tool can run fine and print the word "error."

```bash
python3 infra/cc_trace.py session_3.jsonl --md      # pasteable table
python3 infra/cc_trace.py session_3.jsonl --full    # verbatim everything
```

**`strip_one.py`** — one square per call, in order. Fill is the kind of call.
Border weight is the *claim source*: whether the result came back with a line
number, a document path, or nothing to point at.

A locator coming back is not the same as a claim being checked against it. The
strip says how precisely a downstream claim *could* point at its origin, no more.

**`composition.py`** — the same data as a proportional bar, for runs too long to
show one square per call. Calls collapse into two bins — **read** (the result
returned document text) and **other** — and every run is normalized to one width,
so the comparison is shape rather than length. Total call count prints at the
right end, and the dark underline marks the portion of a read segment whose
result carried a line address. An empty path draws a group heading, for stacking
two conditions in one figure.

```bash
python3 infra/composition.py --png -o fig.svg \
  "n = 8 papers::" \
  "Run 0=baseline:run_0a/session_0a.jsonl" \
  "n = 200 papers::" \
  "Run 0=baseline:run_0/session_0.jsonl"
```

**`artifact_trace.py`** — where each output file's bytes came from. `strip_one`
can tell you a Write happened; it cannot tell a Write that persists a parsed file
from a Write that transcribes a table out of the model's context. Those look
identical as calls and are completely different as evidence. This reads the file
graph instead and reports each artifact as **parsed** (produced by code that read
an input file), **transcribed** (came out of the model's context), or **fetched**
(written directly by a command).

**`extract_skill.py`** — pulls the skill text a run actually loaded, out of its log.
Skill files self-update, so the copy on disk is not the copy any past run used. If
it changes under you mid-experiment, this is how you find out.

---

## Reading the output

Start with `artifact_trace_N.md`. If your deliverable is `transcribed`, the numbers
in it came from the model's context rather than from a parse, and everything
downstream inherits that.

Then `strip_N.svg` or the composition bar, for the shape of the run: where the
reads happened relative to the writes, and whether anything came back addressable.

Then `trace_N.md` when you want to know what a specific call actually did.

Three checks worth running by hand, because no script here does them for you:

- **Conservation.** Count the inputs you handed the agent against the ones that
  appear in the output. A run can drop 60% of its corpus and say nothing about it.
- **Claims in the summary.** The agent's closing prose usually states coverage.
  Check the number against the artifact.
- **Provenance of any locator.** If an output cites line numbers, confirm the trace
  contains reads that returned them.

---

## Requirements

Python 3, no dependencies for the readers. `composition.py --png` needs
`cairosvg` (`pip install cairosvg`); without it you get the SVG and a note.

The environment snapshot in `newrun.sh` / `finishrun.sh` shells out to a
domain-specific CLI and will report a failure line if you do not have it. Nothing
else in the repo assumes any particular tool — the readers work on any Claude Code
session log.

---

## Scope

Built for single-session Claude Code runs on a laptop. Not tested against
multi-agent setups, subagent sidechains, or background shells — a run that polls a
file in the background will inflate its call count with reads that do no work,
and the strip will show that honestly but not label it.
