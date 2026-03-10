from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import socket
import json
from pathlib import Path
import time
import re

@dataclass
class StepResult:
    step_index: int
    kind: str
    sent: Optional[str] = None
    received: Optional[str] = None
    ok: bool = True
    error: str = ""


REPLY_RE = re.compile(r"^(?P<code>\+\w+|-\w+)(?:\s+(?P<body>.*))?$")


def _parse_reply(resp: str) -> tuple[str, str]:
    m = REPLY_RE.match(resp.strip())
    if not m:
        return "", ""
    return m.group("code"), (m.group("body") or "").strip()


def _is_int_token(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _evaluate_oracle(
    expect: Optional[str],
    resp: str,
    last_send_cmd: str,
    logical_state: str,
) -> tuple[bool, str, str]:
    code, body = _parse_reply(resp)
    if not code:
        return False, "Malformed server reply", logical_state

    next_state = logical_state
    ok = True
    reason = ""

    if expect:
        if expect.startswith("REGEX:"):
            pattern = expect[len("REGEX:"):].strip()
            ok = bool(re.match(pattern, resp))
            if not ok:
                reason = f"Reply did not match regex '{pattern}'"
        elif expect in {"+OK", "-ERR"}:
            ok = code == expect
            if not ok:
                reason = f"Expected reply class {expect}, got {code}"
        else:
            ok = resp == expect
            if not ok:
                reason = f"Expected exact reply '{expect}', got '{resp}'"
    if not ok:
        return False, reason, logical_state

    cmd = last_send_cmd.split(" ", 1)[0].upper() if last_send_cmd else ""
    if cmd == "USER":
        if code == "+OK":
            next_state = "USER_OK"
    elif cmd == "PASS":
        if code == "+OK":
            if logical_state != "USER_OK":
                return False, "PASS accepted outside USER_OK state", logical_state
            next_state = "AUTH"
    elif cmd == "STAT":
        if code == "+OK":
            if logical_state != "AUTH":
                return False, "STAT accepted outside AUTH state", logical_state
            parts = body.split()
            if len(parts) < 2 or not _is_int_token(parts[0]) or not _is_int_token(parts[1]):
                return False, "STAT +OK reply must contain '<count> <size>' integers", logical_state
        elif code == "-ERR" and logical_state == "AUTH":
            return False, "STAT returned -ERR in AUTH state", logical_state
    elif cmd == "QUIT":
        if code != "+OK":
            return False, "QUIT must receive +OK before close", logical_state
        next_state = "END"

    return True, "", next_state


def run_trace(host: str, port: int, trace: Dict[str, Any], timeout_s: float = 2.0) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    ok = True
    start = time.time()
    logical_state = "START"
    last_send_cmd = ""

    with socket.create_connection((host, port), timeout=timeout_s) as s:
        s.settimeout(timeout_s)
        # server greeting (optional)
        try:
            greeting = s.recv(4096).decode("utf-8", errors="replace").strip()
        except Exception:
            greeting = ""

        for idx, step in enumerate(trace["steps"]):
            if step["kind"] == "SEND":
                data = (step["data"].rstrip("\r\n") + "\r\n").encode("utf-8")
                try:
                    s.sendall(data)
                    last_send_cmd = step["data"].strip()
                    results.append({"step_index": idx, "kind": "SEND", "sent": step["data"], "ok": True})
                except Exception as e:
                    ok = False
                    results.append({"step_index": idx, "kind": "SEND", "sent": step["data"], "ok": False, "error": str(e)})
                    break
            elif step["kind"] == "RECV":
                try:
                    resp = s.recv(4096).decode("utf-8", errors="replace").strip()
                    expect = step.get("expect")
                    ok_step, reason, next_state = _evaluate_oracle(expect, resp, last_send_cmd, logical_state)
                    result = {
                        "step_index": idx,
                        "kind": "RECV",
                        "received": resp,
                        "expect": expect,
                        "ok": ok_step,
                    }
                    if not ok_step:
                        result["error"] = reason
                    results.append(result)
                    if not ok_step:
                        ok = False
                        break
                    logical_state = next_state
                except Exception as e:
                    ok = False
                    results.append({"step_index": idx, "kind": "RECV", "ok": False, "error": str(e)})
                    break
            else:
                results.append({"step_index": idx, "kind": step["kind"], "ok": False, "error": "Unknown step kind"})
                ok = False
                break

    return {
        "trace_id": trace.get("trace_id"),
        "ok": ok,
        "duration_ms": int((time.time() - start) * 1000),
        "results": results,
        "notes": {"greeting": greeting, "final_state": logical_state},
    }

def run_traces(host: str, port: int, traces_dir: str, out_path: str) -> Dict[str, Any]:
    td = Path(traces_dir)
    paths = sorted(td.glob("trace_*.json"))
    runs = []
    pass_count = 0

    for p in paths:
        trace = json.loads(p.read_text(encoding="utf-8"))
        r = run_trace(host, port, trace)
        runs.append(r)
        if r["ok"]:
            pass_count += 1

    summary = {
        "host": host,
        "port": port,
        "total": len(runs),
        "passed": pass_count,
        "failed": len(runs) - pass_count,
        "runs": runs,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
