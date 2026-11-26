import os
import json
import re
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from langchain.tools import tool
except ImportError:
    # Decorador @tool compatible
    def tool(func):
        func.is_tool = True
        return func

from src.retriever import buscar, re_rankear

RUTA_CITAS = os.path.join(os.path.dirname(__file__), "..", "data", "citas.json")
DIRECTORIO_REPORTES = os.path.join(os.path.dirname(__file__), "..", "data", "reportes")


@tool
def consultar_informacion_clinica(indice: list, consulta: str, sede: str = None) -> str:
    # Consulta informacion clinica y protocolos en el indice documental
    fragmentos = buscar(indice, consulta, sede_filtro=sede)
    fragmentos_ordenados = re_rankear(fragmentos)
    if not fragmentos_ordenados:
        return "No se encontro informacion suficiente en los documentos oficiales."
    mejor = fragmentos_ordenados[0]
    fuente = mejor.get("titulo", "Documento oficial")
    if mejor.get("sede") and mejor["sede"] not in ("Todas", "Externa"):
        fuente += f", sede {mejor['sede']}"
    return f"{mejor['texto']} (Fuente: {fuente})"


@tool
def agendar_o_modificar_cita(
    paciente: str,
    especialidad: str,
    fecha_hora: str,
    sede: str = "Providencia",
    accion: str = "crear",
    id_cita: Optional[str] = None,
    ruta_archivo_citas: Optional[str] = None
) -> Dict[str, Any]:
    # Gestiona creacion modificacion o anulacion de citas medicas
    ruta_final = ruta_archivo_citas or RUTA_CITAS
    os.makedirs(os.path.dirname(os.path.abspath(ruta_final)), exist_ok=True)
    citas = []
    if os.path.exists(ruta_final):
        try:
            with open(ruta_final, "r", encoding="utf-8") as archivo:
                citas = json.load(archivo)
        except Exception:
            citas = []

    accion_normalizada = (accion or "crear").lower().strip()

    if accion_normalizada == "anular":
        cita_encontrada = None
        for c in citas:
            if (id_cita and c.get("id_cita") == id_cita) or (c.get("paciente", "").lower() == paciente.lower() and c.get("estado") != "Anulada"):
                c["estado"] = "Anulada"
                c["actualizado_en"] = datetime.now().isoformat()
                cita_encontrada = c
                break
        if not cita_encontrada:
            return {"error": "Cita no encontrada para anular", "estado": "No encontrada"}
        with open(ruta_final, "w", encoding="utf-8") as archivo:
            json.dump(citas, archivo, ensure_ascii=False, indent=2)
        return cita_encontrada

    if accion_normalizada == "modificar":
        cita_encontrada = None
        for c in citas:
            if (id_cita and c.get("id_cita") == id_cita) or (c.get("paciente", "").lower() == paciente.lower() and c.get("estado") != "Anulada"):
                if especialidad:
                    c["especialidad"] = especialidad
                if fecha_hora:
                    c["fecha_hora"] = fecha_hora
                if sede:
                    c["sede"] = sede
                c["estado"] = "Modificada"
                c["actualizado_en"] = datetime.now().isoformat()
                cita_encontrada = c
                break
        if not cita_encontrada:
            return {"error": "Cita no encontrada para modificar", "estado": "No encontrada"}
        with open(ruta_final, "w", encoding="utf-8") as archivo:
            json.dump(citas, archivo, ensure_ascii=False, indent=2)
        return cita_encontrada

    # Accion por defecto: crear cita
    nuevo_id = f"CITA-{len(citas) + 1:04d}"
    nueva_cita = {
        "id_cita": nuevo_id,
        "paciente": paciente,
        "especialidad": especialidad,
        "fecha_hora": fecha_hora,
        "sede": sede,
        "estado": "Confirmada",
        "creado_en": datetime.now().isoformat()
    }
    citas.append(nueva_cita)

    with open(ruta_final, "w", encoding="utf-8") as archivo:
        json.dump(citas, archivo, ensure_ascii=False, indent=2)

    return nueva_cita


@tool
def generar_comprobante_cita(datos_cita: Dict[str, Any], directorio_salida: Optional[str] = None) -> str:
    # Genera un comprobante de atencion en archivo de texto
    if "error" in datos_cita:
        return ""
    dir_final = directorio_salida or DIRECTORIO_REPORTES
    os.makedirs(dir_final, exist_ok=True)
    id_cita = datos_cita.get("id_cita", "SIN_ID")
    nombre_archivo = f"comprobante_{id_cita}.txt"
    ruta_archivo = os.path.join(dir_final, nombre_archivo)

    contenido = (
        "========================================\n"
        "      CLINICA VITALIS - COMPROBANTE     \n"
        "========================================\n"
        f"Codigo Cita   : {datos_cita.get('id_cita')}\n"
        f"Paciente      : {datos_cita.get('paciente')}\n"
        f"Especialidad  : {datos_cita.get('especialidad')}\n"
        f"Fecha y Hora  : {datos_cita.get('fecha_hora')}\n"
        f"Sede          : {datos_cita.get('sede')}\n"
        f"Estado        : {datos_cita.get('estado')}\n"
        "========================================\n"
        "Por favor presentarse 15 minutos antes.\n"
    )

    with open(ruta_archivo, "w", encoding="utf-8") as archivo:
        archivo.write(contenido)

    return ruta_archivo
