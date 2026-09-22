"""Esquemas de dominio.

La extracción de estructura se hace contra estos modelos, no contra texto
libre. Es lo que permite construir un diagrama a partir de componentes y
relaciones reales en vez de a partir de la forma del texto.
"""

from __future__ import annotations

import unicodedata
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class ComponentKind(StrEnum):
    SERVICE = "service"
    DATASTORE = "datastore"
    QUEUE = "queue"
    EXTERNAL = "external"
    UI = "ui"
    JOB = "job"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Component(BaseModel):
    """Una pieza identificable de la arquitectura descrita en el documento."""

    name: str = Field(description="Nombre corto y estable del componente")
    kind: ComponentKind = ComponentKind.UNKNOWN
    responsibility: str = Field(
        default="", description="Qué hace, en una frase"
    )

    def node_id(self) -> str:
        """Identificador ASCII seguro para Mermaid.

        `str.isalnum()` acepta caracteres acentuados, así que filtrar solo por
        él deja IDs como `c_liquidación`. Algunos renderizadores de Mermaid no
        los admiten, de modo que primero se descompone el texto y se descartan
        las marcas diacríticas.
        """
        decomposed = unicodedata.normalize("NFKD", self.name)
        ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
        cleaned = "".join(c if c.isalnum() else "_" for c in ascii_only)
        return f"c_{cleaned.lower()}"[:48]


class Relation(BaseModel):
    """Arista dirigida entre dos componentes."""

    source: str = Field(description="Nombre del componente origen")
    target: str = Field(description="Nombre del componente destino")
    label: str = Field(default="", description="Qué viaja por la relación")


class Risk(BaseModel):
    description: str
    severity: Severity = Severity.MEDIUM


class DocumentStructure(BaseModel):
    """Modelo estructurado que el LLM debe rellenar.

    Es deliberadamente pequeño: cuanto más estrecho el esquema, más fiable
    la extracción y más útil el diagrama resultante.
    """

    title: str = ""
    components: list[Component] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)

    def resolved_relations(self) -> list[Relation]:
        """Descarta relaciones que apunten a componentes inexistentes.

        Los modelos inventan extremos con cierta frecuencia; dejarlos pasar
        produce diagramas con nodos huérfanos.
        """
        known = {c.name for c in self.components}
        return [r for r in self.relations if r.source in known and r.target in known]


class Document(BaseModel):
    path: Path
    content: str

    @property
    def name(self) -> str:
        return self.path.name


class Chunk(BaseModel):
    """Fragmento de texto con presupuesto de tokens ya calculado."""

    index: int
    text: str
    estimated_tokens: int
    source: str = ""
