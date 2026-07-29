"""Entry point so `python -m agent` runs cleanly.

Running `python -m agent.core` directly triggers the package __init__ first,
which imports .core, which then gets re-executed under __main__ — Python warns
about that and it looks like a fault when it is not.
"""
import sys

from .core import MODEL, TOOLS, build_llm_agent, run_offline

if "--agent" in sys.argv:
    a = build_llm_agent()
    print(f"Built ADK agent {a.name!r} on {MODEL} with "
          f"{len(TOOLS)} tools: {', '.join(t.__name__ for t in TOOLS)}")
    print("Run it with the ADK runner or `adk web`.")
else:
    for k, v in run_offline().items():
        print(f"  {k}: {v}")
