from __future__ import annotations
import networkx as nx
from rfc2spec.models.schemas import ProtocolGraph

def to_nx(pg: ProtocolGraph) -> nx.MultiDiGraph:
    # Use MultiDiGraph so parallel transitions between same states are preserved.
    g = nx.MultiDiGraph()
    for s in pg.states.values():
        g.add_node(s.name, kind="state")
    for t in pg.transitions:
        g.add_edge(t.from_state, t.to_state, send=t.send, recv=t.recv, source_pids=t.source_pids)
    return g
