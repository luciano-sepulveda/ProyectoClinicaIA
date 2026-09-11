# Clínica Vitalis — Agente LLM + RAG

Prototipo funcional del agente de atención a pacientes de Clínica Vitalis,
desarrollado para la Evaluación Parcial N°1 de ISY0101 (Ingeniería de
Soluciones con IA, Duoc UC).

## Descripción

El sistema responde consultas administrativas frecuentes de pacientes
(preparación de exámenes, indicaciones post-consulta, cobertura de
convenios), recuperando información desde documentos internos y guías
MINSAL (fuente externa), y deriva automáticamente a un profesional humano
cuando detecta urgencia o falta de información en las fuentes oficiales.

## Estructura del repositorio

```
clinica-vitalis-rag/
├── main.py                  # Demo por consola del flujo completo
├── data/
│   └── documentos.py        # Documentos de ejemplo (internos y externos)
├── src/
│   ├── prompts.py           # Los 3 prompts diseñados (system, query, generación)
│   ├── ingest.py            # Chunking + construcción del índice
│   ├── retriever.py         # Búsqueda por similitud + re-ranking (interno > externo)
│   └── agent.py             # Orquestador: clasificación de urgencia + generación
├── tests/
│   └── test_pipeline.py     # Pruebas unitarias de cada módulo
└── diagrams/
    └── arquitectura_clinica_vitalis.mermaid   # Diagrama de arquitectura (IE4/IE7)
```

## Cómo ejecutar

Requiere Python 3.8+ (sin dependencias externas).

```bash
# Clonar el repositorio y entrar a la carpeta
cd clinica-vitalis-rag

# Ejecutar la demo con 4 consultas de ejemplo
python3 main.py

# Ejecutar las pruebas unitarias
python3 -m unittest discover -s tests -v
```

## Cómo funciona (mapeo con el informe técnico)

1. **`data/documentos.py`**: simula las fuentes internas (manuales,
   convenios) y externas (guías MINSAL) descritas en el pipeline RAG.
2. **`src/ingest.py`**: aplica chunking con overlap y agrega metadata
   (sede, tipo, categoría) a cada fragmento, tal como se documenta en
   el apartado "Preprocesamiento".
3. **`src/retriever.py`**: busca los fragmentos más relevantes mediante
   similitud de palabras clave, filtra por sede/categoría, y aplica
   re-ranking priorizando fuentes internas sobre externas.
4. **`src/agent.py`**: orquesta el flujo — detecta urgencia (escalamiento
   inmediato), reformula la consulta, recupera contexto y genera la
   respuesta final citando la fuente.
5. **`src/prompts.py`**: contiene el texto exacto de los 3 prompts
   diseñados y justificados en el informe (system, reformulación de
   consulta, generación de respuesta).

## Nota importante sobre el LLM utilizado

Este prototipo usa una **generación simulada basada en reglas**
(`generar_respuesta()` en `src/agent.py`) en lugar de una llamada real a
un LLM, ya que el proyecto no incluye una clave de API. La lógica
implementada respeta fielmente el comportamiento definido en los prompts
(no alucinar, citar fuente, derivar si falta información).

Para conectar un LLM real (OpenAI, Anthropic, etc.), reemplazar la función
`generar_respuesta()` por una llamada a la API usando `prompts.SYSTEM_PROMPT`
y `prompts.GENERATION_PROMPT_TEMPLATE`, por ejemplo:

```python
respuesta = cliente_llm.generar(
    system=prompts.SYSTEM_PROMPT,
    prompt=prompts.GENERATION_PROMPT_TEMPLATE.format(
        contexto_recuperado=contexto, pregunta_paciente=consulta
    ),
)
```

## Limitaciones conocidas

- La búsqueda usa similitud de palabras clave (Jaccard), no embeddings
  semánticos reales. Un despliegue productivo debería usar una base
  vectorial (Chroma/FAISS/Pinecone) con embeddings, como se indica en el
  informe técnico, para mejorar el recall ante sinónimos o paráfrasis.
- El clasificador de urgencia usa una lista fija de palabras clave; en
  producción debería reforzarse con un modelo de clasificación entrenado
  o un prompt de clasificación dedicado.

## Evidencia de pruebas

Las 9 pruebas unitarias en `tests/test_pipeline.py` cubren: chunking con
overlap, generación de metadata, búsqueda con y sin filtro de sede,
re-ranking interno/externo, detección de urgencia, escalamiento por falta
de información, y citación de fuente en la respuesta final. Todas pasan
exitosamente (`OK`, 9/9).

## Declaración de uso de IA

Ver declaración completa en el informe técnico (`InformeTecnico.pdf`).
Este código fue desarrollado con apoyo de IA (Claude, Anthropic) para la
estructura y redacción; la lógica de diseño fue validada por el equipo.
