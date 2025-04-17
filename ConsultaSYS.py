import pandas as pd
import requests
from fpdf import FPDF
from collections import defaultdict
import streamlit as st
import tempfile
import os

# --- CONFIGURACIÓN ---

TOKEN_USUARIO = st.secrets["token_sos"]  # Reemplazá por tu token personal

# --- FUNCIONES AUXILIARES ---



def obtener_jwt_cliente(idcuit):
    url = f"https://api.sos-contador.com/api-comunidad/cuit/credentials/{idcuit}"
    headers = {"Authorization": f"Bearer {TOKEN_USUARIO}"}
    return requests.get(url, headers=headers).json().get("jwt")

def obtener_sumas_saldos(jwt, desde, hasta):
    url = f"https://api.sos-contador.com/api-comunidad/sumasysaldos/listado/?fechadesde={desde}&fechahasta={hasta}"
    headers = {"Authorization": f"Bearer {jwt}"}
    return requests.get(url, headers=headers).json().get("items", [])

def clasificar_rubro(codigo):
    if codigo.startswith("01.01"): return "Activo Corriente"
    if codigo.startswith("01.02"): return "Activo No Corriente"
    if codigo.startswith("02.01"): return "Pasivo Corriente"
    if codigo.startswith("02.02"): return "Pasivo No Corriente"
    if codigo.startswith("03."): return "Patrimonio Neto"
    if codigo.startswith("04.01"): return "Ingresos"
    if codigo.startswith("04.02"): return "Gastos"
    return "Otros"

def mapear_presentacion(codigo):
    orden = {
        "01.01.01": "01.01.01 CAJA Y BANCOS",
        "01.01.02": "01.01.02 CRÉDITOS POR VENTAS",
        "01.01.03": "01.01.03 OTROS CRÉDITOS",
        "01.01.04": "01.01.04 BIENES DE CAMBIO",
        "01.02": "01.02 ACTIVO NO CORRIENTE",
        "02.01.02": "02.01.02 DEUDAS COMERCIALES",
        "02.01.03": "02.01.03 DEUDAS SOCIALES Y FISCALES",
        "02.01.04": "02.01.04 OTRAS DEUDAS",
        "02.02": "02.02 PASIVO NO CORRIENTE",
        "03.": "03.00 PATRIMONIO NETO",
        "04.01": "04.01 INGRESOS",
        "04.02": "04.02 GASTOS"
    }
    for pref, label in orden.items():
        if codigo.startswith(pref):
            return label
    return "Z_99_OTROS"

def generar_balance_para(id_cuit, desde, hasta,cuit_str,razon_social):
    try:
        jwt = obtener_jwt_cliente(int(id_cuit))
        datos = obtener_sumas_saldos(jwt, desde, hasta)
        df = pd.DataFrame(datos)
        

        df["montosaldo_fin"] = df["montosaldo_fin"].round(2)
        df = df[df["montosaldo_fin"] != 0]  # 👈 FILTRAR cuentas con saldo ≠ 0
        df["Rubro Balance"] = df["codigo"].apply(clasificar_rubro)
        df["Presentacion"] = df["codigo"].apply(mapear_presentacion)

        # --- ESTADO DE RESULTADOS ---
        eerr_df = df[df["Rubro Balance"].isin(["Ingresos", "Gastos"])]
        eerr_detalle = eerr_df[["Presentacion", "cuenta", "montosaldo_fin"]].sort_values(by="Presentacion")
        resultado = eerr_df.groupby("Rubro Balance")["montosaldo_fin"].sum()
        resultado_final = resultado.get("Ingresos", 0) + resultado.get("Gastos", 0)

        # --- BALANCE DE PRESENTACIÓN ---
        balance_df = df[df["Rubro Balance"].isin(["Activo Corriente", "Activo No Corriente", "Pasivo Corriente", "Pasivo No Corriente", "Patrimonio Neto"])]
        balance_agrupado = balance_df.groupby("Presentacion")["montosaldo_fin"].sum().reset_index()
        balance_agrupado.rename(columns={"montosaldo_fin": "Total ($)"}, inplace=True)
        balance_agrupado = balance_agrupado.sort_values(by="Presentacion")

        # Incluir resultado en PN
        idx_pn = balance_agrupado[balance_agrupado["Presentacion"] == "03.00 PATRIMONIO NETO"].index
        if not idx_pn.empty:
            balance_agrupado.loc[idx_pn[0], "Total ($)"] += round(resultado_final, 2)
        else:
            balance_agrupado.loc[len(balance_agrupado)] = ["03.00 PATRIMONIO NETO", round(resultado_final, 2)]

        # --- EXPORTACIÓN A EXCEL ---
        with pd.ExcelWriter("balance_final_88350.xlsx", engine="xlsxwriter") as writer:
            balance_agrupado.to_excel(writer, sheet_name="Balance", index=False)
            eerr_detalle.to_excel(writer, sheet_name="Estado Resultados", index=False)

        # --- ESTRUCTURA PARA PDF (Rubro > Subrubro > Cuenta) ---
        df_rubros = df[df["Rubro Balance"].isin(["Activo Corriente", "Activo No Corriente", "Pasivo Corriente", "Pasivo No Corriente", "Patrimonio Neto"])]
        estructura = defaultdict(lambda: defaultdict(list))
        for _, row in df_rubros.iterrows():
            estructura[row["Rubro Balance"]][row["Presentacion"]].append((row["cuenta"], row["montosaldo_fin"]))



        # Agrupar cuentas por bloque y subrubro para presentación en columnas
        estructura_horizontal = {}

        # Separar por grandes bloques
        bloques = {
            "ACTIVO": df[df["Rubro Balance"].isin(["Activo Corriente", "Activo No Corriente"])],
            "PASIVO": df[df["Rubro Balance"].isin(["Pasivo Corriente", "Pasivo No Corriente"])],
            "PATRIMONIO NETO": df[df["Rubro Balance"] == "Patrimonio Neto"],
            "RESULTADOS": df[df["Rubro Balance"].isin(["Ingresos", "Gastos"])]
        }

        # Armar la estructura: bloque → subrubro → [(cuenta, monto)]
        for bloque, df_bloque in bloques.items():
            subestructura = defaultdict(list)
            for _, row in df_bloque.iterrows():
                if row["montosaldo_fin"] != 0:
                    subestructura[row["Presentacion"]].append((row["cuenta"], row["montosaldo_fin"]))
            estructura_horizontal[bloque] = subestructura
        # --- PDF ---

        class PDFBalance(FPDF):
            def __init__(self, empresa, cuit, desde, hasta, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.empresa = empresa
                self.cuit = cuit
                self.desde = desde
                self.hasta = hasta

            def header(self):
                self.set_font("Arial", "B", 12)
                self.cell(0, 10, f"Balance General - Ejercicio {self.desde} al {self.hasta}", ln=True, align="C")
                self.set_font("Arial", "", 10)
                self.cell(0, 7, f"Empresa: {self.empresa} - CUIT: {self.cuit}", ln=True, align="C")
                self.ln(3)
                self.line(10, self.get_y(), 287, self.get_y())
                self.ln(4)

            def render_col(self, x, w, title, estructura):
                self.set_xy(x, 30)
                self.set_fill_color(235, 235, 235)
                self.set_font("Arial", "B", 11)
                self.cell(w, 8, title.upper(), ln=True, align="C", border=1, fill=True)

                for subrubro, cuentas in estructura.items():
                    total_subrubro = sum(s for _, s in cuentas)
                    if total_subrubro == 0:
                        continue

                    # Limpiar prefijo numérico
                    subrubro_clean = " ".join(subrubro.split(" ")[1:]) if " " in subrubro else subrubro

                    self.set_x(x)
                    self.set_fill_color(245, 245, 245)
                    self.set_font("Arial", "B", 9)
                    self.cell(w * 0.65, 6, subrubro_clean[:40], border="B", fill=True)
                    self.cell(w * 0.35, 6, f"${total_subrubro:,.2f}", border="B", ln=True, align="R", fill=True)

                    self.set_font("Arial", "", 8)
                    for cuenta, monto in cuentas:
                        if monto == 0:
                            continue

                        cuenta_texto = f"- {cuenta}"

                        # Truncar texto para que no se pase al lado del monto
                        max_chars = int((w * 1 - 5) // 2.0)  # estimación por fuente Arial 8
                        if len(cuenta_texto) > max_chars:
                            cuenta_texto = cuenta_texto[:max_chars - 3] + "..."

                        self.set_x(x + 2)
                        self.cell(w * 0.65 - 2, 5, cuenta_texto, border=0)
                        self.cell(w * 0.35, 5, f"${monto:,.2f}", border=0, ln=True, align="R")


                    self.ln(1)

        # Crear PDF
        
        pdf = PDFBalance(
            empresa=razon_social,
            cuit=cuit_str,
            desde=desde,
            hasta=hasta,
            orientation='L', unit='mm', format='A4'
        )     
        pdf.add_page()

        # Distribución uniforme: 4 columnas iguales (69.25 mm de ancho cada una)
        col_width = 69.25
        posiciones = [10, 10 + col_width, 10 + 2 * col_width, 10 + 3 * col_width]
        anchos = [col_width] * 4

        # Renderizar columnas
        for i, (nombre_bloque, contenido) in enumerate(estructura_horizontal.items()):
            pdf.render_col(posiciones[i], anchos[i], nombre_bloque, contenido)

        # Exportar
        # Sanitizar nombre de empresa para usar en el nombre del archivo
        nombre_limpio = razon_social.replace(" ", "_").replace(".", "").replace(",", "")
        nombre_archivo = f"Balance_{nombre_limpio}_{desde}_a_{hasta}.pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            pdf.output(tmpfile.name)
            ruta_pdf = tmpfile.name

        return True, ruta_pdf
    except Exception as e:
        return False, str(e)

