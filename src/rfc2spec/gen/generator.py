from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple
import random
import re
import json

IOSPEC_MTP_RE = re.compile(r"^\s*-\s*(?P<pid>mtp-\d+):\s*(?P<from>\S+)\s*->\s*(?P<to>\S+)\s*::\s*(?P<seq>.*)$")
STEP_RE = re.compile(r"(SEND|RECV)\(([^)]+)\)")
IOSPEC_MSG_RE = re.compile(r"^\s*-\s*(?P<name>\S+)\s+\((?P<direction>C->S|S->C|BIDIR)\)\s*$")
IOSPEC_FIELD_RE = re.compile(r"^\s*field\s+(?P<name>[^:]+):\s*(?P<type>[^\s(]+)")
IOSPEC_CONSTRAINT_RE = re.compile(r"^\s*constraint\s+\w+:\s*(?P<expr>.+)$")

CONSTRAINT_IN_SET_RE = re.compile(r"^\s*(?P<field>[A-Za-z_]\w*)\s+in\s+\{(?P<values>.+)\}\s*$")
CONSTRAINT_EQ_RE = re.compile(r"^\s*(?P<field>[A-Za-z_]\w*)\s*==\s*(?P<value>.+)\s*$")
CONSTRAINT_LEN_RE = re.compile(r"^\s*len\((?P<field>[A-Za-z_]\w*)\)\s*==\s*(?P<size>\d+)\s*$")


@dataclass
class MessageModel:
    name: str
    direction: str
    fields: List[Tuple[str, str]] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

def parse_mtps_from_iospec(text: str) -> List[List[Tuple[str,str]]]:
    mtps: List[List[Tuple[str,str]]] = []
    in_mtps = False
    for line in text.splitlines():
        if line.strip() == "MTPS":
            in_mtps = True
            continue
        if in_mtps and line.strip() == "":
            break
        if in_mtps:
            m = IOSPEC_MTP_RE.match(line)
            if not m:
                continue
            seq = m.group("seq")
            steps = [(k, msg) for k, msg in STEP_RE.findall(seq)]
            if steps:
                mtps.append(steps)
    return mtps

def parse_messages_from_iospec(text: str) -> Dict[str, MessageModel]:
    messages: Dict[str, MessageModel] = {}
    in_messages = False
    current: MessageModel | None = None

    for line in text.splitlines():
        if line.strip() == "MESSAGES":
            in_messages = True
            continue
        if in_messages and line.strip() == "":
            break
        if not in_messages:
            continue

        m_msg = IOSPEC_MSG_RE.match(line)
        if m_msg:
            if current is not None:
                messages[current.name] = current
            current = MessageModel(name=m_msg.group("name"), direction=m_msg.group("direction"))
            continue

        if current is None:
            continue

        m_field = IOSPEC_FIELD_RE.match(line)
        if m_field:
            current.fields.append((m_field.group("name").strip(), m_field.group("type").strip()))
            continue

        m_cons = IOSPEC_CONSTRAINT_RE.match(line)
        if m_cons:
            current.constraints.append(m_cons.group("expr").strip())

    if current is not None:
        messages[current.name] = current
    return messages


def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and ((v[0] == "'" and v[-1] == "'") or (v[0] == '"' and v[-1] == '"')):
        return v[1:-1]
    return v


def _random_token(length: int, rng: random.Random) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(rng.choice(alphabet) for _ in range(max(1, length)))


def _default_value_for_type(field_name: str, field_type: str, rng: random.Random) -> str:
    ftype = field_type.lower()
    if ftype.startswith("uint") or ftype.startswith("int"):
        return str(rng.randint(0, 1024))
    if ftype in {"bytes", "binary"}:
        return "00"
    if ftype == "enum":
        return f"{field_name}_v1"
    return f"{field_name}_{rng.randint(1, 999)}"


def _apply_constraints(values: Dict[str, str], constraints: List[str], rng: random.Random) -> None:
    for expr in constraints:
        m_len = CONSTRAINT_LEN_RE.match(expr)
        if m_len:
            field = m_len.group("field")
            if field in values:
                size = int(m_len.group("size"))
                values[field] = _random_token(size, rng)
            continue

        m_in = CONSTRAINT_IN_SET_RE.match(expr)
        if m_in:
            field = m_in.group("field")
            if field in values:
                raw_vals = [x.strip() for x in m_in.group("values").split(",")]
                candidates = [_strip_quotes(v) for v in raw_vals if v]
                if candidates:
                    values[field] = rng.choice(candidates)
            continue

        m_eq = CONSTRAINT_EQ_RE.match(expr)
        if m_eq:
            field = m_eq.group("field")
            if field in values:
                values[field] = _strip_quotes(m_eq.group("value"))


def instantiate_send(message: str, models: Dict[str, MessageModel], rng: random.Random) -> str:
    model = models.get(message)
    if model is None:
        return message

    # For request messages with fields, synthesize arguments from extracted schema/constraints.
    if not model.fields:
        return message

    field_values: Dict[str, str] = {}
    for field_name, field_type in model.fields:
        field_values[field_name] = _default_value_for_type(field_name, field_type, rng)
    _apply_constraints(field_values, model.constraints, rng)

    args = [field_values[field_name] for field_name, _ in model.fields]
    return " ".join([message] + args)

def generate_traces(iospec_path: str, n: int, out_dir: str, seed: int = 7) -> List[Path]:
    rng = random.Random(seed)
    text = Path(iospec_path).read_text(encoding="utf-8")
    mtps = parse_mtps_from_iospec(text)
    message_models = parse_messages_from_iospec(text)
    if not mtps:
        raise ValueError("No MTPS found in iospec. Run `rfc2spec mtp` and `rfc2spec synth` first.")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    for i in range(1, n+1):
        steps = rng.choice(mtps)
        convo = []
        for kind, msg in steps:
            if kind == "SEND":
                convo.append({"kind": "SEND", "data": instantiate_send(msg, message_models, rng)})
            else:
                convo.append({"kind": "RECV", "expect": msg})
        trace = {
            "trace_id": f"trace-{i:04d}",
            "steps": convo
        }
        p = out / f"trace_{i:04d}.json"
        p.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        written.append(p)
    return written
