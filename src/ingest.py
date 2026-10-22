import os
import re
from typing import List, Dict


def chunk_text(texto: str, chunk_size: int = 50, overlap: int = 15) -> List[str]:
    # Divide texto respetando limites de palabras y overlap
    palabras = texto.split()
    if len(palabras) <= chunk_size:
        return [texto]

    chunks = []
    inicio = 0
    while inicio < len(palabras):
        fin = inicio + chunk_size
        chunk = " ".join(palabras[inicio:fin])
        chunks.append(chunk)
        if fin >= len(palabras):
            break
        inicio = fin - overlap
    return chunks


def construir_indice(documentos: List[Dict]) -> List[Dict]:
    # Convierte documentos en chunks indexables con metadata completa
    indice = []
    for doc in documentos:
        chunks = chunk_text(doc["texto"])
        for i, chunk in enumerate(chunks):
            indice.append(
                {
                    "chunk_id": f"{doc['id']}_chunk{i}",
                    "doc_id": doc["id"],
                    "titulo": doc["titulo"],
                    "sede": doc["sede"],
                    "tipo": doc["tipo"],
                    "categoria": doc["categoria"],
                    "texto": chunk,
                }
            )
    return indice
