import streamlit as st

# Función de utilidad para manipular session_state de forma segura
def set_session_state(key, value):
    """Establece un valor en session_state de forma segura, manejando excepciones"""
    try:
        st.session_state[key] = value
        return True
    except Exception as e:
        st.warning(f"Error al establecer {key} en session_state: {e}")
        return False
        
def get_session_state(key, default=None):
    """Obtiene un valor de session_state de forma segura, manejando excepciones"""
    try:
        return st.session_state.get(key, default)
    except Exception as e:
        st.warning(f"Error al obtener {key} de session_state: {e}")
        return default

# Configurar el título de la página que aparece en la pestaña del navegador
st.set_page_config(
    page_title="Dispatch TEKPRO",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="auto"
)

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
.item-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
}
.item-table th, .item-table td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}
.item-table th {
    background-color: #e6f7f7;
    color: #1db6b6;
}
.item-table tr:nth-child(even){
    background-color: #f9f9f9;
}
.add-item-section {
    background-color: #f8f9fa;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
    border: 1px solid #e9ecef;
}
.add-item-section h4 {
    margin-top: 0;
    color: #1db6b6;
    margin-bottom: 15px;
}
.search-results {
    max-height: 200px;
    overflow-y: auto;
    border: 1px solid #e9ecef;
    border-radius: 5px;
    margin-top: 10px;
    margin-bottom: 15px;
}
.search-item {
    padding: 8px 12px;
    border-bottom: 1px solid #e9ecef;
    cursor: pointer;
}
.search-item:hover {
    background-color: #f2f2f2;
}
.search-item.selected {
    background-color: #e6f7f7;
}
.search-highlight {
    background-color: #ffff99;
    font-weight: bold;
}
.remove-item-btn {
    color: #ff4b4b;
    cursor: pointer;
    font-weight: bold;
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
from streamlit_drawable_canvas import st_canvas
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import json


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
    import urllib.parse
    
    # El redirect URI DEBE coincidir exactamente con el registrado en
    # Google Cloud Console. Para Streamlit Cloud, usa la versión CON barra final.
    redirect_uri = st.secrets.get("REDIRECT_URI", "https://dispatchtekpro.streamlit.app/")
    
    st.info("ℹ️ **Verifica en Google Cloud Console:**\n"
            f"El redirect URI debe ser EXACTAMENTE: `{redirect_uri}`\n"
            f"(procura que coincida precisamente, incluyendo la barra final)")

    # Crear flow con manejo de errores
    try:
        flow = Flow.from_client_config(
            {"web": dict(st.secrets.oauth2)},
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    except Exception as e:
        st.error(f"Error al crear el Flow de autenticación: {e}")
        st.error("Verifica que `oauth2` esté correctamente configurado en st.secrets")
        st.stop()
        return
    
    auth_url, _ = flow.authorization_url(
        prompt='consent', 
        access_type='offline', 
        include_granted_scopes='true'
    )
    
    st.markdown(f"## [👉 Haz clic aquí para autorizar con Google Drive]({auth_url})")
    st.markdown("""
    ⏱️ **IMPORTANTE:** El código de autorización expira en ~10 minutos.  
    1. Haz clic en el enlace de arriba
    2. Autoriza el acceso a Google Drive
    3. **INMEDIATAMENTE** copia la URL completa a la que fuiste redirigido
    4. Pégala abajo y valida antes de que expire
    """, unsafe_allow_html=True)
    
    # Input para pegar la URL
    url_input = st.text_input(
        "📋 Pega aquí la URL de redirección completa:", 
        key="oauth_url_input",
        placeholder="https://ejemplo.com/?code=..." 
    )
    
    # parse URL or allow manual code input
    auth_code = ""
    error_message = None
    
    if url_input:
        try:
            parsed = urllib.parse.urlparse(url_input)
            params = urllib.parse.parse_qs(parsed.query)
            auth_code = params.get("code", [""])[0]
            st.text(f"redirect_uri usado por Flow: {redirect_uri}")
            if auth_code:
                st.success("✅ Código detectado automáticamente.")
            else:
                error_message = (
                    "❌ No se encontró el parámetro 'code' en la URL.\n\n" 
                    "Verifica que:"
                    "- Copiaste la URL completa (incluyendo '?code=...')"
                    "- No eliminaste caracteres al pegar"
                )
                st.warning(error_message)
        except Exception as e:
            error_message = f"Error al procesar la URL: {e}"
            st.error(error_message)
    
    # Si no se detectó código, permitir la entrada manual
    if not auth_code:
        manual_input = st.text_input("O ingresa manualmente el código aquí:", key="manual_code_input")
        if manual_input and not auth_code:
            auth_code = manual_input.strip()
            if auth_code:
                st.success("✅ Código manual ingresado. Presiona Validar código.")

    # Botón para validar el código
    if st.button("✓ Validar código", key="validar_codigo_oauth"):
        if not auth_code:
            st.error("⚠️ Debes proporcionar un código válido (a través de la URL o manualmente).")
            st.stop()
            return

        with st.spinner("Intercambiando código por token..."):
            try:
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
                st.session_state['drive_oauth_token'] = creds.to_json()
                st.success("🎉 ¡Autorización exitosa! Refresca la página para continuar.")
                st.balloons()
                import time
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error("❌ Error al intercambiar el código")
                error_details = str(e)
                # print raw error
                st.write("🧾 Error completo:", error_details)
                if "invalid_grant" in error_details:
                    st.error(
                        "**Causas frecuentes de invalid_grant:**\n"
                        "• Código expirado (~10 min)\n"
                        "• Código ya usado\n"
                        "• redirect_uri incorrecto"
                    )
                    st.warning("Vuelve a obtener un nuevo código desde el enlace y pégalo rápidamente.")
                elif "redirect_uri" in error_details.lower():
                    st.error(
                        "**redirect_uri mal configurado**\n"
                        f"Debe coincidir EXACTAMENTE con `{redirect_uri}` y con lo registrado en Google Cloud.")
                if hasattr(e, "response"):
                    try:
                        with st.expander("Detalles técnicos de la respuesta"):
                            st.text(e.response.content)
                    except Exception:
                        pass
    
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

# Función para enviar correo electrónico
def enviar_correo(destinatario, asunto, mensaje):
    try:
        # Obtener credenciales del correo desde los secretos
        correo_remitente = st.secrets.email_config.EMAIL
        password = st.secrets.email_config.PASSWORD
        smtp_server = st.secrets.email_config.SMTP_SERVER
        smtp_port = st.secrets.email_config.SMTP_PORT
        
        # Mostrar información de depuración (sin mostrar la contraseña)
        st.info(f"Intentando enviar correo desde {correo_remitente} vía {smtp_server}:{smtp_port}")
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = correo_remitente
        msg['To'] = destinatario
        msg['Subject'] = asunto
        
        # Agregar cuerpo del mensaje
        msg.attach(MIMEText(mensaje, 'html'))
        
        # Iniciar sesión en el servidor SMTP y enviar el correo
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()  # Algunos servidores requieren un segundo EHLO después de STARTTLS
                server.login(correo_remitente, password)
                server.send_message(msg)
            return True, "Correo enviado correctamente"
        except smtplib.SMTPAuthenticationError:
            return False, """Error de autenticación SMTP. Si estás usando Gmail, necesitas:
            1. Habilitar la verificación en dos pasos en tu cuenta Google
            2. Crear una 'Contraseña de aplicación' específica para esta aplicación
            3. Usar esa contraseña en lugar de tu contraseña normal
            
            Puedes crear una contraseña de aplicación aquí:
            https://myaccount.google.com/apppasswords"""
        except smtplib.SMTPException as smtp_error:
            return False, f"Error SMTP: {str(smtp_error)}"
        
    except Exception as e:
        return False, f"Error al enviar correo: {str(e)}"

def main():
    # Importar datetime al inicio de la función main
    import datetime

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
        
        # Función para asegurar que los encabezados estén correctamente configurados
        def setup_lista_empaque_headers():
            try:
                # Intentar abrir la hoja
                empaque_sheet = sheet_client.open(file_name).worksheet(worksheet_name)
                empaque_values = empaque_sheet.get_all_values()
                
                # Definir los encabezados exactos como deberían aparecer en la hoja
                headers = [
                    "OP", 
                    "Fecha", 
                    "Cliente", 
                    "Equipo", 
                    "Encargado logística", 
                    "Número de guacales",
                    "Descripción general",
                    "Observaciones"
                ]
                
                # Si la hoja está vacía o los encabezados no coinciden, establecer los encabezados
                if not empaque_values or empaque_values[0] != headers:
                    empaque_sheet.clear()  # Limpiar la hoja
                    empaque_sheet.update('A1', [headers])  # Actualizar encabezados
                    
                    # Formatear encabezados (negrita, centrado, fondo de color)
                    header_format = {
                        "textFormat": {"bold": True},
                        "horizontalAlignment": "CENTER",
                        "backgroundColor": {"red": 0.114, "green": 0.714, "blue": 0.714}  # Color #1DB6B6
                    }
                    
                    # Crear el formato para las celdas de encabezado
                    header_range = f'A1:{chr(64 + len(headers))}1'  # Rango desde A1 hasta la última columna
                    empaque_sheet.format(header_range, {"textFormat": {"bold": True}, "horizontalAlignment": "CENTER"})
                    
                    st.success("Encabezados de Lista de Empaque configurados correctamente.")
                
                return headers
            except Exception as e:
                st.error(f"Error al configurar encabezados: {str(e)}")
                return None
        
        # Asegurar que los encabezados estén configurados
        lista_empaque_headers = setup_lista_empaque_headers()

        # Leer órdenes de pedido existentes desde actas diligenciadas
        ordenes_list = []
        try:
            diligenciadas_sheet = sheet_client.open(file_name).worksheet("actas de entregas diligenciadas")
            diligenciadas_rows = diligenciadas_sheet.get_all_values()
            if diligenciadas_rows:
                diligenciadas_headers = [h.strip().lower() for h in diligenciadas_rows[0]]
                op_dili_idx = None
                for idx, h in enumerate(diligenciadas_headers):
                    if "op dili" in h:
                        op_dili_idx = idx
                        break
                
                if op_dili_idx is not None:
                    for row in diligenciadas_rows[1:]:
                        if len(row) > op_dili_idx and row[op_dili_idx].strip():
                            ordenes_list.append(row[op_dili_idx].strip())
        except Exception as e:
            st.warning(f"No se pudieron cargar las actas: {e}")
        except Exception:
            ordenes_list = []

        st.markdown("<b>Selecciona la orden de pedido:</b>", unsafe_allow_html=True)
        orden_pedido_val = st.selectbox(
            "OP:",
            ["SELECCIONA"] + (ordenes_list if ordenes_list else []),
            key="orden_pedido_selectbox"
        )
        
        # Obtener información básica de la OP seleccionada
        auto_cliente = ""
        auto_equipo = ""
        articulos_presentes = []
        diligenciadas_headers = []
        row_acta = []
        
        if orden_pedido_val and orden_pedido_val != "SELECCIONA":
            try:
                diligenciadas_sheet = sheet_client.open(file_name).worksheet("actas de entregas diligenciadas")
                diligenciadas_rows = diligenciadas_sheet.get_all_values()
                if diligenciadas_rows:
                    diligenciadas_headers = [h.strip().lower() for h in diligenciadas_rows[0]]
                    headers_dili = diligenciadas_headers
                    cliente_idx = headers_dili.index("cliente dili") if "cliente dili" in headers_dili else None
                    equipo_idx = headers_dili.index("equipo dili") if "equipo dili" in headers_dili else None
                    op_idx = headers_dili.index("op dili") if "op dili" in headers_dili else None
                    
                    if op_idx is not None:
                        for row in diligenciadas_rows[1:]:
                            if len(row) > op_idx and row[op_idx].strip() == orden_pedido_val:
                                row_acta = row
                                if cliente_idx is not None and len(row) > cliente_idx:
                                    auto_cliente = row[cliente_idx]
                                if equipo_idx is not None and len(row) > equipo_idx:
                                    auto_equipo = row[equipo_idx]
                                
                                # Obtener artículos presentes desde el acta
                                # Buscar columnas que contengan estos términos (más flexible)
                                articulos_busqueda = {
                                    "motor": "Motores",
                                    "reductor": "Reductor",
                                    "bomba": "Bomba",
                                    "turbina": "Turbina",
                                    "quemador": "Quemador",
                                    "vacio": "Bomba De Vacio",
                                    "compresor": "Compresor",
                                    "otros elementos": "Otros Elementos"
                                }
                                
                                for idx_col, header in enumerate(headers_dili):
                                    for busqueda, nombre_articulo in articulos_busqueda.items():
                                        # Verificar si el header contiene el término de búsqueda
                                        if busqueda in header and "dili" in header:
                                            # Verificar si el valor indica "Sí"
                                            if idx_col < len(row):
                                                valor = row[idx_col].strip().lower()
                                                if valor in ["si", "sí", "x", "1", "true", "yes"]:
                                                    if nombre_articulo not in articulos_presentes:
                                                        articulos_presentes.append(nombre_articulo)
                                            break
                                break
            except Exception as e:
                st.warning(f"Error al obtener información: {e}")

        # Mostrar información del cliente y equipo antes del formulario
        if orden_pedido_val and orden_pedido_val != "SELECCIONA" and auto_cliente:
            st.markdown(f"""
            <div style='background:#f7fafb; padding:1em; border-left:4px solid #1db6b6; border-radius:4px; margin-bottom:20px;'>
                <p style='margin:0; font-weight:bold; color:#1db6b6;'>Información del proyecto</p>
                <p style='margin:5px 0;'><b>Cliente:</b> {auto_cliente}</p>
                <p style='margin:5px 0;'><b>Equipo:</b> {auto_equipo if auto_equipo and auto_equipo != "Si" and auto_equipo != "Sí" else ""}</p>
            </div>
            """, unsafe_allow_html=True)

        # Formulario simplificado
        with st.form("lista_empaque_form"):
            fecha = st.date_input("Fecha del día", value=datetime.date.today())

            # Encargado almacén como selectbox con solo Andrea Ochoa
            encargado_almacen = st.selectbox(
                "Encargado almacén",
                ["", "Angela Zapata"]
            )
            

            # Encargado logística como selectbox con opciones específicas
            encargado_logistica = st.selectbox(
                "Encargado logística",
                ["", "Angela Zapata", "Jhon Restrepo", "Juan Rendon"]
            )
                       
            # Campo para firma de logística utilizando canvas
            st.markdown("<b>Firma encargado logística:</b>", unsafe_allow_html=True)
            firma_logistica = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=2,
                stroke_color="#1db6b6",
                background_color="#f7fafb",
                height=150,
                width=400,
                drawing_mode="freedraw",
                key="firma_canvas"
            )
            
            # Encargado ingeniería y diseño
            encargado_ingenieria = st.selectbox(
                "Encargado ingeniería y diseño",
                [
                    "",
                    "Alejandro Diaz",
                    "Juan David Martinez",
                    "Juan Andres Zapata",
                    "Daniel Valbuena",
                    "Victor Manuel Baena",
                    "Diomer Arbelaez",
                    "Jose Perez"
                ]
            )

            # Sección de artículos a empacar
            st.markdown("<b>Selecciona los artículos a empacar:</b>", unsafe_allow_html=True)
            
            articulos_seleccion = {}
            if not articulos_presentes:
                st.warning("No se encontraron artículos en el acta. Seleccione una OP válida.")
            else:
                st.info(f"Se encontraron {len(articulos_presentes)} artículos en el acta.")
                for art in articulos_presentes:
                    articulos_seleccion[art] = st.checkbox(art, value=True, key=f"empacar_{art}")
                    
                    # Si es 'Otros Elementos', mostrar la descripción registrada en el acta
                    if art.lower() == "otros elementos":
                        desc_otros = ""
                        for idx, h in enumerate(diligenciadas_headers):
                            if "descripcion otros elementos" in h.lower():
                                desc_otros = row_acta[idx] if idx < len(row_acta) else ""
                                break
                        if desc_otros and desc_otros.strip():
                            st.markdown(f"<div style='margin-left:2em; color:#6c757d; font-size:0.97em; background:#f7fafb; border-left:3px solid #1db6b6; padding:0.5em 1em; border-radius:6px; margin-bottom:0.5em;'><b>Descripción:</b> {desc_otros}</div>", unsafe_allow_html=True)

            st.markdown("<b>Paquetes (guacales):</b>", unsafe_allow_html=True)
            
            # Campo para observaciones
            observaciones = st.text_area("Observaciones adicionales")
            
            # Checkbox para enviar notificación
            enviar_notificacion = st.checkbox("Enviar notificación por correo al guardar", value=True)
            
            # Guardar los campos del formulario previo en session_state
            # para poder accederlos después del segundo formulario
            st.session_state['dispatch_form_fecha'] = fecha
            st.session_state['dispatch_form_encargado_almacen'] = encargado_almacen
            st.session_state['dispatch_form_encargado_logistica'] = encargado_logistica
            st.session_state['dispatch_form_firma_logistica'] = firma_logistica
            st.session_state['dispatch_form_observaciones'] = observaciones
            st.session_state['dispatch_form_enviar_notificacion'] = enviar_notificacion
            
            # Final del primer formulario
            form_part1_submitted = st.form_submit_button("Continuar a guacales")

        # Procesar solo si se ha enviado la primera parte del formulario
        if 'dispatch_form_fecha' in st.session_state:
            # Variables para almacenar guacales
            paquetes = []
            
            # Inicializar número de guacales si no existe
            if 'num_paquetes' not in st.session_state:
                st.session_state['num_paquetes'] = 1
            
            # Verificar si es necesario hacer un rerun
            if 'need_rerun' in st.session_state and st.session_state['need_rerun']:
                st.session_state['need_rerun'] = False
                try:
                    st.rerun()
                except Exception as e:
                    st.warning(f"Error al reiniciar: {e}")
                    pass
                
            # Código para los guacales con subcampos
            for i in range(st.session_state['num_paquetes']):
                st.markdown(f"<b>Guacal {i+1}</b>", unsafe_allow_html=True)
                
                # Campo de descripción general del guacal
                desc_guacal = st.text_area(f"Descripción general del guacal {i+1}", key=f"desc_guacal_{i+1}", placeholder="Describa el contenido del guacal...")
                
                # Crear un campo de observaciones adicionales para el guacal
                obs_guacal = st.text_area(f"Observaciones adicionales del guacal {i+1}", key=f"obs_guacal_{i+1}")
                
                # Campo para subir fotos del guacal
                fotos = st.file_uploader(f"Fotos guacal {i+1}", type=["jpg", "jpeg", "png"], key=f"fotos_paquete_{i+1}", accept_multiple_files=True)
                
                # Guardar información completa del guacal
                paquetes.append({
                    "desc": desc_guacal,
                    "obs": obs_guacal,
                    "fotos": fotos
                })
            
            # Botón para agregar más guacales (fuera del formulario)
            if st.button("Agregar otro guacal", key="btn_add_guacal"):
                st.session_state['num_paquetes'] += 1
                st.session_state['need_rerun'] = True
            
            # Segundo formulario para continuar con el proceso
            with st.form("dispatch_form_part2"):
                # Recuperar valores del primer formulario desde session_state
                try:
                    if 'dispatch_form_fecha' in st.session_state:
                        fecha = st.session_state['dispatch_form_fecha']
                        encargado_almacen = st.session_state['dispatch_form_encargado_almacen']
                        encargado_logistica = st.session_state['dispatch_form_encargado_logistica']
                        firma_logistica = st.session_state['dispatch_form_firma_logistica']
                        observaciones = st.session_state['dispatch_form_observaciones']
                        enviar_notificacion = st.session_state['dispatch_form_enviar_notificacion']
                except Exception as e:
                    st.error(f"Error al recuperar datos del formulario: {str(e)}")

                # Confirmar observaciones para este formulario
                final_observaciones = st.text_area("Confirmar observaciones", value=observaciones if 'dispatch_form_observaciones' in st.session_state else "", key="final_observaciones")
                
                # Actualizar observaciones con el valor final
                observaciones = final_observaciones
                
                # Añadir opción para enviar notificación por correo
                final_notificacion = st.checkbox("Enviar notificación por correo al guardar", value=enviar_notificacion if 'dispatch_form_enviar_notificacion' in st.session_state else True, key="final_notificacion")
                
                # Actualizar la opción de notificación
                enviar_notificacion = final_notificacion
                
                if enviar_notificacion:
                    st.markdown("<small>Se enviará un correo automático a coordinadorinventarios@tekpro.com.co notificando del despacho realizado.</small>", unsafe_allow_html=True)
                
                submitted = st.form_submit_button("Guardar despacho")

            if submitted:
                # Validar que todos los campos requeridos estén completos
                error_validacion = False
                mensajes_error = []
                
                # Validar campos obligatorios (excepto observaciones)
                if not orden_pedido_val or orden_pedido_val == "SELECCIONA":
                    mensajes_error.append("Debe seleccionar una orden de pedido válida")
                    error_validacion = True
                
                if not encargado_almacen:
                    mensajes_error.append("Debe seleccionar un encargado de almacén")
                    error_validacion = True
                
                if not encargado_logistica:
                    mensajes_error.append("Debe seleccionar un encargado de logística")
                    error_validacion = True
                
                if not encargado_ingenieria:
                    mensajes_error.append("Debe seleccionar un encargado de ingeniería y diseño")
                    error_validacion = True
                
                # Verificar si hay firma de logística
                if firma_logistica.image_data is None:
                    mensajes_error.append("Debe incluir la firma del encargado de logística")
                    error_validacion = True
                
                # Verificar que al menos un guacal tenga descripción y fotos
                guacales_completos = False
                for i, paquete in enumerate(paquetes):
                    # Verificar si hay descripción para este guacal
                    has_descripcion = paquete["desc"] and paquete["desc"].strip()
                    # Verificar si hay fotos para este guacal
                    has_fotos = paquete["fotos"] and len(paquete["fotos"]) > 0
                    
                    # Si este guacal tiene tanto descripción como fotos, marcarlo como completo
                    if has_descripcion and has_fotos:
                        guacales_completos = True
                        break
                
                if not guacales_completos:
                    mensajes_error.append("Al menos un guacal debe tener descripción y fotos.")
                    error_validacion = True
                
                # Obtener artículos enviados y no enviados
                enviados = [art for art, v in articulos_seleccion.items() if v]
                no_enviados = [art for art, v in articulos_seleccion.items() if not v]
                
                if articulos_presentes and not enviados:
                    mensajes_error.append("Debe seleccionar al menos un artículo para enviar")
                    error_validacion = True
                
                # Si hay errores de validación, mostrar y detener
                if error_validacion:
                    st.error("Por favor complete todos los campos obligatorios:")
                    for mensaje in mensajes_error:
                        st.warning(mensaje)
                    
                    # Sugerencias adicionales para ayudar al usuario
                    st.info("Sugerencias para solucionar los problemas:")
                    st.markdown("""
                    - Agregue una descripción del contenido del guacal
                    - Asegúrese de haber subido al menos una foto para el guacal
                    - Verifique que ha seleccionado al menos un artículo para enviar
                    - Complete todos los campos obligatorios (encargados y firma)
                    """)
                    return
                
                # Si la validación es exitosa, procedemos con el guardado
                # Estructura del array según los encabezados de la hoja:
                row = [
                    orden_pedido_val,                # Op
                    str(fecha),                      # Fecha
                    auto_cliente,                    # Cliente
                    auto_equipo,                     # Equipo
                    encargado_almacen,               # Encargado almacén
                    encargado_ingenieria,            # Encargado ingeniería y diseño
                    encargado_logistica,             # Encargado logística
                    "",                              # Firma encargado logística (vacío por ahora)
                    observaciones,                   # Observaciones adicionales
                    ", ".join(enviados),             # Artículos enviados
                    ", ".join(no_enviados),          # Artículos no enviados
                ]
                # Procesar firma si está disponible
                firma_imagen = None
                if firma_logistica.image_data is not None:
                    import base64
                    from PIL import Image
                    import io
                    
                    # Convertir la imagen a bytes para subirla
                    firma_image = Image.fromarray(firma_logistica.image_data.astype('uint8'))
                    buffer = io.BytesIO()
                    firma_image.save(buffer, format="PNG")
                    buffer.seek(0)
                    
                    # Subir la firma a Google Drive
                    try:
                        image_filename = f"Firma_{orden_pedido_val}.png"
                        public_url = upload_image_to_drive_oauth(buffer, image_filename, folder_id)
                        row[7] = public_url  # Actualizar la posición de la firma en el array
                        st.success("Firma subida correctamente")
                    except Exception as upload_error:
                        st.error(f"Error al subir la firma: {str(upload_error)}")
                
                # Completar el arreglo con guacales (para mantener la estructura de encabezados)
                for idx, paquete in enumerate(paquetes, start=1):
                    # Preparar el texto descriptivo del guacal
                    guacal_descripcion = paquete["desc"] if paquete["desc"] else ""
                    
                    # Añadir observaciones si existen
                    if paquete["obs"] and paquete["obs"].strip():
                        if guacal_descripcion:
                            guacal_descripcion += f"\n\nObservaciones: {paquete['obs']}"
                        else:
                            guacal_descripcion = f"Observaciones: {paquete['obs']}"
                    
                    # Agregar descripción del guacal
                    row.append(guacal_descripcion)  # Descripción Guacal n
                    
                    # Procesar y agregar fotos del guacal
                    enlaces = []
                    if paquete["fotos"]:
                        for n, foto in enumerate(paquete["fotos"], start=1):
                            try:
                                image_filename = f"Guacal_{orden_pedido_val}_{idx}_{n}.jpg"
                                file_stream = io.BytesIO(foto.read())
                                public_url = upload_image_to_drive_oauth(file_stream, image_filename, folder_id)
                                enlaces.append(public_url)
                                st.success(f"Foto {n} de guacal {idx} subida correctamente")
                            except Exception as upload_error:
                                st.error(f"Error al subir la foto {n} de guacal {idx}: {str(upload_error)}")
                        
                        # Agregar enlaces de fotos
                        if enlaces:
                            row.append(", ".join(enlaces))  # Fotos Guacal n
                        else:
                            row.append("Error al subir foto")
                    else:
                        row.append("Sin foto")
                
                # Completar con guacales vacíos hasta llegar a 7 (si es necesario)
                remaining_guacales = 7 - len(paquetes)
                for _ in range(remaining_guacales):
                    row.append("")  # Descripción Guacal vacío
                    row.append("")  # Fotos Guacal vacío
                
                # Escribir fila completa en la hoja
                write_link_to_sheet(sheet_client, file_name, worksheet_name, row)
                st.success("Despacho guardado correctamente.")
                st.info("Las fotos han sido subidas a Google Drive y el enlace está disponible en la hoja.")
                
                # Envío automático de correo electrónico si el checkbox está seleccionado
                if enviar_notificacion:
                    try:
                        email_destinatario = "coordinadorinventarios@tekpro.com.co"
                        asunto = f"Lista de Empaque completada - OP: {orden_pedido_val}"
                        
                        # Obtener lista de guacales con descripción
                        guacales_texto = ""
                        guacales_con_contenido = 0
                        for idx, paquete in enumerate(paquetes, start=1):
                            if paquete["desc"]:
                                guacales_con_contenido += 1
                                # Formateamos el contenido para el email con HTML
                                obs_html = f"<div style='margin-top:5px;'><em>Observaciones: {paquete['obs']}</em></div>" if paquete.get('obs') else ""
                                
                                guacales_texto += f"""<li>
                                    <strong>Guacal {idx}:</strong> 
                                    <div>{paquete['desc']}</div>
                                    {obs_html}
                                </li>"""
                        
                        mensaje = f"""
                        <html>
                        <body>
                            <div style="border-left: 5px solid #1db6b6; padding-left: 15px;">
                                <h2 style="color: #1db6b6;">Notificación de Lista de Empaque</h2>
                                <p>Se ha completado la lista de empaque con la siguiente información:</p>
                                <ul>
                                    <li><strong>OP:</strong> {orden_pedido_val}</li>
                                    <li><strong>Cliente:</strong> {auto_cliente}</li>
                                    <li><strong>Equipo:</strong> {auto_equipo}</li>
                                    <li><strong>Fecha:</strong> {fecha}</li>
                                </ul>
                                <p><strong>Encargado Almacén:</strong> {encargado_almacen}</p>
                                <p><strong>Encargado Logística:</strong> {encargado_logistica}</p>
                                <p><strong>Encargado Ingeniería:</strong> {encargado_ingenieria}</p>
                                
                                <p><strong>Artículos enviados ({len(enviados)}):</strong></p>
                                <ul>
                                    {"".join(f"<li>{art}</li>" for art in enviados) if enviados else "<li>Ninguno</li>"}
                                </ul>
                                
                                <p><strong>Guacales preparados ({guacales_con_contenido} de {len(paquetes)}):</strong></p>
                                <ul>
                                    {guacales_texto}
                                </ul>
                                
                                <p><strong>Observaciones:</strong> {observaciones}</p>
                                
                                <p>Esta es una notificación automática del sistema Dispatch Tekpro.</p>
                            </div>
                        </body>
                        </html>
                        """
                        
                        exito, mensaje_resultado = enviar_correo(email_destinatario, asunto, mensaje)
                        if exito:
                            st.success(f"Se ha enviado una notificación por correo a {email_destinatario}")
                        else:
                            st.warning(f"No se pudo enviar la notificación por correo: {mensaje_resultado}")
                    except Exception as e:
                        st.warning(f"Error al enviar correo: {str(e)}")


    elif opcion_menu == "ACTA DE ENTREGA":
        # Autorización Google Drive OAuth2 igual que en LISTA DE EMPAQUE
        if 'drive_oauth_token' not in st.session_state:
            authorize_drive_oauth()

        st.markdown("<h3 style='color:#1db6b6;'>ACTA DE ENTREGA</h3>", unsafe_allow_html=True)

        with st.expander("Datos Generales del Proyecto", expanded=True):
            st.markdown("""
                <div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;border-top: 3px solid #1db6b6;'>
                <b style='font-size:1.1em;color:#1db6b6'>Información Principal</b>
            """, unsafe_allow_html=True)
            # --- DATOS GENERALES ---
            auto_cliente = ""
            auto_equipo = ""
            auto_item = ""
            auto_cantidad = ""
            auto_fecha = datetime.date.today()
            op_options = []
            op_to_row = {}
            try:
                # Asegurarse de que sheet_client está inicializado
                creds = get_service_account_creds()
                sheet_client = gspread.authorize(creds)
                file_name = st.secrets.drive_config.FILE_NAME
                worksheet_name = "Acta de entrega" # Asegúrate que este es el worksheet correcto para las OPs
                
                sheet = sheet_client.open(file_name).worksheet(worksheet_name)
                all_rows = sheet.get_all_values()
                
                # Obtener OPs ya diligenciadas para filtrarlas
                ops_diligenciadas = set()
                try:
                    diligenciadas_sheet = sheet_client.open(file_name).worksheet("actas de entregas diligenciadas")
                    diligenciadas_rows = diligenciadas_sheet.get_all_values()
                    if diligenciadas_rows:
                        diligenciadas_headers = [h.strip().lower() for h in diligenciadas_rows[0]]
                        op_dili_idx = None
                        for idx, h in enumerate(diligenciadas_headers):
                            if "op dili" in h:
                                op_dili_idx = idx
                                break
                        
                        if op_dili_idx is not None:
                            for row in diligenciadas_rows[1:]:
                                if len(row) > op_dili_idx and row[op_dili_idx].strip():
                                    ops_diligenciadas.add(row[op_dili_idx].strip())
                except Exception as e:
                    st.warning(f"No se pudieron cargar las actas de entrega diligenciadas: {e}")
                
                # Condicional más explícito siguiendo el patrón solicitado
                if all_rows:
                    headers = [h.strip().lower() for h in all_rows[0]]
                    op_idx = headers.index("op") if "op" in headers else None
                    for row in all_rows[1:]:
                        if op_idx is not None and len(row) > op_idx:
                            op_val = row[op_idx].strip()
                            if op_val:
                                # If: Si está en "actas de entregas diligenciadas", que no aparezca en la barra
                                if op_val in ops_diligenciadas:
                                    # No añadir a opciones (se omite)
                                    pass
                                # Else: Si está en "acta de entrega", que aparezca en la barra
                                else:
                                    op_options.append(op_val)
                                    op_to_row[op_val] = row
            except Exception as e:
                st.warning(f"No se pudieron cargar las órdenes de pedido existentes: {e}")
                pass

            # Inicializar una sesión para detectar cambios en la OP seleccionada
            if 'previous_op' not in st.session_state:
                st.session_state['previous_op'] = ""
            
            # Inicializar bandera para reinicio
            if 'need_rerun' not in st.session_state:
                st.session_state['need_rerun'] = False
                
            # Callback para resetear los campos cuando cambia la OP
            def on_op_change():
                if st.session_state['previous_op'] != st.session_state['op_selector']:
                    # Limpiar todos los checkbox de selección
                    for key in list(st.session_state.keys()):
                        # Limpiar checkboxes de mostrar elementos
                        if key.startswith('cb_mostrar_'):
                            st.session_state[key.replace('cb_', '')] = False
                        
                        # Limpiar todos los file uploaders y campos de formulario
                        if key.startswith('fotos_') or key.startswith('foto_'):
                            if key in st.session_state:
                                del st.session_state[key]
                                
                        # Limpiar campos de texto del formulario
                        if key.startswith('descripcion_') or key.startswith('tension_'):
                            if key in st.session_state:
                                del st.session_state[key]
                                
                        # Limpiar selectboxes
                        if key.startswith('select_'):
                            if key in st.session_state:
                                del st.session_state[key]
                    
                    # Limpiar campos específicos del formulario
                    campos_a_limpiar = ['revision_soldadura', 'revision_sentidos', 
                                      'manual_funcionamiento', 'revision_filos', 
                                      'revision_tratamientos', 'revision_tornilleria',
                                      'revision_ruidos', 'ensayo_equipo', 
                                      'observaciones_generales', 'lider_inspeccion',
                                      'encargado_soldador', 'disenador']
                    
                    for campo in campos_a_limpiar:
                        if campo in st.session_state:
                            del st.session_state[campo]
                    
                    # Actualizar el estado previo
                    st.session_state['previous_op'] = st.session_state['op_selector']
                    
                    # Establecer bandera para reinicio
                    st.session_state['need_rerun'] = True

            op_selected = st.selectbox("Orden de Pedido (OP)", 
                options=["SELECCIONA"] + list(set(op_options)),
                key="op_selector",
                on_change=on_op_change)
            
            # Mostrar mensaje informativo si no se ha seleccionado una OP
            if op_selected == "SELECCIONA":
                st.info("ℹ️ **Debe seleccionar una Orden de Pedido para continuar.** Los datos se cargarán automáticamente al seleccionar una OP.")
            
            # Actualizar el estado previo si no cambia
            if st.session_state['previous_op'] != op_selected:
                st.session_state['previous_op'] = op_selected
                
            # Verificar si es necesario reiniciar la página
            if st.session_state.get('need_rerun', False):
                st.session_state['need_rerun'] = False
                st.rerun()
            
            if op_selected != "SELECCIONA":
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

            cliente = st.text_input("Cliente", value=auto_cliente)
            # OP se almacena internamente pero no se muestra en la interfaz
            op = op_selected
            equipo = st.text_input("Equipo", value=auto_equipo)
            item = st.text_input("Ítem", value=auto_item)
            cantidad = st.text_input("Cantidad", value=auto_cantidad)
            fecha = st.date_input("Fecha", value=auto_fecha, key="fecha_acta")
            st.markdown("</div>", unsafe_allow_html=True)
        
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        folder_id = st.secrets.drive_config.FOLDER_ID
        file_name = st.secrets.drive_config.FILE_NAME
        worksheet_name = "Acta de entrega"
       
        # --- INFORMACIÓN GENERAL DEL EQUIPO ---
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Información General del Equipo")

        # --- ESPACIO SOLO PARA LISTAS DE CHEQUEO HE INFOS ---
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

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Lista de chequeo general accesorios")
        botones_accesorios = [
            ("mostrar_manometros", "¿Hay manómetros?"),
            ("mostrar_vacuometros", "¿Hay vacuómetros?"),
            ("mostrar_valvulas", "¿Hay válvulas?"),
            ("mostrar_mangueras", "¿Hay mangueras?"),
            ("mostrar_boquillas", "¿Hay boquillas?"),
            ("mostrar_reguladores", "¿Hay reguladores aire/gas?"),
            ("mostrar_tuberia", "¿Hay tubería?"),
            ("mostrar_cables", "¿Hay cables?"),
            ("mostrar_curvas", "¿Hay curvas?"),
            ("mostrar_tornilleria_acc", "¿Hay tornillería?")
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




        with st.form("acta_entrega_form"):
            
            # --- INFORMACIÓN GENERAL DEL EQUIPO DENTRO DEL FORMULARIO PRINCIPAL ---
            st.markdown("### Información General del Equipo")
            st.markdown("""
                <div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;border-top: 3px solid #1db6b6;'>
                <b style='font-size:1.1em;color:#1db6b6'>Descripción y Foto General</b>
            """, unsafe_allow_html=True)
            
            # Utilizamos la clave única para cada OP
            form_key_suffix = f"_{op}" if op else "_new"
            descripcion_general = st.text_area(
                "Descripción general del equipo", 
                key=f"descripcion_general{form_key_suffix}"
            )
            fotos_generales = st.file_uploader(
                "Foto general del equipo", 
                type=["jpg","jpeg","png"], 
                accept_multiple_files=True,
                key=f"fotos_generales{form_key_suffix}"
            )
            
            st.markdown("</div>", unsafe_allow_html=True)

            # --- Secciones visuales para cada artículo ---
            def seccion_articulo(nombre, mostrar, campos):
                if mostrar:
                    with st.expander(f"{nombre}", expanded=False):
                        st.markdown(f"""
                            <div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;border-top: 3px solid #1db6b6;'>
                            <b style='font-size:1.1em;color:#1db6b6'>{nombre}</b>
                        """, unsafe_allow_html=True)
                        resultados = {}
                        # Crear un sufijo único para las claves basado en la OP actual
                        key_suffix = f"_{op}" if op else "_new"
                        
                        for campo in campos:
                            if campo['tipo'] == 'number':
                                resultados[campo['nombre']] = st.number_input(
                                    campo['label'], 
                                    min_value=0, 
                                    step=1, 
                                    format="%d",
                                    key=f"{campo['nombre']}{key_suffix}"
                                )
                            elif campo['tipo'] == 'text':
                                resultados[campo['nombre']] = st.text_input(
                                    campo['label'],
                                    key=f"{campo['nombre']}{key_suffix}"
                                )
                            elif campo['tipo'] == 'text_area':
                                resultados[campo['nombre']] = st.text_area(
                                    campo['label'],
                                    key=f"{campo['nombre']}{key_suffix}"
                                )
                            elif campo['tipo'] == 'file':
                                resultados[campo['nombre']] = st.file_uploader(
                                    campo['label'], 
                                    type=["jpg","jpeg","png"], 
                                    accept_multiple_files=True, 
                                    key=f"fotos_{nombre}{key_suffix}"
                                )
                            elif campo['tipo'] == 'select':
                                if 'opciones' in campo:
                                    resultados[campo['nombre']] = st.selectbox(
                                        campo['label'], 
                                        campo['opciones'], 
                                        key=f"select_{campo['nombre']}{key_suffix}"
                                    )
                                else:
                                    resultados[campo['nombre']] = st.selectbox(
                                        campo['label'], 
                                        ["", "Opción 1", "Opción 2"], 
                                        key=f"select_{campo['nombre']}{key_suffix}"
                                    )
                        st.markdown("</div>", unsafe_allow_html=True)
                        return resultados
                else:
                    return {campo['nombre']: 0 if campo['tipo'] == 'number' else "" for campo in campos}            # --- Agrupación por listas de chequeo principales ---
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
                    {'nombre': 'tipo_combustible_quemador', 'label': 'Tipo combustible quemador', 'tipo': 'select', 'opciones': ["", "ACPM", "GAS"]},
                    {'nombre': 'metodo_uso_quemador', 'label': 'Método de uso quemador', 'tipo': 'text'},
                    {'nombre': 'foto_quemador', 'label': 'Foto quemador', 'tipo': 'file'}
                ]
                quemador = seccion_articulo("Quemador", st.session_state.get('mostrar_quemador', False), quemador_campos)
                voltaje_quemador = quemador['voltaje_quemador']
                tipo_combustible_quemador = quemador.get('tipo_combustible_quemador', "")
                metodo_uso_quemador = quemador.get('metodo_uso_quemador', "")
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

                tuberia_campos = [
                    {'nombre': 'descripcion_tuberia', 'label': 'Descripción tubería', 'tipo': 'text_area'},
                    {'nombre': 'foto_tuberia', 'label': 'Foto tubería', 'tipo': 'file'}
                ]
                tuberia = seccion_articulo("Tubería", st.session_state.get('mostrar_tuberia', False), tuberia_campos)
                descripcion_tuberia = tuberia.get('descripcion_tuberia', "")
                foto_tuberia = tuberia.get('foto_tuberia', "")

                cables_campos = [
                    {'nombre': 'descripcion_cables', 'label': 'Descripción cables', 'tipo': 'text_area'},
                    {'nombre': 'foto_cables', 'label': 'Foto cables', 'tipo': 'file'}
                ]
                cables = seccion_articulo("Cables", st.session_state.get('mostrar_cables', False), cables_campos)
                descripcion_cables = cables.get('descripcion_cables', "")
                foto_cables = cables.get('foto_cables', "")

                curvas_campos = [
                    {'nombre': 'descripcion_curvas', 'label': 'Descripción curvas', 'tipo': 'text_area'},
                    {'nombre': 'foto_curvas', 'label': 'Foto curvas', 'tipo': 'file'}
                ]
                curvas = seccion_articulo("Curvas", st.session_state.get('mostrar_curvas', False), curvas_campos)
                descripcion_curvas = curvas.get('descripcion_curvas', "")
                foto_curvas = curvas.get('foto_curvas', "")

                tornilleria_acc_campos = [
                    {'nombre': 'descripcion_tornilleria', 'label': 'Descripción tornillería', 'tipo': 'text_area'},
                    {'nombre': 'foto_tornilleria', 'label': 'Foto tornillería', 'tipo': 'file'}
                ]
                tornilleria_acc = seccion_articulo("Tornillería", st.session_state.get('mostrar_tornilleria_acc', False), tornilleria_acc_campos)
                descripcion_tornilleria = tornilleria_acc.get('descripcion_tornilleria', "")
                foto_tornilleria = tornilleria_acc.get('foto_tornilleria', "")

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
                # Usar clave única basada en OP
                key_suffix = f"_{op}" if op else "_new"
                otros_elementos = st.text_area(
                    "Otros Elementos", 
                    key=f"otros_elementos{key_suffix}"
                )
            with col_otros2:
                fotos_otros_elementos = st.file_uploader(
                    "Fotos Otros Elementos", 
                    type=["jpg","jpeg","png"], 
                    accept_multiple_files=True, 
                    key=f"fotos_otros_elementos{key_suffix}"
                )
            st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin: 1.5em 0;'>", unsafe_allow_html=True)
            st.markdown("<b>Preguntas de revisión (Sí/No)</b>", unsafe_allow_html=True)
            revision_soldadura = st.selectbox(
                "Revisión de soldadura", 
                ["", "Sí", "No"], 
                key=f"revision_soldadura{key_suffix}"
            )
            revision_sentidos = st.selectbox(
                "Revisión de sentidos de giro", 
                ["", "Sí", "No"], 
                key=f"revision_sentidos{key_suffix}"
            )
            manual_funcionamiento = st.selectbox(
                "Manual de funcionamiento", 
                ["", "Sí", "No"], 
                key=f"manual_funcionamiento{key_suffix}"
            )
            revision_filos = st.selectbox(
                "Revisión de filos y acabados", 
                ["", "Sí", "No"], 
                key=f"revision_filos{key_suffix}"
            )
            revision_tratamientos = st.selectbox(
                "Revisión de tratamientos", 
                ["", "Sí", "No"], 
                key=f"revision_tratamientos{key_suffix}"
            )
            revision_tornilleria = st.selectbox(
                "Revisión de tornillería", 
                ["", "Sí", "No"], 
                key=f"revision_tornilleria{key_suffix}"
            )
            revision_ruidos = st.selectbox(
                "Revisión de ruidos", 
                ["", "Sí", "No"], 
                key=f"revision_ruidos{key_suffix}"
            )
            ensayo_equipo = st.selectbox(
                "Ensayo de equipo", 
                ["", "Sí", "No"], 
                key=f"ensayo_equipo{key_suffix}"
            )

            st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin: 1.5em 0;'>", unsafe_allow_html=True)
            st.markdown("<b>Información final</b>", unsafe_allow_html=True)
            observaciones_generales = st.text_area(
                "Observaciones generales",
                key=f"observaciones_generales{key_suffix}"
            )

            lider_inspeccion = st.selectbox(
                "Líder de inspección",
                ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata", "Juan David Martinez", "Victor Manuel Baena", "Diomer Arbelaez"],
                key=f"lider_inspeccion{key_suffix}"
            )
            encargado_soldador = st.selectbox(
                "Encargado de soldadura",
                ["", "Leudys Castillo", "Jaime Rincon", "Jaime Ramos", "Gabriel Garcia", "Jefferson Galindez", "Jeison Arboleda", "Octaviano Velasquez","Sebastian Zapata", "Katerine Padilla"],
                key=f"encargado_soldador{key_suffix}"
            )
            disenador = st.selectbox(
                "Diseñador",
                ["", "Daniel Valbuena", "Juan David Martinez", "Juan Andres Zapata", "Alejandro Diaz"],
                key=f"disenador{key_suffix}"
            )
            fecha_entrega = st.date_input("Fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta")

            # La notificación por correo se incluirá en el formulario como un checkbox
            enviar_notificacion = st.checkbox("Enviar notificación por correo al guardar", value=True)
            if enviar_notificacion:
                st.markdown("<small>Se enviará un correo automático a coordinadorinventarios@tekpro.com.co notificando del acta completada.</small>", unsafe_allow_html=True)

            # Crear columnas para los botones
            col1, col2 = st.columns(2)
            
            with col1:
                submitted = st.form_submit_button("Guardar acta de entrega", type="primary")
            
            with col2:
                limpiar = st.form_submit_button("Limpiar Acta", type="secondary")

            # Validación: solo encabezado y responsables son obligatorios

            # Manejar el botón limpiar
            if limpiar:
                # Limpiar todos los campos del session state relacionados con el formulario
                keys_to_clear = [
                    'op_selector', 'previous_op', 'need_rerun',
                    'mostrar_motores', 'mostrar_reductor', 'mostrar_bomba', 'mostrar_turbina',
                    'mostrar_quemador', 'mostrar_bomba_vacio', 'mostrar_compresor', 'mostrar_manometros',
                    'mostrar_vacuometros', 'mostrar_valvulas', 'mostrar_mangueras', 'mostrar_boquillas',
                    'mostrar_reguladores', 'mostrar_tuberia', 'mostrar_cables', 'mostrar_tornilleria',
                    'mostrar_curvas', 'mostrar_pinon1', 'mostrar_pinon2', 'mostrar_polea1', 'mostrar_polea2',
                    'mostrar_gabinete', 'mostrar_arrancadores', 'mostrar_control_nivel', 'mostrar_variadores',
                    'mostrar_sensores_temperatura', 'mostrar_toma_corriente', 'mostrar_otros_elementos'
                ]
                
                # Limpiar todas las keys del session state relacionadas con el formulario
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                
                # Limpiar también cualquier otra key que contenga datos del formulario
                keys_to_remove = []
                for key in st.session_state.keys():
                    if any(x in key.lower() for x in ['acta', 'motor', 'bomba', 'turbina', 'quemador', 'compresor', 
                                                     'manometro', 'vacuometro', 'valvula', 'manguera', 'boquilla',
                                                     'regulador', 'tuberia', 'cable', 'tornilleria', 'curva',
                                                     'pinon', 'polea', 'gabinete', 'arrancador', 'control', 
                                                     'variador', 'sensor', 'toma', 'otros']):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.success("✅ Todos los campos han sido limpiados exitosamente.")
                st.rerun()

            if submitted:
                # Validar que todos los campos de elementos seleccionados estén completos
                error_validacion = False
                mensajes_error = []

                # Función para validar componentes
                def validar_componente(mostrar_key, nombre_componente, campos_requeridos):
                    if st.session_state.get(mostrar_key, False):
                        for campo, valor in campos_requeridos.items():
                            if not valor:
                                return f"Falta completar '{campo}' para {nombre_componente}"
                    return None

                # Validar elementos electromecánicos
                if st.session_state.get('mostrar_motores', False):
                    if not cantidad_motores or not voltaje_motores or not fotos_motores:
                        mensajes_error.append("Complete todos los campos de Motores (cantidad, voltaje y fotos)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_reductor', False):
                    if not cantidad_reductores or not voltaje_reductores or not fotos_reductores:
                        mensajes_error.append("Complete todos los campos de Reductores (cantidad, voltaje y fotos)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_bomba', False):
                    if not cantidad_bombas or not voltaje_bombas or not fotos_bombas:
                        mensajes_error.append("Complete todos los campos de Bombas (cantidad, voltaje y fotos)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_turbina', False):
                    if not voltaje_turbina or not foto_turbina:
                        mensajes_error.append("Complete todos los campos de Turbina (voltaje y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_quemador', False):
                    if not voltaje_quemador or not tipo_combustible_quemador or not metodo_uso_quemador or not foto_quemador:
                        mensajes_error.append("Complete todos los campos de Quemador (voltaje, tipo de combustible, método de uso y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_bomba_vacio', False):
                    if not voltaje_bomba_vacio or not foto_bomba_vacio:
                        mensajes_error.append("Complete todos los campos de Bomba de vacío (voltaje y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_compresor', False):
                    if not voltaje_compresor or not foto_compresor:
                        mensajes_error.append("Complete todos los campos de Compresor (voltaje y foto)")
                        error_validacion = True
                
                # Validar accesorios
                if st.session_state.get('mostrar_manometros', False):
                    if not cantidad_manometros or not foto_manometros:
                        mensajes_error.append("Complete todos los campos de Manómetros (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_vacuometros', False):
                    if not cantidad_vacuometros or not foto_vacuometros:
                        mensajes_error.append("Complete todos los campos de Vacuómetros (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_valvulas', False):
                    if not cantidad_valvulas or not foto_valvulas:
                        mensajes_error.append("Complete todos los campos de Válvulas (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_mangueras', False):
                    if not cantidad_mangueras or not foto_mangueras:
                        mensajes_error.append("Complete todos los campos de Mangueras (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_boquillas', False):
                    if not cantidad_boquillas or not foto_boquillas:
                        mensajes_error.append("Complete todos los campos de Boquillas (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_reguladores', False):
                    if not cantidad_reguladores or not foto_reguladores:
                        mensajes_error.append("Complete todos los campos de Reguladores aire/gas (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_tuberia', False):
                    if not descripcion_tuberia or not foto_tuberia:
                        mensajes_error.append("Complete todos los campos de Tubería (descripción y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_cables', False):
                    if not descripcion_cables or not foto_cables:
                        mensajes_error.append("Complete todos los campos de Cables (descripción y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_curvas', False):
                    if not descripcion_curvas or not foto_curvas:
                        mensajes_error.append("Complete todos los campos de Curvas (descripción y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_tornilleria_acc', False):
                    if not descripcion_tornilleria or not foto_tornilleria:
                        mensajes_error.append("Complete todos los campos de Tornillería (descripción y foto)")
                        error_validacion = True
                
                # Validar elementos mecánicos
                if st.session_state.get('mostrar_pinon1', False):
                    if not tension_pinon1 or not foto_pinon1:
                        mensajes_error.append("Complete todos los campos de Piñón 1 (tensión y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_pinon2', False):
                    if not tension_pinon2 or not foto_pinon2:
                        mensajes_error.append("Complete todos los campos de Piñón 2 (tensión y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_polea1', False):
                    if not tension_polea1 or not foto_polea1:
                        mensajes_error.append("Complete todos los campos de Polea 1 (tensión y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_polea2', False):
                    if not tension_polea2 or not foto_polea2:
                        mensajes_error.append("Complete todos los campos de Polea 2 (tensión y foto)")
                        error_validacion = True
                
                # Validar elementos eléctricos
                if st.session_state.get('mostrar_gabinete', False):
                    if not cantidad_gabinete or not foto_gabinete:
                        mensajes_error.append("Complete todos los campos de Gabinete eléctrico (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_arrancador', False):
                    if not cantidad_arrancadores or not foto_arrancadores:
                        mensajes_error.append("Complete todos los campos de Arrancadores (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_control_nivel', False):
                    if not cantidad_control_nivel or not foto_control_nivel:
                        mensajes_error.append("Complete todos los campos de Control de nivel (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_variador', False):
                    if not cantidad_variadores or not foto_variadores:
                        mensajes_error.append("Complete todos los campos de Variadores de velocidad (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_sensor_temp', False):
                    if not cantidad_sensores or not foto_sensores:
                        mensajes_error.append("Complete todos los campos de Sensores de temperatura (cantidad y foto)")
                        error_validacion = True
                
                if st.session_state.get('mostrar_toma_corriente', False):
                    if not cantidad_toma_corriente or not foto_toma_corrientes:
                        mensajes_error.append("Complete todos los campos de Toma corriente (cantidad y foto)")
                        error_validacion = True
                
                # Validar preguntas de revisión
                if not revision_soldadura:
                    mensajes_error.append("Seleccione Sí o No para la revisión de soldadura")
                    error_validacion = True
                
                if not revision_sentidos:
                    mensajes_error.append("Seleccione Sí o No para la revisión de sentidos de giro")
                    error_validacion = True
                
                if not manual_funcionamiento:
                    mensajes_error.append("Seleccione Sí o No para el manual de funcionamiento")
                    error_validacion = True
                
                if not revision_filos:
                    mensajes_error.append("Seleccione Sí o No para la revisión de filos y acabados")
                    error_validacion = True
                
                if not revision_tratamientos:
                    mensajes_error.append("Seleccione Sí o No para la revisión de tratamientos")
                    error_validacion = True
                
                if not revision_tornilleria:
                    mensajes_error.append("Seleccione Sí o No para la revisión de tornillería")
                    error_validacion = True
                
                if not revision_ruidos:
                    mensajes_error.append("Seleccione Sí o No para la revisión de ruidos")
                    error_validacion = True
                
                if not ensayo_equipo:
                    mensajes_error.append("Seleccione Sí o No para el ensayo de equipo")
                    error_validacion = True
                
                # Validar información final
                if not lider_inspeccion:
                    mensajes_error.append("Seleccione un líder de inspección")
                    error_validacion = True
                
                if not encargado_soldador:
                    mensajes_error.append("Seleccione un encargado de soldadura")
                    error_validacion = True
                
                if not disenador:
                    mensajes_error.append("Seleccione un diseñador")
                    error_validacion = True
                
                # Validar que se haya seleccionado una OP
                if not op or op == "SELECCIONA" or op_selected == "SELECCIONA":
                    mensajes_error.append("Debe seleccionar una Orden de Pedido (OP) válida")
                    error_validacion = True
                
                # Campos obligatorios generales
                if not cliente or not item or not equipo or not cantidad:
                    mensajes_error.append("Complete todos los campos de información general (Cliente, Item, Equipo y Cantidad)")
                    error_validacion = True
                
                # Validar que se haya subido una foto general del equipo
                if not descripcion_general or not fotos_generales:
                    mensajes_error.append("Debe incluir una descripción y foto general del equipo")
                    error_validacion = True

                # Si hay errores de validación, mostrar y detener
                if error_validacion:
                    st.error("Por favor complete todos los campos obligatorios:")
                    for mensaje in mensajes_error:
                        st.warning(mensaje)
                    return

                # Si la validación es exitosa, proceder con el guardado
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

                row = [
                    str(cliente), str(op), str(item), str(equipo), str(cantidad), str(fecha),
                    str(descripcion_general), serializa_fotos(fotos_generales, f"FotoGeneral_{op}", folder_id),
                    str(cantidad_motores), str(voltaje_motores), serializa_fotos(fotos_motores, f"Motores_{op}", folder_id),
                    str(cantidad_reductores), str(voltaje_reductores), serializa_fotos(fotos_reductores, f"Reductores_{op}", folder_id),
                    str(cantidad_bombas), str(voltaje_bombas), serializa_fotos(fotos_bombas, f"Bombas_{op}", folder_id),
                    str(voltaje_turbina), serializa_fotos(foto_turbina, f"Turbina_{op}", folder_id),
                    str(tipo_combustible_quemador), str(metodo_uso_quemador), str(voltaje_quemador), serializa_fotos(foto_quemador, f"Quemador_{op}", folder_id),
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
                    str(descripcion_tuberia), serializa_fotos(foto_tuberia, f"Tuberia_{op}", folder_id),
                    str(descripcion_cables), serializa_fotos(foto_cables, f"Cables_{op}", folder_id),
                    str(descripcion_curvas), serializa_fotos(foto_curvas, f"Curvas_{op}", folder_id),
                    str(descripcion_tornilleria), serializa_fotos(foto_tornilleria, f"Tornilleria_{op}", folder_id),
                    str(revision_soldadura), str(revision_sentidos), str(manual_funcionamiento), 
                    str(revision_filos), str(revision_tratamientos), str(revision_tornilleria),
                    str(revision_ruidos), str(ensayo_equipo), str(observaciones_generales), 
                    str(lider_inspeccion), str(encargado_soldador), str(disenador), str(fecha_entrega)
                ]
                headers = [
                    "cliente dili", "op dili", "item dili", "equipo dili", "cantidad dili", "fecha dili", 
                    "descripcion general dili", "foto general dili",
                    "cantidad motores dili", "voltaje motores dili", "fotos motores dili",
                    "cantidad reductores dili", "voltaje reductores dili", "fotos reductores dili", 
                    "cantidad bombas dili", "voltaje bombas dili", "fotos bombas dili",
                    "voltaje turbina dili", "foto turbina dili", 
                    "Tipo combustible quemador dili", "Metodo de uso quemador dili", "voltaje quemador dili", "foto quemador dili", 
                    "voltaje bomba de vacio dili", "foto bomba de vacio dili",
                    "voltaje compresor dili", "foto compresor dili", 
                    "cantidad manometros dili", "foto manometros dili", 
                    "cantidad vacuometros dili", "foto vacuometros dili",
                    "cantidad valvulas dili", "foto valvulas dili", 
                    "cantidad mangueras dili", "foto mangueras dili", 
                    "cantidad boquillas dili", "foto boquillas dili",
                    "cantidad reguladores aire/gas dili", "foto reguladores dili", 
                    "tension piñon 1 dili", "foto piñon 1 dili", 
                    "tension piñon 2 dili", "foto piñon 2 dili",
                    "tension polea 1 dili", "foto polea 1 dili", 
                    "tension polea 2 dili", "foto polea 2 dili", 
                    "cantidad gabinete electrico dili", "foto gabinete dili",
                    "cantidad arrancadores dili", "foto arrancadores dili", 
                    "cantidad control de nivel dili", "foto control de nivel dili", 
                    "cantidad variadores de velociad dili", "foto variadores de velocidad dili",
                    "cantidad sensores de temperatura dili", "foto sensores de temperatura dili", 
                    "cantidad toma corriente dili", "foto toma corrientes dili", 
                    "descripcion otros elementos dili", "fotos otros elementos dili",
                    "descripcion tuberias dili", "foto tuberias dili", 
                    "descripcion cables dili", "foto cables dili", 
                    "descripcion curvas dili", "foto curvas dili",
                    "descripcion tornilleria dili", "foto tornilleria dili",
                    "revision de soldadura dili", "revision de sentidos de giro dili", 
                    "manual de funcionamiento dili", "revision de filos y acabados dili", 
                    "revision de tratamientos dili", "revision de tornilleria dili",
                    "revision de ruidos dili", "ensayo equipo dili", 
                    "observciones generales dili", "lider de inspeccion dili", 
                    "Encargado soldador dili", "diseñador dili", "fecha de entrega dili"
                ]
                
                worksheet_name_diligenciadas = "actas de entregas diligenciadas"
                try:
                    # Solo intenta abrir la hoja existente
                    sheet = sheet_client.open(file_name).worksheet(worksheet_name_diligenciadas)
                except gspread.exceptions.WorksheetNotFound:
                    # Si la hoja no existe, mostrar error y no continuar
                    st.error(f"La hoja '{worksheet_name_diligenciadas}' no existe. Contacta al administrador para que la cree.")
                    return

                # Si la hoja existe pero está vacía, agrega los encabezados
                if not sheet.get_all_values():
                    sheet.append_row(headers)
                
                sheet.append_row(row)
                st.success("Acta de entrega guardada correctamente en 'actas de entregas diligenciadas'.")
                
                # Mostrar información sobre las fotos subidas
                if fotos_generales:
                    st.info(f"Se han subido {len(fotos_generales)} fotos generales del equipo.")
                
                # Envío automático de correo electrónico si el checkbox está seleccionado
                if enviar_notificacion:
                    try:
                        email_destinatario = "coordinadorinventarios@tekpro.com.co"
                        asunto = f"Acta de entrega completada - OP: {op}"
                        mensaje = f"""
                        <html>
                        <body>
                            <div style="border-left: 5px solid #1db6b6; padding-left: 15px;">
                                <h2 style="color: #1db6b6;">Notificación de Acta de Entrega</h2>
                                <p>Se ha completado el acta de entrega con la siguiente información:</p>
                                <ul>
                                    <li><strong>OP:</strong> {op}</li>
                                    <li><strong>Cliente:</strong> {cliente}</li>
                                    <li><strong>Equipo:</strong> {equipo}</li>
                                    <li><strong>Item:</strong> {item}</li>
                                    <li><strong>Fecha:</strong> {fecha}</li>
                                </ul>
                                <p>El acta fue realizada por: <strong>{lider_inspeccion}</strong></p>
                                <p>Observaciones generales: {observaciones_generales}</p>
                                <p>Esta es una notificación automática del sistema Dispatch Tekpro.</p>
                            </div>
                        </body>
                        </html>
                        """
                        
                        exito, mensaje_resultado = enviar_correo(email_destinatario, asunto, mensaje)
                        if exito:
                            st.success(f"Se ha enviado una notificación por correo a {email_destinatario}")
                        else:
                            st.warning(f"No se pudo enviar la notificación por correo: {mensaje_resultado}")
                    except Exception as e:
                        st.warning(f"Error al enviar correo: {str(e)}")

if __name__ == "__main__":
    main() 
