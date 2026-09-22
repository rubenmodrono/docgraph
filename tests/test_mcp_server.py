"""Tests del servidor MCP.

El decorador `@server.tool()` devuelve la función intacta y la registra como
efecto secundario, así que las herramientas se pueden invocar directamente.
"""

import asyncio

import pytest

pytest.importorskip("mcp", reason="el extra 'mcp' no está instalado")

from docgraph.mcp_server import (  # noqa: E402
    AnalysisResult,
    analyse_directory,
    analyse_text,
    server,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Fuerza el proveedor offline: los tests no llaman a ninguna API."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def test_las_dos_herramientas_estan_registradas():
    nombres = {t.name for t in asyncio.run(server.list_tools())}
    assert {"analyse_text", "analyse_directory"} <= nombres


def test_analyse_text_devuelve_resultado_estructurado():
    resultado = analyse_text("# Servicio\n\nPublica eventos en una cola.")

    assert isinstance(resultado, AnalysisResult)
    # En modo offline no hay extracción, pero el grafo debe recorrerse entero.
    assert resultado.components == []


def test_analyse_text_rechaza_texto_vacio():
    with pytest.raises(ValueError, match="vacío"):
        analyse_text("   \n  ")


def test_analyse_text_no_deja_ficheros_tras_de_si(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    analyse_text("contenido de prueba")

    sobrantes = [p for p in tmp_path.iterdir() if p.name.startswith("docgraph-")]
    assert sobrantes == [], f"directorios temporales sin limpiar: {sobrantes}"


def test_analyse_directory_rechaza_ruta_inexistente():
    with pytest.raises(ValueError, match="No es un directorio"):
        analyse_directory("/ruta/que/no/existe/en/ningun/sitio")


def test_analyse_directory_lee_los_documentos(tmp_path):
    (tmp_path / "doc.md").write_text("# Arquitectura\n\nUn servicio.", encoding="utf-8")

    resultado = analyse_directory(str(tmp_path))

    assert isinstance(resultado, AnalysisResult)
    assert resultado.warnings == []


def test_directorio_vacio_avisa_en_lugar_de_reventar(tmp_path):
    resultado = analyse_directory(str(tmp_path))

    assert resultado.summary == ""
    assert any("documento" in w for w in resultado.warnings)
