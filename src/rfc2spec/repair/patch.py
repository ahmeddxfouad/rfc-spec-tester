from __future__ import annotations
from typing import Dict, Any

def propose_patch(run: Dict[str, Any]) -> Dict[str, Any]:
    """MVP patch proposal.
    For real protocols, this should locate the responsible rule/constraint and emit a minimal diff.
    """
    return {
        "trace_id": run.get("trace_id"),
        "proposal": "MVP: no automatic patching implemented yet",
        "hint": "Implement rule-localization + constraint relaxation for your target protocol.",
    }
