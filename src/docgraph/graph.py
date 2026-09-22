"""Cableado del grafo.

    ingest → chunk → ┬─(corto)──→ summarize_direct ──┐
                     └─(largo)──→ summarize_map →     │
                                  summarize_reduce ──┤
                                                     ↓
                            extract_structure ←──┐   │
                                     │           │   │
                                     └─(fallo)───┘   │
                                     │                │
                                     ↓                │
                              build_diagram ←─────────┘
                                     ↓
                                  render → END

Dos decisiones visibles aquí: el enrutado por tamaño (evita map-reduce
innecesario en documentos cortos) y el reintento acotado en la extracción
(el único nodo donde el modelo puede devolver algo inválido de forma
detectable).

Ver docs/adr/0001-langgraph-sobre-pipeline-lineal.md
"""

from __future__ import annotations

import logging
from functools import partial
from pathlib import Path

from langgraph.graph import END, StateGraph

from docgraph.llm.provider import LLMProvider, build_provider
from docgraph.nodes.chunk import chunk
from docgraph.nodes.diagram import build_diagram
from docgraph.nodes.extract import extract_structure, should_retry_extraction
from docgraph.nodes.ingest import ingest
from docgraph.nodes.render import render
from docgraph.nodes.summarize import (
    needs_map_reduce,
    summarize_direct,
    summarize_map,
    summarize_reduce,
)
from docgraph.state import DocGraphState

logger = logging.getLogger(__name__)


def build_graph(provider: LLMProvider | None = None):
    """Compila el grafo. El proveedor se inyecta en los nodos que lo usan."""
    llm = provider or build_provider()
    graph = StateGraph(DocGraphState)

    graph.add_node("ingest", ingest)
    graph.add_node("chunk", chunk)
    graph.add_node("summarize_direct", partial(summarize_direct, provider=llm))
    graph.add_node("summarize_map", partial(summarize_map, provider=llm))
    graph.add_node("summarize_reduce", partial(summarize_reduce, provider=llm))
    graph.add_node("extract_structure", partial(extract_structure, provider=llm))
    graph.add_node("build_diagram", build_diagram)
    graph.add_node("render", render)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "chunk")

    graph.add_conditional_edges(
        "chunk",
        needs_map_reduce,
        {"summarize_direct": "summarize_direct", "summarize_map": "summarize_map"},
    )
    graph.add_edge("summarize_map", "summarize_reduce")
    graph.add_edge("summarize_direct", "extract_structure")
    graph.add_edge("summarize_reduce", "extract_structure")

    graph.add_conditional_edges(
        "extract_structure",
        should_retry_extraction,
        {"extract_structure": "extract_structure", "build_diagram": "build_diagram"},
    )
    graph.add_edge("build_diagram", "render")
    graph.add_edge("render", END)

    return graph.compile()


def analyse(
    input_dir: Path, output_dir: Path, provider: LLMProvider | None = None
) -> DocGraphState:
    """Punto de entrada programático."""
    app = build_graph(provider)
    initial: DocGraphState = {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "chunk_summaries": [],
        "errors": [],
    }
    # El reintento de extracción necesita margen sobre el límite por defecto.
    final = app.invoke(initial, config={"recursion_limit": 50})

    for error in final.get("errors", []):
        logger.warning("Incidencia: %s", error)

    return final
