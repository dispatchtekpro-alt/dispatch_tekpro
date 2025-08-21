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
#
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
    if st.button("Validar código"):
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

    # Título principal y subtítulo con estilo corporativo
    st.markdown(
        """
        <div style="margin-bottom: 0.5em;">
            <h1 style="margin: 0; font-family: 'Montserrat', Arial, sans-serif; color: #1db6b6; font-weight: 700; letter-spacing: 1px;">DISPATCH TEKPRO</h1>
            <h2 style="margin: 0; font-family: 'Montserrat', Arial, sans-serif; color: #1db6b6; font-weight: 600; font-size: 1.5em;">Acta de entrega y lista de empaque</h2>
        </div>
        <hr style="border: none; border-top: 2px solid #1db6b6; margin-bottom: 1.5em;">
        """,
        unsafe_allow_html=True
    )

    # Configuración: carpeta y sheet
    folder_id = st.secrets.drive_config.FOLDER_ID
    file_name = st.secrets.drive_config.FILE_NAME
    worksheet_name = st.secrets.drive_config.WORKSHEET_NAME

    creds = get_service_account_creds()
    sheet_client = gspread.authorize(creds)

    # Leer órdenes de pedido existentes y sus datos
    try:
        sheet = sheet_client.open(file_name).worksheet(worksheet_name)
        all_rows = sheet.get_all_values()
        # Suponiendo que la primera fila es encabezado y las columnas son:
        # Fecha, Nombre Proyecto, Orden Pedido, Encargado Ensamblador, Encargado Almacen, Encargado Ingenieria, ...
        ordenes_existentes = {}
        for row in all_rows[1:]:
            if len(row) >= 6:
                orden = row[2]
                ordenes_existentes[orden] = {
                    "nombre_proyecto": row[1],
                    "encargado_ingenieria": row[5]
                }
        ordenes_list = list(ordenes_existentes.keys())
    except Exception:
        ordenes_existentes = {}
        ordenes_list = []

    # Autorizar Drive solo si no hay token
    if 'drive_oauth_token' not in st.session_state:
        authorize_drive_oauth()

    if "num_guacales" not in st.session_state:
        st.session_state["num_guacales"] = 1

    with st.form("dispatch_form"):
        import datetime
        fecha = st.date_input("Fecha del día", value=datetime.date.today())



        # Orden de pedido: selectbox nativo con opción para escribir nueva
        st.markdown("<b>Orden de pedido</b> (elige una existente o escribe una nueva)", unsafe_allow_html=True)
        opciones_orden = ordenes_list + ["Otra (escribir nueva)"] if ordenes_list else ["Otra (escribir nueva)"]
        seleccion_orden = st.selectbox(
            "Selecciona una orden existente o elige 'Otra (escribir nueva)' para ingresar una nueva:",
            opciones_orden,
            index=0 if ordenes_list else 0,
            key="orden_pedido_selectbox"
        )
        if seleccion_orden == "Otra (escribir nueva)":
            orden_pedido_val = st.text_input("Escribe la nueva orden de pedido:", key="orden_pedido_nueva")
        else:
            orden_pedido_val = seleccion_orden

        # Autocompletar nombre de proyecto y encargado de ingeniería si existe
        nombre_proyecto_default = ""
        encargado_ingenieria_default = ""
        if orden_pedido_val and orden_pedido_val in ordenes_existentes:
            nombre_proyecto_default = ordenes_existentes[orden_pedido_val]["nombre_proyecto"]
            encargado_ingenieria_default = ordenes_existentes[orden_pedido_val]["encargado_ingenieria"]

        nombre_proyecto = st.text_input("Nombre de proyecto", value=nombre_proyecto_default)
        encargado_ensamblador = st.selectbox(
            "Encargado ensamblador",
            [
                "Jaime Ramos",
                "Jaime Rincon",
                "Lewis",
                "Kate",
                "Jefferson",
                "Yeison",
                "Gabriel"
            ]
        )
        encargado_almacen = st.selectbox("Encargado almacén", ["Andrea", "Juan Pablo"])
        encargado_ingenieria = st.selectbox(
            "Encargado ingeniería y diseño",
            [
                "Daniel Valbuena",
                "Alejandro Diaz",
                "Juan Andres",
                "Juan David",
                "Jose",
                "Diomer",
                "Victor"
            ],
            index=[
                "Daniel Valbuena",
                "Alejandro Diaz",
                "Juan Andres",
                "Juan David",
                "Jose",
                "Diomer",
                "Victor"
            ].index(encargado_ingenieria_default) if encargado_ingenieria_default in [
                "Daniel Valbuena",
                "Alejandro Diaz",
                "Juan Andres",
                "Juan David",
                "Jose",
                "Diomer",
                "Victor"
            ] else 0
        )

        guacales = []
        for i in range(st.session_state["num_guacales"]):
            st.subheader(f"PAQUETE {i+1}")
            desc = st.text_area(f"Descripción PAQUETE {i+1}", key=f"desc_{i+1}")
            fotos = st.file_uploader(
                f"Fotos PAQUETE {i+1}",
                type=["jpg", "jpeg", "png"],
                key=f"foto_{i+1}",
                accept_multiple_files=True
            )
            guacales.append({
                "desc": desc,
                "fotos": fotos
            })
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state["num_guacales"] < 10:
                if st.form_submit_button("Agregar paquete"):
                    st.session_state["num_guacales"] += 1
                    st.experimental_rerun()
        with col2:
            submitted = st.form_submit_button("Guardar despacho")

    if submitted:
        if not guacales[0]["desc"]:
            st.error("La descripción del PAQUETE 1 es obligatoria.")
        else:
            row = [
                str(fecha), nombre_proyecto, orden_pedido_val,
                encargado_ensamblador, encargado_almacen, encargado_ingenieria
            ]
            # Subir fotos y agregar descripciones y links
            for idx, guacal in enumerate(guacales, start=1):
                row.append(guacal["desc"])
                fotos = guacal["fotos"]
                enlaces = []
                if fotos:
                    for n, foto in enumerate(fotos, start=1):
                        try:
                            image_filename = f"Guacal_{idx}_{orden_pedido_val}_{n}.jpg"
                            file_stream = io.BytesIO(foto.read())
                            public_url = upload_image_to_drive_oauth(file_stream, image_filename, folder_id)
                            enlaces.append(public_url)
                            st.success(f"Foto {n} del Guacal {idx} subida correctamente")
                        except Exception as upload_error:
                            st.error(f"Error al subir la foto {n} del Guacal {idx}: {str(upload_error)}")
                    if enlaces:
                        row.append(", ".join(enlaces))
                    else:
                        row.append("Error al subir foto")
                else:
                    row.append("Sin foto")
            # Guardar en Sheets
            write_link_to_sheet(sheet_client, file_name, worksheet_name, row)
            st.success("Despacho guardado correctamente.")
            st.info("Las fotos han sido subidas a Google Drive y el enlace está disponible en la hoja.")

if __name__ == "__main__":
    main()
