from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import json
from rfc2spec.models.schemas import SegmentedDoc, SectionMap, ExtractedElements
from rfc2spec.llm.base import LLMProvider
from rfc2spec.llm.prompts import SECTION_EXTRACT_PROMPT
from rfc2spec.llm.retry import complete_json_with_retries

def extract_elements(doc: SegmentedDoc, section_map: SectionMap, out_dir: str, provider: LLMProvider) -> List[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    sid2sec = {s.section_id: s for s in doc.sections}
    written: List[Path] = []

    for decision in section_map.decisions:
        if decision.action == "SKIP":
            continue
        sec = sid2sec.get(decision.section_id)
        if not sec:
            continue

        evidence_paras = [p for p in sec.paragraphs if (not decision.evidence_pids) or (p.pid in decision.evidence_pids)]
        evidence_text = "\n\n".join([f"[{p.pid}] {p.text}" for p in evidence_paras])

        prompt = SECTION_EXTRACT_PROMPT.format(
            doc_id=doc.doc_id,
            section_id=sec.section_id,
            title=sec.title,
            evidence=evidence_text
        )
        extracted: ExtractedElements = complete_json_with_retries(
            provider,
            prompt,
            ExtractedElements,
            max_attempts=3,
        )

        path = out / f"section_{sec.section_id.replace('.', '_')}.json"
        path.write_text(json.dumps(extracted.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        written.append(path)

    return written
