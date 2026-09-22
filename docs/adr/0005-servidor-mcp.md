# ADR-0005 — Exponer el grafo como servidor MCP

**Estado:** aceptada · **Fecha:** 2026-09-22

## Contexto

El grafo solo se podía invocar por CLI. Eso obliga a que el usuario salga de
su herramienta, prepare un directorio y luego vuelva con el resultado a mano.

El caso de uso real es el contrario: alguien está leyendo documentación
dentro de un asistente y quiere la estructura ahí mismo. El Model Context
Protocol es el estándar para eso, y el coste de adoptarlo es bajo porque la
lógica ya está aislada detrás de `analyse()`.

## Decisión

Un servidor MCP sobre stdio (`docgraph-mcp`) con dos herramientas:

- `analyse_text(text, filename)` — para contenido que el cliente ya tiene en
  contexto.
- `analyse_directory(input_dir)` — para documentos en disco.

Ambas devuelven un modelo Pydantic, de modo que el cliente recibe salida
estructurada y no texto que tenga que volver a parsear.

El SDK de MCP es un extra opcional (`pip install ".[mcp]"`), igual que el de
Gemini: quien solo use la CLI no lo instala.

### El grafo no se modifica

`analyse_text` materializa el texto en un directorio temporal en vez de
añadir una segunda vía de entrada al grafo. Y como el nodo de renderizado
siempre escribe a disco, las herramientas MCP le pasan un directorio temporal
y descartan los ficheros: el cliente quiere el contenido, no rutas.

Es menos elegante que hacer configurable el renderizado, pero mantiene un
solo camino de ejecución. Un segundo camino es un segundo sitio donde el
comportamiento puede divergir sin que los tests lo noten.

## Consecuencias

**A favor**

- El análisis se invoca desde cualquier cliente MCP sin tocar la CLI.
- La salida estructurada evita que el cliente reparsee texto.
- El grafo y sus garantías (presupuesto de tokens, reintento acotado) se
  aplican igual por las dos vías, porque son la misma.

**En contra**

- Escribir a temporales para leerlos acto seguido es trabajo de E/S
  innecesario. Con documentos grandes se nota.
- El renderizado se ejecuta y se tira. Son milisegundos, pero es gasto que no
  se aprovecha.
- Dos superficies públicas que mantener sincronizadas.

## Nota de implementación

Al desarrollarlo se detectó que un directorio sin documentos legibles llegaba
igualmente a `summarize_direct` y llamaba al modelo con un prompt vacío: gasto
facturable por analizar nada. Se añadió la guarda correspondiente y un test
con un proveedor espía que afirma que no hubo llamadas.

El caso no se había visto por CLI porque nadie apunta la CLI a un directorio
vacío. La superficie MCP lo expuso porque un cliente sí puede hacerlo.

## Alternativas descartadas

- **Solo CLI, que el cliente la invoque por shell.** Funciona, pero pierde el
  esquema de entrada y salida, y obliga al cliente a parsear stdout.
- **Transporte HTTP en vez de stdio.** Necesario si el servidor fuese remoto;
  para una herramienta local que lee ficheros del usuario, stdio evita tener
  que resolver autenticación.
