import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.documentos import DOCUMENTOS
from src.ingest import chunk_text, construir_indice
from src.retriever import buscar, re_rankear
from src.agent import AgenteClinicaVitalis, detectar_urgencia, procesar_consulta, extraer_datos_cita
from src.tools import (
    consultar_informacion_clinica,
    agendar_o_modificar_cita,
    generar_comprobante_cita,
)
from src.memory import SistemaMemoriaClinica, MemoriaLargoPlazo


class TestIngest(unittest.TestCase):
    def test_chunking_respeta_overlap(self):
        texto = " ".join([f"palabra{i}" for i in range(120)])
        chunks = chunk_text(texto, chunk_size=50, overlap=15)
        self.assertGreater(len(chunks), 1)
        palabras_c1 = chunks[0].split()[-15:]
        palabras_c2 = chunks[1].split()[:15]
        self.assertEqual(palabras_c1, palabras_c2)

    def test_construir_indice_genera_metadata(self):
        indice = construir_indice(DOCUMENTOS)
        self.assertTrue(len(indice) >= len(DOCUMENTOS))
        for chunk in indice:
            self.assertIn("sede", chunk)
            self.assertIn("tipo", chunk)
            self.assertIn("categoria", chunk)


class TestRetriever(unittest.TestCase):
    def setUp(self):
        self.indice = construir_indice(DOCUMENTOS)

    def test_buscar_encuentra_examen_sangre(self):
        resultados = buscar(self.indice, "examen de sangre ayuno")
        self.assertTrue(len(resultados) > 0)
        self.assertIn("sangre", resultados[0]["texto"].lower())

    def test_buscar_encuentra_horario_atencion(self):
        resultados = buscar(self.indice, "¿Cuál es el horario de atención?", sede_filtro="Providencia")
        self.assertTrue(len(resultados) > 0)
        self.assertTrue(any("horarios" in r["titulo"].lower() for r in resultados))

    def test_filtro_por_sede(self):
        resultados = buscar(
            self.indice, "examen de sangre", sede_filtro="Las Condes"
        )
        sedes = {r["sede"] for r in resultados}
        self.assertTrue(sedes.issubset({"Las Condes", "Todas", "Externa"}))

    def test_rerank_prioriza_interna(self):
        chunks = [
            {"tipo": "externa", "score": 0.9, "chunk_id": "a"},
            {"tipo": "interna", "score": 0.5, "chunk_id": "b"},
        ]
        resultado = re_rankear(chunks)
        self.assertEqual(resultado[0]["tipo"], "interna")


class TestTools(unittest.TestCase):
    def setUp(self):
        self.indice = construir_indice(DOCUMENTOS)
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_citas = os.path.join(self.tmp_dir, "citas_test.json")

    def test_herramienta_consulta_clinica(self):
        respuesta = consultar_informacion_clinica(self.indice, "ayuno examen sangre", sede="Providencia")
        self.assertIn("Fuente:", respuesta)

    def test_herramienta_agendamiento_modificacion_y_anulacion(self):
        # Crear cita
        cita = agendar_o_modificar_cita(
            paciente="Paciente Prueba",
            especialidad="Cardiologia",
            fecha_hora="2026-11-10 15:30",
            sede="Las Condes",
            accion="crear",
            ruta_archivo_citas=self.tmp_citas
        )
        self.assertIn("id_cita", cita)
        self.assertEqual(cita["estado"], "Confirmada")

        # Modificar cita
        cita_mod = agendar_o_modificar_cita(
            paciente="Paciente Prueba",
            especialidad="Cardiologia",
            fecha_hora="2026-11-12 16:00",
            sede="Las Condes",
            accion="modificar",
            id_cita=cita["id_cita"],
            ruta_archivo_citas=self.tmp_citas
        )
        self.assertEqual(cita_mod["estado"], "Modificada")
        self.assertEqual(cita_mod["fecha_hora"], "2026-11-12 16:00")

        # Anular cita
        cita_anulada = agendar_o_modificar_cita(
            paciente="Paciente Prueba",
            especialidad="",
            fecha_hora="",
            accion="anular",
            id_cita=cita["id_cita"],
            ruta_archivo_citas=self.tmp_citas
        )
        self.assertEqual(cita_anulada["estado"], "Anulada")

    def test_herramienta_manejo_error_no_encontrada(self):
        resultado = agendar_o_modificar_cita(
            paciente="Desconocido",
            especialidad="",
            fecha_hora="",
            accion="anular",
            id_cita="NO-EXISTE",
            ruta_archivo_citas=self.tmp_citas
        )
        self.assertIn("error", resultado)

    def test_generar_comprobante_en_directorio_temporal(self):
        datos = {
            "id_cita": "TEST-01",
            "paciente": "Test",
            "especialidad": "General",
            "fecha_hora": "2026-11-01 10:00",
            "sede": "Providencia",
            "estado": "Confirmada"
        }
        ruta_archivo = generar_comprobante_cita(datos, directorio_salida=self.tmp_dir)
        self.assertTrue(os.path.exists(ruta_archivo))


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_memoria = os.path.join(self.tmp_dir, "memoria_test.json")

    def test_memoria_corto_plazo(self):
        memoria = SistemaMemoriaClinica(limite_giros=2)
        memoria.registrar_mensaje("Paciente", "Hola")
        memoria.registrar_mensaje("Agente", "En que puedo ayudarte")
        historial = memoria.corto_plazo.obtener_historial()
        self.assertEqual(len(historial), 2)

    def test_memoria_largo_plazo_persistencia_json(self):
        memoria_lp = MemoriaLargoPlazo(ruta_archivo=self.tmp_memoria)
        memoria_lp.guardar_antecedente("Juan", "alergia", "penicilina")
        self.assertTrue(os.path.exists(self.tmp_memoria))

        memoria_recargada = MemoriaLargoPlazo(ruta_archivo=self.tmp_memoria)
        antecedentes = memoria_recargada.buscar_antecedentes("Juan", "alergia")
        self.assertEqual(len(antecedentes), 1)
        self.assertEqual(antecedentes[0]["valor"], "penicilina")


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.indice = construir_indice(DOCUMENTOS)
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_citas = os.path.join(self.tmp_dir, "citas_agent_test.json")
        self.tmp_memoria = os.path.join(self.tmp_dir, "memoria_agent_test.json")
        self.memoria = SistemaMemoriaClinica(ruta_largo_plazo=self.tmp_memoria)
        self.agente = AgenteClinicaVitalis(indice=self.indice, memoria=self.memoria)

    def test_detecta_urgencia_compleja_y_respiracion(self):
        self.assertTrue(detectar_urgencia("dolor muy fuerte en el pecho y me cuesta respirar"))
        self.assertTrue(detectar_urgencia("siento que me cuesta respirar"))
        self.assertTrue(detectar_urgencia("tengo dolor agudo e intenso en el pecho"))
        self.assertFalse(detectar_urgencia("me golpee levemente el pecho sin dolor"))
        self.assertFalse(detectar_urgencia("necesito saber sobre mi examen"))

    def test_extraer_datos_cita_manana_con_y_sin_enie(self):
        d1 = extraer_datos_cita("cita de dermatologia para manana en providencia")
        self.assertEqual(d1["fecha_hora"], "manana")
        d2 = extraer_datos_cita("cita de cardiologia para mañana en las condes")
        self.assertEqual(d2["fecha_hora"], "mañana")

    def test_ruta_a_urgencia_prioritaria(self):
        resultado = self.agente.ejecutar_flujo("ayuda tengo dolor intenso en el pecho")
        self.assertEqual(resultado["intencion"], "RUTA_A_URGENCIA")
        self.assertTrue(resultado["escalado"])
        self.assertIn("EMERGENCIA", resultado["respuesta"])

    def test_urgencia_en_medio_de_conversacion(self):
        self.agente.ejecutar_flujo("hola buenas tardes")
        resultado = self.agente.ejecutar_flujo("siento que no puedo respirar y dolor de pecho")
        self.assertEqual(resultado["intencion"], "RUTA_A_URGENCIA")
        self.assertTrue(resultado["escalado"])

    def test_ruta_b_pregunta_si_faltan_datos(self):
        resultado = self.agente.ejecutar_flujo("quiero agendar una cita")
        self.assertEqual(resultado["intencion"], "RUTA_B_RESERVA")
        self.assertIn("SolicitudDatosFaltantes", resultado["herramientas_usadas"])
        self.assertIn("especialidad", resultado["respuesta"].lower())

    def test_memoria_corto_plazo_completa_datos_en_siguiente_turno(self):
        # Turno 1: Paciente solo dice que quiere cita -> Agente pregunta
        r1 = self.agente.ejecutar_flujo("necesito agendar una cita")
        self.assertIn("SolicitudDatosFaltantes", r1["herramientas_usadas"])

        # Turno 2: Paciente responde solo con los datos faltantes sin repetir 'cita'
        r2 = self.agente.ejecutar_flujo(
            "dermatologia para manana en providencia",
            paciente="Carlos Soto",
            ruta_archivo_citas=self.tmp_citas,
            directorio_reportes=self.tmp_dir
        )
        self.assertEqual(r2["intencion"], "RUTA_B_RESERVA")
        self.assertIn("AgendarOModificarCita", r2["herramientas_usadas"])
        self.assertIn("Cita confirmada", r2["respuesta"])

    def test_agente_manejo_error_cita_no_cae(self):
        resultado = self.agente.ejecutar_flujo(
            "anular cita",
            paciente="Inexistente",
            datos_adicionales={"accion": "anular", "id_cita": "ID-FALSO"},
            ruta_archivo_citas=self.tmp_citas
        )
        self.assertIn("No se pudo", resultado["respuesta"])
        self.assertFalse(resultado["escalado"])

    def test_antecedentes_usados_en_respuesta_posterior(self):
        self.agente.ejecutar_flujo(
            "agendar cita de oftalmologia para el lunes en las condes",
            paciente="Ana Lopez",
            ruta_archivo_citas=self.tmp_citas,
            directorio_reportes=self.tmp_dir
        )
        resultado = self.agente.ejecutar_flujo(
            "indicaciones fondo de ojo",
            paciente="Ana Lopez"
        )
        self.assertIn("antecedentes", resultado["respuesta"].lower())
        self.assertIn("oftalmologia", resultado["respuesta"].lower())

    def test_ruta_c_sin_informacion_deriva_a_humano(self):
        resultado = self.agente.ejecutar_flujo("informacion sobre neurocirugia cuantica")
        self.assertTrue(resultado["escalado"])
        self.assertIn("derivare", resultado["respuesta"].lower())

    def test_compatibilidad_procesar_consulta(self):
        resultado = procesar_consulta(self.indice, "ayuno para examen de sangre")
        self.assertFalse(resultado["escalado"])
        self.assertIn("Fuente:", resultado["respuesta"])


if __name__ == "__main__":
    unittest.main()
