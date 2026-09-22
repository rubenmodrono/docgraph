"""Generación del diagrama Mermaid.

El diagrama se deriva del modelo extraído: nodos = componentes, aristas =
relaciones. No de la forma del texto. Si no hay componentes, no hay diagrama
— es preferible a dibujar una cadena de frases sueltas que aparenta ser un
flujo sin serlo.
"""

from __future__ import annotations

import logging

from docgraph.models import Component, ComponentKind, DocumentStructure
from docgraph.state import DocGraphState

logger = logging.getLogger(__name__)

# Forma del nodo según el tipo de componente. Mermaid usa delimitadores
# distintos para cada forma.
_SHAPES: dict[ComponentKind, tuple[str, str]] = {
    ComponentKind.SERVICE: ("[", "]"),
    ComponentKind.DATASTORE: ("[(", ")]"),
    ComponentKind.QUEUE: (">", "]"),
    ComponentKind.EXTERNAL: ("{{", "}}"),
    ComponentKind.UI: ("([", "])"),
    ComponentKind.JOB: ("[/", "/]"),
    ComponentKind.UNKNOWN: ("[", "]"),
}


def _escape(text: str) -> str:
    """Mermaid rompe con comillas dobles y saltos de línea en etiquetas."""
    return text.replace('"', "'").replace("\n", " ").strip()


def _truncate(text: str, limit: int) -> str:
    """Recorta por frontera de palabra.

    Cortar por número de caracteres produce etiquetas como "finalización de
    operacio", que en un diagrama leen como un error de datos y no como una
    abreviatura.
    """
    if len(text) <= limit:
        return text

    clipped = text[: limit - 1]
    spaced = clipped.rsplit(" ", 1)[0]
    # Si la primera palabra ya excede el límite no hay frontera que respetar.
    return f"{spaced or clipped}…"


def _label(text: str, limit: int) -> str:
    return _truncate(_escape(text), limit)


def _render_node(component: Component) -> str:
    open_d, close_d = _SHAPES[component.kind]
    return f'    {component.node_id()}{open_d}"{_label(component.name, 60)}"{close_d}'


def build_mermaid(structure: DocumentStructure) -> str:
    if not structure.components:
        return ""

    by_name = {c.name: c for c in structure.components}
    lines = ["flowchart LR"]
    lines += [_render_node(c) for c in structure.components]

    for relation in structure.resolved_relations():
        source = by_name[relation.source].node_id()
        target = by_name[relation.target].node_id()
        label = _label(relation.label, 40)
        arrow = f'-- "{label}" -->' if label else "-->"
        lines.append(f"    {source} {arrow} {target}")

    return "\n".join(lines)


def build_diagram(state: DocGraphState) -> DocGraphState:
    structure = state.get("structure") or DocumentStructure()
    mermaid = build_mermaid(structure)

    if not mermaid:
        logger.info("Sin componentes identificados: no se genera diagrama")
    else:
        logger.info(
            "Diagrama con %d nodos y %d aristas",
            len(structure.components),
            len(structure.resolved_relations()),
        )

    return {"diagram": mermaid}
