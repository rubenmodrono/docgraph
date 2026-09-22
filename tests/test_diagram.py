"""Tests de la generación del diagrama.

El diagrama es la salida más visible, y sus dos modos de fallo son silenciosos:
IDs que el renderizador rechaza, y etiquetas cortadas a media palabra que
parecen datos corruptos.
"""

from docgraph.models import Component, ComponentKind, DocumentStructure, Relation
from docgraph.nodes.diagram import _truncate, build_mermaid


def test_id_de_nodo_es_ascii_pese_a_los_acentos():
    # `str.isalnum()` acepta 'ó', así que el filtro ingenuo la dejaría pasar.
    assert Component(name="Motor de Liquidación").node_id() == "c_motor_de_liquidacion"


def test_id_de_nodo_sustituye_separadores():
    assert Component(name="API-Gateway v2").node_id() == "c_api_gateway_v2"


def test_sin_componentes_no_hay_diagrama():
    assert build_mermaid(DocumentStructure()) == ""


def test_cada_tipo_usa_su_forma():
    structure = DocumentStructure(
        components=[
            Component(name="Ingesta", kind=ComponentKind.SERVICE),
            Component(name="Cola", kind=ComponentKind.QUEUE),
            Component(name="Postgres", kind=ComponentKind.DATASTORE),
            Component(name="Core", kind=ComponentKind.EXTERNAL),
        ]
    )

    mermaid = build_mermaid(structure)

    assert 'c_ingesta["Ingesta"]' in mermaid
    assert 'c_cola>"Cola"]' in mermaid
    assert 'c_postgres[("Postgres")]' in mermaid
    assert 'c_core{{"Core"}}' in mermaid


def test_se_descartan_relaciones_con_extremos_inexistentes():
    structure = DocumentStructure(
        components=[Component(name="A"), Component(name="B")],
        relations=[
            Relation(source="A", target="B", label="ok"),
            Relation(source="A", target="Fantasma", label="inventada"),
        ],
    )

    mermaid = build_mermaid(structure)

    assert "c_a -- \"ok\" --> c_b" in mermaid
    assert "Fantasma" not in mermaid
    assert "inventada" not in mermaid


def test_etiqueta_larga_se_corta_por_palabra():
    resultado = _truncate("interactúa para finalización de operaciones", 40)

    assert resultado.endswith("…")
    assert not resultado.startswith("interactúa para finalización de operacio…")
    assert " " not in resultado[-2:], "no debe quedar un espacio antes de los puntos"
    assert len(resultado) <= 40


def test_texto_corto_no_se_toca():
    assert _truncate("corto", 40) == "corto"


def test_palabra_unica_mas_larga_que_el_limite_se_corta_igual():
    resultado = _truncate("x" * 60, 10)
    assert len(resultado) == 10
    assert resultado.endswith("…")
