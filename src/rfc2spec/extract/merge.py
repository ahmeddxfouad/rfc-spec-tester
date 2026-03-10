from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import json
from rfc2spec.models.schemas import ExtractedElements, ProtocolGraph, StateDef, MessageDef, TransitionDef

def load_extracted(folder: str) -> List[ExtractedElements]:
    paths = sorted(Path(folder).glob("section_*.json"))
    out: List[ExtractedElements] = []
    for p in paths:
        data = json.loads(p.read_text(encoding="utf-8"))
        out.append(ExtractedElements.model_validate(data))
    return out

def merge_elements(extracted: List[ExtractedElements]) -> ProtocolGraph:
    if not extracted:
        return ProtocolGraph(doc_id="DOC")
    doc_id = extracted[0].doc_id

    states: Dict[str, StateDef] = {}
    messages: Dict[str, MessageDef] = {}
    transitions: List[TransitionDef] = []
    conflicts: List[str] = []

    def norm(name: str) -> str:
        return name.strip()

    for ex in extracted:
        for s in ex.states:
            key = norm(s.name)
            if key in states:
                # merge provenance + keep first description if exists
                merged = states[key]
                merged.source_pids = sorted(set(merged.source_pids + s.source_pids))
                if not merged.description and s.description:
                    merged.description = s.description
                states[key] = merged
            else:
                states[key] = s

        for m in ex.messages:
            key = norm(m.name)
            if key in messages:
                merged = messages[key]
                # direction conflicts are meaningful
                if merged.direction != m.direction:
                    conflicts.append(f"Message '{key}' direction conflict: {merged.direction} vs {m.direction}")
                merged.source_pids = sorted(set(merged.source_pids + m.source_pids))
                merged.examples = sorted(set(merged.examples + m.examples))
                # merge fields by name (very simple)
                field_by_name = {f.name: f for f in merged.fields}
                for f in m.fields:
                    if f.name in field_by_name:
                        # prefer filled description/type if missing
                        existing = field_by_name[f.name]
                        if existing.type == "string" and f.type != "string":
                            existing.type = f.type
                        if not existing.description and f.description:
                            existing.description = f.description
                        field_by_name[f.name] = existing
                    else:
                        field_by_name[f.name] = f
                merged.fields = list(field_by_name.values())
                merged.constraints = merged.constraints + m.constraints
                messages[key] = merged
            else:
                messages[key] = m

        transitions.extend(ex.transitions)

    return ProtocolGraph(doc_id=doc_id, states=states, messages=messages, transitions=transitions, conflicts=conflicts)
