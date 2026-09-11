"""
ingest.py
----------
Preprocesamiento: convierte documentos en chunks con metadata,
tal como se describe en el apartado "Preprocesamiento" del informe
(chunking con overlap para no perder contexto entre párrafos).
"""

from typing import List, Dict


def chunk_text(texto: str, chunk_size: int = 40, overlap: int = 10) -> List[str]:
    """
    Divide un texto en chunks de `chunk_size` palabras, con `overlap`
    palabras de traslape entre chunks consecutivos.
    """
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
    """
    Convierte la lista de documentos en una lista de chunks indexables,
    cada uno con su metadata heredada del documento original.
    """
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
