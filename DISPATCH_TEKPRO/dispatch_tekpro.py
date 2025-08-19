import streamlit as st
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import date
import io

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]
from google.oauth2.service_account import Credentials
import json

creds = None
try:
    # Intentar usar Service Account primero
    if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
        try:
            creds = Credentials.from_service_account_info(
                st.secrets.gcp_service_account,
                scopes=SCOPES
            )
            st.success("Conectado usando Service Account")
        except Exception as e:
            st.warning(f"No se pudo usar Service Account: {str(e)}")
            creds = None
    
    # Si Service Account falla, intentar OAuth2
    if creds is None and hasattr(st, 'secrets') and 'oauth2' in st.secrets:
        try:
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": dict(st.secrets.oauth2)
                },
                SCOPES
            )
            creds = flow.run_local_server(port=0)
            st.success("Conectado usando OAuth2")
        except Exception as oauth_error:
            st.error(f"Error con OAuth2: {str(oauth_error)}")
            st.stop()
    
    # Si no hay credenciales en secrets.toml, intentar archivos locales
    if creds is None:
        # Intentar Service Account local
        service_account_path = 'secrets/credentials.json'
        if os.path.exists(service_account_path):
            try:
                creds = Credentials.from_service_account_file(
                    service_account_path,
                    scopes=SCOPES
                )
                st.success("Conectado usando archivo local de Service Account")
            except Exception as e:
                st.warning(f"No se pudo usar archivo local de Service Account: {str(e)}")
                creds = None
        
        # Si todo lo anterior falla, intentar OAuth2 local
        if creds is None:
            client_secret_path = 'secrets/client_secret.json'
            if os.path.exists(client_secret_path):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        client_secret_path,
                        SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    st.success("Conectado usando archivo local de OAuth2")
                except Exception as e:
                    st.error(f"Error con archivo local de OAuth2: {str(e)}")
                    st.stop()
            else:
                st.error("No se encontraron credenciales válidas")
                st.stop()

    if creds is None:
        st.error("No se pudo establecer conexión con ningún método de autenticación")
        st.stop()

except Exception as e:
    st.error(f"Error al configurar credenciales: {str(e)}")
    st.stop()
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

# Obtener configuración de Drive y Sheets
SHEET_NAME = st.secrets.drive_config.SHEET_NAME
sheet = client.open(SHEET_NAME).sheet1

st.title("Despacho de Guacales - Tekpro")

if "num_guacales" not in st.session_state:
    st.session_state["num_guacales"] = 5

with st.form("dispatch_form"):
    fecha = st.date_input("Fecha del día", value=date.today())
    nombre_proyecto = st.text_input("Nombre de proyecto")
    orden_pedido = st.text_input("Orden de pedido")
    encargado_ensamblador = st.text_input("Encargado ensamblador")
    encargado_almacen = st.text_input("Encargado almacen")
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
    if st.session_state["num_guacales"] < 10:
        if st.form_submit_button("Agregar guacal"):
            st.session_state["num_guacales"] += 1
            st.experimental_rerun()
    submitted = st.form_submit_button("Guardar despacho")

if submitted:
    if not guacales[0]["desc"]:
        st.error("La descripción del Guacal 1 es obligatoria.")
    else:
        row = [
            str(fecha), nombre_proyecto, orden_pedido,
            encargado_ensamblador, encargado_almacen, encargado_ingenieria
        ]
        folder_id = st.secrets.drive_config.FOLDER_ID
        for idx, guacal in enumerate(guacales, start=1):
            row.append(guacal["desc"])
            foto = guacal["foto"]
            if foto:
                # Subir foto a Google Drive en la carpeta especificada
                file_name = f"Guacal_{idx}_{orden_pedido}.jpg"
                file_stream = io.BytesIO(foto.read())
                media = MediaIoBaseUpload(file_stream, mimetype=foto.type, resumable=True)
                file_metadata = {
                    'name': file_name,
                    'parents': [folder_id],
                }
                uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                # Hacer el archivo público
                drive_service.permissions().create(
                    fileId=uploaded_file['id'],
                    body={'type': 'anyone', 'role': 'reader'}
                ).execute()
                # Obtener el enlace público
                public_url = f"https://drive.google.com/uc?id={uploaded_file['id']}"
                row.append(public_url)
            else:
                row.append("Sin foto")
        sheet.append_row(row)
        st.success("Despacho guardado correctamente.")
        st.info("Las fotos han sido subidas a Google Drive y el enlace está disponible en la hoja.")
