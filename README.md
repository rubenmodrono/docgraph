# docgraph

Analiza documentación técnica y produce un one-pager con resumen, componentes
identificados, decisiones de diseño, riesgos y un diagrama de arquitectura.

Construido sobre [LangGraph](https://github.com/langchain-ai/langgraph).

---

## El problema

Los pipelines de "resume este documento con un LLM" suelen fallar en tres
puntos, y los tres se notan justo cuando el documento es grande y de verdad
merecía la pena resumirlo:

1. **Concatenan todo en un único prompt.** Con entradas grandes, o revienta o
   se trunca en silencio. El segundo caso es peor: el resultado parece
   correcto.
2. **Infieren la estructura de la forma del texto** — primeras líneas, líneas
   cortas, encabezados. Funciona en el documento con el que se probó y en
   ningún otro.
3. **Dibujan un "diagrama" que no lo es**: una cadena `A → B → C` de frases
   sueltas, que aparenta un flujo sin describir ninguno.

`docgraph` ataca los tres explícitamente.

## Diseño

```
ingest → chunk → ┬─(corto)──→ summarize_direct ──┐
                 └─(largo)──→ summarize_map →    │
                              summarize_reduce ──┤
                                                 ↓
                        extract_structure ←──┐   │
                                 │           │   │
                                 └─(fallo)───┘   │
                                 │                │
                                 ↓                │
                          build_diagram ←─────────┘
                                 ↓
                              render → END
```

| Nodo | Responsabilidad |
| --- | --- |
| `ingest` | Carga PDF, DOCX, MD, TXT, YAML y JSON. Un fichero ilegible no aborta el lote |
| `chunk` | Trocea respetando párrafos, con presupuesto de tokens explícito |
| `summarize_*` | Directo si cabe; map-reduce si no. Lo decide el grafo, no el nodo |
| `extract_structure` | Rellena un esquema Pydantic. Reintenta una vez si no valida |
| `build_diagram` | Mermaid derivado de componentes y relaciones reales |
| `render` | Markdown y HTML |

### Decisiones

Las cuatro decisiones no obvias están documentadas como ADR:

- [ADR-0001 — LangGraph sobre un pipeline lineal](docs/adr/0001-langgraph-sobre-pipeline-lineal.md)
- [ADR-0002 — Presupuesto de tokens explícito](docs/adr/0002-presupuesto-de-tokens.md)
- [ADR-0003 — Extracción estructurada frente a heurísticas](docs/adr/0003-extraccion-estructurada.md)
- [ADR-0004 — Abstracción de proveedor LLM](docs/adr/0004-abstraccion-de-proveedor.md)

Vista de contenedores y contexto en [docs/architecture.md](docs/architecture.md).

### Dos detalles que importan

**Las relaciones se validan contra los componentes.** Los modelos inventan
extremos con cierta frecuencia; `DocumentStructure.resolved_relations()`
descarta las aristas cuyo origen o destino no exista. Es preferible un
diagrama incompleto a uno con nodos huérfanos.

**Sin componentes no hay diagrama.** Si el documento no describe una
arquitectura, `build_diagram` devuelve vacío en lugar de fabricar un flujo
que no existe.

## Uso

```bash
pip install -e ".[dev]"
cp .env.example .env    # añade GEMINI_API_KEY
docgraph --input-dir ./examples --output-dir ./output
```

Sin `GEMINI_API_KEY` el grafo se ejecuta igualmente en **modo offline**: se
recorre entero y se generan las salidas, pero el resumen y la estructura van
vacíos. Sirve para validar el cableado sin gastar cuota.

Salidas en `--output-dir`: `analisis.md`, `analisis.html` y, si hay
componentes, `diagrama.mmd`.

## Tests

```bash
pytest
```

La cobertura se concentra en el troceado, que es la garantía de que un
documento grande no se trunca en silencio.

## Limitaciones conocidas

- **La estructura se extrae del resumen, no del texto completo.** Es más
  barato y más estable, pero pierde componentes que solo aparezcan en
  secciones secundarias. La alternativa —extracción por fragmento y
  consolidación de grafos— está pendiente.
- **La estimación de tokens es aproximada** (4 caracteres por token). Se
  prefiere a atar el proyecto al tokenizador de un proveedor concreto; el
  margen de error se absorbe con un presupuesto conservador.
- **Sin caché.** Reprocesar el mismo documento vuelve a gastar cuota.
- **Solo se ha probado con documentación en español e inglés.**

## Licencia

MIT
