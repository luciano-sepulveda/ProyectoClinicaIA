"""
agent.py
---------
Orquestador del flujo completo, siguiendo el diagrama de arquitectura
del informe:

  paciente -> clasificador de intención -> (RAG | escalamiento humano)
           -> generación de respuesta -> validación -> respuesta/escalamiento
"""

from typing import Dict, List
from src import prompts
from src.retriever import buscar, re_rankear

# Palabras clave que gatillan escalamiento inmediato a un humano
# (urgencia, síntomas, dolor agudo). Ver restricción normativa del informe.
PALABRAS_URGENCIA = [
    "dolor fuerte", "dolor intenso", "urgencia", "sangrado", "desmayo",
    "no puedo respirar", "convulsion", "convulsión", "emergencia",
]

MENSAJE_ESCALAMIENTO = (
    "Esta consulta requiere la evaluación de un profesional de salud. "
    "Te derivaré con un miembro de nuestro equipo de inmediato."
)

MENSAJE_SIN_INFORMACION = (
    "No tengo información suficiente sobre esto en mis fuentes "
    "disponibles; te derivaré con un miembro de nuestro equipo."
)


def detectar_urgencia(consulta: str) -> bool:
    consulta_lower = consulta.lower()
    return any(palabra in consulta_lower for palabra in PALABRAS_URGENCIA)


def reformular_consulta(consulta: str) -> str:
    """
    Aplica el prompt de reformulación de consulta.
    NOTA: aquí se simula la salida del LLM. Para producción, reemplazar
    por una llamada real, por ejemplo:

        prompt = prompts.QUERY_REWRITE_PROMPT_TEMPLATE.format(
            input_paciente=consulta
        )
        respuesta = llamar_llm_real(prompt)
    """
    # Simulación simple: se limpia la consulta y se usa tal cual.
    # (la lógica real de extracción de keywords ocurre en el retriever)
    return consulta.strip()


def generar_respuesta(consulta: str, chunks: List[Dict]) -> str:
    """
    Aplica el prompt de generación final. Simulado con reglas simples
    que respetan el comportamiento exigido por el prompt (citar fuente,
    no alucinar, fallback si no hay contexto).

    Para producción, reemplazar por una llamada real, por ejemplo:

        prompt = prompts.GENERATION_PROMPT_TEMPLATE.format(
            contexto_recuperado=contexto, pregunta_paciente=consulta
        )
        respuesta = llamar_llm_real(prompt, system=prompts.SYSTEM_PROMPT)
    """
    if not chunks:
        return MENSAJE_SIN_INFORMACION

    mejor = chunks[0]
    fuente = f"{mejor['titulo']}" + (
        f", sede {mejor['sede']}" if mejor["sede"] not in ("Todas", "Externa") else ""
    )
    return f"{mejor['texto']} (Fuente: {fuente})"


def procesar_consulta(
    indice: List[Dict], consulta: str, sede: str = None
) -> Dict:
    """
    Punto de entrada principal del agente. Devuelve un dict con el
    resultado y metadata de trazabilidad (para pruebas/evaluación).
    """
    if detectar_urgencia(consulta):
        return {
            "respuesta": MENSAJE_ESCALAMIENTO,
            "escalado": True,
            "chunks_usados": [],
        }

    consulta_reformulada = reformular_consulta(consulta)
    chunks = buscar(indice, consulta_reformulada, sede_filtro=sede)
    chunks = re_rankear(chunks)

    if not chunks:
        return {
            "respuesta": MENSAJE_SIN_INFORMACION,
            "escalado": True,
            "chunks_usados": [],
        }

    respuesta = generar_respuesta(consulta_reformulada, chunks)
    return {
        "respuesta": respuesta,
        "escalado": False,
        "chunks_usados": [c["chunk_id"] for c in chunks],
    }
