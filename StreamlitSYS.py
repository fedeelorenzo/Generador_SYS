import streamlit as st
from ConsultaSYS import generar_balance_para

st.set_page_config(page_title="Generador de Sumas y Saldos", layout="centered")

# --- Autenticación ---
st.session_state['auth'] = st.session_state.get('auth', False)
if not st.session_state['auth']:
    password = st.text_input("🔐 Ingresá tu token de acceso:", type="password")
    if password == st.secrets["clave_acceso"]:
        st.session_state['auth'] = True
        st.experimental_rerun()
    else:
        st.stop()

# --- Clientes desde secrets ---
clientes = st.secrets["clientes"]
empresas = list(clientes.keys())

st.title("📊 Generador de Sumas y Saldos Online")

# --- Formulario ---
with st.form("form_balance"):
    empresa = st.selectbox("Seleccioná la Empresa", empresas)
    desde = st.date_input("Fecha Desde")
    hasta = st.date_input("Fecha Hasta")

    submitted = st.form_submit_button("Generar Sumas y Saldos")

    if submitted and empresa:
        cuit = clientes[empresa]["cuit"]
        id_cuit = clientes[empresa]["id"]

        exito, mensaje = generar_balance_para(id_cuit, str(desde), str(hasta), cuit, empresa)
        if exito:
            st.success(mensaje)
            archivo = f"Balance_{empresa.replace(' ', '_')}_CUIT_{cuit}_{desde}_a_{hasta}.pdf"
            with open(archivo, "rb") as f:
                st.download_button("📥 Descargar PDF", data=f, file_name=archivo)
        else:
            st.error(mensaje)
