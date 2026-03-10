from __future__ import annotations

SECTION_FILTER_PROMPT = """
You are a protocol specification analyst.

Given a segmented protocol document in JSON (sections + paragraphs with stable IDs),
produce a JSON object matching the provided schema:
- For each section_id decide label + action
- Include evidence paragraph IDs

Rules:
- Output JSON only (no markdown)
- Be conservative: if unsure, label MAYBE_RELEVANT and choose EXTRACT_ALL

SEGMENTED_DOC_JSON:
{segmented_doc_json}
""".strip()


SECTION_EXTRACT_PROMPT = """
You are extracting protocol elements from a single section of a protocol specification.

Return a JSON object that matches the provided schema for ExtractedElements:
- messages (name, direction, fields, constraints, examples)
- states
- transitions (from_state, to_state, send, recv, constraints)
- Keep provenance: include source_pids referencing paragraph IDs

Rules:
- Output JSON only (no markdown)
- Only extract what is supported by the evidence text
- If the section is not relevant, return empty lists

DOC_ID: {doc_id}
SECTION_ID: {section_id}
SECTION_TITLE: {title}

EVIDENCE (paragraphs):
{evidence}

""".strip()
