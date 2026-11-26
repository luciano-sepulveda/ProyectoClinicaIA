import hashlib
import json
import os
import time
import tracemalloc
from datetime import datetime, timezone
from functools import wraps

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT_DIR, "data", "observabilidad")
LOG_FILE = os.path.join(LOG_DIR, "ejecuciones.jsonl")


def registrar_evento(evento):
    os.makedirs(LOG_DIR, exist_ok=True)
    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **evento
    }
    with open(LOG_FILE, "a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def instrumentar_agente(clase_agente):
    if getattr(clase_agente, "_observabilidad_activa", False):
        return

    metodo_original = clase_agente.ejecutar_flujo

    @wraps(metodo_original)
    def ejecutar_con_observabilidad(self, consulta, *args, **kwargs):
        if not tracemalloc.is_tracing():
            tracemalloc.start()

        tracemalloc.reset_peak()
        inicio = time.perf_counter()
        cpu_inicio = time.process_time()

        try:
            resultado = metodo_original(self, consulta, *args, **kwargs)
            duracion_ms = (time.perf_counter() - inicio) * 1000
            cpu_ms = (time.process_time() - cpu_inicio) * 1000
            memoria_actual, memoria_pico = tracemalloc.get_traced_memory()

            registrar_evento({
                "tipo": "ejecucion",
                "estado": "correcto",
                "intencion": resultado.get("intencion", "DESCONOCIDA"),
                "ruta": resultado.get("ruta", "DESCONOCIDA"),
                "escalado": bool(resultado.get("escalado", False)),
                "herramientas": resultado.get("herramientas_usadas", []),
                "latencia_ms": round(duracion_ms, 3),
                "cpu_ms": round(cpu_ms, 3),
                "memoria_actual_mb": round(memoria_actual / 1024 / 1024, 3),
                "memoria_pico_mb": round(memoria_pico / 1024 / 1024, 3),
                "respuesta_hash": hashlib.sha256(
                    str(resultado.get("respuesta", "")).encode("utf-8")
                ).hexdigest()
            })
            return resultado

        except Exception as error:
            duracion_ms = (time.perf_counter() - inicio) * 1000
            registrar_evento({
                "tipo": "ejecucion",
                "estado": "error",
                "tipo_error": type(error).__name__,
                "latencia_ms": round(duracion_ms, 3)
            })
            raise

    clase_agente.ejecutar_flujo = ejecutar_con_observabilidad
    clase_agente._observabilidad_activa = True
