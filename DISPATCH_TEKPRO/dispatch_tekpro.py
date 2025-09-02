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
    # ...existing code...


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
        ["Acta de entrega", "Lista de empaque"],
        horizontal=True,
        key="menu_opcion_radio"
    )

    if menu_opcion == "Acta de entrega":
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        folder_id = st.secrets.drive_config.FOLDER_ID
    file_name = "dispatch_tekpro"
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
            # Mapear todos los campos relevantes
            def get_val(col):
                idx = headers_lower.index(col) if col in headers_lower else None
                return r[idx] if idx is not None and len(r) > idx else ""

            auto_cliente = get_val("cliente")
            auto_equipo = get_val("equipo")
            auto_item = get_val("item")
            auto_cantidad = get_val("cantidad")
            auto_fecha = datetime.date.today()
            fecha_val = get_val("fecha")
            if fecha_val:
                try:
                    auto_fecha = datetime.datetime.strptime(fecha_val, "%Y-%m-%d").date()
                except Exception:
                    try:
                        auto_fecha = datetime.datetime.strptime(fecha_val, "%d/%m/%Y").date()
                    except Exception:
                        auto_fecha = datetime.date.today()

            # Rellenar campos editables si existen en la fila
            st.session_state["cantidad_motores"] = get_val("cantidad motores")
            st.session_state["voltaje_motores"] = get_val("voltaje motores")
            st.session_state["cantidad_reductores"] = get_val("cantidad reductores")
            st.session_state["voltaje_reductores"] = get_val("voltaje reductores")
            st.session_state["cantidad_bombas"] = get_val("cantidad bombas")
            st.session_state["voltaje_bombas"] = get_val("voltaje bombas")
            st.session_state["voltaje_turbina"] = get_val("voltaje turbina")
            st.session_state["tipo_combustible_turbina"] = get_val("tipo combustible turbina")
            st.session_state["metodo_uso_turbina"] = get_val("metodo uso turbina")
            st.session_state["voltaje_quemador"] = get_val("voltaje quemador")
            st.session_state["voltaje_bomba_vacio"] = get_val("voltaje bomba de vacio")
            st.session_state["voltaje_compresor"] = get_val("voltaje compresor")
            st.session_state["cantidad_manometros"] = get_val("cantidad manometros")
            st.session_state["cantidad_vacuometros"] = get_val("cantidad vacuometros")
            st.session_state["cantidad_valvulas"] = get_val("cantidad valvulas")
            st.session_state["cantidad_mangueras"] = get_val("cantidad mangueras")
            st.session_state["cantidad_boquillas"] = get_val("cantidad boquillas")
            st.session_state["cantidad_reguladores"] = get_val("cantidad reguladores aire/gas")
            st.session_state["tension_pinon1"] = get_val("tension piñon 1")
            st.session_state["tension_pinon2"] = get_val("tension piñon 2")
            st.session_state["tension_polea1"] = get_val("tension polea 1")
            st.session_state["tension_polea2"] = get_val("tension polea 2")
            st.session_state["cantidad_gabinete"] = get_val("cantidad gabinete electrico")
            st.session_state["cantidad_arrancadores"] = get_val("cantidad arrancadores")
            st.session_state["cantidad_control_nivel"] = get_val("cantidad control de nivel")
            st.session_state["cantidad_variadores"] = get_val("cantidad variadores de velociad")
            st.session_state["cantidad_sensores"] = get_val("cantidad sensores de temperatura")
            st.session_state["cantidad_toma_corriente"] = get_val("cantidad toma corriente")

        # Rellenar automáticamente los campos al seleccionar una OP
        cliente = st.text_input("cliente", value=auto_cliente, key="cliente_input")
        op = op_selected
        item = st.text_input("item", value=auto_item, key="item_input")
        equipo = st.text_input("equipo", value=auto_equipo, key="equipo_input")
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
                    st.number_input("Cantidad motores", min_value=0, step=1, format="%d", key="cantidad_motores")
                    st.text_input("Voltaje motores", key="voltaje_motores")
                    st.file_uploader("Foto motores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_motores")
            if reductor_checked:
                with st.expander("Reductores", expanded=True):
                    st.markdown("<b>Reductores</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad reductores", min_value=0, step=1, format="%d", key="cantidad_reductores")
                    st.text_input("Voltaje reductores", key="voltaje_reductores")
                    st.file_uploader("Foto reductores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_reductores")
            if bomba_checked:
                with st.expander("Bombas", expanded=True):
                    st.markdown("<b>Bombas</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad bombas", min_value=0, step=1, format="%d", key="cantidad_bombas")
                    st.text_input("Voltaje bombas", key="voltaje_bombas")
                    st.file_uploader("Foto bombas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_bombas")
            if turbina_checked:
                with st.expander("Turbinas", expanded=True):
                    st.markdown("<b>Turbinas</b>", unsafe_allow_html=True)
                    st.text_input("Voltaje turbinas", key="voltaje_turbina")
                    tipo_combustible_turbina = st.selectbox("Tipo de combustible", ["", "Gas Natural", "GLP", "ACPM"], key="tipo_combustible_turbina")
                    metodo_uso_turbina = st.selectbox("Método de uso", ["", "Alto/Bajo", "On/Off"], key="metodo_uso_turbina")
                    st.file_uploader("Foto turbinas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_turbina")
            if quemador_checked:
                with st.expander("Quemadores", expanded=True):
                    st.markdown("<b>Quemadores</b>", unsafe_allow_html=True)
                    st.text_input("Voltaje quemadores", key="voltaje_quemador")
                    st.text_input("Tipo de combustible", key="tipo_combustible_quemador")
                    st.text_input("Métodos de uso", key="metodos_uso_quemador")
                    st.file_uploader("Foto quemadores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_quemador")
            if bomba_vacio_checked:
                with st.expander("Bombas de vacío", expanded=True):
                    st.markdown("<b>Bombas de vacío</b>", unsafe_allow_html=True)
                    st.text_input("Voltaje bombas de vacío", key="voltaje_bomba_vacio")
                    st.file_uploader("Foto bombas de vacío", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_bomba_vacio")
            if compresor_checked:
                with st.expander("Compresores", expanded=True):
                    st.markdown("<b>Compresores</b>", unsafe_allow_html=True)
                    st.text_input("Voltaje compresores", key="voltaje_compresor")
                    st.file_uploader("Foto compresores", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_compresor")

        # Aquí van los bloques únicos de cada lista de chequeo (ya presentes más abajo en el código)
        # ...existing code...


        # Otros elementos: checkbox, descripción y foto (al final de las listas de chequeo)
        mostrar_otros_elementos = st.checkbox("Otros elementos", key="cb_otros_elementos")
        if mostrar_otros_elementos:
            with st.expander("Otros elementos", expanded=True):
                otros_elementos = st.text_area("Descripción de otros elementos", key="otros_elementos")
                fotos_otros_elementos = st.file_uploader("Foto(s) de otros elementos", type=["jpg","jpeg","png"], accept_multiple_files=True, key="fotos_otros_elementos")
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
            if tornillos_checked:
                with st.expander("Tornillos", expanded=True):
                    st.markdown("<b>Tornillos</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad tornillos", min_value=0, step=1, format="%d", key="cantidad_tornillos")
                    st.file_uploader("Foto tornillos", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_tornillos")
            if curvas_checked:
                with st.expander("Curvas", expanded=True):
                    st.markdown("<b>Curvas</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad curvas", min_value=0, step=1, format="%d", key="cantidad_curvas")
                    st.file_uploader("Foto curvas", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_curvas")
            if cables_checked:
                with st.expander("Cables", expanded=True):
                    st.markdown("<b>Cables</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad cables", min_value=0, step=1, format="%d", key="cantidad_cables")
                    st.file_uploader("Foto cables", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_cables")
            if tuberias_checked:
                with st.expander("Tuberías", expanded=True):
                    st.markdown("<b>Tuberías</b>", unsafe_allow_html=True)
                    st.number_input("Cantidad tuberías", min_value=0, step=1, format="%d", key="cantidad_tuberias")
                    st.file_uploader("Foto tuberías", type=["jpg","jpeg","png"], accept_multiple_files=True, key="foto_tuberias")
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

    # Selectboxes de revisión general (ahora debajo de las listas de chequeo)
    st.markdown("<h4>Revisión general</h4>", unsafe_allow_html=True)
    revision_visual = st.selectbox("Revisión visual", ["", "Si", "No"], key="revision_visual")
    revision_funcional = st.selectbox("Revisión funcional", ["", "Si", "No"], key="revision_funcional")
    revision_soldadura = st.selectbox("Revisión de soldadura", ["", "Si", "No"], key="revision_soldadura")
    revision_sentidos = st.selectbox("Revisión de sentidos de giro", ["", "Si", "No"], key="revision_sentidos")
    manual_funcionamiento = st.selectbox("Manual de funcionamiento", ["", "Si", "No"], key="manual_funcionamiento")
    revision_filos = st.selectbox("Revisión de filos y acabados", ["", "Si", "No"], key="revision_filos")
    revision_tratamientos = st.selectbox("Revisión de tratamientos", ["", "Si", "No"], key="revision_tratamientos")
    revision_tornilleria = st.selectbox("Revisión de tornillería", ["", "Si", "No"], key="revision_tornilleria")
    revision_ruidos = st.selectbox("Revisión de ruidos", ["", "Si", "No"], key="revision_ruidos")
    ensayo_equipo = st.selectbox("Ensayo equipo", ["", "Si", "No"], key="ensayo_equipo")

    # Observaciones generales
    observaciones_generales = st.text_area("Observaciones generales", key="observaciones_generales")

    # Líder de inspección
    lideres = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata","Juan David Martinez"]  # Puedes personalizar esta lista
    lider_inspeccion = st.selectbox("Líder de inspección", lideres, key="lider_inspeccion")

    # Soldador
    soldador = ["", "Jaime Ramos", "Jaime Rincon", "Gabriel","Lewis"]  # Puedes personalizar esta lista
    soldador = st.selectbox("Encargado Soldador", soldador, key="soldador")

    # Diseñador
    disenadores = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata","Juan David Martinez"]  # Puedes personalizar esta lista
    disenador = st.selectbox("Diseñador", disenadores, key="disenador")

    # Fecha y hora de entrega
    fecha_entrega = st.date_input("Fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta")
    hora_entrega = st.time_input("Hora de entrega", value=datetime.datetime.now().time(), key="hora_entrega_acta")

    # Mostrar fecha y hora en formato DD-MM-AA-HH:MM:SS
    dt_entrega = datetime.datetime.combine(fecha_entrega, hora_entrega)
    fecha_hora_formateada = dt_entrega.strftime("%d-%m-%y-%H:%M:%S")
    st.info(f"Fecha y hora de entrega: {fecha_hora_formateada}")

    if menu_opcion == "Lista de empaque":
        # ...existing code para lista de empaque...
        pass  # Bloque vacío para evitar error de indentación

    # Verificar estado de acta de entrega para la OP (solo completa si hay datos relevantes)

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
    # Encabezados según lo solicitado
    headers = [
        "cliente", "Op", "item", "equipo", "cantidad", "fecha",
        "cantidad motores", "voltaje motores", "fotos motores",
        "cantidad reductores", "voltaje reductores", "fotos reductores",
        "cantidad bombas", "voltaje bombas", "fotos bombas",
        "voltaje turbina", "Tipo combustible turbina", "Metodo uso turbina", "foto turbina",
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
        "descripcion otros elementos", "fotos otros elementos",
        "descripcion tuberias", "foto tuberias",
        "descripcion cables", "foto cables",
        "descripcion curvas", "foto curvas",
        "descripcion tornilleria", "foto tornilleria",
        "revision de soldadura", "revision de sentidos de giro", "manual de funcionamiento",
        "revision de filos y acabados", "revision de tratamientos", "revision de tornilleria",
        "revision de ruidos", "ensayo equipo", "observciones generales",
        "lider de inspeccion", "Encargado soldador", "diseñador", "fecha de entrega"
    ]

    # Construir la fila de datos en el mismo orden que los encabezados
    def to_url_list(files, folder_id, prefix):
        urls = []
        if files:
            for idx, file in enumerate(files):
                if file is not None:
                    url = upload_image_to_drive_oauth(file, f"{prefix}_{idx+1}.jpg", folder_id)
                    urls.append(url)
        return ", ".join(urls)

    row = [
        str(cliente), str(op), str(item), str(equipo), str(cantidad), str(fecha),
        str(st.session_state.get("cantidad_motores", 0)),
        str(st.session_state.get("voltaje_motores", "")),
        to_url_list(st.session_state.get("fotos_motores", []), folder_id, "motores"),
        str(st.session_state.get("cantidad_reductores", 0)),
        str(st.session_state.get("voltaje_reductores", "")),
        to_url_list(st.session_state.get("fotos_reductores", []), folder_id, "reductores"),
        str(st.session_state.get("cantidad_bombas", 0)),
        str(st.session_state.get("voltaje_bombas", "")),
        to_url_list(st.session_state.get("fotos_bombas", []), folder_id, "bombas"),
        str(st.session_state.get("voltaje_turbina", "")),
        str(st.session_state.get("tipo_combustible_turbina", "")),
        str(st.session_state.get("metodo_uso_turbina", "")),
        to_url_list(st.session_state.get("foto_turbina", []), folder_id, "turbina"),
        str(st.session_state.get("voltaje_quemador", "")),
        to_url_list(st.session_state.get("foto_quemador", []), folder_id, "quemador"),
        str(st.session_state.get("voltaje_bomba_vacio", "")),
        to_url_list(st.session_state.get("foto_bomba_vacio", []), folder_id, "bomba_vacio"),
        str(st.session_state.get("voltaje_compresor", "")),
        to_url_list(st.session_state.get("foto_compresor", []), folder_id, "compresor"),
        str(st.session_state.get("cantidad_manometros", 0)),
        to_url_list(st.session_state.get("foto_manometros", []), folder_id, "manometros"),
        str(st.session_state.get("cantidad_vacuometros", 0)),
        to_url_list(st.session_state.get("foto_vacuometros", []), folder_id, "vacuometros"),
        str(st.session_state.get("cantidad_valvulas", 0)),
        to_url_list(st.session_state.get("foto_valvulas", []), folder_id, "valvulas"),
        str(st.session_state.get("cantidad_mangueras", 0)),
        to_url_list(st.session_state.get("foto_mangueras", []), folder_id, "mangueras"),
        str(st.session_state.get("cantidad_boquillas", 0)),
        to_url_list(st.session_state.get("foto_boquillas", []), folder_id, "boquillas"),
        str(st.session_state.get("cantidad_reguladores", 0)),
        to_url_list(st.session_state.get("foto_reguladores", []), folder_id, "reguladores"),
        str(st.session_state.get("tension_pinon1", "")),
        to_url_list(st.session_state.get("foto_pinon1", []), folder_id, "pinon1"),
        str(st.session_state.get("tension_pinon2", "")),
        to_url_list(st.session_state.get("foto_pinon2", []), folder_id, "pinon2"),
        str(st.session_state.get("tension_polea1", "")),
        to_url_list(st.session_state.get("foto_polea1", []), folder_id, "polea1"),
        str(st.session_state.get("tension_polea2", "")),
        to_url_list(st.session_state.get("foto_polea2", []), folder_id, "polea2"),
        str(st.session_state.get("cantidad_gabinete", 0)),
        to_url_list(st.session_state.get("foto_gabinete", []), folder_id, "gabinete"),
        str(st.session_state.get("cantidad_arrancadores", 0)),
        to_url_list(st.session_state.get("foto_arrancadores", []), folder_id, "arrancadores"),
        str(st.session_state.get("cantidad_control_nivel", 0)),
        to_url_list(st.session_state.get("foto_control_nivel", []), folder_id, "control_nivel"),
        str(st.session_state.get("cantidad_variadores", 0)),
        to_url_list(st.session_state.get("foto_variadores", []), folder_id, "variadores"),
        str(st.session_state.get("cantidad_sensores", 0)),
        to_url_list(st.session_state.get("foto_sensores", []), folder_id, "sensores"),
        str(st.session_state.get("cantidad_toma_corriente", 0)),
        to_url_list(st.session_state.get("foto_toma_corrientes", []), folder_id, "toma_corriente"),
        str(st.session_state.get("otros_elementos", "")),
        to_url_list(st.session_state.get("fotos_otros_elementos", []), folder_id, "otros_elementos"),
        str(st.session_state.get("descripcion_tuberias", "")),
        to_url_list(st.session_state.get("foto_tuberias", []), folder_id, "tuberias"),
        str(st.session_state.get("descripcion_cables", "")),
        to_url_list(st.session_state.get("foto_cables", []), folder_id, "cables"),
        str(st.session_state.get("descripcion_curvas", "")),
        to_url_list(st.session_state.get("foto_curvas", []), folder_id, "curvas"),
        str(st.session_state.get("descripcion_tornilleria", "")),
        to_url_list(st.session_state.get("foto_tornilleria", []), folder_id, "tornilleria"),
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
        str(st.session_state.get("encargado_soldador", "")),
        str(st.session_state.get("disenador", "")),
        str(st.session_state.get("fecha_hora_formateada", ""))
    ]
    # Botón para enviar el acta de entrega (al final del formulario)
    enviar_acta = st.button("Enviar Acta de Entrega", key="enviar_acta_entrega")
    # Guardar solo al presionar el botón
    if enviar_acta:
        sheet = sheet_client.open(file_name).worksheet(worksheet_name)
        if not sheet.get_all_values():
            sheet.append_row(headers)
        sheet.append_row(row)
        st.success("Acta de entrega guardada correctamente en Google Sheets.")

if __name__ == "__main__":
    main()
