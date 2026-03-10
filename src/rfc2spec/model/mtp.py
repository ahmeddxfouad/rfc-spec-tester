from __future__ import annotations
from itertools import product
from typing import List
import networkx as nx
from rfc2spec.models.schemas import ProtocolGraph, MinimalTransitionPaths, Path, ActionStep
from rfc2spec.model.graph import to_nx

def compute_mtps(pg: ProtocolGraph, start_state: str = "START", max_paths: int = 50) -> MinimalTransitionPaths:
    g = to_nx(pg)
    paths: List[Path] = []
    if start_state not in g.nodes:
        # pick any node as fallback
        start_state = next(iter(g.nodes), "START")

    # BFS shortest paths from start to every reachable state
    try:
        sp = nx.single_source_shortest_path(g, start_state)
    except Exception:
        sp = {start_state: [start_state]}

    pid = 1
    for target, nodes in sp.items():
        if target == start_state:
            continue
        # For each hop in a shortest node-path, keep all parallel transitions.
        per_hop_steps: List[List[List[ActionStep]]] = []
        for u, v in zip(nodes, nodes[1:]):
            edge_data = g.get_edge_data(u, v) or {}
            hop_alternatives: List[List[ActionStep]] = []
            for data in edge_data.values():
                alt_steps: List[ActionStep] = []
                if data.get("send"):
                    alt_steps.append(ActionStep(kind="SEND", message=data["send"]))
                if data.get("recv"):
                    alt_steps.append(ActionStep(kind="RECV", message=data["recv"]))
                hop_alternatives.append(alt_steps)
            if not hop_alternatives:
                hop_alternatives = [[]]
            per_hop_steps.append(hop_alternatives)

        for combo in product(*per_hop_steps):
            steps: List[ActionStep] = []
            for alt in combo:
                steps.extend(alt)
            paths.append(Path(
                path_id=f"mtp-{pid:03d}",
                from_state=start_state,
                to_state=target,
                steps=steps
            ))
            pid += 1
            if len(paths) >= max_paths:
                break
        if len(paths) >= max_paths:
            break

    return MinimalTransitionPaths(doc_id=pg.doc_id, paths=paths)
