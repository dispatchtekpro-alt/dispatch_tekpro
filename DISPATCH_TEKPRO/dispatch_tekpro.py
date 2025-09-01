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


            # 5. Accesorios varios (solo cantidad y foto)
            accesorios_varios_items = [
                {"key": "tuberias", "label": "Tuberías"},
                {"key": "curvas", "label": "Curvas"},
                {"key": "tornilleria", "label": "Tornillería"}
            ]
            st.markdown("<hr>", unsafe_allow_html=True)
            st.subheader("Lista de chequeo accesorios varios")
            global accesorios_varios_cant, accesorios_varios_foto
            global accesorios_varios_desc, accesorios_varios_foto
            accesorios_varios_desc = {}
            accesorios_varios_foto = {}
            for item in accesorios_varios_items:
                key = item["key"]
                label = item["label"]
                accesorios_varios_desc[key] = st.text_area(f"Descripción {label}", key=f"desc_{key}_accesorios_varios")
                accesorios_varios_foto[key] = st.file_uploader(f"Foto {label}", type=["jpg","jpeg","png"], accept_multiple_files=True, key=f"foto_{key}_accesorios_varios")


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

try:
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
    acta_sheet = sheet_client.open(file_name).worksheet("Acta de entrega")
    acta_rows = acta_sheet.get_all_values()
    headers = acta_rows[0] if acta_rows else []
    # Buscar índice de OP (exacto)
    op_idx = None
    for idx, h in enumerate(headers):
        if h.strip().lower() == "op":
            op_idx = idx
            break
    ordenes_existentes = {}
    ordenes_list = []
    # Definir los campos relevantes para considerar una OP como completa (igual que en ACTA DE ENTREGA)
    campos_relevantes = [
        "cantidad motores", "cantidad bombas", "cantidad reductores", "cantidad manometros", "cantidad valvulas", "cantidad mangueras", "cantidad boquillas", "cantidad gabinete electrico", "cantidad arrancadores", "cantidad control de nivel", "cantidad variadores de velociad", "cantidad sensores de temperatura", "cantidad toma corriente"
    ]
    for row in acta_rows[1:]:
        if op_idx is not None and len(row) > op_idx:
            orden = row[op_idx]
            # Verificar si la OP está completa
            completa = False
            for campo in campos_relevantes:
                if campo in headers:
                    idx_campo = headers.index(campo)
                    if idx_campo < len(row):
                        valor = row[idx_campo]
                        if valor and str(valor).strip() not in ["", "0", "no", "No"]:
                            completa = True
                            break
            if completa:
                ordenes_existentes[orden] = row
                ordenes_list.append(orden)
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



# Mostrar TODOS los artículos posibles del acta de entrega como opciones en lista de empaque
articulos_presentes = []
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
    "Otros elementos": "otros elementos",
    # Accesorios varios
    "Tuberías": None,
    "Curvas": None,
    "Tornillería": None
}
if orden_pedido_val and orden_pedido_val in ordenes_existentes:
    row = ordenes_existentes[orden_pedido_val]
    headers = acta_rows[0]
    # Solo mostrar los artículos que realmente fueron seleccionados en el acta (valor distinto de vacío o 0)
    for art, col in mapeo_articulos.items():
        if col is not None:
            try:
                idx = headers.index(col)
                val = row[idx] if idx < len(row) else ""
                if isinstance(val, str):
                    val_ok = val.strip() != "" and val.strip() != "0"
                else:
                    val_ok = val not in (None, 0, "0", "")
                if val_ok:
                    articulos_presentes.append(art)
            except Exception:
                pass

# Estado dinámico para número de paquetes
if 'num_paquetes' not in st.session_state:
    st.session_state['num_paquetes'] = 1

# Leer artículos de BDD SAG
try:
    bdd_sag_sheet = sheet_client.open(file_name).worksheet("BDD SAG")
    bdd_sag_rows = bdd_sag_sheet.get_all_values()
    bdd_sag_headers = bdd_sag_rows[0] if bdd_sag_rows else []
    # Buscar columnas relevantes: código, descripción, unidad
    codigo_idx = descripcion_idx = unidad_idx = None
    for idx, h in enumerate(bdd_sag_headers):
        h_low = h.strip().lower()
        if h_low in ["codigo", "código", "code"]:
            codigo_idx = idx
        elif h_low in ["descripcion", "descripción", "artículo", "articulo", "nombre"]:
            descripcion_idx = idx
        elif h_low in ["unidad", "unid.", "unid", "unit"]:
            unidad_idx = idx
    bdd_sag_articulos = []
    bdd_sag_articulos_fmt = []
    for row in bdd_sag_rows[1:]:
        if codigo_idx is not None and descripcion_idx is not None and unidad_idx is not None:
            if len(row) > max(codigo_idx, descripcion_idx, unidad_idx):
                code = row[codigo_idx].strip()
                desc = row[descripcion_idx].strip()
                unidad = row[unidad_idx].strip()
                label = f"{code}-{desc}-{unidad}"
                bdd_sag_articulos.append(label)
                bdd_sag_articulos_fmt.append((label, code, desc, unidad))
        elif descripcion_idx is not None:
            # fallback: just description
            desc = row[descripcion_idx].strip()
            bdd_sag_articulos.append(desc)
            bdd_sag_articulos_fmt.append((desc, "", desc, ""))
except Exception:
    bdd_sag_articulos = []
    bdd_sag_articulos_fmt = []

with st.form("dispatch_form"):
    import datetime
    # Autocompletar nombre_proyecto y encargado_ingenieria si la OP existe
    auto_nombre_proyecto = ""
    auto_encargado_ingenieria = ""
    if orden_pedido_val and orden_pedido_val in ordenes_existentes:
        row = ordenes_existentes[orden_pedido_val]
        headers = acta_rows[0]
        # Buscar índice de cliente y diseñador
        cliente_idx = None
        disenador_idx = None
        for idx, h in enumerate(headers):
            if h.strip().lower() == "cliente":
                cliente_idx = idx
            if h.strip().lower() == "diseñador":
                disenador_idx = idx
        if cliente_idx is not None and len(row) > cliente_idx:
            auto_nombre_proyecto = row[cliente_idx]
        if disenador_idx is not None and len(row) > disenador_idx:
            auto_encargado_ingenieria = row[disenador_idx]
    fecha = st.date_input("Fecha del día", value=datetime.date.today())
    nombre_proyecto = st.text_input("Nombre de proyecto", value=auto_nombre_proyecto)
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
        ],
        index=["", "Alejandro Diaz", "Juan David Martinez", "Juan Andres Zapata", "Daniel Valbuena", "Victor Manuel Baena", "Diomer Arbelaez", "Jose Perez"].index(auto_encargado_ingenieria) if auto_encargado_ingenieria in ["", "Alejandro Diaz", "Juan David Martinez", "Juan Andres Zapata", "Daniel Valbuena", "Victor Manuel Baena", "Diomer Arbelaez", "Jose Perez"] else 0
    )

    st.markdown("<b>Selecciona los artículos a empacar:</b>", unsafe_allow_html=True)
    articulos_seleccion = {}
    for art in articulos_presentes:
        articulos_seleccion[art] = st.checkbox(art, value=True, key=f"empacar_{art}")
        # Si es 'Otros elementos', mostrar la descripción registrada en el acta justo debajo
        if art.lower() == "otros elementos":
            desc_otros = ""
            # Buscar columna de descripción de otros elementos
            for idx, h in enumerate(headers):
                if "otros elementos" in h.lower():
                    desc_otros = row[idx] if idx < len(row) else ""
                    break
            if desc_otros and desc_otros.strip():
                st.markdown(f"<div style='margin-left:2em; color:#6c757d; font-size:0.97em; background:#f7fafb; border-left:3px solid #1db6b6; padding:0.5em 1em; border-radius:6px; margin-bottom:0.5em;'><b>Descripción:</b> {desc_otros}</div>", unsafe_allow_html=True)

    # Quitar el <hr> literal, solo dejar la línea de paquetes
    st.markdown("<b>Paquetes (guacales):</b>", unsafe_allow_html=True)
    paquetes = []
    for i in range(st.session_state['num_paquetes']):
        st.markdown(f"<b>Paquete {i+1}</b>", unsafe_allow_html=True)
        articulos_guacal = st.multiselect(
            f"Agregar artículos de BDD SAG al paquete {i+1}",
            options=bdd_sag_articulos,
            key=f"bddsag_paquete_{i+1}"
        )
        desc_bdd = ""
        if articulos_guacal:
            desc_bdd = "(" + ",".join(articulos_guacal) + ")"
        desc_adicional = st.text_area(
            f"Descripción adicional paquete {i+1}",
            key=f"desc_adic_paquete_{i+1}"
        )
        fotos = st.file_uploader(f"Fotos paquete {i+1}", type=["jpg", "jpeg", "png"], key=f"fotos_paquete_{i+1}", accept_multiple_files=True)
        paquetes.append({
            "desc_bdd": desc_bdd,
            "desc_adicional": desc_adicional,
            "fotos": fotos,
            "articulos_guacal": articulos_guacal
        })
    if st.form_submit_button("Agregar otro paquete"):
        st.session_state['num_paquetes'] += 1
        st.experimental_rerun()

    encargado_logistica = st.text_input("Encargado logística")
    from streamlit_drawable_canvas import st_canvas
    st.markdown("<b>Firma encargado logística:</b>", unsafe_allow_html=True)
    canvas_result = st_canvas(
        fill_color="#000000",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#fff",
        height=150,
        width=400,
        drawing_mode="freedraw",
        key="canvas_firma_logistica"
    )
    firma_logistica_img = None
    firma_logistica_url = ""
    if canvas_result.image_data is not None:
        import io
        from PIL import Image
        import numpy as np
        # Convertir a imagen y guardar en memoria
        img = Image.fromarray((canvas_result.image_data * 255).astype(np.uint8)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        firma_logistica_img = buf
    observaciones = st.text_area("Observaciones adicionales")
    submitted = st.form_submit_button("Guardar despacho")

if submitted:
    if not articulos_presentes:
        st.error("No hay artículos para empacar en esta OP.")
    else:

        # Estructura recomendada de encabezados:
        # OP, Fecha, Nombre de proyecto, Encargado ensamblador, Encargado almacén, Encargado ingeniería y diseño, Observaciones adicionales,
        # Artículos enviados, Artículos no enviados,
        # Descripción Guacal 1, Descripción adicional Guacal 1, Dimensiones Guacal 1, Peso Neto Guacal 1, Peso Bruto Guacal 1, Fotos Guacal 1, ...
        sheet = sheet_client.open(file_name).worksheet(worksheet_name)
        all_rows = sheet.get_all_values()
        headers = all_rows[0] if all_rows else []
        # Determinar artículos enviados/no enviados
        articulos_enviados = [art for art, checked in articulos_seleccion.items() if checked]
        articulos_no_enviados = [art for art, checked in articulos_seleccion.items() if not checked]
        # Construir encabezados dinámicamente según la cantidad de paquetes
        base_headers = [
            "OP", "Fecha", "Nombre de proyecto", "Encargado almacén", "Encargado ingeniería y diseño", "Encargado logística", "Firma encargado logística", "Observaciones adicionales",
            "Artículos enviados", "Artículos no enviados"
        ]
        paquete_headers = []
        for i in range(st.session_state['num_paquetes']):
            n = i+1
            paquete_headers.extend([
                f"Descripción Guacal {n}",
                f"Descripción adicional Guacal {n}",
                f"Fotos Guacal {n}"
            ])
        full_headers = base_headers + paquete_headers
        # Si los headers actuales no coinciden, actualizarlos
        if headers != full_headers:
            if not all_rows:
                sheet.append_row(full_headers)
            else:
                sheet.resize(rows=1)
                sheet.update('A1', [full_headers])
        # Subir firma a Drive y obtener enlace
        firma_logistica_url = ""
        if firma_logistica_img is not None:
            try:
                image_filename = f"FirmaLogistica_{orden_pedido_val}.png"
                firma_logistica_url = upload_image_to_drive_oauth(firma_logistica_img, image_filename, folder_id)
            except Exception as e:
                firma_logistica_url = f"Error: {e}"
        # Preparar la fila a guardar
        row_data = [
            str(orden_pedido_val),
            str(fecha),
            str(nombre_proyecto),
            str(encargado_almacen),
            str(encargado_ingenieria),
            str(encargado_logistica),
            str(firma_logistica_url),
            str(observaciones),
            ", ".join(articulos_enviados),
            ", ".join(articulos_no_enviados)
        ]
        for i, paquete in enumerate(paquetes):
            # Subir fotos a Drive y obtener links
            fotos_links = []
            if paquete["fotos"]:
                for idx, f in enumerate(paquete["fotos"], start=1):
                    try:
                        import io
                        file_stream = io.BytesIO(f.read())
                        image_filename = f"Guacal{i+1}_{orden_pedido_val}_{idx}.jpg"
                        public_url = upload_image_to_drive_oauth(file_stream, image_filename, folder_id)
                        fotos_links.append(public_url)
                    except Exception as e:
                        fotos_links.append(f"Error: {e}")
            row_data.extend([
                paquete["desc_bdd"],
                paquete["desc_adicional"],
                ", ".join(fotos_links)
            ])
        sheet.append_row(row_data)
        st.success("Información de la lista de empaque guardada correctamente en Google Sheets.")


if opcion_menu == "ACTA DE ENTREGA":
    # Autorización Google Drive OAuth2 igual que en LISTA DE EMPAQUE
    if 'drive_oauth_token' not in st.session_state:
        authorize_drive_oauth()

    st.markdown("<h3 style='color:#1db6b6;'>ACTA DE ENTREGA</h3>", unsafe_allow_html=True)
    st.markdown("<b>Encabezado del acta de entrega</b>", unsafe_allow_html=True)
    # Mostrar datos generales en un recuadro visual
    # Inicializar variables generales si no existen
    auto_cliente = globals().get('auto_cliente', '')
    op_selected = globals().get('op_selected', '')
    auto_equipo = globals().get('auto_equipo', '')
    auto_item = globals().get('auto_item', '')
    auto_cantidad = globals().get('auto_cantidad', '')
    auto_fecha = globals().get('auto_fecha', '')
    st.markdown(f'''
        <div style="background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;">
            <b style="color:#1db6b6;">Datos generales:</b><br>
            <b>Cliente:</b> {auto_cliente} &nbsp; | &nbsp;
            <b>OP:</b> {op_selected} &nbsp; | &nbsp;
            <b>Equipo:</b> {auto_equipo} &nbsp; | &nbsp;
            <b>Item:</b> {auto_item} &nbsp; | &nbsp;
            <b>Cantidad:</b> {auto_cantidad} &nbsp; | &nbsp;
            <b>Fecha:</b> {auto_fecha}
        </div>
    ''', unsafe_allow_html=True)
    # Definir seccion_articulo antes de su uso
    def seccion_articulo(nombre, mostrar, campos):
        if mostrar:
            with st.expander(f"{nombre}", expanded=False):
                st.markdown(f"""<div style='background:#f7fafb;padding:1em 1.5em 1em 1.5em;border-radius:8px;border:1px solid #1db6b6;margin-bottom:1.5em;border-top: 3px solid #1db6b6;'><b style='font-size:1.1em;color:#1db6b6'>{nombre}</b>""", unsafe_allow_html=True)
                resultados = {}
                for campo in campos:
                    if campo['tipo'] == 'number':
                        resultados[campo['nombre']] = st.number_input(campo['label'], min_value=0, step=1, format="%d")
                    elif campo['tipo'] == 'text':
                        resultados[campo['nombre']] = st.text_input(campo['label'])
                    elif campo['tipo'] == 'text_area':
                        resultados[campo['nombre']] = st.text_area(campo['label'])
                    elif campo['tipo'] == 'file':
                        resultados[campo['nombre']] = st.file_uploader(campo['label'], type=["jpg","jpeg","png"], accept_multiple_files=True, key=f"fotos_{nombre}")
                st.markdown("</div>", unsafe_allow_html=True)
                return resultados
        else:
            return {campo['nombre']: 0 if campo['tipo'] == 'number' else "" for campo in campos}
    # ...existing code...

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

    # 3. Elementos mecánicos
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
        otros_elementos = st.text_area("otros elementos")
    with col_otros2:
        fotos_otros_elementos = st.file_uploader("Fotos otros elementos", type=["jpg","jpeg","png"], accept_multiple_files=True, key="fotos_otros_elementos")

    st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin: 1.5em 0;'>", unsafe_allow_html=True)
    st.markdown("<b>Preguntas de revisión (Sí/No)</b>", unsafe_allow_html=True)
    revision_soldadura = st.selectbox("revision de soldadura", ["", "Sí", "No"])
    revision_sentidos = st.selectbox("revision de sentidos de giro", ["", "Sí", "No"])
    manual_funcionamiento = st.selectbox("manual de funcionamiento", ["", "Sí", "No"])
    revision_filos = st.selectbox("revision de filos y acabados", ["", "Sí", "No"])
    revision_tratamientos = st.selectbox("revision de tratamientos", ["", "Sí", "No"])
    revision_tornilleria = st.selectbox("revision de tornilleria", ["", "Sí", "No"])
    revision_ruidos = st.selectbox("revision de ruidos", ["", "Sí", "No"])
    ensayo_equipo = st.selectbox("ensayo equipo", ["", "Sí", "No"])
    st.markdown("<hr style='border: none; border-top: 2px solid #1db6b6; margin: 1.5em 0;'>", unsafe_allow_html=True)
    st.markdown("<b>Información final</b>", unsafe_allow_html=True)
    observaciones_generales = st.text_area("observciones generales")

    lider_inspeccion = st.text_input("lider de inspeccion")
    encargado_ensamblador = st.text_input("encargado ensamblador")
    disenador = st.selectbox(
        "diseñador",
        ["", "Daniel Valbuena", "Juan David Martinez", "Juan Andres Zapata", "Alejandro Diaz"]
    )
    fecha_entrega = st.date_input("fecha de entrega", value=datetime.date.today(), key="fecha_entrega_acta")

    submitted = st.form_submit_button("Guardar acta de entrega")

    # Validación: solo encabezado y responsables son obligatorios
    if submitted:
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

        # Definir variables de los inputs
        # Inicializar variables de checklist si no existen
        def safe_get(var, default):
            return var if var is not None else default

        cantidad_motores = globals().get('cantidad_motores', 0)
        voltaje_motores = globals().get('voltaje_motores', '')
        fotos_motores = globals().get('fotos_motores', [])
        cantidad_reductores = globals().get('cantidad_reductores', 0)
        voltaje_reductores = globals().get('voltaje_reductores', '')
        fotos_reductores = globals().get('fotos_reductores', [])
        cantidad_bombas = globals().get('cantidad_bombas', 0)
        voltaje_bombas = globals().get('voltaje_bombas', '')
        fotos_bombas = globals().get('fotos_bombas', [])
        voltaje_turbina = globals().get('voltaje_turbina', '')
        foto_turbina = globals().get('foto_turbina', [])
        voltaje_quemador = globals().get('voltaje_quemador', '')
        foto_quemador = globals().get('foto_quemador', [])
        voltaje_bomba_vacio = globals().get('voltaje_bomba_vacio', '')
        foto_bomba_vacio = globals().get('foto_bomba_vacio', [])
        voltaje_compresor = globals().get('voltaje_compresor', '')
        foto_compresor = globals().get('foto_compresor', [])
        cantidad_manometros = globals().get('cantidad_manometros', 0)
        foto_manometros = globals().get('foto_manometros', [])
        cantidad_vacuometros = globals().get('cantidad_vacuometros', 0)
        foto_vacuometros = globals().get('foto_vacuometros', [])
        cantidad_valvulas = globals().get('cantidad_valvulas', 0)
        foto_valvulas = globals().get('foto_valvulas', [])
        cantidad_mangueras = globals().get('cantidad_mangueras', 0)
        foto_mangueras = globals().get('foto_mangueras', [])
        cantidad_boquillas = globals().get('cantidad_boquillas', 0)
        foto_boquillas = globals().get('foto_boquillas', [])
        cantidad_reguladores = globals().get('cantidad_reguladores', 0)
        foto_reguladores = globals().get('foto_reguladores', [])
        tension_pinon1 = globals().get('tension_pinon1', '')
        foto_pinon1 = globals().get('foto_pinon1', [])
        tension_pinon2 = globals().get('tension_pinon2', '')
        foto_pinon2 = globals().get('foto_pinon2', [])
        tension_polea1 = globals().get('tension_polea1', '')
        foto_polea1 = globals().get('foto_polea1', [])
        tension_polea2 = globals().get('tension_polea2', '')
        foto_polea2 = globals().get('foto_polea2', [])
        cantidad_gabinete = globals().get('cantidad_gabinete', 0)
        foto_gabinete = globals().get('foto_gabinete', [])
        cantidad_arrancadores = globals().get('cantidad_arrancadores', 0)
        foto_arrancadores = globals().get('foto_arrancadores', [])
        cantidad_control_nivel = globals().get('cantidad_control_nivel', 0)
        foto_control_nivel = globals().get('foto_control_nivel', [])
        cantidad_variadores = globals().get('cantidad_variadores', 0)
        foto_variadores = globals().get('foto_variadores', [])
        cantidad_sensores = globals().get('cantidad_sensores', 0)
        foto_sensores = globals().get('foto_sensores', [])
        cantidad_toma_corriente = globals().get('cantidad_toma_corriente', 0)
        foto_toma_corrientes = globals().get('foto_toma_corrientes', [])
        otros_elementos = globals().get('otros_elementos', '')
        fotos_otros_elementos = globals().get('fotos_otros_elementos', [])
        accesorios_varios_desc = globals().get('accesorios_varios_desc', {"tuberias":"","curvas":"","tornilleria":""})
        accesorios_varios_foto = globals().get('accesorios_varios_foto', {"tuberias":[],"curvas":[],"tornilleria":[]})
        cliente_val = auto_cliente if auto_cliente else ""
        op_val = op_selected if op_selected else ""
        item_val = auto_item if auto_item else ""
        equipo_val = auto_equipo if auto_equipo else ""
        cantidad_val = auto_cantidad if auto_cantidad else ""
        fecha_val = auto_fecha if auto_fecha else ""

        row = [
            str(cliente_val), str(op_val), str(item_val), str(equipo_val), str(cantidad_val), str(fecha_val), str(encargado_ensamblador),
            str(cantidad_motores), str(voltaje_motores), serializa_fotos(fotos_motores, f"Motores_{op_val}", folder_id),
            str(cantidad_reductores), str(voltaje_reductores), serializa_fotos(fotos_reductores, f"Reductores_{op_val}", folder_id),
            str(cantidad_bombas), str(voltaje_bombas), serializa_fotos(fotos_bombas, f"Bombas_{op_val}", folder_id),
            str(voltaje_turbina), serializa_fotos(foto_turbina, f"Turbina_{op_val}", folder_id),
            str(voltaje_quemador), serializa_fotos(foto_quemador, f"Quemador_{op_val}", folder_id),
            str(voltaje_bomba_vacio), serializa_fotos(foto_bomba_vacio, f"BombaVacio_{op_val}", folder_id),
            str(voltaje_compresor), serializa_fotos(foto_compresor, f"Compresor_{op_val}", folder_id),
            str(cantidad_manometros), serializa_fotos(foto_manometros, f"Manometros_{op_val}", folder_id),
            str(cantidad_vacuometros), serializa_fotos(foto_vacuometros, f"Vacuometros_{op_val}", folder_id),
            str(cantidad_valvulas), serializa_fotos(foto_valvulas, f"Valvulas_{op_val}", folder_id),
            str(cantidad_mangueras), serializa_fotos(foto_mangueras, f"Mangueras_{op_val}", folder_id),
            str(cantidad_boquillas), serializa_fotos(foto_boquillas, f"Boquillas_{op_val}", folder_id),
            str(cantidad_reguladores), serializa_fotos(foto_reguladores, f"Reguladores_{op_val}", folder_id),
            str(tension_pinon1), serializa_fotos(foto_pinon1, f"Pinon1_{op_val}", folder_id),
            str(tension_pinon2), serializa_fotos(foto_pinon2, f"Pinon2_{op_val}", folder_id),
            str(tension_polea1), serializa_fotos(foto_polea1, f"Polea1_{op_val}", folder_id),
            str(tension_polea2), serializa_fotos(foto_polea2, f"Polea2_{op_val}", folder_id),
            str(cantidad_gabinete), serializa_fotos(foto_gabinete, f"Gabinete_{op_val}", folder_id),
            str(cantidad_arrancadores), serializa_fotos(foto_arrancadores, f"Arrancadores_{op_val}", folder_id),
            str(cantidad_control_nivel), serializa_fotos(foto_control_nivel, f"ControlNivel_{op_val}", folder_id),
            str(cantidad_variadores), serializa_fotos(foto_variadores, f"Variadores_{op_val}", folder_id),
            str(cantidad_sensores), serializa_fotos(foto_sensores, f"Sensores_{op_val}", folder_id),
            str(cantidad_toma_corriente), serializa_fotos(foto_toma_corrientes, f"TomaCorriente_{op_val}", folder_id),
            str(otros_elementos), serializa_fotos(fotos_otros_elementos, f"OtrosElementos_{op_val}", folder_id),
            str(accesorios_varios_desc["tuberias"]), serializa_fotos(accesorios_varios_foto["tuberias"], f"Tuberias_{op_val}", folder_id),
            str(accesorios_varios_desc["curvas"]), serializa_fotos(accesorios_varios_foto["curvas"], f"Curvas_{op_val}", folder_id),
            str(accesorios_varios_desc["tornilleria"]), serializa_fotos(accesorios_varios_foto["tornilleria"], f"Tornilleria_{op_val}", folder_id),
            str(revision_soldadura), str(revision_sentidos), str(manual_funcionamiento), str(revision_filos), str(revision_tratamientos), str(revision_tornilleria),
            str(revision_ruidos), str(ensayo_equipo), str(observaciones_generales), str(lider_inspeccion), str(encargado_ensamblador), str(disenador), str(fecha_entrega)
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
            "cantidad sensores de temperatura", "foto sensores de temperatura", "cantidad toma corriente", "foto toma corrientes", "otros elementos", "fotos otros elementos",
            # Accesorios varios
            "descripcion tuberias", "foto tuberias", "descripcion curvas", "foto curvas", "descripcion tornilleria", "foto tornilleria",
            "revision de soldadura", "revision de sentidos de giro", "manual de funcionamiento", "revision de filos y acabados", "revision de tratamientos", "revision de tornilleria",
            "revision de ruidos", "ensayo equipo", "observciones generales", "lider de inspeccion", "diseñador", "fecha de entrega"
        ]
        sheet = sheet_client.open(file_name).worksheet(worksheet_name)
        all_rows = sheet.get_all_values()
        if not all_rows:
            sheet.append_row(headers)
            all_rows = [headers]
        # Buscar índice de OP
        op_idx = None
        for idx, h in enumerate(headers):
            if h.strip().lower() == "op":
                op_idx = idx
                break
        found = False
        if op_idx is not None:
            for i, r in enumerate(all_rows[1:], start=2):  # start=2 por encabezado y 1-indexed para gspread
                if len(r) > op_idx and r[op_idx] == str(op_val):
                    sheet.update(f'A{i}', [row])
                    found = True
                    break
        if not found:
            sheet.append_row(row)
        st.success("Acta de entrega guardada correctamente en Google Sheets.")

if __name__ == "__main__":
    main()
