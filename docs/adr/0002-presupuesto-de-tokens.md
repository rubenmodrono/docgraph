# ADR-0002 — Presupuesto de tokens explícito

**Estado:** aceptada · **Fecha:** 2026-09-22

## Contexto

El fallo más común de estos pipelines es concatenar todos los documentos en
un string y mandarlo en un único prompt. Con entradas grandes pasa una de dos
cosas: la llamada falla, o el proveedor trunca la entrada.

El segundo caso es el peligroso. No hay excepción, no hay aviso, y el
resumen resultante parece correcto: está bien escrito y es coherente. Solo
que describe el primer 15% del documento.

## Decisión

Trocear siempre, con un presupuesto por fragmento declarado como constante
(`CHUNK_TOKEN_BUDGET = 6000`). El troceado respeta párrafos y solo recurre a
un corte duro cuando un párrafo por sí solo excede el presupuesto.

La estimación de tokens es una aproximación por caracteres (4 por token) en
lugar de un tokenizador real.

## Consecuencias

**A favor**

- El truncamiento silencioso deja de ser posible.
- Sin dependencia de `tiktoken` ni del tokenizador de ningún proveedor, que
  además no coincide entre modelos.
- El presupuesto es un número visible y ajustable, no un efecto emergente.

**En contra**

- La estimación tiene error. Se compensa con un presupuesto conservador que
  deja hueco para la instrucción y la respuesta.
- Texto no latino (CJK) tiene una relación caracteres/token muy distinta; el
  proyecto no está validado para esos idiomas.

## Alternativas descartadas

- **`tiktoken`.** Exacto para modelos OpenAI e inexacto para el resto. Ata el
  proyecto a un proveedor para ganar una precisión que el margen ya absorbe.
- **Confiar en el límite del proveedor.** Es precisamente el fallo que este
  ADR existe para evitar.
