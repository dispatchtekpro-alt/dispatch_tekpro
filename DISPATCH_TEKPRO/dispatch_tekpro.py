import streamlit as st
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
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
def get_drive_service_oauth():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    from google_auth_oauthlib.flow import Flow
    redirect_uri = "https://dispatchtekpro.streamlit.app/"
    st.info(f"[LOG] Usando redirect_uri: {redirect_uri}")
    print(f"[LOG] Usando redirect_uri: {redirect_uri}")
    flow = Flow.from_client_config(
        {"web": dict(st.secrets.oauth2)},
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
    st.markdown(f"[Haz clic aquí para autorizar con Google Drive]({auth_url})")
    auth_code = st.text_input("Pega aquí el código de autorización que recibiste tras autorizar:")
    creds = None
    if auth_code:
        try:
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            st.success("¡Autorización exitosa!")
        except Exception as e:
            st.error(f"Error al intercambiar el código: {e}")
    if creds:
        return build('drive', 'v3', credentials=creds)
    else:
        st.stop()

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
    st.title("Despacho de Guacales - Tekpro")

    # Configuración: carpeta y sheet
    folder_id = st.secrets.drive_config.FOLDER_ID
    file_name = st.secrets.drive_config.FILE_NAME
    worksheet_name = st.secrets.drive_config.WORKSHEET_NAME

    creds = get_service_account_creds()
    sheet_client = gspread.authorize(creds)

    if "num_guacales" not in st.session_state:
        st.session_state["num_guacales"] = 1

    with st.form("dispatch_form"):
        import datetime
        fecha = st.date_input("Fecha del día", value=datetime.date.today())
        nombre_proyecto = st.text_input("Nombre de proyecto")
        orden_pedido = st.text_input("Orden de pedido")
        encargado_ensamblador = st.text_input("Encargado ensamblador")
        encargado_almacen = st.text_input("Encargado almacén")
        encargado_ingenieria = st.text_input("Encargado ingeniería y diseño")

        guacales = []
        for i in range(st.session_state["num_guacales"]):
            st.subheader(f"Guacal {i+1}")
            desc = st.text_area(f"Descripción Guacal {i+1}", key=f"desc_{i+1}")
            foto = st.file_uploader(f"Foto Guacal {i+1}", type=["jpg", "jpeg", "png"], key=f"foto_{i+1}")
            guacales.append({
                "desc": desc,
                "foto": foto
            })
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state["num_guacales"] < 10:
                if st.form_submit_button("Agregar guacal"):
                    st.session_state["num_guacales"] += 1
                    st.experimental_rerun()
        with col2:
            submitted = st.form_submit_button("Guardar despacho")

    if submitted:
        if not guacales[0]["desc"]:
            st.error("La descripción del Guacal 1 es obligatoria.")
        else:
            row = [
                str(fecha), nombre_proyecto, orden_pedido,
                encargado_ensamblador, encargado_almacen, encargado_ingenieria
            ]
            # Subir fotos y agregar descripciones y links
            for idx, guacal in enumerate(guacales, start=1):
                row.append(guacal["desc"])
                foto = guacal["foto"]
                if foto:
                    try:
                        image_filename = f"Guacal_{idx}_{orden_pedido}.jpg"
                        file_stream = io.BytesIO(foto.read())
                        public_url = upload_image_to_drive_oauth(file_stream, image_filename, folder_id)
                        row.append(public_url)
                        st.success(f"Foto del Guacal {idx} subida correctamente")
                    except Exception as upload_error:
                        st.error(f"Error al subir la foto del Guacal {idx}: {str(upload_error)}")
                        row.append("Error al subir foto")
                else:
                    row.append("Sin foto")
            # Guardar en Sheets
            write_link_to_sheet(sheet_client, file_name, worksheet_name, row)
            st.success("Despacho guardado correctamente.")
            st.info("Las fotos han sido subidas a Google Drive y el enlace está disponible en la hoja.")

if __name__ == "__main__":
    main()
