# rfc2spec — RFC/spec → executable protocol spec → tests (AutoSpec-style MVP)

This repository is an **implementable starter** for a thesis project inspired by the paper
*Synthesizing Precise Protocol Specs from Natural Language for Effective Test Generation*.

It implements the **end-to-end pipeline** (segmentation → section filtering → structured extraction → merge → minimal paths → spec synthesis → generation → execution harness),
with a **toy protocol** you can run fully offline.

> ✅ Works offline end-to-end using a `MockLLM` on the included `MiniPOP` example.
> 🔌 To run on real RFCs, plug in your LLM provider in `src/rfc2spec/llm/providers/`.

---

## Quickstart (offline demo)

```bash
# 1) create a venv and install
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 2) run the toy server in a terminal
python examples/minipop_server.py

# 3) run the pipeline on the toy "RFC-like" spec
rfc2spec segment examples/minipop_spec.txt -o out/segments.json
rfc2spec filter  out/segments.json -o out/section_map.json --provider mock
rfc2spec extract out/segments.json out/section_map.json -o out/extracted --provider mock
rfc2spec merge   out/extracted -o out/graph.json
rfc2spec mtp     out/graph.json -o out/mtps.json
rfc2spec synth   out/graph.json out/mtps.json -o out/spec.iospec
rfc2spec generate out/spec.iospec --n 10 -o out/traces
rfc2spec run --host 127.0.0.1 --port 21110 out/traces -o out/results.json
rfc2spec repair out/results.json out/spec.iospec -o out/repair --host 127.0.0.1 --port 21110 --iterations 2 --n 10

If `rfc2spec` is not on your PATH, use:

```bash
python -m rfc2spec.cli <command> ...
```
```

You should see passing conversations like:
- `USER alice` → `+OK`
- `PASS secret` → `+OK`
- `STAT` → `+OK 2 320`
- `QUIT` → `+OK`

---

## What’s implemented

### Pipeline stages
1. **Segmentation** (`segment`): splits input into numbered sections + paragraph IDs
2. **Section filtering** (`filter`): labels sections and decides extraction actions (LLM or mock)
3. **Structured extraction** (`extract`): produces schema-validated JSON elements per section (LLM or mock)
4. **Deterministic merge** (`merge`): merges section extractions into a single protocol graph with provenance
5. **Minimal Transition Paths** (`mtp`): BFS-based minimal paths through the state machine
6. **Spec synthesis** (`synth`): emits a simple I/O-grammar-like spec format (`.iospec`)
7. **Generation** (`generate`): generates concrete traces from the spec
8. **Execution harness** (`run`): runs traces against a server and records oracle outcomes
9. **Repair loop** (`repair`): classifies failures, proposes patches, regenerates traces, and reruns

### What’s intentionally “MVP” / thesis extension points
- LLM provider is pluggable, but only `MockLLM` is fully implemented.
- Repair loop is wired end-to-end (`src/rfc2spec/repair/`) and currently uses MVP patch proposals.
- For TLS you’ll replace message encoding + harness (and likely test at decrypted-message level).

---

## Repo layout

- `src/rfc2spec/` — library code
- `examples/` — toy protocol spec + toy server
- `out/` — generated artifacts (ignored by git)
- `docs/` — notes/templates for prompts and schemas

---

## Next steps for your thesis
- Add an LLM provider (OpenAI / local model) in `src/rfc2spec/llm/providers/`
- Add a real protocol target (SMTP/POP3 first, then TLS 1.2 or TLS 1.3)
- Extend constraints to cover binary framing rules and cross-field constraints
- Improve oracles: beyond “no timeout + expected response class”
