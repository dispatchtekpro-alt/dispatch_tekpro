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


    # Menú de inicio
    st.markdown("""
    <div style='margin-bottom: 1em;'>
        <h1 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 700; letter-spacing: 1px;'>DISPATCH TEKPRO</h1>
        <h2 style='margin: 0; font-family: Montserrat, Arial, sans-serif; color: #1db6b6; font-weight: 600; font-size: 1.5em;'>Menú principal</h2>
    </div>
    <hr style='border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;'>
    """, unsafe_allow_html=True)

    opcion_menu = st.radio(
        "Selecciona una opción:",
        ["ACTA DE ENTREGA", "LISTA DE EMPAQUE"],
        horizontal=True
    )

    if opcion_menu == "LISTA DE EMPAQUE":
        # Configuración: carpeta y sheet
        folder_id = st.secrets.drive_config.FOLDER_ID
        file_name = st.secrets.drive_config.FILE_NAME
        worksheet_name = "Lista de empaque"

        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)

    # Leer órdenes de pedido existentes y sus datos
    sheet = sheet_client.open(file_name).worksheet(worksheet_name)
    all_rows = sheet.get_all_values()

    with st.form("acta_entrega_form"):
                col1, col2 = st.columns(2)
                with col1:
                    cliente = st.text_input("Cliente")
                    op = st.text_input("OP (Orden de pedido)")
                    item = st.text_input("Item")
                with col2:
                    equipo = st.text_input("Equipo")
                    cantidad = st.number_input("Cantidad", min_value=1, step=1)
                    import datetime
                    fecha_solicitud = st.date_input("Fecha de solicitud", value=datetime.date.today())

                # Variables condicionales para cada sección
                motores = []
                num_motores = 0
                if st.session_state.get('mostrar_motores', False):
                    num_motores = st.number_input("¿Cuántos motores?", min_value=1, max_value=4, value=1, step=1, key="num_motores")
                    for i in range(int(num_motores)):
                        st.markdown(f"**Motor {i+1}**")
                        voltaje = st.text_input(f"Voltaje Motor {i+1}", key=f"voltaje_motor_{i+1}")
                        foto = st.file_uploader(f"Foto Motor {i+1}", type=["jpg","jpeg","png"], key=f"foto_motor_{i+1}")
                        motores.append({"voltaje": voltaje, "foto": foto})
                # Reductor
                voltaje_reductor = ""
                foto_reductor = None
                if st.session_state.get('mostrar_reductor', False):
                    st.markdown("**Reductor**")
                    voltaje_reductor = st.text_input("Voltaje Reductor")
                    foto_reductor = st.file_uploader("Foto Reductor", type=["jpg","jpeg","png"], key="foto_reductor")
                # Bomba
                voltaje_bomba = ""
                foto_bomba = None
                if st.session_state.get('mostrar_bomba', False):
                    st.markdown("**Bomba**")
                    voltaje_bomba = st.text_input("Voltaje Bomba")
                    foto_bomba = st.file_uploader("Foto Bomba", type=["jpg","jpeg","png"], key="foto_bomba")
                # Turbina
                voltaje_turbina = ""
                foto_turbina = None
                if st.session_state.get('mostrar_turbina', False):
                    st.markdown("**Turbina**")
                    voltaje_turbina = st.text_input("Voltaje Turbina")
                    foto_turbina = st.file_uploader("Foto Turbina", type=["jpg","jpeg","png"], key="foto_turbina")
                # Quemador
                voltaje_quemador = ""
                foto_quemador = None
                if st.session_state.get('mostrar_quemador', False):
                    st.markdown("**Quemador**")
                    voltaje_quemador = st.text_input("Voltaje Quemador")
                    foto_quemador = st.file_uploader("Foto Quemador", type=["jpg","jpeg","png"], key="foto_quemador")
                # Bomba de vacío
                voltaje_bomba_vacio = ""
                foto_bomba_vacio = None
                if st.session_state.get('mostrar_bomba_vacio', False):
                    st.markdown("**Bomba de vacío**")
                    voltaje_bomba_vacio = st.text_input("Voltaje Bomba de vacío")
                    foto_bomba_vacio = st.file_uploader("Foto Bomba de vacío", type=["jpg","jpeg","png"], key="foto_bomba_vacio")
                # Compresor
                voltaje_compresor = ""
                foto_compresor = None
                if st.session_state.get('mostrar_compresor', False):
                    st.markdown("**Compresor**")
                    voltaje_compresor = st.text_input("Voltaje Compresor")
                    foto_compresor = st.file_uploader("Foto Compresor", type=["jpg","jpeg","png"], key="foto_compresor")
                # Manómetros
                cantidad_manometros = 0
                foto_manometros = None
                if st.session_state.get('mostrar_manometros', False):
                    cantidad_manometros = st.number_input("Cantidad de manómetros", min_value=1, step=1)
                    foto_manometros = st.file_uploader("Foto manómetros", type=["jpg","jpeg","png"], key="foto_manometros")
                # Vacuómetros
                cantidad_vacuometros = 0
                foto_vacuometros = None
                if st.session_state.get('mostrar_vacuometros', False):
                    cantidad_vacuometros = st.number_input("Cantidad de vacuómetros", min_value=1, step=1)
                    foto_vacuometros = st.file_uploader("Foto vacuómetros", type=["jpg","jpeg","png"], key="foto_vacuometros")
                # Válvulas
                cantidad_valvulas = 0
                foto_valvulas = None
                if st.session_state.get('mostrar_valvulas', False):
                    cantidad_valvulas = st.number_input("Cantidad de válvulas", min_value=1, step=1)
                    foto_valvulas = st.file_uploader("Foto válvulas", type=["jpg","jpeg","png"], key="foto_valvulas")
                # Mangueras
                cantidad_mangueras = 0
                foto_mangueras = None
                if st.session_state.get('mostrar_mangueras', False):
                    cantidad_mangueras = st.number_input("Cantidad de mangueras", min_value=1, step=1)
                    foto_mangueras = st.file_uploader("Foto mangueras", type=["jpg","jpeg","png"], key="foto_mangueras")
                # Boquillas
                cantidad_boquillas = 0
                foto_boquillas = None
                if st.session_state.get('mostrar_boquillas', False):
                    cantidad_boquillas = st.number_input("Cantidad de boquillas", min_value=1, step=1)
                    foto_boquillas = st.file_uploader("Foto boquillas", type=["jpg","jpeg","png"], key="foto_boquillas")
                # Reguladores
                cantidad_reguladores = 0
                foto_reguladores = None
                if st.session_state.get('mostrar_reguladores', False):
                    cantidad_reguladores = st.number_input("Cantidad de reguladores aire/gas", min_value=1, step=1)
                    foto_reguladores = st.file_uploader("Foto reguladores aire/gas", type=["jpg","jpeg","png"], key="foto_reguladores")
                # Piñón 1
                tension_pinon1 = ""
                foto_pinon1 = None
                if st.session_state.get('mostrar_pinon1', False):
                    tension_pinon1 = st.text_input("Tensión Piñón 1")
                    foto_pinon1 = st.file_uploader("Foto Piñón 1", type=["jpg","jpeg","png"], key="foto_pinon1")
                # Piñón 2
                tension_pinon2 = ""
                foto_pinon2 = None
                if st.session_state.get('mostrar_pinon2', False):
                    tension_pinon2 = st.text_input("Tensión Piñón 2")
                    foto_pinon2 = st.file_uploader("Foto Piñón 2", type=["jpg","jpeg","png"], key="foto_pinon2")
                # Polea 1
                tension_polea1 = ""
                foto_polea1 = None
                if st.session_state.get('mostrar_polea1', False):
                    tension_polea1 = st.text_input("Tensión Polea 1")
                    foto_polea1 = st.file_uploader("Foto Polea 1", type=["jpg","jpeg","png"], key="foto_polea1")
                # Polea 2
                tension_polea2 = ""
                foto_polea2 = None
                if st.session_state.get('mostrar_polea2', False):
                    tension_polea2 = st.text_input("Tensión Polea 2")
                    foto_polea2 = st.file_uploader("Foto Polea 2", type=["jpg","jpeg","png"], key="foto_polea2")
                # Gabinete eléctrico
                foto_gabinete = None
                if st.session_state.get('mostrar_gabinete', False):
                    foto_gabinete = st.file_uploader("Foto gabinete eléctrico", type=["jpg","jpeg","png"], key="foto_gabinete")
                # Arrancador
                foto_arrancador = None
                if st.session_state.get('mostrar_arrancador', False):
                    foto_arrancador = st.file_uploader("Foto arrancador", type=["jpg","jpeg","png"], key="foto_arrancador")
                # Control de nivel
                foto_control_nivel = None
                if st.session_state.get('mostrar_control_nivel', False):
                    foto_control_nivel = st.file_uploader("Foto control de nivel", type=["jpg","jpeg","png"], key="foto_control_nivel")
                # Variador de velocidad
                foto_variador = None
                if st.session_state.get('mostrar_variador', False):
                    foto_variador = st.file_uploader("Foto variador de velocidad", type=["jpg","jpeg","png"], key="foto_variador")
                # Sensor de temperatura
                foto_sensor_temp = None
                if st.session_state.get('mostrar_sensor_temp', False):
                    foto_sensor_temp = st.file_uploader("Foto sensor de temperatura", type=["jpg","jpeg","png"], key="foto_sensor_temp")
                # Toma corriente
                foto_toma_corriente = None
                if st.session_state.get('mostrar_toma_corriente', False):
                    foto_toma_corriente = st.file_uploader("Foto toma corriente", type=["jpg","jpeg","png"], key="foto_toma_corriente")

                # Otros elementos
                st.markdown("<hr>", unsafe_allow_html=True)
                st.subheader("Otros elementos")
                otros_elementos = st.text_area("Describa otros elementos relevantes ")

                # Inspección visual
                st.markdown("<hr>", unsafe_allow_html=True)
                st.subheader("INSPECCION VISUAL")
                col1v, col2v = st.columns(2)
                with col1v:
                    soldadura = st.selectbox("Revisión de soldadura", ["Sí", "No"])
                    sentidos = st.selectbox("Revisión de sentidos de giro/entrada/salida", ["Sí", "No"])
                    manual = st.selectbox("Manual de funcionamiento", ["Sí", "No"])
                    filos = st.selectbox("Revisión de filos y acabados", ["Sí", "No"])
                with col2v:
                    tratamientos = st.selectbox("Revisión de tratamientos superficiales", ["Sí", "No"])
                    tornilleria = st.selectbox("Revisión de tornillería/tuercas de seguridad/guasas", ["Sí", "No"])
                    ruidos = st.selectbox("Revisión de ruidos y vibraciones", ["Sí", "No"])
                    ensayo = st.selectbox("Ensayo del equipo", ["Sí", "No"])

                # Observaciones generales
                st.markdown("<hr>", unsafe_allow_html=True)
                st.subheader("OBSERVACIONES GENERALES")
                observaciones_generales = st.text_area("Observaciones generales ")

                # Responsables
                st.markdown("<hr>", unsafe_allow_html=True)
                st.subheader("RESPONSABLES")
                col1r, col2r = st.columns(2)
                with col1r:
                    lider_inspeccion = st.text_input("Líder de la inspección")
                    disenador = st.text_input("Diseñador")
                with col2r:
                    recibe = st.text_input("Recibe")
                    fecha_entrega = st.date_input("Fecha de entrega", value=datetime.date.today())

                submitted = st.form_submit_button("Guardar acta de entrega")

                # Validación: solo encabezado y responsables son obligatorios
                encabezado_completo = all([
                    cliente.strip(),
                    op.strip(),
                    item.strip(),
                    equipo.strip(),
                    lider_inspeccion.strip(),
                    disenador.strip(),
                    recibe.strip()
                ])

                if submitted:
                    if not encabezado_completo:
                        st.error("Por favor complete todos los campos obligatorios del encabezado y responsables.")
                    else:
                        def subir_foto(foto, nombre, label=None):
                            if foto:
                                import io
                                file_stream = io.BytesIO(foto.read())
                                url = upload_image_to_drive_oauth(file_stream, nombre, folder_id)
                                st.success(f"{label or nombre} subida correctamente")
                                st.markdown(f"[Ver foto]({url})")
                                return url
                            return ""

                        motores_links = []
                        motores_voltajes = []
                        motores_fotos = []
                        num_motores_val = 0
                        if st.session_state.get('mostrar_motores', False):
                            num_motores_val = int(num_motores)
                            for idx, m in enumerate(motores, start=1):
                                link = subir_foto(m["foto"], f"Motor_{op}_{idx}.jpg", label=f"Foto Motor {idx}") if m["foto"] else ""
                                motores_links.append(link)
                                motores_voltajes.append(m["voltaje"])
                                motores_fotos.append(link)

                        foto_reductor_link = subir_foto(foto_reductor, f"Reductor_{op}.jpg", label="Foto Reductor") if st.session_state.get('mostrar_reductor', False) else ""
                        foto_bomba_link = subir_foto(foto_bomba, f"Bomba_{op}.jpg", label="Foto Bomba") if st.session_state.get('mostrar_bomba', False) else ""
                        foto_turbina_link = subir_foto(foto_turbina, f"Turbina_{op}.jpg", label="Foto Turbina") if st.session_state.get('mostrar_turbina', False) else ""
                        foto_quemador_link = subir_foto(foto_quemador, f"Quemador_{op}.jpg", label="Foto Quemador") if st.session_state.get('mostrar_quemador', False) else ""
                        foto_bomba_vacio_link = subir_foto(foto_bomba_vacio, f"BombaVacio_{op}.jpg", label="Foto Bomba de vacío") if st.session_state.get('mostrar_bomba_vacio', False) else ""
                        foto_compresor_link = subir_foto(foto_compresor, f"Compresor_{op}.jpg", label="Foto Compresor") if st.session_state.get('mostrar_compresor', False) else ""
                        foto_manometros_link = subir_foto(foto_manometros, f"Manometros_{op}.jpg", label="Foto manómetros") if st.session_state.get('mostrar_manometros', False) else ""
                        foto_vacuometros_link = subir_foto(foto_vacuometros, f"Vacuometros_{op}.jpg", label="Foto vacuómetros") if st.session_state.get('mostrar_vacuometros', False) else ""
                        foto_valvulas_link = subir_foto(foto_valvulas, f"Valvulas_{op}.jpg", label="Foto válvulas") if st.session_state.get('mostrar_valvulas', False) else ""
                        foto_mangueras_link = subir_foto(foto_mangueras, f"Mangueras_{op}.jpg", label="Foto mangueras") if st.session_state.get('mostrar_mangueras', False) else ""
                        foto_boquillas_link = subir_foto(foto_boquillas, f"Boquillas_{op}.jpg", label="Foto boquillas") if st.session_state.get('mostrar_boquillas', False) else ""
                        foto_reguladores_link = subir_foto(foto_reguladores, f"Reguladores_{op}.jpg", label="Foto reguladores") if st.session_state.get('mostrar_reguladores', False) else ""
                        foto_pinon1_link = subir_foto(foto_pinon1, f"Pinon1_{op}.jpg", label="Foto Piñón 1") if st.session_state.get('mostrar_pinon1', False) else ""
                        foto_pinon2_link = subir_foto(foto_pinon2, f"Pinon2_{op}.jpg", label="Foto Piñón 2") if st.session_state.get('mostrar_pinon2', False) else ""
                        foto_polea1_link = subir_foto(foto_polea1, f"Polea1_{op}.jpg", label="Foto Polea 1") if st.session_state.get('mostrar_polea1', False) else ""
                        foto_polea2_link = subir_foto(foto_polea2, f"Polea2_{op}.jpg", label="Foto Polea 2") if st.session_state.get('mostrar_polea2', False) else ""
                        foto_gabinete_link = subir_foto(foto_gabinete, f"Gabinete_{op}.jpg", label="Foto gabinete eléctrico") if st.session_state.get('mostrar_gabinete', False) else ""
                        foto_arrancador_link = subir_foto(foto_arrancador, f"Arrancador_{op}.jpg", label="Foto arrancador") if st.session_state.get('mostrar_arrancador', False) else ""
                        foto_control_nivel_link = subir_foto(foto_control_nivel, f"ControlNivel_{op}.jpg", label="Foto control de nivel") if st.session_state.get('mostrar_control_nivel', False) else ""
                        foto_variador_link = subir_foto(foto_variador, f"Variador_{op}.jpg", label="Foto variador de velocidad") if st.session_state.get('mostrar_variador', False) else ""
                        foto_sensor_temp_link = subir_foto(foto_sensor_temp, f"SensorTemp_{op}.jpg", label="Foto sensor de temperatura") if st.session_state.get('mostrar_sensor_temp', False) else ""
                        foto_toma_corriente_link = subir_foto(foto_toma_corriente, f"TomaCorriente_{op}.jpg", label="Foto toma corriente") if st.session_state.get('mostrar_toma_corriente', False) else ""

                        row = [
                            cliente, op, item, equipo, cantidad, str(fecha_solicitud),
                            num_motores_val,
                            *motores_voltajes,
                            *motores_fotos,
                            voltaje_reductor, foto_reductor_link, voltaje_bomba, foto_bomba_link,
                            voltaje_turbina, foto_turbina_link, voltaje_quemador, foto_quemador_link, voltaje_bomba_vacio, foto_bomba_vacio_link, voltaje_compresor, foto_compresor_link,
                            cantidad_manometros, foto_manometros_link, cantidad_vacuometros, foto_vacuometros_link, cantidad_valvulas, foto_valvulas_link, cantidad_mangueras, foto_mangueras_link, cantidad_boquillas, foto_boquillas_link, cantidad_reguladores, foto_reguladores_link,
                            tension_pinon1, foto_pinon1_link, tension_pinon2, foto_pinon2_link, tension_polea1, foto_polea1_link, tension_polea2, foto_polea2_link,
                            foto_gabinete_link, foto_arrancador_link, foto_control_nivel_link, foto_variador_link, foto_sensor_temp_link, foto_toma_corriente_link,
                            otros_elementos,
                            soldadura, sentidos, manual, filos, tratamientos, tornilleria, ruidos, ensayo,
                            observaciones_generales,
                            lider_inspeccion, disenador, recibe, str(fecha_entrega)
                        ]
                        headers = [
                            "Cliente", "OP (Orden de pedido)", "Item", "Equipo", "Cantidad", "Fecha de solicitud",
                            "Cantidad de motores",
                            "Voltaje Motor 1", "Voltaje Motor 2", "Voltaje Motor 3", "Voltaje Motor 4",
                            "Foto Motor 1", "Foto Motor 2", "Foto Motor 3", "Foto Motor 4",
                            "Voltaje Reductor", "Foto Reductor", "Voltaje Bomba", "Foto Bomba",
                            "Voltaje Turbina", "Foto Turbina", "Voltaje Quemador", "Foto Quemador", "Voltaje Bomba de vacío", "Foto Bomba de vacío", "Voltaje Compresor", "Foto Compresor",
                            "Cantidad manómetros", "Foto manómetros", "Cantidad vacuómetros", "Foto vacuómetros", "Cantidad válvulas", "Foto válvulas", "Cantidad mangueras", "Foto mangueras", "Cantidad boquillas", "Foto boquillas", "Cantidad reguladores", "Foto reguladores",
                            "Tensión Piñón 1", "Foto Piñón 1", "Tensión Piñón 2", "Foto Piñón 2", "Tensión Polea 1", "Foto Polea 1", "Tensión Polea 2", "Foto Polea 2",
                            "Foto gabinete eléctrico", "Foto arrancador", "Foto control de nivel", "Foto variador de velocidad", "Foto sensor de temperatura", "Foto toma corriente",
                            "Otros elementos",
                            "Revisión de soldadura", "Revisión de sentidos de giro/entrada/salida", "Manual de funcionamiento", "Revisión de filos y acabados", "Revisión de tratamientos superficiales", "Revisión de tornillería/tuercas de seguridad/guasas", "Revisión de ruidos y vibraciones", "Ensayo del equipo",
                            "Observaciones generales",
                            "Líder de la inspección", "Diseñador", "Recibe", "Fecha de entrega"
                        ]
                        sheet = sheet_client.open(file_name).worksheet(worksheet_name)
                        if not sheet.get_all_values():
                            sheet.append_row(headers)
                        sheet.append_row(row)
                        st.success("Acta de entrega guardada correctamente en Google Sheets.")

if __name__ == "__main__":
    main()
