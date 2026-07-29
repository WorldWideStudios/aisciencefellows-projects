import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT, ML_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# ADK discovers root_agent via lazy import in agent.py — do not import agent here
# (would load google-adk and all tools at package import time).

def __getattr__(name: str):
    if name == "root_agent":
        from . import agent as agent_module
        return agent_module.root_agent
    raise AttributeError(name)
