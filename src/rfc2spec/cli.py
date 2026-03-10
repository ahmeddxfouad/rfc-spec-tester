from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print

from rfc2spec.util.logging import setup_logging
from rfc2spec.rfc.segment import segment_text
from rfc2spec.rfc.io import load_text, save_json, load_segmented
from rfc2spec.llm.registry import default_registry
from rfc2spec.extract.section_filter import filter_sections
from rfc2spec.extract.element_extractor import extract_elements
from rfc2spec.extract.merge import load_extracted, merge_elements
from rfc2spec.model.mtp import compute_mtps
from rfc2spec.spec.iospec import synthesize_iospec
from rfc2spec.gen.generator import generate_traces
from rfc2spec.run.harness import run_traces
from rfc2spec.repair.loop import run_repair_loop

app = typer.Typer(add_completion=False, help="rfc2spec: RFC/spec -> executable spec -> protocol tests (AutoSpec-style MVP)")

@app.command()
def segment(input_path: str, output: str = typer.Option(..., "-o", help="Output JSON path"), doc_id: str = "DOC"):
    """Split a spec into sections + paragraph IDs."""
    setup_logging()
    text = load_text(input_path)
    doc = segment_text(doc_id=doc_id, text=text)
    save_json(output, doc.model_dump())
    print(f"[green]Wrote[/green] {output} ({len(doc.sections)} sections)")

@app.command()
def filter(segmented_json: str, output: str = typer.Option(..., "-o"), provider: str = typer.Option("mock", help="LLM provider name")):
    """Label sections and decide extraction actions."""
    setup_logging()
    reg = default_registry()
    prov = reg.get(provider)
    doc = load_segmented(segmented_json)
    smap = filter_sections(doc, prov)
    save_json(output, smap.model_dump())
    print(f"[green]Wrote[/green] {output} ({len(smap.decisions)} decisions)")

@app.command()
def extract(segmented_json: str, section_map_json: str, out_dir: str = typer.Option(..., "-o"), provider: str = typer.Option("mock")):
    """Extract messages/states/transitions from relevant sections."""
    setup_logging()
    reg = default_registry()
    prov = reg.get(provider)
    doc = load_segmented(segmented_json)
    smap = json.loads(Path(section_map_json).read_text(encoding="utf-8"))
    from rfc2spec.models.schemas import SectionMap
    smap = SectionMap.model_validate(smap)
    written = extract_elements(doc, smap, out_dir, prov)
    print(f"[green]Wrote[/green] {len(written)} extracted section files to {out_dir}")

@app.command()
def merge(extracted_dir: str, output: str = typer.Option(..., "-o")):
    """Merge extracted elements into a single protocol graph."""
    setup_logging()
    extracted = load_extracted(extracted_dir)
    pg = merge_elements(extracted)
    save_json(output, pg.model_dump())
    print(f"[green]Wrote[/green] {output} (states={len(pg.states)} messages={len(pg.messages)} transitions={len(pg.transitions)})")
    if pg.conflicts:
        print("[yellow]Conflicts:[/yellow]")
        for c in pg.conflicts:
            print(" -", c)

@app.command()
def mtp(graph_json: str, output: str = typer.Option(..., "-o"), start_state: str = "START", max_paths: int = 50):
    """Compute minimal transition paths (MTPs)."""
    setup_logging()
    from rfc2spec.models.schemas import ProtocolGraph
    pg = ProtocolGraph.model_validate(json.loads(Path(graph_json).read_text(encoding="utf-8")))
    mtps = compute_mtps(pg, start_state=start_state, max_paths=max_paths)
    save_json(output, mtps.model_dump())
    print(f"[green]Wrote[/green] {output} ({len(mtps.paths)} paths)")

@app.command()
def synth(graph_json: str, mtps_json: str, output: str = typer.Option(..., "-o")):
    """Synthesize an executable I/O-grammar-like spec (.iospec)."""
    setup_logging()
    from rfc2spec.models.schemas import ProtocolGraph, MinimalTransitionPaths
    pg = ProtocolGraph.model_validate(json.loads(Path(graph_json).read_text(encoding="utf-8")))
    mtps = MinimalTransitionPaths.model_validate(json.loads(Path(mtps_json).read_text(encoding="utf-8")))
    text = synthesize_iospec(pg, mtps)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(text, encoding="utf-8")
    print(f"[green]Wrote[/green] {output}")

@app.command()
def generate(spec_path: str, n: int = 10, out_dir: str = typer.Option(..., "-o"), seed: int = 7):
    """Generate concrete traces from an iospec file."""
    setup_logging()
    written = generate_traces(spec_path, n=n, out_dir=out_dir, seed=seed)
    print(f"[green]Wrote[/green] {len(written)} traces to {out_dir}")

@app.command()
def run(traces_dir: str, output: str = typer.Option(..., "-o"), host: str = "127.0.0.1", port: int = 21110):
    """Run traces against a server and write results."""
    setup_logging()
    summary = run_traces(host=host, port=port, traces_dir=traces_dir, out_path=output)
    print(f"[green]Wrote[/green] {output}  (passed={summary['passed']}/{summary['total']})")

@app.command()
def repair(
    results_json: str,
    spec_path: str,
    out_dir: str = typer.Option(..., "-o", help="Output directory for repair artifacts"),
    host: str = "127.0.0.1",
    port: int = 21110,
    n: int = 10,
    iterations: int = 1,
    seed: int = 7,
):
    """Run repair loop: classify -> patch proposal -> regenerate -> rerun."""
    setup_logging()
    summary = run_repair_loop(
        results_json=results_json,
        spec_path=spec_path,
        out_dir=out_dir,
        host=host,
        port=port,
        n=n,
        iterations=iterations,
        seed=seed,
    )
    print(f"[green]Wrote[/green] {summary['summary_path']}")
    print(
        f"[cyan]Repair loop[/cyan] iterations={summary['iterations_executed']}/"
        f"{summary['iterations_requested']} final_results={summary['final_results']}"
    )

if __name__ == "__main__":
    app()
