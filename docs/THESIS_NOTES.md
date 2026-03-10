# Thesis notes / TODOs

## How to extend from the MVP to the paper-level system

1) Replace `MockLLM` with a real LLM provider
- Add JSON-mode / schema-constrained outputs
- Add retry on schema validation errors
- Keep paragraph provenance (`source_pids`)

2) Expand the constraint DSL
- Cross-field constraints (len==field)
- Dependencies (extension present -> field required)
- Numeric ranges and enums
- For TLS: vector length encoding and handshake message lengths

3) Add a real executable I/O grammar backend
- This repo emits a human-readable `.iospec`
- Replace with (or compile into) your chosen I/O grammar interpreter/generator
- Alternatively: compile to a stateful generator with constraint solving

4) Add a repair loop
- This MVP provides failure classification scaffolding
- The paper’s key contribution is iterative repair using runtime evidence

5) TLS adaptation strategy
- Start with TLS 1.2 handshake (more plaintext early)
- Or generate abstract handshake messages and let a TLS library encode/encrypt them
- Or instrument an implementation for decrypted traces

