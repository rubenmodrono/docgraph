# ADR-0004 — Abstracción de proveedor LLM

**Estado:** aceptada · **Fecha:** 2026-09-22

## Contexto

Los SDK de los proveedores cambian de API con frecuencia y arrastran árboles
de dependencias pesados. El de Google trae `cryptography`, que necesita
toolchain de Rust si no hay wheel precompilada para tu versión de Python.

Si los nodos importan el SDK directamente, cambiar de modelo obliga a tocar
todos los nodos, y los tests necesitan red o mocks del SDK.

## Decisión

Los nodos dependen de un `Protocol` con dos métodos: `complete()` y
`complete_structured()`. Las implementaciones concretas viven en
`llm/provider.py` y el SDK se importa de forma perezosa.

El SDK de Gemini es un extra opcional (`pip install ".[gemini]"`), no una
dependencia del núcleo.

## Consecuencias

**A favor**

- Los tests usan un stub de veinte líneas. Sin red, sin mocks del SDK.
- `EchoProvider` permite recorrer el grafo entero sin clave ni cuota, lo que
  hace que el cableado sea verificable por sí mismo.
- El núcleo instala sin compilar nada.
- Añadir un proveedor es añadir una clase.

**En contra**

- Una capa de indirección para un proyecto que hoy usa un solo proveedor.
- `complete_structured()` se implementa pidiendo JSON en el prompt y
  validando. Los proveedores con salida estructurada nativa lo hacen mejor;
  la abstracción no lo aprovecha todavía.

## Alternativas descartadas

- **Usar el SDK directamente.** Menos código hoy, tests con red y un
  acoplamiento que se paga en la primera migración.
- **LangChain como capa de abstracción.** Resuelve esto, pero añade una
  superficie muy grande para lo que aquí son dos métodos.
