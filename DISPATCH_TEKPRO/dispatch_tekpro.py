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

# Simulación de base de datos SAG - Podría ser reemplazado por una conexión real a la BDD
def get_sag_database():
    """
    Obtiene los datos de la base de datos SAG desde la hoja 'BDD SAG' en Google Sheets.
    Estructura de la hoja esperada:
    - Primera columna: Código del artículo
    - Segunda columna: Descripción del artículo
    - Tercera columna: Unidad del artículo
    """
    try:
        # Configurar acceso a la hoja de cálculo
        creds = get_service_account_creds()
        file_name = st.secrets.drive_config.FILE_NAME
        sheet_client = gspread.authorize(creds)
        
        # Abrir la hoja específica "BDD SAG"
        try:
            sag_sheet = sheet_client.open(file_name).worksheet("BDD SAG")
            sag_data = sag_sheet.get_all_values()
            
            # Verificar que hay datos y encabezados
            if not sag_data or len(sag_data) < 2:  # Al menos debe haber encabezados y un dato
                st.warning("La hoja BDD SAG está vacía o no tiene suficientes datos.")
                return []
            
            # Obtener los encabezados
            headers = sag_data[0]
            
            # Verificar que las columnas necesarias están presentes
            required_columns = ["CODIGO", "DESCRIPCION", "UNIDAD"]
            column_indices = {}
            
            for req_col in required_columns:
                found = False
                for i, header in enumerate(headers):
                    if header.upper().strip() == req_col:
                        column_indices[req_col] = i
                        found = True
                        break
                
                if not found:
                    st.warning(f"No se encontró la columna {req_col} en la hoja BDD SAG.")
                    return []
            
            # Construir la base de datos
            sag_db = []
            for row in sag_data[1:]:  # Omitir encabezados
                if len(row) > max(column_indices.values()):  # Asegurar que la fila tiene suficientes columnas
                    codigo = row[column_indices["CODIGO"]].strip()
                    descripcion = row[column_indices["DESCRIPCION"]].strip()
                    unidad = row[column_indices["UNIDAD"]].strip()
                    
                    if codigo and descripcion:  # Solo agregar si tiene al menos código y descripción
                        sag_db.append({
                            "codigo": codigo,
                            "descripcion": descripcion,
                            "unidad": unidad if unidad else "UND"  # Valor predeterminado si no hay unidad
                        })
            
            return sag_db
            
        except gspread.exceptions.WorksheetNotFound:
            st.warning("No se encontró la hoja 'BDD SAG' en el documento. Creando una hoja de ejemplo...")
            # Crear la hoja si no existe
            try:
                sheet = sheet_client.open(file_name)
                worksheet = sheet.add_worksheet(title="BDD SAG", rows=100, cols=20)
                
                # Añadir encabezados
                headers = ["CODIGO", "DESCRIPCION", "UNIDAD"]
                worksheet.update('A1:C1', [headers])
                
                # Añadir algunos datos de ejemplo
                sample_data = [
                    ["M001", "Motor eléctrico 5HP", "UND"],
                    ["M002", "Motor eléctrico 10HP", "UND"],
                    ["R001", "Reductor 1:10", "UND"],
                    ["B001", "Bomba centrífuga 1HP", "UND"],
                    ["V001", "Válvula de bola 1\"", "UND"]
                ]
                worksheet.update('A2:C6', sample_data)
                
                # Formatear encabezados (negrita, centrados)
                worksheet.format('A1:C1', {
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER"
                })
                
                st.success("Se ha creado la hoja 'BDD SAG' con datos de ejemplo.")
                
                # Convertir los datos de muestra al formato requerido
                return [{"codigo": code, "descripcion": desc, "unidad": unit} for code, desc, unit in sample_data]
                
            except Exception as e:
                st.error(f"Error al crear la hoja BDD SAG: {str(e)}")
                return []
                
    except Exception as e:
        st.error(f"Error al obtener datos de BDD SAG: {str(e)}")
        # En caso de error, devolver algunos datos de muestra
        return [
            {"codigo": "M001", "descripcion": "Motor eléctrico 5HP", "unidad": "UND"},
            {"codigo": "B001", "descripcion": "Bomba centrífuga 1HP", "unidad": "UND"},
            {"codigo": "V001", "descripcion": "Válvula de bola 1\"", "unidad": "UND"},
            {"codigo": "T003", "descripcion": "Tornillo inox 3/8\"", "unidad": "UND"},
            {"codigo": "J001", "descripcion": "Junta de caucho 1\"", "unidad": "UND"}
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

    # Inicializar la base de datos SAG
    sag_db = get_sag_database()
    
    # Guardar la base de datos en session_state para reutilizarla
    if 'sag_db' not in st.session_state:
        st.session_state.sag_db = sag_db
    
    # Asegurar que sag_database está disponible para la selección de productos
    if 'sag_database' not in st.session_state:
        st.session_state['sag_database'] = sag_db

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
                    "Encargado almacén", 
                    "Encargado ingeniería y diseño", 
                    "Encargado logística", 
                    "Firma encargado logística", 
                    "Observaciones adicionales", 
                    "Artículos enviados", 
                    "Artículos no enviados"
                ]
                
                # Agregar encabezados para cada guacal (1-7)
                for i in range(1, 8):
                    headers.extend([
                        f"Descripción Guacal {i}",
                        f"Dimensiones Guacal {i}",
                        f"Peso Bruto Guacal {i} (kg)",
                        f"Peso Neto Guacal {i} (kg)",
                        f"Fotos Guacal {i}"
                    ])
                
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

        # Leer órdenes de pedido existentes desde ACTA DE ENTREGA, solo mostrar las que estén completas
        try:
            acta_sheet = sheet_client.open(file_name).worksheet("Acta de entrega")
            acta_rows = acta_sheet.get_all_values()
            headers = acta_rows[0] if acta_rows else []
            # Usar encabezados estándar proporcionados por el usuario
            encabezados_estandar = [
                "cliente", "OP", "Item", "Equipo", "Cantidad", "fecha", "cantidad motores", "voltaje motores", "fotos motores",
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
            
            # Buscar índice de OP (exacto)
            op_idx = None
            for idx, h in enumerate(headers):
                if h.strip().lower() == "op":
                    op_idx = idx
                    break
            ordenes_existentes = {}
            ordenes_list = []
            # Obtener las OPs que ya están en la hoja de Lista de empaque
            ops_lista_empaque = set()
            try:
                empaque_sheet = sheet_client.open(file_name).worksheet("Lista de empaque")
                empaque_rows = empaque_sheet.get_all_values()
                if empaque_rows:
                    # Asumiendo que la primera columna es la OP en la hoja Lista de empaque
                    for row in empaque_rows[1:]:  # Saltar la fila de encabezados
                        if row and row[0].strip():
                            ops_lista_empaque.add(row[0].strip())
            except Exception as e:
                st.warning(f"No se pudieron cargar las OPs de Lista de empaque: {e}")
            
            # Recopilar datos solo de OPs diligenciadas que NO estén en Lista de empaque
            try:
                for row in diligenciadas_rows[1:]:
                    if op_dili_idx is not None and len(row) > op_dili_idx and row[op_dili_idx].strip():
                        orden_dili = row[op_dili_idx].strip()
                        # Solo agregar si la OP no está ya en Lista de empaque
                        if orden_dili not in ops_lista_empaque:
                            ordenes_existentes[orden_dili] = row  # Agregar a las existentes
                            ordenes_list.append(orden_dili)       # Agregar a la lista de selección
                
                if not ordenes_list:
                    if ops_lista_empaque:
                        st.warning("Todas las órdenes ya están registradas en 'Lista de empaque'.")
                    else:
                        st.warning("No hay órdenes de pedido en 'actas de entregas diligenciadas'.")
            except Exception as e:
                st.warning(f"Error al procesar actas diligenciadas para mostrar OPs: {e}")
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
       

        # Variables para almacenar información de cliente, equipo y diseñador
        auto_cliente = ""
        auto_equipo = ""
        auto_disenador = ""
        
        # Intentar obtener información de "actas de entregas diligenciadas" primero
        try:
            diligenciadas_sheet = sheet_client.open(file_name).worksheet("actas de entregas diligenciadas")
            diligenciadas_rows = diligenciadas_sheet.get_all_values()
            if diligenciadas_rows:
                headers_dili = [h.strip().lower() for h in diligenciadas_rows[0]]
                cliente_idx = None
                equipo_idx = None
                disenador_idx = None
                op_idx = None
                
                # Encontrar índices de las columnas relevantes (buscando coincidencias exactas)
                for idx, h in enumerate(headers_dili):
                    if h == "cliente dili":
                        cliente_idx = idx
                    elif h == "equipo dili":
                        equipo_idx = idx
                    elif h == "diseñador dili":
                        disenador_idx = idx
                    elif h == "op dili":
                        op_idx = idx
                
                # Buscar si la OP actual está en las diligenciadas
                if op_idx is not None and orden_pedido_val != "No hay órdenes registradas":
                    for row in diligenciadas_rows[1:]:
                        if len(row) > op_idx and row[op_idx].strip() == orden_pedido_val:
                            # Si encontramos la OP, obtenemos los datos
                            if cliente_idx is not None and len(row) > cliente_idx:
                                auto_cliente = row[cliente_idx]
                            if equipo_idx is not None and len(row) > equipo_idx:
                                auto_equipo = row[equipo_idx]
                            if disenador_idx is not None and len(row) > disenador_idx:
                                auto_disenador = row[disenador_idx]
                            break
        except Exception as e:
            st.warning(f"No se pudo obtener información de actas diligenciadas: {e}")
            
            # No es necesario buscar en actas de entrega porque solo usamos diligenciadas        # Obtener solo los artículos que tienen fotos diligenciadas
        articulos_presentes = []
        if orden_pedido_val and orden_pedido_val in ordenes_existentes:
            row = ordenes_existentes[orden_pedido_val]
            headers = diligenciadas_headers
            
            # Mapeo de nombre de artículo a columna de foto correspondiente
            mapeo_articulos_fotos = {
                "Motores": "fotos motores dili",
                "Reductores": "fotos reductores dili",
                "Bombas": "fotos bombas dili",
                "Turbina": "foto turbina dili",
                "Quemador": "foto quemador dili",
                "Bomba de vacío": "foto bomba de vacio dili",
                "Compresor": "foto compresor dili",
                "Manómetros": "foto manometros dili",
                "Vacuómetros": "foto vacuometros dili",
                "Válvulas": "foto valvulas dili",
                "Mangueras": "foto mangueras dili",
                "Boquillas": "foto boquillas dili",
                "Reguladores aire/gas": "foto reguladores dili",
                "Tuberia": "foto tuberia dili",
                "Cables": "foto cables dili",
                "Tornillería": "foto tornilleria dili",
                "Curvas": "foto curvas dili",
                "Piñón 1": "foto piñon 1 dili",
                "Piñón 2": "foto piñon 2 dili",
                "Polea 1": "foto polea 1 dili",
                "Polea 2": "foto polea 2 dili",
                "Gabinete eléctrico": "foto gabinete dili",
                "Arrancadores": "foto arrancadores dili",
                "Control de nivel": "foto control de nivel dili",
                "Variadores de velocidad": "foto variadores de velocidad dili",
                "Sensores de temperatura": "foto sensores de temperatura dili",
                "Toma corriente": "foto toma corrientes dili",
                "Otros elementos": "fotos otros elementos dili"
            }
            
            # Verificar si el artículo tiene foto diligenciada
            for art, col_foto in mapeo_articulos_fotos.items():
                try:
                    if col_foto in headers:
                        idx = headers.index(col_foto)
                        valor = row[idx] if idx < len(row) else ""
                        if valor and valor.strip().lower() not in ["", "sin foto", "error al subir foto"]:
                            articulos_presentes.append(art)
                except Exception as e:
                    st.warning(f"Error al procesar artículo {art}: {e}")
            
            # Mostrar mensaje si no hay artículos con fotos
            if not articulos_presentes:
                st.warning("No se encontraron artículos con fotos diligenciadas en esta orden de pedido.")

        # Estado dinámico para número de paquetes
        if 'num_paquetes' not in st.session_state:
            st.session_state['num_paquetes'] = 1
            
        # Inicializar el estado para los items de guacales si no existe
        if 'guacales_items' not in st.session_state:
            st.session_state['guacales_items'] = {}

        # Mostrar información del cliente y equipo antes del formulario
        if orden_pedido_val and orden_pedido_val != "No hay órdenes registradas" and auto_cliente:
            st.markdown(f"""
            <div style='background:#f7fafb; padding:1em; border-left:4px solid #1db6b6; border-radius:4px; margin-bottom:20px;'>
                <p style='margin:0; font-weight:bold; color:#1db6b6;'>Información del proyecto</p>
                <p style='margin:5px 0;'><b>Cliente:</b> {auto_cliente}</p>
                <p style='margin:5px 0;'><b>Equipo:</b> {auto_equipo if auto_equipo and auto_equipo != "Si" and auto_equipo != "Sí" else ""}</p>
            </div>
            """, unsafe_allow_html=True)

        with st.form("dispatch_form"):
            fecha = st.date_input("Fecha del día", value=datetime.date.today())

            # Encargado almacén como selectbox con solo Andrea Ochoa
            encargado_almacen = st.selectbox(
                "Encargado almacén",
                ["", "Andrea Ochoa"]
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
            
            # Usar diseñador de las actas si está disponible
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
                ],
                index=([
                    "",
                    "Alejandro Diaz",
                    "Juan David Martinez",
                    "Juan Andres Zapata",
                    "Daniel Valbuena",
                    "Victor Manuel Baena",
                    "Diomer Arbelaez",
                    "Jose Perez"
                ].index(auto_disenador) if auto_disenador in [
                    "",
                    "Alejandro Diaz",
                    "Juan David Martinez",
                    "Juan Andres Zapata",
                    "Daniel Valbuena",
                    "Victor Manuel Baena",
                    "Diomer Arbelaez",
                    "Jose Perez"
                ] else 0)
            )

            st.markdown("<b>Selecciona los artículos a empacar:</b>", unsafe_allow_html=True)
            
            if not articulos_presentes:
                st.warning("No se encontraron artículos. No hay elementos para empacar.")
                
            else:
                st.info(f"Se encontraron {len(articulos_presentes)} artículos .")
                articulos_seleccion = {}
                for art in articulos_presentes:
                    articulos_seleccion[art] = st.checkbox(art, value=True, key=f"empacar_{art}")
                    
                    # Si es 'Otros elementos', mostrar la descripción registrada en el acta justo debajo
                    if art.lower() == "otros elementos":
                        desc_otros = ""
                        # Buscar columna de descripción de otros elementos
                        for idx, h in enumerate(diligenciadas_headers):
                            if "descripcion otros elementos" in h.lower():
                                desc_otros = row[idx] if idx < len(row) else ""
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
                
                # Definir el ID único para este guacal
                guacal_id = f"guacal_{i+1}"
                
                # Inicializar la lista de items para este guacal si no existe
                if guacal_id not in st.session_state['guacales_items']:
                    st.session_state['guacales_items'][guacal_id] = []
                
                # Crear contenedor para la tabla de items de este guacal
                st.markdown("<b>Items del guacal:</b>", unsafe_allow_html=True)
                
                # Mostrar la tabla de items ya agregados a este guacal
                if st.session_state['guacales_items'][guacal_id]:
                    # Encabezado para la tabla
                    st.markdown("#### Items añadidos al guacal")
                    
                    # Crear DataFrame para mostrar los ítems
                    items_df = pd.DataFrame(st.session_state['guacales_items'][guacal_id])
                    
                    # Usar un contenedor para dar estilo a la tabla
                    with st.container():
                        # Crear columnas para cada ítem con opción de eliminar
                        for idx, item in enumerate(st.session_state['guacales_items'][guacal_id]):
                            cols = st.columns([1, 3, 1, 1, 1])
                            with cols[0]:
                                st.text(item['codigo'])
                            with cols[1]:
                                st.text(item['descripcion'])
                            with cols[2]:
                                st.text(str(item['cantidad']))
                            with cols[3]:
                                st.text(item['unidad'])
                            with cols[4]:
                                if st.button("❌", key=f"delete_{guacal_id}_{idx}"):
                                    st.session_state['guacales_items'][guacal_id].pop(idx)
                                    st.success(f"Ítem eliminado del guacal {i+1}")
                                    st.session_state['need_rerun'] = True
                        
                    # Mostrar el total de ítems
                    st.info(f"Total de ítems: {len(st.session_state['guacales_items'][guacal_id])}")
                
                # Formulario para añadir un nuevo ítem al guacal
                st.markdown("<div class='add-item-section'><h4>Añadir nuevo ítem</h4>", unsafe_allow_html=True)
                
                # Crear columnas para organizar la entrada de datos
                col1, col2 = st.columns(2)
                
                # Opciones para buscar por código o descripción
                with col1:
                    search_option = st.radio(
                        "Buscar por:",
                        ["Código", "Descripción"],
                        horizontal=True,
                        key=f"search_option_{guacal_id}"
                    )
                
                # Campo de búsqueda
                with col2:
                    search_term = st.text_input(
                        "Buscar:",
                        key=f"search_term_{guacal_id}",
                        placeholder="Escribe para buscar código o descripción"
                    )
                
                # Procesar la base de datos para búsqueda
                if not st.session_state['sag_database']:
                    st.warning("No hay códigos disponibles en la base de datos SAG. Por favor, añade datos a la hoja 'BDD SAG'.")
                    filtered_items = []
                else:
                    # Filtrar items según el término de búsqueda
                    if search_term:
                        if search_option == "Código":
                            filtered_items = [item for item in st.session_state['sag_database'] 
                                            if search_term.lower() in item['codigo'].lower()]
                        else:  # Búsqueda por descripción
                            filtered_items = [item for item in st.session_state['sag_database'] 
                                            if search_term.lower() in item['descripcion'].lower()]
                    else:
                        filtered_items = st.session_state['sag_database']
                
                # Mostrar los resultados en formato de tabla seleccionable
                if filtered_items:
                    # Crear opciones para mostrar en el selectbox
                    if search_option == "Código":
                        options = [f"{item['codigo']} - {item['descripcion']}" for item in filtered_items]
                    else:  # Mostrar dando prioridad a la descripción
                        options = [f"{item['descripcion']} - {item['codigo']}" for item in filtered_items]
                    
                    selected_item = st.selectbox(
                        "Seleccionar artículo:",
                        options=options,
                        key=f"selected_item_{guacal_id}"
                    )
                    
                    # Extraer código del ítem seleccionado
                    if search_option == "Código":
                        selected_codigo = selected_item.split(" - ")[0]
                    else:
                        selected_codigo = selected_item.split(" - ")[1]
                    
                    # Buscar información completa del ítem
                    item_info = next((item for item in st.session_state['sag_database'] if item['codigo'] == selected_codigo), None)
                else:
                    st.warning("No se encontraron coincidencias con tu búsqueda.")
                    selected_codigo = ""
                    item_info = None
                
                # Mostrar la información completa del ítem seleccionado
                col1, col2, col3, col4 = st.columns([2, 3, 1, 1])
                
                # Mostrar el código
                with col1:
                    st.text_input("Código:", value=selected_codigo, disabled=True, key=f"codigo_display_{guacal_id}")
                
                # Mostrar la descripción
                with col2:
                    descripcion = st.text_input("Descripción:", value=item_info['descripcion'] if item_info else "", disabled=True, key=f"desc_{guacal_id}")
                
                # Entrada de cantidad (único campo editable)
                with col3:
                    cantidad = st.number_input("Cantidad:", min_value=1, value=1, key=f"cantidad_{guacal_id}")
                
                # Mostrar la unidad automáticamente
                with col4:
                    unidad = st.text_input("Unidad:", value=item_info['unidad'] if item_info else "", disabled=True, key=f"unidad_{guacal_id}")
                
                # Botón para añadir el ítem (fuera de las columnas)
                if st.button("Añadir ítem", key=f"btn_add_{guacal_id}", type="primary"):
                    try:
                        if item_info:
                            # Crear un nuevo ítem con los datos seleccionados
                            new_item = {
                                'codigo': selected_codigo,
                                'descripcion': item_info['descripcion'],
                                'cantidad': cantidad,
                                'unidad': item_info['unidad']
                            }
                            
                            # Añadir el ítem a la lista de items del guacal en session_state
                            if guacal_id in st.session_state['guacales_items']:
                                st.session_state['guacales_items'][guacal_id].append(new_item)
                                # Mostrar mensaje de éxito
                                st.success(f"Ítem añadido al guacal {i+1}: {item_info['descripcion']} (Cantidad: {cantidad} {item_info['unidad']})")
                            else:
                                st.warning(f"No se pudo encontrar el guacal {i+1} en la sesión. Intente reiniciar la página.")
                    except Exception as e:
                        st.error(f"Error al añadir ítem: {str(e)}")
                        
                        # Limpiar campo de búsqueda para permitir añadir otro ítem
                        try:
                            # Verificar si la clave existe antes de intentar modificarla
                            if f"search_term_{guacal_id}" in st.session_state:
                                # En lugar de asignar una cadena vacía, removemos la clave del session_state
                                del st.session_state[f"search_term_{guacal_id}"]
                        except Exception as e:
                            st.warning(f"No se pudo limpiar el término de búsqueda: {e}")
                        
                        # Forzar rerun para actualizar la interfaz de forma segura
                        set_session_state('need_rerun', True)
                    else:
                        st.warning("No se ha seleccionado un ítem válido. Por favor, busque y seleccione un ítem primero.")
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Mostrar tabla de ítems ya agregados al guacal
                if guacal_id in st.session_state['guacales_items'] and len(st.session_state['guacales_items'][guacal_id]) > 0:
                    st.markdown(f"<b>Ítems agregados al guacal {i+1}:</b>", unsafe_allow_html=True)
                    
                    # Crear un DataFrame para mostrar los ítems en una tabla
                    items_data = []
                    for idx, item in enumerate(st.session_state['guacales_items'][guacal_id]):
                        items_data.append({
                            "N°": idx + 1,
                            "Código": item['codigo'],
                            "Descripción": item['descripcion'],
                            "Cantidad": item['cantidad'],
                            "Unidad": item['unidad']
                        })
                    
                    # Mostrar la tabla de ítems
                    if items_data:
                        items_df = pd.DataFrame(items_data)
                        st.dataframe(items_df, use_container_width=True)
                else:
                    st.info(f"No hay ítems agregados al guacal {i+1}. Use el buscador para encontrar y añadir ítems.")
                
                # Crear un campo de observaciones adicionales para el guacal
                obs_guacal = st.text_area(f"Observaciones adicionales del guacal {i+1}", key=f"obs_guacal_{i+1}")
                
                # Campos para dimensiones y pesos del guacal
                st.markdown(f"<b>Dimensiones y pesos del guacal {i+1}:</b>", unsafe_allow_html=True)
                
                # Crear 3 columnas para los campos de dimensiones
                dim_col1, dim_col2, dim_col3 = st.columns(3)
                
                with dim_col1:
                    largo = st.number_input(f"Largo (cm):", min_value=0.0, value=0.0, step=0.1, format="%.1f", key=f"largo_guacal_{i+1}")
                
                with dim_col2:
                    ancho = st.number_input(f"Ancho (cm):", min_value=0.0, value=0.0, step=0.1, format="%.1f", key=f"ancho_guacal_{i+1}")
                
                with dim_col3:
                    alto = st.number_input(f"Alto (cm):", min_value=0.0, value=0.0, step=0.1, format="%.1f", key=f"alto_guacal_{i+1}")
                
                # Crear 2 columnas para los pesos
                peso_col1, peso_col2 = st.columns(2)
                
                with peso_col1:
                    peso_bruto = st.number_input(f"Peso bruto (kg):", min_value=0.0, value=0.0, step=0.1, format="%.1f", key=f"peso_bruto_guacal_{i+1}")
                
                with peso_col2:
                    peso_neto = st.number_input(f"Peso neto (kg):", min_value=0.0, value=0.0, step=0.1, format="%.1f", key=f"peso_neto_guacal_{i+1}")
                
                # Campo para subir fotos del guacal
                fotos = st.file_uploader(f"Fotos guacal {i+1}", type=["jpg", "jpeg", "png"], key=f"fotos_paquete_{i+1}", accept_multiple_files=True)
                
                # Guardar información completa del guacal
                desc_items = json.dumps(st.session_state['guacales_items'][guacal_id]) if st.session_state['guacales_items'][guacal_id] else ""
                paquetes.append({
                    "desc": desc_items,
                    "obs": obs_guacal,
                    "fotos": fotos,
                    "dimensiones": {
                        "largo": largo,
                        "ancho": ancho,
                        "alto": alto
                    },
                    "pesos": {
                        "bruto": peso_bruto,
                        "neto": peso_neto
                    }
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
                if not articulos_presentes:
                    st.error("No hay artículos para empacar en esta OP.")
                else:
                    # Validar que todos los campos requeridos estén completos
                    error_validacion = False
                    mensajes_error = []
                
                # Validar campos obligatorios (excepto observaciones)
                if not orden_pedido_val or orden_pedido_val == "No hay órdenes registradas":
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
                
                # Verificar que al menos un guacal tenga items y fotos
                guacales_completos = False
                for i, paquete in enumerate(paquetes):
                    guacal_id = f"guacal_{i+1}"
                    # Verificar si hay items en la sesión para este guacal
                    has_items = guacal_id in st.session_state['guacales_items'] and len(st.session_state['guacales_items'][guacal_id]) > 0
                    # Verificar si hay fotos para este guacal
                    has_fotos = paquete["fotos"] and len(paquete["fotos"]) > 0
                    
                    # Si este guacal tiene tanto items como fotos, marcarlo como completo
                    if has_items and has_fotos:
                        guacales_completos = True
                        break
                
                if not guacales_completos:
                    mensajes_error.append("Al menos un guacal debe tener items detallados y fotos. Asegúrese de agregar al menos un ítem con el botón 'Añadir ítem' y subir al menos una foto.")
                    error_validacion = True
                
                # Verificar que se haya seleccionado al menos un artículo para enviar
                enviados = [art for art, v in articulos_seleccion.items() if v]
                no_enviados = [art for art, v in articulos_seleccion.items() if not v]
                
                if not enviados:
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
                    - Para agregar un ítem al guacal, use el buscador, seleccione el ítem y haga clic en 'Añadir ítem'
                    - Asegúrese de haber subido al menos una foto para cada guacal
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
                    guacal_id = f"guacal_{idx}"
                    
                    # Preparar el texto descriptivo de los items
                    items_descripcion = ""
                    if guacal_id in st.session_state['guacales_items'] and st.session_state['guacales_items'][guacal_id]:
                        items_lines = []
                        for item in st.session_state['guacales_items'][guacal_id]:
                            item_line = f"{item['codigo']} - {item['descripcion']} - {item['cantidad']} {item['unidad']}"
                            items_lines.append(item_line)
                        items_descripcion = "\n".join(items_lines)
                    
                    # Añadir observaciones si existen
                    if paquete["obs"] and paquete["obs"].strip():
                        if items_descripcion:
                            items_descripcion += f"\n\nObservaciones: {paquete['obs']}"
                        else:
                            items_descripcion = f"Observaciones: {paquete['obs']}"
                    
                    # Añadir información de dimensiones y pesos
                    dimensiones_info = f"{paquete['dimensiones']['largo']}×{paquete['dimensiones']['ancho']}×{paquete['dimensiones']['alto']} cm"
                    peso_bruto = f"{paquete['pesos']['bruto']} kg"
                    peso_neto = f"{paquete['pesos']['neto']} kg"
                    
                    # Preparar solo la descripción con ítems y observaciones
                    if items_descripcion:
                        if paquete["obs"] and paquete["obs"].strip():
                            items_descripcion += f"\n\nObservaciones: {paquete['obs']}"
                    else:
                        if paquete["obs"] and paquete["obs"].strip():
                            items_descripcion = f"Observaciones: {paquete['obs']}"
                    
                    # Agregar descripción del guacal (ahora contiene solo los ítems y observaciones)
                    row.append(items_descripcion)  # Descripción Guacal n
                    
                    # Agregar dimensiones y pesos como columnas separadas
                    row.append(dimensiones_info)  # Dimensiones Guacal n
                    row.append(peso_bruto)        # Peso Bruto Guacal n
                    row.append(peso_neto)         # Peso Neto Guacal n
                    
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
                    row.append("")  # Dimensiones Guacal vacío
                    row.append("")  # Peso Bruto Guacal vacío
                    row.append("")  # Peso Neto Guacal vacío
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
                                dimensiones = paquete['dimensiones']
                                pesos = paquete['pesos']
                                dimensiones_html = f"<div style='margin-top:10px;'><strong>Dimensiones:</strong> {dimensiones['largo']}×{dimensiones['ancho']}×{dimensiones['alto']} cm</div>"
                                pesos_html = f"<div><strong>Peso bruto:</strong> {pesos['bruto']} kg, <strong>Peso neto:</strong> {pesos['neto']} kg</div>"
                                
                                guacales_texto += f"""<li>
                                    <strong>Guacal {idx}:</strong> 
                                    <div>{paquete['desc']}</div>
                                    {dimensiones_html}
                                    {pesos_html}
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
                                    {"".join(f"<li>{art}</li>" for art in enviados)}
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
                ["", "Leudys Castillo", "Jaime Rincon", "Jaime Ramos", "Gabriel Garcia", "Jefferson Galindez", "Jeison Arboleda", "Octaviano Velasquez","Sebastian Zapata", "Katerine Padilla", "No Aplica", "Osvaldo Gil","Julio Cesar"],
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

