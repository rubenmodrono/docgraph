"""Tests del troceado.

El presupuesto de tokens es la garantía que impide que un documento grande
se trunque en silencio, así que conviene que esté cubierta.
"""

from pathlib import Path

import pytest

from docgraph.models import Document
from docgraph.nodes.chunk import CHARS_PER_TOKEN, chunk_document, estimate_tokens


def make_doc(content: str) -> Document:
    return Document(path=Path("test.md"), content=content)


def test_documento_corto_produce_un_solo_fragmento():
    chunks = chunk_document(make_doc("Un párrafo corto."), budget=1_000)
    assert len(chunks) == 1


def test_ningun_fragmento_excede_el_presupuesto():
    budget = 100
    max_chars = budget * CHARS_PER_TOKEN
    doc = make_doc("\n\n".join(f"Párrafo número {i}. " * 20 for i in range(50)))

    chunks = chunk_document(doc, budget=budget)

    assert len(chunks) > 1, "el documento debería trocearse"
    assert all(len(c) <= max_chars for c in chunks)


def test_parrafo_mayor_que_el_presupuesto_se_parte():
    budget = 10
    doc = make_doc("x" * (budget * CHARS_PER_TOKEN * 3))

    chunks = chunk_document(doc, budget=budget)

    assert len(chunks) == 3
    assert all(len(c) <= budget * CHARS_PER_TOKEN for c in chunks)


def test_no_se_pierde_contenido_al_trocear():
    doc = make_doc("\n\n".join(f"Bloque {i}" for i in range(30)))

    recompuesto = "".join(chunk_document(doc, budget=20))

    for i in range(30):
        assert f"Bloque {i}" in recompuesto


@pytest.mark.parametrize("texto,minimo", [("", 1), ("abcd", 1), ("a" * 400, 100)])
def test_estimacion_de_tokens(texto, minimo):
    assert estimate_tokens(texto) >= minimo
