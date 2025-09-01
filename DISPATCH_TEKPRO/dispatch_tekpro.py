import streamlit as st

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


import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
import io
import os


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
    from google_auth_oauthlib.flow import Flow
    redirect_uri = "https://dispatchtekpro.streamlit.app/"
    st.info(f"[LOG] Usando redirect_uri: {redirect_uri}")
    flow = Flow.from_client_config(
        {"web": dict(st.secrets.oauth2)},
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    import urllib.parse
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
    from google.oauth2.credentials import Credentials as UserCreds
    import json
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


    # --- Unificación de estructura de formularios para ambos menús ---
    # Menú de inicio unificado
    col1, col2 = st.columns([4,1])
    with col1:
        st.markdown("""
        <h1 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 700; letter-spacing: 1px;'>DISPATCH TEKPRO</h1>
        <h2 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 600; font-size: 1.5em;'>Menú principal</h2>
        """, unsafe_allow_html=True)
    with col2:
        st.image("https://drive.google.com/thumbnail?id=19MGYsVVEtnwv8SpdnRw4TainlJBsQLSE", width=150)
    st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;'>", unsafe_allow_html=True)

    opcion_menu = st.radio(
        "Selecciona una opción:",
        ["ACTA DE ENTREGA", "LISTA DE EMPAQUE"],
        horizontal=True
    )

    # Aquí va el resto del flujo de menú y lógica principal, asegurando que todo esté dentro de main()

def accesorios_varios_section():
    accesorios_varios_items = [
        {"key": "tuberias", "label": "Tuberías"},
        {"key": "curvas", "label": "Curvas"},
        {"key": "tornilleria", "label": "Tornillería"}
    ]
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Lista de chequeo accesorios varios")
    accesorios_varios_desc = {}
    accesorios_varios_foto = {}
    for item in accesorios_varios_items:
        key = item["key"]
        label = item["label"]
        accesorios_varios_desc[key] = st.text_area(f"Descripción {label}", key=f"desc_{key}_accesorios_varios")
        accesorios_varios_foto[key] = st.file_uploader(f"Foto {label}", type=["jpg","jpeg","png"], accept_multiple_files=True, key=f"foto_{key}_accesorios_varios")
    return accesorios_varios_desc, accesorios_varios_foto



    # Menú de inicio unificado
    col1, col2 = st.columns([4,1])
    with col1:
        st.markdown("""
        <h1 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 700; letter-spacing: 1px;'>DISPATCH TEKPRO</h1>
        <h2 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 600; font-size: 1.5em;'>Menú principal</h2>
        """, unsafe_allow_html=True)
    with col2:
        st.image("https://drive.google.com/thumbnail?id=19MGYsVVEtnwv8SpdnRw4TainlJBsQLSE", width=150)
    st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;'>", unsafe_allow_html=True)

    opcion_menu = st.radio(
        "Selecciona una opción:",
        ["ACTA DE ENTREGA", "LISTA DE EMPAQUE"],
        horizontal=True
    )



    # --- Menú: LISTA DE EMPAQUE ---
    if opcion_menu == "LISTA DE EMPAQUE":
        folder_id = st.secrets.drive_config.FOLDER_ID
        file_name = st.secrets.drive_config.FILE_NAME
        worksheet_name = "Lista de empaque"
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        # ...existing code for OPs, artículos, BDD SAG, etc...
        # (Aquí va la lógica de la lista de empaque, usando la misma estructura visual y de formulario que el acta de entrega, pero con los campos y lógica propios de la lista de empaque)
        # ...existing code...

    # --- Menú: ACTA DE ENTREGA ---
    elif opcion_menu == "ACTA DE ENTREGA":
        # ...existing code for acta de entrega, usando la misma estructura visual y de formulario...
        # ...existing code...
        with st.form("acta_entrega_form"):
            # ...existing code de campos y secciones...
            accesorios_varios_desc, accesorios_varios_foto = accesorios_varios_section()
            # ...resto del código del formulario, usando accesorios_varios_desc y accesorios_varios_foto...

    auto_cliente = globals().get('auto_cliente', '')
    op_selected = globals().get('op_selected', '')
    auto_equipo = globals().get('auto_equipo', '')
    auto_item = globals().get('auto_item', '')
    auto_cantidad = globals().get('auto_cantidad', '')
    auto_fecha = globals().get('auto_fecha', '')
    st.markdown(f'''
        <div style="background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;">
            <b style="color:#1db6b6;">Datos generales:</b><br>
            <b>Cliente:</b> {auto_cliente} &nbsp; | &nbsp;
            <b>OP:</b> {op_selected} &nbsp; | &nbsp;
            <b>Equipo:</b> {auto_equipo} &nbsp; | &nbsp;
            <b>Item:</b> {auto_item} &nbsp; | &nbsp;
            <b>Cantidad:</b> {auto_cantidad} &nbsp; | &nbsp;
            <b>Fecha:</b> {auto_fecha}
        </div>
    ''', unsafe_allow_html=True)
    creds = get_service_account_creds()
    sheet_client = gspread.authorize(creds)
    folder_id = st.secrets.drive_config.FOLDER_ID
    file_name = st.secrets.drive_config.FILE_NAME
    worksheet_name = "Acta de entrega"

    # --- Botones para mostrar/ocultar secciones de artículos (comportamiento clásico) ---
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Lista de chequeo general elementos electromecánicos")
    botones_articulos = [
            ("mostrar_motores", "¿Hay motores?"),
            ("mostrar_reductor", "¿Hay reductor?"),
            ("mostrar_bomba", "¿Hay bomba?"),
            ("mostrar_turbina", "¿Hay turbina?"),
            ("mostrar_quemador", "¿Hay quemador?"),
            ("mostrar_bomba_vacio", "¿Hay bomba de vacío?"),
            ("mostrar_compresor", "¿Hay compresor?")
        ]
    for key, label in botones_articulos:
        default_value = st.session_state.get(key, False)
        checkbox_value = st.checkbox(label, value=default_value, key=f"cb_{key}")
        if st.session_state.get(key, None) != checkbox_value:
            st.session_state[key] = checkbox_value
        # Si es quemador y está seleccionado, mostrar los campos mejorados
        if key == "mostrar_quemador" and checkbox_value:
            if 'quemador_voltaje' not in st.session_state:
                st.session_state['quemador_voltaje'] = ""
            if 'quemador_tipo_combustible' not in st.session_state:
                st.session_state['quemador_tipo_combustible'] = ""
            if 'quemador_metodos_uso' not in st.session_state:
                st.session_state['quemador_metodos_uso'] = ""
        st.session_state['quemador_voltaje'] = st.text_input("Voltaje quemador", value=st.session_state['quemador_voltaje'], key="quemador_voltaje")
        st.session_state['quemador_tipo_combustible'] = st.selectbox(
            "Tipo de combustible",
            ["", "Gas natural", "GLP", "ACPM"],
            index=["", "Gas natural", "GLP", "ACPM"].index(st.session_state['quemador_tipo_combustible']) if st.session_state['quemador_tipo_combustible'] in ["", "Gas natural", "GLP", "ACPM"] else 0,
            key="quemador_tipo_combustible"
        )
        st.session_state['quemador_metodos_uso'] = st.selectbox(
            "Métodos de uso",
            ["", "Alto", "Bajo", "On/Off"],
            index=["", "Alto", "Bajo", "On/Off"].index(st.session_state['quemador_metodos_uso']) if st.session_state['quemador_metodos_uso'] in ["", "Alto", "Bajo", "On/Off"] else 0,
            key="quemador_metodos_uso"
        )

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Lista de chequeo general accesorios")
        botones_accesorios = [
            ("mostrar_manometros", "¿Hay manómetros?"),
            ("mostrar_vacuometros", "¿Hay vacuómetros?"),
            ("mostrar_valvulas", "¿Hay válvulas?"),
            ("mostrar_mangueras", "¿Hay mangueras?"),
            ("mostrar_boquillas", "¿Hay boquillas?"),
            ("mostrar_reguladores", "¿Hay reguladores aire/gas?")
        ]
        for key, label in botones_accesorios:
            default_value = st.session_state.get(key, False)
            checkbox_value = st.checkbox(label, value=default_value, key=f"cb_{key}")
            if st.session_state.get(key, None) != checkbox_value:
                st.session_state[key] = checkbox_value

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Lista de chequeo general elementos mecánicos")
        botones_mecanicos = [
            ("mostrar_pinon1", "¿Hay piñón 1?"),
            ("mostrar_pinon2", "¿Hay piñón 2?"),
            ("mostrar_polea1", "¿Hay polea 1?"),
            ("mostrar_polea2", "¿Hay polea 2?")
        ]
        for key, label in botones_mecanicos:
            default_value = st.session_state.get(key, False)
            checkbox_value = st.checkbox(label, value=default_value, key=f"cb_{key}")
            if st.session_state.get(key, None) != checkbox_value:
                st.session_state[key] = checkbox_value

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Lista de chequeo general elementos eléctricos")
        botones_electricos = [
            ("mostrar_gabinete", "¿Hay gabinete eléctrico?"),
            ("mostrar_arrancador", "¿Hay arrancador?"),
            ("mostrar_control_nivel", "¿Hay control de nivel?"),
            ("mostrar_variador", "¿Hay variador de velocidad?"),
            ("mostrar_sensor_temp", "¿Hay sensor de temperatura?"),
            ("mostrar_toma_corriente", "¿Hay toma corriente?")
        ]
        for key, label in botones_electricos:
            default_value = st.session_state.get(key, False)
            checkbox_value = st.checkbox(label, value=default_value, key=f"cb_{key}")
            if st.session_state.get(key, None) != checkbox_value:
                st.session_state[key] = checkbox_value

        # --- Formulario principal ---

        # --- Estado de acta de entrega (completa/pendiente) ---
        import datetime
        st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales del acta de entrega</b>", unsafe_allow_html=True)
        # --- Autocompletar datos generales si la OP existe en el sheet, usando selectbox ---
        auto_cliente = ""
        auto_equipo = ""
        auto_item = ""
        auto_cantidad = ""
        auto_fecha = datetime.date.today()
        op_options = []
        op_to_row = {}
        try:
            sheet = sheet_client.open(file_name).worksheet(worksheet_name)
            all_rows = sheet.get_all_values()
            if all_rows:
                headers = [h.strip().lower() for h in all_rows[0]]
                op_idx = headers.index("op") if "op" in headers else None
                for row in all_rows[1:]:
                    if op_idx is not None and len(row) > op_idx:
                        op_val = row[op_idx].strip()
                        if op_val:
                            op_options.append(op_val)
                            op_to_row[op_val] = row
        except Exception:
            pass
        op_selected = st.selectbox("op", options=["(Nueva OP)"] + op_options)
        if op_selected != "(Nueva OP)":
            row = op_to_row.get(op_selected, [])
            try:
                headers = [h.strip().lower() for h in all_rows[0]]
                cliente_idx = headers.index("cliente") if "cliente" in headers else None
                equipo_idx = headers.index("equipo") if "equipo" in headers else None
                item_idx = headers.index("item") if "item" in headers else None
                cantidad_idx = headers.index("cantidad") if "cantidad" in headers else None
                fecha_idx = headers.index("fecha") if "fecha" in headers else None
                auto_cliente = row[cliente_idx] if cliente_idx is not None and len(row) > cliente_idx else ""
                auto_equipo = row[equipo_idx] if equipo_idx is not None and len(row) > equipo_idx else ""
                auto_item = row[item_idx] if item_idx is not None and len(row) > item_idx else ""
                auto_cantidad = row[cantidad_idx] if cantidad_idx is not None and len(row) > cantidad_idx else ""
                try:
                    auto_fecha = datetime.datetime.strptime(row[fecha_idx], "%Y-%m-%d").date() if fecha_idx is not None and len(row) > fecha_idx and row[fecha_idx] else datetime.date.today()
                except Exception:
                    auto_fecha = datetime.date.today()
            except Exception:
                pass
        else:
            op_selected = ""
        cliente = st.text_input("cliente", value=auto_cliente)
        op = op_selected
        equipo = st.text_input("equipo", value=auto_equipo)
        item = st.text_input("item", value=auto_item)
        cantidad = st.text_input("cantidad", value=auto_cantidad)
        fecha = st.date_input("fecha", value=auto_fecha, key="fecha_acta")
        st.markdown("</div>", unsafe_allow_html=True)

        # Verificar estado de acta de entrega para la OP (solo completa si hay datos relevantes)
        acta_status = "pendiente"
        if op:
            try:
                sheet = sheet_client.open(file_name).worksheet(worksheet_name)
                all_rows = sheet.get_all_values()
                op_idx = None
                if all_rows:
                    headers = all_rows[0]
                    for idx, h in enumerate(headers):
                        if h.strip().lower() == "op":
                            op_idx = idx
                            break
                    # Buscar la fila de la OP
                    if op_idx is not None:
                        for row in all_rows[1:]:
                            if len(row) > op_idx and row[op_idx].strip() == op.strip():
                                # Considerar campos relevantes para determinar si está completa
                                campos_relevantes = [
                                    "cantidad motores", "cantidad bombas", "cantidad reductores", "cantidad manometros", "cantidad valvulas", "cantidad mangueras", "cantidad boquillas", "cantidad gabinete electrico", "cantidad arrancadores", "cantidad control de nivel", "cantidad variadores de velociad", "cantidad sensores de temperatura", "cantidad toma corriente"
                                ]
                                completa = False
                                for campo in campos_relevantes:
                                    if campo in headers:
                                        idx_campo = headers.index(campo)
                                        if idx_campo < len(row):
                                            valor = row[idx_campo]
                                            if valor and str(valor).strip() not in ["", "0", "no", "No"]:
                                                completa = True
                                                break
                                if completa:
                                    acta_status = "completa"
                                break
            except Exception:
                pass
        if acta_status == "completa":
            st.markdown("""
                <div style='background:#e6f7e6;border:2px solid #1db6b6;color:#1db6b6;padding:0.8em 1.2em;border-radius:8px;font-weight:600;font-size:1.1em;margin-bottom:1em;text-align:center;'>
                ✅ Acta de entrega completa
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style='background:#fff3e6;border:2px solid #f7b267;color:#f7b267;padding:0.8em 1.2em;border-radius:8px;font-weight:600;font-size:1.1em;margin-bottom:1em;text-align:center;'>
                ⏳ Acta de entrega pendiente
                </div>
            """, unsafe_allow_html=True)

        with st.form("acta_entrega_form"):

            # --- Secciones visuales para cada artículo ---
            def seccion_articulo(nombre, mostrar, campos):
                if mostrar:
                    with st.expander(f"{nombre}", expanded=False):
                        st.markdown(f"""
                            <div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;border-top: 3px solid #1db6b6;'>
                            <b style='font-size:1.1em;color:#1db6b6'>{nombre}</b>
                        """, unsafe_allow_html=True)
                        resultados = {}
                        for campo in campos:
                            if campo['tipo'] == 'number':
                                resultados[campo['nombre']] = st.number_input(campo['label'], min_value=0, step=1, format="%d")
                            elif campo['tipo'] == 'text':
                                resultados[campo['nombre']] = st.text_input(campo['label'])
                            elif campo['tipo'] == 'text_area':
                                resultados[campo['nombre']] = st.text_area(campo['label'])
                            elif campo['tipo'] == 'file':
                                resultados[campo['nombre']] = st.file_uploader(campo['label'], type=["jpg","jpeg","png"], accept_multiple_files=True, key=f"fotos_{nombre}")
                        st.markdown("</div>", unsafe_allow_html=True)
                        return resultados
                else:
                    return {campo['nombre']: 0 if campo['tipo'] == 'number' else "" for campo in campos}

            # --- Agrupación por listas de chequeo principales ---
            # 1. Elementos electromecánicos
            with st.expander("Lista de chequeo general elementos electromecánicos", expanded=False):
                motores_campos = [
                    {'nombre': 'cantidad_motores', 'label': 'Cantidad de motores', 'tipo': 'number'},
                    {'nombre': 'voltaje_motores', 'label': 'Voltaje de motores', 'tipo': 'text'},
                    {'nombre': 'fotos_motores', 'label': 'Fotos motores', 'tipo': 'file'}
                ]
                motores = seccion_articulo("Motores", st.session_state.get('mostrar_motores', False), motores_campos)
                cantidad_motores = motores['cantidad_motores']
                voltaje_motores = motores['voltaje_motores']
                fotos_motores = motores['fotos_motores']

                reductores_campos = [
                    {'nombre': 'cantidad_reductores', 'label': 'Cantidad de reductores', 'tipo': 'number'},
                    {'nombre': 'voltaje_reductores', 'label': 'Voltaje de reductores', 'tipo': 'text'},
                    {'nombre': 'fotos_reductores', 'label': 'Fotos reductores', 'tipo': 'file'}
                ]
                reductores = seccion_articulo("Reductores", st.session_state.get('mostrar_reductor', False), reductores_campos)
                cantidad_reductores = reductores['cantidad_reductores']
                voltaje_reductores = reductores['voltaje_reductores']
                fotos_reductores = reductores['fotos_reductores']

                bombas_campos = [
                    {'nombre': 'cantidad_bombas', 'label': 'Cantidad de bombas', 'tipo': 'number'},
                    {'nombre': 'voltaje_bombas', 'label': 'Voltaje de bombas', 'tipo': 'text'},
                    {'nombre': 'fotos_bombas', 'label': 'Fotos bombas', 'tipo': 'file'}
                ]
                bombas = seccion_articulo("Bombas", st.session_state.get('mostrar_bomba', False), bombas_campos)
                cantidad_bombas = bombas['cantidad_bombas']
                voltaje_bombas = bombas['voltaje_bombas']
                fotos_bombas = bombas['fotos_bombas']

                turbina_campos = [
                    {'nombre': 'voltaje_turbina', 'label': 'Voltaje turbina', 'tipo': 'text'},
                    {'nombre': 'foto_turbina', 'label': 'Foto turbina', 'tipo': 'file'}
                ]
                turbina = seccion_articulo("Turbina", st.session_state.get('mostrar_turbina', False), turbina_campos)
                voltaje_turbina = turbina['voltaje_turbina']
                foto_turbina = turbina['foto_turbina']

                quemador_campos = [
                    {'nombre': 'voltaje_quemador', 'label': 'Voltaje quemador', 'tipo': 'text'},
                    {'nombre': 'tipo_combustible_quemador', 'label': 'Tipo de combustible', 'tipo': 'select', 'options': ["", "Gas natural", "GLP", "ACPM"]},
                    {'nombre': 'metodos_uso_quemador', 'label': 'Métodos de uso', 'tipo': 'select', 'options': ["", "Alto", "Bajo", "On/Off"]},
                    {'nombre': 'foto_quemador', 'label': 'Foto quemador', 'tipo': 'file'}
                ]
                quemador = {}
                if st.session_state.get('mostrar_quemador', False):
                    with st.expander("Quemador", expanded=False):
                        st.markdown(f"""
                            <div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;border-top: 3px solid #1db6b6;'>
                            <b style='font-size:1.1em;color:#1db6b6'>Quemador</b>
                        """, unsafe_allow_html=True)
                        quemador['voltaje_quemador'] = st.text_input('Voltaje quemador', value=st.session_state.get('quemador_voltaje', ""), key='quemador_voltaje_form')
                        quemador['tipo_combustible_quemador'] = st.selectbox('Tipo de combustible', ["", "Gas natural", "GLP", "ACPM"], key='quemador_tipo_combustible_form')
                        quemador['metodos_uso_quemador'] = st.selectbox('Métodos de uso', ["", "Alto", "Bajo", "On/Off"], key='quemador_metodos_uso_form')
                        quemador['foto_quemador'] = st.file_uploader('Foto quemador', type=["jpg","jpeg","png"], accept_multiple_files=True, key='fotos_Quemador')
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    quemador = {'voltaje_quemador': '', 'tipo_combustible_quemador': '', 'metodos_uso_quemador': '', 'foto_quemador': ''}
                voltaje_quemador = quemador['voltaje_quemador']
                tipo_combustible_quemador = quemador['tipo_combustible_quemador']
                metodos_uso_quemador = quemador['metodos_uso_quemador']
                foto_quemador = quemador['foto_quemador']

                bomba_vacio_campos = [
                    {'nombre': 'voltaje_bomba_vacio', 'label': 'Voltaje bomba de vacío', 'tipo': 'text'},
                    {'nombre': 'foto_bomba_vacio', 'label': 'Foto bomba de vacío', 'tipo': 'file'}
                ]
                bomba_vacio = seccion_articulo("Bomba de vacío", st.session_state.get('mostrar_bomba_vacio', False), bomba_vacio_campos)
                voltaje_bomba_vacio = bomba_vacio['voltaje_bomba_vacio']
                foto_bomba_vacio = bomba_vacio['foto_bomba_vacio']

                compresor_campos = [
                    {'nombre': 'voltaje_compresor', 'label': 'Voltaje compresor', 'tipo': 'text'},
                    {'nombre': 'foto_compresor', 'label': 'Foto compresor', 'tipo': 'file'}
                ]
                compresor = seccion_articulo("Compresor", st.session_state.get('mostrar_compresor', False), compresor_campos)
                voltaje_compresor = compresor['voltaje_compresor']
                foto_compresor = compresor['foto_compresor']

            # 2. Accesorios
            with st.expander("Lista de chequeo general accesorios", expanded=False):
                manometros_campos = [
                    {'nombre': 'cantidad_manometros', 'label': 'Cantidad manómetros', 'tipo': 'number'},
                    {'nombre': 'foto_manometros', 'label': 'Foto manómetros', 'tipo': 'file'}
                ]
                manometros = seccion_articulo("Manómetros", st.session_state.get('mostrar_manometros', False), manometros_campos)
                cantidad_manometros = manometros['cantidad_manometros']
                foto_manometros = manometros['foto_manometros']

                vacuometros_campos = [
                    {'nombre': 'cantidad_vacuometros', 'label': 'Cantidad vacuómetros', 'tipo': 'number'},
                    {'nombre': 'foto_vacuometros', 'label': 'Foto vacuómetros', 'tipo': 'file'}
                ]
                vacuometros = seccion_articulo("Vacuómetros", st.session_state.get('mostrar_vacuometros', False), vacuometros_campos)
                cantidad_vacuometros = vacuometros['cantidad_vacuometros']
                foto_vacuometros = vacuometros['foto_vacuometros']

                valvulas_campos = [
                    {'nombre': 'cantidad_valvulas', 'label': 'Cantidad válvulas', 'tipo': 'number'},
                    {'nombre': 'foto_valvulas', 'label': 'Foto válvulas', 'tipo': 'file'}
                ]
                valvulas = seccion_articulo("Válvulas", st.session_state.get('mostrar_valvulas', False), valvulas_campos)
                cantidad_valvulas = valvulas['cantidad_valvulas']
                foto_valvulas = valvulas['foto_valvulas']

                mangueras_campos = [
                    {'nombre': 'cantidad_mangueras', 'label': 'Cantidad mangueras', 'tipo': 'number'},
                    {'nombre': 'foto_mangueras', 'label': 'Foto mangueras', 'tipo': 'file'}
                ]
                mangueras = seccion_articulo("Mangueras", st.session_state.get('mostrar_mangueras', False), mangueras_campos)
                cantidad_mangueras = mangueras['cantidad_mangueras']
                foto_mangueras = mangueras['foto_mangueras']

                boquillas_campos = [
                    {'nombre': 'cantidad_boquillas', 'label': 'Cantidad boquillas', 'tipo': 'number'},
                    {'nombre': 'foto_boquillas', 'label': 'Foto boquillas', 'tipo': 'file'}
                ]
                boquillas = seccion_articulo("Boquillas", st.session_state.get('mostrar_boquillas', False), boquillas_campos)
                cantidad_boquillas = boquillas['cantidad_boquillas']
                foto_boquillas = boquillas['foto_boquillas']

                reguladores_campos = [
                    {'nombre': 'cantidad_reguladores', 'label': 'Cantidad reguladores aire/gas', 'tipo': 'number'},
                    {'nombre': 'foto_reguladores', 'label': 'Foto reguladores', 'tipo': 'file'}
                ]
                reguladores = seccion_articulo("Reguladores aire/gas", st.session_state.get('mostrar_reguladores', False), reguladores_campos)
                cantidad_reguladores = reguladores['cantidad_reguladores']
                foto_reguladores = reguladores['foto_reguladores']

            # 3. Elementos mecánicos
            with st.expander("Lista de chequeo general elementos mecánicos", expanded=False):
                pinon1_campos = [
                    {'nombre': 'tension_pinon1', 'label': 'Tensión piñón 1', 'tipo': 'text'},
                    {'nombre': 'foto_pinon1', 'label': 'Foto piñón 1', 'tipo': 'file'}
                ]
                pinon1 = seccion_articulo("Piñón 1", st.session_state.get('mostrar_pinon1', False), pinon1_campos)
                tension_pinon1 = pinon1['tension_pinon1']
                foto_pinon1 = pinon1['foto_pinon1']

                pinon2_campos = [
                    {'nombre': 'tension_pinon2', 'label': 'Tensión piñón 2', 'tipo': 'text'},
                    {'nombre': 'foto_pinon2', 'label': 'Foto piñón 2', 'tipo': 'file'}
                ]
                pinon2 = seccion_articulo("Piñón 2", st.session_state.get('mostrar_pinon2', False), pinon2_campos)
                tension_pinon2 = pinon2['tension_pinon2']
                foto_pinon2 = pinon2['foto_pinon2']

                polea1_campos = [
                    {'nombre': 'tension_polea1', 'label': 'Tensión polea 1', 'tipo': 'text'},
                    {'nombre': 'foto_polea1', 'label': 'Foto polea 1', 'tipo': 'file'}
                ]
                polea1 = seccion_articulo("Polea 1", st.session_state.get('mostrar_polea1', False), polea1_campos)
                tension_polea1 = polea1['tension_polea1']
                foto_polea1 = polea1['foto_polea1']

                polea2_campos = [
                    {'nombre': 'tension_polea2', 'label': 'Tensión polea 2', 'tipo': 'text'},
                    {'nombre': 'foto_polea2', 'label': 'Foto polea 2', 'tipo': 'file'}
                ]
                polea2 = seccion_articulo("Polea 2", st.session_state.get('mostrar_polea2', False), polea2_campos)
                tension_polea2 = polea2['tension_polea2']
                foto_polea2 = polea2['foto_polea2']

            # 4. Elementos eléctricos
            with st.expander("Lista de chequeo general elementos eléctricos", expanded=False):
                gabinete_campos = [
                    {'nombre': 'cantidad_gabinete', 'label': 'Cantidad gabinete eléctrico', 'tipo': 'number'},
                    {'nombre': 'foto_gabinete', 'label': 'Foto gabinete', 'tipo': 'file'}
                ]
                gabinete = seccion_articulo("Gabinete eléctrico", st.session_state.get('mostrar_gabinete', False), gabinete_campos)
                cantidad_gabinete = gabinete['cantidad_gabinete']
                foto_gabinete = gabinete['foto_gabinete']

                arrancadores_campos = [
                    {'nombre': 'cantidad_arrancadores', 'label': 'Cantidad arrancadores', 'tipo': 'number'},
                    {'nombre': 'foto_arrancadores', 'label': 'Foto arrancadores', 'tipo': 'file'}
                ]
                arrancadores = seccion_articulo("Arrancadores", st.session_state.get('mostrar_arrancador', False), arrancadores_campos)
                cantidad_arrancadores = arrancadores['cantidad_arrancadores']
                foto_arrancadores = arrancadores['foto_arrancadores']

                control_nivel_campos = [
                    {'nombre': 'cantidad_control_nivel', 'label': 'Cantidad control de nivel', 'tipo': 'number'},
                    {'nombre': 'foto_control_nivel', 'label': 'Foto control de nivel', 'tipo': 'file'}
                ]
                control_nivel = seccion_articulo("Control de nivel", st.session_state.get('mostrar_control_nivel', False), control_nivel_campos)
                cantidad_control_nivel = control_nivel['cantidad_control_nivel']
                foto_control_nivel = control_nivel['foto_control_nivel']

                variadores_campos = [
                    {'nombre': 'cantidad_variadores', 'label': 'Cantidad variadores de velocidad', 'tipo': 'number'},
                    {'nombre': 'foto_variadores', 'label': 'Foto variadores de velocidad', 'tipo': 'file'}
                ]
                variadores = seccion_articulo("Variadores de velocidad", st.session_state.get('mostrar_variador', False), variadores_campos)
                cantidad_variadores = variadores['cantidad_variadores']
                foto_variadores = variadores['foto_variadores']

                sensores_campos = [
                    {'nombre': 'cantidad_sensores', 'label': 'Cantidad sensores de temperatura', 'tipo': 'number'},
                    {'nombre': 'foto_sensores', 'label': 'Foto sensores de temperatura', 'tipo': 'file'}
                ]
                sensores = seccion_articulo("Sensores de temperatura", st.session_state.get('mostrar_sensor_temp', False), sensores_campos)
                cantidad_sensores = sensores['cantidad_sensores']
                foto_sensores = sensores['foto_sensores']

                toma_corriente_campos = [
                    {'nombre': 'cantidad_toma_corriente', 'label': 'Cantidad toma corriente', 'tipo': 'number'},
                    {'nombre': 'foto_toma_corrientes', 'label': 'Foto toma corrientes', 'tipo': 'file'}
                ]
                toma_corriente = seccion_articulo("Toma corriente", st.session_state.get('mostrar_toma_corriente', False), toma_corriente_campos)
                cantidad_toma_corriente = toma_corriente['cantidad_toma_corriente']
                foto_toma_corrientes = toma_corriente['foto_toma_corrientes']
            col_otros1, col_otros2 = st.columns([2,2])
            with col_otros1:
                otros_elementos = st.text_area("otros elementos")
            with col_otros2:
                fotos_otros_elementos = st.file_uploader("Fotos otros elementos", type=["jpg","jpeg","png"], accept_multiple_files=True, key="fotos_otros_elementos")
            st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin: 1.5em 0;'>", unsafe_allow_html=True)
            st.markdown("<b>Preguntas de revisión (Sí/No)</b>", unsafe_allow_html=True)
            revision_soldadura = st.selectbox("revision de soldadura", ["", "Sí", "No"])
            revision_sentidos = st.selectbox("revision de sentidos de giro", ["", "Sí", "No"])
            manual_funcionamiento = st.selectbox("manual de funcionamiento", ["", "Sí", "No"])
            revision_filos = st.selectbox("revision de filos y acabados", ["", "Sí", "No"])
            revision_tratamientos = st.selectbox("revision de tratamientos", ["", "Sí", "No"])
            revision_tornilleria = st.selectbox("revision de tornilleria", ["", "Sí", "No"])
            revision_ruidos = st.selectbox("revision de ruidos", ["", "Sí", "No"])
            ensayo_equipo = st.selectbox("ensayo equipo", ["", "Sí", "No"])
            st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin: 1.5em 0;'>", unsafe_allow_html=True)
            st.markdown("<b>Información final</b>", unsafe_allow_html=True)
            observaciones_generales = st.text_area("observciones generales")

            lider_inspeccion = st.text_input("lider de inspeccion")
            encargado_ensamblador = st.text_input("encargado ensamblador")
            disenador = st.selectbox(
                "diseñador",
                ["", "Daniel Valbuena", "Juan David Martinez", "Juan Andres Zapata", "Alejandro Diaz"]
            )
            fecha_entrega = st.date_input("fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta")

            submitted = st.form_submit_button("Guardar acta de entrega")

            # Validación: solo encabezado y responsables son obligatorios

            if submitted:
                # Serializar todos los campos a string y manejar file_uploader
                def serializa_fotos(valor, nombre_base, folder_id):
                    enlaces = []
                    if isinstance(valor, list):
                        for idx, f in enumerate(valor, start=1):
                            try:
                                import io
                                file_stream = io.BytesIO(f.read())
                                image_filename = f"{nombre_base}_{idx}.jpg"
                                public_url = upload_image_to_drive_oauth(file_stream, image_filename, folder_id)
                                enlaces.append(public_url)
                            except Exception as e:
                                enlaces.append(f"Error: {e}")
                        return ", ".join(enlaces) if enlaces else ""
                    elif hasattr(valor, 'name'):
                        try:
                            import io
                            file_stream = io.BytesIO(valor.read())
                            image_filename = f"{nombre_base}.jpg"
                            public_url = upload_image_to_drive_oauth(file_stream, image_filename, folder_id)
                            return public_url
                        except Exception as e:
                            return f"Error: {e}"
                    else:
                        return str(valor) if valor is not None else ""

                accesorios_varios_desc, accesorios_varios_foto = accesorios_varios_section()

                row = [
                    str(cliente), str(op), str(item), str(equipo), str(cantidad), str(fecha), str(encargado_ensamblador),
                    str(cantidad_motores), str(voltaje_motores), serializa_fotos(fotos_motores, f"Motores_{op}", folder_id),
                    str(cantidad_reductores), str(voltaje_reductores), serializa_fotos(fotos_reductores, f"Reductores_{op}", folder_id),
                    str(cantidad_bombas), str(voltaje_bombas), serializa_fotos(fotos_bombas, f"Bombas_{op}", folder_id),
                    str(voltaje_turbina), serializa_fotos(foto_turbina, f"Turbina_{op}", folder_id),
                    str(voltaje_quemador), serializa_fotos(foto_quemador, f"Quemador_{op}", folder_id),
                    str(voltaje_bomba_vacio), serializa_fotos(foto_bomba_vacio, f"BombaVacio_{op}", folder_id),
                    str(voltaje_compresor), serializa_fotos(foto_compresor, f"Compresor_{op}", folder_id),
                    str(cantidad_manometros), serializa_fotos(foto_manometros, f"Manometros_{op}", folder_id),
                    str(cantidad_vacuometros), serializa_fotos(foto_vacuometros, f"Vacuometros_{op}", folder_id),
                    str(cantidad_valvulas), serializa_fotos(foto_valvulas, f"Valvulas_{op}", folder_id),
                    str(cantidad_mangueras), serializa_fotos(foto_mangueras, f"Mangueras_{op}", folder_id),
                    str(cantidad_boquillas), serializa_fotos(foto_boquillas, f"Boquillas_{op}", folder_id),
                    str(cantidad_reguladores), serializa_fotos(foto_reguladores, f"Reguladores_{op}", folder_id),
                    str(tension_pinon1), serializa_fotos(foto_pinon1, f"Pinon1_{op}", folder_id),
                    str(tension_pinon2), serializa_fotos(foto_pinon2, f"Pinon2_{op}", folder_id),
                    str(tension_polea1), serializa_fotos(foto_polea1, f"Polea1_{op}", folder_id),
                    str(tension_polea2), serializa_fotos(foto_polea2, f"Polea2_{op}", folder_id),
                    str(cantidad_gabinete), serializa_fotos(foto_gabinete, f"Gabinete_{op}", folder_id),
                    str(cantidad_arrancadores), serializa_fotos(foto_arrancadores, f"Arrancadores_{op}", folder_id),
                    str(cantidad_control_nivel), serializa_fotos(foto_control_nivel, f"ControlNivel_{op}", folder_id),
                    str(cantidad_variadores), serializa_fotos(foto_variadores, f"Variadores_{op}", folder_id),
                    str(cantidad_sensores), serializa_fotos(foto_sensores, f"Sensores_{op}", folder_id),
                    str(cantidad_toma_corriente), serializa_fotos(foto_toma_corrientes, f"TomaCorriente_{op}", folder_id),
                    str(otros_elementos), serializa_fotos(fotos_otros_elementos, f"OtrosElementos_{op}", folder_id),
                    # Accesorios varios
                    str(accesorios_varios_desc["tuberias"]), serializa_fotos(accesorios_varios_foto["tuberias"], f"Tuberias_{op}", folder_id),
                    str(accesorios_varios_desc["curvas"]), serializa_fotos(accesorios_varios_foto["curvas"], f"Curvas_{op}", folder_id),
                    str(accesorios_varios_desc["tornilleria"]), serializa_fotos(accesorios_varios_foto["tornilleria"], f"Tornilleria_{op}", folder_id),
                    str(revision_soldadura), str(revision_sentidos), str(manual_funcionamiento), str(revision_filos), str(revision_tratamientos), str(revision_tornilleria),
                    str(revision_ruidos), str(ensayo_equipo), str(observaciones_generales), str(lider_inspeccion), str(encargado_ensamblador), str(disenador), str(fecha_entrega)
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
                    # Accesorios varios
                    "descripcion tuberias", "foto tuberias", "descripcion curvas", "foto curvas", "descripcion tornilleria", "foto tornilleria",
                    "revision de soldadura", "revision de sentidos de giro", "manual de funcionamiento", "revision de filos y acabados", "revision de tratamientos", "revision de tornilleria",
                    "revision de ruidos", "ensayo equipo", "observciones generales", "lider de inspeccion", "diseñador", "fecha de entrega"
                ]
                sheet = sheet_client.open(file_name).worksheet(worksheet_name)
                if not sheet.get_all_values():
                    sheet.append_row(headers)
                sheet.append_row(row)
                st.success("Acta de entrega guardada correctamente en Google Sheets.")

if __name__ == "__main__":
    main()
