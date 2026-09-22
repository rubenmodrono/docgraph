"""Estado del grafo.

Un único diccionario tipado que atraviesa todos los nodos. LangGraph lo
mezcla nodo a nodo, así que cada nodo devuelve solo las claves que modifica.
"""

from __future__ import annotations

import operator
from pathlib import Path
from typing import Annotated, TypedDict

from docgraph.models import Chunk, Document, DocumentStructure


class DocGraphState(TypedDict, total=False):
    # --- entrada ---
    input_dir: Path
    output_dir: Path

    # --- ingesta ---
    documents: list[Document]
    chunks: list[Chunk]
    total_tokens: int

    # --- resumen ---
    # Los resúmenes parciales se acumulan: el fan-out del map escribe
    # concurrentemente sobre esta clave.
    chunk_summaries: Annotated[list[str], operator.add]
    summary: str

    # --- extracción ---
    structure: DocumentStructure
    extraction_attempts: int

    # --- salida ---
    diagram: str
    outputs: dict[str, Path]

    # --- diagnóstico ---
    errors: Annotated[list[str], operator.add]
