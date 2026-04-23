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
    st.image("logo.png", width=180)
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

    # Generamos PDF
    exito_pdf, ruta_pdf = generar_balance_para(id_cuit, desde, hasta, cuit, empresa)
    
    # Generamos Excel
    exito_xls, contenido_xls = generar_excel_para(id_cuit, desde, hasta, cuit, empresa)

    if exito_pdf and exito_xls:
        st.success("Documentos generados correctamente ✅")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            with open(ruta_pdf, "rb") as f:
                st.download_button(
                    label="📥 Descargar PDF",
                    data=f,
                    file_name=os.path.basename(ruta_pdf),
                    mime="application/pdf",
                    use_container_width=True
                )
        
        with col_btn2:
            nombre_xls = os.path.basename(ruta_pdf).replace(".pdf", ".xlsx")
            st.download_button(
                label="Excel", # Botón de Excel
                data=contenido_xls,
                file_name=nombre_xls,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.error(f"Error al generar: {ruta_pdf if not exito_pdf else contenido_xls}")
   
