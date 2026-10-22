import os
import sys

# Asegurar importacion desde la raiz del proyecto
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from data.documentos import DOCUMENTOS
from src.ingest import construir_indice
from src.agent import AgenteClinicaVitalis
from src.memory import SistemaMemoriaClinica

ESCENARIOS_DEMO = [
    # Escenario 1: Urgencia / Alerta medica (Ruta A)
    {
        "paciente": "Raul Castro",
        "sede": None,
        "consulta": "Tengo un dolor muy fuerte en el pecho y me cuesta respirar, ¿que puedo tomar?",
        "descripcion": "Escenario 1: Deteccion prioritaria de Urgencia (Ruta A)"
    },
    # Escenario 2: Intencion de reserva con datos incompletos (Ruta B - El agente solicita datos faltantes)
    {
        "paciente": "Elena Morales",
        "sede": None,
        "consulta": "Hola, necesito agendar una cita por favor.",
        "descripcion": "Escenario 2: Reserva con datos faltantes (Ruta B - Adaptacion y pregunta)"
    },
    # Escenario 3: Reserva con datos completos (Ruta B - Agendamiento, Comprobante y Persistencia)
    {
        "paciente": "Elena Morales",
        "sede": "Providencia",
        "consulta": "Deseo agendar cita de dermatologia para el viernes en providencia",
        "descripcion": "Escenario 3: Reserva exitosa con emision de comprobante (Ruta B)"
    },
    # Escenario 4: Consulta Informativa RAG con filtro por sede (Ruta C)
    {
        "paciente": "Marcos Vega",
        "sede": "Providencia",
        "consulta": "¿Que ayuno requiero para el examen de sangre?",
        "descripcion": "Escenario 4: Consulta RAG oficial citando fuente (Ruta C)"
    },
    # Escenario 5: Paciente recurrente donde el agente recupera sus antecedentes de la memoria
    {
        "paciente": "Elena Morales",
        "sede": "Providencia",
        "consulta": "¿Que cuidados debo tener despues de mi atencion?",
        "descripcion": "Escenario 5: Memoria a largo plazo (El agente recuerda la cita anterior del paciente)"
    }
]


def ejecutar_modo_interactivo(agente: AgenteClinicaVitalis):
    print("\n=======================================================")
    print("  MODO INTERACTIVO CONTINUO - AGENTE CLINICA VITALIS   ")
    print("  (Escribe 'salir' para finalizar la sesion)           ")
    print("=======================================================")
    nombre_paciente = input("Ingrese nombre del paciente: ").strip() or "Paciente"

    while True:
        try:
            consulta = input(f"\n[{nombre_paciente}]: ")
        except (EOFError, KeyboardInterrupt):
            break
        if not consulta or consulta.lower() in ("salir", "exit", "quit"):
            print("Cerrando sesion interactiva.")
            break
        resultado = agente.ejecutar_flujo(consulta, paciente=nombre_paciente)
        print(f"\n[Agente Clinica Vitalis - {resultado['ruta']}]:")
        print(f"{resultado['respuesta']}")
        print(f"Herramientas invocadas: {resultado['herramientas_usadas']}")


def main():
    print("========================================================")
    print("  CLINICA VITALIS - AGENTE INTELIGENTE AUTONOMO (EP2)   ")
    print("========================================================")

    indice = construir_indice(DOCUMENTOS)
    memoria_sistema = SistemaMemoriaClinica()
    agente = AgenteClinicaVitalis(indice=indice, memoria=memoria_sistema)

    print(f"Documentos indexados en base de conocimiento: {len(indice)} chunks\n")

    for idx, escenario in enumerate(ESCENARIOS_DEMO, 1):
        print(f"\n--- {escenario['descripcion']} ---")
        print(f"Paciente ({escenario['paciente']}): \"{escenario['consulta']}\"")
        resultado = agente.ejecutar_flujo(
            escenario["consulta"],
            sede=escenario["sede"],
            paciente=escenario["paciente"]
        )
        print(f"Agente [{resultado['ruta']}]:")
        print(f"-> {resultado['respuesta']}")
        print(f"[Herramientas: {resultado['herramientas_usadas']} | Escalado Humano: {resultado['escalado']}]")

    if "--interactivo" in sys.argv:
        ejecutar_modo_interactivo(agente)


if __name__ == "__main__":
    main()
