"""Tests del grafo con proveedor simulado.

Cubren las dos rutas del enrutado por tamaño y la construcción del diagrama,
que son las partes donde vive la lógica propia del proyecto.
"""

from pathlib import Path

import pytest

from docgraph.graph import analyse
from docgraph.models import (
    Component,
    ComponentKind,
    DocumentStructure,
    Relation,
    Risk,
    Severity,
)
from docgraph.nodes.diagram import build_mermaid
from docgraph.nodes.summarize import DIRECT_SUMMARY_THRESHOLD


class StubProvider:
    """Proveedor determinista que devuelve una estructura conocida."""

    name = "stub"

    def __init__(self):
        self.completions = 0
        self.structured_calls = 0

    def complete(self, prompt: str) -> str:
        self.completions += 1
        return f"resumen-{self.completions}"

    def complete_structured(self, prompt: str, schema):
        self.structured_calls += 1
        return DocumentStructure(
            title="Plataforma de pagos",
            components=[
                Component(name="Ingesta", kind=ComponentKind.SERVICE),
                Component(name="Kafka", kind=ComponentKind.QUEUE),
                Component(name="PostgreSQL", kind=ComponentKind.DATASTORE),
            ],
            relations=[
                Relation(source="Ingesta", target="Kafka", label="publica"),
                Relation(source="Kafka", target="PostgreSQL"),
                Relation(source="Fantasma", target="Kafka"),  # extremo inexistente
            ],
            risks=[Risk(description="Punto único de fallo", severity=Severity.HIGH)],
        )


@pytest.fixture
def workspace(tmp_path: Path):
    src = tmp_path / "docs"
    src.mkdir()
    return src, tmp_path / "out"


def test_documento_corto_usa_resumen_directo(workspace):
    src, out = workspace
    (src / "corto.md").write_text("Un documento breve.", encoding="utf-8")
    provider = StubProvider()

    analyse(src, out, provider=provider)

    # Una llamada de resumen (directo) + una de extracción estructurada.
    assert provider.completions == 1
    assert provider.structured_calls == 1


def test_documento_largo_usa_map_reduce(workspace):
    src, out = workspace
    parrafo = "Texto de relleno para forzar el troceado. " * 40
    contenido = "\n\n".join(parrafo for _ in range(120))
    (src / "largo.md").write_text(contenido, encoding="utf-8")
    provider = StubProvider()

    analyse(src, out, provider=provider)

    # Varios map + un reduce: más de una llamada de texto libre.
    assert provider.completions > 1, "debería haberse troceado y resumido por partes"


def test_se_generan_las_salidas(workspace):
    src, out = workspace
    (src / "doc.md").write_text("Contenido.", encoding="utf-8")

    result = analyse(src, out, provider=StubProvider())

    assert (out / "analisis.md").exists()
    assert (out / "analisis.html").exists()
    assert (out / "diagrama.mmd").exists()
    assert "markdown" in result["outputs"]


def test_directorio_vacio_no_rompe(workspace):
    src, out = workspace

    result = analyse(src, out, provider=StubProvider())

    assert result["errors"], "debería registrar que no encontró documentos"


def test_el_diagrama_descarta_relaciones_huerfanas():
    structure = StubProvider().complete_structured("", DocumentStructure)

    mermaid = build_mermaid(structure)

    assert "flowchart LR" in mermaid
    assert "Ingesta" in mermaid and "Kafka" in mermaid
    assert "Fantasma" not in mermaid, "la relación con extremo inexistente debe caer"
    assert mermaid.count("-->") == 2


def test_sin_componentes_no_hay_diagrama():
    assert build_mermaid(DocumentStructure()) == ""


def test_el_umbral_de_ruta_es_coherente():
    assert DIRECT_SUMMARY_THRESHOLD > 0
