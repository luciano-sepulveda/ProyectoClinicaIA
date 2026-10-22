import os
import json
import re
from typing import List, Dict, Any, Optional

RUTA_MEMORIA_LARGO_PLAZO = os.path.join(os.path.dirname(__file__), "..", "data", "memoria_largo_plazo.json")


class MemoriaCortoPlazo:
    # Gestor de memoria a corto plazo para ventana de conversacion activa
    def __init__(self, limite_giros: int = 10):
        self.limite_giros = limite_giros
        self.historial: List[Dict[str, str]] = []

    def agregar_interaccion(self, rol: str, contenido: str):
        self.historial.append({"rol": rol, "contenido": contenido})
        if len(self.historial) > self.limite_giros * 2:
            self.historial = self.historial[-self.limite_giros * 2:]

    def obtener_historial(self) -> List[Dict[str, str]]:
        return list(self.historial)

    def limpiar(self):
        self.historial.clear()


class MemoriaLargoPlazo:
    # Gestor de memoria a largo plazo persistente en disco JSON
    def __init__(self, ruta_archivo: Optional[str] = None):
        self.ruta_archivo = ruta_archivo or RUTA_MEMORIA_LARGO_PLAZO
        self.registros: List[Dict[str, Any]] = self._cargar()

    def _cargar(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.ruta_archivo):
            try:
                with open(self.ruta_archivo, "r", encoding="utf-8") as archivo:
                    return json.load(archivo)
            except Exception:
                return []
        return []

    def _guardar(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.ruta_archivo)), exist_ok=True)
        with open(self.ruta_archivo, "w", encoding="utf-8") as archivo:
            json.dump(self.registros, archivo, ensure_ascii=False, indent=2)

    def guardar_antecedente(self, paciente: str, clave: str, valor: str):
        registro = {
            "paciente": paciente.lower().strip(),
            "clave": clave.lower().strip(),
            "valor": valor.strip()
        }
        for item in self.registros:
            if item["paciente"] == registro["paciente"] and item["clave"] == registro["clave"]:
                item["valor"] = registro["valor"]
                self._guardar()
                return
        self.registros.append(registro)
        self._guardar()

    def buscar_antecedentes(self, paciente: str, consulta: str = "") -> List[Dict[str, Any]]:
        paciente_lower = paciente.lower().strip()
        terminos = [t for t in re.findall(r"[a-záéíóúñ0-9]+", consulta.lower()) if len(t) > 2]
        resultados = []
        for reg in self.registros:
            if reg["paciente"] == paciente_lower:
                if not terminos:
                    resultados.append(reg)
                else:
                    texto = f"{reg['clave']} {reg['valor']}".lower()
                    if any(t in texto for t in terminos):
                        resultados.append(reg)
        return resultados


class SistemaMemoriaClinica:
    # Unifica la memoria de corto plazo y largo plazo con persistencia
    def __init__(self, limite_giros: int = 10, ruta_largo_plazo: Optional[str] = None):
        self.corto_plazo = MemoriaCortoPlazo(limite_giros=limite_giros)
        self.largo_plazo = MemoriaLargoPlazo(ruta_archivo=ruta_largo_plazo)

    def registrar_mensaje(self, rol: str, contenido: str):
        self.corto_plazo.agregar_interaccion(rol, contenido)

    def obtener_contexto_reciente(self) -> str:
        lineas = []
        for turno in self.corto_plazo.obtener_historial():
            lineas.append(f"{turno['rol']}: {turno['contenido']}")
        return "\n".join(lineas)

    def obtener_resumen_antecedentes(self, paciente: str) -> str:
        antecedentes = self.largo_plazo.buscar_antecedentes(paciente)
        if not antecedentes:
            return ""
        items = [f"{a['clave'].replace('_', ' ').capitalize()}: {a['valor']}" for a in antecedentes]
        return "Antecedentes y preferencias del paciente:\n" + "\n".join(f"- {item}" for item in items)
