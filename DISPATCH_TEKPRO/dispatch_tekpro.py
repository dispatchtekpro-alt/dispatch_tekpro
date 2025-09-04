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
import concurrent.futures


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

# Autorizar Drive con OAuth2
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

# Subir imagen a Drive usando OAuth2 (con detección automática de mimetype)
def upload_image_to_drive_oauth(file, filename, folder_id):
    drive_service = get_drive_service_oauth()
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    # Detectar automáticamente el tipo MIME según la extensión
    if hasattr(file, 'type') and file.type:
        mime_type = file.type
    else:
        # Fallback al tipo basado en la extensión
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.jpg' or ext == '.jpeg':
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        else:
            mime_type = 'image/jpeg'  # Default
    
    media = MediaIoBaseUpload(file, mimetype=mime_type)
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

# Función para subir imágenes en paralelo
def upload_images_parallel(files, prefix, folder_id):
    if not files:
        return []
    
    urls = []
    
    def upload_single(args):
        idx, file = args
        if file is not None:
            try:
                url = upload_image_to_drive_oauth(file, f"{prefix}_{idx+1}.jpg", folder_id)
                return url
            except Exception as e:
                st.error(f"Error al subir {prefix}_{idx+1}: {e}")
                return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(upload_single, enumerate(files)))
    
    return [r for r in results if r is not None]

# Escribir link en Google Sheets
def write_link_to_sheet(sheet_client, file_name, worksheet_name, row):
    sheet = sheet_client.open(file_name).worksheet(worksheet_name)
    sheet.append_row(row)

# Funciones auxiliares para gestión de estado
def store_files(files, state_key):
    if files is not None:
        st.session_state[state_key + "_files"] = files
    else:
        st.session_state[state_key + "_files"] = []

def to_url_list(state_key):
    return ", ".join(st.session_state.get(state_key + "_links", []))

# Función para manejar elementos genéricos (reduce duplicación de código)
def handle_element(name, label, key_prefix, folder_id, has_cantidad=True, has_voltaje=False, 
                   has_tension=False, has_descripcion=False, has_tipo_combustible=False, 
                   has_metodo_uso=False):
    with st.expander(label, expanded=True):
        st.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
        col = st.columns(1)
        
        inputs = {}
        
        if has_cantidad:
            cantidad = col[0].number_input(f"Cantidad {label.lower()}", min_value=0, step=1, format="%d", 
                                         key=f"cantidad_{key_prefix}")
            inputs[f"cantidad_{key_prefix}"] = cantidad
        
        if has_voltaje:
            voltaje = col[0].text_input(f"Voltaje {label.lower()}", key=f"voltaje_{key_prefix}")
            inputs[f"voltaje_{key_prefix}"] = voltaje
            
        if has_tension:
            tension = col[0].text_input(f"Tensión {label.lower()}", key=f"tension_{key_prefix}")
            inputs[f"tension_{key_prefix}"] = tension
            
        if has_tipo_combustible:
            tipo = col[0].selectbox("Tipo de combustible", ["", "Gas Natural", "GLP", "ACPM"], 
                                   key=f"tipo_combustible_{key_prefix}")
            inputs[f"tipo_combustible_{key_prefix}"] = tipo
            
        if has_metodo_uso:
            metodo = col[0].selectbox("Método de uso", ["", "Alto/Bajo", "On/Off"], 
                                     key=f"metodo_uso_{key_prefix}")
            inputs[f"metodo_uso_{key_prefix}"] = metodo
            
        if has_descripcion:
            descripcion = col[0].text_area(f"Descripción {label.lower()}", key=f"descripcion_{key_prefix}")
            inputs[f"descripcion_{key_prefix}"] = descripcion
        
        fotos = col[0].file_uploader(f"Foto {label.lower()}", type=["jpg","jpeg","png"], 
                                    accept_multiple_files=True, key=f"fotos_{key_prefix}")
        
        # Guardar en session_state
        for k, v in inputs.items():
            st.session_state[k] = v
            
        store_files(fotos, key_prefix)
        
        return fotos

# Función para la sección principal
def main():
    # Centralización del folder_id (aquí evitamos el bug del folder_id no definido)
    folder_id = st.secrets.drive_config.FOLDER_ID if 'drive_config' in st.secrets else ""
    
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

    # ------------ ACTA DE ENTREGA ------------
    if menu_opcion == "Acta de entrega":
        st.markdown("<h1 style='color:#1db6b6;font-family:Montserrat,Arial,sans-serif;font-weight:700;'>ACTA DE ENTREGA TEKPRO</h1>", unsafe_allow_html=True)
        st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;'>", unsafe_allow_html=True)
        
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        file_name = "dispatch_tekpro"
        worksheet_name_base = "Acta de entrega"
        worksheet_name_diligenciadas = "Actas de entregas diligenciadas"
        
        # Cargar OPs y filtrar las ya diligenciadas
        op_options = []
        ops_guardadas = set()
        
        # Leer OPs base desde la hoja plantilla
        try:
            sheet_base = sheet_client.open(file_name).worksheet(worksheet_name_base)
            all_rows_base = sheet_base.get_all_values()
            if all_rows_base:
                headers_lower = [h.strip().lower() for h in all_rows_base[0]]
                op_idx = headers_lower.index("op") if "op" in headers_lower else None
                for r in all_rows_base[1:]:
                    if op_idx is not None and len(r) > op_idx and r[op_idx].strip():
                        op_options.append(r[op_idx].strip())
        except Exception as e:
            st.warning(f"Error al leer OPs de la hoja base: {e}")
            op_options = []
            
        # Leer todas las OPs ya guardadas en la hoja 'Actas de entregas diligenciadas'
        try:
            # Optimización: solo buscar columna OP en vez de toda la hoja
            sheet_diligenciadas = sheet_client.open(file_name).worksheet(worksheet_name_diligenciadas)
            all_rows_diligenciadas = sheet_diligenciadas.get_all_values()
            if all_rows_diligenciadas:
                headers_lower = [h.strip().lower() for h in all_rows_diligenciadas[0]]
                op_idx = headers_lower.index("op dili") if "op dili" in headers_lower else None
                for r in all_rows_diligenciadas[1:]:
                    if op_idx is not None and len(r) > op_idx and r[op_idx].strip():
                        ops_guardadas.add(r[op_idx].strip())
        except Exception:
            ops_guardadas = set()
            
        # Filtrar solo las OPs que no han sido guardadas
        op_options_filtradas = [op for op in op_options if op not in ops_guardadas]
        op_options_filtradas = list(dict.fromkeys(op_options_filtradas))  # Eliminar duplicados
        
        op_selected = st.selectbox("Orden de compra (OP)", 
                                options=[" "] + op_options_filtradas, 
                                key="op_input_selectbox")
        
        # --- AUTOLLENADO DE DATOS GENERALES ---
        op_row = []
        headers_base = [h.strip().lower() for h in all_rows_base[0]] if all_rows_base else []
        
        if op_selected and op_selected.strip() != " ":
            op_idx = headers_base.index("op") if "op" in headers_base else None
            for r in all_rows_base[1:]:
                if op_idx is not None and len(r) > op_idx and r[op_idx].strip() == op_selected.strip():
                    op_row = r
                    break
                    
        # Definir get_base_val para extraer valores de la fila seleccionada
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

        # Diccionario para almacenar las fotos subidas por categoría
        uploaded_files = {}
        
        # Lista de chequeo elementos electromecánicos
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
            
            # Usar la nueva función handle_element para cada tipo de elemento
            if motor_checked:
                uploaded_files['motores'] = handle_element("motores", "Motores", "motores", folder_id, 
                                                         has_cantidad=True, has_voltaje=True)
                
            if reductor_checked:
                uploaded_files['reductores'] = handle_element("reductores", "Reductores", "reductores", folder_id,
                                                           has_cantidad=True, has_voltaje=True)
                
            if bomba_checked:
                uploaded_files['bombas'] = handle_element("bombas", "Bombas", "bombas", folder_id,
                                                       has_cantidad=True, has_voltaje=True)
                
            if turbina_checked:
                uploaded_files['turbina'] = handle_element("turbina", "Turbinas", "turbina", folder_id,
                                                        has_voltaje=True)
                
            if quemador_checked:
                uploaded_files['quemador'] = handle_element("quemador", "Quemadores", "quemador", folder_id,
                                                         has_voltaje=True, has_tipo_combustible=True, has_metodo_uso=True)
                
            if bomba_vacio_checked:
                uploaded_files['bomba_vacio'] = handle_element("bomba_vacio", "Bombas de vacío", "bomba_vacio", folder_id,
                                                            has_voltaje=True)
                
            if compresor_checked:
                uploaded_files['compresor'] = handle_element("compresor", "Compresores", "compresor", folder_id,
                                                          has_voltaje=True)

        # Lista de chequeo accesorios
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
            
            # Manejar cada tipo de accesorio
            if manometro_checked:
                uploaded_files['manometros'] = handle_element("manometros", "Manómetros", "manometros", folder_id)
                
            if vacuometro_checked:
                uploaded_files['vacuometros'] = handle_element("vacuometros", "Vacuómetros", "vacuometros", folder_id)
                
            if valvula_checked:
                uploaded_files['valvulas'] = handle_element("valvulas", "Válvulas", "valvulas", folder_id)
                
            if manguera_checked:
                uploaded_files['mangueras'] = handle_element("mangueras", "Mangueras", "mangueras", folder_id)
                
            if boquilla_checked:
                uploaded_files['boquillas'] = handle_element("boquillas", "Boquillas", "boquillas", folder_id)
                
            if regulador_checked:
                uploaded_files['reguladores'] = handle_element("reguladores", "Reguladores aire/gas", "reguladores", folder_id)
                
            if tornillos_checked:
                uploaded_files['tornillos'] = handle_element("tornillos", "Tornillos", "tornillos", folder_id)
                
            if curvas_checked:
                uploaded_files['curvas'] = handle_element("curvas", "Curvas", "curvas", folder_id,
                                                      has_descripcion=True)
                
            if cables_checked:
                uploaded_files['cables'] = handle_element("cables", "Cables", "cables", folder_id,
                                                      has_descripcion=True)
                
            if tuberias_checked:
                uploaded_files['tuberias'] = handle_element("tuberias", "Tuberías", "tuberias", folder_id,
                                                        has_descripcion=True)
            
        # Lista de chequeo elementos mecánicos
        if mostrar_mecanicos:
            st.markdown("""
                <h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general elementos mecánicos</h3>
            """, unsafe_allow_html=True)
            
            pinon1_checked = st.checkbox("¿Hay piñón 1?", key="pinon1_check_mecanicos_accesorios")
            pinon2_checked = st.checkbox("¿Hay piñón 2?", key="pinon2_check_mecanicos2")
            polea1_checked = st.checkbox("¿Hay polea 1?", key="polea1_check_mecanicos2")
            polea2_checked = st.checkbox("¿Hay polea 2?", key="polea2_check_mecanicos2")
            st.markdown("<hr>", unsafe_allow_html=True)
            
            # Manejar cada elemento mecánico
            if pinon1_checked:
                uploaded_files['pinon1'] = handle_element("pinon1", "Piñón 1", "pinon1", folder_id,
                                                      has_cantidad=False, has_tension=True)
                
            if pinon2_checked:
                uploaded_files['pinon2'] = handle_element("pinon2", "Piñón 2", "pinon2", folder_id,
                                                      has_cantidad=False, has_tension=True)
                
            if polea1_checked:
                uploaded_files['polea1'] = handle_element("polea1", "Polea 1", "polea1", folder_id,
                                                      has_cantidad=False, has_tension=True)
                
            if polea2_checked:
                uploaded_files['polea2'] = handle_element("polea2", "Polea 2", "polea2", folder_id,
                                                      has_cantidad=False, has_tension=True)
                
        # Lista de chequeo elementos eléctricos
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
            
            # Manejar cada elemento eléctrico
            if gabinete_checked:
                uploaded_files['gabinete'] = handle_element("gabinete", "Gabinete eléctrico", "gabinete", folder_id,
                                                         has_descripcion=True)
                
            if arrancador_checked:
                uploaded_files['arrancadores'] = handle_element("arrancadores", "Arrancador", "arrancadores", folder_id,
                                                             has_descripcion=True)
                
            if control_nivel_checked:
                uploaded_files['control_nivel'] = handle_element("control_nivel", "Control de nivel", "control_nivel", folder_id,
                                                              has_descripcion=True)
                
            if variador_checked:
                uploaded_files['variador'] = handle_element("variador", "Variador de velocidad", "variador", folder_id,
                                                         has_descripcion=True)
                
            if sensor_temp_checked:
                uploaded_files['sensor_temp'] = handle_element("sensor_temp", "Sensor de temperatura", "sensor_temp", folder_id,
                                                           has_descripcion=True)
                
            if toma_corriente_checked:
                uploaded_files['toma_corriente'] = handle_element("toma_corriente", "Toma corriente", "toma_corriente", folder_id,
                                                               has_descripcion=True)

        # Otros elementos
        mostrar_otros_elementos = st.checkbox("Otros elementos", key="cb_otros_elementos")
        if mostrar_otros_elementos:
            with st.expander("Otros elementos", expanded=True):
                otros_elementos = st.text_area("Descripción de otros elementos", key="otros_elementos")
                fotos_otros_elementos = st.file_uploader("Foto(s) de otros elementos", type=["jpg","jpeg","png"], 
                                                      accept_multiple_files=True, key="fotos_otros_elementos")
                store_files(fotos_otros_elementos, "otros_elementos")
                uploaded_files['otros_elementos'] = fotos_otros_elementos

        # Selectboxes de revisión general
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

        # Personal técnico
        col_lider = st.columns(1)
        lideres = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata","Juan David Martinez"]
        lider_inspeccion = col_lider[0].selectbox("Líder de inspección", lideres, key="lider_inspeccion")

        col_soldador = st.columns(1)
        soldadores = ["", "Jaime Ramos", "Jaime Rincon", "Gabriel","Lewis"]
        soldador = col_soldador[0].selectbox("Encargado Soldador", soldadores, key="soldador")

        col_disenador = st.columns(1)
        disenadores = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata","Juan David Martinez"]
        disenador = col_disenador[0].selectbox("Diseñador", disenadores, key="disenador")

        # Fecha y hora de entrega
        col_fecha = st.columns(1)
        fecha_entrega = col_fecha[0].date_input("Fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta")
        hora_entrega = col_fecha[0].time_input("Hora de entrega", value=datetime.datetime.now().time(), key="hora_entrega_acta")

        # Mostrar fecha y hora en formato DD-MM-AA-HH:MM:SS
        dt_entrega = datetime.datetime.combine(fecha_entrega, hora_entrega)
        fecha_hora_formateada = dt_entrega.strftime("%d-%m-%y-%H:%M:%S")
        st.info(f"Fecha y hora de entrega: {fecha_hora_formateada}")

        # Botón para enviar el acta de entrega
        enviar_acta = st.button("Enviar Acta de Entrega", key="enviar_acta_entrega")
        
        # Validación y guardado de datos
        if enviar_acta:
            # Validar campos obligatorios
            if not op or not cliente or not equipo:
                st.error("Debes completar al menos los campos: OP, Cliente y Equipo")
                st.stop()
                
            # Subir imágenes a Drive de forma paralela
            uploaded_urls = {}
            
            with st.spinner("Subiendo imágenes..."):
                for key, files in uploaded_files.items():
                    if files:
                        uploaded_urls[key] = upload_images_parallel(files, key, folder_id)
                        # Guardar URLs en session_state para referencia posterior
                        st.session_state[key + "_links"] = uploaded_urls.get(key, [])
            
            # Preparar fila para Google Sheets
            # Corrección del bug: usar las claves correctas en session_state
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
                str(st.session_state.get("cantidad_variador", "")),  # Corrección del bug
                to_url_list("variador"),
                str(st.session_state.get("cantidad_sensor_temp", "")),  # Corrección del bug
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
                str(revision_soldadura),
                str(revision_sentidos),
                str(manual_funcionamiento),
                str(revision_filos),
                str(revision_tratamientos),
                str(revision_tornilleria),
                str(revision_ruidos),
                str(ensayo_equipo),
                str(observaciones_generales),
                str(lider_inspeccion),
                str(soldador),
                str(disenador),
                str(fecha_entrega)
            ]
            
            # Guardar en Google Sheets
            try:
                # Verificar si existe la hoja
                try:
                    sheet_diligenciadas = sheet_client.open(file_name).worksheet(worksheet_name_diligenciadas)
                except:
                    # Crear la hoja con los encabezados si no existe
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
                    sheet_diligenciadas = sheet_client.open(file_name).add_worksheet(
                        title=worksheet_name_diligenciadas, rows=100, cols=len(headers))
                    sheet_diligenciadas.append_row(headers)
                
                # Verificar si la hoja está vacía y necesita encabezados
                if not sheet_diligenciadas.get_all_values():
                    headers = [
                        "cliente dili", "op dili", "item dili", "equipo dili", "cantidad dili", "fecha dili",
                        # ... (resto de headers igual que arriba)
                    ]
                    sheet_diligenciadas.append_row(headers)
                
                # Guardar la fila de datos
                sheet_diligenciadas.append_row(row)
                st.success("Acta de entrega guardada correctamente en 'Actas de entregas diligenciadas'.")
                
            except Exception as e:
                st.error(f"Error al guardar los datos: {e}")

    # ------------ LISTA DE EMPAQUE ------------
    if menu_opcion == "Lista de empaque":
        st.markdown("<h1 style='color:#1db6b6;font-family:Montserrat,Arial,sans-serif;font-weight:700;'>LISTA DE EMPAQUE TEKPRO</h1>", unsafe_allow_html=True)
        st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;'>", unsafe_allow_html=True)
        
        # Inicializar folder_id de nuevo para asegurar que está disponible
        folder_id = st.secrets.drive_config.FOLDER_ID if 'drive_config' in st.secrets else ""
        
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        file_name = "dispatch_tekpro"
        worksheet_name = "Acta de entrega"
        
        st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales para empaque</b>", unsafe_allow_html=True)
        
        # Cargar opciones de OP
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
        except Exception as e:
            st.warning(f"No se pudo leer la hoja de acta de entrega: {e}")
            op_options_empaque = []
            
        # Seleccionar OP
        op_selected_empaque = st.selectbox("Selecciona la OP a empacar", 
                                        options=[" "] + op_options_empaque, 
                                        key="op_selectbox_empaque_2")
        
        # Inicializar variables
        op = ""
        fecha = ""
        cliente = ""
        equipo = ""
        encargado_ingenieria = ""
        
        # Cargar datos de la OP seleccionada
        if op_selected_empaque and op_selected_empaque.strip() != " ":
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
            
        # Seleccionar personal encargado
        encargados_almacen = ["", "Andrea Ochoa"]
        col_almacen = st.columns(1)
        encargado_almacen = col_almacen[0].selectbox("Encargado almacén", 
                                                  encargados_almacen, 
                                                  key="encargado_almacen_empaque")
        
        encargados_logistica = ["", "Angela Zapata", "Jhon Restrepo", "Juan Rendon"]
        col_logistica = st.columns(1)
        encargado_logistica = col_logistica[0].selectbox("Encargado logística", 
                                                      encargados_logistica, 
                                                      key="encargado_logistica_empaque")
        
        # Mostrar resumen de datos
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
        
        # Firma digital
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
        
        # Mostrar firma
        if canvas_result.image_data is not None:
            # Verificar que no sea una imagen vacía
            if np.sum(canvas_result.image_data) > 0:
                st.image(canvas_result.image_data, caption="Firma digital de logística", use_container_width=False)
        
        observaciones_adicionales = st.text_area("Observaciones adicionales", 
                                              key="observaciones_adicionales")
        
        # Gestión de guacales
        st.markdown("<h3>Guacales</h3>", unsafe_allow_html=True)
        
        if 'guacales' not in st.session_state:
            st.session_state['guacales'] = []

        def add_guacal():
            st.session_state['guacales'].append({'descripcion': '', 'fotos': []})

        st.button("Agregar guacal", on_click=add_guacal, key="btn_agregar_guacal")
        
        # Crear expanders para cada guacal
        for idx, guacal in enumerate(st.session_state['guacales']):
            with st.expander(f"Guacal {idx+1}", expanded=True):
                descripcion = st.text_area(f"Descripción del guacal {idx+1}", 
                                         value=guacal['descripcion'], 
                                         key=f"descripcion_guacal_{idx+1}")
                                         
                fotos = st.file_uploader(f"Foto(s) del guacal {idx+1}", 
                                       type=["jpg","jpeg","png"], 
                                       accept_multiple_files=True, 
                                       key=f"fotos_guacal_{idx+1}")
                                       
                guacal['descripcion'] = descripcion
                guacal['fotos'] = fotos if fotos else []
        
        # Botón para enviar la lista de empaque
        enviar_empaque = st.button("Enviar Lista de Empaque", key="enviar_lista_empaque")
        
        if enviar_empaque:
            # Validar campos obligatorios
            if not op or not cliente or not equipo or not encargado_logistica:
                st.error("Debes completar al menos los campos: OP, Cliente, Equipo y Encargado logística")
                st.stop()
            
            # Subir fotos de guacales a Drive
            guacales_data = []
            
            with st.spinner("Subiendo imágenes de guacales..."):
                for idx, guacal in enumerate(st.session_state['guacales']):
                    urls_fotos = upload_images_parallel(
                        guacal['fotos'], 
                        f"guacal{idx+1}_{op}", 
                        folder_id
                    )
                    
                    guacales_data.append({
                        'descripcion': guacal['descripcion'],
                        'fotos': urls_fotos
                    })
            
            # Subir firma a Drive
            firma_url = ""
            if canvas_result.image_data is not None and np.sum(canvas_result.image_data) > 0:
                with st.spinner("Guardando firma digital..."):
                    img = Image.fromarray((canvas_result.image_data).astype(np.uint8))
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                        img.save(tmpfile.name)
                        tmpfile.seek(0)
                        with open(tmpfile.name, "rb") as f:
                            firma_url = upload_image_to_drive_oauth(f, f"firma_logistica_{op}.png", folder_id)
            
            # Encabezados base
            headers_empaque = [
                "Op", "Fecha", "Cliente", "Equipo", "Encargado almacén", 
                "Encargado ingeniería y diseño", "Encargado logística", 
                "Firma encargado logística", "Observaciones adicionales"
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
            
            # Guardar en Google Sheets
            file_name_empaque = "dispatch_tekpro"
            worksheet_name_empaque = "Lista de empaque"
            
            try:
                # Verificar si existe la hoja
                try:
                    sheet_empaque = sheet_client.open(file_name_empaque).worksheet(worksheet_name_empaque)
                except:
                    # Crear la hoja si no existe
                    sheet_empaque = sheet_client.open(file_name_empaque).add_worksheet(
                        title=worksheet_name_empaque, 
                        rows=100, 
                        cols=len(headers_empaque)
                    )
                    sheet_empaque.append_row(headers_empaque)
                
                # Verificar si la hoja está vacía y necesita encabezados
                if not sheet_empaque.get_all_values():
                    sheet_empaque.append_row(headers_empaque)
                
                # Guardar la fila de datos
                sheet_empaque.append_row(row_empaque)
                st.success("Lista de empaque guardada correctamente en Google Sheets.")
                
            except Exception as e:
                st.error(f"Error al guardar la lista de empaque: {e}")

if __name__ == "__main__":
    main()
