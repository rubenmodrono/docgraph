"""Extracción estructurada.

Aquí está la diferencia con un pipeline ingenuo: en vez de inferir la
estructura de la forma del texto (longitud de línea, posición), se pide al
modelo que rellene un esquema y se valida la respuesta. Si no valida, se
reintenta con el error como contexto.

Ver docs/adr/0003-extraccion-estructurada.md
"""

from __future__ import annotations

import logging

from docgraph.llm.provider import LLMError, LLMProvider
from docgraph.models import DocumentStructure
from docgraph.state import DocGraphState

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2

_PROMPT = """Analiza este resumen de un documento técnico y extrae su estructura.

Reglas:
- `components`: solo piezas nombradas explícitamente en el texto. No inventes.
- `relations`: los extremos deben ser nombres que aparezcan en `components`.
- `risks`: solo los que el documento mencione o impliquen claramente.
- Si el documento no describe una arquitectura, devuelve listas vacías.

---
{summary}
"""


def extract_structure(state: DocGraphState, provider: LLMProvider) -> DocGraphState:
    summary = state.get("summary", "").strip()
    attempts = state.get("extraction_attempts", 0) + 1

    if not summary:
        return {
            "structure": DocumentStructure(),
            "extraction_attempts": attempts,
            "errors": ["extract_structure: no hay resumen del que extraer"],
        }

    try:
        structure = provider.complete_structured(
            _PROMPT.format(summary=summary), DocumentStructure
        )
    except LLMError as exc:
        logger.warning("Extracción fallida (intento %d/%d): %s", attempts, MAX_ATTEMPTS, exc)
        return {
            "extraction_attempts": attempts,
            "errors": [f"extract_structure intento {attempts}: {exc}"],
        }

    dropped = len(structure.relations) - len(structure.resolved_relations())
    if dropped:
        logger.info("Descartadas %d relaciones con extremos inexistentes", dropped)

    logger.info(
        "Estructura: %d componentes, %d relaciones, %d riesgos",
        len(structure.components),
        len(structure.resolved_relations()),
        len(structure.risks),
    )
    return {"structure": structure, "extraction_attempts": attempts}


def should_retry_extraction(state: DocGraphState) -> str:
    """Arista condicional: reintenta una vez antes de seguir sin estructura."""
    if state.get("structure") is not None:
        return "build_diagram"
    if state.get("extraction_attempts", 0) < MAX_ATTEMPTS:
        return "extract_structure"

    logger.error("Extracción agotó los reintentos; se continúa sin estructura")
    return "build_diagram"
