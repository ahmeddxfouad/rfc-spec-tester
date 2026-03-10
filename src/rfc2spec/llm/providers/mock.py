from __future__ import annotations
import re
from typing import Type, List
from pydantic import BaseModel
from rfc2spec.models.schemas import (
    SectionMap, SectionDecision,
    ExtractedElements, MessageDef, FieldDef, StateDef, TransitionDef, Constraint,
)

class MockLLM:
    """Offline provider for the included MiniPOP example.
    It uses simple heuristics keyed to the example spec text.
    """
    name = "mock"

    def complete_json(self, prompt: str, schema: Type[BaseModel]):
        if schema is SectionMap:
            return self._mock_section_map(prompt)
        if schema is ExtractedElements:
            return self._mock_extract(prompt)
        raise ValueError(f"MockLLM doesn't support schema {schema}")

    def _mock_section_map(self, prompt: str) -> SectionMap:
        # prompt contains serialized segments; detect section IDs and label them.
        sids = re.findall(r'"section_id"\s*:\s*"([^"]+)"', prompt)
        sids = list(dict.fromkeys(sids))  # preserve order unique
        decisions: List[SectionDecision] = []
        for sid in sids:
            if sid.startswith("2"):
                decisions.append(SectionDecision(section_id=sid, label="MESSAGE_FORMAT", action="EXTRACT_ALL",
                                                evidence_pids=[f"{sid}.p1"], short_summary="Command/response formats"))
            elif sid.startswith("3"):
                decisions.append(SectionDecision(section_id=sid, label="STATE_MACHINE", action="EXTRACT_ALL",
                                                evidence_pids=[f"{sid}.p1"], short_summary="States and valid sequences"))
            elif sid.startswith("4"):
                decisions.append(SectionDecision(section_id=sid, label="ERROR_HANDLING", action="EXTRACT_CONSTRAINTS",
                                                evidence_pids=[f"{sid}.p1"], short_summary="Error behavior"))
            else:
                decisions.append(SectionDecision(section_id=sid, label="IRRELEVANT", action="SKIP",
                                                evidence_pids=[], short_summary="Not needed for MVP"))
        # doc_id is embedded in the prompt for mock; fallback:
        m = re.search(r'"doc_id"\s*:\s*"([^"]+)"', prompt)
        doc_id = m.group(1) if m else "DOC"
        return SectionMap(doc_id=doc_id, decisions=decisions)

    def _mock_extract(self, prompt: str) -> ExtractedElements:
        # Extract section_id from prompt
        m_sid = re.search(r"SECTION_ID:\s*([^\n]+)", prompt)
        section_id = m_sid.group(1).strip() if m_sid else "0"
        m_doc = re.search(r"DOC_ID:\s*([^\n]+)", prompt)
        doc_id = m_doc.group(1).strip() if m_doc else "DOC"

        # MiniPOP protocol definitions
        messages = [
            MessageDef(name="USER", direction="C->S",
                       fields=[FieldDef(name="username", type="string", description="User identifier")],
                       examples=["USER alice"], source_pids=[f"{section_id}.p1"]),
            MessageDef(name="PASS", direction="C->S",
                       fields=[FieldDef(name="password", type="string")],
                       examples=["PASS secret"], source_pids=[f"{section_id}.p1"]),
            MessageDef(name="STAT", direction="C->S", fields=[],
                       examples=["STAT"], source_pids=[f"{section_id}.p1"]),
            MessageDef(name="QUIT", direction="C->S", fields=[],
                       examples=["QUIT"], source_pids=[f"{section_id}.p1"]),
            MessageDef(name="+OK", direction="S->C",
                       fields=[FieldDef(name="text", type="string", description="Optional text")],
                       examples=["+OK", "+OK 2 320"], source_pids=[f"{section_id}.p1"]),
            MessageDef(name="-ERR", direction="S->C",
                       fields=[FieldDef(name="text", type="string")],
                       examples=["-ERR bad sequence"], source_pids=[f"{section_id}.p1"]),
        ]

        states = [
            StateDef(name="START", description="Connected, not authenticated", source_pids=[f"{section_id}.p1"]),
            StateDef(name="USER_OK", description="USER accepted; waiting for PASS", source_pids=[f"{section_id}.p1"]),
            StateDef(name="AUTH", description="Authenticated", source_pids=[f"{section_id}.p1"]),
            StateDef(name="END", description="Connection closing", source_pids=[f"{section_id}.p1"]),
        ]

        transitions = [
            TransitionDef(from_state="START", to_state="USER_OK", send="USER", recv="+OK",
                          source_pids=[f"{section_id}.p1"]),
            TransitionDef(from_state="USER_OK", to_state="AUTH", send="PASS", recv="+OK",
                          source_pids=[f"{section_id}.p1"]),
            TransitionDef(from_state="AUTH", to_state="AUTH", send="STAT", recv="+OK",
                          source_pids=[f"{section_id}.p1"]),
            TransitionDef(from_state="START", to_state="END", send="QUIT", recv="+OK",
                          source_pids=[f"{section_id}.p1"]),
            TransitionDef(from_state="USER_OK", to_state="END", send="QUIT", recv="+OK",
                          source_pids=[f"{section_id}.p1"]),
            TransitionDef(from_state="AUTH", to_state="END", send="QUIT", recv="+OK",
                          source_pids=[f"{section_id}.p1"]),
        ]

        # error rule: STAT before AUTH => -ERR
        transitions.append(
            TransitionDef(from_state="START", to_state="START", send="STAT", recv="-ERR",
                          postconditions=[Constraint(expr="error='bad sequence'", severity="SOFT")],
                          source_pids=[f"{section_id}.p1"])
        )

        return ExtractedElements(
            doc_id=doc_id, section_id=section_id,
            messages=messages, states=states, transitions=transitions,
            notes=["Mock extraction for MiniPOP"], source_pids=[f"{section_id}.p1"]
        )
