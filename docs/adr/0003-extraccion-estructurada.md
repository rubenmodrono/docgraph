# ADR-0003 — Extracción estructurada frente a heurísticas

**Estado:** aceptada · **Fecha:** 2026-09-22

## Contexto

Para dibujar un diagrama hace falta saber qué componentes hay y cómo se
relacionan. El atajo habitual es deducirlo de la forma del texto: las
primeras líneas, las líneas cortas, las que empiezan por mayúscula.

Eso no identifica componentes. Identifica líneas. Funciona con el documento
sobre el que se ajustó la heurística y con ninguno más, y produce diagramas
que encadenan frases sueltas con flechas: tienen aspecto de arquitectura sin
describir ninguna.

## Decisión

Definir un esquema Pydantic (`DocumentStructure`) y pedir al modelo que lo
rellene. Validar la respuesta contra el esquema. Si no valida, reintentar una
vez; si vuelve a fallar, continuar sin estructura.

Además, `resolved_relations()` descarta las aristas cuyo origen o destino no
esté entre los componentes declarados.

## Consecuencias

**A favor**

- El diagrama describe componentes y relaciones, no la maquetación del texto.
- El esquema es a la vez contrato y documentación del prompt.
- El fallo es detectable: o valida o no valida.
- Filtrar relaciones huérfanas elimina el artefacto más visible de la
  extracción con LLM, que es inventarse extremos.

**En contra**

- Una llamada más al modelo.
- El esquema es deliberadamente estrecho. Documentos que describan cosas
  fuera de él (por ejemplo, modelos de datos) no se representan bien.
- Se extrae del resumen, no del texto completo: más barato y más estable,
  pero pierde componentes que solo aparezcan en secciones secundarias.

## Alternativas descartadas

- **Heurísticas sobre el texto.** El problema que motiva este ADR.
- **Extracción por fragmento y consolidación de grafos.** Más fiel, y
  probablemente el siguiente paso. Requiere resolver la deduplicación de
  componentes entre fragmentos, que no es trivial. Pendiente.
