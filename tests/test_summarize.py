"""Tests del resumen.

Lo que se protege aquí es el gasto: cada llamada al proveedor se factura, así
que las rutas que no tienen nada que resumir no deben llegar al modelo.
"""

import pytest

from docgraph.models import Chunk
from docgraph.nodes.summarize import (
    DIRECT_SUMMARY_THRESHOLD,
    needs_map_reduce,
    summarize_direct,
    summarize_map,
    summarize_reduce,
)


class SpyProvider:
    """Cuenta llamadas para poder afirmar que no se hicieron."""

    name = "spy"

    def __init__(self):
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return "resumen simulado"

    def complete_structured(self, prompt, schema):
        self.calls.append(prompt)
        return schema()


def chunk(text: str, index: int = 0) -> Chunk:
    return Chunk(index=index, text=text, estimated_tokens=len(text) // 4 or 1)


def test_sin_fragmentos_no_se_llama_al_modelo():
    spy = SpyProvider()

    resultado = summarize_direct({"chunks": []}, provider=spy)

    assert spy.calls == [], "un directorio vacío no debe generar gasto"
    assert resultado["summary"] == ""


def test_con_fragmentos_si_se_llama():
    spy = SpyProvider()

    resultado = summarize_direct({"chunks": [chunk("contenido")]}, provider=spy)

    assert len(spy.calls) == 1
    assert resultado["summary"] == "resumen simulado"


def test_reduce_sin_parciales_no_llama_y_avisa():
    spy = SpyProvider()

    resultado = summarize_reduce({"chunk_summaries": []}, provider=spy)

    assert spy.calls == []
    assert resultado["errors"]


def test_map_hace_una_llamada_por_fragmento():
    spy = SpyProvider()
    chunks = [chunk(f"parte {i}", i) for i in range(3)]

    resultado = summarize_map({"chunks": chunks}, provider=spy)

    assert len(spy.calls) == 3
    assert len(resultado["chunk_summaries"]) == 3


@pytest.mark.parametrize(
    "tokens,esperado",
    [
        (0, "summarize_direct"),
        (DIRECT_SUMMARY_THRESHOLD, "summarize_direct"),
        (DIRECT_SUMMARY_THRESHOLD + 1, "summarize_map"),
    ],
)
def test_enrutado_por_tamano(tokens, esperado):
    assert needs_map_reduce({"total_tokens": tokens}) == esperado
