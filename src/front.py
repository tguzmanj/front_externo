# -*- coding: utf-8 -*-
"""
Created on Mon Jul 29 11:41:25 2024

@author: a.campos.mercado
"""

import streamlit as st
import streamlit_authenticator as stauth
import datetime
import json
import io
import yaml
import pytz
from calendar import month_abbr
from yaml.loader import SafeLoader
from PIL import Image
import unicodedata

from streamlit_datalist import stDatalist

from utils import formateo_json, login, subir_json, cargar_correlativo_desde_google_drive, cargar_correlativo_hacia_google_drive, tipo_de_audiencia, tipo_de_script
from params import alternativas, dict_reemplazo

# =============================================================================
# Funciones
# =============================================================================

# Funciones de Streamlit ######################################################

def clear_all():
    """
    Limpia las alternativas seleccionadas, manteniendo las de arriba

    Returns
    -------
    None.

    """
    
    # Para cada session_state
    for i in st.session_state:
        # Que sea una selección
        if i not in ['siguiente',
                    'authentication_status',
                    'username',
                    'logout',
                    'rerun',
                    'FormSubmitter:my_form-Enviar',
                    'FormSubmitter:my_form-Limpiar alternativas',
                    'expander_open',
                    'init',
                    '_xsrf',
                    'name_cookie',
                    'name', 'correlativo', 
                    'holding', 'anunciante', 'campania', 'marca', 'solicitada_cliente', 'descripcion']: # No limpiar lo de arriba
            
            # Inicializarla dependiendo de qué es
            if type(st.session_state[i]) is list: # Para multiselect
                st.session_state[i] = []
            elif type(st.session_state[i]) is int: # Para number_input   
                st.session_state[i] = None
            elif type(st.session_state[i]) is str: # Para selectbox 
                st.session_state[i] = None
            elif type(st.session_state[i]) is bool: # Para checkbox 
                st.session_state[i] = False
            else:
                # debugging
                # print(i)
                # print(st.session_state[i])
                # print(type(st.session_state[i]))
                pass 
        # Siempre que se limpien las opciones, abrir el expander para que se pueda modificar
        if i == 'expander_open': 
            st.session_state[i] = True
    
# Función para colapsar el expander
def collapse_expander():
    st.session_state.expander_open = False
    
def parte_superior():
    
    global holding
    global anunciante
    global campania
    global mes_implementacion
    global solicitada_cliente
    global solicitante
    global descripcion
    global marca
    
    print("Desplegando parte superior")
    
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
                holding = st.selectbox('Holding', holding_list, index=index_holding, placeholder = 'Selecciona un holding', key='holding')
                anunciante = stDatalist(label='Anunciante', options=[""]+anunciante_list, key='anunciante')
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
                    mes_implementacion = f"{str(report_month).zfill(2)}/{report_year}"
                    
            with col_cont_3:
                marca = st.text_input("Marca", key='marca')
                if usuario_externo:
                    solicitada_cliente = "Sí"
                    solicitante = st.session_state['name']
                else:                    
                    solicitada_cliente = st.radio("¿Solicitada por cliente?", ["Sí", "No"], horizontal = True, index=None, key='solicitada_cliente')
                    if solicitada_cliente == "Sí":
                        solicitante = st.text_input("Solicitante", key='solicitante')
                    else:
                        solicitante = ''
                descripcion = st.text_input("Breve descripción de la audiencia a solicitar", key = 'descripcion')
                # Botón de avanzar
                if st.button("Siguiente", on_click=collapse_expander):
                    if holding and anunciante: # Verificar que campos obligatorios hayan sido rellenados
                        st.session_state.siguiente = True
                    else:
                        st.warning("Por favor, rellena todos los campos obligatorios.")

def reglas_enviar_formulario(json):
    # Si se ingresó cross, no puede haber arquetipo de compra y viceversa
    if (any(value != "" for value in json['3_info_cross'].values()) & any(value != "" for value in json['5_info_arquetipo_compra'].values())):
        st.warning('No pueden enviarse audiencias de "Compras en categorías de productos" y de "Arquetipo de Compra" en el mismo requerimiento')
        return False
    
    # Si se ingresó Lifestyles, todos los campos deben estar ingresados
    if any(value != "" for value in json['2_info_lifestyle'].values()):
        if any(value == "" for value in json['2_info_lifestyle'].values()):
            st.warning("Todos los campos de audiencia 'Lifestyle' deben estar ingresados")
            return False
    # Si se ingresó Ranking de transacciones, debe estar ingresada la BU, el KPI y el top de clientes
    if any(value != "" for value in json['9_ranking_transaccional'].values()):
        if (json['9_ranking_transaccional']['unidad_de_negocio'] == '') | \
           (json['9_ranking_transaccional']['variable_trx'] == '') | \
           (json['9_ranking_transaccional']['n_mejores_clientes'] == ''):
            st.warning("Audiencias de 'Ranking de transacciones' deben tener al menos la unidad de negocio, el KPI a utilizar y el top de clientes requerido")
            return False
    # Si se ingresó Programa de lealtad, debe estar ingresado el lapso y uno de los otros dos campos
    if any(value != "" for value in json['10_loyalty'].values()):
        if (json['10_loyalty']['lapso'] == '') | ((json['10_loyalty']['acumulacion'] == '') & (json['10_loyalty']['canje'] == '')):
            st.warning("Audiencias de 'Programa de lealtad' deben tener el lapso y acumulación o canje ingresados")
            return False
    # Si se ingresó cross, debe estar ingresado el lapso y categorías
    if any(value != "" for value in json['3_info_cross'].values()):
        if (json['3_info_cross']['lapso'] == '') | (json['3_info_cross']['categorias_f'] == ''):
            st.warning("Audiencias de 'Compras en categorías de productos' deben tener al menos el lapso y sus categorías ingresados")
            return False    
    # Si se ingresó arquetipo de compra, debe estar ingresado el lapso, categorías y arquetipo
    if any(value != "" for value in json['5_info_arquetipo_compra'].values()):
        if (json['5_info_arquetipo_compra']['lapso'] == '') | \
            (json['5_info_arquetipo_compra']['categorias_f'] == '') | \
            (json['5_info_arquetipo_compra']['arquetipo'] == ''):
            st.warning("Audiencias de 'Arquetipo de Compra' deben tener al menos el arquetipo, el lapso y sus categorías ingresados")
            return False        
    # Si se ingresó CMR, debe estar ingresado el lapso y comercios/keywords
    if any(value != "" for value in json['8_info_cmr'].values()):
        if (json['8_info_cmr']['lapso'] == '') | ((json['8_info_cmr']['comercios'] == '') & (json['8_info_cmr']['keywords'] == '') \
                                                  & (json['8_info_cmr']['comercios_exclusion'] == '') & (json['8_info_cmr']['keywords_exclusion'] == '')):
            st.warning("Audiencias de 'Compras en negocios usando tarjeta de crédito' deben al menos tener el lapso y comercios o keywords ingresados")
            return False
    # Si se ingresó Seguros Falabella, todos los campos deben estar ingresados
    if any(value != "" for value in json['11_seguros'].values()):
        if any(value == "" for value in json['11_seguros'].values()):
            st.warning("Todos los campos de audiencia 'Seguros Falabella' deben estar ingresados")
            return False
    
    return True

# =============================================================================
# Parámetros
# =============================================================================

# Leer las credenciales desde secrets
credentials_json = st.secrets["GOOGLE_DRIVE"]["GOOGLE_APPLICATION_CREDENTIALS_JSON"]
# Convertir el JSON a un diccionario
credentials_dict = json.loads(credentials_json)

# Leer las credenciales desde secrets
credentials_yaml = st.secrets["LOGIN_INFO"]["STREAMLIT_CREDENTIALS_YAML"]
# Convertir el string YAML a un diccionario
config = yaml.load(credentials_yaml, Loader=SafeLoader)

santiago_tz = pytz.timezone('America/Santiago')
ayer = (datetime.date.today() - datetime.timedelta(days=1))
# Configuración de página para formato wide
st.set_page_config(page_title="Falabella Audiencias SelfService", layout="wide")

logo = Image.open('src/logo.png')
half = 0.25
logo = logo.resize( [int(half * s) for s in logo.size] )

cats_f = alternativas['categorias_f']
# cats_f = [eliminar_antes_del_guion(x) for x in cats_f]

anunciante_list = alternativas['anunciante']
anunciante_list.sort()
lapso_predefinido = alternativas['lapso_predefinido']
lapso_fijo = alternativas['lapso_fijo']
lapso_lyty = alternativas['lapso_lyty']
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
property_type = alternativas['property_type']
cluster = alternativas['cluster']

def main():
    print("Cargando main")
    st.button("Limpiar alternativas seleccionadas", on_click=clear_all)

    # Crear las 5 columnas
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Columna 1: Selector múltiple de 5 opciones y selectbox con calendario condicional
    with col1:
        
        # =============================================================================
        # Parametros Lifestyle
        # =============================================================================
        
        st.header("Lifestyles")
        lifestyle_lifestyles = st.multiselect('Lifestyle', alternativas['lifestyles'], placeholder = 'Selecciona lifestyles', key='lifestyle_lifestyles',
                                              help='Corresponde a caracterizaciones de clientes del holding de acuerdo a su transaccionalidad en los últimos 12 meses.')
        lifestyle_objetivo = st.selectbox('Objetivo de la campaña', alternativas['lifestyle_objetivo'], index=None, placeholder = "Selecciona un objetivo", key='lifestyle_objetivo',
                                          help='Ayuda a determinar el tipo de audiencia del lifestyle en base al objetivo de la campaña.')
        
        # =============================================================================
        # Parametros Arquetipo de Negocio
        # =============================================================================
        
        st.header("Arquetipo de Negocio")
        arq_neg_arq_neg = st.multiselect('Arquetipo de negocio', alternativas['arquetipo_de_negocio'], placeholder = 'Selecciona un arquetipo de negocio', key='arq_neg_arq_neg',
                                         help='Se define a partir del comportamiento de compra (frecuencia y/o gasto) para cada unidad de negocio.')
        
        # =============================================================================
        # Parametros Ranking Transaccional
        # =============================================================================
        
        st.header("Ranking de transacciones")
        rnk_trx_bu = st.selectbox('Unidad de negocio', ["Falabella", "Sodimac", "Tottus"], index=None, placeholder = "Selecciona una unidad de negocio", key='rnk_trx_bu')
        rnk_trx_kpi = st.selectbox('KPI', ["Frecuencia", "Gasto"], index=None, placeholder = "Selecciona un KPI", key='rnk_trx_kpi',
                                   help='Puede ser frecuencia de compra (cada cuánto tiempo compra en la unidad de negocio) o gasto (cuánto dinero ha gastado en la unidad de negocio), siempre considerando los últimos 12 meses.')
        rnk_trx_top_customers = st.number_input("Mejores clientes", value=None, min_value=0, placeholder="Ingresa un número mayor a 0", key='rnk_trx_top_customers',
                                                help = "Considerará a los mejores X clientes a la hora de obtener la audiencia. Por ejemplo, los top 5000 clientes de mayor gasto en Sodimac.")
        rnk_trx_canal_compra = st.selectbox('Canal de compra', ["Solo online", "Solo offline"], index=None, placeholder = 'Selecciona un canal de compra', key='rnk_trx_canal_compra',
                                            help='Permite considerar solo transacciones realizadas online (web o app) o solo presenciales.')

        # =============================================================================
        # Parametros Loyalty
        # =============================================================================

        st.header("Programa de lealtad")
        
        # Acumulación y canje #########################################################
        # Layout para tener las entradas en la misma fila
        col_lyty_acumul_1, col_lyty_acumul_2,  col_lyty_acumul_3 = st.columns([2, 1, 1])
        with col_lyty_acumul_1:
            lyty_acumul_rango = st.selectbox("Filtro de acumulación", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='lyty_acumul_rango')
            
        if lyty_acumul_rango == "Rango":
            # Input para el precio "desde"
            with col_lyty_acumul_2:
                lyty_acumul_desde = st.number_input('Acumulación desde', min_value=0, value=None, key='lyty_acumul_desde', help = 'Por ejemplo: 5000')
            # Input para el precio "hasta"
            with col_lyty_acumul_3:
                lyty_acumul_hasta = st.number_input('Acumulación hasta', min_value=0, value=None, key='lyty_acumul_hasta', help = 'Por ejemplo: 30000')
        else:
            with col_lyty_acumul_2:
                lyty_acumul_desde = st.number_input('Acumulación', min_value=0, value=None, key='lyty_acumul_desde', help = 'Por ejemplo: 5000')
        
        # Layout para tener las entradas en la misma fila
        col_lyty_canje_1, col_lyty_canje_2,  col_lyty_canje_3 = st.columns([2, 1, 1])
        with col_lyty_canje_1:
            lyty_canje_rango = st.selectbox("Filtro de canje", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='lyty_canje_rango')
            
        if lyty_canje_rango == "Rango":
            # Input para el precio "desde"
            with col_lyty_canje_2:
                lyty_canje_desde = st.number_input('Canje desde', min_value=0, value=None, key='lyty_canje_desde', help = 'Por ejemplo: 5000')
            # Input para el precio "hasta"
            with col_lyty_canje_3:
                lyty_canje_hasta = st.number_input('Canje hasta', min_value=0, value=None, key='lyty_canje_hasta', help = 'Por ejemplo: 30000')
        else:
            with col_lyty_canje_2:
                lyty_canje_desde = st.number_input('Canje', min_value=0, value=None, key='lyty_canje_desde', help = 'Por ejemplo: 5000')
        
        # Lapso ###############################################################
        lyty_lapso = st.selectbox('Lapso', lapso_lyty, index=None, placeholder = 'Selecciona un lapso', key='lyty_lapso',
                                  help='Corresponde al periodo de tiempo que se considerará la acumulación y/o el canje')
        
    # Columna 2: 4 selectbox y 4 multiselect
    with col2:
        
        # =============================================================================
        # Parametros Cross
        # =============================================================================
        
        st.header("Compras en categorías de productos")

        # Categorías F ########################################################
        cross_cat_f = st.multiselect('Categorías de productos', cats_f, placeholder = 'Selecciona categorías', key='cross_cat_f', 
                                     help='Cada categoría puede considerar productos de Falabella, Sodimac y Tottus, cuando corresponda.')
        
        # Lapso ###############################################################
        cross_lapso = st.selectbox('Lapso', lapso_predefinido, index=None, placeholder = 'Selecciona un lapso', key='cross_lapso',
                                   help='Corresponde al periodo de tiempo que se considerará en la compra de algún producto dentro de la categoría seleccionada.')
        if cross_lapso == 'Crear mi propio rango':
            cross_lapso_perso = st.date_input(
                'Selecciona un rango de fechas', 
                value=((ayer-datetime.timedelta(days=30)).replace(day=1), ayer),
                max_value = ayer, 
                key='cross_lapso_perso')
        else:
            cross_lapso_perso = None
        
        # Marca ###############################################################
        cross_brands = st.multiselect('Marcas', brands, placeholder = 'Selecciona marcas', key='cross_brands',
                                      help='Define qué marcas de productos deben haber sido compradas para ser considerado dentro de la audiencia.')
        
        # Precio ##############################################################
        # Layout para tener las entradas en la misma fila
        col_cross_1, col_cross_2,  col_cross_3 = st.columns([2, 1, 1])
        
        with col_cross_1:
            cross_precio_rango = st.selectbox("Filtro de precios (en $)", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='cross_precio_rango',
                                              help='Define el rango de precios que deben tener los productos comprados dentro de la categoría seleccionada.')

        if cross_precio_rango == "Rango":
            # Input para el precio "desde"
            with col_cross_2:
                cross_precio_desde = st.number_input("Precio desde", min_value=0, value=None, key='cross_precio_desde',
                                                     help='En $, por ejemplo: 9990')
            # Input para el precio "hasta"
            with col_cross_3:
                cross_precio_hasta = st.number_input("Precio hasta", min_value=0, value=None, key='cross_precio_hasta',
                                                     help='En $, por ejemplo: 59990')
        else:
            with col_cross_2:
                cross_precio_desde = st.number_input("Precio", min_value=0, value=None, key='cross_precio_desde',
                                                     help='En $, por ejemplo: 9990')
    
        # Canal de compra #####################################################
        cross_canal_compra = st.selectbox('Canal de compra', ["Solo online", "Solo offline"], index=None, placeholder = 'Selecciona un canal de compra', key='cross_canal_compra',
                                          help='Permite considerar solo transacciones realizadas online (web o app) o solo presenciales.')
        
        cross_top_descuento = st.checkbox("Top 20% discount seekers", key = 'cross_top_descuento',
                                       help = 'Al seleccionar este item, solo se considerarán a los top 20% de clientes que más veces compren con descuento dentro de lo seleccionado en este apartado.')        
        
        # =============================================================================
        # Parametros Arquetipo de Compra
        # =============================================================================
        
        st.header("Arquetipo de Compra")
        arq_compra_arq_compra = st.selectbox('Arquetipo de compra', arquetipo_de_compra, index=None, placeholder = "Selecciona un arquetipo", key='arquetipo_de_compra',
                                             help="""Se conforma de niveles de lealtad hacia una determinada categoría.\n- Fieles: Clientes donde más del 90% de las unidades compradas dentro de la categoría perteneces a una marca (i.e., típicamente compran esa marca dentro de la categoría)\n- Mix: Clientes que no son fieles (i.e., no tienen una marca favorita, cambian de marca dentro de la categoría)\n- Fugados: Clientes que compraban en la categoría en los últimos 6 meses, pero en los últimos 3 meses no lo han hecho""")
        
        # Marca ###############################################################
        if arq_compra_arq_compra in ['Fieles a la marca',
                                   'Fieles a competencia de la marca',
                                   'Mix que incluyen a la marca',
                                   'Mix solo entre competidores',
                                   'Fugados de la categoría que compraban la marca',
                                   'Fugados de la categoría que compraban solo la competencia',
                                   'Fugados marca en categoría',
                                   'Marca en otras categorías']:
            arq_compra_brands = st.multiselect('Marcas', brands, placeholder = 'Selecciona marcas', key='arq_compra_brands',
                                               help='De qué marca estamos hablando en la definición del arquetipo.')
        else:
            arq_compra_brands = []
            
        # Categorías F ########################################################
        arq_compra_cat_f = st.multiselect('Categorías de productos', cats_f, placeholder = 'Selecciona categorías', key='arq_compra_cat_f',
                                          help='Cada categoría puede considerar productos de Falabella, Sodimac y Tottus, cuando corresponda.')

        # Lapso ###############################################################
        arq_compra_lapso = st.selectbox('Lapso', lapso_predefinido, index=None, placeholder = 'Selecciona un lapso', key='arq_compra_lapso',
                                        help='Corresponde al periodo de tiempo que se considerará en la compra de algún producto dentro de la categoría seleccionada.')
        # if arq_compra_lapso == 'Crear mi propio rango':
        #     arq_compra_lapso_perso = st.date_input(
        #         'Selecciona un rango de fechas', 
        #         value=((ayer-datetime.timedelta(days=30)).replace(day=1), ayer),
        #         max_value = ayer, 
        #         key='arq_compra_lapso_perso')
        # else:
        #     arq_compra_lapso_perso = None
        
        # Precio ##############################################################
        # Layout para tener las entradas en la misma fila
        col_arq_compra_1, col_arq_compra_2,  col_arq_compra_3 = st.columns([2, 1, 1])
        
        with col_arq_compra_1:
            arq_compra_precio_rango = st.selectbox("Filtro de precios (en $)", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='arq_compra_precio_rango',
                                                   help='Define el rango de precios que deben tener los productos comprados dentro de la categoría seleccionada.')

        if arq_compra_precio_rango == "Rango":
            # Input para el precio "desde"
            with col_arq_compra_2:
                arq_compra_precio_desde = st.number_input('Precio desde', min_value=0, value=None, key='arq_compra_precio_desde',
                                                          help='En $, por ejemplo: 9990')
            # Input para el precio "hasta"
            with col_arq_compra_3:
                arq_compra_precio_hasta = st.number_input('Precio hasta', min_value=0, value=None, key='arq_compra_precio_hasta',
                                                          help='En $, por ejemplo: 59990')
        else:
            with col_arq_compra_2:
                arq_compra_precio_desde = st.number_input('Precio', min_value=0, value=None, key='arq_compra_precio_desde',
                                                          help='En $, por ejemplo: 9990')

    # Columna 3: Textbox
    with col3:
        
        # =============================================================================
        # Parametros CMR
        # =============================================================================

        st.header("Compras en negocios usando tarjeta de crédito")
        
        # Comercios ###########################################################
        cmr_comercios = st.multiselect('Comercios a incluir', alternativas['comercios'], placeholder = 'Selecciona comercios a incluir', key='cmr_comercios',
                                       help='Son los comercios en los que deben haber comprado para aparecer en la audiencia.')
        # cmr_keywords = st.text_input("Keywords a incluir", key='cmr_keywords')
        cmr_comercios_exclusion = st.multiselect('Comercios a excluir', alternativas['comercios'], placeholder = 'Selecciona comercios a excluir', key='cmr_comercios_exclusion',
                                                  help='La audiencia resultante no tendrá transacciones realizadas en estos comercios')
        # cmr_keywords_exclusion = st.text_input("Keywords a excluir", key='cmr_keywords_exclusion')
        
        # Lapso ###############################################################
        cmr_lapso = st.selectbox('Lapso', lapso_predefinido, index=None, placeholder = 'Selecciona un lapso', key='cmr_lapso',
                                 help='Corresponde al periodo de tiempo que se considerará en la compra dentro de los comercios seleccionados.')
        if cmr_lapso == 'Crear mi propio rango':
            cmr_lapso_perso = st.date_input(
                'Selecciona un rango de fechas', 
                value=((ayer-datetime.timedelta(days=30)).replace(day=1), ayer),
                max_value = ayer,
                key='cmr_lapso_perso')
        else:
            cmr_lapso_perso = None
        
        # Precio ##############################################################
        
        # Layout para tener las entradas en la misma fila
        col_cmr_precio_1, col_cmr_precio_2,  col_cmr_precio_3 = st.columns([2, 1, 1])
        
        with col_cmr_precio_1:
            cmr_precio_rango = st.selectbox("Filtro precios com. a incluir", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='cmr_precio_rango',
                                            help='Define el rango de precios que debe tener la transacción dentro de los comercios a incluir seleccionados.')
        
        if cmr_precio_rango == "Rango":
            # Input para el precio "desde"
            with col_cmr_precio_2:
                cmr_precio_desde = st.number_input("Precio desde", min_value=0, value=None, key='cmr_precio_desde',
                                                   help='En $, por ejemplo: 30000')
            # Input para el precio "hasta"
            with col_cmr_precio_3:
                cmr_precio_hasta = st.number_input("Precio hasta", min_value=0, value=None, key='cmr_precio_hasta',
                                                   help='En $, por ejemplo: 80000')
        else:
            with col_cmr_precio_2:
                cmr_precio_desde = st.number_input("Precio", min_value=0, value=None, key='cmr_precio_desde',
                                                   help='En $, por ejemplo: 30000')
        
        # Layout para tener las entradas en la misma fila
        col_cmr_exclusion_1, col_cmr_exclusion_2,  col_cmr_exclusion_3 = st.columns([2, 1, 1])
        
        with col_cmr_exclusion_1:
            cmr_precio_exclusion_rango = st.selectbox("Filtro precios com. a excluir", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='cmr_precio_exclusion_rango',
                                                      help='Define el rango de precios que debe tener la transacción dentro de los comercios a excluir seleccionados.')
            
        if cmr_precio_exclusion_rango == "Rango":
            # Input para el precio "desde"
            with col_cmr_exclusion_2:
                cmr_precio_exclusion_desde = st.number_input("Precio desde", min_value=0, value=None, key='cmr_precio_exclusion_desde',
                                                             help='En $, por ejemplo: 30000')
            # Input para el precio "hasta"
            with col_cmr_exclusion_3:
                cmr_precio_exclusion_hasta = st.number_input("Precio hasta", min_value=0, value=None, key='cmr_precio_exclusion_hasta',
                                                             help='En $, por ejemplo: 80000')
        else:
            with col_cmr_exclusion_2:
                cmr_precio_exclusion_desde = st.number_input("Precio", min_value=0, value=None, key='cmr_precio_exclusion_desde',
                                                             help='En $, por ejemplo: 30000')
                
        # Tipo compra #########################################################
        cmr_tipo_compra = st.selectbox('Tipo de compra comercios a incluir', ["Solo nacional", "Solo internacional"], index=None, placeholder = 'Selecciona un tipo de compra', key='cmr_tipo_compra',
                                       help = 'Permite considerar solo transacciones nacionales o internacionales para los comercios a incluir.')
        cmr_tipo_compra_exclusion = st.selectbox('Tipo de compra comercios a excluir', ["Solo nacional", "Solo internacional"], placeholder = 'Selecciona un tipo de compra', index=None, key='cmr_tipo_compra_exclusion',
                                                 help = 'Permite considerar solo transacciones nacionales o internacionales para los comercios a excluir.')

        
        
        # =============================================================================
        # Parametros Seguros
        # =============================================================================
        
        st.header("Seguros Falabella")
        
        # Lapso ###############################################################
        sf_lapso = st.selectbox('Lapso', lapso_predefinido, index=None, placeholder = "Selecciona un lapso", key='sf_lapso',
                                help='Corresponde al periodo de tiempo que se considerará en la compra del seguro.')
        # if sf_lapso == 'Crear mi propio rango':
        #     sf_lapso_perso = st.date_input(
        #         'Selecciona un rango de fechas', 
        #         value=(datetime.date(2024, 6, 1), datetime.datetime.now()),
        #         key='sf_lapso_perso')
        # else:
        #     sf_lapso_perso = None
        
        sf_seguros = st.multiselect('Tipo de seguro', alternativas['sf_seguros'], placeholder = "Selecciona seguros", key='sf_seguros')
        
    # Columna 4: Slide input que permite poner un rango de valores
    with col4:
        # =============================================================================
        # Parametros Sociodemográficos
        # =============================================================================
        
        st.header("Características sociodemográficas")
        st.write("""Si dejas las opciones en blanco, se entiende que entran todos los clientes. Por ejemplo, si no seleccionas Sexo, tu audiencia tendrá ambos sexos""")
        sociodem_sexo = st.multiselect('Sexo', sexo, placeholder = 'Selecciona un sexo', key='sociodem_sexo')
        # Layout para tener las entradas en la misma fila
        col_sociodem_edad_1, col_sociodem_edad_2, col_sociodem_edad_3 = st.columns([2, 1, 1])
        
        with col_sociodem_edad_1:
            sociodem_edad_rango = st.selectbox("Rango de edad", rango_opciones, index=None, placeholder = 'Selecciona un rango', key='sociodem_edad_rango')

        if sociodem_edad_rango == "Rango":
            # Input para el precio "desde"
            with col_sociodem_edad_2:
                sociodem_edad_desde = st.number_input('Edad desde', min_value=18, max_value=120, value=None, key = 'sociodem_edad_desde')
            # Input para el precio "hasta"
            with col_sociodem_edad_3:
                sociodem_edad_hasta = st.number_input('Edad hasta', min_value=18, max_value=120, value=None, key = 'sociodem_edad_hasta')
        else:
            with col_sociodem_edad_2:
                sociodem_edad_desde = st.number_input('Edad', min_value=18, max_value=120, value=None, key = 'sociodem_edad_desde')
                
        sociodem_gse = st.multiselect('GSE', gse, placeholder = 'Selecciona GSEs', key='sociodem_gse')
        sociodem_marital_status = st.multiselect('Estado civil', marital_status, placeholder = 'Selecciona estados civiles', key='sociodem_marital_status')
        sociodem_education_level = st.multiselect('Nivel de estudios', educational_level, placeholder = 'Selecciona niveles de estudio', key='sociodem_education_level')
        sociodem_regiones = st.multiselect('Regiones', regiones, placeholder = 'Selecciona regiones', key='sociodem_regiones')
        sociodem_comunas = st.multiselect('Comunas', comunas, placeholder = 'Selecciona comunas', key='sociodem_comunas')
        sociodem_factura = st.checkbox("Compra con facturas en últimos 2 años", key = 'sociodem_factura',
                                       help = 'Al seleccionar este item, solo se considerarán clientes que hayan pagado al menos una vez con factura en los últimos 2 años.')        
        
        # Layout para tener las entradas en la misma fila
        col_sociodem_n_propiedades_1, col_sociodem_n_propiedades_2, col_sociodem_n_propiedades_3 = st.columns([2, 1, 1])
        
        with col_sociodem_n_propiedades_1:
            sociodem_n_propiedades_rango = st.selectbox("Filtro de N° propiedades", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='sociodem_n_propiedades_rango')

        if sociodem_n_propiedades_rango == "Rango":
            # Input para el precio "desde"
            with col_sociodem_n_propiedades_2:
                sociodem_n_propiedades_desde = st.number_input('N° desde', min_value=0, value=None, key = 'sociodem_n_propiedades_desde')
            # Input para el precio "hasta"
            with col_sociodem_n_propiedades_3:
                sociodem_n_propiedades_hasta = st.number_input('N° hasta', min_value=0, value=None, key = 'sociodem_n_propiedades_hasta')
        else:
            with col_sociodem_n_propiedades_2:
                sociodem_n_propiedades_desde = st.number_input('N° propiedades', min_value=0, value=None, key = 'sociodem_n_propiedades_desde')

        sociodem_tipo_propiedad = st.multiselect('Tipo de propiedad', property_type, placeholder = 'Selecciona tipos de propiedades', key='sociodem_tipo_propiedad')

        # Layout para tener las entradas en la misma fila
        col_sociodem_valor_propiedades_1, col_sociodem_valor_propiedades_2,  col_sociodem_valor_propiedades_3 = st.columns([2, 1, 1])
        
        with col_sociodem_valor_propiedades_1:
            sociodem_valor_propiedades_rango = st.selectbox("Filtro valor propiedad (en $M)", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='sociodem_valor_propiedades_rango')
        
        if sociodem_valor_propiedades_rango == "Rango":
            # Input para el precio "desde"
            with col_sociodem_valor_propiedades_2:
                sociodem_valor_propiedad_desde = st.number_input('Valor desde', min_value=0, value=None, key = 'sociodem_valor_propiedad_desde',
                                                                 help='En millones de pesos, por ejemplo: 120.5')
            # Input para el precio "hasta"
            with col_sociodem_valor_propiedades_3:
                sociodem_valor_propiedad_hasta = st.number_input('Valor hasta', min_value=0, value=None, key = 'sociodem_valor_propiedad_hasta',
                                                                 help='En millones de pesos, por ejemplo: 180')
        else:
            with col_sociodem_valor_propiedades_2:
                sociodem_valor_propiedad_desde = st.number_input('Valor', min_value=0, value=None, key = 'sociodem_valor_propiedad_desde',
                                                                 help='En millones de pesos, por ejemplo: 120.5')

        # Layout para tener las entradas en la misma fila
        col_sociodem_m2_propiedad_1, col_sociodem_m2_propiedad_2,  col_sociodem_m2_propiedad_3 = st.columns([2, 1, 1])
        
        with col_sociodem_m2_propiedad_1:
            sociodem_m2_propiedad_rango = st.selectbox("Filtro de m2 de propiedad", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='sociodem_m2_propiedad_rango')
            
        if sociodem_m2_propiedad_rango == "Rango":
            # Input para el precio "desde"
            with col_sociodem_m2_propiedad_2:
                sociodem_m2_propiedad_desde = st.number_input('m2 desde', min_value=0, value=None, key = 'sociodem_m2_propiedad_desde')
            # Input para el precio "hasta"
            with col_sociodem_m2_propiedad_3:
                sociodem_m2_propiedad_hasta = st.number_input('m2 hasta', min_value=0, value=None, key = 'sociodem_m2_propiedad_hasta')
        else:
            with col_sociodem_m2_propiedad_2:
                sociodem_m2_propiedad_desde = st.number_input('m2 propiedad', min_value=0, value=None, key = 'sociodem_m2_propiedad_desde')
                
    # Columna 5: Selectbox
    with col5:
        # Layout para tener las entradas en la misma fila
        col_sociodem_n_vehiculos_1, col_sociodem_n_vehiculos_2, col_sociodem_n_vehiculos_3 = st.columns([2, 1, 1])
        
        with col_sociodem_n_vehiculos_1:
            sociodem_n_vehiculos_rango = st.selectbox("Filtro de N° vehículos", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='sociodem_n_vehiculos_rango')

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
        
        sociodem_tipo_vehiculo = st.multiselect('Tipo de vehículo', vehicle_type, placeholder = 'Selecciona tipos de vehículos', key='sociodem_tipo_vehiculo')
        
        # Layout para tener las entradas en la misma fila
        col_sociodem_anio_vehiculos_1, col_sociodem_anio_vehiculos_2,  col_sociodem_anio_vehiculos_3 = st.columns([2, 1, 1])
        
        with col_sociodem_anio_vehiculos_1:
            sociodem_anio_vehiculos_rango = st.selectbox("Filtro de año de vehículo", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='sociodem_anio_vehiculos_rango')
            
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
            sociodem_valor_vehiculos_rango = st.selectbox("Filtro valor vehículo (en $M)", rango_opciones, index=None, placeholder = 'Selecciona un filtro', key='sociodem_valor_vehiculos_rango')
        
        if sociodem_valor_vehiculos_rango == "Rango":
            # Input para el precio "desde"
            with col_sociodem_valor_vehiculos_2:
                sociodem_valor_vehiculos_desde = st.number_input('Valor desde', min_value=0, value=None, key = 'sociodem_valor_vehiculos_desde',
                                                                 help='En millones de pesos, por ejemplo: 5.5')
            # Input para el precio "hasta"
            with col_sociodem_valor_vehiculos_3:
                sociodem_valor_vehiculos_hasta = st.number_input('Valor hasta', min_value=0, value=None, key = 'sociodem_valor_vehiculos_hasta',
                                                                 help='En millones de pesos, por ejemplo: 25')
        else:
            with col_sociodem_valor_vehiculos_2:
                sociodem_valor_vehiculos_desde = st.number_input('Valor', min_value=0, value=None, key = 'sociodem_valor_vehiculos_desde',
                                                                 help='En millones de pesos, por ejemplo: 5.5')
        
        sociodem_marca_vehiculo = st.multiselect('Marca del vehículo', brand_vehicle, placeholder = 'Selecciona marcas de vehículos', key='sociodem_marca_vehiculo')

        # =============================================================================
        # Parametros de Cluster
        # =============================================================================
        
        st.header("Clusters")
        
        cluster_cluster = st.multiselect('Cluster', cluster, placeholder = 'Selecciona un cluster', key='cluster_cluster',
                                         help='Conjunto de características que deben cumplir los clientes, que varían dependiendo del cluster elegido. Para ver qué características tienen los cluster, ver hoja "Clusters" de excel online "Compilado audiencias"')
        
    # Crear el formulario
    with st.form(key='my_form'):
        # Botón de submit
        submit_button = st.form_submit_button(label='Enviar')

    # Mostrar los valores seleccionados
    if submit_button:
        
        # Load data from JSON file
        with open('src/json_vacio.json', 'r') as f:
            json_output = json.load(f)
        
        json_output["1_info_general"]["holding"] = holding
        json_output["1_info_general"]["agencia"] = ''
        json_output["1_info_general"]["anunciante"] = anunciante
        json_output["1_info_general"]["comentario"] = ''
        json_output["1_info_general"]["solicitada_cliente"] = '' if solicitada_cliente is None else solicitada_cliente
        json_output["1_info_general"]["solicitante"] = solicitante
        json_output["1_info_general"]["descripcion"] = descripcion
        json_output["1_info_general"]["mes_implementacion"] = mes_implementacion
        json_output["1_info_general"]["marca"] = marca
        json_output["1_info_general"]["campania"] = campania
        json_output["1_info_general"]["tipo_de_venta"] = ''
        json_output["1_info_general"]["fecha_solicitud"] = datetime.datetime.now(tz=santiago_tz).strftime('%Y-%m-%d %H:%M:%S')        
        
        json_output["2_info_lifestyle"]["lifestyle_seleccionado"] = lifestyle_lifestyles
        json_output["2_info_lifestyle"]["objetivo"] = lifestyle_objetivo
        
        json_output["3_info_cross"]["categorias_f"] = cross_cat_f
        if cross_lapso == 'Crear mi propio rango':
            json_output["3_info_cross"]["lapso"] = [x.strftime('%Y-%m-%d') for x in cross_lapso_perso]
        else:
            json_output["3_info_cross"]["lapso"] = cross_lapso
        json_output["3_info_cross"]["marcas"] = cross_brands
        if cross_precio_rango == "Rango":
            json_output["3_info_cross"]["precio"] = [cross_precio_desde, cross_precio_hasta]
        else:
            json_output["3_info_cross"]["precio"] = [cross_precio_rango, cross_precio_desde]
        json_output["3_info_cross"]["canal_compra"] = cross_canal_compra
        json_output["3_info_cross"]["top_descuento"] = cross_top_descuento
        
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
        if sociodem_edad_rango == "Rango":
            json_output["7_info_sociodemografica"]["cust_age"] = [sociodem_edad_desde, sociodem_edad_hasta]
        else:
            json_output["7_info_sociodemografica"]["cust_age"] = [sociodem_edad_rango, sociodem_edad_desde]
        json_output["7_info_sociodemografica"]["cust_gse"] = sociodem_gse
        json_output["7_info_sociodemografica"]["cust_education_level"] = sociodem_education_level
        json_output["7_info_sociodemografica"]["cust_marital_status"] = sociodem_marital_status
        json_output["7_info_sociodemografica"]["compra_con_factura"] = sociodem_factura
        json_output["7_info_sociodemografica"]["regiones"] = sociodem_regiones
        json_output["7_info_sociodemografica"]["cust_city"] = [dict_reemplazo["comunas"].get(item,item) for item in sociodem_comunas]
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
        if sociodem_n_propiedades_rango == "Rango":
            json_output["7_info_sociodemografica"]["no_of_property"] = [sociodem_n_propiedades_desde, sociodem_n_propiedades_hasta]
        else:
            json_output["7_info_sociodemografica"]["no_of_property"] = [sociodem_n_propiedades_rango, sociodem_n_propiedades_desde]
        json_output["7_info_sociodemografica"]["property_type"] = sociodem_tipo_propiedad
        if sociodem_valor_propiedades_rango == "Rango":
            json_output["7_info_sociodemografica"]["property_value"] = [sociodem_valor_propiedad_desde, sociodem_valor_propiedad_hasta]
        else:
            json_output["7_info_sociodemografica"]["property_value"] = [sociodem_valor_propiedades_rango, sociodem_valor_propiedad_desde]
        if sociodem_m2_propiedad_rango == "Rango":
            json_output["7_info_sociodemografica"]["property_built_mts"] = [sociodem_m2_propiedad_desde, sociodem_m2_propiedad_hasta]
        else:
            json_output["7_info_sociodemografica"]["property_built_mts"] = [sociodem_m2_propiedad_rango, sociodem_m2_propiedad_desde]

        if cmr_lapso == 'Crear mi propio rango':
            json_output["8_info_cmr"]["lapso"] = [x.strftime('%Y-%m-%d') for x in cmr_lapso_perso]
        else:
            json_output["8_info_cmr"]["lapso"] = cmr_lapso
        json_output["8_info_cmr"]["comercios"] = cmr_comercios
        json_output["8_info_cmr"]["comercios_exclusion"] = cmr_comercios_exclusion
        json_output["8_info_cmr"]["keywords"] = ''
        json_output["8_info_cmr"]["keywords_exclusion"] = ''
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
        json_output["9_ranking_transaccional"]["n_mejores_clientes"] = '' if rnk_trx_top_customers is None else rnk_trx_top_customers
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
        json_output["11_seguros"]["seguros"] = [dict_reemplazo["sf_seguros"].get(item,item) for item in sf_seguros]
        json_output["12_cluster"]["cluster"] = cluster_cluster
        
        # Formatea el JSON para que quede como el output que entrega el formulario de Microsoft
        json_output_formated = formateo_json(json_output)
        # Checkea que los campos estén correctamente ingresados
        if reglas_enviar_formulario(json_output_formated):
        
            # Agrega el tipo de audiencia
            json_output_formated["1_info_general"]["tipo_audiencia"] = tipo_de_audiencia(json_output_formated)
            
            # No aumentar correlativo cuando sea una prueba
            if campania != 'prueba': # Si la ejecución no es una prueba
                credenciales = login(credentials_dict)
                # Carga el último correlativo
                st.session_state.correlativo, archivo_correlativo = cargar_correlativo_desde_google_drive('ultimo_correlativo_usado.txt', credenciales)
            else:
                st.session_state.correlativo = 99900
                
            # Incrementar el ID correlativo y guardarlo
            st.session_state.correlativo += 1
            
            # Crear el nombre de la tabla en BQ
            campania_procesada = campania.strip()
            campania_procesada = ''.join((c for c in unicodedata.normalize('NFD', campania_procesada) if unicodedata.category(c) != 'Mn'))
            # Elimina caracteres raros al string de la marca (primera marca si se ingresó más de una)
            nombre_tabla_final = f"{anunciante}_{st.session_state.correlativo}_{campania_procesada}".upper().replace(" ","_").replace(".","").replace("-","_").replace('"',"").replace(',',"_").replace('/',"_").replace('&',"_").replace('(',"").replace(')',"").replace('+',"PLUS").replace('Ñ',"N")
            json_output_formated["1_info_general"]["nombre_tabla"] = nombre_tabla_final
            
            # Agrega el nombre a la audiencia
            json_output_formated["1_info_general"]["nombre_unico"] = f"{datetime.datetime.now(tz=santiago_tz).strftime('%Y%m%d')}-{holding}-{anunciante}-a{st.session_state.correlativo}-{tipo_de_script(json_output_formated)}".replace(" ", "_")
            
            # Convertir el diccionario a JSON
            datos_json = json.dumps(json_output_formated, 
                                    indent=4, # Para que tenga identación de JSON
                                    ensure_ascii=False
                                    ).encode('latin-1')
                    
            file_content = io.BytesIO(datos_json)
            
            if campania != 'prueba':
                # Subir el JSON a la carpeta online
                subir_json(file_content, json_output_formated["1_info_general"]["nombre_unico"]+'.json', credenciales)
                st.success('Requerimiento de audiencia enviada correctamente', icon="✅")
    
            # cargar_archivo_a_sharepoint(file_content.getvalue(), 
            #                             json_output["1_info_general"]["nombre_unico"]+'.json', 
            #                             st.secrets["SITE_URL"], 
            #                             st.secrets["USERNAME"], 
            #                             st.secrets["PASSWORD"], 
            #                             st.secrets["FOLDER_URL"])
            
            if campania != 'prueba':
                # Actualiza el archivo de correlativos con el último correlativo usado
                cargar_correlativo_hacia_google_drive(archivo_correlativo, str(st.session_state.correlativo))
                
                
            # cargar_archivo_a_sharepoint(st.session_state.correlativo, 
            #                             'ultimo_correlativo_usado.txt', 
            #                             st.secrets["SITE_URL"], 
            #                             st.secrets["USERNAME"], 
            #                             st.secrets["PASSWORD"], 
            #                             st.secrets["FOLDER_URL"])
            
            st.write(json_output_formated)


# =============================================================================
# Autenticación
# =============================================================================

# with open('src/conn/login.yml', encoding='utf8') as file:
#     config = yaml.load(file, Loader=SafeLoader)


# =============================================================================
# Aplicativo
# =============================================================================

if __name__ == "__main__":
    
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )


    authenticator.login()
        
    # Esta parte es para que aparezca el botón de "anunciante", ya que no aparece de inmediato
    if 'rerun' not in st.session_state:
        st.session_state.rerun = True
    if st.session_state.rerun == True:    
        st.session_state.rerun = False
        st.rerun() 
        
    if 'siguiente' not in st.session_state:
        st.session_state.siguiente = False
    
    # Inicializar la variable de sesión para controlar el estado del expander
    if 'expander_open' not in st.session_state:
        st.session_state.expander_open = True
    
    if st.session_state["authentication_status"]:
        
        # Obtiene lo que está entre corchetes
        agencia_usuario = st.session_state['name'][st.session_state['name'].find("[")+1:st.session_state['name'].find("]")] 
        if agencia_usuario!="FALABELLA":
            usuario_externo = True
            holding_list = [agencia_usuario]
            index_holding = 0
        else:
            usuario_externo = False
            holding_list = alternativas['holding']
            index_holding = None
            
        parte_superior()
        
        if st.session_state.siguiente:
            main()
            
    elif st.session_state["authentication_status"] is False:
        st.error('Usuario/contraseña es incorrecto')
    elif st.session_state["authentication_status"] is None:
        st.warning('Por favor, ingresa tu usuario y contraseña')
