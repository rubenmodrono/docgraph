# ADR-0001 — LangGraph sobre un pipeline lineal

**Estado:** aceptada · **Fecha:** 2026-09-22

## Contexto

El análisis de un documento es, en el caso simple, una secuencia: leer,
resumir, extraer, dibujar, escribir. Una función que llame a cinco funciones
lo resuelve, sin dependencias adicionales.

Pero hay dos puntos donde el flujo deja de ser lineal:

- El tamaño del documento decide la estrategia de resumen. Un documento corto
  se resume mejor de una vez, porque el modelo ve todo el contexto; uno largo
  obliga a map-reduce.
- La extracción estructurada puede devolver algo que no valida contra el
  esquema. Es el único punto donde el fallo es detectable y reintentable.

## Decisión

Usar LangGraph con estado tipado, aristas condicionales para el enrutado por
tamaño y un ciclo acotado para el reintento de extracción.

## Consecuencias

**A favor**

- Las dos bifurcaciones son declarativas: se leen en `graph.py` en lugar de
  estar repartidas en `if` dentro de las funciones.
- El estado es un `TypedDict` explícito. Cada nodo declara qué claves escribe.
- El grafo es inspeccionable y se puede exportar como diagrama.

**En contra**

- Una dependencia más, y no trivial.
- Para el caso corto es maquinaria de sobra: son dos nodos y una arista.
- El límite de recursión hay que subirlo a mano para acomodar el ciclo de
  reintento.

## Alternativas descartadas

- **Funciones encadenadas.** Más simple hoy, pero el enrutado y el reintento
  acaban como condicionales dispersos, que es exactamente lo que hace
  ilegibles estos pipelines cuando crecen.
- **Celery o similar.** Resuelve orquestación distribuida, problema que aquí
  no existe: esto es un proceso único y corto.
