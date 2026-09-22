"""Abstracción de proveedor LLM.

El grafo depende de este protocolo, nunca de un SDK concreto. Cambiar de
Gemini a otro modelo es añadir una implementación, no tocar los nodos.

Ver docs/adr/0004-abstraccion-de-proveedor.md
"""

from __future__ import annotations

import json
import logging
import os
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Fallo recuperable de proveedor. El grafo decide si reintenta."""


class LLMProvider(Protocol):
    """Contrato mínimo que necesita el grafo."""

    name: str

    def complete(self, prompt: str) -> str:
        """Texto libre."""
        ...

    def complete_structured(self, prompt: str, schema: type[T]) -> T:
        """Respuesta validada contra un esquema Pydantic."""
        ...


class GeminiProvider:
    """Implementación sobre el SDK google-genai."""

    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        from google import genai  # import perezoso: el SDK es opcional

        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise LLMError("Falta GEMINI_API_KEY")
        self._client = genai.Client(api_key=key)
        self.model = model

    def complete(self, prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=prompt
            )
        except Exception as exc:  # noqa: BLE001 - se reclasifica como LLMError
            raise LLMError(f"Gemini falló: {exc}") from exc

        text = getattr(response, "text", None)
        if not text:
            raise LLMError("Gemini devolvió una respuesta sin texto")
        return text.strip()

    def complete_structured(self, prompt: str, schema: type[T]) -> T:
        instruction = (
            f"{prompt}\n\n"
            "Responde EXCLUSIVAMENTE con un objeto JSON válido que cumpla "
            f"este JSON Schema. Sin markdown, sin explicaciones.\n\n"
            f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
        )
        raw = self.complete(instruction)
        return _parse_into(raw, schema)


class EchoProvider:
    """Proveedor offline determinista.

    Existe para que los tests y el modo sin clave ejecuten el grafo completo
    en vez de morir en la primera llamada. No simula inteligencia: devuelve
    estructuras vacías y lo dice explícitamente.
    """

    name = "echo"

    def complete(self, prompt: str) -> str:
        return (
            "[modo offline] No hay proveedor LLM configurado. "
            f"Se habrían procesado {len(prompt)} caracteres de prompt."
        )

    def complete_structured(self, prompt: str, schema: type[T]) -> T:
        return schema()


def _parse_into(raw: str, schema: type[T]) -> T:
    """Tolera los envoltorios habituales (```json ... ```) antes de validar."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text[3:]
        text = text.removeprefix("json").strip()

    try:
        return schema.model_validate_json(text)
    except ValidationError as exc:
        raise LLMError(f"La respuesta no cumple el esquema {schema.__name__}: {exc}") from exc
    except ValueError as exc:
        raise LLMError(f"La respuesta no es JSON válido: {exc}") from exc


def build_provider() -> LLMProvider:
    """Selecciona proveedor según entorno. Sin clave, degrada a offline."""
    if os.getenv("GEMINI_API_KEY"):
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        logger.info("Proveedor: Gemini (%s)", model)
        return GeminiProvider(model=model)

    logger.warning("Sin GEMINI_API_KEY: ejecutando en modo offline")
    return EchoProvider()
