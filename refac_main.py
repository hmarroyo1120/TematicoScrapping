# mi version (main14.py)+ roy version 1 (main16.py): uso semi-manual (para evitar programar la búsqueda)
# búsqueda avanzada por campos: Estado o federación = Queretaro
# dans powershell: $env:NODE_OPTIONS="--max-old-space-size=8192"
# ----------------------------------------
# para 2023
# ----------------------------------------
from pymsgbox import *
from playwright.sync_api import sync_playwright,TimeoutError 
from typing import List 
from playwright.sync_api._generated import Page
import pandas as pd 
from math import ceil
from re import findall,compile
import time
import codecs
import json 
from copy import deepcopy
# from connector import MySql


# global vars & intialisations : 
data = []
manual = False 
begins_from = 0

# Create a database connection
# mySql = MySql()
start_url = "https://tematicos.plataformadetransparencia.org.mx/web/guest/informacionrelevante?p_p_id=informacionrelevante_WAR_Informacionrelevante&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_informacionrelevante_WAR_Informacionrelevante_controller=DirectorioController"
annee = "2023"
_timeout = 1500


# helper functions : 
def close_popup(page):
    while True:
        try:
            page.click(
                "//div[@class='col-md-1 bg-alicegray']/i[@class='fa fa-times no-print']")
        except (Exception,):
            time.sleep(1)
        return True


def next_page(page):
    while True:
        try:
            page.locator(
                "//a[@class='paginate_button next']").first.click(timeout=60000)
        except (Exception,):
            time.sleep(2)
        return True
    
def get_total_pages(source:str) -> int :
    return ceil(int(findall('"totalResultado":(\d+)',source)[0])/20)
    
    
def data_extractor(source:str,federation:str,annee:str) -> List[str]:
    cleaned_source = codecs.decode(source,'unicode_escape')
    cleaned_source = cleaned_source.replace('\\','')
    regex = '\\{"informacionPrincipal"[\\s\\S]+?"idInformacion":"\\d+"\\}'
    people_raw_objs = findall(regex,cleaned_source)
    extracted_items = [
        json.loads(
            raw_obj.replace('"{','{').replace('}"','}')
        ) 
        for raw_obj in people_raw_objs
    ]
    new_data = [
        {
            'federation':federation,
            'annee':annee,
            'nom':item['informacionPrincipal']['nombre'],
            'poste':item['informacionPrincipal']['denominacion'],
            'courriel':item['informacionSecundaria']['correo']
        } for item in extracted_items
    ]
    [log_item(item) for item in new_data]
    return new_data


def get_data_source(page:Page) -> str :
    with page.expect_response(compile('p_p_resource_id')) as response_info : 
        response = response_info.value 
        return response.text()
    
def export(federation,annee):
    global data             
    pd.DataFrame(data).to_csv('output.csv')
    
def visit_first_page_urls(page:Page,federation:str):
    global data 
    all_urls = page.query_selector_all(
        "//tbody[contains(@id,'tbodyDirectorio')]/tr")
    for url in all_urls:
        # on clique sur le popup
        try:
            url.click()
            page.wait_for_timeout(1000)
        except (Exception,):
            try:
                url.click(force=True)
                page.wait_for_timeout(1000)
            except (Exception,):
                try:
                    page.dispatch_event(url, 'click')
                    page.wait_for_timeout(1000)
                except (Exception,):
                    pass
    
        print(f"federation: {federation}")
        print(f"année: {annee}")

        nom = '' #obj['informacionPrincipal']['nombre']
        try:
            nom = page.locator(
                "//label[@id='modalDNombre']").inner_text()
        except (Exception,):
            pass
        print(f"nom: {nom}")

        poste = ''
        try:
            poste = page.locator(
                "//label[@id='modalDCargo']").inner_text()
        except (Exception,):
            pass
        print(f"poste: {poste}")

        courriel = ''#obj['informacionSecundaria']['correo']
        try:
            courriel = page.locator(
                "//label[@id='modalDCorreo']").inner_text()
        except (Exception,):
            pass
        print(f"courriel: {courriel}")
        print()
        data.append(
            {
                'federation':federation,
                'annee':annee,
                'nom':nom,
                'poste':poste,
                'courriel':courriel
            }
        )
        export(federation,annee)
        close_popup(page)
        insert_row(federation,annee,nom,poste,courriel)

def log_item(item:dict):
        print(f"federation: {item['federation']}")
        print(f"année: {item['annee']}")
        print(f"nom: {item['nom']}")
        print(f"poste: {item['poste']}")
        print(f"courriel: {item['courriel']}")
        print()

def insert_row(*args):
    #   Insérer un nouvel enregistrement dans la table data
    sql = """
            INSERT INTO data (federation, annee, nom, poste, courriel)
            VALUES (%s, %s, %s, %s, %s)
            """
    val = args
    # mySql.insert(sql, val)

    
def run(p,federation):
    global data
    global manual
    browser = p.chromium.launch(
        headless=False,executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
    page = browser.new_page()
    page.set_default_timeout(60000)

    # on se connecte sur la page principale
    page.goto(start_url)
    page.wait_for_load_state('load')

    alert("fais la recherche manuellement comme stipulé par Guillaume")

    page.wait_for_selector('//input[@id="busqueda"]') ## 

    # on écrit la fédération dans le champ de recherche
    page.fill("//input[@id='busqueda']", federation)
    page.wait_for_timeout(_timeout)

    # on lance la recherche
    while True : 
        try : 
            page.press("//input[@id='busqueda']", 'Enter')
            with page.expect_response(compile('p_p_resource_id'),timeout=500) as response_value :
                pass 
        except TimeoutError :
            continue 
        # on clique sur le checkbox 2023 pour filtrer les données 2023
        try :
            page.click("//input[@id='a_2023']",timeout=5000)
        except TimeoutError :
            manual = True 
            break 
        with page.expect_response(compile('p_p_resource_id'),timeout=5000) as response_value :
            first_page_source = response_value.value.text()
            data += data_extractor(first_page_source,federation,annee) if not begins_from else data
            export(federation,annee)
            total_pages = get_total_pages(first_page_source)
            break
    alert("si la recherche est correcte, valide et sinon fais la recherche correctemente manuellement et valide")
    if manual :
        total_pages = max(
            [
                int(handle.inner_text()) for handle in page.query_selector_all('//a[@class="paginate_button "]')
            ]
        )

    
    cont = 0
    [next_page(page) for _ in range(1,begins_from+1)]
    data += data_extractor(get_data_source(page),federation,annee) if begins_from else []
    export(federation,annee) if begins_from else None 
    cont = begins_from 
    while True : 
        cont += 1 
        if manual and cont == 1:
            visit_first_page_urls(page,federation)
            manual = False 
        if cont == total_pages : 
            print('last page')
            break 
        next_page(page)
        data += data_extractor(get_data_source(page),federation,annee)
        export(federation,annee)
    [insert_row(item) for item in data]

def main(federation):
    with sync_playwright() as p :
        run(p,federation)


if __name__ == '__main__':
    #main("Instituto de Ecología, A.C. (INECOL)")
    main("Instituto Nacional de Electricidad y Energías Limpias (INEEL)")
    #main("Comisión Nacional para el Uso Eficiente de la Energía (CONUEE)")
    #main("Petróleos Mexicanos (PEMEX)")
    #main("Instituto Nacional de Ecología y Cambio Climático (INECC)")
    #main("Comisión Nacional de Hidrocarburos (CNH)")
    # main("Comisión Federal de Competencia Económica (COFECE)")
    # main("Banco Nacional de Obras y Servicios Públicos, S.N.C. (BANOBRAS)")
    # main("Centro Nacional de Control del Gas Natural (CENAGAS)")
    # main("Banco Nacional de Comercio Exterior, S.N.C. (BANCOMEXT)")
    #main("Secretaría de Energía (SENER)")
    # main("Comisión Reguladora de Energía (CRE)")
    # main("Centro Nacional de Control de Energía (CENACE)")
    # main("Instituto Politécnico Nacional (IPN)")
    # main("Nacional Financiera, S.N.C. (NAFIN)")
    # main("Instituto Mexicano del Petróleo (IMP)")
    # main("Secretaría de Economía (SE)")
    # main("Secretaría de Relaciones Exteriores (SRE)")
    # main("Secretaría de Medio Ambiente y Recursos Naturales (SEMARNAT)")
    # main("Secretaría de Infraestructura, Comunicaciones y Transportes (SICT)")
    # main("Universidad Nacional Autónoma de México (UNAM)")
    # main("Comisión Federal de Electricidad (CFE)")
    # main("Banco de México (BANXICO)")
    # main("Centro de Investigación en Materiales Avanzados, S.C. (CIMAV)")
    # main("Centro de Investigación y Desarrollo Tecnológico en Electroquímica, S.C. (CIDETEQ)")
    # main("Fondo Nacional de Fomento al Turismo (FONATUR)")
    # main("Instituto Federal de Telecomunicaciones (IFT)")
    # main("Instituto Nacional del Suelo Sustentable (INSUS)")