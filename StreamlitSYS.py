import streamlit as st
from ConsultaSYS import generar_balance_para
import os
from PIL import Image



st.set_page_config(page_title="Generador de Sumas y Saldos", layout="centered")

# --- Autenticación ---
st.session_state['auth'] = st.session_state.get('auth', False)
if not st.session_state['auth']:
    password = st.text_input("🔐 Ingresá tu token de acceso:", type="password")
    if password == st.secrets["clave_acceso"]:
        st.session_state['auth'] = True
        st.rerun()
    else:
        st.stop()


col1, col2 = st.columns([1, 6])
with col1:
    st.image("logo.png", width=60)
with col2:
    st.markdown(
        "<h3 style='margin-top: 15px; font-weight: 600;'>📊 Generador de Sumas y Saldos</h3>",
        unsafe_allow_html=True
    )
st.markdown("<small style='color: gray;'>Versión Online - Lorenzo y Asociados</small>", unsafe_allow_html=True)
    


# --- Clientes desde secrets ---
clientes = st.secrets["clientes"]
empresas = list(clientes.keys())

# --- Formulario ---
with st.form("form_balance"):
    empresa = st.selectbox("Seleccioná la Empresa", empresas)
    desde = st.date_input("Fecha Desde")
    hasta = st.date_input("Fecha Hasta")
    submitted = st.form_submit_button("Generar Sumas y Saldos")

# --- Procesamiento fuera del form ---
if submitted and empresa:
    cuit = clientes[empresa]["cuit"]
    id_cuit = clientes[empresa]["id"]

    exito, ruta_pdf = generar_balance_para(id_cuit, str(desde), str(hasta), cuit, empresa)

    if exito and os.path.exists(ruta_pdf):
        st.success("Balance generado correctamente ✅")
        with open(ruta_pdf, "rb") as f:
            st.download_button(
                label="📥 Descargar PDF",
                data=f,
                file_name=os.path.basename(ruta_pdf),
                mime="application/pdf"
            )
    else:
        st.error("No se pudo generar o encontrar el archivo PDF.")
   
