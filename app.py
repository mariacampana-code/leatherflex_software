import os
import sys

# Agregar la carpeta actual al path de Python para evitar fallos de ruta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "leatherflex"))



"""Interfaz de Leather-Flex 3D.  Ejecutar:  streamlit run app.py"""
import os
import json
import tempfile
import shutil

import cv2
import numpy as np
import streamlit as st

from leatherflex import calibracion, pipeline, acomodo, simulador
from leatherflex.config import Config

st.set_page_config(page_title="Leather-Flex 3D", page_icon="🟫", layout="wide")
TMP = st.session_state.setdefault("tmp", tempfile.mkdtemp(prefix="leatherflex_"))


def guardar_subidos(archivos, carpeta):
    shutil.rmtree(carpeta, ignore_errors=True); os.makedirs(carpeta)
    for a in archivos:
        with open(os.path.join(carpeta, a.name), "wb") as f:
            f.write(a.getbuffer())
    return carpeta


def imagen(archivo):
    return cv2.imdecode(np.frombuffer(archivo.getbuffer(), np.uint8), cv2.IMREAD_COLOR)


st.title("Leather-Flex 3D")
st.caption("Del escaneo por fotos al mapa de la piel, sus defectos y el acomodo de moldes")

# ------------------------------------------------------------------ 1. calibracion
with st.sidebar:
    st.header("1 · Calibración")
    st.write("Una sola vez por escáner y celular. Imprime el tablero al 100 % y fotografíalo dentro del escáner; "
             "luego fotografía una hoja blanca mate.")
    ruta_tab = os.path.join(TMP, "tablero_para_imprimir.png")
    if not os.path.exists(ruta_tab):
        calibracion.tablero_para_imprimir(ruta_tab)
    st.download_button("Descargar tablero para imprimir", open(ruta_tab, "rb"), "tablero_calibracion.png", "image/png")
    f_tab = st.file_uploader("Foto del tablero", type=["jpg", "jpeg", "png"], key="tab")
    f_bla = st.file_uploader("Foto de la hoja blanca (opcional)", type=["jpg", "jpeg", "png"], key="bla")
    ruta_cal = os.path.join(TMP, "calib.json")
    if f_tab and st.button("Calibrar", use_container_width=True):
        try:
            cal = calibracion.calibrar_tablero(imagen(f_tab))
            gan = calibracion.campo_plano(imagen(f_bla)) if f_bla else None
            calibracion.guardar(cal, gan, ruta_cal)
            st.session_state["cal"] = cal
        except ValueError as e:
            st.error(str(e))
    if "cal" in st.session_state:
        c = st.session_state["cal"]
        st.success(f"Escala {c['mm_por_px_foto']:.4f} mm/px · giro {c['angulo_grados']:+.2f}°")

    st.header("Parámetros")
    cfg = Config()
    cfg.paso_x_mm = st.number_input("Paso entre columnas (mm)", 20.0, 300.0, cfg.paso_x_mm, 5.0)
    cfg.paso_y_mm = st.number_input("Paso entre filas (mm)", 20.0, 300.0, cfg.paso_y_mm, 5.0)
    cfg.filas = st.number_input("Fotos por columna", 1, 30, cfg.filas, 1,
                                help="Solo se usa si las fotos no se llaman como su posición (A1.jpg, B3.jpg...)")
    cfg.ruta = st.selectbox("Orden de las fotos sin nombre", ["columnas", "serpentina"],
                            help="columnas: A1, A2, A3, A4, B1...  ·  serpentina: A1..A4, B4..B1, C1...")
    cfg.umbral_sigma = st.slider("Sensibilidad a defectos (menor = detecta más)", 2.0, 5.0, cfg.umbral_sigma, 0.1)
    cfg.margen_defecto_mm = st.slider("Margen alrededor de cada defecto (mm)", 0.0, 20.0, cfg.margen_defecto_mm, 1.0)
    if st.checkbox("Respetar el hilo del cuero (solo giros de 0° y 180°)"):
        cfg.rotaciones = [0, 180]

# ------------------------------------------------------------------ 2. fotos y moldes
col1, col2 = st.columns(2)
with col1:
    st.subheader("2 · Fotos del escaneo")
    fotos = st.file_uploader("Fotos (JPG). Si se llaman A1.jpg, B2.jpg... se usa ese nombre como posición.",
                             type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="fotos")
    demo = st.button("Probar con un escaneo simulado", help="Genera fotos sintéticas con defectos conocidos")
with col2:
    st.subheader("3 · Moldes")
    dxfs = st.file_uploader("Moldes en DXF (milímetros, un molde por archivo). Sin archivos se usan los de ejemplo.",
                            type=["dxf"], accept_multiple_files=True, key="dxf")
    moldes = None
    if dxfs:
        moldes = []
        carp = guardar_subidos(dxfs, os.path.join(TMP, "moldes"))
        for a in dxfs:
            try:
                pol = acomodo.molde_desde_dxf(os.path.join(carp, a.name))
                cant = st.number_input(f"{a.name} · cantidad (0 = llenar la piel)", 0, 500, 0, key="c_" + a.name)
                moldes.append({"nombre": os.path.splitext(a.name)[0], "poligono": pol, "cantidad": cant or None})
                st.caption(f"{a.name}: {pol.bounds[2]:.0f} × {pol.bounds[3]:.0f} mm, {pol.area / 100:.0f} cm²")
            except Exception as e:
                st.error(f"{a.name}: {e}")
    else:
        st.info("Moldes de ejemplo: capellada, plantilla y billetera.")

procesar = st.button("Procesar piel", type="primary", disabled=not (fotos and os.path.exists(ruta_cal)) and not demo)

if demo:
    carpeta_demo = os.path.join(TMP, "demo")
    with st.spinner("Generando escaneo simulado..."):
        shutil.rmtree(carpeta_demo, ignore_errors=True)
        simulador.generar(carpeta_demo)
        cal = calibracion.calibrar_tablero(cv2.imread(os.path.join(carpeta_demo, "calibracion", "tablero.jpg")))
        calibracion.guardar(cal, calibracion.campo_plano(cv2.imread(os.path.join(carpeta_demo, "calibracion", "blanco.jpg"))),
                            os.path.join(carpeta_demo, "calib.json"))
    st.session_state["entrada"] = (os.path.join(carpeta_demo, "fotos"), os.path.join(carpeta_demo, "calib.json"))
    procesar = True
elif procesar:
    st.session_state["entrada"] = (guardar_subidos(fotos, os.path.join(TMP, "fotos")), ruta_cal)

# ------------------------------------------------------------------ 4. resultados
if procesar and "entrada" in st.session_state:
    carpeta_fotos, cal_json = st.session_state["entrada"]
    salida = os.path.join(TMP, "salida")
    estado = st.status("Procesando...", expanded=True)
    try:
        r = pipeline.procesar(carpeta_fotos, cal_json, salida, cfg, moldes, avisar=estado.write)
        estado.update(label="Listo", state="complete", expanded=False)
        st.session_state["resultado"] = (r["info"], salida)
    except Exception as e:
        estado.update(label="Error", state="error")
        st.error(f"No se pudo procesar: {e}")

if "resultado" in st.session_state:
    info, salida = st.session_state["resultado"]
    st.subheader("4 · Resultado")
    m = st.columns(5)
    m[0].metric("Piel", f"{info['piel_m2']} m²")
    m[1].metric("Defectos", info["defectos"])
    m[2].metric("Piezas", info["piezas"])
    m[3].metric("Aprovechamiento", f"{info['aprovechamiento_pct']} %")
    m[4].metric("Error de unión", f"{info['union']['error_medio_union_mm']} mm")
    t1, t2, t3 = st.tabs(["Defectos y piezas", "Mapa de la piel", "Lista de defectos"])
    t1.image(os.path.join(salida, "resultado.jpg"), use_container_width=True)
    t2.image(os.path.join(salida, "mapa.jpg"), use_container_width=True)
    t3.dataframe([{"#": i + 1, "tipo": d["tipo"], "área (mm²)": d["area_mm2"],
                   "x (mm)": d["caja_mm"][0], "y (mm)": d["caja_mm"][1],
                   "ancho (mm)": round(d["caja_mm"][2] - d["caja_mm"][0], 1), "alto (mm)": round(d["caja_mm"][3] - d["caja_mm"][1], 1)}
                  for i, d in enumerate(info["lista_defectos"])], use_container_width=True)
    d1, d2, d3 = st.columns(3)
    d1.download_button("Plantilla de corte (DXF)", open(os.path.join(salida, "plantilla_corte.dxf"), "rb"), "plantilla_corte.dxf")
    d2.download_button("Reporte (JSON)", open(os.path.join(salida, "reporte.json"), "rb"), "reporte.json")
    d3.download_button("Mapa (JPG)", open(os.path.join(salida, "mapa.jpg"), "rb"), "mapa.jpg")
