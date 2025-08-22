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

        # Leer órdenes de pedido existentes desde ACTA DE ENTREGA
        try:
            acta_sheet = sheet_client.open(file_name).worksheet("Acta de entrega")
            acta_rows = acta_sheet.get_all_values()
            op_idx = None
            if acta_rows:
                headers = acta_rows[0]
                if "OP (Orden de pedido)" in headers:
                    op_idx = headers.index("OP (Orden de pedido)")
            ordenes_existentes = {}
            for row in acta_rows[1:]:
                if op_idx is not None and len(row) > op_idx:
                    orden = row[op_idx]
                    ordenes_existentes[orden] = row
            ordenes_list = list(ordenes_existentes.keys())
        except Exception:
            ordenes_existentes = {}
            ordenes_list = []

        if 'drive_oauth_token' not in st.session_state:
            authorize_drive_oauth()

        st.markdown("<b>Orden de pedido</b> (elige una existente o agrega una nueva)", unsafe_allow_html=True)
        orden_pedido_val = st.selectbox(
            "Selecciona una orden de pedido existente:",
            ordenes_list if ordenes_list else ["No hay órdenes registradas"],
            key="orden_pedido_selectbox"
        )
        if 'mostrar_nueva_op' not in st.session_state:
            st.session_state['mostrar_nueva_op'] = False
        if st.button("Agregar nueva OP"):
            st.session_state['mostrar_nueva_op'] = True
        nueva_op = ""
        if st.session_state['mostrar_nueva_op']:
            nueva_op = st.text_input("Escribe la nueva orden de pedido:", key="orden_pedido_nueva")
            if nueva_op:
                orden_pedido_val = nueva_op

        # Obtener solo los artículos presentes (sin cantidades/voltajes)
        articulos_presentes = []
        if orden_pedido_val and orden_pedido_val in ordenes_existentes:
            row = ordenes_existentes[orden_pedido_val]
            headers = acta_rows[0]
            posibles_articulos = [
                "Motor", "Reductor", "Bomba", "Turbina", "Quemador", "Bomba de vacío", "Compresor",
                "Manómetros", "Vacuómetros", "Válvulas", "Mangueras", "Boquillas", "Reguladores",
                "Piñón 1", "Piñón 2", "Polea 1", "Polea 2", "Gabinete eléctrico", "Arrancador",
                "Control de nivel", "Variador de velocidad", "Sensor de temperatura", "Toma corriente",
                "Otros elementos"
            ]
            for art in posibles_articulos:
                encontrado = False
                for idx, h in enumerate(headers):
                    if art.lower() in h.lower():
                        valor = row[idx] if idx < len(row) else ""
                        if valor and valor.strip().lower() not in ["", "0", "no"]:
                            articulos_presentes.append(art)
                            encontrado = True
                            break

        # Estado dinámico para número de paquetes
        if 'num_paquetes' not in st.session_state:
            st.session_state['num_paquetes'] = 1

        with st.form("dispatch_form"):
            import datetime
            fecha = st.date_input("Fecha del día", value=datetime.date.today())
            nombre_proyecto = st.text_input("Nombre de proyecto")
            encargado_ensamblador = st.text_input("Encargado ensamblador")
            encargado_almacen = st.text_input("Encargado almacén")
            encargado_ingenieria = st.text_input("Encargado ingeniería y diseño")

            st.markdown("<b>Selecciona los artículos a empacar:</b>", unsafe_allow_html=True)
            articulos_seleccion = {}
            for art in articulos_presentes:
                articulos_seleccion[art] = st.checkbox(art, value=True, key=f"empacar_{art}")
                # Si es 'Otros elementos', mostrar la descripción registrada en el acta
                if art.lower() == "otros elementos":
                    desc_otros = ""
                    # Buscar columna de descripción de otros elementos
                    for idx, h in enumerate(headers):
                        if "otros elementos" in h.lower() and "descrip" in h.lower():
                            desc_otros = row[idx] if idx < len(row) else ""
                            break
                    if desc_otros:
                        st.markdown(f"<span style='color: #666; font-size: 0.95em'><b>Descripción en acta:</b> {desc_otros}</span>", unsafe_allow_html=True)

            st.markdown("<hr>")
            st.markdown("<b>Paquetes (guacales):</b>", unsafe_allow_html=True)
            paquetes = []
            for i in range(st.session_state['num_paquetes']):
                st.markdown(f"<b>Paquete {i+1}</b>", unsafe_allow_html=True)
                desc = st.text_area(f"Descripción paquete {i+1}", key=f"desc_paquete_{i+1}")
                fotos = st.file_uploader(f"Fotos paquete {i+1}", type=["jpg", "jpeg", "png"], key=f"fotos_paquete_{i+1}", accept_multiple_files=True)
                paquetes.append({"desc": desc, "fotos": fotos})
            if st.form_submit_button("Agregar otro paquete"):
                st.session_state['num_paquetes'] += 1
                st.experimental_rerun()

            observaciones = st.text_area("Observaciones adicionales")
            submitted = st.form_submit_button("Guardar despacho")

        if submitted:
            if not articulos_presentes:
                st.error("No hay artículos para empacar en esta OP.")
            else:
                enviados = [art for art, v in articulos_seleccion.items() if v]
                no_enviados = [art for art, v in articulos_seleccion.items() if not v]
                row = [
                    str(fecha),
                    nombre_proyecto,
                    orden_pedido_val,
                    encargado_ensamblador,
                    encargado_almacen,
                    encargado_ingenieria,
                    ", ".join(enviados),
                    ", ".join(no_enviados)
                ]
                for idx, paquete in enumerate(paquetes, start=1):
                    row.append(paquete["desc"])
                    enlaces = []
                    if paquete["fotos"]:
                        for n, foto in enumerate(paquete["fotos"], start=1):
                            try:
                                image_filename = f"Paquete_{orden_pedido_val}_{idx}_{n}.jpg"
                                file_stream = io.BytesIO(foto.read())
                                public_url = upload_image_to_drive_oauth(file_stream, image_filename, folder_id)
                                enlaces.append(public_url)
                                st.success(f"Foto {n} de paquete {idx} subida correctamente")
                            except Exception as upload_error:
                                st.error(f"Error al subir la foto {n} de paquete {idx}: {str(upload_error)}")
                        if enlaces:
                            row.append(", ".join(enlaces))
                        else:
                            row.append("Error al subir foto")
                    else:
                        row.append("Sin foto")
                write_link_to_sheet(sheet_client, file_name, worksheet_name, row)
                st.success("Despacho guardado correctamente.")
                st.info("Las fotos han sido subidas a Google Drive y el enlace está disponible en la hoja.")


    elif opcion_menu == "ACTA DE ENTREGA":
        # Autorización Google Drive OAuth2 igual que en LISTA DE EMPAQUE
        if 'drive_oauth_token' not in st.session_state:
            authorize_drive_oauth()

        st.markdown("<h3 style='color:#1db6b6;'>ACTA DE ENTREGA</h3>", unsafe_allow_html=True)
        st.markdown("<b>Encabezado del acta de entrega</b>", unsafe_allow_html=True)
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        folder_id = st.secrets.drive_config.FOLDER_ID
        file_name = st.secrets.drive_config.FILE_NAME
        worksheet_name = "Acta de entrega"

        # --- Botones de mostrar/ocultar secciones (fuera del form) ---
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Lista de chequeo general elementos electromecánicos")
        if 'mostrar_motores' not in st.session_state:
            st.session_state['mostrar_motores'] = False
        if st.button("¿Hay motores?"):
            st.session_state['mostrar_motores'] = not st.session_state['mostrar_motores']
        if 'mostrar_reductor' not in st.session_state:
            st.session_state['mostrar_reductor'] = False
        if st.button("¿Hay reductor?"):
            st.session_state['mostrar_reductor'] = not st.session_state['mostrar_reductor']
        if 'mostrar_bomba' not in st.session_state:
            st.session_state['mostrar_bomba'] = False
        if st.button("¿Hay bomba?"):
            st.session_state['mostrar_bomba'] = not st.session_state['mostrar_bomba']
        if 'mostrar_turbina' not in st.session_state:
            st.session_state['mostrar_turbina'] = False
        if st.button("¿Hay turbina?"):
            st.session_state['mostrar_turbina'] = not st.session_state['mostrar_turbina']
        if 'mostrar_quemador' not in st.session_state:
            st.session_state['mostrar_quemador'] = False
        if st.button("¿Hay quemador?"):
            st.session_state['mostrar_quemador'] = not st.session_state['mostrar_quemador']
        if 'mostrar_bomba_vacio' not in st.session_state:
            st.session_state['mostrar_bomba_vacio'] = False
        if st.button("¿Hay bomba de vacío?"):
            st.session_state['mostrar_bomba_vacio'] = not st.session_state['mostrar_bomba_vacio']
        if 'mostrar_compresor' not in st.session_state:
            st.session_state['mostrar_compresor'] = False
        if st.button("¿Hay compresor?"):
            st.session_state['mostrar_compresor'] = not st.session_state['mostrar_compresor']

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Lista de chequeo general accesorios")
        if 'mostrar_manometros' not in st.session_state:
            st.session_state['mostrar_manometros'] = False
        if st.button("¿Hay manómetros?"):
            st.session_state['mostrar_manometros'] = not st.session_state['mostrar_manometros']
        if 'mostrar_vacuometros' not in st.session_state:
            st.session_state['mostrar_vacuometros'] = False
        if st.button("¿Hay vacuómetros?"):
            st.session_state['mostrar_vacuometros'] = not st.session_state['mostrar_vacuometros']
        if 'mostrar_valvulas' not in st.session_state:
            st.session_state['mostrar_valvulas'] = False
        if st.button("¿Hay válvulas?"):
            st.session_state['mostrar_valvulas'] = not st.session_state['mostrar_valvulas']
        if 'mostrar_mangueras' not in st.session_state:
            st.session_state['mostrar_mangueras'] = False
        if st.button("¿Hay mangueras?"):
            st.session_state['mostrar_mangueras'] = not st.session_state['mostrar_mangueras']
        if 'mostrar_boquillas' not in st.session_state:
            st.session_state['mostrar_boquillas'] = False
        if st.button("¿Hay boquillas?"):
            st.session_state['mostrar_boquillas'] = not st.session_state['mostrar_boquillas']
        if 'mostrar_reguladores' not in st.session_state:
            st.session_state['mostrar_reguladores'] = False
        if st.button("¿Hay reguladores aire/gas?"):
            st.session_state['mostrar_reguladores'] = not st.session_state['mostrar_reguladores']

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Lista de chequeo general elementos mecánicos")
        if 'mostrar_pinon1' not in st.session_state:
            st.session_state['mostrar_pinon1'] = False
        if st.button("¿Hay piñón 1?"):
            st.session_state['mostrar_pinon1'] = not st.session_state['mostrar_pinon1']
        if 'mostrar_pinon2' not in st.session_state:
            st.session_state['mostrar_pinon2'] = False
        if st.button("¿Hay piñón 2?"):
            st.session_state['mostrar_pinon2'] = not st.session_state['mostrar_pinon2']
        if 'mostrar_polea1' not in st.session_state:
            st.session_state['mostrar_polea1'] = False
        if st.button("¿Hay polea 1?"):
            st.session_state['mostrar_polea1'] = not st.session_state['mostrar_polea1']
        if 'mostrar_polea2' not in st.session_state:
            st.session_state['mostrar_polea2'] = False
        if st.button("¿Hay polea 2?"):
            st.session_state['mostrar_polea2'] = not st.session_state['mostrar_polea2']

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Lista de chequeo general elementos eléctricos")
        if 'mostrar_gabinete' not in st.session_state:
            st.session_state['mostrar_gabinete'] = False
        if st.button("¿Hay gabinete eléctrico?"):
            st.session_state['mostrar_gabinete'] = not st.session_state['mostrar_gabinete']
        if 'mostrar_arrancador' not in st.session_state:
            st.session_state['mostrar_arrancador'] = False
        if st.button("¿Hay arrancador?"):
            st.session_state['mostrar_arrancador'] = not st.session_state['mostrar_arrancador']
        if 'mostrar_control_nivel' not in st.session_state:
            st.session_state['mostrar_control_nivel'] = False
        if st.button("¿Hay control de nivel?"):
            st.session_state['mostrar_control_nivel'] = not st.session_state['mostrar_control_nivel']
        if 'mostrar_variador' not in st.session_state:
            st.session_state['mostrar_variador'] = False
        if st.button("¿Hay variador de velocidad?"):
            st.session_state['mostrar_variador'] = not st.session_state['mostrar_variador']
        if 'mostrar_sensor_temp' not in st.session_state:
            st.session_state['mostrar_sensor_temp'] = False
        if st.button("¿Hay sensor de temperatura?"):
            st.session_state['mostrar_sensor_temp'] = not st.session_state['mostrar_sensor_temp']
        if 'mostrar_toma_corriente' not in st.session_state:
            st.session_state['mostrar_toma_corriente'] = False
        if st.button("¿Hay toma corriente?"):
            st.session_state['mostrar_toma_corriente'] = not st.session_state['mostrar_toma_corriente']

        # --- Formulario principal ---

        with st.form("acta_entrega_form"):
            # Encabezados en el orden y nombre exacto solicitado

            st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales del acta de entrega</b>", unsafe_allow_html=True)
            cliente = st.text_input("cliente")
            op = st.text_input("op")
            equipo = st.text_input("equipo")
            item = st.text_input("item")
            cantidad = st.text_input("cantidad")
            fecha = st.text_input("fecha")
            st.markdown("</div>", unsafe_allow_html=True)

            # Motores
            hay_motores = st.checkbox("¿Hay motores?")
            if hay_motores:
                cantidad_motores = st.text_input("cantidad motores")
                voltaje_motores = st.text_input("voltaje motores")
                fotos_motores = st.text_input("fotos motores (URL o nombre)")
            else:
                cantidad_motores = ""
                voltaje_motores = ""
                fotos_motores = ""

            # Reductores
            hay_reductores = st.checkbox("¿Hay reductores?")
            if hay_reductores:
                cantidad_reductores = st.text_input("cantidad reductores")
                voltaje_reductores = st.text_input("voltaje reductores")
                fotos_reductores = st.text_input("fotos reductores (URL o nombre)")
            else:
                cantidad_reductores = ""
                voltaje_reductores = ""
                fotos_reductores = ""

            # Bombas
            hay_bombas = st.checkbox("¿Hay bombas?")
            if hay_bombas:
                cantidad_bombas = st.text_input("cantidad bombas")
                voltaje_bombas = st.text_input("voltaje bombas")
                fotos_bombas = st.text_input("fotos bombas (URL o nombre)")
            else:
                cantidad_bombas = ""
                voltaje_bombas = ""
                fotos_bombas = ""

            # Turbina
            hay_turbina = st.checkbox("¿Hay turbina?")
            if hay_turbina:
                voltaje_turbina = st.text_input("voltaje turbina")
                foto_turbina = st.text_input("foto turbina (URL o nombre)")
            else:
                voltaje_turbina = ""
                foto_turbina = ""

            # Quemador
            hay_quemador = st.checkbox("¿Hay quemador?")
            if hay_quemador:
                voltaje_quemador = st.text_input("voltaje quemador")
                foto_quemador = st.text_input("foto quemador (URL o nombre)")
            else:
                voltaje_quemador = ""
                foto_quemador = ""

            # Bomba de vacío
            hay_bomba_vacio = st.checkbox("¿Hay bomba de vacio?")
            if hay_bomba_vacio:
                voltaje_bomba_vacio = st.text_input("voltaje bomba de vacio")
                foto_bomba_vacio = st.text_input("foto bomba de vacio (URL o nombre)")
            else:
                voltaje_bomba_vacio = ""
                foto_bomba_vacio = ""

            # Compresor
            hay_compresor = st.checkbox("¿Hay compresor?")
            if hay_compresor:
                voltaje_compresor = st.text_input("voltaje compresor")
                foto_compresor = st.text_input("foto compresor (URL o nombre)")
            else:
                voltaje_compresor = ""
                foto_compresor = ""

            # Manómetros
            hay_manometros = st.checkbox("¿Hay manometros?")
            if hay_manometros:
                cantidad_manometros = st.text_input("cantidad manometros")
                foto_manometros = st.text_input("foto manometros (URL o nombre)")
            else:
                cantidad_manometros = ""
                foto_manometros = ""

            # Vacuómetros
            hay_vacuometros = st.checkbox("¿Hay vacuometros?")
            if hay_vacuometros:
                cantidad_vacuometros = st.text_input("cantidad vacuometros")
                foto_vacuometros = st.text_input("foto vacuometros (URL o nombre)")
            else:
                cantidad_vacuometros = ""
                foto_vacuometros = ""

            # Válvulas
            hay_valvulas = st.checkbox("¿Hay valvulas?")
            if hay_valvulas:
                cantidad_valvulas = st.text_input("cantidad valvulas")
                foto_valvulas = st.text_input("foto valvulas (URL o nombre)")
            else:
                cantidad_valvulas = ""
                foto_valvulas = ""

            # Mangueras
            hay_mangueras = st.checkbox("¿Hay mangueras?")
            if hay_mangueras:
                cantidad_mangueras = st.text_input("cantidad mangueras")
                foto_mangueras = st.text_input("foto mangueras (URL o nombre)")
            else:
                cantidad_mangueras = ""
                foto_mangueras = ""

            # Boquillas
            hay_boquillas = st.checkbox("¿Hay boquillas?")
            if hay_boquillas:
                cantidad_boquillas = st.text_input("cantidad boquillas")
                foto_boquillas = st.text_input("foto boquillas (URL o nombre)")
            else:
                cantidad_boquillas = ""
                foto_boquillas = ""

            # Reguladores
            hay_reguladores = st.checkbox("¿Hay reguladores aire/gas?")
            if hay_reguladores:
                cantidad_reguladores = st.text_input("cantidad reguladores aire/gas")
                foto_reguladores = st.text_input("foto reguladores (URL o nombre)")
            else:
                cantidad_reguladores = ""
                foto_reguladores = ""

            # Piñón 1
            hay_pinon1 = st.checkbox("¿Hay piñon 1?")
            if hay_pinon1:
                tension_pinon1 = st.text_input("tension piñon 1")
                foto_pinon1 = st.text_input("foto piñon 1 (URL o nombre)")
            else:
                tension_pinon1 = ""
                foto_pinon1 = ""

            # Piñón 2
            hay_pinon2 = st.checkbox("¿Hay piñon 2?")
            if hay_pinon2:
                tension_pinon2 = st.text_input("tension piñon 2")
                foto_pinon2 = st.text_input("foto piñon 2 (URL o nombre)")
            else:
                tension_pinon2 = ""
                foto_pinon2 = ""

            # Polea 1
            hay_polea1 = st.checkbox("¿Hay polea 1?")
            if hay_polea1:
                tension_polea1 = st.text_input("tension polea 1")
                foto_polea1 = st.text_input("foto polea 1 (URL o nombre)")
            else:
                tension_polea1 = ""
                foto_polea1 = ""

            # Polea 2
            hay_polea2 = st.checkbox("¿Hay polea 2?")
            if hay_polea2:
                tension_polea2 = st.text_input("tension polea 2")
                foto_polea2 = st.text_input("foto polea 2 (URL o nombre)")
            else:
                tension_polea2 = ""
                foto_polea2 = ""

            # Gabinete electrico
            hay_gabinete = st.checkbox("¿Hay gabinete electrico?")
            if hay_gabinete:
                cantidad_gabinete = st.text_input("cantidad gabinete electrico")
                foto_gabinete = st.text_input("foto gabinete (URL o nombre)")
            else:
                cantidad_gabinete = ""
                foto_gabinete = ""

            # Arrancadores
            hay_arrancadores = st.checkbox("¿Hay arrancadores?")
            if hay_arrancadores:
                cantidad_arrancadores = st.text_input("cantidad arrancadores")
                foto_arrancadores = st.text_input("foto arrancadores (URL o nombre)")
            else:
                cantidad_arrancadores = ""
                foto_arrancadores = ""

            # Control de nivel
            hay_control_nivel = st.checkbox("¿Hay control de nivel?")
            if hay_control_nivel:
                cantidad_control_nivel = st.text_input("cantidad control de nivel")
                foto_control_nivel = st.text_input("foto control de nivel (URL o nombre)")
            else:
                cantidad_control_nivel = ""
                foto_control_nivel = ""

            # Variadores de velocidad
            hay_variadores = st.checkbox("¿Hay variadores de velocidad?")
            if hay_variadores:
                cantidad_variadores = st.text_input("cantidad variadores de velociad")
                foto_variadores = st.text_input("foto variadores de velocidad (URL o nombre)")
            else:
                cantidad_variadores = ""
                foto_variadores = ""

            # Sensores de temperatura
            hay_sensores = st.checkbox("¿Hay sensores de temperatura?")
            if hay_sensores:
                cantidad_sensores = st.text_input("cantidad sensores de temperatura")
                foto_sensores = st.text_input("foto sensores de temperatura (URL o nombre)")
            else:
                cantidad_sensores = ""
                foto_sensores = ""

            # Toma corriente
            hay_toma_corriente = st.checkbox("¿Hay toma corriente?")
            if hay_toma_corriente:
                cantidad_toma_corriente = st.text_input("cantidad toma corriente")
                foto_toma_corrientes = st.text_input("foto toma corrientes (URL o nombre)")
            else:
                cantidad_toma_corriente = ""
                foto_toma_corrientes = ""
            otros_elementos = st.text_area("otros elementos")
            revision_soldadura = st.text_input("revision de soldadura")
            revision_sentidos = st.text_input("revision de sentidos de giro")
            manual_funcionamiento = st.text_input("manual de funcionamiento")
            revision_filos = st.text_input("revision de filos y acabados")
            revision_tratamientos = st.text_input("revision de tratamientos")
            revision_tornilleria = st.text_input("revision de tornilleria")
            revision_ruidos = st.text_input("revision de ruidos")
            ensayo_equipo = st.text_input("ensayo equipo")
            observaciones_generales = st.text_area("observciones generales")
            lider_inspeccion = st.text_input("lider de inspeccion")
            disenador = st.text_input("diseñador")
            recibe = st.text_input("recibe")
            fecha_entrega = st.text_input("fecha de entrega")

            submitted = st.form_submit_button("Guardar acta de entrega")

            # Validación: solo encabezado y responsables son obligatorios

            if submitted:
                # Guardar los datos en el orden exacto solicitado
                row = [
                    cliente, op, item, equipo, cantidad, fecha, cantidad_motores, voltaje_motores, fotos_motores,
                    cantidad_reductores, voltaje_reductores, fotos_reductores, cantidad_bombas, voltaje_bombas, fotos_bombas,
                    voltaje_turbina, foto_turbina, voltaje_quemador, foto_quemador, voltaje_bomba_vacio, foto_bomba_vacio,
                    voltaje_compresor, foto_compresor, cantidad_manometros, foto_manometros, cantidad_vacuometros, foto_vacuometros,
                    cantidad_valvulas, foto_valvulas, cantidad_mangueras, foto_mangueras, cantidad_boquillas, foto_boquillas,
                    cantidad_reguladores, foto_reguladores, tension_pinon1, foto_pinon1, tension_pinon2, foto_pinon2,
                    tension_polea1, foto_polea1, tension_polea2, foto_polea2, cantidad_gabinete, foto_gabinete,
                    cantidad_arrancadores, foto_arrancadores, cantidad_control_nivel, foto_control_nivel, cantidad_variadores, foto_variadores,
                    cantidad_sensores, foto_sensores, cantidad_toma_corriente, foto_toma_corrientes, otros_elementos,
                    revision_soldadura, revision_sentidos, manual_funcionamiento, revision_filos, revision_tratamientos, revision_tornilleria,
                    revision_ruidos, ensayo_equipo, observaciones_generales, lider_inspeccion, disenador, recibe, fecha_entrega
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
                    "cantidad sensores de temperatura", "foto sensores de temperatura", "cantidad toma corriente", "foto toma corrientes", "otros elementos",
                    "revision de soldadura", "revision de sentidos de giro", "manual de funcionamiento", "revision de filos y acabados", "revision de tratamientos", "revision de tornilleria",
                    "revision de ruidos", "ensayo equipo", "observciones generales", "lider de inspeccion", "diseñador", "recibe", "fecha de entrega"
                ]
                sheet = sheet_client.open(file_name).worksheet(worksheet_name)
                if not sheet.get_all_values():
                    sheet.append_row(headers)
                sheet.append_row(row)
                st.success("Acta de entrega guardada correctamente en Google Sheets.")

if __name__ == "__main__":
    main()
