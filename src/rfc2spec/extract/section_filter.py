from __future__ import annotations
import json
from rfc2spec.models.schemas import SegmentedDoc, SectionMap
from rfc2spec.llm.prompts import SECTION_FILTER_PROMPT
from rfc2spec.llm.base import LLMProvider
from rfc2spec.llm.retry import complete_json_with_retries

def filter_sections(doc: SegmentedDoc, provider: LLMProvider) -> SectionMap:
    prompt = SECTION_FILTER_PROMPT.format(segmented_doc_json=json.dumps(doc.model_dump(), ensure_ascii=False))
    return complete_json_with_retries(provider, prompt, SectionMap, max_attempts=3)
