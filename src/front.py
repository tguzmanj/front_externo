# -*- coding: utf-8 -*-
"""
Created on Mon Jul 29 11:41:25 2024

@author: a.campos.mercado
"""

import json
import yaml
import io
from yaml.loader import SafeLoader
import streamlit as st
import datetime
from PIL import Image
import streamlit_authenticator as stauth
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.files.file import File

from calendar import month_abbr

from params import alternativas

# =============================================================================
# Funciones
# =============================================================================

# Función para colapsar el expander
def collapse_expander():
    st.session_state.expander_open = False
    
def parte_superior():
    
    global holding
    global anunciante
    global campania
    global mes_implementacion
    global solicitada_cliente
    global descripcion
    
    authenticator.logout("Logout")
    
    # Crear las 3 columnas
    col_sup_1, col_sup_2 = st.columns([2,3])
    
    with col_sup_1:
        
        st.image(logo)
        st.title("Formulario Falabella Audiencias")
    
    with col_sup_2:
    
        with st.expander('Información de la audiencia', expanded = st.session_state.expander_open):
            col_cont_1, col_cont_2, col_cont_3 = st.columns(3)
            
            with col_cont_1:
                holding = st.selectbox('Variable', [""]+alternativas['holding'], key='holding')
                anunciante = st.selectbox('Variable', [""]+alternativas['holding'], key='anunciante')
                campania = st.text_input("Campaña", key='campania')
            
            with col_cont_2:
                with st.container(border=True):
                    st.write('Mes de implementación de campaña')
                    # Basado en https://github.com/streamlit/streamlit/issues/2463#issuecomment-1241604897
                    this_year = datetime.date.today().year
                    this_month = datetime.date.today().month
                    report_year = st.selectbox('Año', [this_year, this_year+1], label_visibility ='hidden')
                    month_abbr_ = month_abbr[1:]
                    report_month_str = st.radio('Mes', month_abbr_, index=this_month - 1, horizontal=True, label_visibility ='hidden')
                    report_month = month_abbr_.index(report_month_str) + 1
                    mes_implementacion = [report_year, report_month]
                    
            with col_cont_3:
                solicitada_cliente = st.radio("¿Solicitada por cliente?", ["Sí", "No"], horizontal = True, index=None)
                descripcion = st.text_input("Breve descripción de la audiencia a solicitar", key = 'descripcion')
                # Botón de avanzar
                if st.button("Siguiente"):
                    if holding and anunciante: # Verificar que campos obligatorios hayan sido rellenados
                        # Aquí puedes manejar la lógica de envío de datos
                        collapse_expander()  # Colapsar el expander
                        st.session_state.siguiente = True
                        st.rerun()
                    else:
                        st.warning("Por favor, rellena todos los campos obligatorios.")
                    
                    

def formatear_precio(x):
    return f'${x:,}'.replace(',', '.')

def eliminar_antes_del_guion(texto):
    # Dividimos el texto en partes usando el guion como delimitador
    partes = texto.split(' - ', 1)
    # Retornamos la segunda parte, que es lo que está después del guion
    return partes[1] if len(partes) > 1 else texto

def cargar_archivo_a_sharepoint(archivo_a_subir, nombre_de_subida, site_url, username, password, folder_url):
    """
    Sube un archivo a una carpeta de SharePoint

    Parameters
    ----------
    nombre_de_subida : variable
        Archivo que se quiere subir.
    nombre_de_subida : str
        Qué nombre se le quiere poner al archivo subido. Debe ir con su extensión.
        Ejemplo: 'archivo_a_subir.json'
    site_url : str
        URL del sitio donde existe la carpeta destino
        E.g.: 'https://my-business.sharepoint.com/sites/site-name'
    username : str
        Nombre de usuario del SHarepoint. Debe incluir el email completo
    password : str
        Contraseña para ingresar a SharePoint   
    folder_url: str
        Ruta de la carpeta en SharePoint donde se subirán los archivos. 
        La URL debe partir desde "sites/"
        E.g.: '/sites/site-name/Documentos%20compartidos/General/Destino'

    Returns
    -------
    None.

    """
    
    # Autenticación
    auth_context = AuthenticationContext(site_url)
    if auth_context.acquire_token_for_user(username, password):
        ctx = ClientContext(site_url, auth_context)
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()
    
        # st.write(f"Conectado a: {web.properties['Title']}")
    
        folder = ctx.web.get_folder_by_server_relative_url(folder_url)
        files = folder.files
        ctx.load(files)
        ctx.execute_query()
        
        # Subir el JSON editado directamente
        target_folder = ctx.web.get_folder_by_server_relative_url(folder_url)
        target_file = target_folder.upload_file(nombre_de_subida, archivo_a_subir)
        ctx.execute_query()

def cargar_correlativo_desde_sharepoint(archivo_con_el_correlativo, site_url, username, password, folder_url):
    """
    Descarga desde Sharepoint un archivo con el último correlativo utilizado

    Parameters
    ----------
    archivo_con_el_correlativo : str
        Nombre del archivo que tiene el correlativo.
    site_url : str
        URL del sitio donde existe la carpeta destino
        E.g.: 'https://my-business.sharepoint.com/sites/site-name'
    username : str
        Nombre de usuario del SHarepoint. Debe incluir el email completo
    password : str
        Contraseña para ingresar a SharePoint   
    folder_url: str
        Ruta de la carpeta en SharePoint donde se subirán los archivos. 
        La URL debe partir desde "sites/"
        E.g.: '/sites/site-name/Documentos%20compartidos/General/Destino'

    Returns
    -------
    int: Número correlativo.

    """
    # Autenticación
    auth_context = AuthenticationContext(site_url)
    if auth_context.acquire_token_for_user(username, password):
        ctx = ClientContext(site_url, auth_context)
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()
        
        folder = ctx.web.get_folder_by_server_relative_url(folder_url)
        files = folder.files
        ctx.load(files)
        ctx.execute_query()
    
        # Listar archivos
        for file in files:
            if file.properties['Name'] == archivo_con_el_correlativo:
        
                file_url = file.properties['ServerRelativeUrl']
                file_loaded = File.open_binary(ctx, file_url)
                # Cargando archivo
                correlativo = json.loads(file_loaded.content)
    
    return correlativo

# =============================================================================
# Parámetros
# =============================================================================

# Configuración de página para formato wide
st.set_page_config(page_title="Falabella Audiencias SelfService", layout="wide")

logo = Image.open('src/logo.png')
half = 0.25
logo = logo.resize( [int(half * s) for s in logo.size] )

cats_f = alternativas['categorias_f']
cats_f = [eliminar_antes_del_guion(x) for x in cats_f]
lapso_predefinido = alternativas['lapso_predefinido']
lapso_fijo = alternativas['lapso_fijo']
rango_opciones = alternativas['rango_opciones']
brands = alternativas['marcas']
comunas = alternativas['comunas']
regiones = alternativas['regiones']
gse = alternativas['gse']
sexo = alternativas['sexo']
marital_status = alternativas['marital_status']
educational_level = alternativas['educational_level']
brand_vehicle = alternativas['brand_vehicle']
vehicle_type = alternativas['vehicle_type']
lifestyle_objetivo = alternativas['lifestyle_objetivo']
arquetipo_de_negocio = alternativas['arquetipo_de_negocio']
arquetipo_de_compra = alternativas['arquetipo_de_compra']
sf_seguros = alternativas['sf_seguros']

def main():
    
    # Crear las 5 columnas
    col1, col2, col3, col4, col5 = st.columns(5)
    
    
    # Columna 1: Selector múltiple de 5 opciones y selectbox con calendario condicional
    with col1:
        
        # =============================================================================
        # Parametros Lifestyle
        # =============================================================================
        
        st.header("Lifestyles")
        lifestyle_lifestyles = st.multiselect('Lifestyles', alternativas['lifestyles'], key='lifestyle_lifestyles')
        lifestyle_objetivo = st.selectbox('Variable', [""]+alternativas['lifestyle_objetivo'], key='lifestyle_objetivo')
        
        # =============================================================================
        # Parametros Arquetipo de Negocio
        # =============================================================================
        
        st.header("Arquetipo de Negocio")
        arq_neg_arq_neg = st.multiselect('Arquetipo de negocio', alternativas['arquetipo_de_negocio'], key='arq_neg_arq_neg')
        
        
        
        
        
        # =============================================================================
        # Parametros Ranking Transaccional
        # =============================================================================
        
        st.header("Ranking de transacciones")
        rnk_trx_bu = st.selectbox('Unidad de negocio', ["", "Falabella", "Sodimac", "Tottus"], key='rnk_trx_bu')
        rnk_trx_kpi = st.selectbox('Variable', ["", "Frecuencia", "Gasto"], key='rnk_trx_kpi')
        rnk_trx_top_customers = st.number_input("Mejores clientes", value=None, min_value=0, placeholder="Ingresa un número mayor a 0", key='rnk_trx_top_customers')
        rnk_trx_canal_compra = st.selectbox('Canal de compra', ["", "Solo online", "Solo offline"], key='rnk_trx_canal_compra')

        # =============================================================================
        # Parametros Seguros
        # =============================================================================
        
        st.header("Seguros Falabella")
        
        # Lapso ###############################################################
        sf_lapso = st.selectbox('Selecciona una opción', [""]+lapso_predefinido, key='sf_lapso')
        if sf_lapso == 'Crear mi propio rango':
            sf_lapso_perso = st.date_input(
                'Selecciona un rango de fechas', 
                value=(datetime.date(2024, 6, 1), datetime.datetime.now()),
                key='sf_lapso_perso')
        else:
            sf_lapso_perso = None
        
        sf_seguros = st.multiselect('Seguros contratados', alternativas['sf_seguros'], key='sf_seguros')
        
    # Columna 2: 4 selectbox y 4 multiselect
    with col2:
        
        # =============================================================================
        # Parametros Cross
        # =============================================================================
        
        st.header("Compras en categorías de productos")

        # Categorías F ########################################################
        cross_cat_f = st.multiselect('Selecciona opciones', cats_f, key='cross_cat_f')
        
        # Lapso ###############################################################
        cross_lapso = st.selectbox('Selecciona una opción', [""]+lapso_predefinido, key='cross_lapso')
        if cross_lapso == 'Crear mi propio rango':
            cross_lapso_perso = st.date_input(
                'Selecciona un rango de fechas', 
                value=(datetime.date(2024, 6, 1), datetime.datetime.now()),
                key='cross_lapso_perso')
        else:
            cross_lapso_perso = None
        
        # Marca ###############################################################
        cross_brands = st.multiselect('Selecciona opciones', brands, key='cross_brands')
        
        # Precio ##############################################################
        # Layout para tener las entradas en la misma fila
        col_cross_1, col_cross_2,  col_cross_3 = st.columns([2, 1, 1])
        
        with col_cross_1:
            cross_precio_rango = st.selectbox("Filtro de precios", rango_opciones, key='cross_precio_rango')

        if cross_precio_rango == "Rango":
            # Input para el precio "desde"
            with col_cross_2:
                cross_precio_desde = st.number_input("Precio desde", value=None, key='cross_precio_desde')
            # Input para el precio "hasta"
            with col_cross_3:
                cross_precio_hasta = st.number_input("Precio hasta", value=None, key='cross_precio_hasta')
        else:
            with col_cross_2:
                cross_precio_desde = st.number_input("Precio", value=None, key='cross_precio_desde')
    
        # Canal de compra #####################################################
        cross_canal_compra = st.selectbox('Canal de compra', ["", "Solo online", "Solo offline"], key='cross_canal_compra')
        
        # =============================================================================
        # Parametros Arquetipo de Compra
        # =============================================================================
        
        st.header("Arquetipo de Compra")
        arq_compra_arq_compra = st.selectbox('Variable', [""]+arquetipo_de_compra, key='arquetipo_de_compra')
        # Categorías F ########################################################
        arq_compra_cat_f = st.multiselect('Selecciona opciones', cats_f, key='arq_compra_cat_f')

        # Lapso ###############################################################
        arq_compra_lapso = st.selectbox('Selecciona una opción', [""]+lapso_predefinido, key='arq_compra_lapso')
        if arq_compra_lapso == 'Crear mi propio rango':
            arq_compra_lapso_perso = st.date_input(
                'Selecciona un rango de fechas', 
                value=(datetime.date(2024, 6, 1), datetime.datetime.now()),
                key='arq_compra_lapso_perso')
        else:
            arq_compra_lapso_perso = None
        
        # Marca ###############################################################
        arq_compra_brands = st.multiselect('Selecciona opciones', brands, key='arq_compra_brands')
        
        # Precio ##############################################################
        # Layout para tener las entradas en la misma fila
        col_arq_compra_1, col_arq_compra_2,  col_arq_compra_3 = st.columns([2, 1, 1])
        
        with col_arq_compra_1:
            arq_compra_precio_rango = st.selectbox("Filtro de precios", rango_opciones, key='arq_compra_precio_rango')

        if arq_compra_precio_rango == "Rango":
            # Input para el precio "desde"
            with col_arq_compra_2:
                arq_compra_precio_desde = st.number_input('Precio desde', min_value=0, value=None, key='arq_compra_precio_desde')
            # Input para el precio "hasta"
            with col_arq_compra_3:
                arq_compra_precio_hasta = st.number_input('Precio hasta', min_value=0, value=None, key='arq_compra_precio_hasta')
        else:
            with col_arq_compra_2:
                arq_compra_precio_desde = st.number_input('Precio', min_value=0, value=None, key='arq_compra_precio_desde')

    # Columna 3: Textbox
    with col3:
        
        # =============================================================================
        # Parametros CMR
        # =============================================================================

        st.header("Compras en negocios usando CMR")
        
        # Comercios ###########################################################
        cmr_comercios = st.multiselect('Comercios a incluir', ["ADIDAS", "NIKE", "FARMACIAS AHUMADA", "SALCOBRAND"], key='cmr_comercios')
        cmr_comercios_exclusion = st.multiselect('Comercios a excluir', ["ADIDAS", "NIKE", "FARMACIAS AHUMADA", "SALCOBRAND"], key='cmr_comercios_exclusion')
        
        # Lapso ###############################################################
        cmr_lapso = st.selectbox('Selecciona una opción', [""]+lapso_predefinido, key='cmr_lapso')
        if cmr_lapso == 'Crear mi propio rango':
            cmr_lapso_perso = st.date_input(
                'Selecciona un rango de fechas', 
                value=(datetime.date(2024, 6, 1), datetime.datetime.now()),
                key='cmr_lapso_perso')
        else:
            cmr_lapso_perso = None
        
        # Precio ##############################################################
        
        # Layout para tener las entradas en la misma fila
        col_cmr_precio_1, col_cmr_precio_2,  col_cmr_precio_3 = st.columns([2, 1, 1])
        
        with col_cmr_precio_1:
            cmr_precio_rango = st.selectbox("Filtro de precios", rango_opciones, key='cmr_precio_rango')
        
        if cmr_precio_rango == "Rango":
            # Input para el precio "desde"
            with col_cmr_precio_2:
                cmr_precio_desde = st.number_input("Precio desde", value=None, key='cmr_precio_desde')
            # Input para el precio "hasta"
            with col_cmr_precio_3:
                cmr_precio_hasta = st.number_input("Precio hasta", value=None, key='cmr_precio_hasta')
        else:
            with col_cmr_precio_2:
                cmr_precio_desde = st.number_input("Precio", value=None, key='cmr_precio_desde')
        
        # Layout para tener las entradas en la misma fila
        col_cmr_exclusion_1, col_cmr_exclusion_2,  col_cmr_exclusion_3 = st.columns([2, 1, 1])
        
        with col_cmr_exclusion_1:
            cmr_precio_exclusion_rango = st.selectbox("Filtro de precios", rango_opciones, key='cmr_precio_exclusion_rango')
            
        if cmr_precio_exclusion_rango == "Rango":
            # Input para el precio "desde"
            with col_cmr_exclusion_2:
                cmr_precio_exclusion_desde = st.number_input("Precio desde", value=None, key='cmr_precio_exclusion_desde')
            # Input para el precio "hasta"
            with col_cmr_exclusion_3:
                cmr_precio_exclusion_hasta = st.number_input("Precio hasta", value=None, key='cmr_precio_exclusion_hasta')
        else:
            with col_cmr_exclusion_2:
                cmr_precio_exclusion_desde = st.number_input("Precio", value=None, key='cmr_precio_exclusion_desde')
                
        # Tipo compra #########################################################
        cmr_tipo_compra = st.selectbox('Tipo de compra comercios a incluir', ["", "Solo nacional", "Solo internacional"], key='cmr_tipo_compra')
        cmr_tipo_compra_exclusion = st.selectbox('Tipo de compra comercios a excluir', ["", "Solo nacional", "Solo internacional"], key='cmr_tipo_compra_exclusion')

        # =============================================================================
        # Parametros Loyalty
        # =============================================================================

        st.header("Programa de lealtad")
        # Lapso ###############################################################
        lyty_lapso = st.selectbox('Selecciona una opción', [""]+lapso_fijo, key='lyty_lapso')
        # Acumulación y canje #########################################################
        # Layout para tener las entradas en la misma fila
        col_lyty_acumul_1, col_lyty_acumul_2,  col_lyty_acumul_3 = st.columns([2, 1, 1])
        with col_lyty_acumul_1:
            lyty_acumul_rango = st.selectbox("Filtro de acumulación", rango_opciones, key='lyty_acumul_rango')
            
        if lyty_acumul_rango == "Rango":
            # Input para el precio "desde"
            with col_lyty_acumul_2:
                lyty_acumul_desde = st.number_input('Acumulación desde', min_value=0, value=None, key='lyty_acumul_desde')
            # Input para el precio "hasta"
            with col_lyty_acumul_3:
                lyty_acumul_hasta = st.number_input('Acumulación hasta', min_value=0, value=None, key='lyty_acumul_hasta')
        else:
            with col_lyty_acumul_2:
                lyty_acumul_desde = st.number_input('Acumulación', min_value=0, value=None, key='lyty_acumul_desde')
        
        # Layout para tener las entradas en la misma fila
        col_lyty_canje_1, col_lyty_canje_2,  col_lyty_canje_3 = st.columns([2, 1, 1])
        with col_lyty_canje_1:
            lyty_canje_rango = st.selectbox("Filtro de canje", rango_opciones, key='lyty_canje_rango')
            
        if lyty_canje_rango == "Rango":
            # Input para el precio "desde"
            with col_lyty_canje_2:
                lyty_canje_desde = st.number_input('Canje desde', min_value=0, value=None, key='lyty_canje_desde')
            # Input para el precio "hasta"
            with col_lyty_canje_3:
                lyty_canje_hasta = st.number_input('Canje hasta', min_value=0, value=None, key='lyty_canje_hasta')
        else:
            with col_lyty_canje_2:
                lyty_canje_desde = st.number_input('Canje', min_value=0, value=None, key='lyty_canje_desde')

    # Columna 4: Slide input que permite poner un rango de valores
    with col4:
        # =============================================================================
        # Parametros Sociodemográficos
        # =============================================================================
        
        st.header("Características sociodemográficas")
        st.write("""Si dejas las opciones en blanco, se entiende que entran todos los clientes. Por ejemplo, si no seleccionas Sexo, tu audiencia tendrá ambos sexos""")
        sociodem_sexo = st.multiselect('Sexo', sexo, key='sociodem_sexo')
        sociodem_edad = st.slider('Selecciona un rango de edad', 18, 100, (18, 100), key='sociodem_edad')
        
        sociodem_gse = st.multiselect('GSE', gse, key='sociodem_gse')
        sociodem_marital_status = st.multiselect('Estado civil', marital_status, key='sociodem_marital_status')
        sociodem_education_level = st.multiselect('Nivel de estudios', educational_level, key='sociodem_education_level')
        sociodem_regiones = st.multiselect('Regiones', regiones, key='sociodem_regiones')
        sociodem_comunas = st.multiselect('Comunas', comunas, key='sociodem_comunas')
        
        
    # Columna 5: Selectbox
    with col5:
        # Layout para tener las entradas en la misma fila
        col_sociodem_n_vehiculos_1, col_sociodem_n_vehiculos_2,  col_sociodem_n_vehiculos_3 = st.columns([2, 1, 1])
        
        with col_sociodem_n_vehiculos_1:
            sociodem_n_vehiculos_rango = st.selectbox("Filtro de N° vehículos", rango_opciones, key='sociodem_n_vehiculos_rango')

        if sociodem_n_vehiculos_rango == "Rango":
            # Input para el precio "desde"
            with col_sociodem_n_vehiculos_2:
                sociodem_n_vehiculos_desde = st.number_input('N° vehículos desde', min_value=0, value=None, key = 'sociodem_n_vehiculos_desde')
            # Input para el precio "hasta"
            with col_sociodem_n_vehiculos_3:
                sociodem_n_vehiculos_hasta = st.number_input('N° vehículos hasta', min_value=0, value=None, key = 'sociodem_n_vehiculos_hasta')
        else:
            with col_sociodem_n_vehiculos_2:
                sociodem_n_vehiculos_desde = st.number_input('N° vehículos', min_value=0, value=None, key = 'sociodem_n_vehiculos_desde')
        
        # Layout para tener las entradas en la misma fila
        col_sociodem_anio_vehiculos_1, col_sociodem_anio_vehiculos_2,  col_sociodem_anio_vehiculos_3 = st.columns([2, 1, 1])
        
        with col_sociodem_anio_vehiculos_1:
            sociodem_anio_vehiculos_rango = st.selectbox("Filtro de año de vehículo", rango_opciones, key='sociodem_anio_vehiculos_rango')
            
        if sociodem_anio_vehiculos_rango == "Rango":
            # Input para el precio "desde"
            with col_sociodem_anio_vehiculos_2:
                sociodem_anio_vehiculos_desde = st.number_input('Año vehículo desde', min_value=0, value=None, key = 'sociodem_anio_vehiculos_desde')
            # Input para el precio "hasta"
            with col_sociodem_anio_vehiculos_3:
                sociodem_anio_vehiculos_hasta = st.number_input('Año vehículo hasta', min_value=0, value=None, key = 'sociodem_anio_vehiculos_hasta')
        else:
            with col_sociodem_anio_vehiculos_2:
                sociodem_anio_vehiculos_desde = st.number_input('Año vehículo', min_value=0, value=None, key = 'sociodem_anio_vehiculos_desde')
        
        # Layout para tener las entradas en la misma fila
        col_sociodem_valor_vehiculos_1, col_sociodem_valor_vehiculos_2,  col_sociodem_valor_vehiculos_3 = st.columns([2, 1, 1])
        
        with col_sociodem_valor_vehiculos_1:
            sociodem_valor_vehiculos_rango = st.selectbox("Filtro de valor de vehículo", rango_opciones, key='sociodem_valor_vehiculos_rango')
        
        if sociodem_valor_vehiculos_rango == "Rango":
            # Input para el precio "desde"
            with col_sociodem_valor_vehiculos_2:
                sociodem_valor_vehiculos_desde = st.number_input('Valor de vehículo desde', min_value=0, value=None, key = 'sociodem_valor_vehiculos_desde')
            # Input para el precio "hasta"
            with col_sociodem_valor_vehiculos_3:
                sociodem_valor_vehiculos_hasta = st.number_input('Valor de vehículo hasta', min_value=0, value=None, key = 'sociodem_valor_vehiculos_hasta')
        else:
            with col_sociodem_valor_vehiculos_2:
                sociodem_valor_vehiculos_desde = st.number_input('Valor de vehículo', min_value=0, value=None, key = 'sociodem_valor_vehiculos_desde')
        
        sociodem_tipo_vehiculo = st.multiselect('Tipo de vehículo', vehicle_type, key='sociodem_tipo_vehiculo')
        sociodem_marca_vehiculo = st.multiselect('Marca del vehículo', brand_vehicle, key='sociodem_marca_vehiculo')

    # Crear el formulario
    with st.form(key='my_form'):
        # Botón de submit
        submit_button = st.form_submit_button(label='Enviar')

    # Mostrar los valores seleccionados
    if submit_button:
        
        # Load data from JSON file
        with open('src/json_vacio.json', 'r') as f:
            json_output = json.load(f)
        
        # Incrementar el ID correlativo y guardarlo
        st.session_state.correlativo += 1
        
        json_output["1_info_general"]["holding"] = holding
        json_output["1_info_general"]["agencia"] = ''
        json_output["1_info_general"]["anunciante"] = anunciante
        json_output["1_info_general"]["comentario"] = ''
        json_output["1_info_general"]["solicitada_cliente"] = solicitada_cliente
        json_output["1_info_general"]["descripcion"] = descripcion
        json_output["1_info_general"]["mes_implementacion"] = mes_implementacion
        json_output["1_info_general"]["campania"] = campania
        json_output["1_info_general"]["fecha_solicitud"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        json_output["1_info_general"]["nombre_unico"] = f"{datetime.datetime.now().strftime('%Y%m%d')}-{holding}-{anunciante}-a{st.session_state.correlativo}".replace(" ", "-")
        
        json_output["2_info_lifestyle"]["lifestyle_seleccionado"] = lifestyle_lifestyles
        json_output["2_info_lifestyle"]["objetivo"] = lifestyle_objetivo
        
        json_output["3_info_cross"]["categorias_f"] = cross_cat_f
        json_output["3_info_cross"]["lapso"] = cross_lapso
        json_output["3_info_cross"]["marcas"] = cross_brands
        if cross_precio_rango == "Rango":
            json_output["3_info_cross"]["precio"] = [cross_precio_desde, cross_precio_hasta]
        else:
            json_output["3_info_cross"]["precio"] = [cross_precio_rango, cross_precio_desde]
        json_output["3_info_cross"]["canal_compra"] = cross_canal_compra
       
        json_output["4_info_arquetipo_negocio"]["arquetipo"] = arq_neg_arq_neg
        
        json_output["5_info_arquetipo_compra"]["arquetipo"] = arq_compra_arq_compra
        json_output["5_info_arquetipo_compra"]["categorias_f"] = arq_compra_cat_f
        json_output["5_info_arquetipo_compra"]["lapso"] = arq_compra_lapso
        json_output["5_info_arquetipo_compra"]["marcas"] = arq_compra_brands
        if arq_compra_precio_rango == "Rango":
            json_output["5_info_arquetipo_compra"]["precio"] = [arq_compra_precio_desde, arq_compra_precio_hasta]
        else:
            json_output["5_info_arquetipo_compra"]["precio"] = [arq_compra_precio_rango, arq_compra_precio_desde]

        json_output["7_info_sociodemografica"]["cust_gender"] = sociodem_sexo
        json_output["7_info_sociodemografica"]["cust_age"] = sociodem_edad
        json_output["7_info_sociodemografica"]["cust_gse"] = sociodem_gse
        json_output["7_info_sociodemografica"]["cust_education_level"] = sociodem_education_level
        json_output["7_info_sociodemografica"]["cust_marital_status"] = sociodem_marital_status
        json_output["7_info_sociodemografica"]["regiones"] = sociodem_regiones
        json_output["7_info_sociodemografica"]["cust_city"] = sociodem_comunas
        if sociodem_n_vehiculos_rango == "Rango":
            json_output["7_info_sociodemografica"]["no_of_vehicle"] = [sociodem_n_vehiculos_desde, sociodem_n_vehiculos_hasta]
        else:
            json_output["7_info_sociodemografica"]["no_of_vehicle"] = [sociodem_n_vehiculos_rango, sociodem_n_vehiculos_desde]
        if sociodem_anio_vehiculos_rango == "Rango":
            json_output["7_info_sociodemografica"]["vehicle_yr"] = [sociodem_anio_vehiculos_desde, sociodem_anio_vehiculos_hasta]
        else:
            json_output["7_info_sociodemografica"]["vehicle_yr"] = [sociodem_anio_vehiculos_rango, sociodem_anio_vehiculos_desde]
        if sociodem_valor_vehiculos_rango == "Rango":
            json_output["7_info_sociodemografica"]["vehicle_appraised_amt"] = [sociodem_valor_vehiculos_desde, sociodem_valor_vehiculos_hasta]
        else:
            json_output["7_info_sociodemografica"]["vehicle_appraised_amt"] = [sociodem_valor_vehiculos_rango, sociodem_valor_vehiculos_desde]
        json_output["7_info_sociodemografica"]["vehicle_type"] = sociodem_tipo_vehiculo
        json_output["7_info_sociodemografica"]["vehicle_brand"] = sociodem_marca_vehiculo
     
        json_output["8_info_cmr"]["lapso"] = cmr_lapso
        json_output["8_info_cmr"]["comercios"] = cmr_comercios
        json_output["8_info_cmr"]["comercios_exclusion"] = cmr_comercios_exclusion
        json_output["8_info_cmr"]["tipo_compra"] = cmr_tipo_compra
        json_output["8_info_cmr"]["tipo_compra_exclusion"] = cmr_tipo_compra_exclusion
        if cmr_precio_rango == "Rango":
            json_output["8_info_cmr"]["precio"] = [cmr_precio_desde, cmr_precio_hasta]
        else:
            json_output["8_info_cmr"]["precio"] = [cmr_precio_rango, cmr_precio_desde]
        if cmr_precio_exclusion_rango == "Rango":
            json_output["8_info_cmr"]["precio_exclusion"] = [cmr_precio_exclusion_desde, cmr_precio_exclusion_hasta]
        else:
            json_output["8_info_cmr"]["precio_exclusion"] = [cmr_precio_exclusion_rango, cmr_precio_exclusion_desde]
  
        json_output["9_ranking_transaccional"]["unidad_de_negocio"] = rnk_trx_bu
        json_output["9_ranking_transaccional"]["variable_trx"] = rnk_trx_kpi
        json_output["9_ranking_transaccional"]["n_mejores_clientes"] = rnk_trx_top_customers
        json_output["9_ranking_transaccional"]["canal_compra"] = rnk_trx_canal_compra
     
        json_output["10_loyalty"]["lapso"] = lyty_lapso
        if lyty_acumul_rango == "Rango":
            json_output["10_loyalty"]["acumulacion"] = [lyty_acumul_desde, lyty_acumul_hasta]
        else:
            json_output["10_loyalty"]["acumulacion"] = [lyty_acumul_rango, lyty_acumul_desde]
        if lyty_canje_rango == "Rango":
            json_output["10_loyalty"]["canje"] = [lyty_canje_desde, lyty_canje_hasta]
        else:
            json_output["10_loyalty"]["canje"] = [lyty_canje_rango, lyty_canje_desde]
        json_output["11_seguros"]["lapso"] = sf_lapso
        json_output["11_seguros"]["seguros"] = sf_seguros
                
        # Convertir el diccionario a JSON
        datos_json = json.dumps(json_output, indent=4).encode('utf-8')
        file_content = io.BytesIO(datos_json)
    
        cargar_archivo_a_sharepoint(file_content.getvalue(), 
                                    json_output["1_info_general"]["nombre_unico"]+'.json', 
                                    st.secrets["SITE_URL"], 
                                    st.secrets["USERNAME"], 
                                    st.secrets["PASSWORD"], 
                                    st.secrets["FOLDER_URL"])
        
        st.write(json_output)

        cargar_archivo_a_sharepoint(st.session_state.correlativo, 
                                    'ultimo_correlativo_usado.txt', 
                                    st.secrets["SITE_URL"], 
                                    st.secrets["USERNAME"], 
                                    st.secrets["PASSWORD"], 
                                    st.secrets["FOLDER_URL"])



# =============================================================================
# Autenticación
# =============================================================================

with open('src/conn/login.yml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
)



# =============================================================================
# Aplicativo
# =============================================================================

if __name__ == "__main__":
    
    authenticator.login()
    if 'siguiente' not in st.session_state:
        st.session_state.siguiente = False
    
    # Inicializar la variable de sesión para controlar el estado del expander
    if 'expander_open' not in st.session_state:
        st.session_state.expander_open = True
    
    if st.session_state["authentication_status"]:
        
        # Inicializar el contador de ID
        if 'correlativo' not in st.session_state:
            # Cargar último correlativo utilizado
            st.session_state.correlativo = cargar_correlativo_desde_sharepoint('ultimo_correlativo_usado.txt', 
                                                                     st.secrets["SITE_URL"], 
                                                                     st.secrets["USERNAME"], 
                                                                     st.secrets["PASSWORD"], 
                                                                     st.secrets["FOLDER_URL"])
            
        parte_superior()
        
        if st.session_state.siguiente:
            main()
            
    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')

        
        
