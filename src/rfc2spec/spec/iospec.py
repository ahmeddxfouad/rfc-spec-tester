from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from rfc2spec.models.schemas import ProtocolGraph, MinimalTransitionPaths

def synthesize_iospec(pg: ProtocolGraph, mtps: MinimalTransitionPaths) -> str:
    """Emit a minimal, readable I/O-grammar-like spec.

    Format:
    - states listed
    - messages listed
    - transitions listed
    - mtps listed

    This is intentionally simple so you can replace it with a real I/O grammar syntax later.
    """
    lines: List[str] = []
    lines.append(f"DOC {pg.doc_id}")
    lines.append("")
    lines.append("STATES")
    for s in sorted(pg.states.keys()):
        desc = pg.states[s].description.replace("\n", " ").strip()
        lines.append(f"  - {s}: {desc}")
    lines.append("")
    lines.append("MESSAGES")
    for m in sorted(pg.messages.keys()):
        md = pg.messages[m]
        lines.append(f"  - {m} ({md.direction})")
        if md.fields:
            for f in md.fields:
                lines.append(f"      field {f.name}: {f.type} {('('+f.description+')') if f.description else ''}".rstrip())
        for c in md.constraints:
            lines.append(f"      constraint {c.severity}: {c.expr}")
    lines.append("")
    lines.append("TRANSITIONS")
    for t in pg.transitions:
        lines.append(f"  - {t.from_state} -> {t.to_state} : SEND {t.send or '-'} / RECV {t.recv or '-'}")
        for c in t.preconditions:
            lines.append(f"      pre {c.severity}: {c.expr}")
        for c in t.postconditions:
            lines.append(f"      post {c.severity}: {c.expr}")
    lines.append("")
    lines.append("MTPS")
    for p in mtps.paths:
        seq = " ".join([f"{s.kind}({s.message})" for s in p.steps])
        lines.append(f"  - {p.path_id}: {p.from_state} -> {p.to_state} :: {seq}")
    lines.append("")
    return "\n".join(lines)
