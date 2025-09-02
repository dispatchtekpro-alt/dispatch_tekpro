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

def main():


    # Menú de inicio
    col1, col2 = st.columns([4,1])
    with col1:
        st.markdown("""
        <h1 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 700; letter-spacing: 1px;'>DISPATCH TEKPRO</h1>
        <h2 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 600; font-size: 1.5em;'>Menú principal</h2>
        """, unsafe_allow_html=True)
    with col2:
        st.image("https://drive.google.com/thumbnail?id=19MGYsVVEtnwv8SpdnRw4TainlJBsQLSE", width=150)
    st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;'>", unsafe_allow_html=True)

    # --- MENU PRINCIPAL ---
    menu_opcion = st.radio(
        "¿Qué deseas diligenciar?",
        ["Actaaaaa de entrega", "Lista de empaque"],
        horizontal=True,
        key="menu_opcion_radio"
    )

    if menu_opcion == "Actaaaaa de entrega":
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        folder_id = st.secrets.drive_config.FOLDER_ID
        file_name = st.secrets.drive_config.FILE_NAME
        worksheet_name = "Acta de entrega"
        st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales del acta de entrega</b>", unsafe_allow_html=True)
        auto_cliente = auto_equipo = auto_item = auto_cantidad = ""
        auto_fecha = datetime.date.today()
        op_options, op_to_row = [], {}
        try:
            sheet = sheet_client.open(file_name).worksheet(worksheet_name)
            all_rows = sheet.get_all_values()
            if all_rows:
                headers_lower = [h.strip().lower() for h in all_rows[0]]
                op_idx = headers_lower.index("op") if "op" in headers_lower else None
                for r in all_rows[1:]:
                    if op_idx is not None and len(r) > op_idx and r[op_idx].strip():
                        op_options.append(r[op_idx].strip()); op_to_row[r[op_idx].strip()] = r
        except Exception:
            pass
        op_selected = st.selectbox("op", options=[" "] + op_options, key="op_selectbox_main")
        if op_selected != "":
            r = op_to_row.get(op_selected, [])
            if r:
                headers_lower = [h.strip().lower() for h in all_rows[0]]
                cliente_idx = headers_lower.index("cliente") if "cliente" in headers_lower else None
                equipo_idx = headers_lower.index("equipo") if "equipo" in headers_lower else None
                item_idx = headers_lower.index("item") if "item" in headers_lower else None
                cantidad_idx = headers_lower.index("cantidad") if "cantidad" in headers_lower else None
                fecha_idx = headers_lower.index("fecha") if "fecha" in headers_lower else None
                auto_cliente = r[cliente_idx] if cliente_idx is not None and len(r) > cliente_idx else ""
                auto_equipo = r[equipo_idx] if equipo_idx is not None and len(r) > equipo_idx else ""
                auto_item = r[item_idx] if item_idx is not None and len(r) > item_idx else ""
                auto_cantidad = r[cantidad_idx] if cantidad_idx is not None and len(r) > cantidad_idx else ""
                if fecha_idx is not None and len(r) > fecha_idx and r[fecha_idx]:
                    try:
                        auto_fecha = datetime.datetime.strptime(r[fecha_idx], "%Y-%m-%d").date()
                    except Exception:
                        auto_fecha = datetime.date.today()
                else:
                    auto_fecha = datetime.date.today()

        cliente = st.text_input("cliente", value=auto_cliente, key="cliente_input")
        op = op_selected
        equipo = st.text_input("equipo", value=auto_equipo, key="equipo_input")
        item = st.text_input("item", value=auto_item, key="item_input")
        cantidad = st.text_input("cantidad", value=auto_cantidad, key="cantidad_input")
        fecha = st.date_input("fecha", value=auto_fecha, key="fecha_acta_input")

        # Listas de chequeo: solo un bloque de cada tipo
        st.markdown("<h4>Listas de chequeo</h4>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            mostrar_electromecanicos = st.checkbox("Elementos electromecánicos", key="cb_electromecanicos")
        with col2:
            mostrar_accesorios = st.checkbox("Accesorios", key="cb_accesorios")
        with col3:
            mostrar_mecanicos = st.checkbox("Elementos mecánicos", key="cb_mecanicos")
        with col4:
            mostrar_electricos = st.checkbox("Elementos eléctricos", key="cb_electricos")

        # Aquí van los bloques únicos de cada lista de chequeo (ya presentes más abajo en el código)
        # ...existing code...
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
            st.markdown("<hr>", unsafe_allow_html=True)

        if mostrar_accesorios:
            if manometro_checked:
                with st.expander("Manómetros", expanded=True):
                    st.markdown("<b>Manómetros</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad manómetros", min_value=0, step=1, format="%d", key="cantidad_manometros")
                    st.file_uploader("Foto manómetros", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_manometros")
            if vacuometro_checked:
                with st.expander("Vacuómetros", expanded=True):
                    st.markdown("<b>Vacuómetros</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad vacuómetros", min_value=0, step=1, format="%d", key="cantidad_vacuometros")
                    st.file_uploader("Foto vacuómetros", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_vacuometros")
            if valvula_checked:
                with st.expander("Válvulas", expanded=True):
                    st.markdown("<b>Válvulas</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad válvulas", min_value=0, step=1, format="%d", key="cantidad_valvulas")
                    st.file_uploader("Foto válvulas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_valvulas")
            if manguera_checked:
                with st.expander("Mangueras", expanded=True):
                    st.markdown("<b>Mangueras</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad mangueras", min_value=0, step=1, format="%d", key="cantidad_mangueras")
                    st.file_uploader("Foto mangueras", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_mangueras")
            if boquilla_checked:
                with st.expander("Boquillas", expanded=True):
                    st.markdown("<b>Boquillas</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad boquillas", min_value=0, step=1, format="%d", key="cantidad_boquillas")
                    st.file_uploader("Foto boquillas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_boquillas")
            if regulador_checked:
                with st.expander("Reguladores aire/gas", expanded=True):
                    st.markdown("<b>Reguladores aire/gas</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad reguladores aire/gas", min_value=0, step=1, format="%d", key="cantidad_reguladores")
                    st.file_uploader("Foto reguladores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_reguladores")
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
                    st.text_input("Tensión piñón 1", key="tension_pinon1")
                    st.file_uploader("Foto piñón 1", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_pinon1")
            if pinon2_checked:
                with st.expander("Piñón 2", expanded=True):
                    st.markdown("<b>Piñón 2</b>", unsafe_allow_html=True)
                    st.text_input("Tensión piñón 2", key="tension_pinon2")
                    st.file_uploader("Foto piñón 2", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_pinon2")
            if polea1_checked:
                with st.expander("Polea 1", expanded=True):
                    st.markdown("<b>Polea 1</b>", unsafe_allow_html=True)
                    st.text_input("Tensión polea 1", key="tension_polea1")
                    st.file_uploader("Foto polea 1", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_polea1")
            if polea2_checked:
                with st.expander("Polea 2", expanded=True):
                    st.markdown("<b>Polea 2</b>", unsafe_allow_html=True)
                    st.text_input("Tensión polea 2", key="tension_polea2")
                    st.file_uploader("Foto polea 2", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_polea2")
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
                    st.number_input("Cantidad gabinete eléctrico", min_value=0, step=1, format="%d", key="cantidad_gabinete")
                    st.file_uploader("Foto gabinete", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_gabinete")
            if arrancador_checked:
                with st.expander("Arrancador", expanded=True):
                    st.markdown("<b>Arrancador</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad arrancadores", min_value=0, step=1, format="%d", key="cantidad_arrancadores")
                    st.file_uploader("Foto arrancadores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_arrancadores")
            if control_nivel_checked:
                with st.expander("Control de nivel", expanded=True):
                    st.markdown("<b>Control de nivel</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad control de nivel", min_value=0, step=1, format="%d", key="cantidad_control_nivel")
                    st.file_uploader("Foto control de nivel", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_control_nivel")
            if variador_checked:
                with st.expander("Variador de velocidad", expanded=True):
                    st.markdown("<b>Variador de velocidad</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad variadores de velocidad", min_value=0, step=1, format="%d", key="cantidad_variador")
                    st.file_uploader("Foto variador de velocidad", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_variador")
            if sensor_temp_checked:
                with st.expander("Sensor de temperatura", expanded=True):
                    st.markdown("<b>Sensor de temperatura</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad sensores de temperatura", min_value=0, step=1, format="%d", key="cantidad_sensor_temp")
                    st.file_uploader("Foto sensor de temperatura", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_sensor_temp")
            if toma_corriente_checked:
                with st.expander("Toma corriente", expanded=True):
                    st.markdown("<b>Toma corriente</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad tomas corriente", min_value=0, step=1, format="%d", key="cantidad_toma_corriente")
                    st.file_uploader("Foto toma corriente", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_toma_corriente")

    elif menu_opcion == "Lista de empaque":
            lider_inspeccion = st.text_input("lider de inspeccion")
            encargado_ensamblador = st.text_input("encargado ensamblador")
            disenador = st.selectbox("diseñador", ["", "Daniel Valbuena", "Juan David Martinez", "Juan Andres Zapata", "Alejandro Diaz"]) 
            # Fecha de entrega con hora
            try:
                fecha_entrega = st.datetime_input("fecha y hora de entrega", value=datetime.datetime.now(), key="fecha_entrega_acta")
            except AttributeError:
                fecha_date = st.date_input("Fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta_date")
                fecha_time = st.time_input("Hora de entrega", value=datetime.datetime.now().time(), key="fecha_entrega_acta_time")
                fecha_entrega = datetime.datetime.combine(fecha_date, fecha_time)

            submitted_acta = st.button("Guardar lista de empaque")

            if submitted_acta:
                row = [
                    str(cliente), str(op), str(item), str(equipo), str(cantidad), str(fecha),
                    str(lider_inspeccion), str(encargado_ensamblador), str(disenador), str(fecha_entrega)
                ]
                    # ...campos eliminados, solo dejar los campos válidos para acta de entrega o lista de empaque...
                

                headers = [
                    "cliente", "op", "item", "equipo", "cantidad", "fecha",
                    "cantidad motores", "voltaje motores", "fotos motores",
                    "cantidad reductores", "voltaje reductores", "fotos reductores",
                    "cantidad bombas", "voltaje bombas", "fotos bombas",
                    "voltaje turbina", "foto turbina",
                    "voltaje quemador", "foto quemador",
                    "voltaje bomba de vacio", "foto bomba de vacio",
                    "voltaje compresor", "foto compresor",
                    "cantidad manometros", "foto manometros",
                    "cantidad vacuometros", "foto vacuometros",
                    "cantidad valvulas", "foto valvulas",
                    "cantidad mangueras", "foto mangueras",
                    "cantidad boquillas", "foto boquillas",
                    "cantidad reguladores aire/gas", "foto reguladores",
                    "tension piñon 1", "foto piñon 1",
                    "tension piñon 2", "foto piñon 2",
                    "tension polea 1", "foto polea 1",
                    "tension polea 2", "foto polea 2",
                    "cantidad gabinete electrico", "foto gabinete",
                    "cantidad arrancadores", "foto arrancadores",
                    "cantidad control de nivel", "foto control de nivel",
                    "cantidad variadores de velociad", "foto variadores de velocidad",
                    "cantidad sensores de temperatura", "foto sensores de temperatura",
                    "cantidad toma corriente", "foto toma corrientes",
                    "otros elementos", "fotos otros elementos",
                    "descripcion tuberias", "foto tuberias",
                    "descripcion curvas", "foto curvas",
                    "descripcion tornilleria", "foto tornilleria",
                    "revision de soldadura", "revision de sentidos de giro", "manual de funcionamiento", "revision de filos y acabados", "revision de tratamientos", "revision de tornilleria",
                    "revision de ruidos", "ensayo equipo", "observciones generales", "lider de inspeccion", "encargado ensamblador", "diseñador", "fecha de entrega"
                ]

                sheet = sheet_client.open(file_name).worksheet(worksheet_name)
                all_rows = sheet.get_all_values()
                if not all_rows:
                    sheet.append_row(headers)
                elif all_rows and all_rows[0] != headers:
                    sheet.resize(rows=1)
                    sheet.update('A1', [headers])

                # Actualizar fila existente por OP o agregar
                try:
                    headers_lower = [h.strip().lower() for h in sheet.row_values(1)]
                    op_col = headers_lower.index("op") + 1 if "op" in headers_lower else None
                except Exception:
                    op_col = None
                target_row = None
                if op_col:
                    col_values = sheet.col_values(op_col)
                    for idx, v in enumerate(col_values[1:], start=2):
                        if str(v).strip() == str(op).strip() and str(op).strip():
                            target_row = idx
                            break
                if target_row is None:
                    sheet.append_row(row)
                else:
                    sheet.resize(cols=len(headers))
                    sheet.update(f'A{target_row}', [row])
    st.success("Acta de entrega guardada correctamente en Google Sheets.")

        # Verificar estado de acta de entrega para la OP (solo completa si hay datos relevantes)
    acta_status = "pendiente"
    # Recuperar valores de los campos desde st.session_state
    cantidad_motores = st.session_state.get("cantidad_motores", 0)
    voltaje_motores = st.session_state.get("voltaje_motores", "")
    fotos_motores = st.session_state.get("fotos_motores", [])
    cantidad_reductores = st.session_state.get("cantidad_reductores", 0)
    voltaje_reductores = st.session_state.get("voltaje_reductores", "")
    fotos_reductores = st.session_state.get("fotos_reductores", [])
    cantidad_bombas = st.session_state.get("cantidad_bombas", 0)
    voltaje_bombas = st.session_state.get("voltaje_bombas", "")
    fotos_bombas = st.session_state.get("fotos_bombas", [])
    voltaje_turbina = st.session_state.get("voltaje_turbina", "")
    foto_turbina = st.session_state.get("foto_turbina", [])
    voltaje_quemador = st.session_state.get("voltaje_quemador", "")
    foto_quemador = st.session_state.get("foto_quemador", [])
    voltaje_bomba_vacio = st.session_state.get("voltaje_bomba_vacio", "")
    foto_bomba_vacio = st.session_state.get("foto_bomba_vacio", [])
    voltaje_compresor = st.session_state.get("voltaje_compresor", "")
    foto_compresor = st.session_state.get("foto_compresor", [])
    cantidad_manometros = st.session_state.get("cantidad_manometros", 0)
    foto_manometros = st.session_state.get("foto_manometros", [])
    cantidad_vacuometros = st.session_state.get("cantidad_vacuometros", 0)
    foto_vacuometros = st.session_state.get("foto_vacuometros", [])
    cantidad_valvulas = st.session_state.get("cantidad_valvulas", 0)
    foto_valvulas = st.session_state.get("foto_valvulas", [])
    cantidad_mangueras = st.session_state.get("cantidad_mangueras", 0)
    foto_mangueras = st.session_state.get("foto_mangueras", [])
    cantidad_boquillas = st.session_state.get("cantidad_boquillas", 0)
    foto_boquillas = st.session_state.get("foto_boquillas", [])
    cantidad_reguladores = st.session_state.get("cantidad_reguladores", 0)
    foto_reguladores = st.session_state.get("foto_reguladores", [])
    tension_pinon1 = st.session_state.get("tension_pinon1", "")
    foto_pinon1 = st.session_state.get("foto_pinon1", [])
    tension_pinon2 = st.session_state.get("tension_pinon2", "")
    foto_pinon2 = st.session_state.get("foto_pinon2", [])
    tension_polea1 = st.session_state.get("tension_polea1", "")
    foto_polea1 = st.session_state.get("foto_polea1", [])
    tension_polea2 = st.session_state.get("tension_polea2", "")
    foto_polea2 = st.session_state.get("foto_polea2", [])
    cantidad_gabinete = st.session_state.get("cantidad_gabinete", 0)
    foto_gabinete = st.session_state.get("foto_gabinete", [])
    cantidad_arrancadores = st.session_state.get("cantidad_arrancadores", 0)
    foto_arrancadores = st.session_state.get("foto_arrancadores", [])
    cantidad_control_nivel = st.session_state.get("cantidad_control_nivel", 0)
    foto_control_nivel = st.session_state.get("foto_control_nivel", [])
    cantidad_variadores = st.session_state.get("cantidad_variador", 0)
    foto_variadores = st.session_state.get("foto_variador", [])
    cantidad_sensores = st.session_state.get("cantidad_sensor_temp", 0)
    foto_sensores = st.session_state.get("foto_sensor_temp", [])
    cantidad_toma_corriente = st.session_state.get("cantidad_toma_corriente", 0)
    foto_toma_corrientes = st.session_state.get("foto_toma_corriente", [])
    otros_elementos = st.session_state.get("otros_elementos", "")
    fotos_otros_elementos = st.session_state.get("fotos_otros_elementos", [])
    revision_soldadura = st.session_state.get("revision_soldadura", "")
    revision_sentidos = st.session_state.get("revision_sentidos", "")
    manual_funcionamiento = st.session_state.get("manual_funcionamiento", "")
    revision_filos = st.session_state.get("revision_filos", "")
    revision_tratamientos = st.session_state.get("revision_tratamientos", "")
    revision_tornilleria = st.session_state.get("revision_tornilleria", "")
    revision_ruidos = st.session_state.get("revision_ruidos", "")
    ensayo_equipo = st.session_state.get("ensayo_equipo", "")
    observaciones_generales = st.session_state.get("observaciones_generales", "")
    lider_inspeccion = st.session_state.get("lider_inspeccion", "")
    disenador = st.session_state.get("disenador", "")
    encargado_logistica = st.session_state.get("encargado_logistica", "")
    cedula_logistica = st.session_state.get("cedula_logistica", "")
    fecha_entrega = st.session_state.get("fecha_entrega_acta", datetime.date.today())
    row = [
        str(cliente), str(op), str(item), str(equipo), str(cantidad), str(fecha),
        str(lider_inspeccion), str(disenador), str(encargado_logistica), str(cedula_logistica), str(fecha_entrega)
    ]
    headers = [
        "cliente", "op", "item", "equipo", "cantidad", "fecha", "cantidad motores", "voltaje motores", "fotos motores",
        "cantidad reductores", "voltaje reductores", "fotos reductores", "cantidad bombas", "voltaje bombas", "fotos bombas",
        "voltaje turbina", "foto turbina", "voltaje quemador", "foto quemador", "voltaje bomba de vacio", "foto bomba de vacio",
        "voltaje compresor", "foto compresor", "cantidad manometros", "foto manometros", "cantidad vacuometros", "foto vacuometros",
        "cantidad valvulas", "foto valvulas", "cantidad mangueras", "foto mangueras", "cantidad boquillas", "foto boquillas",
        "cantidad reguladores aire/gas", "foto reguladores", "tension piñon 1", "foto piñon 1", "tension piñon 2", "foto piñon 2",
        "tension polea 1", "foto polea 1", "tension polea 2", "foto polea 2", "cantidad gabinete electrico", "foto gabinete",
        "cantidad arrancadores", "foto arrancadores", "cantidad control de nivel", "foto control de nivel", "cantidad variadores de velociad", "foto variadores de velocidad",
        "cantidad sensores de temperatura", "foto sensores de temperatura", "cantidad toma corriente", "foto toma corrientes", "otros elementos", "fotos otros elementos",
        "revision de soldadura", "revision de sentidos de giro", "manual de funcionamiento", "revision de filos y acabados", "revision de tratamientos", "revision de tornilleria",
        "revision de ruidos", "ensayo equipo", "observciones generales", "lider de inspeccion", "diseñador", "encargado logistica", "cedula logistica", "fecha de entrega"
    ]
    sheet = sheet_client.open(file_name).worksheet(worksheet_name)
    if not sheet.get_all_values():
        sheet.append_row(headers)
    sheet.append_row(row)
    st.success("Acta de entrega guardada correctamente en Google Sheets.")

if __name__ == "__main__":
    main()
