import streamlit as st
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
import io
import os
import urllib.parse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials as UserCreds
import json
import datetime
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import tempfile


# Incluir CSS corporativo Tekpro
st.markdown('''
<style>
/* Tekpro corporate style for Streamlit */
body, .stApp {
    background-color: #e6f7f7 !important;
}
h1, .stApp h1, .stMarkdown h1 {
    font-family: 'Montserrat', 'Arial', sans-serif;
    color: #1db6b6;
    font-weight: 700;
    letter-spacing: 1px;
}
h2, h3, .stApp h2, .stApp h3 {
    font-family: 'Montserrat', 'Arial', sans-serif;
    color: #1db6b6;
    font-weight: 600;
}
.stForm, .stTextInput, .stSelectbox, .stTextArea, .stFileUploader, .stDateInput {
    background-color: #f7fafb !important;
    border-radius: 8px !important;
}
.stButton > button {
    background-color: #1db6b6;
    color: #fff;
    border-radius: 8px;
    font-family: 'Montserrat', 'Arial', sans-serif;
    font-weight: 600;
    border: none;
    padding: 0.5em 1.5em;
    transition: background 0.2s;
}
.stButton > button:hover {
    background-color: #0e7c7b;
    color: #fff;
}
.stAlert-success {
    background-color: #f7fafb;
    color: #1db6b6;
    border-left: 5px solid #1db6b6;
}
.stAlert-info {
    background-color: #f7fafb;
    color: #1db6b6;
    border-left: 5px solid #1db6b6;
}
.stFileUploader {
    border: 2px dashed #1db6b6 !important;
}
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
</style>
''', unsafe_allow_html=True)

# Configuración
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Cargar credenciales de Service Account
def get_service_account_creds():
    if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
        return Credentials.from_service_account_info(
            st.secrets.gcp_service_account, scopes=SCOPES
        )
    elif os.path.exists('secrets/credentials.json'):
        return Credentials.from_service_account_file(
            'secrets/credentials.json', scopes=SCOPES
        )
    else:
        st.error("No se encontraron credenciales de Service Account.")
        st.stop()

# Subir imagen a Drive y hacerla pública

# Subir imagen a Drive usando OAuth2 (usuario)
def authorize_drive_oauth():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    redirect_uri = "https://dispatchtekpro.streamlit.app/"
    st.info(f"[LOG] Usando redirect_uri: {redirect_uri}")
    flow = Flow.from_client_config(
        {"web": dict(st.secrets.oauth2)},
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    st.markdown(f"[Haz clic aquí para autorizar con Google Drive]({auth_url})")
    st.markdown("""
    <small>Después de autorizar, copia y pega aquí la URL completa a la que fuiste redirigido.<br>
    El sistema extraerá el código automáticamente.</small>
    """, unsafe_allow_html=True)
    url_input = st.text_input("Pega aquí la URL de redirección:", key="oauth_url_input")
    auth_code = ""
    if url_input:
        parsed = urllib.parse.urlparse(url_input)
        params = urllib.parse.parse_qs(parsed.query)
        auth_code = params.get("code", [""])[0]
        if auth_code:
            st.success("Código detectado automáticamente. Haz clic en 'Validar código' para continuar.")
        else:
            st.warning("No se encontró el parámetro 'code' en la URL. Verifica que pegaste la URL completa.")

    # Botón fuera de cualquier formulario
    validar = st.button("Validar código", key="validar_codigo_oauth")
    if validar:
        if auth_code:
            try:
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
                st.session_state['drive_oauth_token'] = creds.to_json()
                st.success("¡Autorización exitosa! Puedes continuar con el formulario.")
            except Exception as e:
                st.error(f"Error al intercambiar el código: {e}")
        else:
            st.warning("Debes pegar la URL de redirección que contiene el código.")
    st.stop()

def get_drive_service_oauth():
    
    creds = None
    if 'drive_oauth_token' in st.session_state:
        creds = UserCreds.from_authorized_user_info(json.loads(st.session_state['drive_oauth_token']))
    if creds:
        return build('drive', 'v3', credentials=creds)
    else:
        authorize_drive_oauth()

def upload_image_to_drive_oauth(file, filename, folder_id):
    drive_service = get_drive_service_oauth()
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(file, mimetype='image/jpeg')
    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    file_id = uploaded.get('id')
    # Hacer el archivo público
    drive_service.permissions().create(
        fileId=file_id,
        body={
            'type': 'anyone',
            'role': 'reader'
        }
    ).execute()
    public_url = f"https://drive.google.com/uc?id={file_id}"
    return public_url

# Escribir link en Google Sheets
def write_link_to_sheet(sheet_client, file_name, worksheet_name, row):
    sheet = sheet_client.open(file_name).worksheet(worksheet_name)
    sheet.append_row(row)

def store_files(files, state_key):
    if files is not None:
        st.session_state[state_key + "_files"] = files
    else:
        st.session_state[state_key + "_files"] = []

def to_url_list(state_key):
    return ", ".join(st.session_state.get(state_key + "_links", []))

def main():
    # --- AUTORIZACIÓN GOOGLE DRIVE OBLIGATORIA ---
    if 'drive_oauth_token' not in st.session_state:
        st.info("Para continuar, debes autorizar el acceso a Google Drive.")
        authorize_drive_oauth()
        st.stop()

    # Menú principal y selección de formulario
    col1, col2 = st.columns([4,1])
    with col1:
        st.markdown("""
        <h1 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 700; letter-spacing: 1px;'>DISPATCH TEKPRO</h1>
        <h2 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 600; font-size: 1.5em;'>Menú principal</h2>
        """, unsafe_allow_html=True)
    with col2:
        st.image("https://drive.google.com/thumbnail?id=19MGYsVVEtnwv8SpdnRw4TainlJBsQLSE", width=150)
    st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;'>", unsafe_allow_html=True)

    menu_opcion = st.radio(
        "¿Qué deseas diligenciar?",
        ["Acta de entrega", "Lista de empaque"],
        horizontal=True,
        key="menu_opcion_radio"
    )
    if menu_opcion == "Acta de entrega":
        st.markdown("<h1 style='color:#1db6b6;font-family:Montserrat,Arial,sans-serif;font-weight:700;'>ACTA DE ENTREGA TEKPRO</h1>", unsafe_allow_html=True)
        st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;'>", unsafe_allow_html=True)
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        file_name = "dispatch_tekpro"
        worksheet_name_base = "Acta de entrega"
        worksheet_name_diligenciadas = "Actas de entregas diligenciadas"
        # Leer OPs base desde la hoja plantilla
        try:
            sheet_base = sheet_client.open(file_name).worksheet(worksheet_name_base)
            all_rows_base = sheet_base.get_all_values()
            op_options = []
            if all_rows_base:
                headers_lower = [h.strip().lower() for h in all_rows_base[0]]
                op_idx = headers_lower.index("op") if "op" in headers_lower else None
                for r in all_rows_base[1:]:
                    if op_idx is not None and len(r) > op_idx and r[op_idx].strip():
                        op_options.append(r[op_idx].strip())
        except Exception:
            op_options = []
        # Leer todas las OPs ya guardadas en la hoja 'Actas de entregas diligenciadas'
        try:
            sheet_diligenciadas = sheet_client.open(file_name).worksheet(worksheet_name_diligenciadas)
            all_rows_diligenciadas = sheet_diligenciadas.get_all_values()
            ops_guardadas = set()
            if all_rows_diligenciadas:
                headers_lower = [h.strip().lower() for h in all_rows_diligenciadas[0]]
                op_idx = headers_lower.index("op") if "op" in headers_lower else None
                for r in all_rows_diligenciadas[1:]:
                    if op_idx is not None and len(r) > op_idx and r[op_idx].strip():
                        ops_guardadas.add(r[op_idx].strip())
        except Exception:
            ops_guardadas = set()
        # Filtrar solo las OPs que no han sido guardadas (ninguna ocurrencia si ya existe en la hoja)
        op_options_filtradas = [op for op in op_options if op not in ops_guardadas]
        op_options_filtradas = list(dict.fromkeys(op_options_filtradas))
        op_selected = st.selectbox("Orden de compra (OP)", options=[" "] + op_options_filtradas, key="op_input_selectbox")
        # --- AUTOLLENADO DE DATOS GENERALES ---
        op_row = []
        headers_base = [h.strip().lower() for h in all_rows_base[0]] if all_rows_base else []
        if op_selected and op_selected.strip() != " ":
            op_idx = headers_base.index("op") if "op" in headers_base else None
            for r in all_rows_base[1:]:
                if op_idx is not None and len(r) > op_idx and r[op_idx].strip() == op_selected.strip():
                    op_row = r
                    break
        # Definir get_base_val SIEMPRE antes de cualquier uso

        def get_base_val(col):
            col = col.strip().lower()
            if not headers_base or not op_row:
                return ""
            idx = headers_base.index(col) if col in headers_base else None
            return op_row[idx] if idx is not None and idx < len(op_row) else ""

        # --- SECCIÓN 1: DATOS GENERALES ---
        st.markdown("<h2>Datos generales</h2>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            op = st.text_input("Orden de compra (OP)", value=op_selected if op_selected else "", key="op_input")
        with col2:
            fecha_default = get_base_val("fecha dili") if get_base_val("fecha dili") else datetime.date.today().strftime("%Y-%m-%d")
            try:
                fecha_val = datetime.datetime.strptime(fecha_default, "%Y-%m-%d").date()
            except:
                fecha_val = datetime.date.today()
            fecha = st.date_input("Fecha", value=fecha_val, key="fecha_input")

        cliente = st.text_input("Cliente", value=get_base_val("cliente"), key="cliente_input")
        equipo = st.text_input("Equipo", value=get_base_val("equipo"), key="equipo_input")
        item = st.text_input("Item", value=get_base_val("item"), key="item_input")
        cantidad_default = get_base_val("cantidad")
        try:
            cantidad_val = int(cantidad_default) if cantidad_default else 1
        except:
            cantidad_val = 1
        cantidad = st.number_input("Cantidad", min_value=1, value=cantidad_val, step=1, key="cantidad_input")

        # --- SECCIÓN 2: LISTAS DE CHEQUEO ---
    st.markdown("<h2>Listas de chequeo</h2>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    mostrar_electromecanicos = col1.checkbox("Elementos electromecánicos", key="cb_electromecanicos")
    mostrar_accesorios = col2.checkbox("Accesorios", key="cb_accesorios")
    mostrar_mecanicos = col3.checkbox("Elementos mecánicos", key="cb_mecanicos")
    mostrar_electricos = col4.checkbox("Elementos eléctricos", key="cb_electricos")

    # Lista de chequeo general elementos electromecánicos
    if mostrar_electromecanicos:
        st.markdown("""
<h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general elementos electromecánicos</h3>
""", unsafe_allow_html=True)
        motor_checked = st.checkbox("¿Hay motores?", key="motor_check")
        reductor_checked = st.checkbox("¿Hay reductores?", key="reductor_check")
        bomba_checked = st.checkbox("¿Hay bombas?", key="bomba_check")
        turbina_checked = st.checkbox("¿Hay turbinas?", key="turbina_check")
        quemador_checked = st.checkbox("¿Hay quemadores?", key="quemador_check")
        bomba_vacio_checked = st.checkbox("¿Hay bombas de vacío?", key="bomba_vacio_check")
        compresor_checked = st.checkbox("¿Hay compresores?", key="compresor_check")
        st.markdown("<hr>", unsafe_allow_html=True)

    if mostrar_electromecanicos:
        if motor_checked:
            with st.expander("Motores", expanded=True):
                st.markdown("<b>Motores</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad motores", min_value=0, step=1, format="%d", key="cantidad_motores")
                col[0].text_input("Voltaje motores", key="voltaje_motores")
                fotos_motores = col[0].file_uploader("Foto motores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="fotos_motores")
                store_files(fotos_motores, "motores")
        if reductor_checked:
            with st.expander("Reductores", expanded=True):
                st.markdown("<b>Reductores</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad reductores", min_value=0, step=1, format="%d", key="cantidad_reductores")
                col[0].text_input("Voltaje reductores", key="voltaje_reductores")
                fotos_reductores = col[0].file_uploader("Foto reductores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="fotos_reductores")
                store_files(fotos_reductores, "reductores")
        if bomba_checked:
            with st.expander("Bombas", expanded=True):
                st.markdown("<b>Bombas</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad bombas", min_value=0, step=1, format="%d", key="cantidad_bombas")
                col[0].text_input("Voltaje bombas", key="voltaje_bombas")
                fotos_bombas = col[0].file_uploader("Foto bombas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="fotos_bombas")
                store_files(fotos_bombas, "bombas")
        if turbina_checked:
            with st.expander("Turbinas", expanded=True):
                st.markdown("<b>Turbinas</b>", unsafe_allow_html=True)
                st.text_input("Voltaje turbinas", key="voltaje_turbina")
                fotos_turbina = st.file_uploader("Foto turbinas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_turbina")
                store_files(fotos_turbina, "turbina")
        if quemador_checked:
            with st.expander("Quemadores", expanded=True):
                st.markdown("<b>Quemadores</b>", unsafe_allow_html=True)
                st.text_input("Voltaje quemadores", key="voltaje_quemador")
                st.selectbox("Tipo de combustible", ["", "Gas Natural", "GLP", "ACPM"], key="tipo_combustible_quemador")
                st.selectbox("Método de uso", ["", "Alto/Bajo", "On/Off"], key="metodo_uso_quemador")
                fotos_quemador = st.file_uploader("Foto quemadores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_quemador")
                store_files(fotos_quemador, "quemador")
        if bomba_vacio_checked:
            with st.expander("Bombas de vacío", expanded=True):
                st.markdown("<b>Bombas de vacío</b>", unsafe_allow_html=True)
                st.text_input("Voltaje bombas de vacío", key="voltaje_bomba_vacio")
                fotos_bomba_vacio = st.file_uploader("Foto bombas de vacío", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_bomba_vacio")
                store_files(fotos_bomba_vacio, "bomba_vacio")
        if compresor_checked:
            with st.expander("Compresores", expanded=True):
                st.markdown("<b>Compresores</b>", unsafe_allow_html=True)
                st.text_input("Voltaje compresores", key="voltaje_compresor")
                fotos_compresor = st.file_uploader("Foto compresores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_compresor")
                store_files(fotos_compresor, "compresor")

    # Aquí van los bloques únicos de cada lista de chequeo (ya presentes más abajo en el código)
    # ...existing code...


    # Otros elementos: checkbox, descripción y foto (al final de las listas de chequeo)
    mostrar_otros_elementos = st.checkbox("Otros elementos", key="cb_otros_elementos")
    if mostrar_otros_elementos:
        with st.expander("Otros elementos", expanded=True):
            otros_elementos = st.text_area("Descripción de otros elementos", key="otros_elementos")
            fotos_otros_elementos = st.file_uploader("Foto(s) de otros elementos", type=["jpg","jpeg","png"], accept_multiple_files=True, key="fotos_otros_elementos")
            store_files(fotos_otros_elementos, "otros_elementos")
    if mostrar_accesorios:
        st.markdown("""
<h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general accesorios</h3>
""", unsafe_allow_html=True)
        manometro_checked = st.checkbox("¿Hay manómetros?", key="manometro_check_accesorios2")
        vacuometro_checked = st.checkbox("¿Hay vacuómetros?", key="vacuometro_check_accesorios2")
        valvula_checked = st.checkbox("¿Hay válvulas?", key="valvula_check_accesorios2")
        manguera_checked = st.checkbox("¿Hay mangueras?", key="manguera_check_accesorios2")
        boquilla_checked = st.checkbox("¿Hay boquillas?", key="boquilla_check_accesorios2")
        regulador_checked = st.checkbox("¿Hay reguladores aire/gas?", key="regulador_check_accesorios2")
        tornillos_checked = st.checkbox("¿Hay tornillos?", key="tornillos_check_accesorios2")
        curvas_checked = st.checkbox("¿Hay curvas de ascenso o descenso?", key="curvas_check_accesorios2")
        cables_checked = st.checkbox("¿Hay cables?", key="cables_check_accesorios2")
        tuberias_checked = st.checkbox("¿Hay tuberías?", key="tuberias_check_accesorios2")
        st.markdown("<hr>", unsafe_allow_html=True)

    if mostrar_accesorios:
        if manometro_checked:
            with st.expander("Manómetros", expanded=True):
                st.markdown("<b>Manómetros</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad manómetros", min_value=0, step=1, format="%d", key="cantidad_manometros")
                fotos_manometros = col[0].file_uploader("Foto manómetros", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_manometros")
                if fotos_manometros:
                    urls = []
                    for idx, file in enumerate(fotos_manometros):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"manometros_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_manometros"] = urls
        if vacuometro_checked:
            with st.expander("Vacuómetros", expanded=True):
                st.markdown("<b>Vacuómetros</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad vacuómetros", min_value=0, step=1, format="%d", key="cantidad_vacuometros")
                fotos_vacuometros = col[0].file_uploader("Foto vacuómetros", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_vacuometros")
                if fotos_vacuometros:
                    urls = []
                    for idx, file in enumerate(fotos_vacuometros):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"vacuometros_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_vacuometros"] = urls
        if valvula_checked:
            with st.expander("Válvulas", expanded=True):
                st.markdown("<b>Válvulas</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad válvulas", min_value=0, step=1, format="%d", key="cantidad_valvulas")
                fotos_valvulas = col[0].file_uploader("Foto válvulas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_valvulas")
                if fotos_valvulas:
                    urls = []
                    for idx, file in enumerate(fotos_valvulas):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"valvulas_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_valvulas"] = urls
        if manguera_checked:
            with st.expander("Mangueras", expanded=True):
                st.markdown("<b>Mangueras</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad mangueras", min_value=0, step=1, format="%d", key="cantidad_mangueras")
                fotos_mangueras = col[0].file_uploader("Foto mangueras", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_mangueras")
                if fotos_mangueras:
                    urls = []
                    for idx, file in enumerate(fotos_mangueras):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"mangueras_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_mangueras"] = urls
        if boquilla_checked:
            with st.expander("Boquillas", expanded=True):
                st.markdown("<b>Boquillas</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad boquillas", min_value=0, step=1, format="%d", key="cantidad_boquillas")
                fotos_boquillas = col[0].file_uploader("Foto boquillas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_boquillas")
                if fotos_boquillas:
                    urls = []
                    for idx, file in enumerate(fotos_boquillas):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"boquillas_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_boquillas"] = urls
        if regulador_checked:
            with st.expander("Reguladores aire/gas", expanded=True):
                st.markdown("<b>Reguladores aire/gas</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad reguladores aire/gas", min_value=0, step=1, format="%d", key="cantidad_reguladores")
                fotos_reguladores = col[0].file_uploader("Foto reguladores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_reguladores")
                if fotos_reguladores:
                    urls = []
                    for idx, file in enumerate(fotos_reguladores):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"reguladores_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_reguladores"] = urls
        if tornillos_checked:
            with st.expander("Tornillos", expanded=True):
                st.markdown("<b>Tornillos</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad tornillos", min_value=0, step=1, format="%d", key="cantidad_tornillos")
                fotos_tornillos = col[0].file_uploader("Foto tornillos", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_tornillos")
                if fotos_tornillos:
                    urls = []
                    for idx, file in enumerate(fotos_tornillos):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"tornillos_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_tornilleria"] = urls
        if curvas_checked:
            with st.expander("Curvas", expanded=True):
                st.markdown("<b>Curvas</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad curvas", min_value=0, step=1, format="%d", key="cantidad_curvas")
                fotos_curvas = col[0].file_uploader("Foto curvas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_curvas")
                if fotos_curvas:
                    urls = []
                    for idx, file in enumerate(fotos_curvas):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"curvas_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_curvas"] = urls
        if cables_checked:
            with st.expander("Cables", expanded=True):
                st.markdown("<b>Cables</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad cables", min_value=0, step=1, format="%d", key="cantidad_cables")
                fotos_cables = col[0].file_uploader("Foto cables", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_cables")
                if fotos_cables:
                    urls = []
                    for idx, file in enumerate(fotos_cables):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"cables_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_cables"] = urls
        if tuberias_checked:
            with st.expander("Tuberías", expanded=True):
                st.markdown("<b>Tuberías</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad tuberías", min_value=0, step=1, format="%d", key="cantidad_tuberias")
                fotos_tuberias = col[0].file_uploader("Foto tuberías", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_tuberias")
                if fotos_tuberias:
                    urls = []
                    for idx, file in enumerate(fotos_tuberias):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"tuberias_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_tuberias"] = urls
    if mostrar_mecanicos:
        st.markdown("""
<h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general elementos mecánicos</h3>
""", unsafe_allow_html=True)
        pinon1_checked = st.checkbox("¿Hay piñón 1?", key="pinon1_check_mecanicos_accesorios")
        pinon2_checked = st.checkbox("¿Hay piñón 2?", key="pinon2_check_mecanicos2")
        polea1_checked = st.checkbox("¿Hay polea 1?", key="polea1_check_mecanicos2")
        polea2_checked = st.checkbox("¿Hay polea 2?", key="polea2_check_mecanicos2")
        st.markdown("<hr>", unsafe_allow_html=True)

    if mostrar_mecanicos:
        if pinon1_checked:
            with st.expander("Piñón 1", expanded=True):
                st.markdown("<b>Piñón 1</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].text_input("Tensión piñón 1", key="tension_pinon1")
                fotos_pinon1 = col[0].file_uploader("Foto piñón 1", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_pinon1")
                if fotos_pinon1:
                    urls = []
                    for idx, file in enumerate(fotos_pinon1):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"pinon1_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_pinon1"] = urls
        if pinon2_checked:
            with st.expander("Piñón 2", expanded=True):
                st.markdown("<b>Piñón 2</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].text_input("Tensión piñón 2", key="tension_pinon2")
                fotos_pinon2 = col[0].file_uploader("Foto piñón 2", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_pinon2")
                if fotos_pinon2:
                    urls = []
                    for idx, file in enumerate(fotos_pinon2):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"pinon2_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_pinon2"] = urls
        if polea1_checked:
            with st.expander("Polea 1", expanded=True):
                st.markdown("<b>Polea 1</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].text_input("Tensión polea 1", key="tension_polea1")
                fotos_polea1 = col[0].file_uploader("Foto polea 1", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_polea1")
                if fotos_polea1:
                    urls = []
                    for idx, file in enumerate(fotos_polea1):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"polea1_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_polea1"] = urls
        if polea2_checked:
            with st.expander("Polea 2", expanded=True):
                st.markdown("<b>Polea 2</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].text_input("Tensión polea 2", key="tension_polea2")
                fotos_polea2 = col[0].file_uploader("Foto polea 2", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_polea2")
                if fotos_polea2:
                    urls = []
                    for idx, file in enumerate(fotos_polea2):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"polea2_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_polea2"] = urls
    if mostrar_electricos:
        st.markdown("""
<h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general elementos eléctricos</h3>
""", unsafe_allow_html=True)
        gabinete_checked = st.checkbox("¿Hay gabinete eléctrico?", key="gabinete_check")
        arrancador_checked = st.checkbox("¿Hay arrancador?", key="arrancador_check")
        control_nivel_checked = st.checkbox("¿Hay control de nivel?", key="control_nivel_check")
        variador_checked = st.checkbox("¿Hay variador de velocidad?", key="variador_check")
        sensor_temp_checked = st.checkbox("¿Hay sensor de temperatura?", key="sensor_temp_check")
        toma_corriente_checked = st.checkbox("¿Hay toma corriente?", key="toma_corriente_check")
        st.markdown("<hr>", unsafe_allow_html=True)

    if mostrar_electricos:
        if gabinete_checked:
            with st.expander("Gabinete eléctrico", expanded=True):
                st.markdown("<b>Gabinete eléctrico</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad gabinete eléctrico", min_value=0, step=1, format="%d", key="cantidad_gabinete")
                descripcion_gabinete = col[0].text_area("Descripción gabinete eléctrico", key="descripcion_gabinete")
                fotos_gabinete = col[0].file_uploader("Foto gabinete", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_gabinete")
                if fotos_gabinete:
                    urls = []
                    for idx, file in enumerate(fotos_gabinete):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"gabinete_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_gabinete"] = urls
                st.session_state["descripcion_gabinete"] = descripcion_gabinete
        if arrancador_checked:
            with st.expander("Arrancador", expanded=True):
                st.markdown("<b>Arrancador</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad arrancadores", min_value=0, step=1, format="%d", key="cantidad_arrancadores")
                descripcion_arrancadores = col[0].text_area("Descripción arrancadores", key="descripcion_arrancadores")
                fotos_arrancadores = col[0].file_uploader("Foto arrancadores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_arrancadores")
                if fotos_arrancadores:
                    urls = []
                    for idx, file in enumerate(fotos_arrancadores):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"arrancadores_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_arrancadores"] = urls
                st.session_state["descripcion_arrancadores"] = descripcion_arrancadores
        if control_nivel_checked:
            with st.expander("Control de nivel", expanded=True):
                st.markdown("<b>Control de nivel</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad control de nivel", min_value=0, step=1, format="%d", key="cantidad_control_nivel")
                descripcion_control_nivel = col[0].text_area("Descripción control de nivel", key="descripcion_control_nivel")
                fotos_control_nivel = col[0].file_uploader("Foto control de nivel", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_control_nivel")
                if fotos_control_nivel:
                    urls = []
                    for idx, file in enumerate(fotos_control_nivel):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"control_nivel_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_control_nivel"] = urls
                st.session_state["descripcion_control_nivel"] = descripcion_control_nivel
        if variador_checked:
            with st.expander("Variador de velocidad", expanded=True):
                st.markdown("<b>Variador de velocidad</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad variadores de velocidad", min_value=0, step=1, format="%d", key="cantidad_variador")
                descripcion_variador = col[0].text_area("Descripción variador de velocidad", key="descripcion_variador")
                fotos_variador = col[0].file_uploader("Foto variador de velocidad", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_variador")
                if fotos_variador:
                    urls = []
                    for idx, file in enumerate(fotos_variador):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"variador_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_variador"] = urls
                st.session_state["descripcion_variador"] = descripcion_variador
        if sensor_temp_checked:
            with st.expander("Sensor de temperatura", expanded=True):
                st.markdown("<b>Sensor de temperatura</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad sensores de temperatura", min_value=0, step=1, format="%d", key="cantidad_sensor_temp")
                descripcion_sensor_temp = col[0].text_area("Descripción sensor de temperatura", key="descripcion_sensor_temp")
                fotos_sensor_temp = col[0].file_uploader("Foto sensor de temperatura", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_sensor_temp")
                if fotos_sensor_temp:
                    urls = []
                    for idx, file in enumerate(fotos_sensor_temp):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"sensor_temp_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_sensor_temp"] = urls
                st.session_state["descripcion_sensor_temp"] = descripcion_sensor_temp
        if toma_corriente_checked:
            with st.expander("Toma corriente", expanded=True):
                st.markdown("<b>Toma corriente</b>", unsafe_allow_html=True)
                col = st.columns(1)
                col[0].number_input("Cantidad tomas corriente", min_value=0, step=1, format="%d", key="cantidad_toma_corriente")
                descripcion_toma_corriente = col[0].text_area("Descripción toma corriente", key="descripcion_toma_corriente")
                fotos_toma_corriente = col[0].file_uploader("Foto toma corriente", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_toma_corriente")
                if fotos_toma_corriente:
                    urls = []
                    for idx, file in enumerate(fotos_toma_corriente):
                        if file is not None:
                            url = upload_image_to_drive_oauth(file, f"toma_corriente_{idx+1}.jpg", folder_id)
                            urls.append(url)
                    st.session_state["links_foto_toma_corriente"] = urls
                st.session_state["descripcion_toma_corriente"] = descripcion_toma_corriente

    # Selectboxes de revisión general (ahora debajo de las listas de chequeo)
    st.markdown("<h4>Revisión general</h4>", unsafe_allow_html=True)
    col_rev = st.columns(1)
    revision_visual = col_rev[0].selectbox("Revisión visual", ["Selecciona...", "Sí", "No"], key="revision_visual")
    revision_funcional = col_rev[0].selectbox("Revisión funcional", ["Selecciona...", "Sí", "No"], key="revision_funcional")
    revision_soldadura = col_rev[0].selectbox("Revisión de soldadura", ["Selecciona...", "Sí", "No"], key="revision_soldadura")
    revision_sentidos = col_rev[0].selectbox("Revisión de sentidos de giro", ["Selecciona...", "Sí", "No"], key="revision_sentidos")
    manual_funcionamiento = col_rev[0].selectbox("Manual de funcionamiento", ["Selecciona...", "Sí", "No"], key="manual_funcionamiento")
    revision_filos = col_rev[0].selectbox("Revisión de filos y acabados", ["Selecciona...", "Sí", "No"], key="revision_filos")
    revision_tratamientos = col_rev[0].selectbox("Revisión de tratamientos", ["Selecciona...", "Sí", "No"], key="revision_tratamientos")
    revision_tornilleria = col_rev[0].selectbox("Revisión de tornillería", ["Selecciona...", "Sí", "No"], key="revision_tornilleria")
    revision_ruidos = col_rev[0].selectbox("Revisión de ruidos", ["Selecciona...", "Sí", "No"], key="revision_ruidos")
    ensayo_equipo = col_rev[0].selectbox("Ensayo equipo", ["Selecciona...", "Sí", "No"], key="ensayo_equipo")

    # Observaciones generales
    col_obs = st.columns(1)
    observaciones_generales = col_obs[0].text_area("Observaciones generales", key="observaciones_generales")

    # Líder de inspección
    col_lider = st.columns(1)
    lideres = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata","Juan David Martinez"]  # Puedes personalizar esta lista
    lider_inspeccion = col_lider[0].selectbox("Líder de inspección", lideres, key="lider_inspeccion")

    # Soldador
    col_soldador = st.columns(1)
    soldador = ["", "Jaime Ramos", "Jaime Rincon", "Gabriel","Lewis"]  # Puedes personalizar esta lista
    soldador = col_soldador[0].selectbox("Encargado Soldador", soldador, key="soldador")

    # Diseñador
    col_disenador = st.columns(1)
    disenadores = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata","Juan David Martinez"]  # Puedes personalizar esta lista
    disenador = col_disenador[0].selectbox("Diseñador", disenadores, key="disenador")

    # Fecha y hora de entrega
    col_fecha = st.columns(1)
    fecha_entrega = col_fecha[0].date_input("Fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta")
    hora_entrega = col_fecha[0].time_input("Hora de entrega", value=datetime.datetime.now().time(), key="hora_entrega_acta")

    # Mostrar fecha y hora en formato DD-MM-AA-HH:MM:SS
    dt_entrega = datetime.datetime.combine(fecha_entrega, hora_entrega)
    fecha_hora_formateada = dt_entrega.strftime("%d-%m-%y-%H:%M:%S")
    st.info(f"Fecha y hora de entrega: {fecha_hora_formateada}")

    # Botón para enviar el acta de entrega (al final del formulario)
    enviar_acta = st.button("Enviar Acta de Entrega", key="enviar_acta_entrega")
    # Guardar solo al presionar el botón
    if enviar_acta:
        # Subir imágenes a Drive aquí, solo una vez
        image_keys = [
            "motores", "reductores", "bombas", "turbina", "quemador", "bomba_vacio", "compresor",
            "manometros", "vacuometros", "valvulas", "mangueras", "boquillas", "reguladores",
            "pinon1", "pinon2", "polea1", "polea2", "gabinete", "arrancadores", "control_nivel",
            "variador", "sensor_temp", "toma_corriente", "otros_elementos", "tuberias", "cables",
            "curvas", "tornilleria"
        ]
        for key in image_keys:
            files = st.session_state.get(key + "_files", [])
            urls = []
            for idx, file in enumerate(files):
                if file is not None:
                    url = upload_image_to_drive_oauth(file, f"{key}_{idx+1}.jpg", folder_id)
                    urls.append(url)
        # Ahora construir la fila con los links ya subidos
        row = [
            str(cliente),
            str(op),
            str(item),
            str(equipo),
            str(cantidad),
            str(fecha),
            str(st.session_state.get("cantidad_motores", "")),
            str(st.session_state.get("voltaje_motores", "")),
            to_url_list("motores"),
            str(st.session_state.get("cantidad_reductores", "")),
            str(st.session_state.get("voltaje_reductores", "")),
            to_url_list("reductores"),
            str(st.session_state.get("cantidad_bombas", "")),
            str(st.session_state.get("voltaje_bombas", "")),
            to_url_list("bombas"),
            str(st.session_state.get("voltaje_turbina", "")),
            str(st.session_state.get("tipo_combustible_turbina", "")),
            str(st.session_state.get("metodo_uso_turbina", "")),
            to_url_list("turbina"),
            str(st.session_state.get("voltaje_quemador", "")),
            to_url_list("quemador"),
            str(st.session_state.get("voltaje_bomba_vacio", "")),
            to_url_list("bomba_vacio"),
            str(st.session_state.get("voltaje_compresor", "")),
            to_url_list("compresor"),
            str(st.session_state.get("cantidad_manometros", "")),
            to_url_list("manometros"),
            str(st.session_state.get("cantidad_vacuometros", "")),
            to_url_list("vacuometros"),
            str(st.session_state.get("cantidad_valvulas", "")),
            to_url_list("valvulas"),
            str(st.session_state.get("cantidad_mangueras", "")),
            to_url_list("mangueras"),
            str(st.session_state.get("cantidad_boquillas", "")),
            to_url_list("boquillas"),
            str(st.session_state.get("cantidad_reguladores", "")),
            to_url_list("reguladores"),
            str(st.session_state.get("tension_pinon1", "")),
            to_url_list("pinon1"),
            str(st.session_state.get("tension_pinon2", "")),
            to_url_list("pinon2"),
            str(st.session_state.get("tension_polea1", "")),
            to_url_list("polea1"),
            str(st.session_state.get("tension_polea2", "")),
            to_url_list("polea2"),
            str(st.session_state.get("cantidad_gabinete", "")),
            to_url_list("gabinete"),
            str(st.session_state.get("cantidad_arrancadores", "")),
            to_url_list("arrancadores"),
            str(st.session_state.get("cantidad_control_nivel", "")),
            to_url_list("control_nivel"),
            str(st.session_state.get("cantidad_variadores", "")),
            to_url_list("variador"),
            str(st.session_state.get("cantidad_sensores", "")),
            to_url_list("sensor_temp"),
            str(st.session_state.get("cantidad_toma_corriente", "")),
            to_url_list("toma_corriente"),
            str(st.session_state.get("otros_elementos", "")),
            to_url_list("otros_elementos"),
            str(st.session_state.get("descripcion_tuberias", "")),
            to_url_list("tuberias"),
            str(st.session_state.get("descripcion_cables", "")),
            to_url_list("cables"),
            str(st.session_state.get("descripcion_curvas", "")),
            to_url_list("curvas"),
            str(st.session_state.get("descripcion_tornilleria", "")),
            to_url_list("tornilleria"),
            str(st.session_state.get("revision_soldadura", "")),
            str(st.session_state.get("revision_sentidos", "")),
            str(st.session_state.get("manual_funcionamiento", "")),
            str(st.session_state.get("revision_filos", "")),
            str(st.session_state.get("revision_tratamientos", "")),
            str(st.session_state.get("revision_tornilleria", "")),
            str(st.session_state.get("revision_ruidos", "")),
            str(st.session_state.get("ensayo_equipo", "")),
            str(st.session_state.get("observaciones_generales", "")),
            str(st.session_state.get("lider_inspeccion", "")),
            str(st.session_state.get("soldador", "")),
            str(st.session_state.get("disenador", "")),
            str(st.session_state.get("fecha_entrega_acta", ""))
        ]
        # --- GUARDAR EN HOJA 'ACTAS DE ENTREGA DILIGENCIADAS' ---
        # Leer todas las OPs ya guardadas en la hoja 'Actas de entregas diligenciadas'
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        file_name = "dispatch_tekpro"
        worksheet_name_diligenciadas = "Actas de entregas diligenciadas"
        try:
            sheet_diligenciadas = sheet_client.open(file_name).worksheet(worksheet_name_diligenciadas)
            all_rows_diligenciadas = sheet_diligenciadas.get_all_values()
            ops_guardadas = set()
            if all_rows_diligenciadas:
                headers_lower = [h.strip().lower() for h in all_rows_diligenciadas[0]]
                op_idx = headers_lower.index("op") if "op" in headers_lower else None
                for r in all_rows_diligenciadas[1:]:
                    if op_idx is not None and len(r) > op_idx and r[op_idx].strip():
                        ops_guardadas.add(r[op_idx].strip())
        except Exception:
            ops_guardadas = set()
        # Suponiendo que op_options contiene todas las OPs posibles (de otra fuente o lista)
        # Filtrar solo las que no han sido guardadas
        op_options_filtradas = [op for op in op_options if op not in ops_guardadas]
        op_options_filtradas = list(dict.fromkeys(op_options_filtradas))
        op_selected = st.selectbox("Orden de compra (OP)", options=[" "] + op_options_filtradas, key="op_input_selectbox")
        # Encabezados según lo solicitado
        headers = [
            "cliente dili", "op dili", "item dili", "equipo dili", "cantidad dili", "fecha dili",
            "cantidad motores dili", "voltaje motores dili", "fotos motores dili",
            "cantidad reductores dili", "voltaje reductores dili", "fotos reductores dili",
            "cantidad bombas dili", "voltaje bombas dili", "fotos bombas dili",
            "voltaje turbina dili", "Tipo combustible turbina dili", "Metodo uso turbina dili", "foto turbina dili",
            "voltaje quemador dili", "foto quemador dili",
            "voltaje bomba de vacio dili", "foto bomba de vacio dili",
            "voltaje compresor dili", "foto compresor dili",
            "cantidad manometros dili", "foto manometros dili",
            "cantidad vacuometros dili", "foto vacuometros dili",
            "cantidad valvulas dili", "foto valvulas dili",
            "cantidad mangueras dili", "foto mangueras dili",
            "cantidad boquillas dili", "foto boquillas dili",
            "cantidad reguladores aire/gas dili", "foto reguladores dili",
            "tension piñon 1 dili", "foto piñon 1 dili",
            "tension piñon 2 dili", "foto piñon 2 dili",
            "tension polea 1 dili", "foto polea 1 dili",
            "tension polea 2 dili", "foto polea 2 dili",
            "cantidad gabinete electrico dili", "foto gabinete dili",
            "cantidad arrancadores dili", "foto arrancadores dili",
            "cantidad control de nivel dili", "foto control de nivel dili",
            "cantidad variadores de velociad dili", "foto variadores de velocidad dili",
            "cantidad sensores de temperatura dili", "foto sensores de temperatura dili",
            "cantidad toma corriente dili", "foto toma corrientes dili",
            "descripcion otros elementos dili", "fotos otros elementos dili",
            "descripcion tuberias dili", "foto tuberias dili",
            "descripcion cables dili", "foto cables dili",
            "descripcion curvas dili", "foto curvas dili",
            "descripcion tornilleria dili", "foto tornilleria dili",
            "revision de soldadura dili", "revision de sentidos de giro dili", "manual de funcionamiento dili",
            "revision de filos y acabados dili", "revision de tratamientos dili", "revision de tornilleria dili",
            "revision de ruidos dili", "ensayo equipo dili", "observciones generales dili",
            "lider de inspeccion dili", "Encargado soldador dili", "diseñador dili", "fecha de entrega dili"
        ]
        # Si la hoja no existe, crearla y poner encabezados
        try:
            sheet_diligenciadas = sheet_client.open(file_name).add_worksheet(title=worksheet_name_diligenciadas, rows=100, cols=len(headers))
            sheet_diligenciadas.append_row(headers)
        except Exception as e:
            st.error(f"Error al crear la hoja '{worksheet_name_diligenciadas}': {e}")
            st.stop()
        # Si la hoja está vacía, poner encabezados
        if not sheet_diligenciadas.get_all_values():
            sheet_diligenciadas.append_row(headers)
        sheet_diligenciadas.append_row(row)
        st.success("Acta de entrega guardada correctamente en 'Actas de entregas diligenciadas'.")

    #/////////////////////////////////////////////////////////////AQUI EMPIEZA CODIGO DE LISTA DE EMPAQUE////////////////////////
    elif menu_opcion == "Lista de empaque":
        folder_id = st.secrets.drive_config.FOLDER_ID
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        file_name = "dispatch_tekpro"
        worksheet_name = "Acta de entrega"
        st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales para empaque</b>", unsafe_allow_html=True)
        op_options_empaque = []
        op_to_row_empaque = {}
        all_rows = []
        try:
            sheet = sheet_client.open(file_name).worksheet(worksheet_name)
            all_rows = sheet.get_all_values()
            if all_rows:
                headers_lower = [h.strip().lower() for h in all_rows[0]]
                op_idx = headers_lower.index("op") if "op" in headers_lower else None
                for r in all_rows[1:]:
                    if op_idx is not None and len(r) > op_idx and r[op_idx].strip():
                        op_options_empaque.append(r[op_idx].strip())
                        op_to_row_empaque[r[op_idx].strip()] = r
        except Exception:
            st.warning("No se pudo leer la hoja de acta de entrega para obtener las OP disponibles.")
        op_selected_empaque = st.selectbox("Selecciona la OP a empacar", options=[" "] + op_options_empaque, key="op_selectbox_empaque_2")
        op = ""
        fecha = ""
        cliente = ""
        equipo = ""
        encargado_ingenieria = ""
        if op_selected_empaque and op_selected_empaque.strip() != "":
            row = op_to_row_empaque.get(op_selected_empaque, [])
            headers_lower = [h.strip().lower() for h in all_rows[0]] if all_rows else []
            def get_val(col):
                col = col.strip().lower()
                idx = headers_lower.index(col) if col in headers_lower else None
                return row[idx] if idx is not None and idx < len(row) else ""
            op = op_selected_empaque
            fecha = get_val("fecha dili")
            cliente = get_val("cliente dili")
            equipo = get_val("equipo dili")
            encargado_ingenieria = get_val("diseñador dili")
        encargados_almacen = ["", "Andrea Ochoa"]
        col_almacen = st.columns(1)
        encargado_almacen = col_almacen[0].selectbox("Encargado almacén", encargados_almacen, key="encargado_almacen_empaque")
        encargados_logistica = ["", "Angela Zapata", "Jhon Restrepo", "Juan Rendon"]
        col_logistica = st.columns(1)
        encargado_logistica = col_logistica[0].selectbox("Encargado logística", encargados_logistica, key="encargado_logistica_empaque")
        st.markdown(f"""
        <div style='background:#e6f7f7;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'>
        <b>OP:</b> {op}<br>
        <b>Fecha:</b> {fecha}<br>
        <b>Cliente:</b> {cliente}<br>
        <b>Equipo:</b> {equipo}<br>
        <b>Encargado almacén:</b> {encargado_almacen}<br>
        <b>Encargado ingeniería y diseño:</b> {encargado_ingenieria}<br>
        <b>Encargado logística:</b> {encargado_logistica}<br>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<b>Firma encargado logística:</b>", unsafe_allow_html=True)
        st.info("Por favor, firme en el recuadro de abajo:")
        canvas_result = st_canvas(
            fill_color="#00000000",  # Fondo transparente
            stroke_width=2,
            stroke_color="#1db6b6",
            background_color="#f7fafb",
            height=150,
            width=400,
            drawing_mode="freedraw",
            key="firma_logistica_canvas"
        )
        if canvas_result.image_data is not None:
            st.image(canvas_result.image_data, caption="Firma digital de logística", use_container_width=False)
        observaciones_adicionales = st.text_area("Observaciones adicionales", key="observaciones_adicionales")

        st.markdown("<h3>Guacales</h3>", unsafe_allow_html=True)
        if 'guacales' not in st.session_state:
            st.session_state['guacales'] = []

        def add_guacal():
            st.session_state['guacales'].append({'descripcion': '', 'fotos': []})

        st.button("Agregar guacal", on_click=add_guacal, key="btn_agregar_guacal")

        for idx, guacal in enumerate(st.session_state['guacales']):
            with st.expander(f"Guacal {idx+1}", expanded=True):
                descripcion = st.text_area(f"Descripción del guacal {idx+1}", value=guacal['descripcion'], key=f"descripcion_guacal_{idx+1}")
                fotos = st.file_uploader(f"Foto(s) del guacal {idx+1}", type=["jpg","jpeg","png"], accept_multiple_files=True, key=f"fotos_guacal_{idx+1}")
                guacal['descripcion'] = descripcion
                guacal['fotos'] = fotos if fotos else []

        enviar_empaque = st.button("Enviar Lista de Empaque", key="enviar_lista_empaque")
        if enviar_empaque:
            # Subir fotos de guacales a Drive y guardar enlaces
            guacales_data = []
            for idx, guacal in enumerate(st.session_state['guacales']):
                urls_fotos = []
                for j, file in enumerate(guacal['fotos']):
                    if file is not None:
                        url = upload_image_to_drive_oauth(file, f"guacal{idx+1}_{op}_{j+1}.jpg", folder_id)
                        urls_fotos.append(url)
                guacales_data.append({
                    'descripcion': guacal['descripcion'],
                    'fotos': urls_fotos
                })

            # Subir firma a Drive y guardar enlace
            firma_url = ""
            if 'firma_logistica_canvas' in st.session_state:
                canvas_result = st.session_state['firma_logistica_canvas']
                if hasattr(canvas_result, 'image_data') and canvas_result.image_data is not None:
                    img = Image.fromarray((canvas_result.image_data).astype(np.uint8))
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                        img.save(tmpfile.name)
                        tmpfile.seek(0)
                        with open(tmpfile.name, "rb") as f:
                            firma_url = upload_image_to_drive_oauth(f, f"firma_logistica_{op}.png", folder_id)

            # Encabezados base
            headers_empaque = [
                "Op", "Fecha", "Cliente", "Equipo", "Encargado almacén", "Encargado ingeniería y diseño", "Encargado logística", "Firma encargado logística", "Observaciones adicionales"
            ]
            row_empaque = [
                op,
                fecha,
                cliente,
                equipo,
                encargado_almacen,
                encargado_ingenieria,
                encargado_logistica,
                firma_url,
                observaciones_adicionales
            ]
            # Agregar columnas dinámicamente para cada guacal
            for idx, guacal in enumerate(guacales_data):
                headers_empaque.append(f"Descripción Guacal {idx+1}")
                headers_empaque.append(f"Fotos Guacal {idx+1}")
                row_empaque.append(guacal['descripcion'])
                row_empaque.append(", ".join(guacal['fotos']))
            # Guardar en sheet
            file_name_empaque = "dispatch_tekpro"
            worksheet_name_empaque = "Lista de empaque"
            try:
                sheet_empaque = sheet_client.open(file_name_empaque).worksheet(worksheet_name_empaque)
            except Exception:
                sheet_empaque = sheet_client.open(file_name_empaque).add_worksheet(title=worksheet_name_empaque, rows=100, cols=len(headers_empaque))
                sheet_empaque.append_row(headers_empaque)
            if not sheet_empaque.get_all_values():
                sheet_empaque.append_row(headers_empaque)
            sheet_empaque.append_row(row_empaque)
            st.success("Lista de empaque guardada correctamente en Google Sheets.")

if __name__ == "__main__":
    main()
