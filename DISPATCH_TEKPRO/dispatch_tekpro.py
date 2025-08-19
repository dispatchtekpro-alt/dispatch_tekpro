import streamlit as st
import gspread
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import pickle
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import date
import io
import json

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]
from google.oauth2.service_account import Credentials

# Función para limpiar el estado de autenticación
def clear_auth_state():
    keys_to_clear = ['auth_method', 'creds', 'drive_service', 'sheet', 'client', 'oauth_state']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

# Función para inicializar OAuth
def start_oauth_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets.oauth2.client_id,
                "project_id": st.secrets.oauth2.project_id,
                "auth_uri": st.secrets.oauth2.auth_uri,
                "token_uri": st.secrets.oauth2.token_uri,
                "auth_provider_x509_cert_url": st.secrets.oauth2.auth_provider_x509_cert_url,
                "client_secret": st.secrets.oauth2.client_secret,
                "redirect_uris": st.secrets.oauth2.redirect_uris
            }
        },
        scopes=SCOPES,
        redirect_uri="http://localhost:8501/"
    )
    auth_url, state = flow.authorization_url(prompt='consent')
    st.session_state['oauth_state'] = state
    return auth_url

# Inicializar estado de autenticación
if 'auth_method' not in st.session_state:
    st.session_state['auth_method'] = None

# Botón para reiniciar autenticación
if st.session_state.get('auth_method'):
    if st.button("Cambiar método de autenticación"):
        clear_auth_state()
        st.rerun()

creds = None
try:
    # Si ya tenemos credenciales válidas, usarlas
    if 'creds' in st.session_state and st.session_state.get('creds'):
        creds = st.session_state['creds']
        
    # Si no hay método seleccionado, mostrar selector
    elif not st.session_state['auth_method']:
        auth_method = st.radio(
            "Selecciona el método de autenticación:",
            ["Service Account", "OAuth2"],
            index=None
        )
        
        if auth_method == "Service Account":
            if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
                try:
                    creds = Credentials.from_service_account_info(
                        st.secrets.gcp_service_account,
                        scopes=SCOPES
                    )
                    st.session_state['creds'] = creds
                    st.session_state['auth_method'] = 'service_account'
                    st.success("Conectado usando Service Account")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo usar Service Account: {str(e)}")
                    clear_auth_state()
        
        elif auth_method == "OAuth2":
            st.session_state['auth_method'] = 'oauth'
            st.rerun()
    
    # Si Service Account falla, intentar OAuth2
    if creds is None and hasattr(st, 'secrets') and 'oauth2' in st.secrets:
        try:
            # Mostrar instrucciones para OAuth2
            st.info("""
            Para usar OAuth2, necesitarás:
            1. Autorizar la aplicación en la ventana que se abrirá
            2. Iniciar sesión con tu cuenta de Google si es necesario
            3. Dar los permisos solicitados
            4. Serás redirigido automáticamente
            """)
            
            # Configurar OAuth2 para aplicación web
            oauth_config = {
                "web": {
                    "client_id": st.secrets.oauth2.client_id,
                    "project_id": st.secrets.oauth2.project_id,
                    "auth_uri": st.secrets.oauth2.auth_uri,
                    "token_uri": st.secrets.oauth2.token_uri,
                    "auth_provider_x509_cert_url": st.secrets.oauth2.auth_provider_x509_cert_url,
                    "client_secret": st.secrets.oauth2.client_secret,
                    "redirect_uris": st.secrets.oauth2.redirect_uris
                }
            }
            
            flow = Flow.from_client_config(
                oauth_config,
                scopes=SCOPES,
                redirect_uri="http://localhost:8501/"
            )
            
            # URL de autorización
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            # Mostrar el enlace de autorización
            st.markdown(f"[Haz clic aquí para autorizar la aplicación]({auth_url})")
            
            # Obtener el código de autorización de la URL
            if 'code' in st.query_params:
                code = st.query_params['code']
                try:
                    # Intercambiar el código por tokens
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    
                    # Inicializar servicios con las nuevas credenciales
                    drive_service = build('drive', 'v3', credentials=creds)
                    client = gspread.authorize(creds)
                    
                    # Verificar conexión con Drive
                    folder_id = st.secrets.drive_config.FOLDER_ID
                    drive_service.files().get(fileId=folder_id).execute()
                    
                    # Verificar conexión con Sheets
                    sheet = client.open(st.secrets.drive_config.SHEET_NAME).sheet1
                    
                    st.success("¡Autorización exitosa! Conexión establecida con Google Drive y Sheets")
                    
                    # Guardar las credenciales en session_state
                    st.session_state['creds'] = creds
                    st.session_state['drive_service'] = drive_service
                    st.session_state['sheet'] = sheet
                    
                except Exception as token_error:
                    st.error(f"Error al procesar el código de autorización: {str(token_error)}")
                    st.stop()
            else:
                st.warning("Esperando autorización...")
                st.stop()
                
        except Exception as oauth_error:
            st.error(f"Error en la configuración de OAuth2: {str(oauth_error)}")
            st.stop()
            # Generar URL de autorización
            auth_url, _ = flow.authorization_url()
            st.write("**Copia y pega esta URL en tu navegador:**")
            st.code(auth_url)
            
            # Solicitar el código de autorización
            auth_code = st.text_input("Ingresa el código de autorización:")
            if auth_code:
                try:
                    creds = flow.fetch_token(code=auth_code)
                    st.success("Conectado usando OAuth2")
                except Exception as token_error:
                    st.error(f"Error al procesar el código: {str(token_error)}")
                    st.stop()
            else:
                st.warning("Ingresa el código de autorización para continuar")
                st.stop()
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
                    with open(client_secret_path, 'r') as f:
                        client_config = json.load(f)
                    flow = Flow.from_client_config(
                        client_config,
                        scopes=SCOPES,
                        redirect_uri="http://localhost:8501/"
                    )
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    st.markdown(f"[Haz clic aquí para autorizar la aplicación]({auth_url})")
                    
                    query_params = st.experimental_get_query_params()
                    if 'code' in query_params:
                        code = query_params['code'][0]
                        creds = flow.fetch_token(code=code)
                        st.success("Conectado usando archivo local de OAuth2")
                    else:
                        st.warning("Esperando autorización...")
                        st.stop()
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
# Función para generar la URL de autorización de OAuth2
def authenticate_with_oauth2():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets.oauth2.client_id,
                "project_id": st.secrets.oauth2.project_id,
                "auth_uri": st.secrets.oauth2.auth_uri,
                "token_uri": st.secrets.oauth2.token_uri,
                "auth_provider_x509_cert_url": st.secrets.oauth2.auth_provider_x509_cert_url,
                "client_secret": st.secrets.oauth2.client_secret,
                "redirect_uris": st.secrets.oauth2.redirect_uris
            }
        },
        scopes=SCOPES,
        redirect_uri="http://localhost:8501/"
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return flow, auth_url

# Verificar y establecer la conexión con Google Services
try:
    # Verificar si estamos en el proceso de OAuth2
    if st.session_state['auth_method'] == 'oauth':
        if 'code' in st.query_params and 'state' in st.query_params:
            try:
                if 'oauth_state' not in st.session_state:
                    st.error("Estado de OAuth no encontrado. Por favor, inicia el proceso nuevamente.")
                    clear_auth_state()
                    st.rerun()
                
                # Configurar nuevo flujo de OAuth
                flow = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": st.secrets.oauth2.client_id,
                            "project_id": st.secrets.oauth2.project_id,
                            "auth_uri": st.secrets.oauth2.auth_uri,
                            "token_uri": st.secrets.oauth2.token_uri,
                            "auth_provider_x509_cert_url": st.secrets.oauth2.auth_provider_x509_cert_url,
                            "client_secret": st.secrets.oauth2.client_secret,
                            "redirect_uris": st.secrets.oauth2.redirect_uris
                        }
                    },
                    scopes=SCOPES,
                    redirect_uri="http://localhost:8501/",
                    state=st.session_state['oauth_state']
                )
                
                # Obtener token
                code = st.query_params['code']
                flow.fetch_token(code=code)
                creds = flow.credentials
                
                # Probar la conexión
                drive_service = build('drive', 'v3', credentials=creds)
                client = gspread.authorize(creds)
                
                # Verificar acceso
                folder_id = st.secrets.drive_config.FOLDER_ID
                drive_service.files().get(fileId=folder_id).execute()
                sheet = client.open(st.secrets.drive_config.SHEET_NAME).sheet1
                
                # Guardar todo en session_state
                st.session_state['creds'] = creds
                st.session_state['drive_service'] = drive_service
                st.session_state['sheet'] = sheet
                st.session_state['client'] = client
                
                st.success("¡Autorización exitosa! Conectado a Google Drive y Sheets")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error durante la autorización: {str(e)}")
                st.session_state['auth_method'] = None
                for key in ['creds', 'drive_service', 'sheet', 'client']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.button("Intentar nuevamente", on_click=lambda: st.rerun())
                st.stop()
        else:
            # Mostrar botón de autorización
            if 'oauth2' in st.secrets:
                auth_url = start_oauth_flow()
                st.markdown(
                    f'<a href="{auth_url}" target="_blank">'
                    '<button style="background-color: #4285f4; color: white; '
                    'padding: 12px 24px; border: none; border-radius: 4px; '
                    'cursor: pointer; font-size: 16px; font-weight: 500; '
                    'display: inline-flex; align-items: center; gap: 8px;">'
                    '<img src="https://www.google.com/favicon.ico" '
                    'style="width: 18px; height: 18px;"/> '
                    'Autorizar con Google</button></a>',
                    unsafe_allow_html=True
                )
                st.stop()
    
    # Usar credenciales guardadas en session_state si existen
    elif 'creds' in st.session_state and st.session_state['creds']:
        creds = st.session_state['creds']
        drive_service = build('drive', 'v3', credentials=creds)
        client = gspread.authorize(creds)
        
        # Verificar acceso a Drive
        folder_id = st.secrets.drive_config.FOLDER_ID
        drive_service.files().get(fileId=folder_id).execute()
        
        # Verificar acceso a Sheets
        SHEET_NAME = st.secrets.drive_config.SHEET_NAME
        sheet = client.open(SHEET_NAME).sheet1
        
        # Guardar servicios en session_state
        st.session_state['drive_service'] = drive_service
        st.session_state['sheet'] = sheet
    
    else:
        # Si no hay credenciales, iniciar OAuth2
        if 'oauth2' in st.secrets:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": st.secrets.oauth2.client_id,
                        "project_id": st.secrets.oauth2.project_id,
                        "auth_uri": st.secrets.oauth2.auth_uri,
                        "token_uri": st.secrets.oauth2.token_uri,
                        "auth_provider_x509_cert_url": st.secrets.oauth2.auth_provider_x509_cert_url,
                        "client_secret": st.secrets.oauth2.client_secret,
                        "redirect_uris": st.secrets.oauth2.redirect_uris
                    }
                },
                scopes=SCOPES,
                redirect_uri="http://localhost:8501/"
            )
            auth_url, _ = flow.authorization_url(prompt='consent')
            st.markdown(f"[Haz clic aquí para autorizar la aplicación]({auth_url})")
            st.stop()
        else:
            raise Exception("No se encontró configuración OAuth2")
            
except Exception as conn_error:
    st.error(f"Error al conectar con Google Services: {str(conn_error)}")
    st.stop()

# Obtener configuración de Drive y Sheets
SHEET_NAME = st.secrets.drive_config.SHEET_NAME

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
                try:
                    # Subir foto a Google Drive en la carpeta especificada
                    file_name = f"Guacal_{idx}_{orden_pedido}.jpg"
                    file_stream = io.BytesIO(foto.read())
                    media = MediaIoBaseUpload(file_stream, mimetype=foto.type, resumable=True)
                    
                    # Intentar primero con unidad compartida
                    file_metadata = {
                        'name': file_name,
                        'parents': [folder_id],
                        'driveId': folder_id
                    }
                    
                    try:
                        # Subir el archivo
                        uploaded_file = drive_service.files().create(
                            body=file_metadata,
                            media_body=media,
                            fields='id, webViewLink',
                            supportsAllDrives=True
                        ).execute()

                        # Configurar permisos después de subir
                        permission = {
                            'type': 'anyone',
                            'role': 'reader'
                        }
                        drive_service.permissions().create(
                            fileId=uploaded_file['id'],
                            body=permission,
                            fields='id',
                            supportsAllDrives=True
                        ).execute()
                    except Exception as shared_drive_error:
                        if isinstance(creds, Credentials):
                            # Si falla, intentar con OAuth2
                            st.warning("La cuenta de servicio no tiene permisos. Cambiando a OAuth2...")
                            
                            # Mostrar instrucciones
                            st.info("""
                            Para continuar necesitas autorizar el acceso:
                            1. Haz clic en el botón 'Autorizar con Google'
                            2. Inicia sesión y autoriza el acceso
                            3. Copia el código que te den
                            4. Pégalo en el campo que aparece abajo
                            """)

                            # Crear un archivo temporal con las credenciales
                            oauth_creds = {
                                "installed": {
                                    "client_id": st.secrets.oauth2.client_id,
                                    "project_id": st.secrets.oauth2.project_id,
                                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                    "token_uri": "https://oauth2.googleapis.com/token",
                                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                                    "client_secret": st.secrets.oauth2.client_secret,
                                    "redirect_uris": ["http://localhost"]
                                }
                            }
                            
                            # Crear archivo temporal
                            temp_creds_path = "temp_client_secret.json"
                            with open(temp_creds_path, "w") as f:
                                json.dump(oauth_creds, f)
                            
                            try:
                                # Usar el archivo de credenciales
                                oauth_config = {
                                    "web": {
                                        "client_id": st.secrets.oauth2.client_id,
                                        "project_id": st.secrets.oauth2.project_id,
                                        "auth_uri": st.secrets.oauth2.auth_uri,
                                        "token_uri": st.secrets.oauth2.token_uri,
                                        "auth_provider_x509_cert_url": st.secrets.oauth2.auth_provider_x509_cert_url,
                                        "client_secret": st.secrets.oauth2.client_secret,
                                        "redirect_uris": st.secrets.oauth2.redirect_uris
                                    }
                                }
                                flow = Flow.from_client_config(
                                    oauth_config,
                                    scopes=SCOPES,
                                    redirect_uri="http://localhost:8501/"
                                )
                                auth_url, _ = flow.authorization_url()
                            finally:
                                # Eliminar archivo temporal
                                if os.path.exists(temp_creds_path):
                                    os.remove(temp_creds_path)
                            
                            # Crear columnas para centrar el botón de autorización
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                st.write(
                                    f'<div style="text-align: center;">'
                                    f'<a href="{auth_url}" target="_blank">'
                                    '<button style="background-color: #4285f4; color: white; '
                                    'padding: 12px 24px; border: none; border-radius: 4px; '
                                    'cursor: pointer; font-size: 16px; font-weight: 500; '
                                    'display: inline-flex; align-items: center; gap: 8px;">'
                                    '<img src="https://www.google.com/favicon.ico" '
                                    'style="width: 18px; height: 18px;"/> '
                                    'Autorizar con Google</button></a></div>',
                                    unsafe_allow_html=True
                                )
                            
                            # Campo para el código de autorización
                            code = st.text_input(f"Ingresa el código de autorización para el Guacal {idx}:")
                            if code:
                                try:
                                    # Crear archivo temporal nuevamente para el proceso de token
                                    with open(temp_creds_path, "w") as f:
                                        json.dump(oauth_creds, f)
                                    
                                    try:
                                        flow = Flow.from_client_config(
                                            {
                                                "web": {
                                                    "client_id": st.secrets.oauth2.client_id,
                                                    "project_id": st.secrets.oauth2.project_id,
                                                    "auth_uri": st.secrets.oauth2.auth_uri,
                                                    "token_uri": st.secrets.oauth2.token_uri,
                                                    "auth_provider_x509_cert_url": st.secrets.oauth2.auth_provider_x509_cert_url,
                                                    "client_secret": st.secrets.oauth2.client_secret,
                                                    "redirect_uris": st.secrets.oauth2.redirect_uris
                                                }
                                            },
                                            scopes=SCOPES,
                                            redirect_uri="http://localhost:8501/"
                                        )
                                        creds = flow.fetch_token(code=code)
                                        drive_service = build('drive', 'v3', credentials=creds)
                                        
                                        # Intentar subir nuevamente con OAuth2
                                        uploaded_file = drive_service.files().create(
                                            body={'name': file_name, 'parents': [folder_id]},
                                            media_body=media,
                                            fields='id'
                                        ).execute()
                                        st.success(f"Archivo del Guacal {idx} subido correctamente")
                                    finally:
                                        # Asegurarse de eliminar el archivo temporal
                                        if os.path.exists(temp_creds_path):
                                            os.remove(temp_creds_path)
                                            
                                except Exception as token_error:
                                    st.error(f"Error al procesar el código: {str(token_error)}")
                                    st.stop()
                            else:
                                st.warning("Ingresa el código para continuar")
                                st.stop()
                        else:
                            raise shared_drive_error
                    
                    # Obtener el enlace de visualización directamente de la respuesta
                    public_url = uploaded_file.get('webViewLink', f"https://drive.google.com/file/d/{uploaded_file['id']}/view")
                    row.append(public_url)
                    st.success(f"Foto del Guacal {idx} subida correctamente")
                except Exception as upload_error:
                    st.error(f"Error al subir la foto del Guacal {idx}: {str(upload_error)}")
                    row.append("Error al subir foto")
                    if "PERMISSION_DENIED" in str(upload_error):
                        st.error("Error de permisos. Asegúrate de que la cuenta tenga acceso a la carpeta de destino.")
            else:
                row.append("Sin foto")
        sheet.append_row(row)
        st.success("Despacho guardado correctamente.")
        st.info("Las fotos han sido subidas a Google Drive y el enlace está disponible en la hoja.")
