from __future__ import annotations
from typing import Dict, Any, Literal

FailureType = Literal["TIMEOUT", "MISMATCH", "SEND_ERROR", "RECV_ERROR", "UNKNOWN"]

def classify_run(run: Dict[str, Any]) -> FailureType:
    if run.get("ok"):
        return "UNKNOWN"
    for step in run.get("results", []):
        if not step.get("ok"):
            err = (step.get("error") or "").lower()
            if "timed out" in err or "timeout" in err:
                return "TIMEOUT"
            if step.get("kind") == "SEND":
                return "SEND_ERROR"
            if step.get("kind") == "RECV":
                if step.get("received") is not None and step.get("expect") is not None:
                    return "MISMATCH"
                return "RECV_ERROR"
    return "UNKNOWN"
