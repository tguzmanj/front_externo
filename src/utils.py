# -*- coding: utf-8 -*-
"""
Created on Mon Sep  2 17:31:15 2024

@author: a.campos.mercado
"""

import json

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.files.file import File

# Funciones de formateo de JSON ###############################################
def lista_a_string(input):
    if not isinstance(input, list): # Si no es una lista
        if input is None: # A los None los deja como un string vacío
            return ""
        if input is False: # A los False los deja como string vacío
            return ""
        return str(input)
    if not input:  # Verificar si la lista está vacía
        return ""
    return ";".join(map(str, input))  # Convertir cada elemento a string y unir con punto y coma

def rangos_a_string(input_json):
    if not isinstance(input_json, list): # Si no es una lista
        return input_json
    if len(input_json)!=2: # Si la lista no tiene 2 items
        return input_json
    else:

        if input_json[1] is None: # Si segundo item es None, no se ingresó datos
            input_json = ''
        elif not isinstance(input_json[0], str): # Si primer item es número, es un rango
            input_json = f"entre {input_json[0]} y {input_json[1]}"
        elif input_json[0] == "Mayor o igual a":
            input_json = f">={input_json[1]}"
        elif input_json[0] == "Menor o igual a":
            input_json = f"<={input_json[1]}"
        elif input_json[0] == "Mayor a":
            input_json = f">{input_json[1]}"    
        elif input_json[0] == "Menor a":
            input_json = f"<{input_json[1]}"      
        elif input_json[0] == "Igual a":
            input_json = f"={input_json[1]}"      
        return input_json 
    
def formateo_json(data):
    """
    Aplica las funciones foo() y foo2() solo a los valores finales de un JSON.

    Esta función recorre recursivamente el JSON. Si encuentra un diccionario,
    llama a sí misma para procesar sus valores. Si encuentra un valor final 
    (es decir, un valor que no es ni diccionario ni lista), aplica las 
    funciones foo() y foo2() en ese orden al valor.

    Args:
    data (dict, list, o cualquier otro tipo): El JSON o estructura anidada que contiene 
    los valores a procesar.

    Returns:
    El JSON con las funciones foo() y foo2() aplicadas a los valores finales."""
    if isinstance(data, dict):
        return {key: formateo_json(value) for key, value in data.items()}
    else:
        # Aplica las funciones solo a los valores finales
        return lista_a_string(rangos_a_string(data))

# Funciones de conexión a Google Drive ########################################

def login(credentials_dict):
    # Crear una instancia de GoogleAuth
    gauth = GoogleAuth()
    
    # Configurar las credenciales del servicio
    scope = ['https://www.googleapis.com/auth/drive']
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    
    # Crear una instancia de GoogleDrive
    credenciales = GoogleDrive(gauth)
    return credenciales
   
def subir_json(archivo_a_subir, nombre_de_subida, credentials):
    """
    Sube un archivo JSON que ya está en memoria a Google Drive

    Parameters
    ----------
    archivo_a_subir : BytesIO
        Archivo JSON en memoria.
    nombre_de_subida : str
        Qué nombre se le quiere poner al archivo subido. Debe ir con su extensión.
        Ejemplo: 'archivo_a_subir.json'

    Returns
    -------
    None.

    """
    # Crear un nuevo archivo en Google Drive
    new_file = credentials.CreateFile({'title': nombre_de_subida, 'parents': [{'id': '1CJbCLgqzatVNFBsOyl2hReXdbBQFUPds'}]})
    new_file.SetContentString(archivo_a_subir.getvalue().decode('latin-1'))
    new_file.Upload()

def cargar_correlativo_desde_google_drive(archivo_con_el_correlativo, credentials):
    """
    Descarga desde Google Drive un archivo con el último correlativo utilizado

    Parameters
    ----------
    archivo_con_el_correlativo : str
        Nombre del archivo que tiene el correlativo.
    
    Returns
    -------
    int: Número correlativo.

    """
    lista_archivos = credentials.ListFile({'q': "title = '" + archivo_con_el_correlativo + "'"}).GetList()
    correlative_file = None
    for file in lista_archivos:
        # print(f'Title: {file["title"]}, ID: {file["id"]}')
        if file['title'] == archivo_con_el_correlativo:
            correlative_file = file
            break
    
    correlativo = int(correlative_file.GetContentString())
    
    return correlativo, correlative_file

def cargar_correlativo_hacia_google_drive(archivo_con_el_correlativo, new_content):
    """
    Descarga desde Google Drive un archivo con el último correlativo utilizado

    Parameters
    ----------
    archivo_con_el_correlativo : str
        Nombre del archivo que tiene el correlativo.
    
    Returns
    -------
    int: Número correlativo.

    """
    # Reemplazar el contenido del archivo existente
    archivo_con_el_correlativo.SetContentString(new_content)
    archivo_con_el_correlativo.Upload()
    print(f'Archivo {archivo_con_el_correlativo["title"]} reemplazado exitosamente.')

##########

def formatear_precio(x):
    return f'${x:,}'.replace(',', '.')

def eliminar_antes_del_guion(texto):
    # Dividimos el texto en partes usando el guion como delimitador
    partes = texto.split(' - ', 1)
    # Retornamos la segunda parte, que es lo que está después del guion
    return partes[1] if len(partes) > 1 else texto

def tipo_de_audiencia(json_requerimiento):
    
    # Si el requerimiento pedido tiene algo de CMR, entonces es Deluxe
    if any(value != "" for value in json_requerimiento['8_info_cmr'].values()):
        return 'deluxe'
    # Si el requerimiento pedido tiene algo de vehículos, entonces es Deluxe
    if any(value != "" for value in [json_requerimiento["7_info_sociodemografica"]["no_of_vehicle"], 
                                    json_requerimiento["7_info_sociodemografica"]["vehicle_yr"],
                                    json_requerimiento["7_info_sociodemografica"]["vehicle_appraised_amt"],
                                    json_requerimiento["7_info_sociodemografica"]["vehicle_type"],
                                    json_requerimiento["7_info_sociodemografica"]["vehicle_brand"]]):
        return 'deluxe'
    # Si el requerimiento pedido tiene algo de sociodemográfico, entonces es Custom
    if any(value != "" for value in json_requerimiento['7_info_sociodemografica'].values()):
        return 'custom'
    # Si el requerimiento pedido tiene algo de marcas, entonces es Custom
    if any(value != "" for value in [json_requerimiento["3_info_cross"]["marcas"], 
                                     json_requerimiento["5_info_arquetipo_compra"]["marcas"]]):
        return 'custom'
    # Si el requerimiento pedido tiene algo de precios, entonces es Custom
    if any(value != "" for value in [json_requerimiento["3_info_cross"]["precio"], 
                                     json_requerimiento["5_info_arquetipo_compra"]["precio"],
                                     json_requerimiento["8_info_cmr"]["precio"],
                                     json_requerimiento["8_info_cmr"]["precio_exclusion"]
                                     ]):
        return 'custom'
    # Si el requerimiento pedido tiene algo de ranking transaccional, entonces es Custom
    if any(value != "" for value in json_requerimiento['9_ranking_transaccional'].values()):
        return 'custom'
    # Si el requerimiento pedido tiene algo de seguros Falabella, entonces es Custom
    if any(value != "" for value in json_requerimiento['11_seguros'].values()):
        return 'custom'
    else:
        return 'standard'

def tipo_de_script(json_requerimiento):
    
    # Si el requerimiento pedido tiene algo de arquetipos, entonces es S2
    if not all(value == '' for value in json_requerimiento['5_info_arquetipo_compra'].values()):
        return 'S2'
    else:
        return 'S1'

# Funciones de conexión a Sharepoint ##########################################

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