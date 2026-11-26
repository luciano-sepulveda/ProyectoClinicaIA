import json
import os

import pandas as pd
import streamlit as st

RUTA_LOG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "data",
    "observabilidad",
    "ejecuciones.jsonl"
)

st.set_page_config(
    page_title="Observabilidad Clinica Vitalis",
    page_icon="",
    layout="wide"
)

st.title("Dashboard de Observabilidad - Clinica Vitalis")
st.caption("Monitoreo de precision operacional, latencia, consistencia, errores y recursos del agente.")

if not os.path.exists(RUTA_LOG):
    st.warning("Todavia no existen registros. Ejecuta primero: python evaluar_observabilidad.py")
    st.stop()

registros = []
with open(RUTA_LOG, "r", encoding="utf-8") as archivo:
    for linea in archivo:
        try:
            registros.append(json.loads(linea))
        except json.JSONDecodeError:
            continue

if not registros:
    st.warning("El archivo de observabilidad esta vacio.")
    st.stop()

df = pd.DataFrame(registros)
evaluaciones = df[df["tipo"] == "evaluacion"].copy() if "tipo" in df else pd.DataFrame()
ejecuciones = df[df["tipo"] == "ejecucion"].copy() if "tipo" in df else pd.DataFrame()
consistencia = df[df["tipo"] == "resumen_consistencia"].copy() if "tipo" in df else pd.DataFrame()

if evaluaciones.empty:
    st.warning("No hay evaluaciones. Ejecuta python evaluar_observabilidad.py.")
    st.stop()

evaluaciones["correcto"] = evaluaciones["correcto"].astype(bool)
precision = evaluaciones["correcto"].mean() * 100
latencia_media = evaluaciones["latencia_ms"].mean()
latencia_maxima = evaluaciones["latencia_ms"].max()

if not ejecuciones.empty:
    errores = (ejecuciones["estado"] == "error").sum()
    tasa_errores = errores / len(ejecuciones) * 100
    memoria_media = ejecuciones.get("memoria_pico_mb", pd.Series(dtype=float)).mean()
else:
    errores = 0
    tasa_errores = 0
    memoria_media = 0

consistente = bool(consistencia.iloc[-1]["consistente"]) if not consistencia.empty else None

cpu_media = ejecuciones.get("cpu_ms", pd.Series(dtype=float)).mean() if not ejecuciones.empty else 0
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Precision operacional", f"{precision:.1f}%")
c2.metric("Latencia media", f"{latencia_media:.2f} ms")
c3.metric("Latencia maxima", f"{latencia_maxima:.2f} ms")
c4.metric("Tasa de errores", f"{tasa_errores:.1f}%", f"{errores} errores")
c5.metric("Memoria Python pico media", f"{memoria_media:.2f} MB")
c6.metric("CPU media", f"{cpu_media:.2f} ms")

st.subheader("Resultados por escenario")
vista = evaluaciones[["escenario", "intencion_esperada", "intencion_obtenida", "correcto", "latencia_ms", "escalado"]]
st.dataframe(vista, use_container_width=True, hide_index=True)

col_izq, col_der = st.columns(2)
with col_izq:
    st.subheader("Latencia por escenario")
    st.bar_chart(evaluaciones.set_index("escenario")["latencia_ms"])
with col_der:
    st.subheader("Precision por escenario")
    grafico = evaluaciones[["escenario", "correcto"]].copy()
    grafico["resultado"] = grafico["correcto"].map({True: 100, False: 0})
    st.bar_chart(grafico.set_index("escenario")["resultado"])

st.subheader("Consistencia")
if consistente is None:
    st.info("No se ha ejecutado la prueba de consistencia.")
elif consistente:
    st.success("Las tres respuestas repetidas fueron identicas.")
else:
    st.error("Se detectaron diferencias entre las respuestas repetidas.")

st.subheader("Analisis de errores y trazabilidad")
if ejecuciones.empty:
    st.info("No hay ejecuciones instrumentadas.")
else:
    st.write(f"Ejecuciones registradas: {len(ejecuciones)}")
    st.write(f"Ejecuciones con error: {errores}")
    if errores:
        st.dataframe(
            ejecuciones[ejecuciones["estado"] == "error"],
            use_container_width=True,
            hide_index=True
        )
    st.write("Distribucion de rutas ejecutadas")
    rutas = ejecuciones[ejecuciones["estado"] == "correcto"]["ruta"].value_counts()
    if not rutas.empty:
        st.bar_chart(rutas)

st.caption("Los registros no almacenan el texto de las consultas ni nombres de pacientes. La precisión corresponde a escenarios controlados con respuestas esperadas.")
