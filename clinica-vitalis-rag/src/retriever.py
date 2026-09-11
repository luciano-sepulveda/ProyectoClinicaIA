"""
retriever.py
-------------
Implementa la recuperación de información sobre el índice de chunks.

Usa una similitud por solapamiento de palabras clave (Jaccard) para
mantener el proyecto libre de dependencias externas pesadas (embeddings
reales). En un despliegue productivo, esto se reemplazaría por una base
vectorial (Chroma/FAISS/Pinecone) con embeddings semánticos, tal como
se documenta en el informe (apartado "Indexación").
"""

import re
from typing import List, Dict, Optional


STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o",
    "que", "se", "su", "sus", "por", "para", "con", "es", "esta", "esto",
    "sobre", "mi", "me", "yo", "quiero", "saber", "puedo", "tengo",
    "necesito", "hago", "hacer", "despues", "después", "que", "hay",
}


def _tokenizar(texto: str) -> set:
    texto = texto.lower()
    palabras = re.findall(r"[a-záéíóúñ0-9]+", texto)
    return {p for p in palabras if p not in STOPWORDS}


def _similitud_jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    interseccion = len(a & b)
    union = len(a | b)
    return interseccion / union if union else 0.0


def buscar(
    indice: List[Dict],
    consulta: str,
    sede_filtro: Optional[str] = None,
    categoria_filtro: Optional[str] = None,
    top_k: int = 4,
) -> List[Dict]:
    """
    Busca los `top_k` chunks más relevantes para la consulta, aplicando
    filtros opcionales de sede/categoría (filtrado híbrido: semántico +
    metadata, según se describe en el informe).
    """
    tokens_consulta = _tokenizar(consulta)

    candidatos = indice
    if sede_filtro:
        candidatos = [
            c for c in candidatos if c["sede"] in (sede_filtro, "Todas", "Externa")
        ]
    if categoria_filtro:
        candidatos = [c for c in candidatos if c["categoria"] == categoria_filtro]

    resultados = []
    for chunk in candidatos:
        score = _similitud_jaccard(tokens_consulta, _tokenizar(chunk["texto"]))
        if score > 0:
            resultados.append({**chunk, "score": score})

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]


def re_rankear(chunks: List[Dict]) -> List[Dict]:
    """
    Re-ranking: prioriza fuentes internas sobre externas cuando hay
    empate o conflicto de información, según la decisión de diseño
    justificada en el informe (apartado "Combinación de fuentes").
    """
    return sorted(
        chunks,
        key=lambda c: (c["tipo"] != "interna", -c["score"]),
    )
