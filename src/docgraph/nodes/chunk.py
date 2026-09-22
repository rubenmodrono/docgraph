"""Troceado con presupuesto de tokens.

El error clásico en estos pipelines es concatenar todos los documentos y
mandarlos en un único prompt: con entradas grandes o revienta o se trunca
en silencio, que es peor porque el resultado parece correcto.

Aquí el presupuesto es explícito y el troceado respeta fronteras naturales
del texto (párrafos) antes de recurrir a un corte duro.

Ver docs/adr/0002-presupuesto-de-tokens.md
"""

from __future__ import annotations

import logging

from docgraph.models import Chunk, Document
from docgraph.state import DocGraphState

logger = logging.getLogger(__name__)

# Presupuesto por fragmento, en tokens. Conservador a propósito: deja sitio
# para la instrucción del sistema y para la respuesta.
CHUNK_TOKEN_BUDGET = 6_000

# Relación caracteres/token. 4 es la aproximación habitual para texto latino.
# Se prefiere sobre tiktoken para no atar el proyecto a un tokenizador de un
# proveedor concreto; el margen de error se absorbe en el presupuesto.
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in text.split("\n\n")]
    return [p for p in parts if p]


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Último recurso para párrafos que por sí solos exceden el presupuesto."""
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def chunk_document(doc: Document, budget: int = CHUNK_TOKEN_BUDGET) -> list[str]:
    max_chars = budget * CHARS_PER_TOKEN
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_len = 0

    for paragraph in _split_paragraphs(doc.content):
        if len(paragraph) > max_chars:
            if buffer:
                chunks.append("\n\n".join(buffer))
                buffer, buffer_len = [], 0
            chunks.extend(_hard_split(paragraph, max_chars))
            continue

        if buffer_len + len(paragraph) > max_chars:
            chunks.append("\n\n".join(buffer))
            buffer, buffer_len = [], 0

        buffer.append(paragraph)
        buffer_len += len(paragraph) + 2

    if buffer:
        chunks.append("\n\n".join(buffer))

    return chunks


def chunk(state: DocGraphState) -> DocGraphState:
    documents: list[Document] = state.get("documents", [])

    chunks: list[Chunk] = []
    for doc in documents:
        for text in chunk_document(doc):
            chunks.append(
                Chunk(
                    index=len(chunks),
                    text=text,
                    estimated_tokens=estimate_tokens(text),
                    source=doc.name,
                )
            )

    total = sum(c.estimated_tokens for c in chunks)
    logger.info("%d fragmentos, ~%d tokens estimados", len(chunks), total)

    return {"chunks": chunks, "total_tokens": total}
