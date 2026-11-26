
import os
import sys
import tempfile
import time
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.documentos import DOCUMENTOS
from src.agent import AgenteClinicaVitalis
from src.ingest import construir_indice
from src.memory import SistemaMemoriaClinica
from src.observability import registrar_evento


ESCENARIOS = [
    {
        "id": "urgencia",
        "consulta": "Tengo dolor muy fuerte en el pecho y me cuesta respirar",
        "esperado": "RUTA_A_URGENCIA",
        "fragmento": "131"
    },
    {
        "id": "reserva_incompleta",
        "consulta": "Necesito agendar una cita",
        "esperado": "RUTA_B_RESERVA",
        "fragmento": "especialidad"
    },
    {
        "id": "reserva_completa",
        "consulta": "Agendar cita de dermatologia para viernes en Providencia",
        "esperado": "RUTA_B_RESERVA",
        "fragmento": "Cita confirmada"
    },
    {
        "id": "consulta_rag",
        "consulta": "Que ayuno necesito para examen de sangre",
        "esperado": "RUTA_C_CONSULTA",
        "fragmento": "ayuno de 8"
    },
    {
        "id": "consulta_sede_las_condes",
        "consulta": "Cuantas horas de ayuno requiere el examen de sangre",
        "sede": "Las Condes",
        "esperado": "RUTA_C_CONSULTA",
        "fragmento": "8 a 10 horas"
    },
    {
        "id": "horario_providencia",
        "consulta": "Cual es el horario de atencion",
        "sede": "Providencia",
        "esperado": "RUTA_C_CONSULTA",
        "fragmento": "07:30 a 19:30"
    },
    {
        "id": "sin_informacion",
        "consulta": "Necesito informacion sobre neurocirugia cuantica",
        "esperado": "RUTA_C_CONSULTA",
        "fragmento": "No tengo informacion suficiente"
    }
]


def crear_agente(directorio):
    memoria = SistemaMemoriaClinica(
        ruta_largo_plazo=os.path.join(directorio, "memoria.json")
    )
    return AgenteClinicaVitalis(
        indice=construir_indice(DOCUMENTOS),
        memoria=memoria
    )


def ejecutar_evaluacion():
    resultados = []

    with tempfile.TemporaryDirectory() as temporal:
        for escenario in ESCENARIOS:
            carpeta = os.path.join(temporal, escenario["id"])
            os.makedirs(carpeta, exist_ok=True)

            agente = crear_agente(carpeta)

            inicio = time.perf_counter()
            respuesta = agente.ejecutar_flujo(
                escenario["consulta"],
                sede=escenario.get("sede"),
                paciente="Paciente de prueba",
                ruta_archivo_citas=os.path.join(carpeta, "citas.json"),
                directorio_reportes=os.path.join(carpeta, "reportes")
            )
            latencia = (time.perf_counter() - inicio) * 1000

            ruta_correcta = (
                respuesta.get("intencion") == escenario["esperado"]
            )

            contenido_correcto = (
                escenario["fragmento"].lower()
                in respuesta.get("respuesta", "").lower()
            )

            correcto = ruta_correcta and contenido_correcto

            evento = {
                "tipo": "evaluacion",
                "escenario": escenario["id"],
                "intencion_esperada": escenario["esperado"],
                "intencion_obtenida": respuesta.get("intencion"),
                "correcto": correcto,
                "latencia_ms": round(latencia, 3),
                "escalado": bool(respuesta.get("escalado", False))
            }

            registrar_evento(evento)
            resultados.append(evento)

        carpeta_consistencia = os.path.join(temporal, "consistencia")
        os.makedirs(carpeta_consistencia, exist_ok=True)

        agente = crear_agente(carpeta_consistencia)
        consulta = "Que ayuno necesito para examen de sangre"
        hashes = []

        for numero in range(1, 4):
            inicio = time.perf_counter()

            respuesta = agente.ejecutar_flujo(
                consulta,
                paciente="Paciente de consistencia"
            )

            latencia = (time.perf_counter() - inicio) * 1000

            hash_respuesta = hashlib.sha256(
                respuesta.get("respuesta", "").encode("utf-8")
            ).hexdigest()

            hashes.append(hash_respuesta)

            registrar_evento({
                "tipo": "consistencia",
                "grupo": "consulta_rag_repetida",
                "repeticion": numero,
                "respuesta_hash": hash_respuesta,
                "latencia_ms": round(latencia, 3)
            })

        consistencia = len(set(hashes)) == 1

        registrar_evento({
            "tipo": "resumen_consistencia",
            "grupo": "consulta_rag_repetida",
            "repeticiones": len(hashes),
            "consistente": consistencia
        })

    total = len(resultados)
    aciertos = sum(1 for item in resultados if item["correcto"])

    precision = (aciertos / total * 100) if total else 0

    latencia_media = (
        sum(item["latencia_ms"] for item in resultados) / total
        if total else 0
    )

    print("\nEVALUACION DE OBSERVABILIDAD - CLINICA VITALIS")
    print(f"Escenarios evaluados: {total}")
    print(f"Escenarios correctos: {aciertos}")
    print(f"Precision operacional: {precision:.2f}%")
    print(f"Latencia media: {latencia_media:.2f} ms")
    print(f"Consistencia de respuesta: {'SI' if consistencia else 'NO'}")
    print("Registros guardados en: data/observabilidad/ejecuciones.jsonl")


if __name__ == "__main__":
    ejecutar_evaluacion()
