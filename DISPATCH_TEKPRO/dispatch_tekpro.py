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
def upload_image_to_drive_oauth(file, filename, folder_id):
    """
    Sube un archivo a Google Drive usando OAuth2 y devuelve el enlace público.
    file: archivo tipo file-like (por ejemplo, open(..., 'rb'))
    filename: nombre del archivo en Drive
    folder_id: ID de la carpeta de destino en Drive
    """
    # Obtener credenciales de usuario (de st.session_state)
    if 'drive_oauth_token' not in st.session_state:
        st.error("No hay token OAuth2 de Google Drive. Autoriza primero.")
        st.stop()
    creds = UserCreds.from_authorized_user_info(st.session_state['drive_oauth_token'])
    drive_service = build('drive', 'v3', credentials=creds)
    media = MediaIoBaseUpload(file, mimetype='image/png', resumable=True)
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
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

# Solo lógica y UI de lista de empaque
# Mostrar solo: datos generales, firma encargado logística, guacales, observaciones adicionales y guardar en Google Sheets
folder_id = st.secrets.drive_config.FOLDER_ID
creds = get_service_account_creds()
sheet_client = gspread.authorize(creds)
file_name = "dispatch_tekpro"
worksheet_name = "Actas de entregas diligenciadas"
st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales para empaque</b>", unsafe_allow_html=True)
# Leer OPs ya diligenciadas en actas de entregas diligenciadas
op_options_empaque = []
op_to_row_empaque = {}
op_selected_empaque = ""
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
    st.warning("No se pudo leer la hoja de actas de entregas diligenciadas para obtener las OP disponibles.")
op_selected_empaque = st.selectbox("Selecciona la OP a empacar", options=[" "] + op_options_empaque, key="op_selectbox_empaque_1")

# Definir variables en blanco por defecto
op = ""
fecha = ""
cliente = ""
equipo = ""
encargado_ingenieria = ""
# Selectbox para encargado almacén (ancho completo)
encargados_almacen = ["", "Andrea Ochoa"]
col_almacen = st.columns(1)
encargado_almacen = col_almacen[0].selectbox("Encargado almacén", encargados_almacen, key="encargado_almacen_empaque")
# Selectbox para encargado logística (ancho completo)
encargados_logistica = ["", "Angela Zapata", "Jhon Restrepo", "Juan Rendon"]
col_logistica = st.columns(1)
encargado_logistica = col_logistica[0].selectbox("Encargado logística", encargados_logistica, key="encargado_logistica_empaque")

if op_selected_empaque and op_selected_empaque.strip() != "":
    row = op_to_row_empaque.get(op_selected_empaque, [])
    headers_lower = [h.strip().lower() for h in all_rows[0]] if all_rows else []
    def get_val(col):
        col = col.strip().lower()
        idx = headers_lower.index(col) if col in headers_lower else None
        return row[idx] if idx is not None and idx < len(row) else ""
    # Solo los campos necesarios para empaque:
    op = op_selected_empaque
    fecha = get_val("fecha dili")
    cliente = get_val("cliente dili")
    equipo = get_val("equipo dili")
    encargado_ingenieria = get_val("diseñador dili")

# Mostrar los datos SIEMPRE, aunque estén en blanco
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

# Espacio para firma encargado logística
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

# --- SOLO mostrar la sección de lista de empaque ---
# (El resto del código de acta de entrega no se ejecuta)
# Observaciones adicionales
observaciones_adicionales = st.text_area("Observaciones adicionales", key="observaciones_adicionales")
# Guardar solo en variable local para el guardado
if st.button("Guardar Lista de Empaque", key="guardar_lista_empaque"):
    # Definir articulos_map localmente
    articulos_map = {
        "motores": ["motor_check", "Motores"],
        "reductores": ["reductor_check", "Reductores"],
        "bombas": ["bomba_check", "Bombas"],
        "turbina": ["turbina_check", "Turbina"],
        "quemador": ["quemador_check", "Quemador"],
        "bomba_vacio": ["bomba_vacio_check", "Bomba de vacío"],
        "compresor": ["compresor_check", "Compresor"],
        "manometros": ["manometro_check_accesorios2", "Manómetros"],
        "vacuometros": ["vacuometro_check_accesorios2", "Vacuómetros"],
        "valvulas": ["valvula_check_accesorios2", "Válvulas"],
        "mangueras": ["manguera_check_accesorios2", "Mangueras"],
        "boquillas": ["boquilla_check_accesorios2", "Boquillas"],
        "reguladores": ["regulador_check_accesorios2", "Reguladores aire/gas"],
        "tornillos": ["tornillos_check_accesorios2", "Tornillos"],
        "curvas": ["curvas_check_accesorios2", "Curvas"],
        "cables": ["cables_check_accesorios2", "Cables"],
        "tuberias": ["tuberias_check_accesorios2", "Tuberías"],
        "pinon1": ["pinon1_check_mecanicos_accesorios", "Piñón 1"],
        "pinon2": ["pinon2_check_mecanicos2", "Piñón 2"],
        "polea1": ["polea1_check_mecanicos2", "Polea 1"],
        "polea2": ["polea2_check_mecanicos2", "Polea 2"]
    }
    # Definir firma_url localmente
    firma_url = ""
    if 'firma_logistica_canvas' in st.session_state:
        canvas_result = st.session_state['firma_logistica_canvas']
        if hasattr(canvas_result, 'image_data') and canvas_result.image_data is not None:
            from PIL import Image
            import numpy as np
            import tempfile
            img = Image.fromarray((canvas_result.image_data).astype(np.uint8))
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                img.save(tmpfile.name)
                tmpfile.seek(0)
                with open(tmpfile.name, "rb") as f:
                    firma_url = upload_image_to_drive_oauth(f, f"firma_logistica_{op}.png", st.secrets.drive_config.FOLDER_ID)
    # Determinar artículos empacados y no empacados
    articulos_enviados = []
    articulos_no_enviados = []
    if op_selected_empaque and op_selected_empaque.strip() != "":
        for key, (check_col, nombre) in articulos_map.items():
            # Solo mostrar los que estaban presentes en el acta de entrega
            idx = headers_lower.index(check_col) if check_col in headers_lower else None
            if idx is not None and row[idx].strip().lower() in ["true", "1", "si", "yes", "x"]:
                if st.session_state.get(f"empacar_{key}_empaque", False):
                    articulos_enviados.append(nombre)
                else:
                    articulos_no_enviados.append(nombre)
    # Si no hay OP seleccionada, dejar listas vacías
    # Guardar datos en Google Sheets (hoja Lista de empaque)
    file_name_empaque = "dispatch_tekpro"
    worksheet_name_empaque = "Lista de empaque"
    # Subir fotos de todos los guacales a Drive y guardar enlaces
    guacales_data = []
    num_guacales = len(st.session_state['guacales']) if 'guacales' in st.session_state else 0
    for idx in range(num_guacales):
        guacal = st.session_state['guacales'][idx]
        urls_fotos = []
        for j, file in enumerate(guacal['fotos']):
            if file is not None:
                url = upload_image_to_drive_oauth(file, f"guacal{idx+1}_{op}_{j+1}.jpg", st.secrets.drive_config.FOLDER_ID)
                urls_fotos.append(url)
        guacales_data.append({
            'descripcion': guacal['descripcion'],
            'fotos': urls_fotos
        })
    # Encabezados base
    headers_empaque = [
        "Op", "Fecha", "Cliente", "Equipo", "Encargado almacén", "Encargado ingeniería y diseño", "Encargado logística", "Firma encargado logística", "Observaciones adicionales", "Artículos enviados", "Artículos no enviados"
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
        observaciones_adicionales,
        ", ".join(articulos_enviados),
        ", ".join(articulos_no_enviados)
    ]
    # Agregar columnas dinámicamente para cada guacal
    for idx, guacal in enumerate(guacales_data):
        headers_empaque.append(f"Descripción Guacal {idx+1}")
        headers_empaque.append(f"Fotos Guacal {idx+1}")
        row_empaque.append(guacal['descripcion'])
        row_empaque.append(", ".join(guacal['fotos']))
    # Guardar en sheet
    try:
        sheet_empaque = sheet_client.open(file_name_empaque).worksheet(worksheet_name_empaque)
    except Exception:
        # Si la hoja no existe, crearla y poner encabezados
        sheet_empaque = sheet_client.open(file_name_empaque).add_worksheet(title=worksheet_name_empaque, rows=100, cols=len(headers_empaque))
        sheet_empaque.append_row(headers_empaque)
    # Si la hoja está vacía, poner encabezados
    if not sheet_empaque.get_all_values():
        sheet_empaque.append_row(headers_empaque)
    sheet_empaque.append_row(row_empaque)
    st.success(f"Lista de empaque guardada en Google Sheets. Enlace de la firma: {firma_url if firma_url else 'No se capturó firma.'}")
creds = get_service_account_creds()
sheet_client = gspread.authorize(creds)
file_name = "dispatch_tekpro"
worksheet_name = "Acta de entrega"
st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales para empaque</b>", unsafe_allow_html=True)
# Leer OPs ya diligenciadas en acta de entrega
op_options_empaque = []
op_to_row_empaque = {}
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
if op_selected_empaque != "":
    row = op_to_row_empaque.get(op_selected_empaque, [])
    # Obtener headers
    headers_lower = [h.strip().lower() for h in all_rows[0]] if all_rows else []
    def get_val(col):
        col = col.strip().lower()
        idx = headers_lower.index(col) if col in headers_lower else None
        return row[idx] if idx is not None and idx < len(row) else ""

    # Campos arrastrados de acta de entrega
    op = op_selected_empaque
    fecha = get_val("fecha dili")
    cliente = get_val("cliente dili")
    equipo = get_val("equipo dili")
    encargado_ingenieria = get_val("diseñador dili")

    # Selectbox para encargado almacén
    encargados_almacen = ["", "Andrea Ochoa"]
    col_almacen = st.columns(1)
    encargado_almacen = col_almacen[0].selectbox("Encargado almacén", encargados_almacen, key="encargado_almacen_empaque")

    # Selectbox para encargado logística
    encargados_logistica = ["", "Angela Zapata", "Jhon Restrepo", "Juan Rendon"]
    col_logistica = st.columns(1)
    encargado_logistica = col_logistica[0].selectbox("Encargado logística", encargados_logistica, key="encargado_logistica_empaque")

    # Mostrar los datos
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

    # Espacio para firma encargado logística
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

def upload_image_to_drive_oauth(file, filename, folder_id):
    """
    Sube un archivo a Google Drive usando OAuth2 y devuelve el enlace público.
    file: archivo tipo file-like (por ejemplo, open(..., 'rb'))
    filename: nombre del archivo en Drive
    folder_id: ID de la carpeta de destino en Drive
    """
    # Obtener credenciales de usuario (de st.session_state)
    if 'drive_oauth_token' not in st.session_state:
        st.error("No hay token OAuth2 de Google Drive. Autoriza primero.")
        st.stop()
    creds = UserCreds.from_authorized_user_info(st.session_state['drive_oauth_token'])
    drive_service = build('drive', 'v3', credentials=creds)
    media = MediaIoBaseUpload(file, mimetype='image/png', resumable=True)
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
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

# Dummy para evitar error
def store_files(files, key):
    pass

def to_url_list(key):
    # Dummy para evitar error
    return ""

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
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        file_name = "dispatch_tekpro"
        worksheet_name_base = "Acta de entrega"
        worksheet_name_diligenciadas = "Actas de entregas diligenciadas"
        all_rows_base = []
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
        # Filtrar solo las OPs que no han sido guardadas
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
        # --- SECCIÓN 2: LISTAS DE CHEQUEO AGRUPADAS Y REVISIÓN GENERAL ---
        st.markdown("<h2>Listas de chequeo agrupadas</h2>", unsafe_allow_html=True)
        # Ejemplo de estructura de checklists agrupados
        checklists = {
            "Motores": ["Cantidad", "Descripción", "Fotos"],
            "Reductores": ["Cantidad", "Descripción", "Fotos"],
            "Bombas": ["Cantidad", "Descripción", "Fotos"],
            "Turbina": ["Cantidad", "Descripción", "Fotos"],
            "Quemador": ["Cantidad", "Descripción", "Fotos"],
            "Bomba de vacío": ["Cantidad", "Descripción", "Fotos"],
            "Compresor": ["Cantidad", "Descripción", "Fotos"],
        }
        checklist_data = {}
        for equipo, fields in checklists.items():
            with st.expander(f"{equipo}"):
                col = st.columns(1)[0]
                cantidad = col.number_input(f"Cantidad de {equipo}", min_value=0, value=0, key=f"cantidad_{equipo}")
                descripcion = col.text_input(f"Descripción de {equipo}", value="", key=f"descripcion_{equipo}")
                fotos = col.file_uploader(f"Fotos de {equipo}", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=f"fotos_{equipo}")
                fotos_urls = []
                if fotos:
                    for i, file in enumerate(fotos):
                        url = upload_image_to_drive_oauth(file, f"{equipo}_{op_selected}_{i+1}.jpg", st.secrets.drive_config.FOLDER_ID)
                        fotos_urls.append(url)
                checklist_data[equipo] = {
                    "cantidad": cantidad,
                    "descripcion": descripcion,
                    "fotos": fotos_urls
                }
        # --- SECCIÓN DE REVISIÓN GENERAL ---
        st.markdown("<h2>Revisión general</h2>", unsafe_allow_html=True)
        revision_items = [
            "¿Se entregó manual de operación?",
            "¿Se entregó manual de mantenimiento?",
            "¿Se entregó certificado de garantía?",
            "¿Se entregó plano de instalación?",
            "¿Se entregó lista de repuestos?"
        ]
        revision_general = {}
        for item in revision_items:
            col = st.columns(1)[0]
            revision_general[item] = col.selectbox(item, options=["No", "Sí"], key=f"revision_{item}")
        # --- SECCIÓN DE OTROS ELEMENTOS ---
        st.markdown("<h2>Otros elementos</h2>", unsafe_allow_html=True)
        otros_elementos = st.text_area("Otros elementos entregados (describa)", value="", key="otros_elementos")
        # --- SECCIÓN DE OBSERVACIONES ---
        observaciones = st.text_area("Observaciones", value=get_base_val("observaciones"), key="observaciones_input")
        # --- SECCIÓN DE FIRMA ---
        st.markdown("<h2>Firma</h2>", unsafe_allow_html=True)
        st.info("El encargado de logística debe firmar a continuación.")
        canvas_result = st_canvas(
            fill_color="#00000000",
            stroke_width=2,
            stroke_color="#1db6b6",
            background_color="#f7fafb",
            height=150,
            width=400,
            drawing_mode="freedraw",
            key="firma_logistica_canvas"
        )
        firma_url = ""
        if canvas_result.image_data is not None:
            from PIL import Image
            import numpy as np
            import tempfile
            img = Image.fromarray((canvas_result.image_data).astype(np.uint8))
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                img.save(tmpfile.name)
                tmpfile.seek(0)
                with open(tmpfile.name, "rb") as f:
                    firma_url = upload_image_to_drive_oauth(f, f"firma_logistica_{op_selected}.png", st.secrets.drive_config.FOLDER_ID)
            st.image(canvas_result.image_data, caption="Firma digital de logística", use_container_width=False)
        # --- BOTÓN GUARDAR ---
        if st.button("Guardar Acta de Entrega", key="guardar_acta_entrega"):
            # Construir fila para Google Sheets alineada a encabezados
            headers_entrega = [
                "OP", "Fecha", "Cliente", "Equipo", "Item", "Cantidad",
                "Observaciones", "Otros elementos", "Firma encargado logística"
            ]
            # Agregar columnas dinámicas para cada equipo
            for equipo in checklists.keys():
                headers_entrega.append(f"Cantidad {equipo}")
                headers_entrega.append(f"Descripción {equipo}")
                headers_entrega.append(f"Fotos {equipo}")
            # Agregar revisión general
            for item in revision_items:
                headers_entrega.append(item)
            row_entrega = [
                op_selected,
                fecha.strftime("%d-%m-%Y-%H:%M:%S") if hasattr(fecha, 'strftime') else str(fecha),
                cliente,
                equipo,
                item,
                cantidad,
                observaciones,
                otros_elementos,
                firma_url
            ]
            for equipo in checklists.keys():
                data = checklist_data[equipo]
                row_entrega.append(str(data["cantidad"]))
                row_entrega.append(data["descripcion"])
                row_entrega.append(", ".join(data["fotos"]))
            for item in revision_items:
                row_entrega.append(revision_general[item])
            # Guardar en Google Sheets
            try:
                worksheet = sheet_client.open(file_name).worksheet(worksheet_name_base)
                if not worksheet.get_all_values():
                    worksheet.append_row(headers_entrega)
                worksheet.append_row(row_entrega)
                st.success("Acta de entrega guardada exitosamente.")
            except Exception as e:
                st.error(f"Error al guardar en Google Sheets: {e}")
    else:
        # --- SECCIÓN LISTA DE EMPAQUE ---
        st.markdown("<h2>Lista de empaque</h2>", unsafe_allow_html=True)
        # Lógica y UI de lista de empaque (similar a lo que ya existe)
        folder_id = st.secrets.drive_config.FOLDER_ID
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        file_name = "dispatch_tekpro"
        worksheet_name = "Actas de entregas diligenciadas"
        st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales para empaque</b>", unsafe_allow_html=True)
        # Leer OPs ya diligenciadas en actas de entregas diligenciadas
        op_options_empaque = []
        op_to_row_empaque = {}
        op_selected_empaque = ""
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
            st.warning("No se pudo leer la hoja de actas de entregas diligenciadas para obtener las OP disponibles.")
        op_selected_empaque = st.selectbox("Selecciona la OP a empacar", options=[" "] + op_options_empaque, key="op_selectbox_empaque_1")

        # Definir variables en blanco por defecto
        op = ""
        fecha = ""
        cliente = ""
        equipo = ""
        encargado_ingenieria = ""
        # Selectbox para encargado almacén (ancho completo)
        encargados_almacen = ["", "Andrea Ochoa"]
        col_almacen = st.columns(1)
        encargado_almacen = col_almacen[0].selectbox("Encargado almacén", encargados_almacen, key="encargado_almacen_empaque")
        # Selectbox para encargado logística (ancho completo)
        encargados_logistica = ["", "Angela Zapata", "Jhon Restrepo", "Juan Rendon"]
        col_logistica = st.columns(1)
        encargado_logistica = col_logistica[0].selectbox("Encargado logística", encargados_logistica, key="encargado_logistica_empaque")

        if op_selected_empaque and op_selected_empaque.strip() != "":
            row = op_to_row_empaque.get(op_selected_empaque, [])
            headers_lower = [h.strip().lower() for h in all_rows[0]] if all_rows else []
            def get_val(col):
                col = col.strip().lower()
                idx = headers_lower.index(col) if col in headers_lower else None
                return row[idx] if idx is not None and idx < len(row) else ""
            # Solo los campos necesarios para empaque:
            op = op_selected_empaque
            fecha = get_val("fecha dili")
            cliente = get_val("cliente dili")
            equipo = get_val("equipo dili")
            encargado_ingenieria = get_val("diseñador dili")

        # Mostrar los datos SIEMPRE, aunque estén en blanco
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

        # Espacio para firma encargado logística
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

        # --- SOLO mostrar la sección de lista de empaque ---
        # (El resto del código de acta de entrega no se ejecuta)
        # Observaciones adicionales
        observaciones_adicionales = st.text_area("Observaciones adicionales", key="observaciones_adicionales")
        # Guardar solo en variable local para el guardado
        if st.button("Guardar Lista de Empaque", key="guardar_lista_empaque"):
            # Definir articulos_map localmente
            articulos_map = {
                "motores": ["motor_check", "Motores"],
                "reductores": ["reductor_check", "Reductores"],
                "bombas": ["bomba_check", "Bombas"],
                "turbina": ["turbina_check", "Turbina"],
                "quemador": ["quemador_check", "Quemador"],
                "bomba_vacio": ["bomba_vacio_check", "Bomba de vacío"],
                "compresor": ["compresor_check", "Compresor"],
                "manometros": ["manometro_check_accesorios2", "Manómetros"],
                "vacuometros": ["vacuometro_check_accesorios2", "Vacuómetros"],
                "valvulas": ["valvula_check_accesorios2", "Válvulas"],
                "mangueras": ["manguera_check_accesorios2", "Mangueras"],
                "boquillas": ["boquilla_check_accesorios2", "Boquillas"],
                "reguladores": ["regulador_check_accesorios2", "Reguladores aire/gas"],
                "tornillos": ["tornillos_check_accesorios2", "Tornillos"],
                "curvas": ["curvas_check_accesorios2", "Curvas"],
                "cables": ["cables_check_accesorios2", "Cables"],
                "tuberias": ["tuberias_check_accesorios2", "Tuberías"],
                "pinon1": ["pinon1_check_mecanicos_accesorios", "Piñón 1"],
                "pinon2": ["pinon2_check_mecanicos2", "Piñón 2"],
                "polea1": ["polea1_check_mecanicos2", "Polea 1"],
                "polea2": ["polea2_check_mecanicos2", "Polea 2"]
            }
            # Definir firma_url localmente
            firma_url = ""
            if 'firma_logistica_canvas' in st.session_state:
                canvas_result = st.session_state['firma_logistica_canvas']
                if hasattr(canvas_result, 'image_data') and canvas_result.image_data is not None:
                    from PIL import Image
                    import numpy as np
                    import tempfile
                    img = Image.fromarray((canvas_result.image_data).astype(np.uint8))
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                        img.save(tmpfile.name)
                        tmpfile.seek(0)
                        with open(tmpfile.name, "rb") as f:
                            firma_url = upload_image_to_drive_oauth(f, f"firma_logistica_{op}.png", st.secrets.drive_config.FOLDER_ID)
            # Determinar artículos empacados y no empacados
            articulos_enviados = []
            articulos_no_enviados = []
            if op_selected_empaque and op_selected_empaque.strip() != "":
                for key, (check_col, nombre) in articulos_map.items():
                    # Solo mostrar los que estaban presentes en el acta de entrega
                    idx = headers_lower.index(check_col) if check_col in headers_lower else None
                    if idx is not None and row[idx].strip().lower() in ["true", "1", "si", "yes", "x"]:
                        if st.session_state.get(f"empacar_{key}_empaque", False):
                            articulos_enviados.append(nombre)
                        else:
                            articulos_no_enviados.append(nombre)
            # Si no hay OP seleccionada, dejar listas vacías
            # Guardar datos en Google Sheets (hoja Lista de empaque)
            file_name_empaque = "dispatch_tekpro"
            worksheet_name_empaque = "Lista de empaque"
            # Subir fotos de todos los guacales a Drive y guardar enlaces
            guacales_data = []
            num_guacales = len(st.session_state['guacales']) if 'guacales' in st.session_state else 0
            for idx in range(num_guacales):
                guacal = st.session_state['guacales'][idx]
                urls_fotos = []
                for j, file in enumerate(guacal['fotos']):
                    if file is not None:
                        url = upload_image_to_drive_oauth(file, f"guacal{idx+1}_{op}_{j+1}.jpg", st.secrets.drive_config.FOLDER_ID)
                        urls_fotos.append(url)
                guacales_data.append({
                    'descripcion': guacal['descripcion'],
                    'fotos': urls_fotos
                })
            # Encabezados base
            headers_empaque = [
                "Op", "Fecha", "Cliente", "Equipo", "Encargado almacén", "Encargado ingeniería y diseño", "Encargado logística", "Firma encargado logística", "Observaciones adicionales", "Artículos enviados", "Artículos no enviados"
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
                observaciones_adicionales,
                ", ".join(articulos_enviados),
                ", ".join(articulos_no_enviados)
            ]
            # Agregar columnas dinámicamente para cada guacal
            for idx, guacal in enumerate(guacales_data):
                headers_empaque.append(f"Descripción Guacal {idx+1}")
                headers_empaque.append(f"Fotos Guacal {idx+1}")
                row_empaque.append(guacal['descripcion'])
                row_empaque.append(", ".join(guacal['fotos']))
            # Guardar en sheet
            try:
                sheet_empaque = sheet_client.open(file_name_empaque).worksheet(worksheet_name_empaque)
            except Exception:
                # Si la hoja no existe, crearla y poner encabezados
                sheet_empaque = sheet_client.open(file_name_empaque).add_worksheet(title=worksheet_name_empaque, rows=100, cols=len(headers_empaque))
                sheet_empaque.append_row(headers_empaque)
            # Si la hoja está vacía, poner encabezados
            if not sheet_empaque.get_all_values():
                sheet_empaque.append_row(headers_empaque)
            sheet_empaque.append_row(row_empaque)
            st.success(f"Lista de empaque guardada en Google Sheets. Enlace de la firma: {firma_url if firma_url else 'No se capturó firma.'}")

def upload_image_to_drive_oauth(file, filename, folder_id):
    """
    Sube un archivo a Google Drive usando OAuth2 y devuelve el enlace público.
    file: archivo tipo file-like (por ejemplo, open(..., 'rb'))
    filename: nombre del archivo en Drive
    folder_id: ID de la carpeta de destino en Drive
    """
    # Obtener credenciales de usuario (de st.session_state)
    if 'drive_oauth_token' not in st.session_state:
        st.error("No hay token OAuth2 de Google Drive. Autoriza primero.")
        st.stop()
    creds = UserCreds.from_authorized_user_info(st.session_state['drive_oauth_token'])
    drive_service = build('drive', 'v3', credentials=creds)
    media = MediaIoBaseUpload(file, mimetype='image/png', resumable=True)
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
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

# Dummy para evitar error
def store_files(files, key):
    pass

def to_url_list(key):
    # Dummy para evitar error
    return ""

main()
