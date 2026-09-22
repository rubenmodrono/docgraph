"""Renderizado de salidas: Markdown y HTML.

El HTML es autocontenido salvo por Mermaid, que se carga por CDN para no
empaquetar un bundle de JS en el repositorio.
"""

from __future__ import annotations

import html
import logging
from pathlib import Path

from docgraph.models import DocumentStructure
from docgraph.state import DocGraphState

logger = logging.getLogger(__name__)


def _markdown(summary: str, structure: DocumentStructure, diagram: str) -> str:
    title = structure.title or "Análisis del documento"
    parts = [f"# {title}", "", "## Resumen", "", summary or "_No disponible._", ""]

    if structure.components:
        parts += ["## Componentes", ""]
        for c in structure.components:
            detail = f" — {c.responsibility}" if c.responsibility else ""
            parts.append(f"- **{c.name}** (`{c.kind.value}`){detail}")
        parts.append("")

    if diagram:
        parts += ["## Diagrama", "", "```mermaid", diagram, "```", ""]

    if structure.key_decisions:
        parts += ["## Decisiones de diseño", ""]
        parts += [f"- {d}" for d in structure.key_decisions]
        parts.append("")

    if structure.risks:
        parts += ["## Riesgos", "", "| Severidad | Descripción |", "| --- | --- |"]
        parts += [f"| {r.severity.value} | {r.description} |" for r in structure.risks]
        parts.append("")

    return "\n".join(parts)


_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 62rem; margin: 0 auto; padding: 2rem 1.5rem; line-height: 1.6; }}
  h1, h2 {{ line-height: 1.25; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #8884; padding: .5rem .75rem; text-align: left; }}
  .mermaid {{ overflow-x: auto; margin: 1.5rem 0; }}
</style>
</head>
<body>
<h1>{title}</h1>
<h2>Resumen</h2>
<p>{summary}</p>
{components}
{diagram}
{risks}
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{ startOnLoad: true }});
</script>
</body>
</html>
"""


def _html_doc(summary: str, structure: DocumentStructure, diagram: str) -> str:
    esc = html.escape

    components = ""
    if structure.components:
        items = "".join(
            f"<li><strong>{esc(c.name)}</strong> <code>{c.kind.value}</code>"
            f"{f' — {esc(c.responsibility)}' if c.responsibility else ''}</li>"
            for c in structure.components
        )
        components = f"<h2>Componentes</h2><ul>{items}</ul>"

    diagram_html = ""
    if diagram:
        diagram_html = f'<h2>Diagrama</h2><pre class="mermaid">{esc(diagram)}</pre>'

    risks = ""
    if structure.risks:
        rows = "".join(
            f"<tr><td>{r.severity.value}</td><td>{esc(r.description)}</td></tr>"
            for r in structure.risks
        )
        risks = (
            "<h2>Riesgos</h2><table><thead><tr><th>Severidad</th>"
            f"<th>Descripción</th></tr></thead><tbody>{rows}</tbody></table>"
        )

    return _HTML.format(
        title=esc(structure.title or "Análisis del documento"),
        summary=esc(summary or "No disponible."),
        components=components,
        diagram=diagram_html,
        risks=risks,
    )


def render(state: DocGraphState) -> DocGraphState:
    output_dir: Path = state["output_dir"]
    summary = state.get("summary", "")
    structure = state.get("structure") or DocumentStructure()
    diagram = state.get("diagram", "")

    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    files = {
        "markdown": ("analisis.md", _markdown(summary, structure, diagram)),
        "html": ("analisis.html", _html_doc(summary, structure, diagram)),
    }
    if diagram:
        files["mermaid"] = ("diagrama.mmd", diagram)

    errors: list[str] = []
    for key, (filename, content) in files.items():
        path = output_dir / filename
        try:
            path.write_text(content, encoding="utf-8")
            written[key] = path
            logger.info("Escrito %s", path.name)
        except OSError as exc:
            errors.append(f"render {filename}: {exc}")

    return {"outputs": written, "errors": errors}
