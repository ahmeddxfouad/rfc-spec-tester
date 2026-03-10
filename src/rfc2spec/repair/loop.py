from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import json

from rfc2spec.gen.generator import generate_traces
from rfc2spec.repair.classify import classify_run
from rfc2spec.repair.patch import propose_patch
from rfc2spec.run.harness import run_traces


def run_repair_loop(
    results_json: str,
    spec_path: str,
    out_dir: str,
    host: str,
    port: int,
    n: int = 10,
    iterations: int = 1,
    seed: int = 7,
) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    current_results_path = Path(results_json)
    current_summary = json.loads(current_results_path.read_text(encoding="utf-8"))
    history: List[Dict[str, Any]] = []

    for i in range(1, iterations + 1):
        failed_runs = [r for r in current_summary.get("runs", []) if not r.get("ok")]
        failure_reports = []
        for run in failed_runs:
            failure_reports.append(
                {
                    "trace_id": run.get("trace_id"),
                    "failure_type": classify_run(run),
                    "patch_proposal": propose_patch(run),
                }
            )

        iter_dir = out / f"iter_{i:02d}"
        iter_dir.mkdir(parents=True, exist_ok=True)
        report_path = iter_dir / "repair_report.json"
        report = {
            "iteration": i,
            "input_results": str(current_results_path),
            "total_runs": current_summary.get("total", 0),
            "failed_runs": len(failed_runs),
            "failures": failure_reports,
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        iter_record: Dict[str, Any] = {
            "iteration": i,
            "repair_report": str(report_path),
            "input_results": str(current_results_path),
            "failed_runs": len(failed_runs),
        }

        if not failed_runs:
            iter_record["status"] = "converged_no_failures"
            history.append(iter_record)
            break

        traces_dir = iter_dir / "traces"
        iter_seed = seed + (i - 1)
        generate_traces(spec_path, n=n, out_dir=str(traces_dir), seed=iter_seed)

        iter_results_path = iter_dir / "results.json"
        current_summary = run_traces(host=host, port=port, traces_dir=str(traces_dir), out_path=str(iter_results_path))
        current_results_path = iter_results_path

        iter_record["status"] = "rerun_completed"
        iter_record["generated_traces_dir"] = str(traces_dir)
        iter_record["output_results"] = str(iter_results_path)
        iter_record["rerun_passed"] = current_summary.get("passed")
        iter_record["rerun_total"] = current_summary.get("total")
        history.append(iter_record)

    final_summary = {
        "initial_results": results_json,
        "final_results": str(current_results_path),
        "iterations_requested": iterations,
        "iterations_executed": len(history),
        "history": history,
    }
    summary_path = out / "repair_loop_summary.json"
    summary_path.write_text(json.dumps(final_summary, indent=2), encoding="utf-8")
    final_summary["summary_path"] = str(summary_path)
    return final_summary
