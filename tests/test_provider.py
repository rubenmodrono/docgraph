"""Tests de la selección y construcción de proveedor.

El SDK de Gemini es un extra opcional. Que falte es un estado esperado, no
un error del programa, así que debe producir un mensaje accionable y no un
ImportError a mitad de la construcción del grafo.
"""

import sys

import pytest

from docgraph.llm.provider import (
    EchoProvider,
    GeminiProvider,
    LLMError,
    _parse_into,
    build_provider,
)
from docgraph.models import DocumentStructure


def test_sin_clave_degrada_a_offline(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert isinstance(build_provider(), EchoProvider)


def test_sdk_ausente_da_error_accionable(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    # Bloquea el import del SDK sin desinstalarlo.
    monkeypatch.setitem(sys.modules, "google", None)

    with pytest.raises(LLMError) as exc:
        GeminiProvider()

    mensaje = str(exc.value)
    assert "google-genai" in mensaje
    assert "pip install" in mensaje


def test_falta_de_clave_es_llmerror(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    pytest.importorskip("google.genai")

    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        GeminiProvider()


def test_echo_devuelve_estructura_vacia_valida():
    resultado = EchoProvider().complete_structured("lo que sea", DocumentStructure)
    assert isinstance(resultado, DocumentStructure)
    assert resultado.components == []


@pytest.mark.parametrize(
    "crudo",
    [
        '{"title": "X"}',
        '```json\n{"title": "X"}\n```',
        '```\n{"title": "X"}\n```',
    ],
)
def test_parseo_tolera_envoltorios_markdown(crudo):
    assert _parse_into(crudo, DocumentStructure).title == "X"


def test_json_invalido_da_llmerror():
    with pytest.raises(LLMError):
        _parse_into("esto no es json", DocumentStructure)
