import os
import re
import unicodedata
from typing import List, Dict, Optional

STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "y", "o",
    "que", "se", "su", "sus", "por", "para", "con", "es", "esta", "esto",
    "sobre", "mi", "me", "yo", "quiero", "saber", "puedo", "tengo",
    "necesito", "hago", "hacer", "despues", "después", "hay",
}

# Lematizacion o expansion de terminos comunes
EQUIVALENCIAS = {
    "horario": "horarios",
    "horarios": "horario",
    "atencion": "atiende",
    "atención": "atiende",
    "atiende": "atencion",
}


def _normalizar(texto: str) -> str:
    # Quita tildes y caracteres diacriticos
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def _tokenizar(texto: str) -> set:
    texto_norm = _normalizar(texto.lower())
    palabras = re.findall(r"[a-z0-9]+", texto_norm)
    tokens = {p for p in palabras if p not in STOPWORDS}
    tokens_expandidos = set(tokens)
    for t in tokens:
        if t in EQUIVALENCIAS:
            tokens_expandidos.add(EQUIVALENCIAS[t])
        # Manejo de plural/singular simple
        if t.endswith("s") and len(t) > 3:
            tokens_expandidos.add(t[:-1])
        else:
            tokens_expandidos.add(t + "s")
    return tokens_expandidos


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
    # Busca chunks relevantes combinando similitud semantica y filtros de sede o categoria
    tokens_consulta = _tokenizar(consulta)

    candidatos = indice
    if sede_filtro:
        candidatos = [
            c for c in candidatos if c.get("sede") in (sede_filtro, "Todas", "Externa")
        ]
    if categoria_filtro:
        candidatos = [c for c in candidatos if c.get("categoria") == categoria_filtro]

    resultados = []
    for chunk in candidatos:
        # Busca en titulo, texto y categoria para capturar contexto completo
        texto_busqueda = f"{chunk.get('titulo', '')} {chunk.get('texto', '')} {chunk.get('categoria', '')}"
        tokens_doc = _tokenizar(texto_busqueda)
        score = _similitud_jaccard(tokens_consulta, tokens_doc)
        if score > 0:
            resultados.append({**chunk, "score": score})

    resultados.sort(key=lambda x: x["score"], reverse=True)
    return resultados[:top_k]


def re_rankear(chunks: List[Dict]) -> List[Dict]:
    # Prioriza documentos de fuentes internas sobre externas
    return sorted(
        chunks,
        key=lambda c: (c.get("tipo") != "interna", -c.get("score", 0)),
    )
