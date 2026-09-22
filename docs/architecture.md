# Arquitectura

Notación [C4](https://c4model.com/), niveles 1 y 2. El nivel 3 no aporta
aquí: los componentes internos son los nodos del grafo y están descritos en
el README.

## Nivel 1 — Contexto

```mermaid
flowchart LR
    analista(["Analista técnico"])
    docgraph["<b>docgraph</b><br/>Analiza documentación<br/>y genera un one-pager"]
    fuentes[("Documentación<br/>PDF · DOCX · MD · TXT")]
    llm{{"Proveedor LLM<br/>Gemini"}}
    salidas[("One-pager<br/>MD · HTML · Mermaid")]

    analista -- "ejecuta sobre un directorio" --> docgraph
    fuentes -- "se leen" --> docgraph
    docgraph -- "resumen y extracción" --> llm
    docgraph -- "escribe" --> salidas
    analista -- "lee" --> salidas
```

## Nivel 2 — Contenedores

```mermaid
flowchart TB
    cli["<b>CLI</b><br/>argparse<br/><i>__main__.py</i>"]

    subgraph grafo["Grafo — LangGraph"]
        direction TB
        ingest["ingest"]
        chunk["chunk"]
        sum_d["summarize_direct"]
        sum_m["summarize_map"]
        sum_r["summarize_reduce"]
        extract["extract_structure"]
        diagram["build_diagram"]
        render["render"]

        ingest --> chunk
        chunk -. "≤ umbral" .-> sum_d
        chunk -. "> umbral" .-> sum_m
        sum_m --> sum_r
        sum_d --> extract
        sum_r --> extract
        extract -. "no valida" .-> extract
        extract --> diagram
        diagram --> render
    end

    estado[("<b>DocGraphState</b><br/>TypedDict")]
    provider["<b>LLMProvider</b><br/>Protocol"]
    gemini["GeminiProvider"]
    echo["EchoProvider<br/><i>offline</i>"]

    cli --> grafo
    grafo <--> estado
    sum_d & sum_m & sum_r & extract --> provider
    provider -.implementa.- gemini
    provider -.implementa.- echo
```

## Puntos de extensión

| Quiero… | Toco… |
| --- | --- |
| Añadir un proveedor | Una clase en `llm/provider.py` que cumpla el protocolo |
| Soportar otro formato | Un lector en `nodes/ingest.py` y su entrada en `_READERS` |
| Cambiar el modelo extraído | `models.py`; el diagrama y el render se adaptan solos |
| Añadir un paso | Un nodo en `nodes/` y su arista en `graph.py` |

## Flujo del estado

Cada nodo recibe el estado completo y devuelve **solo las claves que
modifica**; LangGraph las mezcla. Dos claves usan reducción aditiva
(`operator.add`) porque se escriben desde varios puntos:

- `chunk_summaries` — la fase map acumula un resumen por fragmento.
- `errors` — cualquier nodo puede registrar una incidencia sin abortar.

Esa distinción es lo que permite que el pipeline **degrade en lugar de
romperse**: un fragmento que falla resta calidad al resumen, no invalida la
ejecución.
