import os
import re
from typing import Dict, Any, List, Optional
from src.tools import (
    consultar_informacion_clinica,
    agendar_o_modificar_cita,
    generar_comprobante_cita,
)
from src.memory import SistemaMemoriaClinica
from src import prompts


def cargar_entorno():
    ruta_env = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(ruta_env):
        with open(ruta_env, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    clave, valor = linea.split("=", 1)
                    os.environ.setdefault(clave.strip(), valor.strip())

cargar_entorno()

LIMITE_GIROS_CONFIG = int(os.environ.get("LIMITE_GIROS_MEMORIA", "10"))
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "simulado")

# Regex con \b y palabras intermedias entre dolor y fuerte/intenso/pecho, agregando "me cuesta respirar"
PATRONES_URGENCIA = [
    r"\bdolor\b(?:\s+\w+){0,3}\s+\b(?:fuerte|intenso)\b",
    r"\bdolor\b(?:\s+\w+){0,4}\s+\bpecho\b",
    r"\burgencia\b",
    r"\bsangrado\b",
    r"\bdesmayo\b",
    r"\bno\s+puedo\s+respirar\b",
    r"\bme\s+cuesta\s+respirar\b",
    r"\bdificultad\s+para\s+respirar\b",
    r"\bconvulsi[oó]n\b",
    r"\bemergencia\b",
    r"\basfixia\b",
    r"\binfarto\b",
]

PATRONES_RESERVA = [
    r"\bhora\b",
    r"\bcita\b",
    r"\bagendar\b",
    r"\breservar\b",
    r"\bmodificar\b",
    r"\banular\b",
    r"\bcancelar\b",
]

ESPECIALIDADES_CONOCIDAS = [
    "dermatologia", "dermatología", "cardiologia", "cardiología",
    "pediatria", "pediatría", "medicina general", "oftalmologia", "oftalmología",
    "ginecologia", "ginecología", "traumatologia", "traumatología"
]

SEDES_CONOCIDAS = ["providencia", "las condes"]

MENSAJE_URGENCIA = (
    "PROTOCOLO DE EMERGENCIA ACTIVADO: Tu consulta presenta senales de alerta medica. "
    "Por favor acude de inmediato al servicio de urgencias mas cercano o comunicate al 131."
)

MENSAJE_SIN_INFORMACION = (
    "No tengo informacion suficiente sobre esto en mis fuentes oficiales; "
    "te derivare con un miembro de nuestro equipo."
)


def detectar_urgencia(consulta: str) -> bool:
    # Evalua presencia de sintomas criticos mediante regex con limites de palabra
    consulta_lower = consulta.lower()
    for patron in PATRONES_URGENCIA:
        if re.search(patron, consulta_lower):
            return True
    return False


def extraer_datos_cita(texto: str) -> Dict[str, Optional[str]]:
    # Extrae especialidad fecha y sede reconociendo variantes con o sin tilde
    texto_lower = texto.lower()
    especialidad_encontrada = None
    for esp in ESPECIALIDADES_CONOCIDAS:
        if esp in texto_lower:
            especialidad_encontrada = esp.capitalize()
            break

    sede_encontrada = None
    for sede in SEDES_CONOCIDAS:
        if sede in texto_lower:
            sede_encontrada = "Providencia" if "providencia" in sede else "Las Condes"
            break

    # Soporta manana con o sin ñ y dias de la semana
    match_fecha = re.search(
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?|\d{1,2}:\d{2}|mañana|manana|lunes|martes|miercoles|miércoles|jueves|viernes|sabado|sábado)\b",
        texto_lower
    )
    fecha_encontrada = match_fecha.group(1) if match_fecha else None

    return {
        "especialidad": especialidad_encontrada,
        "fecha_hora": fecha_encontrada,
        "sede": sede_encontrada
    }


class AgenteClinicaVitalis:
    # Agente orquestador clinico con planificacion rutas adaptativas y memoria
    def __init__(
        self,
        indice: List[Dict[str, Any]],
        memoria: Optional[SistemaMemoriaClinica] = None,
        limite_giros: int = LIMITE_GIROS_CONFIG
    ):
        self.indice = indice
        self.memoria = memoria or SistemaMemoriaClinica(limite_giros=limite_giros)
        self.system_prompt = prompts.SYSTEM_PROMPT

    def clasificar_intencion(self, consulta: str, contexto_reciente: str = "") -> str:
        # Clasifica en urgencia reserva o consulta informativa considerando contexto reciente
        if detectar_urgencia(consulta):
            return "RUTA_A_URGENCIA"

        # Si el ultimo turno del agente fue solicitar datos faltantes, se continua en Ruta B
        lineas = [l.strip() for l in contexto_reciente.strip().split("\n") if l.strip()]
        ultimo_mensaje = lineas[-1] if lineas else ""
        if "para coordinar su cita necesito" in ultimo_mensaje.lower():
            return "RUTA_B_RESERVA"

        consulta_lower = consulta.lower()
        for patron in PATRONES_RESERVA:
            if re.search(patron, consulta_lower):
                return "RUTA_B_RESERVA"
        return "RUTA_C_CONSULTA"

    def ejecutar_flujo(
        self,
        consulta: str,
        sede: Optional[str] = None,
        paciente: str = "Paciente General",
        datos_adicionales: Optional[Dict[str, Any]] = None,
        ruta_archivo_citas: Optional[str] = None,
        directorio_reportes: Optional[str] = None
    ) -> Dict[str, Any]:
        # Orquestacion reactiva y adaptativa
        contexto_previo = self.memoria.obtener_contexto_reciente()
        self.memoria.registrar_mensaje("Paciente", consulta)
        datos_adicionales = datos_adicionales or {}

        # 1. Prioridad Maxima: Evaluacion de Urgencia
        if detectar_urgencia(consulta):
            respuesta = MENSAJE_URGENCIA
            resultado = {
                "intencion": "RUTA_A_URGENCIA",
                "ruta": "Ruta A (Urgencia/Sintomas)",
                "respuesta": respuesta,
                "escalado": True,
                "herramientas_usadas": ["ProtocoloEmergencia"],
                "detalles": {}
            }
            self.memoria.registrar_mensaje("Agente", respuesta)
            return resultado

        intencion = self.clasificar_intencion(consulta, contexto_reciente=contexto_previo)

        # 2. Ruta B: Reserva, Modificacion o Anulacion
        if intencion == "RUTA_B_RESERVA":
            accion = datos_adicionales.get("accion")
            if not accion:
                consulta_lower = consulta.lower()
                if "anular" in consulta_lower or "cancelar" in consulta_lower:
                    accion = "anular"
                elif "modificar" in consulta_lower or "cambiar" in consulta_lower:
                    accion = "modificar"
                else:
                    accion = "crear"

            # Anulacion de citas
            if accion == "anular":
                id_cita = datos_adicionales.get("id_cita")
                cita = agendar_o_modificar_cita(
                    paciente=paciente,
                    especialidad="",
                    fecha_hora="",
                    accion="anular",
                    id_cita=id_cita,
                    ruta_archivo_citas=ruta_archivo_citas
                )
                if "error" in cita:
                    respuesta = f"No se pudo anular la cita: {cita['error']}."
                else:
                    respuesta = f"Su cita ha sido anulada exitosamente para el paciente {paciente}."
                resultado = {
                    "intencion": intencion,
                    "ruta": "Ruta B (Reserva/Modificacion)",
                    "respuesta": respuesta,
                    "escalado": False,
                    "herramientas_usadas": ["AgendarOModificarCita"],
                    "detalles": {"cita": cita}
                }
                self.memoria.registrar_mensaje("Agente", respuesta)
                return resultado

            # Extraccion de datos combinando mensaje actual y contexto inmediato anterior
            lineas = [l.strip() for l in contexto_previo.strip().split("\n") if l.strip()]
            ultimo_turno = lineas[-2:] if len(lineas) >= 2 else lineas
            texto_contexto_inmediato = " ".join(ultimo_turno) + " " + consulta

            extraidos = extraer_datos_cita(consulta)
            extraidos_contexto = extraer_datos_cita(texto_contexto_inmediato)

            especialidad = datos_adicionales.get("especialidad") or extraidos["especialidad"] or extraidos_contexto["especialidad"]
            fecha_hora = datos_adicionales.get("fecha_hora") or extraidos["fecha_hora"] or extraidos_contexto["fecha_hora"]
            sede_cita = sede or datos_adicionales.get("sede") or extraidos["sede"] or extraidos_contexto["sede"]

            # Si faltan datos clave para crear la cita, solicita los faltantes
            datos_faltantes = []
            if not especialidad:
                datos_faltantes.append("la especialidad medica")
            if not fecha_hora:
                datos_faltantes.append("la fecha y hora de preferencia")
            if not sede_cita:
                datos_faltantes.append("la sede (Providencia o Las Condes)")

            if datos_faltantes and accion == "crear":
                solicitud = ", ".join(datos_faltantes)
                respuesta = f"Para coordinar su cita necesito que por favor me indique: {solicitud}."
                resultado = {
                    "intencion": intencion,
                    "ruta": "Ruta B (Reserva/Modificacion)",
                    "respuesta": respuesta,
                    "escalado": False,
                    "herramientas_usadas": ["SolicitudDatosFaltantes"],
                    "detalles": {"faltantes": datos_faltantes}
                }
                self.memoria.registrar_mensaje("Agente", respuesta)
                return resultado

            # Datos completos: ejecuta agendamiento
            cita = agendar_o_modificar_cita(
                paciente=paciente,
                especialidad=especialidad or "Medicina General",
                fecha_hora=fecha_hora or "Fecha coordinada",
                sede=sede_cita or "Providencia",
                accion=accion,
                id_cita=datos_adicionales.get("id_cita"),
                ruta_archivo_citas=ruta_archivo_citas
            )

            # Validacion segura si la herramienta devuelve error
            if "error" in cita:
                respuesta = f"No fue posible gestionar su cita médica: {cita['error']}."
                resultado = {
                    "intencion": intencion,
                    "ruta": "Ruta B (Reserva/Modificacion)",
                    "respuesta": respuesta,
                    "escalado": False,
                    "herramientas_usadas": ["AgendarOModificarCita"],
                    "detalles": {"cita": cita}
                }
                self.memoria.registrar_mensaje("Agente", respuesta)
                return resultado

            ruta_reporte = generar_comprobante_cita(cita, directorio_salida=directorio_reportes)

            # Persistir antecedente en memoria de largo plazo
            self.memoria.largo_plazo.guardar_antecedente(
                paciente=paciente,
                clave="ultima_cita",
                valor=f"{cita.get('especialidad')} el {cita.get('fecha_hora')} en sede {cita.get('sede')}"
            )

            respuesta = (
                f"Cita confirmada con exito. Codigo: {cita['id_cita']} para {cita['especialidad']} "
                f"el {cita['fecha_hora']} en sede {cita['sede']}. Comprobante generado en: {ruta_reporte}"
            )
            resultado = {
                "intencion": intencion,
                "ruta": "Ruta B (Reserva/Modificacion)",
                "respuesta": respuesta,
                "escalado": False,
                "herramientas_usadas": ["AgendarOModificarCita", "GenerarComprobanteCita"],
                "detalles": {"cita": cita, "comprobante": ruta_reporte}
            }
            self.memoria.registrar_mensaje("Agente", respuesta)
            return resultado

        # 3. Ruta C: Consulta Documental RAG con incorporacion de antecedentes
        antecedentes = self.memoria.largo_plazo.buscar_antecedentes(paciente)
        contexto_antecedentes = ""
        if antecedentes:
            recordatorios = [f"{a['clave'].replace('_', ' ')}: {a['valor']}" for a in antecedentes]
            contexto_antecedentes = f"[Nota de antecedentes del paciente: {'; '.join(recordatorios)}] "

        respuesta_rag = consultar_informacion_clinica(self.indice, consulta, sede=sede)
        escalado = "No se encontro informacion suficiente" in respuesta_rag

        if escalado:
            respuesta_final = MENSAJE_SIN_INFORMACION
        else:
            respuesta_final = f"{contexto_antecedentes}{respuesta_rag}"

        resultado = {
            "intencion": intencion,
            "ruta": "Ruta C (Dudas/Protocolos)",
            "respuesta": respuesta_final,
            "escalado": escalado,
            "herramientas_usadas": ["ConsultarInformacionClinica"],
            "detalles": {"antecedentes": antecedentes}
        }
        self.memoria.registrar_mensaje("Agente", respuesta_final)
        return resultado


def procesar_consulta(indice: List[Dict[str, Any]], consulta: str, sede: Optional[str] = None) -> Dict[str, Any]:
    # Compatibilidad con flujos y pruebas anteriores
    agente = AgenteClinicaVitalis(indice=indice)
    resultado = agente.ejecutar_flujo(consulta, sede=sede)
    return {
        "respuesta": resultado["respuesta"],
        "escalado": resultado["escalado"],
        "chunks_usados": ["herramienta_ejecutada"] if not resultado["escalado"] else []
    }
