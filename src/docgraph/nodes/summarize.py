"""Resumen por map-reduce.

Documentos cortos van directos. Documentos largos se resumen por fragmento
y luego se consolidan. La decisión la toma el grafo, no este módulo.
"""

from __future__ import annotations

import logging

from docgraph.llm.provider import LLMError, LLMProvider
from docgraph.models import Chunk
from docgraph.state import DocGraphState

logger = logging.getLogger(__name__)

# Por debajo de este umbral no compensa el map-reduce: una sola llamada
# da mejor resultado porque el modelo ve todo el contexto a la vez.
DIRECT_SUMMARY_THRESHOLD = 8_000

_DIRECT = """Resume el siguiente documento técnico en español.
Céntrate en: propósito, componentes principales, flujos y decisiones de diseño.
Máximo 400 palabras.

---
{text}
"""

_MAP = """Resume este fragmento ({n} de {total}) de un documento técnico.
Sé factual y conciso. Conserva nombres propios de componentes y tecnologías.
Máximo 150 palabras.

---
{text}
"""

_REDUCE = """A continuación hay {n} resúmenes parciales de un mismo documento
técnico, en orden. Consolídalos en un único resumen coherente en español.
Elimina repeticiones. Máximo 500 palabras.

---
{text}
"""


def needs_map_reduce(state: DocGraphState) -> str:
    """Arista condicional del grafo."""
    total = state.get("total_tokens", 0)
    route = "summarize_direct" if total <= DIRECT_SUMMARY_THRESHOLD else "summarize_map"
    logger.info("~%d tokens -> ruta '%s'", total, route)
    return route


def summarize_direct(state: DocGraphState, provider: LLMProvider) -> DocGraphState:
    chunks: list[Chunk] = state.get("chunks", [])
    text = "\n\n".join(c.text for c in chunks)

    try:
        return {"summary": provider.complete(_DIRECT.format(text=text))}
    except LLMError as exc:
        logger.error("Resumen directo falló: %s", exc)
        return {"summary": "", "errors": [f"summarize_direct: {exc}"]}


def summarize_map(state: DocGraphState, provider: LLMProvider) -> DocGraphState:
    chunks: list[Chunk] = state.get("chunks", [])
    summaries: list[str] = []
    errors: list[str] = []

    for c in chunks:
        prompt = _MAP.format(n=c.index + 1, total=len(chunks), text=c.text)
        try:
            summaries.append(provider.complete(prompt))
        except LLMError as exc:
            # Un fragmento perdido degrada el resumen, no lo invalida.
            logger.warning("Fragmento %d falló: %s", c.index, exc)
            errors.append(f"chunk {c.index}: {exc}")

    logger.info("Resumidos %d/%d fragmentos", len(summaries), len(chunks))
    return {"chunk_summaries": summaries, "errors": errors}


def summarize_reduce(state: DocGraphState, provider: LLMProvider) -> DocGraphState:
    partials = state.get("chunk_summaries", [])
    if not partials:
        return {"summary": "", "errors": ["No hay resúmenes parciales que consolidar"]}

    joined = "\n\n---\n\n".join(partials)
    try:
        return {"summary": provider.complete(_REDUCE.format(n=len(partials), text=joined))}
    except LLMError as exc:
        logger.error("Consolidación falló: %s", exc)
        # Degradación útil: concatenar es peor que consolidar, pero no es nada.
        return {"summary": joined, "errors": [f"summarize_reduce: {exc}"]}
