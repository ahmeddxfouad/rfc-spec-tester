from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any

Direction = Literal["C->S", "S->C", "BIDIR"]

class Paragraph(BaseModel):
    pid: str
    text: str

class Section(BaseModel):
    section_id: str
    title: str = ""
    paragraphs: List[Paragraph]

class SegmentedDoc(BaseModel):
    doc_id: str
    sections: List[Section]

# --- Section filtering output ---
SectionLabel = Literal[
    "MESSAGE_FORMAT",
    "STATE_MACHINE",
    "ERROR_HANDLING",
    "EXAMPLES",
    "SECURITY",
    "IRRELEVANT",
    "MAYBE_RELEVANT",
]

SectionAction = Literal[
    "EXTRACT_TRANSITIONS",
    "EXTRACT_FIELDS",
    "EXTRACT_CONSTRAINTS",
    "EXTRACT_ALL",
    "SKIP",
]

class SectionDecision(BaseModel):
    section_id: str
    label: SectionLabel
    action: SectionAction
    evidence_pids: List[str] = Field(default_factory=list)
    short_summary: str = ""

class SectionMap(BaseModel):
    doc_id: str
    decisions: List[SectionDecision]

# --- Extraction output (per section) ---

class FieldDef(BaseModel):
    name: str
    type: str = "string"   # e.g. "string", "uint16", "bytes", "enum", ...
    size: Optional[int] = None  # bits/bytes depending on your encoder; MVP uses None/bytes
    description: str = ""

class Constraint(BaseModel):
    # MVP constraint DSL: store as a simple expression string + optional description.
    expr: str  # e.g. "len(payload)==length", "ext.type in {0x0000,0x000a}"
    description: str = ""
    severity: Literal["HARD", "SOFT"] = "HARD"

class MessageDef(BaseModel):
    name: str
    direction: Direction
    fields: List[FieldDef] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    source_pids: List[str] = Field(default_factory=list)

class StateDef(BaseModel):
    name: str
    description: str = ""
    source_pids: List[str] = Field(default_factory=list)

class TransitionDef(BaseModel):
    from_state: str
    to_state: str
    send: Optional[str] = None
    recv: Optional[str] = None
    preconditions: List[Constraint] = Field(default_factory=list)
    postconditions: List[Constraint] = Field(default_factory=list)
    source_pids: List[str] = Field(default_factory=list)

class ExtractedElements(BaseModel):
    doc_id: str
    section_id: str
    messages: List[MessageDef] = Field(default_factory=list)
    states: List[StateDef] = Field(default_factory=list)
    transitions: List[TransitionDef] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    source_pids: List[str] = Field(default_factory=list)

# --- Merged model ---

class ProtocolGraph(BaseModel):
    doc_id: str
    states: Dict[str, StateDef] = Field(default_factory=dict)
    messages: Dict[str, MessageDef] = Field(default_factory=dict)
    transitions: List[TransitionDef] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)

class ActionStep(BaseModel):
    kind: Literal["SEND", "RECV"]
    message: str

class Path(BaseModel):
    path_id: str
    from_state: str
    to_state: str
    steps: List[ActionStep]

class MinimalTransitionPaths(BaseModel):
    doc_id: str
    paths: List[Path]
