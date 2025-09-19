import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import json
from google.oauth2.service_account import Credentials
import gspread
import time
import smtplib
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- USUARIOS HARDCODED ---
USUARIOS = {
    "tekpro": {
        "contraseña": "tekpro123",  # tekpro2023
        "empresa": "TEKPRO",
        "es_admin": True
    },
    "demo": {
        "contraseña": "demo123",  # demo123
        "empresa": "DEMO",
        "es_admin": False
    },
    "administrador": {
        "contraseña": "admin1234",  # admin
        "empresa": "TEKPRO ADMINISTRADOR",
        "es_admin": True
    },
    
    "granjazul": {
        "contraseña": "granjazul123",  # granjazul2023
        "empresa": "1230263 - PRODUCTOS AVICOLAS, SOCIEDAD ANONIMA GRANJAZUL",
        "es_admin": False
    },
    "paulandia": {
        "contraseña": "paulandia123",  # paulandia2023
        "empresa": "900316481 - PAULANDIA S.A.S",
        "es_admin": False
    },
    "handelung": {
        "contraseña": "handelung123",  # handelung2023
        "empresa": "81003536 - HANDELUNG S.A",
        "es_admin": False
    },
}

# --- Fin de la definición de usuarios ---


# --- FUNCIÓN CON REINTENTOS PARA ACCESO A GOOGLE SHEETS ---
def get_sheet_with_retry(client, sheet_id, worksheet_name, retries=3, delay=2):
    for i in range(retries):
        try:
            return client.open_by_key(sheet_id).worksheet(worksheet_name)
        except Exception as e:
            if i < retries - 1:
                time.sleep(delay)
            else:
                st.error(f"No se pudo acceder a la hoja '{worksheet_name}': {e}")
                st.stop()

# --- CONFIGURACIÓN GOOGLE SHEETS ---
# --- FUNCIÓN PARA EDITAR LA DESCRIPCIÓN DE UN CONSUMIBLE EN LA HOJA DE EQUIPOS ---
def actualizar_descripcion_consumible(empresa, codigo, consumible, nueva_descripcion):
    # Buscar la fila correspondiente en equipos_df
    idx = None
    for i, row in equipos_df.iterrows():
        if row["empresa"].strip() == empresa and row["codigo"].strip() == codigo:
            idx = i
            break
    if idx is None:
        st.error("No se encontró el equipo en la hoja de Equipos.")
        return False
    # Obtener la lista de consumibles y descripciones actuales
    consumibles = [c.strip() for c in equipos_df.iloc[idx]["consumibles"].split(",")]
    descripciones_raw = str(equipos_df.iloc[idx].get("descripcion_consumibles", "")).strip()
    descripciones = [d.strip() for d in descripciones_raw.split("|")] if descripciones_raw else ["" for _ in consumibles]
    # Actualizar la descripción del consumible
    for i, c in enumerate(consumibles):
        if c == consumible:
            descripciones[i] = nueva_descripcion
    # Unir las descripciones y actualizar la celda en Google Sheets
    nueva_celda = "|".join(descripciones)
    ws = sheet_equipos
    # Buscar el índice de la columna descripcion_consumibles
    cols = ws.row_values(1)
    col_idx = None
    for i, col in enumerate(cols):
        if col.lower().strip() == "descripcion_consumibles":
            col_idx = i + 1
            break
    if col_idx is None:
        st.error("No se encontró la columna 'descripcion_consumibles' en la hoja de Equipos.")
        return False
    ws.update_cell(idx + 2, col_idx, nueva_celda)
    st.success(f"Descripción actualizada para '{consumible}' en el equipo '{codigo}'.")
    return True
try:
    service_account_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPE)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"Error al inicializar la conexión con Google Sheets: {str(e)}")
    st.warning("No se pudo establecer conexión con Google Sheets. La aplicación funcionará con funcionalidad limitada.")
    # Crear un cliente falso para evitar errores de atributos faltantes
    client = None


# --- HOJAS ---
SHEET_ID = "1288rxOwtZDI3A7kuLnR4AXaI-GKt6YizeZS_4ZvdTnQ"

# Inicializar hojas solo si hay conexión
if client:
    try:
        sheet_registro = get_sheet_with_retry(client, SHEET_ID, "Hoja 1")
        sheet_equipos = get_sheet_with_retry(client, SHEET_ID, "Equipos")
        # --- HOJA DE CHAT ---
        try:
            sheet_chat = get_sheet_with_retry(client, SHEET_ID, "Chat")
        except:
            # Si no existe, crearla con encabezados
            sheet_chat = client.open_by_key(SHEET_ID).add_worksheet(title="Chat", rows="1000", cols="4")
            sheet_chat.append_row(["fecha", "usuario", "mensaje", "empresa"])
    except Exception as e:
        st.error(f"Error al inicializar las hojas de datos: {str(e)}")
        st.warning("La aplicación funcionará en modo limitado sin acceso a datos en la nube.")
        # Crear variables vacías para evitar errores
        sheet_registro = None
        sheet_equipos = None
        sheet_chat = None
else:
    # Si no hay cliente, crear variables vacías
    sheet_registro = None
    sheet_equipos = None
    sheet_chat = None

# --- ELIMINADA TODA LA FUNCIONALIDAD DE TAREAS ---

# --- CONFIGURACIÓN DE USUARIOS Y CONTRASEÑAS ---
# Los usuarios se han definido al inicio del archivo en el diccionario USUARIOS

# --- ELIMINADA LA FUNCIONALIDAD DE CACHÉ DE TAREAS ---

# --- Ya no necesitamos cargar_usuarios_df porque los usuarios están definidos en el código ---
# Esta función se mantiene por compatibilidad pero ahora devuelve los usuarios del diccionario
def cargar_usuarios_df():
    # Convertir el diccionario de usuarios a un DataFrame para mantener compatibilidad
    usuarios_lista = []
    for nombre_usuario, datos in USUARIOS.items():
        usuarios_lista.append({
            "usuario": nombre_usuario,
            "empresa": datos["empresa"],
            "contrasena": datos["contrasena"],
            "es_admin": "si" if datos["es_admin"] else "no"
        })
    
    return pd.DataFrame(usuarios_lista)

# --- FUNCIÓN DE VALIDACIÓN DE USUARIO ---
def validar_usuario(usuario, contrasena):
    """
    Valida el usuario y contraseña y retorna la empresa asociada si es válido.
    Ahora usa el diccionario USUARIOS definido en el código en lugar de Google Sheets.
    """
    # Verificar si el usuario existe en nuestro diccionario
    if usuario in USUARIOS:
        usuario_info = USUARIOS[usuario]
        
        # Verificar contraseña (comparando texto plano)
        if contrasena == usuario_info["contraseña"]:
            empresa = usuario_info["empresa"]
            return empresa
        else:
            st.error("Contraseña incorrecta")
            return None
    else:
        st.error(f"Usuario '{usuario}' no encontrado")
        return None

# --- FUNCIÓN PARA REGISTRAR NUEVO USUARIO ---
def registrar_usuario(empresa, usuario, contrasena, es_admin=False):
    """
    Esta función permite registrar nuevos usuarios en el diccionario.
    Nota: En una aplicación real, este cambio se perdería cuando se reinicie el servidor.
    Se recomienda guardar en un archivo o base de datos permanente.
    """
    # Solo administradores pueden agregar usuarios
    if not st.session_state.get('es_admin', False):
        st.error("Solo los administradores pueden registrar nuevos usuarios")
        return False
    
    # Verificar si ya existe el usuario
    if usuario in USUARIOS:
        st.error(f"El usuario '{usuario}' ya existe en el sistema")
        return False
    
    # Agregar el nuevo usuario al diccionario
    USUARIOS[usuario] = {
        "contraseña": contrasena,
        "empresa": empresa,
        "es_admin": es_admin
    }
    
    st.success(f"Usuario '{usuario}' registrado correctamente para la empresa '{empresa}'")
    st.info("NOTA: Este usuario solo existirá durante la sesión actual. En una aplicación real, deberías guardar estos datos en un archivo o base de datos.")
    return True

# --- VIDA ÚTIL POR DEFECTO ---
VIDA_UTIL_DEFECTO = 700


# --- CACHÉ DE LECTURAS DE GOOGLE SHEETS ---
@st.cache_data(ttl=300, show_spinner=False)
def cargar_equipos_df():
    try:
        # Intentar obtener los registros con reintentos y definiendo explícitamente los encabezados
        for intento in range(3):
            try:
                # Obtener la primera fila para ver qué encabezados hay
                headers_row = sheet_equipos.row_values(1)
                
                # Eliminar duplicados manteniendo el primer valor
                headers_unique = []
                for header in headers_row:
                    if header not in headers_unique:
                        headers_unique.append(header)
                
                # Si había duplicados, mostrar advertencia
                if len(headers_unique) != len(headers_row):
                    st.warning(f"Se detectaron encabezados duplicados en la hoja de equipos. Se usará solo la primera ocurrencia de cada encabezado.")
                
                # Usar los encabezados únicos para obtener los datos
                df = pd.DataFrame(sheet_equipos.get_all_records(expected_headers=headers_unique))
                df.columns = [col.lower().strip() for col in df.columns]
                return df
            except Exception as e:
                if intento < 2:  # Si no es el último intento, esperar y reintentar
                    time.sleep(2)
                else:
                    raise e
    except Exception as e:
        # Manejo de error más detallado
        st.error(f"Error al cargar la hoja de equipos: {str(e)}")
        st.info("Usando datos de respaldo o vacíos para permitir que la aplicación funcione.")
        # Devolver un DataFrame vacío con las columnas esperadas para evitar errores posteriores
        return pd.DataFrame(columns=["empresa", "codigo", "descripcion", "consumibles", "zona", "alertas_activas"])

@st.cache_data(ttl=300, show_spinner=False)
def cargar_registro_df():
    try:
        # Intentar obtener los registros con reintentos y definiendo explícitamente los encabezados
        for intento in range(3):
            try:
                # Obtener la primera fila para ver qué encabezados hay
                headers_row = sheet_registro.row_values(1)
                
                # Eliminar duplicados manteniendo el primer valor
                headers_unique = []
                for header in headers_row:
                    if header not in headers_unique:
                        headers_unique.append(header)
                
                # Si había duplicados, mostrar advertencia
                if len(headers_unique) != len(headers_row):
                    st.warning(f"Se detectaron encabezados duplicados en la hoja de registro. Se usará solo la primera ocurrencia de cada encabezado.")
                
                # Usar los encabezados únicos para obtener los datos
                df = pd.DataFrame(sheet_registro.get_all_records(expected_headers=headers_unique))
                df.columns = [col.lower().strip() for col in df.columns]
                return df
            except Exception as e:
                if intento < 2:  # Si no es el último intento, esperar y reintentar
                    time.sleep(2)
                else:
                    raise e
    except Exception as e:
        # Manejo de error más detallado
        st.error(f"Error al cargar la hoja de registro: {str(e)}")
        st.info("Usando datos de respaldo o vacíos para permitir que la aplicación funcione.")
        # Devolver un DataFrame vacío con las columnas esperadas
        return pd.DataFrame(columns=["empresa", "codigo", "fecha", "operador", "hora de uso"])

# --- USAR FUNCIONES CACHEADAS PARA LEER DATOS ---
equipos_df = cargar_equipos_df()

# --- GESTIÓN DE ALERTAS ACTIVAS POR EMPRESA ---
if 'alertas_activas' not in equipos_df.columns:
    equipos_df['alertas_activas'] = 'sí'  # Por defecto activas si la columna no existe

def actualizar_alertas_activas_empresa(empresa, activar):
    # Cambia el valor de alertas_activas para todas las filas de la empresa
    for idx, row in equipos_df.iterrows():
        if row['empresa'].strip() == empresa:
            ws = sheet_equipos
            cols = ws.row_values(1)
            col_idx = None
            for i, col in enumerate(cols):
                if col.lower().strip() == 'alertas_activas':
                    col_idx = i + 1
                    break
            if col_idx is not None:
                ws.update_cell(idx + 2, col_idx, 'sí' if activar else 'no')
    st.success(f"Alertas {'activadas' if activar else 'desactivadas'} para la empresa {empresa}.")

def obtener_alertas_activas_empresa(empresa):
    # Devuelve True si alguna fila de la empresa tiene alertas_activas en 'sí'
    df_empresa = equipos_df[equipos_df['empresa'].str.strip() == empresa]
    if not df_empresa.empty:
        return (df_empresa['alertas_activas'].str.lower() == 'sí').any()
    return True  # Por defecto activas

# Diccionario para guardar descripciones fijas de consumibles
DESCRIPCIONES_CONSUMIBLES = {}

EQUIPOS_EMPRESA = {}
VIDA_UTIL = {}

for _, row in equipos_df.iterrows():
    empresa = row["empresa"].strip()
    codigo = row["codigo"].strip()
    descripcion = row["descripcion"].strip()
    consumibles = [c.strip() for c in row["consumibles"].split(",")]
    # Descripciones fijas por consumible (columna: descripcion_consumibles)
    descripciones_raw = str(row.get("descripcion_consumibles", "")).strip()
    descripciones = [d.strip() for d in descripciones_raw.split("|")] if descripciones_raw else ["" for _ in consumibles]

    # Nueva lógica: vida útil específica por consumible
    # Obtener el valor de vida útil del sheet (puede ser un valor único o separado)
    vida_util_raw = str(row.get("vida_util", "")).strip()
    vidas = []
    
    # Según la captura del sheet, parece que cada fila tiene un único valor numérico
    # Pero por flexibilidad, seguimos manejando posibles separadores
    if vida_util_raw:
        # Primero intentamos interpretar como un número único
        if vida_util_raw.strip().replace('.', '', 1).isdigit():
            # Es un único número, usamos este valor para todos los consumibles
            vidas = [vida_util_raw.strip()]
        # Si no es un número único, probamos con diferentes separadores
        elif "," in vida_util_raw:
            vidas = [v.strip() for v in vida_util_raw.split(",") if v.strip()]
        elif ";" in vida_util_raw:
            vidas = [v.strip() for v in vida_util_raw.split(";") if v.strip()]
        elif "|" in vida_util_raw:
            vidas = [v.strip() for v in vida_util_raw.split("|") if v.strip()]
        else:
            # Si no tiene separador pero tampoco es número, lo intentamos usar como está
            vidas = [vida_util_raw.strip()] if vida_util_raw.strip() else []
    
    # Obtener la zona del equipo (por defecto "General" si no está definida)
    zona = row.get("zona", "General").strip()
    if not zona:
        zona = "General"

    if empresa not in EQUIPOS_EMPRESA:
        EQUIPOS_EMPRESA[empresa] = {}
    
    # Crear la estructura por zonas si no existe
    if zona not in EQUIPOS_EMPRESA[empresa]:
        EQUIPOS_EMPRESA[empresa][zona] = {}

    # Obtener información adicional (si existe)
    numero_op = str(row.get("numero_op", "")).strip()
    foto_url = str(row.get("foto_url", "")).strip()
    fecha_instalacion = str(row.get("fecha_instalacion", "")).strip()
    manual_url = str(row.get("manual_url", "")).strip()
    ficha_tecnica_url = str(row.get("ficha_tecnica_url", "")).strip()
    
    EQUIPOS_EMPRESA[empresa][zona][codigo] = {
        "descripcion": descripcion,
        "consumibles": consumibles,
        "numero_op": numero_op,
        "foto_url": foto_url,
        "fecha_instalacion": fecha_instalacion,
        "manual_url": manual_url,
        "ficha_tecnica_url": ficha_tecnica_url
    }

    for i, consumible in enumerate(consumibles):
        if consumible.strip():  # Asegurarse de que el consumible no esté vacío
            try:
                # Determinar qué valor de vida útil usar para este consumible
                if len(vidas) == 1 and i >= 1:
                    # Si hay un único valor para múltiples consumibles, usar el mismo para todos
                    vida_util_valor = vidas[0]
                elif i < len(vidas):
                    # Si hay un valor específico para este consumible, usarlo
                    vida_util_valor = vidas[i]
                else:
                    # Si no hay valor específico, usar valor por defecto
                    vida_util_valor = str(VIDA_UTIL_DEFECTO)
                
                # Convertir a entero, manejando posibles formatos numéricos
                if vida_util_valor.strip():
                    # Eliminar comas y puntos para manejar números como "1,200.50" o "1200,50"
                    valor_limpio = vida_util_valor.replace(',', '')
                    
                    # Si es un número decimal, convertir a float y luego a int
                    if '.' in valor_limpio:
                        VIDA_UTIL[consumible] = int(float(valor_limpio))
                    else:
                        VIDA_UTIL[consumible] = int(valor_limpio)
                else:
                    # Si está vacío, usar valor por defecto
                    if consumible not in VIDA_UTIL:  # Solo si no existe ya
                        VIDA_UTIL[consumible] = VIDA_UTIL_DEFECTO
            except Exception as e:
                # En caso de error, usar el valor por defecto y mostrar advertencia
                if consumible not in VIDA_UTIL:  # Solo si no existe ya
                    VIDA_UTIL[consumible] = VIDA_UTIL_DEFECTO
                print(f"Error al procesar vida útil para {consumible}: {e}")
                
            # Guardar descripción fija
            DESCRIPCIONES_CONSUMIBLES[f"{empresa}|{codigo}|{consumible}"] = descripciones[i] if i < len(descripciones) else ""


# --- INTERFAZ ---

st.set_page_config(page_title="DeTEK PRO Lite", layout="centered")

# --- CSS PARA EL CARRITO DE COMPRAS ---
cart_style = """
    <style>
    .shopping-cart {
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 9999;
        font-size: 24px;
        background-color: white;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        transition: transform 0.3s ease;
    }
    .shopping-cart:hover {
        transform: scale(1.1);
    }
    </style>
    
    <a href="https://tienda.tekpro.com.co/categoria-producto/avicola/" target="_blank" class="shopping-cart" title="Ir a la tienda">🛒</a>
"""
st.markdown(cart_style, unsafe_allow_html=True)

# --- CSS PERSONALIZADO PARA OCULTAR ELEMENTOS DE GITHUB ---
hide_github_css = """
    <style>
    /* Ocultar absolutamente todos los elementos de GitHub y elementos no esenciales */
    /* Botones superiores de GitHub */
    .css-1jc7ptx, .e1ewe7hr3, .viewerBadge_container__1QSob, .styles_viewerBadge__1yB5,
    .viewerBadge_link__1S137, .viewerBadge_text__1JaDK, .css-1rs6os {
        display: none !important;
    }
    
    /* Elementos específicos de GitHub por sus IDs */
    #github-fork-button, #github-star-button, #github-link,
    button[aria-label*="GitHub"], button[title*="GitHub"],
    button[aria-label*="github"], button[title*="github"] {
        display: none !important;
    }
    
    /* Botones en la esquina superior */
    .main-header {
        visibility: hidden !important;
    }
    
    /* Todos los botones en la esquina superior derecha */
    div[data-testid="stToolbar"] {
        visibility: hidden !important;
    }
    
    /* Botón de Fork y el menú de tres puntos */
    header[data-testid="stHeader"] {
        visibility: hidden !important;
    }
    
    /* Botón de GitHub en la esquina de la página */
    .css-r698ie e8zbici2 {
        visibility: hidden !important;
    }
    
    /* Para los íconos específicos mostrados en la imagen */
    img[src*="github"], svg[data-icon*="github"] {
        display: none !important;
    }
    
    /* Elementos por su ubicación aproximada */
    .stDeployButton {
        display: none !important;
    }
    
    /* Cualquier otro elemento con referencias a GitHub */
    *[class*="github"], *[id*="github"], *[data-testid*="github"],
    *[class*="Github"], *[id*="Github"], *[data-testid*="Github"] {
        display: none !important;
    }
    
    /* Ocultar iconos SVG y botones específicos */
    svg {
        visibility: hidden !important;
    }
    
    /* Botón hamburguesa de menú y opciones */
    button[kind="icon"], button[data-testid="baseButton-headerNoPadding"] {
        visibility: hidden !important;
    }
    
    /* Ocultar elementos específicos de la captura de pantalla */
    .css-eh5xgm, .css-1aungmb, .css-18ni7ap {
        display: none !important;
    }
    
    /* Eliminar márgenes superiores */
    .block-container {
        margin-top: -75px;
    }
    </style>
    
    <script>
    // Esta función se ejecutará cuando el DOM esté completamente cargado
    document.addEventListener('DOMContentLoaded', function() {
        // Función para eliminar elementos de GitHub
        function removeGitHubElements() {
            // Eliminar elementos con "Fork" o "GitHub" en su texto
            document.querySelectorAll('*').forEach(function(el) {
                if (el.innerText && (el.innerText.includes('Fork') || el.innerText.includes('GitHub'))) {
                    el.style.display = 'none';
                }
            });
            
            // Eliminar botones en la parte superior
            document.querySelectorAll('header button, header a').forEach(function(el) {
                el.style.display = 'none';
            });
            
            // Eliminar header completamente
            const header = document.querySelector('header');
            if (header) header.style.display = 'none';
            
            // Asegurar que el botón del carrito permanezca visible
            const cartButton = document.querySelector('.shopping-cart');
            if (cartButton) cartButton.style.display = 'flex';
        }
        
        // Ejecutar inmediatamente
        removeGitHubElements();
        
        // Y también ejecutar periódicamente para capturar elementos cargados dinámicamente
        setInterval(removeGitHubElements, 1000);
    });
    </script>
"""
st.markdown(hide_github_css, unsafe_allow_html=True)

# --- LOGO ÚNICO ---
st.markdown(
    """
    <div style="display: flex; flex-direction: column; align-items: center; margin-top: 18px; margin-bottom: 10px;">
        <img src='https://drive.google.com/thumbnail?id=1FH3JryIBULTuesoK3zHRae12nkke3usP' style='max-width: 90vw; width: 200px; height: auto; margin-bottom: 0;'>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Inicializar variables de sesión ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if 'empresa_actual' not in st.session_state:
    st.session_state['empresa_actual'] = ""

if 'usuario_actual' not in st.session_state:
    st.session_state['usuario_actual'] = ""

if 'es_admin' not in st.session_state:
    st.session_state['es_admin'] = False

# --- Página de login si no está autenticado ---
if not st.session_state['autenticado']:
    st.subheader("🔐 Acceso al sistema")
    
    # Formulario de login - Sin preselección de empresa
    with st.form("login_form"):
        usuario = st.text_input("Usuario:", placeholder="Ingresa tu usuario")
        contrasena = st.text_input("Contraseña:", type="password", placeholder="Ingresa tu contraseña")
        submit_button = st.form_submit_button("Iniciar sesión")
        
        if submit_button:
            # Refrescar explícitamente los datos de usuarios para asegurar información actualizada
            st.cache_data.clear()
            
            # Mostrar mensaje de intento de inicio de sesión
            with st.spinner("Verificando credenciales..."):
                # Validar credenciales usando la función centralizada
                empresa_usuario = validar_usuario(usuario, contrasena)
            
            if empresa_usuario is not None:
                # Autenticación exitosa
                st.session_state['autenticado'] = True
                st.session_state['empresa_actual'] = empresa_usuario
                st.session_state['usuario_actual'] = usuario
                
                # Obtener el estado de administrador directamente del diccionario
                es_admin = USUARIOS[usuario]["es_admin"]
                st.write(f"Estado de administrador para {usuario}: {es_admin}")
                
                st.session_state['es_admin'] = es_admin
                st.success(f"Bienvenido {usuario} a {empresa_usuario}")
                st.rerun()
            else:
                # Mostrar mensaje de error más genérico para evitar revelar información
                st.error("Usuario o contraseña incorrectos")
    
    # Información sobre las credenciales
    st.markdown("---")
    st.info("🔄 El sistema valida tus credenciales directamente con la base de datos en tiempo real.")
    
    # Información de ayuda
    with st.expander("¿Necesitas ayuda?"):
        st.markdown("""
        ### Información importante
        
        Cada usuario está asociado a una única empresa y solo podrá acceder a la información de dicha empresa. 
        
        Al iniciar sesión, automáticamente se mostrará la información específica de tu empresa. 
        No es necesario seleccionar la empresa, ya que el sistema la detecta basándose en tus credenciales de acceso.
        
        ### Credenciales
        
        Las credenciales se almacenan y validan directamente desde la hoja de Google Sheets. Cualquier actualización 
        en las credenciales será efectiva inmediatamente en el sistema de inicio de sesión.
        
        ### Soporte técnico
        
        Si no tienes acceso a tu cuenta o has olvidado tus credenciales, por favor contacta con el administrador del sistema o con TEKPRO al correo soportetecnico@tekpro.com.co
        """)
        
    st.markdown("---")
    st.markdown("#### ¿Cómo funciona el sistema de acceso?")
    st.info("El sistema utiliza tus credenciales para identificar a qué empresa perteneces, verificándolas directamente con la base de datos en Google Sheets. Una vez que inicies sesión, solo verás la información relacionada con tu empresa. Cada usuario está vinculado a una única empresa.")
    
    # Detener la ejecución del resto del código
    st.stop()

# --- Menú de empresa y selección de empresa (esto define empresa_seleccionada) ---
# Todas las empresas son visibles para todos los usuarios
empresas_disponibles = list(EQUIPOS_EMPRESA.keys())
empresa_seleccionada = st.sidebar.selectbox("Selecciona la empresa:", empresas_disponibles)
st.sidebar.markdown(f"**Empresa seleccionada: {empresa_seleccionada}**")

# Panel de administración (solo visible para administradores)
if st.session_state['es_admin']:
    # Barra de administración con información de todas las empresas
    with st.expander("🔍 Panel de Administración - Visión General de Empresas", expanded=False):
        st.markdown("### Resumen de todas las empresas")
        
        # Crear un DataFrame con información resumida de todas las empresas
        empresas_data = []
        for empresa in empresas_disponibles:
            zonas = list(EQUIPOS_EMPRESA.get(empresa, {}).keys())
            num_zonas = len(zonas)
            
            # Contar equipos totales de la empresa
            equipos_total = 0
            for zona in zonas:
                equipos_total += len(EQUIPOS_EMPRESA[empresa].get(zona, {}))
            
            # Determinar el estado de alertas
            alertas_estado = " Activadas" if obtener_alertas_activas_empresa(empresa) else " Desactivadas"
            
            empresas_data.append({
                "Empresa": empresa,
                "Zonas": num_zonas,
                "Equipos": equipos_total,
                "Alertas": alertas_estado
            })
        
        if empresas_data:
            empresas_df = pd.DataFrame(empresas_data)
            st.dataframe(empresas_df, use_container_width=True)
            
            # Sección para ver detalles de una empresa específica
            st.markdown("### Detalles de Equipos por Empresa")
            empresa_seleccionada_admin = st.selectbox("Selecciona una empresa para ver detalles:", empresas_disponibles, key="admin_empresa_select")
            
            if empresa_seleccionada_admin:
                zonas_admin = list(EQUIPOS_EMPRESA.get(empresa_seleccionada_admin, {}).keys())
                
                if zonas_admin:
                    zona_seleccionada_admin = st.selectbox("Selecciona una zona:", zonas_admin, key="admin_zona_select")
                    
                    if zona_seleccionada_admin:
                        equipos_zona = EQUIPOS_EMPRESA[empresa_seleccionada_admin].get(zona_seleccionada_admin, {})
                        
                        if equipos_zona:
                            st.markdown(f"#### Equipos en {zona_seleccionada_admin} ({len(equipos_zona)} equipos)")
                            
                            equipos_data = []
                            for codigo, detalles in equipos_zona.items():
                                equipos_data.append({
                                    "Código": codigo,
                                    "Descripción": detalles["descripcion"],
                                    "Consumibles": len(detalles["consumibles"]) if "consumibles" in detalles else 0
                                })
                                
                            equipos_df = pd.DataFrame(equipos_data)
                            st.dataframe(equipos_df, use_container_width=True)
                        else:
                            st.info(f"No hay equipos en la zona {zona_seleccionada_admin}.")
                else:
                    st.info(f"No hay zonas definidas para la empresa {empresa_seleccionada_admin}.")
        else:
            st.info("No hay empresas con equipos registrados en el sistema.")

# Verificar que la empresa existe en los datos disponibles
if empresa_seleccionada not in EQUIPOS_EMPRESA:
    st.sidebar.error(f"La empresa '{empresa_seleccionada}' no existe en el sistema o no tiene equipos registrados.")
    st.error(f"La empresa '{empresa_seleccionada}' no existe o no tiene equipos registrados.")
    st.stop()

# --- Información del usuario logueado ---
st.sidebar.markdown(f"**Usuario conectado:** {st.session_state['usuario_actual']}")
if st.sidebar.button("Cerrar sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

# --- SECCIÓN DE ADMINISTRACIÓN (SOLO PARA ADMIN) ---
if st.session_state['es_admin']:
    with st.expander("⚙️ Panel de Administración", expanded=False):
        st.subheader("Gestión de Usuarios")
        
        # Información sobre el sistema de credenciales
        st.info("🔒 Las credenciales se almacenan y validan directamente desde Google Sheets. Los cambios realizados aquí se reflejan inmediatamente en el sistema.")
        
        # Botón para refrescar los datos
        if st.button("🔄 Actualizar lista de usuarios"):
            st.cache_data.clear()
            st.success("Lista de usuarios actualizada desde Google Sheets")
            st.rerun()
        
        # Mostrar usuarios existentes
        usuarios_df = cargar_usuarios_df()
        if not usuarios_df.empty:
            st.markdown("### Usuarios registrados")
            st.dataframe(
                usuarios_df[["empresa", "usuario"]], 
                column_config={
                    "empresa": "Empresa",
                    "usuario": "Nombre de Usuario"
                },
                use_container_width=True
            )
        else:
            st.warning("No hay usuarios registrados o no se pudo cargar la información")
        
        # Formulario para añadir nuevo usuario
        st.markdown("---")
        st.subheader("Añadir nuevo usuario")
        with st.form("form_nuevo_usuario"):
            nueva_empresa_usuario = st.selectbox("Empresa:", empresas_disponibles)
            nuevo_usuario = st.text_input("Usuario:")
            nueva_contrasena = st.text_input("Contraseña:", type="password")
            confirmar_contrasena = st.text_input("Confirmar contraseña:", type="password")
            
            st.warning("⚠️ IMPORTANTE: Cada usuario solo podrá acceder a la información de la empresa a la que esté asociado.")
            st.info("💾 El usuario será registrado directamente en Google Sheets y estará disponible inmediatamente.")
            
            if st.form_submit_button("Registrar usuario"):
                if not nuevo_usuario or not nueva_contrasena:
                    st.error("Todos los campos son obligatorios")
                elif nueva_contrasena != confirmar_contrasena:
                    st.error("Las contraseñas no coinciden")
                else:
                    # Limpiar caché para asegurar datos frescos
                    st.cache_data.clear()
                    if registrar_usuario(nueva_empresa_usuario, nuevo_usuario, nueva_contrasena, es_admin=True):
                        st.success(f"Usuario {nuevo_usuario} registrado correctamente para la empresa {nueva_empresa_usuario}")
                        # Limpiar caché nuevamente después del registro
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("El usuario ya existe en el sistema")

# --- ELIMINADA SECCIÓN DE TAREAS ASIGNADAS ---

# --- SWITCH PARA ACTIVAR/DESACTIVAR ALERTAS ---
alertas_activas = obtener_alertas_activas_empresa(empresa_seleccionada)
switch = st.sidebar.checkbox(
    "Recibir notificaciones de alertas para esta empresa",
    value=alertas_activas,
    help="Activa o desactiva el envío de alertas por email para esta empresa."
)
if switch != alertas_activas:
    actualizar_alertas_activas_empresa(empresa_seleccionada, switch)

# --- La funcionalidad de registro de nuevo equipo se ha movido a detek_procompany.py ---

# --- CARGAR REGISTROS EXISTENTES ---
data = cargar_registro_df()

# --- PROCESOS Y SELECTOR ---
zonas_empresa = EQUIPOS_EMPRESA.get(empresa_seleccionada, {})

if not zonas_empresa:
    st.warning("⚠️ Esta empresa aún no tiene equipos registrados. Agrega uno desde la barra lateral.")
    st.stop()

# Primero seleccionamos la zona
zonas_disponibles = list(zonas_empresa.keys())
st.markdown("**Selecciona la zona:**")
zona_seleccionada = st.selectbox("", zonas_disponibles, label_visibility="collapsed")

# Mostramos la zona seleccionada con un estilo similar a la imagen proporcionada
st.markdown(f"""
<div style="background-color: #E6F2F8; padding: 10px; border-radius: 5px; margin-top: 10px; margin-bottom: 10px;">
    <h3 style="margin: 0; font-size: 1.1rem;">{zona_seleccionada}</h3>
</div>
""", unsafe_allow_html=True)

# Luego obtenemos los equipos de esa zona
equipos_zona = zonas_empresa.get(zona_seleccionada, {})

selector_visible = []
estado_equipos = {}

for codigo, detalles in equipos_zona.items():
    descripcion = detalles["descripcion"]
    consumibles = detalles["consumibles"]
    estado_icono = "🟢"
    data_equipo = data[(data["empresa"] == empresa_seleccionada) & (data["codigo"] == codigo)]
    estado_partes = {parte: 0 for parte in consumibles}

    for _, fila in data_equipo.iterrows():
        horas = fila.get("hora de uso", 0)
        try:
            horas = float(horas)
        except:
            horas = 0
        partes_cambiadas = str(fila.get("parte cambiada", "")).split(";")
        for parte in estado_partes:
            if parte in partes_cambiadas:
                estado_partes[parte] = 0
            else:
                estado_partes[parte] += horas

    # Determinar el estado más crítico entre los consumibles
    icono_equipo = "🟢"
    for parte, usadas in estado_partes.items():
        limite = VIDA_UTIL.get(parte, VIDA_UTIL_DEFECTO)
        restantes = limite - usadas
        if restantes <= 0.5:
            icono_equipo = "⚠️"
            break
        elif restantes <= 3 and icono_equipo != "⚠️":
            icono_equipo = "🔴"

    visible = f"{icono_equipo} {codigo} - {descripcion}"
    selector_visible.append(visible)
    estado_equipos[visible] = codigo



# --- CHAT EN LÍNEA EN BARRA LATERAL IZQUIERDA (EXPANDER) ---
with st.sidebar.expander("💬 Chat en línea entre usuarios de la empresa", expanded=False):
    chat_df = pd.DataFrame(sheet_chat.get_all_records())
    if not chat_df.empty:
        chat_df = chat_df[chat_df["empresa"] == empresa_seleccionada]
        chat_df = chat_df.tail(30)
        for _, row in chat_df.iterrows():
            st.markdown(f"<span style='color:#00BDAD'><b>{row['usuario']}</b></span> <span style='color:gray;font-size:12px'>({row['fecha']})</span>: {row['mensaje']}", unsafe_allow_html=True)
    else:
        st.info("No hay mensajes en el chat todavía.")
    st.markdown("---")
    usuario_chat = st.text_input("Tu nombre para el chat:", value=empresa_seleccionada, key="chat_nombre")
    mensaje_chat = st.text_input("Mensaje:", value="", key="chat_mensaje")
    if st.button("Enviar mensaje", key="chat_enviar"):
        if mensaje_chat.strip():
            sheet_chat.append_row([
                str(datetime.now()),
                usuario_chat.strip(),
                mensaje_chat.strip(),
                empresa_seleccionada
            ])
            st.success("Mensaje enviado!")
            # No recargar toda la app, solo limpiar el campo de mensaje si se desea
            # st.experimental_rerun() eliminado para evitar recarga global

# --- SELECCIÓN DE EQUIPO ---
st.markdown(f"**Empresa :** `{empresa_seleccionada}`")
st.markdown("<hr style='margin-top:10px;margin-bottom:10px;border:1px solid #e0e0e0;'>", unsafe_allow_html=True)

if not selector_visible:
    st.warning("⚠️ Esta empresa aún no tiene equipos registrados. Agrega uno desde la barra lateral.")
    st.stop()

st.markdown("**Selecciona el equipo:**")
seleccion = st.selectbox("", selector_visible, label_visibility="collapsed")

if not seleccion or seleccion not in estado_equipos:
    st.warning("⚠️ Selecciona un equipo válido para continuar.")
    st.stop()

codigo = estado_equipos[seleccion]
descripcion = equipos_zona[codigo]["descripcion"]

# Asegurarse de que todos los consumibles se carguen correctamente
consumibles_equipo = []
consumibles_raw = equipos_zona[codigo].get("consumibles", [])
if isinstance(consumibles_raw, list):
    consumibles_equipo = [c for c in consumibles_raw if c.strip()]
else:
    # Si consumibles no es una lista, intentar separar por comas
    consumibles_equipo = [c.strip() for c in str(consumibles_raw).split(",") if c.strip()]

# Verificación extra: buscar en el dataframe original si no hay consumibles
if not consumibles_equipo:
    equipo_df = equipos_df[(equipos_df["empresa"] == empresa_seleccionada) & (equipos_df["codigo"] == codigo)]
    if not equipo_df.empty and "consumibles" in equipo_df.columns:
        consumibles_raw = equipo_df.iloc[0]["consumibles"]
        consumibles_equipo = [c.strip() for c in str(consumibles_raw).split(",") if c.strip()]

# Mostrar un mensaje si no hay consumibles
if not consumibles_equipo:
    st.warning("No hay consumibles registrados para este equipo.")

# Mostrar cantidad de equipos
st.markdown("**Cantidad de equipos:**")
st.markdown(f"<span style='color: #888; font-size: 1.2rem;'>{len(equipos_zona)}</span>", unsafe_allow_html=True)

# --- INFORMACIÓN ADICIONAL DEL EQUIPO ---
with st.expander("Información adicional del equipo", expanded=False):
    
    # Sección de documentación
    st.markdown("### Documentación del equipo")
    
    # Obtenemos las URLs
    foto_url = equipos_zona[codigo].get("foto_url", "")
    manual_url = equipos_zona[codigo].get("manual_url", "")
    ficha_url = equipos_zona[codigo].get("ficha_tecnica_url", "")
    
    col1, col2, col3 = st.columns(3)
    
    # Botón para ver foto del equipo
    with col1:
            if foto_url and foto_url.startswith(('http://', 'https://')):
                if st.button(" Ver foto del equipo", key="ver_foto", use_container_width=True):
                    # Crear un botón de estilo HTML que abra la foto en una nueva pestaña
                    st.markdown(f"""
                    <div style='text-align:center;'>
                        <a href="{foto_url}" target="_blank" style="display:inline-block; background-color:#007bff; color:white; padding:10px 20px; text-align:center; text-decoration:none; font-size:16px; margin:4px 2px; cursor:pointer; border-radius:5px;">
                             Abrir foto
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.button(" Ver foto del equipo", key="ver_foto", disabled=True, use_container_width=True)
                st.markdown("<div style='text-align:center; font-size:0.8em; color:#888;'>No disponible</div>", unsafe_allow_html=True)
        
    # Botón para ver manual
    with col2:
        if manual_url and manual_url.startswith(('http://', 'https://')):
            if st.button("Ver manual", key="ver_manual", use_container_width=True):
                # Crear un botón de estilo HTML que abra el enlace en una nueva pestaña
                st.markdown(f"""
                <div style='text-align:center;'>
                    <a href="{manual_url}" target="_blank" style="display:inline-block; background-color:#007bff; color:white; padding:10px 20px; text-align:center; text-decoration:none; font-size:16px; margin:4px 2px; cursor:pointer; border-radius:5px;">
                         Abrir manual en nueva pestaña
                    </a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.button(" Ver manual", key="ver_manual", disabled=True, use_container_width=True)
            st.markdown("<div style='text-align:center; font-size:0.8em; color:#888;'>No disponible</div>", unsafe_allow_html=True)
    
    # Botón para ver ficha técnica
    with col3:
        if ficha_url and ficha_url.startswith(('http://', 'https://')):
            if st.button(" Ver ficha técnica", key="ver_ficha", use_container_width=True):
                st.markdown(f'<iframe src="{ficha_url}" width="100%" height="400px"></iframe>', unsafe_allow_html=True)
        else:
            st.button("Ver ficha técnica", key="ver_ficha", disabled=True, use_container_width=True)
            st.markdown("<div style='text-align:center; font-size:0.8em; color:#888;'>No disponible</div>", unsafe_allow_html=True)

# --- HORARIO DE OPERACIÓN ---
#st.subheader(" Horario del turno")
#col1, col2 = st.columns(2)
#with col1:
    #hora_inicio = st.time_input("Hora de inicio", value=datetime.strptime("07:00", "%H:%M").time())
#with col2:
    #hora_fin = st.time_input("Hora de finalización", value=datetime.strptime("17:00", "%H:%M").time())

#inicio_dt = datetime.combine(date.today(), hora_inicio)
#fin_dt = datetime.combine(date.today(), hora_fin)
#if fin_dt < inicio_dt:
    #fin_dt += timedelta(days=1)
#horas_trabajadas = round((fin_dt - inicio_dt).total_seconds() / 3600, 2)

# --- OBSERVACIONES ---
st.subheader(" Observaciones")
observaciones = st.text_area("Ingrese observaciones del día:")

# --- GUARDAR DATOS ---
if st.button("Guardar información para todos los equipos de esta zona"):
    # Recorrer todos los equipos de la zona seleccionada
    for codigo, detalles in equipos_zona.items():
        fila = [
            empresa_seleccionada,
            str(date.today()),
            "",  # OP
            codigo,
            detalles["descripcion"],
            #horas_trabajadas,
            "",  # Parte cambiada
            observaciones,
            ""  # Observaciones técnicas
        ]
        sheet_registro.append_row(fila)
    st.success("✅ Registro guardado para todos los procesos.")

# --- ESTADO DE CONSUMIBLES ---

st.markdown(f"<h3>🔧 Estado de consumibles del proceso seleccionado</h3>", unsafe_allow_html=True)

# Verificar si hay consumibles
if not consumibles_equipo:
    st.info("No hay consumibles registrados para este equipo.")
    
    # Intento de recuperación: buscar en el dataframe original
    equipo_df = equipos_df[(equipos_df["empresa"] == empresa_seleccionada) & (equipos_df["codigo"] == codigo)]
    if not equipo_df.empty and "consumibles" in equipo_df.columns:
        consumibles_raw = equipo_df.iloc[0]["consumibles"]
        if consumibles_raw:
            consumibles_equipo = [c.strip() for c in str(consumibles_raw).split(",") if c.strip()]
            if consumibles_equipo:
                st.success(f"Se recuperaron {len(consumibles_equipo)} consumibles del registro original.")

# Si aún hay consumibles disponibles, mostrarlos
if consumibles_equipo:
    # Mostrar información general
    st.markdown(f"**Consumibles registrados:** {len(consumibles_equipo)}")
    
    # Tabla resumen de consumibles con sus vidas útiles
    resumen_data = []
    for cons in consumibles_equipo:
        vida_util_cons = VIDA_UTIL.get(cons, VIDA_UTIL_DEFECTO)
        resumen_data.append({"Consumible": cons, "Vida útil (horas)": vida_util_cons})
    
    if resumen_data:
        st.markdown("### Resumen de consumibles configurados:")
        df_resumen = pd.DataFrame(resumen_data)
        st.dataframe(df_resumen, hide_index=True)
    
    # Calcular horas de uso para cada consumible
    data_equipo = data[(data["empresa"] == empresa_seleccionada) & (data["codigo"] == codigo)]
    estado_partes = {parte: 0 for parte in consumibles_equipo}

# Diccionario para guardar descripciones de consumibles
if 'descripcion_consumibles' not in st.session_state:
    st.session_state['descripcion_consumibles'] = {}

for _, fila in data_equipo.iterrows():
    horas = fila.get("hora de uso", 0)
    try:
        horas = float(horas)
    except:
        horas = 0
    partes_cambiadas = str(fila.get("parte cambiada", "")).split(";")
    for parte in estado_partes:
        if parte in partes_cambiadas:
            estado_partes[parte] = 0
        else:
            estado_partes[parte] += horas

if 'alertas_enviadas' not in st.session_state:
    st.session_state['alertas_enviadas'] = {}
#-------------------------------------------------CAMBIAR CORREO AQUIIII-----------------------------
def enviar_alerta_email(parte, equipo, empresa, restantes, descripcion):
    remitente = st.secrets.get("EMAIL_USER")
    password = st.secrets.get("EMAIL_PASS")
    destinatario = "produccion@tekpro.com.co"
    if not remitente or not password or not destinatario:
        st.warning("No se pudo enviar alerta: faltan datos de configuración de correo.")
        return False
    asunto = f"ALERTA: Consumible crítico en {equipo} ({empresa})"
    cuerpo = f"El consumible '{parte}' del equipo '{equipo}' en la empresa '{empresa}' está en estado de falla inminente. Restan {restantes:.1f} horas de vida útil.\n\nDescripción: {descripcion}\n\nComunicate con TEKPRO al siguiente correo ventas@tekpro.com.co, o escribenos al chat que esta en la app DeTEK PRO."
    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo, 'plain'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remitente, password)
            server.sendmail(remitente, destinatario, msg.as_string())
        return True
    except Exception as e:
        st.warning(f"No se pudo enviar alerta por email: {e}")
        return False

for parte, usadas in estado_partes.items():
    if not parte.strip():  # Ignorar consumibles vacíos
        continue
        
    # Obtener la vida útil específica para este consumible
    limite = VIDA_UTIL.get(parte, VIDA_UTIL_DEFECTO)
    restantes = limite - usadas
    clave_alerta = f"{empresa_seleccionada}|{codigo}|{parte}"
    # Mostrar descripción fija desde hoja de Equipos
    descripcion_fija = DESCRIPCIONES_CONSUMIBLES.get(clave_alerta, "")
    
    # Determinar el estado del consumible
    if restantes <= 0.5:
        color, estado = "⚠️", "Falla esperada"
        # Lógica para alertas
        if not st.session_state['alertas_enviadas'].get(clave_alerta, False):
            if obtener_alertas_activas_empresa(empresa_seleccionada):
                enviado_email = enviar_alerta_email(parte, codigo, empresa_seleccionada, restantes, descripcion_fija)
                
                if enviado_email:
                    st.success(f"Alerta enviada por email para {parte} ({codigo})")
                else:
                    st.error(f"No se pudo enviar la alerta por email para {parte} ({codigo})")
            else:
                st.info("Las alertas están desactivadas para esta empresa. No se enviaron notificaciones.")
            st.session_state['alertas_enviadas'][clave_alerta] = True
    elif restantes <= 24:
        color, estado = "🔴", "Crítico"
    elif restantes <= 360:
        color, estado = "🟡", "Advertencia"
    else:
        color, estado = "🟢", "Bueno"
        # Si el consumible vuelve a estar en "Bueno", se puede resetear la alerta para futuros eventos
        if st.session_state['alertas_enviadas'].get(clave_alerta, False):
            st.session_state['alertas_enviadas'][clave_alerta] = False
    
    # Mostrar información del consumible en un formato más detallado
    consumible_container = st.container()
    with consumible_container:
        st.markdown(f"{color} **{parte}** - Estado: {estado}")
        
        # Mostrar descripción si existe
        if descripcion_fija:
            st.markdown(f"<span style='color:#666; font-style:italic;'>{descripcion_fija}</span>", unsafe_allow_html=True)
        
        # Mostrar vida útil y uso claramente
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Vida útil configurada:** `{limite}` horas")
            st.markdown(f"**Uso acumulado:** `{usadas:.1f}` horas")
        with col2:
            st.markdown(f"**Horas restantes:** `{restantes:.1f}` horas")
            porcentaje_vida = max(0, min(100, (restantes / limite * 100))) if limite > 0 else 0
            if restantes <= 0:
                st.markdown("<span style='color:red;font-weight:bold;'>⚠️ ¡Requiere cambio inmediato!</span>", unsafe_allow_html=True)
            elif porcentaje_vida < 10:
                st.markdown("<span style='color:orange;font-weight:bold;'>⚠️ Cambio pronto requerido</span>", unsafe_allow_html=True)
        
        # Añadir una barra de progreso para visualizar el estado
        progreso = usadas / limite if limite > 0 else 0
        progreso = min(1.0, progreso)  # Asegurar que no exceda el 100%
    
    # Determinar el color de la barra de progreso según el estado
    if estado == "Bueno":
        barra_color = "green"
    elif estado == "Advertencia":
        barra_color = "yellow"
    elif estado == "Crítico":
        barra_color = "red"
    else:
        barra_color = "gray"
    
    # Mostrar la barra de progreso
    st.progress(progreso, text=None)
    
    # Campo para cantidad del consumible
    cantidad = 1  # Valor por defecto
    st.markdown(f"Cantidad: {cantidad}")
    
    # Línea divisoria
    st.markdown("<hr style='margin-top:10px;margin-bottom:10px;border:1px solid #e0e0e0;'>", unsafe_allow_html=True)
