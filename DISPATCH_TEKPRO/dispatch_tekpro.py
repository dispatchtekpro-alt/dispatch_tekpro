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
    # Intentar cargar credenciales desde archivo local
    service_account_path = 'secrets/client_secret.json'
    if os.path.exists(service_account_path):
        creds = Credentials.from_service_account_file(
            service_account_path,
            scopes=SCOPES
        )
    # Si no hay archivo local, intentar usar secretos de Streamlit
    elif hasattr(st, 'secrets'):
        try:
            creds = Credentials.from_service_account_info(
                st.secrets,
                scopes=SCOPES
            )
        except Exception as e:
            st.error(f"Error con secretos de Streamlit: {str(e)}")
            st.stop()
    else:
        st.error("No se encontraron credenciales")
        st.stop()
except Exception as e:
    st.error(f"Error al configurar credenciales: {str(e)}")
    st.stop()
client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

# Reemplaza con el nombre de tu hoja de cálculo
SHEET_NAME = 'dispatch_tekpro'
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
        FOLDER_ID = "1btIvJTu0Nn7U_8H9i9aKOKxjHXYuldAF"
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
                    'parents': [FOLDER_ID],
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
