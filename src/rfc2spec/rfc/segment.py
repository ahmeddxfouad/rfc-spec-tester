from __future__ import annotations
from typing import List, Tuple
import re
from rfc2spec.models.schemas import SegmentedDoc, Section, Paragraph

# Very simple "RFC-like" segmentation:
# - Section headings like: "1 Introduction" or "2.1 Commands"
# - Paragraphs split by blank lines
HEADING_RE = re.compile(r"^(?P<sid>\d+(?:\.\d+)*)\s+(?P<title>.+?)\s*$")

def segment_text(doc_id: str, text: str) -> SegmentedDoc:
    lines = text.splitlines()
    sections: List[Section] = []
    cur_sid = "0"
    cur_title = "Preamble"
    cur_buf: List[str] = []
    order: List[Tuple[str,str,List[str]]] = []  # sid, title, lines

    def flush():
        nonlocal cur_buf, cur_sid, cur_title
        if cur_buf:
            order.append((cur_sid, cur_title, cur_buf))
        cur_buf = []

    for line in lines:
        m = HEADING_RE.match(line.strip())
        if m:
            flush()
            cur_sid = m.group("sid")
            cur_title = m.group("title")
        else:
            cur_buf.append(line)
    flush()

    for sid, title, sec_lines in order:
        raw = "\n".join(sec_lines).strip()
        if not raw:
            continue
        # paragraphs are separated by >=1 blank line
        paras = [p.strip() for p in re.split(r"\n\s*\n+", raw) if p.strip()]
        paragraphs: List[Paragraph] = []
        for i, p in enumerate(paras, start=1):
            pid = f"{sid}.p{i}"
            paragraphs.append(Paragraph(pid=pid, text=p))
        sections.append(Section(section_id=sid, title=title, paragraphs=paragraphs))

    return SegmentedDoc(doc_id=doc_id, sections=sections)
