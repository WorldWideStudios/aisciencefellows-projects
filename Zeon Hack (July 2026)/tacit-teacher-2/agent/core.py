#!/usr/bin/env python3
"""The agent layer — ADK function tools with a model-free path underneath.

Ported from green-knight (Zeon hack, Track A), where this shape was built and
verified end to end against a live Gemini model. The domain is different here;
the structure is what transfers, and it earned its keep:

  MODEL-FREE   `run_offline()` drives the same tools an agent would, with plain
               Python control flow. This is the demo path. No API key, no
               network, no google-adk import required.

  MODEL-DRIVEN `build_llm_agent()` / `build_loop_agent()` hand those tools to a
               real LlmAgent. Activated only when google-adk imports AND a key
               is set.

On stage the live model is the most likely thing to fail, so it is never the
thing the demo depends on. Keep that ordering.

    python agent.py           # model-free
    python agent.py --agent   # live agent, needs GEMINI_API_KEY
"""

import os
import sys

# --------------------------------------------------------------------------- #
# Model selection — a lesson, not a preference.
# gemini-2.0-flash returns 429 RESOURCE_EXHAUSTED with `limit: 0` on a free-tier
# key: no quota at all, so it fails on the FIRST call rather than under load.
# 2.5-flash was verified working. Override per-machine with TACIT_MODEL.
# --------------------------------------------------------------------------- #
MODEL = os.environ.get("TACIT_MODEL", "gemini-2.5-flash")

#: Everything the agent writes lands here. Paths that come from a model are not
#: trusted to stay where you expect — a hallucinated "../../x" is a real
#: overwrite. See _write_path.
WORKDIR_ENV = "TACIT_WORKDIR"
DEFAULT_WORKDIR = "out"


def _workdir() -> str:
    return os.environ.get(WORKDIR_ENV, DEFAULT_WORKDIR)


def _write_path(name: str, suffix: str = "") -> str:
    """Resolve a model-supplied output filename inside the work directory.

    Only the basename survives, so the worst case is a junk file in a scratch
    directory rather than a clobbered source file.
    """
    base = os.path.basename(str(name).strip()) or "untitled"
    if suffix and not base.endswith(suffix):
        base += suffix
    root = os.path.abspath(_workdir())
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, base)


def _read_path(name: str, allowed_suffixes=(".py", ".json", ".yaml", ".yml", ".md")) -> str:
    """Resolve a model-supplied input path. Must exist and have a known suffix,
    so a confused agent cannot read arbitrary files into model context."""
    path = os.path.abspath(str(name).strip())
    if not path.endswith(tuple(allowed_suffixes)):
        raise ValueError(f"refusing to read {name!r}: not one of {allowed_suffixes}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"no such file: {name!r}")
    return path


# --------------------------------------------------------------------------- #
# Function tools.
#
# ADK reads the SIGNATURE and the DOCSTRING and sends both to the model, so both
# are part of the interface. Rules that cost us time to learn:
#   - type hints on every parameter, JSON-friendly types only
#     (str, int, float, bool, list, dict)
#   - no default values — some ADK versions cannot express them in the schema
#   - always return a dict
#   - write the docstring for the model, not for a code reviewer
#
# TODO(design): these are placeholders. The real tools follow from the design
# conversation we cut short — see docs/ once the spec lands.
# --------------------------------------------------------------------------- #
def draft_skill(name: str, description: str, python_code: str) -> dict:
    """Write a Zeon skill to disk as robotic_code.py plus metadata.

    A Zeon skill is a Python file; its parameters come from the function
    signature in robotic_code.py, not from the metadata file. Write a complete,
    runnable function — not a sketch.

    Args:
        name: skill name, lowercase with underscores or hyphens, max 64 chars.
        description: one line on what the skill does, for the metadata.
        python_code: the full contents of robotic_code.py.

    Returns:
        dict with the paths written.
    """
    skill_dir = os.path.join(os.path.abspath(_workdir()), "skills", name)
    os.makedirs(skill_dir, exist_ok=True)
    code_path = os.path.join(skill_dir, "robotic_code.py")
    meta_path = os.path.join(skill_dir, "metadata.yaml")
    with open(code_path, "w") as f:
        f.write(python_code.rstrip() + "\n")
    with open(meta_path, "w") as f:
        f.write(f"name: {name}\ndescription: {description}\n")
    return {"skill": name, "code": code_path, "metadata": meta_path}


def record_answer(question: str, answer: str, transcript: str) -> dict:
    """Append one question-and-answer exchange to the knowledge transcript.

    The transcript is the record of what the expert actually said, separate from
    whatever was inferred from it. Keep them separate — the transcript is
    evidence, the skill is an interpretation of it.

    Args:
        question: the question that was put to the expert.
        answer: the expert's answer, verbatim.
        transcript: filename for the transcript, e.g. "uncap_vial.md".

    Returns:
        dict with the transcript path and how many exchanges it now holds.
    """
    path = _write_path(transcript, ".md")
    entry = f"\n**Q:** {question}\n\n**A:** {answer}\n"
    with open(path, "a") as f:
        f.write(entry)
    with open(path) as f:
        n = f.read().count("**Q:**")
    return {"transcript": path, "exchanges": n}


TOOLS = [draft_skill, record_answer]


# --------------------------------------------------------------------------- #
# Model-free path — the demo path.
# --------------------------------------------------------------------------- #
def run_offline() -> dict:
    """Drive the tools with plain control flow, no model involved."""
    out = record_answer(
        "Which way does the cap unscrew, from the robot's point of view?",
        "Counter-clockwise. It lifts free with no resistance once it's off.",
        "example_session.md")
    return {"transcript": out["transcript"], "exchanges": out["exchanges"],
            "tools": [t.__name__ for t in TOOLS], "model_used": False}


# --------------------------------------------------------------------------- #
# Model-driven layer — strictly optional, strictly gated.
# --------------------------------------------------------------------------- #
def agent_available() -> bool:
    """True only if google-adk imports AND a key is present."""
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        return False
    try:
        import google.adk  # noqa: F401
    except Exception:
        return False
    return True


def _require_adk():
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise RuntimeError(
            "No GEMINI_API_KEY / GOOGLE_API_KEY set. The model-free path still "
            "works: `python agent.py`.")
    try:
        from google.adk.agents import LlmAgent, LoopAgent
    except Exception as e:
        raise RuntimeError(
            f"google-adk not installed ({e}). `pip install google-adk`, or use "
            "the model-free path: `python agent.py`.") from e
    return LlmAgent, LoopAgent


INSTRUCTION = (
    "You are helping a laboratory expert hand a manual technique over to a "
    "robot.\n"
    "Interview them. Ask one question at a time, and only about things that "
    "change what the robot does: direction of motion, forces, approach angles, "
    "how you can tell the step worked, and what to do when it fails.\n"
    "Record every exchange with record_answer before moving on.\n"
    "When you have enough to act, call draft_skill with complete runnable "
    "Python — not a sketch.\n"
    "Never invent a detail the expert did not give you. If you need it, ask."
)


def build_llm_agent():
    """The live interviewer. Raises RuntimeError if ADK or a key is missing."""
    LlmAgent, _ = _require_adk()
    return LlmAgent(name="tacit_teacher", model=MODEL,
                    instruction=INSTRUCTION, tools=TOOLS)


def build_loop_agent(max_iterations: int = 4):
    """Iterated interview → draft → refine, with session state between passes."""
    _, LoopAgent = _require_adk()
    return LoopAgent(name="tacit_teacher_loop", sub_agents=[build_llm_agent()],
                     max_iterations=max_iterations)


if __name__ == "__main__":
    if "--agent" in sys.argv:
        a = build_llm_agent()
        print(f"Built ADK agent {a.name!r} on {MODEL} with "
              f"{len(TOOLS)} tools: {', '.join(t.__name__ for t in TOOLS)}")
        print("Run it with the ADK runner or `adk web`.")
    else:
        for k, v in run_offline().items():
            print(f"  {k}: {v}")
