# Clínica Vitalis — Agente Autónomo con Herramientas y Memoria 

Clinica Vitalis


## 1. Decisiones de Diseño y Arquitectura

1. "Framework de Agentes (LangChain / LangGraph)"

   - Transforma el pipeline anterior en un agente con herramientas formales.

   - Enlace activo de variables de entorno mediante `LLM_PROVIDER` (Gemini u Ollama) y ejecucion autonoma con simulacion segura de LLM para pruebas sin conexion.
   - Conexion real con `SYSTEM_PROMPT` 

2. "Base Vectorial y Busqueda Semantica"

   - Base de conocimiento ampliada a 18 documentos clinicos internos y guias MINSAL.
   - Busqueda hibrida con normalizacion diacritica (tildes), sinoimos y lematizacion. Resuelve consultas como "¿Cual es el horario de atencion?".
   - Mantiene filtros estrictos por sede y categoria, priorizando fuentes internas sobre externas en el re-ranking.

3. "Arquitectura de Memoria Dual"

   - **Memoria de Corto Plazo** Retiene el hilo de la conversacion turno a turno. Si el agente pide datos faltantes, el paciente puede responder en el siguiente turno con los datos sin tener que repetir la palabra.
   - **Memoria de Largo Plazo** Guardada en archivo JSON ([`data/memoria_largo_plazo.json`](file:///c:/Users/Notebook/Downloads/ProyectoClinicaIA-main%20%281%29/ProyectoClinicaIA-main/data/memoria_largo_plazo.json)) para recordar antecedentes y citas entre sesiones.

4. "Planificacion y Decisiones Adaptativas"
   - **Prioridad Maxima de Urgencia:** Deteccion estricta antes de invocar al modelo mediante expresiones regulares (`\b`). Detecta "dolor muy fuerte en el pecho y me cuesta respirar" o "me cuesta respirar".

   - **Gestion de Citas Robusta:** Permite crear, modificar y anular citas. Si una cita no existe o hay error, responde cordial y ordenadamente sin excepciones (`KeyError`).


## 3. Diagrama de Flujo de Planificacion

```mermaid
flowchart TD
    Inicio([Consulta del Paciente]) --> Urgencia{"¿Presenta sintomas de urgencia o dolor de pecho?"}
    
    Urgencia -->|Si| RutaA[Ruta A: Protocolo de Emergencia<br/>Derivacion inmediata a Urgencias / 131]
    
    Urgencia -->|No| Clasificador{Clasificacion de Intencion}
    
    Clasificador -->|Reserva / Modificacion / Turno previo pendiente| ChequeoDatos{¿Datos completos?<br/>Especialidad, Fecha, Sede}
    ChequeoDatos -->|Faltan Datos| Preguntar[Agente solicita datos faltantes al paciente]
    ChequeoDatos -->|Completos| AccionCita[Ejecutar agendar_o_modificar_cita<br/>Persistir en data/citas.json]
    AccionCita --> Comprobante[Ejecutar generar_comprobante_cita<br/>Emitir archivo .txt en data/reportes/]
    Comprobante --> GuardarMemoria[Guardar antecedente en memoria de largo plazo]
    
    Clasificador -->|Dudas / Protocolos / Horarios| RAG[Ejecutar consultar_informacion_clinica<br/>Busqueda en Base Documental]
    RAG --> InfoSuficiente{¿Existe informacion oficial suficiente?}
    InfoSuficiente -->|Si| Responder[Generar respuesta citando fuente y sede]
    InfoSuficiente -->|No| Derivar[Derivar a ejecutivo humano por falta de informacion]
    
    RutaA --> Fin([Fin de interaccion])
    Preguntar --> Fin
    GuardarMemoria --> Fin
    Responder --> Fin
    Derivar --> Fin
```

---

4. "Estructura del Repositorio"

```
ProyectoClinicaIA/
├── main.py                     # Demostración de los 5 escenarios y modo interactivo
├── requirements.txt            # Dependencias del framework y utilidades
├── .env.example                # Plantilla de variables de entorno
├── .gitignore                  # Reglas de exclusión de entornos y archivos temporales
├── data/
│   ├── documentos.py           # 18 documentos clínicos (internos y guías MINSAL)
│   ├── citas.json              # Registro persistente de citas médicas
│   ├── memoria_largo_plazo.json# Persistencia de antecedentes de pacientes
│   └── reportes/               # Comprobantes generados en formato .txt
├── src/
│   ├── __init__.py
│   ├── agent.py                # Agente orquestador y planificador de rutas
│   ├── tools.py                # Herramientas consulta, agendamiento, comprobante
│   ├── memory.py               # Memoria de corto y largo plazo persistente
│   ├── ingest.py               # Preprocesamiento y chunking con overlap
│   ├── retriever.py            # Búsqueda semántica híbrida y re-ranking
│   └── prompts.py              # Definición de System Prompt y plantillas
├── tests/
│   └── test_pipeline.py        # 22 pruebas unitarias automatizadas las que son 100% aisladas
├── docs/
│   ├── arquitectura.png        # Infografía de arquitectura del agente
│   └── evidencia_pruebas.txt   # Salida real de las 22 pruebas ejecutadas
└── diagrams/
    └── arquitectura_clinica_vitalis.mermaid # Diagrama de arquitectura
```



## 5. Instalación y Ejecución del proyecto

```bash
# 1. Configurar variables de entorno
cp .env.example .env

# 2. Ejecutar la demostración de los 5 escenarios
python main.py

# 3. Ejecutar el modo interactivo por consola
python main.py --interactivo

# 4. Ejecutar las 22 pruebas unitarias automatizadas
python -m unittest discover -s tests -v
```

---

## 6. Ejemplos de Flujos Reales de Ejecución (`python main.py`)

### Escenario 1: Detección prioritaria de Urgencia (Ruta A)
- **Paciente (Raul Castro):** `"Tengo un dolor muy fuerte en el pecho y me cuesta respirar, ¿que puedo tomar?"`
- **Agente [Ruta A (Urgencia/Síntomas)]:**
  > `PROTOCOLO DE EMERGENCIA ACTIVADO: Tu consulta presenta señales de alerta médica. Por favor acude de inmediato al servicio de urgencias más cercano o comunícate al 131.`
- `[Herramientas: ['ProtocoloEmergencia'] | Escalado Humano: True]`

### Escenario 2: Reserva con datos faltantes (Ruta B - Adaptación y pregunta)
- **Paciente (Elena Morales):** `"Hola, necesito agendar una cita por favor."`
- **Agente [Ruta B (Reserva/Modificación)]:**
  > `Para coordinar su cita necesito que por favor me indique: la especialidad médica, la fecha y hora de preferencia, la sede (Providencia o Las Condes).`
- `[Herramientas: ['SolicitudDatosFaltantes'] | Escalado Humano: False]`

### Escenario 3: Reserva exitosa con emisión de comprobante (Ruta B)
- **Paciente (Elena Morales):** `"Deseo agendar cita de dermatologia para el viernes en providencia"`
- **Agente [Ruta B (Reserva/Modificación)]:**
  > `Cita confirmada con éxito. Código: CITA-0001 para Dermatologia el viernes en sede Providencia. Comprobante generado en: data/reportes/comprobante_CITA-0001.txt`
- `[Herramientas: ['AgendarOModificarCita', 'GenerarComprobanteCita'] | Escalado Humano: False]`

### Escenario 4: Consulta RAG oficial citando fuente (Ruta C)
- **Paciente (Marcos Vega):** `"¿Que ayuno requiero para el examen de sangre?"`
- **Agente [Ruta C (Dudas/Protocolos)]:**
  > `Para el examen de sangre general, el paciente debe asistir en ayuno estricto de 8 horas. Se recomienda no consumir alcohol 24 horas antes ni realizar ejercicio extenuante. El examen se realiza de lunes a viernes entre 08:00 y 11:00 hrs en el laboratorio de la sede Providencia. (Fuente: Protocolo de Preparación - Examen de Sangre (Sede Providencia), sede Providencia)`
- `[Herramientas: ['ConsultarInformacionClinica'] | Escalado Humano: False]`

### Escenario 5: Memoria a largo plazo reinyectada (Ruta C)
- **Paciente (Elena Morales):** `"¿Que cuidados debo tener despues de mi atencion?"`
- **Agente [Ruta C (Dudas/Protocolos)]:**
  > `[Nota de antecedentes del paciente: ultima cita: Dermatologia el viernes en sede Providencia] Tras una consulta dermatológica con procedimiento tópico o biopsia, evite exposición solar directa por 48 horas y no aplique cosméticos sobre la zona tratada durante 24 horas. (Fuente: Indicaciones Post-Consulta Dermatológica)`
- `[Herramientas: ['ConsultarInformacionClinica'] | Escalado Humano: False]`


## 7. Observabilidad - Evaluación Parcial N.º 3

El proyecto incorpora un módulo de observabilidad que registra automáticamente las ejecuciones del agente en `data/observabilidad/ejecuciones.jsonl`. Se almacenan la ruta ejecutada, estado, herramientas utilizadas, latencia, tiempo de CPU y memoria Python estimada. No se guarda el texto de las consultas ni el nombre de los pacientes.

### Ejecutar evaluación de métricas

```bash
python evaluar_observabilidad.py
```

El evaluador ejecuta siete escenarios controlados: urgencia, reserva incompleta, reserva completa, consulta RAG y consulta sin información. Compara la ruta y un fragmento esperado de la respuesta. También repite tres veces una consulta RAG para medir consistencia.

La precisión operacional se calcula como escenarios que cumplen la ruta y el contenido esperado dividido por el total de escenarios evaluados. Es una métrica de validación sobre este conjunto de pruebas, no una garantía de precisión clínica general.

### Iniciar dashboard

```bash
streamlit run dashboard.py
```

El dashboard presenta precisión operacional, latencia media y máxima, tasa de errores, memoria estimada, resultados por escenario, consistencia y distribución de rutas.

### Orden recomendado

```bash
pip install -r requirements.txt
python evaluar_observabilidad.py
streamlit run dashboard.py
```

Los registros se acumulan en el archivo JSONL. Para una nueva medición desde cero, elimina `data/observabilidad/ejecuciones.jsonl` antes de ejecutar el evaluador.
