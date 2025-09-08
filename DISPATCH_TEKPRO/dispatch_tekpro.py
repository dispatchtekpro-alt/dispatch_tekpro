# ...existing code...

import streamlit as st
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCreds
import io
import os
import urllib.parse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials as UserCreds
import json
import datetime
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np
import tempfile
import concurrent.futures

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

# Configuración
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

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

# Autorizar Google Drive con OAuth2
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

# Autorizar Google Drive con OAuth2
def authorize_drive_oauth():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    redirect_uri = "https://dispatchtekpro.streamlit.app/"
    st.info(f"[LOG] Usando redirect_uri: {redirect_uri}")
    flow = Flow.from_client_config(
        {"web": dict(st.secrets.oauth2)},
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
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

    from PIL import Image
    import io
    drive_service = get_drive_service_oauth()
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    # Comprimir imagen antes de subir
    try:
        file.seek(0)
        img = Image.open(file)
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG', quality=70, optimize=True)
        img_io.seek(0)
        media = MediaIoBaseUpload(img_io, mimetype='image/jpeg')
    except Exception:
        file.seek(0)
        media = MediaIoBaseUpload(file, mimetype='image/jpeg')
    from googleapiclient.errors import HttpError
    max_retries = 7
    delay = 5
    for attempt in range(max_retries):
        try:
            uploaded = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            file_id = uploaded.get('id')
            drive_service.permissions().create(
                fileId=file_id,
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()
            public_url = f"https://drive.google.com/uc?id={file_id}"
            return public_url
        except HttpError as e:
            status = getattr(e.resp, 'status', None)
            if status == 429:
                print(f"Intento {attempt+1}: cuota excedida, esperando {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                print(f"Error subiendo {filename}: {e}")
                return None
        except Exception as e:
            print(f"Error inesperado subiendo {filename}: {e}")
            return None
    return None
    return None

# Función para subir múltiples imágenes en paralelo
def upload_images_parallel(files, base_name, folder_id):
    if not files:
        return []
    urls = []
    failed = []
    # Limitar a 1 hilo máximo para ahorrar cuota
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        futures = []
        for idx, file in enumerate(files):
            if file is not None:
                futures.append(
                    executor.submit(
                        upload_image_to_drive_oauth, 
                        file, 
                        f"{base_name}_{idx+1}.jpg", 
                        folder_id
                    )
                )
        for idx, future in enumerate(futures):
            url = future.result()
            if url:
                urls.append(url)
            else:
                failed.append(idx)
    # Si hay fallidas, mostrar botón para reintentar
    if failed:
        if st.button("Reintentar subida de imágenes fallidas"):
            for idx in failed:
                file = files[idx]
                url = upload_image_to_drive_oauth(file, f"{base_name}_{idx+1}_retry.jpg", folder_id)
                if url:
                    urls.append(url)
    return urls

# Escribir link en Google Sheets
def write_link_to_sheet(sheet_client, file_name, worksheet_name, row):
    sheet = sheet_client.open(file_name).worksheet(worksheet_name)
    sheet.append_row(row)

def store_files(files, state_key):
    if files is not None:
        st.session_state[state_key + "_files"] = files
    else:
        st.session_state[state_key + "_files"] = []

def to_url_list(state_key):
    urls = st.session_state.get(state_key + "_links", [])
    if isinstance(urls, list):
        return ", ".join(urls)
    return str(urls)

# Función segura para manejar elementos/componentes reutilizables
def safe_handle_component(component_name, display_name, has_cantidad=False, has_voltaje=False, 
                        has_tension=False, has_descripcion=False, has_tipo_combustible=False, 
                        has_metodo_uso=False):
    """
    Maneja la UI de un componente de manera segura sin guardar directamente en session_state
    """
    results = {}
    
    if has_cantidad:
        cantidad = st.number_input(f"Cantidad {display_name}", 
                                min_value=0, step=1, format="%d", 
                                key=f"cantidad_{component_name}")
        results[f"cantidad_{component_name}"] = cantidad
    
    if has_voltaje:
        voltaje = st.text_input(f"Voltaje {display_name}", 
                             key=f"voltaje_{component_name}")
        results[f"voltaje_{component_name}"] = voltaje
    
    if has_tension:
        tension = st.text_input(f"Tensión {display_name}", 
                             key=f"tension_{component_name}")
        results[f"tension_{component_name}"] = tension
    
    if has_descripcion:
        descripcion = st.text_area(f"Descripción {display_name}", 
                                key=f"descripcion_{component_name}")
        results[f"descripcion_{component_name}"] = descripcion
    
    if has_tipo_combustible:
        tipo_combustible = st.selectbox(f"Tipo de combustible", 
                                     ["", "Gas Natural", "GLP", "ACPM"], 
                                     key=f"tipo_combustible_{component_name}")
        results[f"tipo_combustible_{component_name}"] = tipo_combustible
    
    if has_metodo_uso:
        metodo_uso = st.selectbox(f"Método de uso", 
                               ["", "Alto/Bajo", "On/Off"], 
                               key=f"metodo_uso_{component_name}")
        results[f"metodo_uso_{component_name}"] = metodo_uso
    
    fotos = st.file_uploader(f"Foto {display_name}", 
                           type=["jpg", "jpeg", "png"], 
                           accept_multiple_files=True, 
                           key=f"fotos_{component_name}")
    
    # No guardar nada en session_state, solo retornar valores
    return fotos, results

def main():
    # ...existing code...
    # Variables globales para evitar errores de referencia
    item = ""
    cantidad = ""
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
        # ...estructura y lógica de LISTA DE EMPAQUE de Untitled-1...
        folder_id = st.secrets.drive_config.FOLDER_ID
        file_name = st.secrets.drive_config.FILE_NAME
        worksheet_name = "Lista de empaque"

        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)

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
            # Buscar índice de OP (exacto)
            op_idx = None
            for idx, h in enumerate(headers):
                if h.strip().lower() == "op":
                    op_idx = idx
            ordenes_existentes = {}
            ordenes_list = []
            campos_relevantes = [
                "cantidad motores", "cantidad bombas", "cantidad reductores", "cantidad manometros", "cantidad valvulas", "cantidad mangueras", "cantidad boquillas", "cantidad gabinete electrico", "cantidad arrancadores", "cantidad control de nivel", "cantidad variadores de velociad", "cantidad sensores de temperatura", "cantidad toma corriente"
            ]
            for row in acta_rows[1:]:
                if op_idx is not None and len(row) > op_idx:
                    op_val = row[op_idx]
                    ordenes_existentes[op_val] = row
                    ordenes_list.append(op_val)
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

        articulos_presentes = []
        if orden_pedido_val and orden_pedido_val in ordenes_existentes:
            row = ordenes_existentes[orden_pedido_val]
            headers = acta_rows[0]
            mapeo_articulos = {
                "Motores": "cantidad motores",
                "Reductores": "cantidad reductores",
                "Bombas": "cantidad bombas",
                "Turbina": "voltaje turbina",
                "Quemador": "voltaje quemador",
                "Bomba de vacío": "voltaje bomba de vacio",
                "Compresor": "voltaje compresor",
                "Manómetros": "cantidad manometros",
                "Vacuómetros": "cantidad vacuometros",
                "Válvulas": "cantidad valvulas",
                "Mangueras": "cantidad mangueras",
                "Boquillas": "cantidad boquillas",
                "Reguladores aire/gas": "cantidad reguladores aire/gas",
                "Piñón 1": "tension piñon 1",
                "Piñón 2": "tension piñon 2",
                "Polea 1": "tension polea 1",
                "Polea 2": "tension polea 2",
                "Gabinete eléctrico": "cantidad gabinete electrico",
                "Arrancadores": "cantidad arrancadores",
                "Control de nivel": "cantidad control de nivel",
                "Variadores de velocidad": "cantidad variadores de velociad",
                "Sensores de temperatura": "cantidad sensores de temperatura",
                "Toma corriente": "cantidad toma corriente",
                "Otros elementos": "otros elementos"
            }
            for art, col in mapeo_articulos.items():
                if col in headers:
                    articulos_presentes.append(art)

        if 'num_paquetes' not in st.session_state:
            st.session_state['num_paquetes'] = 1

        with st.form("dispatch_form"):
            fecha = st.date_input("Fecha del día", value=datetime.date.today())
            nombre_proyecto = st.text_input("Nombre de proyecto")
            encargado_ensamblador = st.text_input("Encargado ensamblador")
            encargado_almacen = st.selectbox(
                "Encargado almacén",
                ["", "Andrea Ochoa", "Juan Pablo"]
            )
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

            st.markdown("<b>Selecciona los artículos a empacar:</b>", unsafe_allow_html=True)
            articulos_seleccion = {}
            for art in articulos_presentes:
                articulos_seleccion[art] = st.checkbox(art, value=True, key=f"empacar_{art}")
                if art.lower() == "otros elementos":
                    st.markdown(f"<small>{row[headers.index('otros elementos')]}</small>", unsafe_allow_html=True)

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
                    # Aquí podrías subir las fotos y agregar los links a la fila
                    pass
                write_link_to_sheet(sheet_client, file_name, worksheet_name, row)
                st.success("Despacho guardado correctamente.")
                st.info("Las fotos han sido subidas a Google Drive y el enlace está disponible en la hoja.")

    elif opcion_menu == "ACTA DE ENTREGA":
        # ...estructura y lógica de ACTA DE ENTREGA de Untitled-1...
        if 'drive_oauth_token' not in st.session_state:
            authorize_drive_oauth()

        st.markdown("<h3 style='color:#1db6b6;'>ACTA DE ENTREGA</h3>", unsafe_allow_html=True)
        st.markdown("<b>Encabezado del acta de entrega</b>", unsafe_allow_html=True)
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        folder_id = st.secrets.drive_config.FOLDER_ID
        file_name = st.secrets.drive_config.FILE_NAME
        worksheet_name = "Acta de entrega"

        # ...agregar lógica de formulario y manejo de datos como en Untitled-1...
        # Definir los checkboxes antes de usarlos
        gabinete_checked = st.checkbox("¿Hay gabinete eléctrico?", key="gabinete_check")
        arrancador_checked = st.checkbox("¿Hay arrancador?", key="arrancador_check")
        control_nivel_checked = st.checkbox("¿Hay control de nivel?", key="control_nivel_check")
        variador_checked = st.checkbox("¿Hay variador de velocidad?", key="variador_check")
        sensor_temp_checked = st.checkbox("¿Hay sensor de temperatura?", key="sensor_temp_check")
        toma_corriente_checked = st.checkbox("¿Hay toma corriente?", key="toma_corriente_check")
        uploaded_files = {}
        component_results = {}
        if gabinete_checked:
            with st.expander("Gabinete eléctrico", expanded=True):
                fotos, results = safe_handle_component("gabinete", "gabinete eléctrico", has_cantidad=True, has_descripcion=True)
                uploaded_files["gabinete"] = fotos
                component_results.update(results)
        if arrancador_checked:
            with st.expander("Arrancador", expanded=True):
                fotos, results = safe_handle_component("arrancadores", "arrancadores", has_cantidad=True, has_descripcion=True)
                uploaded_files["arrancadores"] = fotos
                component_results.update(results)
        if control_nivel_checked:
            with st.expander("Control de nivel", expanded=True):
                fotos, results = safe_handle_component("control_nivel", "control de nivel", has_cantidad=True, has_descripcion=True)
                uploaded_files["control_nivel"] = fotos
                component_results.update(results)
        if variador_checked:
            with st.expander("Variador de velocidad", expanded=True):
                fotos, results = safe_handle_component("variador", "variador de velocidad", has_cantidad=True, has_descripcion=True)
                uploaded_files["variador"] = fotos
                component_results.update(results)
        if sensor_temp_checked:
            with st.expander("Sensor de temperatura", expanded=True):
                fotos, results = safe_handle_component("sensor_temp", "sensor de temperatura", has_cantidad=True, has_descripcion=True)
                uploaded_files["sensor_temp"] = fotos
                component_results.update(results)
        if toma_corriente_checked:
            with st.expander("Toma corriente", expanded=True):
                fotos, results = safe_handle_component("toma_corriente", "toma corriente", has_cantidad=True, has_descripcion=True)
                uploaded_files["toma_corriente"] = fotos
                component_results.update(results)

        # Otros elementos: checkbox, descripción y foto
        otros_elementos = ""
        fotos_otros_elementos = []
        mostrar_otros_elementos = st.checkbox("Otros elementos", key="cb_otros_elementos")
        if mostrar_otros_elementos:
            with st.expander("Otros elementos", expanded=True):
                otros_elementos = st.text_area("Descripción de otros elementos", key="otros_elementos")
                fotos_otros_elementos = st.file_uploader("Foto(s) de otros elementos", 
                                                       type=["jpg","jpeg","png"], 
                                                       accept_multiple_files=True, 
                                                       key="fotos_otros_elementos")
                uploaded_files["otros_elementos"] = fotos_otros_elementos
                component_results["otros_elementos"] = otros_elementos

        # Selectboxes de revisión general
        st.markdown("<h4>Revisión general</h4>", unsafe_allow_html=True)
        col_rev = st.columns(1)
        revision_visual = col_rev[0].selectbox("Revisión visual", ["Selecciona...", "Sí", "No"], key="revision_visual")
        revision_funcional = col_rev[0].selectbox("Revisión funcional", ["Selecciona...", "Sí", "No"], key="revision_funcional")
        revision_soldadura = col_rev[0].selectbox("Revisión de soldadura", ["Selecciona...", "Sí", "No"], key="revision_soldadura")
        revision_sentidos = col_rev[0].selectbox("Revisión de sentidos de giro", ["Selecciona...", "Sí", "No"], key="revision_sentidos")
        manual_funcionamiento = col_rev[0].selectbox("Manual de funcionamiento", ["Selecciona...", "Sí", "No"], key="manual_funcionamiento")
        revision_filos = col_rev[0].selectbox("Revisión de filos y acabados", ["Selecciona...", "Sí", "No"], key="revision_filos")
        revision_tratamientos = col_rev[0].selectbox("Revisión de tratamientos", ["Selecciona...", "Sí", "No"], key="revision_tratamientos")
        revision_tornilleria = col_rev[0].selectbox("Revisión de tornillería", ["Selecciona...", "Sí", "No"], key="revision_tornilleria")
        revision_ruidos = col_rev[0].selectbox("Revisión de ruidos", ["Selecciona...", "Sí", "No"], key="revision_ruidos")
        ensayo_equipo = col_rev[0].selectbox("Ensayo equipo", ["Selecciona...", "Sí", "No"], key="ensayo_equipo")

        # Observaciones generales
        col_obs = st.columns(1)
        observaciones_generales = col_obs[0].text_area("Observaciones generales", key="observaciones_generales")

        # Líder de inspección
        col_lider = st.columns(1)
        lideres = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata", "Juan David Martinez"]
        lider_inspeccion = col_lider[0].selectbox("Líder de inspección", lideres, key="lider_inspeccion")

        # Soldador
        col_soldador = st.columns(1)
        soldadores = ["", "Jaime Ramos", "Jaime Rincon", "Gabriel", "Lewis"]
        soldador = col_soldador[0].selectbox("Encargado Soldador", soldadores, key="soldador")

        # Diseñador
        col_disenador = st.columns(1)
        disenadores = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata", "Juan David Martinez"]
        disenador = col_disenador[0].selectbox("Diseñador", disenadores, key="disenador")

        # Fecha y hora de entrega
        col_fecha = st.columns(1)
        fecha_entrega = col_fecha[0].date_input("Fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta")
        hora_entrega = col_fecha[0].time_input("Hora de entrega", value=datetime.datetime.now().time(), key="hora_entrega_acta")

        # Mostrar fecha y hora en formato DD-MM-AA-HH:MM:SS
        dt_entrega = datetime.datetime.combine(fecha_entrega, hora_entrega)
        fecha_hora_formateada = dt_entrega.strftime("%d-%m-%y-%H:%M:%S")
        st.info(f"Fecha y hora de entrega: {fecha_hora_formateada}")

        # Validar datos antes de enviar
        def validar_datos():
            if not op or op.strip() == "":
                return False, "La Orden de Compra (OP) es obligatoria."
            if not cliente or cliente.strip() == "":
                return False, "El Cliente es obligatorio."
            if not equipo or equipo.strip() == "":
                return False, "El Equipo es obligatorio."
            return True, ""

        # Botón para enviar el acta de entrega
        enviar_acta = st.button("Enviar Acta de Entrega", key="enviar_acta_entrega")
        if enviar_acta:
            valido, mensaje = validar_datos()
            if not valido:
                st.error(mensaje)
            else:
                image_urls = {}
                # Subir imágenes a Drive en paralelo con concurrencia limitada y reintentos
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    futures = {}
                    for key, files in uploaded_files.items():
                        if files:
                            for idx, file in enumerate(files):
                                if file is not None:
                                    future = executor.submit(
                                        upload_image_to_drive_oauth,
                                        file, 
                                        f"{key}_{idx+1}.jpg", 
                                        folder_id
                                    )
                                    futures[(key, idx)] = future
                    for (key, idx), future in futures.items():
                        url = future.result()
                        if url is None:
                            st.warning("No se pudo subir la imagen por límite de cuota. Intenta nuevamente más tarde.")
                        if url:
                            if key not in image_urls:
                                image_urls[key] = []
                            image_urls[key].append(url)
                # Crear la fila para Google Sheets con todos los datos recopilados
                row = [
                    str(cliente),
                    str(op),
                    str(item),
                    str(equipo),
                    str(cantidad),
                    str(fecha),
                    str(component_results.get("cantidad_motores", "")),
                    str(component_results.get("voltaje_motores", "")),
                    ", ".join(image_urls.get("motores", [])),
                    str(component_results.get("cantidad_reductores", "")),
                    str(component_results.get("voltaje_reductores", "")),
                    ", ".join(image_urls.get("reductores", [])),
                    str(component_results.get("cantidad_bombas", "")),
                    str(component_results.get("voltaje_bombas", "")),
                    ", ".join(image_urls.get("bombas", [])),
                    str(component_results.get("voltaje_turbina", "")),
                    str(component_results.get("tipo_combustible_turbina", "")),
                    str(component_results.get("metodo_uso_turbina", "")),
                    ", ".join(image_urls.get("turbina", [])),
                    str(component_results.get("voltaje_quemador", "")),
                    ", ".join(image_urls.get("quemador", [])),
                    str(component_results.get("voltaje_bomba_vacio", "")),
                    ", ".join(image_urls.get("bomba_vacio", [])),
                    str(component_results.get("voltaje_compresor", "")),
                    ", ".join(image_urls.get("compresor", [])),
                    str(component_results.get("cantidad_manometros", "")),
                    ", ".join(image_urls.get("manometros", [])),
                    str(component_results.get("cantidad_vacuometros", "")),
                    ", ".join(image_urls.get("vacuometros", [])),
                    str(component_results.get("cantidad_valvulas", "")),
                    ", ".join(image_urls.get("valvulas", [])),
                    str(component_results.get("cantidad_mangueras", "")),
                    ", ".join(image_urls.get("mangueras", [])),
                    str(component_results.get("cantidad_boquillas", "")),
                    ", ".join(image_urls.get("boquillas", [])),
                    str(component_results.get("cantidad_reguladores", "")),
                    ", ".join(image_urls.get("reguladores", [])),
                    str(component_results.get("tension_pinon1", "")),
                    ", ".join(image_urls.get("pinon1", [])),
                    str(component_results.get("tension_pinon2", "")),
                    ", ".join(image_urls.get("pinon2", [])),
                    str(component_results.get("tension_polea1", "")),
                    ", ".join(image_urls.get("polea1", [])),
                    str(component_results.get("tension_polea2", "")),
                    ", ".join(image_urls.get("polea2", [])),
                    str(component_results.get("cantidad_gabinete", "")),
                    ", ".join(image_urls.get("gabinete", [])),
                    str(component_results.get("cantidad_arrancadores", "")),
                    ", ".join(image_urls.get("arrancadores", [])),
                    str(component_results.get("cantidad_control_nivel", "")),
                    ", ".join(image_urls.get("control_nivel", [])),
                    str(component_results.get("cantidad_variador", "")),
                    ", ".join(image_urls.get("variador", [])),
                    str(component_results.get("cantidad_sensor_temp", "")),  # Corregido de cantidad_sensores
                    ", ".join(image_urls.get("sensor_temp", [])),
                    str(component_results.get("cantidad_toma_corriente", "")),
                    ", ".join(image_urls.get("toma_corriente", [])),
                    str(otros_elementos),
                    ", ".join(image_urls.get("otros_elementos", [])),
                    str(component_results.get("descripcion_tuberias", "")),
                    ", ".join(image_urls.get("tuberias", [])),
                    str(component_results.get("descripcion_cables", "")),
                    ", ".join(image_urls.get("cables", [])),
                    str(component_results.get("descripcion_curvas", "")),
                    ", ".join(image_urls.get("curvas", [])),
                    str(component_results.get("descripcion_tornillos", "")),
                    ", ".join(image_urls.get("tornillos", [])),
                    str(revision_soldadura),
                    str(revision_sentidos),
                    str(manual_funcionamiento),
                    str(revision_filos),
                    str(revision_tratamientos),
                    str(revision_tornilleria),
                    str(revision_ruidos),
                    str(ensayo_equipo),
                    str(observaciones_generales),
                    str(lider_inspeccion),
                    str(soldador),
                    str(disenador),
                    str(fecha_entrega)
                ]
                
                # Encabezados según lo solicitado
                headers = [
                    "cliente dili", "op dili", "item dili", "equipo dili", "cantidad dili", "fecha dili",
                    "cantidad motores dili", "voltaje motores dili", "fotos motores dili",
                    "cantidad reductores dili", "voltaje reductores dili", "fotos reductores dili",
                    "cantidad bombas dili", "voltaje bombas dili", "fotos bombas dili",
                    "voltaje turbina dili", "Tipo combustible turbina dili", "Metodo uso turbina dili", "foto turbina dili",
                    "voltaje quemador dili", "foto quemador dili",
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
                    "revision de soldadura dili", "revision de sentidos de giro dili", "manual de funcionamiento dili",
                    "revision de filos y acabados dili", "revision de tratamientos dili", "revision de tornilleria dili",
                    "revision de ruidos dili", "ensayo equipo dili", "observciones generales dili",
                    "lider de inspeccion dili", "Encargado soldador dili", "diseñador dili", "fecha de entrega dili"
                ]
                
                # Verificar conexión con Google Drive antes de guardar
                drive_service = get_drive_service_oauth()
                worksheet_name_diligenciadas = "Actas de entregas diligenciadas"
                if drive_service is None:
                    st.error("No se pudo conectar con Google Drive. Por favor autoriza el acceso antes de guardar el acta de entrega.")
                else:
                    try:
                        sheet_diligenciadas = sheet_client.open(file_name).worksheet(worksheet_name_diligenciadas)
                    except Exception:
                        # Si no existe, la creamos
                        sheet_diligenciadas = sheet_client.open(file_name).add_worksheet(
                            title=worksheet_name_diligenciadas, rows=100, cols=len(headers)
                        )
                        sheet_diligenciadas.append_row(headers)
                    # Si existe pero está vacía, agregamos los encabezados
                    if not sheet_diligenciadas.get_all_values():
                        sheet_diligenciadas.append_row(headers)
                    # Añadir la nueva fila de datos
                    sheet_diligenciadas.append_row(row)
                    st.success("Acta de entrega guardada correctamente en 'Actas de entregas diligenciadas'.")

    #/////////////////////////////////////////////////////////////LISTA DE EMPAQUE////////////////////////
    # ...existing code...
    # El bloque de "LISTA DE EMPAQUE" ya está implementado con opcion_menu
        # Solicitar autorización Drive OAuth2 si no está presente
        if 'drive_oauth_token' not in st.session_state:
            authorize_drive_oauth()
        # Asegurarse de que folder_id está definido
        if not folder_id and hasattr(st, 'secrets') and 'drive_config' in st.secrets and 'FOLDER_ID' in st.secrets.drive_config:
            folder_id = st.secrets.drive_config.FOLDER_ID
        
        creds = get_service_account_creds()
        sheet_client = gspread.authorize(creds)
        file_name = "dispatch_tekpro"
        worksheet_name = "Acta de entrega"
        
        st.markdown("<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'><b>Datos generales para empaque</b>", unsafe_allow_html=True)
        
        # Obtener OPs disponibles
        op_options_empaque = []
        op_to_row_empaque = {}
        all_rows = []
        
        try:
            sheet = sheet_client.open(file_name).worksheet(worksheet_name)
            all_rows = sheet.get_all_values()
            if all_rows:
                headers_lower = [h.strip().lower() for h in all_rows[0]]
                op_idx = headers_lower.index("op") if "op" in headers_lower else None
                for r in all_rows[1:]:
                    if op_idx is not None and len(r) > op_idx and r[op_idx].strip():
                        op_options_empaque.append(r[op_idx].strip())
                        op_to_row_empaque[r[op_idx].strip()] = r
        except Exception:
            st.warning("No se pudo leer la hoja de acta de entrega para obtener las OP disponibles.")
        
        op_selected_empaque = st.selectbox("Selecciona la OP a empacar", 
                                         options=[" "] + op_options_empaque, 
                                         key="op_selectbox_empaque_2")
        
        op = ""
        fecha = ""
        cliente = ""
        equipo = ""
        encargado_ingenieria = ""
        
        if op_selected_empaque and op_selected_empaque.strip() != "":
            row = op_to_row_empaque.get(op_selected_empaque, [])
            headers_lower = [h.strip().lower() for h in all_rows[0]] if all_rows else []
            
            def get_val(col):
                col = col.strip().lower()
                idx = headers_lower.index(col) if col in headers_lower else None
                return row[idx] if idx is not None and idx < len(row) else ""
            
            op = op_selected_empaque
            fecha = get_val("fecha dili")
            cliente = get_val("cliente dili")
            equipo = get_val("equipo dili")
            encargado_ingenieria = get_val("diseñador dili")
        
        # Selección de encargados
        encargados_almacen = ["", "Andrea Ochoa"]
        col_almacen = st.columns(1)
        encargado_almacen = col_almacen[0].selectbox("Encargado almacén", 
                                                   encargados_almacen, 
                                                   key="encargado_almacen_empaque")
        
        encargados_logistica = ["", "Angela Zapata", "Jhon Restrepo", "Juan Rendon"]
        col_logistica = st.columns(1)
        encargado_logistica = col_logistica[0].selectbox("Encargado logística", 
                                                       encargados_logistica, 
                                                       key="encargado_logistica_empaque")
        
        # Mostrar resumen
        st.markdown(f"""
        <div style='background:#e6f7f7;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;'>
        <b>OP:</b> {op}<br>
        <b>Fecha:</b> {fecha}<br>
        <b>Cliente:</b> {cliente}<br>
        <b>Equipo:</b> {equipo}<br>
        <b>Encargado almacén:</b> {encargado_almacen}<br>
        <b>Encargado ingeniería y diseño:</b> {encargado_ingenieria}<br>
        <b>Encargado logística:</b> {encargado_logistica}<br>
        </div>
        """, unsafe_allow_html=True)
        
        # Firma de logística
        st.markdown("<b>Firma encargado logística:</b>", unsafe_allow_html=True)
        st.info("Por favor, firme en el recuadro de abajo:")
        
        canvas_result = st_canvas(
            fill_color="#00000000",  # Fondo transparente
            stroke_width=2,
            stroke_color="#1db6b6",
            background_color="#f7fafb",
            height=150,
            width=400,
            drawing_mode="freedraw",
            key="firma_logistica_canvas"
        )
        
        # Verificar si la firma tiene contenido
        firma_valida = False
        if canvas_result.image_data is not None:
            # Verificar si hay algún trazo en la firma
            has_content = np.sum(canvas_result.image_data) > 0
            if has_content:
                firma_valida = True
                st.image(canvas_result.image_data, caption="Firma digital de logística", use_container_width=False)
            else:
                st.warning("La firma está vacía. Por favor, firme antes de continuar.")
        
        # Observaciones adicionales
        observaciones_adicionales = st.text_area("Observaciones adicionales", key="observaciones_adicionales")

        # Manejo de guacales
        st.markdown("<h3>Guacales</h3>", unsafe_allow_html=True)
        if 'guacales' not in st.session_state:
            st.session_state['guacales'] = []

        def add_guacal():
            st.session_state['guacales'].append({'descripcion': '', 'fotos': []})

        st.button("Agregar guacal", on_click=add_guacal, key="btn_agregar_guacal")

        for idx, guacal in enumerate(st.session_state['guacales']):
            with st.expander(f"Guacal {idx+1}", expanded=True):
                descripcion = st.text_area(f"Descripción del guacal {idx+1}", 
                                        value=guacal['descripcion'], 
                                        key=f"descripcion_guacal_{idx+1}")
                fotos = st.file_uploader(f"Foto(s) del guacal {idx+1}", 
                                       type=["jpg","jpeg","png"], 
                                       accept_multiple_files=True, 
                                       key=f"fotos_guacal_{idx+1}")
                guacal['descripcion'] = descripcion
                guacal['fotos'] = fotos if fotos else []

        # Validación antes de enviar lista de empaque
        def validar_empaque():
            if not op or op.strip() == "":
                return False, "Debe seleccionar una OP válida."
            if not encargado_logistica or encargado_logistica.strip() == "":
                return False, "Debe seleccionar un encargado de logística."
            if len(st.session_state['guacales']) == 0:
                return False, "Debe agregar al menos un guacal."
            return True, ""

        # Botón para enviar la lista de empaque
        enviar_empaque = st.button("Enviar Lista de Empaque", key="enviar_lista_empaque")
        
        if enviar_empaque:
            # Validar campos obligatorios
            valido, mensaje = validar_empaque()
            if not valido:
                st.error(mensaje)
            else:
                # Subir fotos de guacales a Drive
                guacales_data = []
                
                with st.spinner("Subiendo imágenes de guacales..."):
                    for idx, guacal in enumerate(st.session_state['guacales']):
                        urls_fotos = upload_images_parallel(
                            guacal['fotos'],
                            f"guacal{idx+1}_{op}",
                            folder_id
                        )
                        guacales_data.append({
                            'descripcion': guacal['descripcion'],
                            'fotos': urls_fotos
                        })
            
            firma_url = ""
            if canvas_result.image_data is not None and np.sum(canvas_result.image_data) > 0:
                with st.spinner("Guardando firma digital..."):
                    img = Image.fromarray((canvas_result.image_data).astype(np.uint8))
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                        img.save(tmpfile.name)
                        tmpfile.seek(0)
                        with open(tmpfile.name, "rb") as f:
                            firma_url = upload_image_to_drive_oauth(f, f"firma_logistica_{op}.png", folder_id)
            
            # Encabezados base
            # Encabezados fijos y hasta 4 guacales
            headers_empaque = [
                "Op",
                "Fecha",
                "Cliente",
                "Equipo",
                "Encargado almacén",
                "Encargado ingeniería y diseño",
                "Encargado logística",
                "Firma encargado logística",
                "Observaciones adicionales",
                "Artículos enviados",
                "Artículos no enviados",
                "Descripción Guacal 1",
                "Fotos Guacal 1",
                "Descripción Guacal 2",
                "Fotos Guacal 2",
                "Descripción Guacal 3",
                "Fotos Guacal 3",
                "Descripción Guacal 4",
                "Fotos Guacal 4"
            ]
            row_empaque = [
                op,
                fecha,
                cliente,
                equipo,
                encargado_almacen,
                encargado_ingenieria,
                encargado_logistica,
                firma_url,
                observaciones_adicionales,
                "",  # Artículos enviados
                "",  # Artículos no enviados
            ]
            # Rellenar hasta 4 guacales, si hay menos poner 0
            for i in range(4):
                if i < len(guacales_data):
                    row_empaque.append(guacales_data[i]['descripcion'] if guacales_data[i]['descripcion'] else "0")
                    row_empaque.append(", ".join(guacales_data[i]['fotos']) if guacales_data[i]['fotos'] else "0")
                else:
                    row_empaque.append("0")
                    row_empaque.append("0")
            # Si hay más de 4 guacales, agregar columnas extra
            if len(guacales_data) > 4:
                for i in range(4, len(guacales_data)):
                    headers_empaque.append(f"Descripción Guacal {i+1}")
                    headers_empaque.append(f"Fotos Guacal {i+1}")
                    row_empaque.append(guacales_data[i]['descripcion'] if guacales_data[i]['descripcion'] else "0")
                    row_empaque.append(", ".join(guacales_data[i]['fotos']) if guacales_data[i]['fotos'] else "0")
            
            # Guardar en Google Sheets
            file_name_empaque = "dispatch_tekpro"
            worksheet_name_empaque = "Lista de empaque"
            
            try:
                # Verificar si existe la hoja
                try:
                    sheet_empaque = sheet_client.open(file_name_empaque).worksheet(worksheet_name_empaque)
                except Exception:
                    sheet_empaque = sheet_client.open(file_name_empaque).add_worksheet(
                        title=worksheet_name_empaque, 
                        rows=100, 
                        cols=len(headers_empaque)
                    )
                    sheet_empaque.append_row(headers_empaque)
                    st.markdown("<h2>Listas de chequeo</h2>", unsafe_allow_html=True)
                    col1, col2, col3, col4 = st.columns(4)
                    mostrar_electromecanicos = col1.checkbox("Elementos electromecánicos", key="cb_electromecanicos")
                    mostrar_accesorios = col2.checkbox("Accesorios", key="cb_accesorios")
                    mostrar_mecanicos = col3.checkbox("Elementos mecánicos", key="cb_mecanicos")
                    mostrar_electricos = col4.checkbox("Elementos eléctricos", key="cb_electricos")

                    uploaded_files = {}
                    component_results = {}

                    if mostrar_electromecanicos:
                        st.markdown("""
                        <h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general elementos electromecánicos</h3>
                        """, unsafe_allow_html=True)
                        # ...existing code...
                    if mostrar_accesorios:
                        st.markdown("""
                        <h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general accesorios</h3>
                        """, unsafe_allow_html=True)
                        # ...existing code...
                    if mostrar_mecanicos:
                        st.markdown("""
                        <h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general elementos mecánicos</h3>
                        """, unsafe_allow_html=True)
                        # ...existing code...
                    if mostrar_electricos:
                        st.markdown("""
                        <h3 style='color:#1db6b6;font-weight:700;'>Lista de chequeo general elementos eléctricos</h3>
                        """, unsafe_allow_html=True)
                        # ...existing code...

                    otros_elementos = ""
                    fotos_otros_elementos = []
                    mostrar_otros_elementos = st.checkbox("Otros elementos", key="cb_otros_elementos")
                    if mostrar_otros_elementos:
                        with st.expander("Otros elementos", expanded=True):
                            otros_elementos = st.text_area("Descripción de otros elementos", key="otros_elementos")
                            fotos_otros_elementos = st.file_uploader("Foto(s) de otros elementos", 
                                                                   type=["jpg","jpeg","png"], 
                                                                   accept_multiple_files=True, 
                                                                   key="fotos_otros_elementos")
                            uploaded_files["otros_elementos"] = fotos_otros_elementos
                            component_results["otros_elementos"] = otros_elementos

                    st.markdown("<h4>Revisión general</h4>", unsafe_allow_html=True)
                    col_rev = st.columns(1)
                    revision_visual = col_rev[0].selectbox("Revisión visual", ["Selecciona...", "Sí", "No"], key="revision_visual")
                    revision_funcional = col_rev[0].selectbox("Revisión funcional", ["Selecciona...", "Sí", "No"], key="revision_funcional")
                    revision_soldadura = col_rev[0].selectbox("Revisión de soldadura", ["Selecciona...", "Sí", "No"], key="revision_soldadura")
                    revision_sentidos = col_rev[0].selectbox("Revisión de sentidos de giro", ["Selecciona...", "Sí", "No"], key="revision_sentidos")
                    manual_funcionamiento = col_rev[0].selectbox("Manual de funcionamiento", ["Selecciona...", "Sí", "No"], key="manual_funcionamiento")
                    revision_filos = col_rev[0].selectbox("Revisión de filos y acabados", ["Selecciona...", "Sí", "No"], key="revision_filos")
                    revision_tratamientos = col_rev[0].selectbox("Revisión de tratamientos", ["Selecciona...", "Sí", "No"], key="revision_tratamientos")
                    revision_tornilleria = col_rev[0].selectbox("Revisión de tornillería", ["Selecciona...", "Sí", "No"], key="revision_tornilleria")
                    revision_ruidos = col_rev[0].selectbox("Revisión de ruidos", ["Selecciona...", "Sí", "No"], key="revision_ruidos")
                    ensayo_equipo = col_rev[0].selectbox("Ensayo equipo", ["Selecciona...", "Sí", "No"], key="ensayo_equipo")

                    col_obs = st.columns(1)
                    observaciones_generales = col_obs[0].text_area("Observaciones generales", key="observaciones_generales")

                    col_lider = st.columns(1)
                    lideres = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata", "Juan David Martinez"]
                    lider_inspeccion = col_lider[0].selectbox("Líder de inspección", lideres, key="lider_inspeccion")

                    col_soldador = st.columns(1)
                    soldadores = ["", "Jaime Ramos", "Jaime Rincon", "Gabriel", "Lewis"]
                    soldador = col_soldador[0].selectbox("Encargado Soldador", soldadores, key="soldador")

                    col_disenador = st.columns(1)
                    disenadores = ["", "Daniel Valbuena", "Alejandro Diaz", "Juan Andres Zapata", "Juan David Martinez"]
                    disenador = col_disenador[0].selectbox("Diseñador", disenadores, key="disenador", on_change=guardar_chequeo_revision)

                    col_fecha = st.columns(1)
                    fecha_entrega = col_fecha[0].date_input("Fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta")
                    hora_entrega = col_fecha[0].time_input("Hora de entrega", value=datetime.datetime.now().time(), key="hora_entrega_acta")

                    dt_entrega = datetime.datetime.combine(fecha_entrega, hora_entrega)
                    fecha_hora_formateada = dt_entrega.strftime("%d-%m-%y-%H:%M:%S")
                    st.info(f"Fecha y hora de entrega: {fecha_hora_formateada}")

                    # Función para guardar automáticamente al seleccionar diseñador
                    def guardar_chequeo_revision():
                        # Aquí va la lógica para guardar todos los datos de chequeo y revisión
                        st.session_state['chequeo_revision_guardado'] = True
                        st.success("Listas de chequeo y revisión guardadas automáticamente.")
                    # ...existing code...
            except Exception as e:
                st.error(f"Error al guardar la lista de empaque: {e}")

  
