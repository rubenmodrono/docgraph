"""Servidor MCP.

Expone el mismo grafo que la CLI como herramientas del Model Context
Protocol, de modo que cualquier cliente MCP (Claude Desktop, un IDE, otro
agente) pueda pedir el análisis sin pasar por la línea de comandos.

Ver docs/adr/0005-servidor-mcp.md
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

from docgraph.graph import analyse
from docgraph.models import Component, Relation, Risk

logger = logging.getLogger(__name__)

server = MCPServer(
    name="docgraph",
    instructions=(
        "Analiza documentación técnica y devuelve su estructura: resumen, "
        "componentes, relaciones, riesgos y un diagrama Mermaid derivado del "
        "modelo extraído. Usa analyse_text para contenido que ya tengas en "
        "contexto y analyse_directory para documentos en disco (PDF, DOCX, "
        "Markdown, texto plano, YAML y JSON)."
    ),
)


class AnalysisResult(BaseModel):
    """Salida estructurada de una herramienta de análisis."""

    title: str = ""
    summary: str = ""
    components: list[Component] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    diagram: str = Field(default="", description="Diagrama en sintaxis Mermaid")
    warnings: list[str] = Field(
        default_factory=list,
        description="Incidencias no fatales: fragmentos fallidos, reintentos agotados",
    )


def _to_result(state: dict) -> AnalysisResult:
    structure = state.get("structure")
    return AnalysisResult(
        title=structure.title if structure else "",
        summary=state.get("summary", ""),
        components=structure.components if structure else [],
        relations=structure.resolved_relations() if structure else [],
        risks=structure.risks if structure else [],
        key_decisions=structure.key_decisions if structure else [],
        diagram=state.get("diagram", ""),
        warnings=state.get("errors", []),
    )


def _run(input_dir: Path) -> AnalysisResult:
    """Ejecuta el grafo descartando las salidas en disco.

    Un cliente MCP quiere el contenido, no ficheros. El nodo de renderizado
    escribe igualmente, así que se le da un directorio temporal que se borra
    al salir, en vez de añadirle una rama condicional al grafo.
    """
    with tempfile.TemporaryDirectory(prefix="docgraph-mcp-") as tmp:
        return _to_result(analyse(input_dir, Path(tmp)))


@server.tool(
    title="Analizar texto",
    description=(
        "Analiza documentación técnica pasada como texto y devuelve resumen, "
        "componentes, relaciones, riesgos y un diagrama Mermaid."
    ),
)
def analyse_text(text: str, filename: str = "documento.md") -> AnalysisResult:
    """Analiza un documento que ya está en contexto.

    Args:
        text: Contenido del documento técnico.
        filename: Nombre con el que tratarlo; su extensión elige el lector.
    """
    if not text.strip():
        raise ValueError("El texto está vacío: no hay nada que analizar.")

    # Se materializa en disco para reutilizar el pipeline de ingesta tal cual.
    with tempfile.TemporaryDirectory(prefix="docgraph-in-") as tmp:
        safe_name = Path(filename).name or "documento.md"
        (Path(tmp) / safe_name).write_text(text, encoding="utf-8")
        return _run(Path(tmp))


@server.tool(
    title="Analizar directorio",
    description=(
        "Analiza todos los documentos de un directorio (PDF, DOCX, Markdown, "
        "texto, YAML, JSON) y devuelve su estructura conjunta."
    ),
)
def analyse_directory(input_dir: str) -> AnalysisResult:
    """Analiza los documentos de un directorio del sistema de ficheros.

    Args:
        input_dir: Ruta al directorio que contiene la documentación.
    """
    path = Path(input_dir).expanduser()
    if not path.is_dir():
        raise ValueError(f"No es un directorio accesible: {input_dir}")

    return _run(path)


def main() -> None:
    """Punto de entrada del servidor sobre stdio."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        # stdio transporta el protocolo por stdout: los logs van a stderr.
    )
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
