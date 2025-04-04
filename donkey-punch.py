import requests
import json
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
import os
from datetime import datetime
import socket
import whois
import re
from bs4 import BeautifulSoup
import dns.resolver
import urllib.parse
import time
from concurrent.futures import ThreadPoolExecutor
import random

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def validate_phone_number(number):
    try:
        parsed_number = phonenumbers.parse(number, None)
        return phonenumbers.is_valid_number(parsed_number)
    except:
        return False

def get_basic_info(number):
    parsed_number = phonenumbers.parse(number, None)
    country_code = phonenumbers.region_code_for_number(parsed_number)
    
    basic_info = {
        "Número formateado": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "País": geocoder.description_for_number(parsed_number, "es"),
        "Código de país": country_code,
        "Operadora": carrier.name_for_number(parsed_number, "es"),
        "Zona horaria": timezone.time_zones_for_number(parsed_number),
        "Es posible número": phonenumbers.is_possible_number(parsed_number),
        "Es válido número": phonenumbers.is_valid_number(parsed_number),
        "Tipo de número": get_number_type(parsed_number),
        "Código nacional": parsed_number.national_number,
        "Código de área": get_area_code(parsed_number, country_code)
    }
    return basic_info

def get_number_type(parsed_number):
    number_type = phonenumbers.number_type(parsed_number)
    types = {
        0: "Fijo",
        1: "Móvil",
        2: "Fijo",
        3: "Móvil",
        4: "Toll Free",
        5: "Premium Rate",
        6: "Shared Cost",
        7: "VoIP",
        8: "Personal Number",
        9: "Pager",
        10: "UAN",
        11: "Desconocido"
    }
    return types.get(number_type, "Desconocido")

def get_area_code(parsed_number, country_code):
    try:
        # Para algunos países podemos extraer el código de área
        if country_code in ["US", "CA", "BR"]:
            return str(parsed_number.national_number)[:3]
        elif country_code in ["GB", "DE", "FR", "ES"]:
            return str(parsed_number.national_number)[:2] or "N/A"
        return "N/A"
    except:
        return "N/A"

def check_google_search(number):
    try:
        formatted_number = phonenumbers.format_number(
            phonenumbers.parse(number, None),
            phonenumbers.PhoneNumberFormat.E164
        ).replace("+", "")
        
        url = f"https://www.google.com/search?q={formatted_number}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = {
            "Enlaces relacionados": [],
            "Menciones": 0
        }
        
        # Extraer enlaces relevantes
        for link in soup.find_all('a', href=True):
            href = link['href']
            if "http" in href and not any(x in href for x in ["google.com", "youtube.com"]):
                clean_link = re.sub(r'&sa=.*', '', href.replace("/url?q=", ""))
                results["Enlaces relacionados"].append(urllib.parse.unquote(clean_link))
        
        # Contar menciones del número
        mentions = response.text.count(formatted_number)
        results["Menciones"] = mentions
        
        # Limitar a 5 enlaces únicos
        results["Enlaces relacionados"] = list(set(results["Enlaces relacionados"]))[:5]
        
        return results
    except Exception as e:
        return {"error": f"Búsqueda fallida: {str(e)}"}

def check_social_media(number):
    try:
        formatted_number = phonenumbers.format_number(
            phonenumbers.parse(number, None),
            phonenumbers.PhoneNumberFormat.E164
        ).replace("+", "")
        
        social_media = {
            "Facebook": f"https://www.facebook.com/login/identify/?ctx=recover&phone={formatted_number}",
            "Twitter": f"https://twitter.com/search?q={formatted_number}&src=typed_query",
            "Instagram": f"https://www.instagram.com/accounts/account_recovery/?phone_number={formatted_number}",
            "LinkedIn": f"https://www.linkedin.com/pub/dir/?phone={formatted_number}",
            "VK": f"https://vk.com/people/{formatted_number}"
        }
        
        return social_media
    except:
        return {"error": "No se pudo generar enlaces de redes sociales"}

def check_breach_data(number):
    try:
        formatted_number = phonenumbers.format_number(
            phonenumbers.parse(number, None),
            phonenumbers.PhoneNumberFormat.E164
        ).replace("+", "")
        
        # Simular consulta a Have I Been Pwned (sin API key)
        url = f"https://haveibeenpwned.com/unifiedsearch/{formatted_number}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return {"status": "Posible filtración encontrada", "source": "Have I Been Pwned"}
        elif response.status_code == 404:
            return {"status": "No se encontraron filtraciones conocidas"}
        else:
            return {"status": "No se pudo verificar", "error": response.status_code}
    except:
        return {"error": "No se pudo verificar datos de filtraciones"}

def check_domain_registrar(number):
    try:
        # Extraer código de país
        parsed_number = phonenumbers.parse(number, None)
        country_code = phonenumbers.region_code_for_number(parsed_number)
        
        # Buscar dominios relacionados con el código de país
        url = f"https://www.whois.com/whois/{country_code.lower()}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        registrar_info = {
            "Dominio ccTLD": f".{country_code.lower()}",
            "Registrador": "No encontrado",
            "Información": "No encontrada"
        }
        
        # Intentar extraer información del registrador
        for div in soup.find_all('div', class_='df-raw'):
            if "Registrar:" in div.text:
                registrar_info["Registrador"] = div.text.replace("Registrar:", "").strip()
            if "URL:" in div.text:
                registrar_info["Información"] = div.text.strip()
        
        return registrar_info
    except:
        return {"error": "No se pudo obtener información del registrador"}

def check_phone_book(number):
    try:
        formatted_number = phonenumbers.format_number(
            phonenumbers.parse(number, None),
            phonenumbers.PhoneNumberFormat.E164
        ).replace("+", "")
        
        # Directorios telefónicos comunes
        phone_books = {
            "TruePeopleSearch": f"https://www.truepeoplesearch.com/results?phoneno={formatted_number}",
            "SpyDialer": f"https://www.spydialer.com/default.aspx?phone={formatted_number}",
            "WhitePages": f"https://www.whitepages.com/phone/{formatted_number}",
            "AnyWho": f"https://www.anywho.com/phone/{formatted_number}",
            "NumberGuru": f"https://www.numberguru.com/phone/{formatted_number}"
        }
        
        return phone_books
    except:
        return {"error": "No se pudo generar enlaces a directorios"}

def check_carrier_info(number):
    try:
        parsed_number = phonenumbers.parse(number, None)
        carrier_name = carrier.name_for_number(parsed_number, "en")
        
        if not carrier_name:
            return {"Operadora": "Desconocida"}
        
        # Buscar información adicional sobre la operadora
        wikipedia_url = f"https://en.wikipedia.org/wiki/{carrier_name.replace(' ', '_')}"
        
        return {
            "Operadora": carrier_name,
            "Wikipedia": wikipedia_url,
            "Sitio web oficial": guess_carrier_website(carrier_name)
        }
    except:
        return {"error": "No se pudo obtener información de la operadora"}

def guess_carrier_website(carrier_name):
    # Mapeo simple de operadoras a sus sitios web
    carriers = {
        "Movistar": "https://www.movistar.es",
        "Vodafone": "https://www.vodafone.es",
        "Orange": "https://www.orange.es",
        "T-Mobile": "https://www.t-mobile.com",
        "Verizon": "https://www.verizon.com",
        "AT&T": "https://www.att.com",
        "Claro": "https://www.claro.com",
        "Telcel": "https://www.telcel.com",
        "O2": "https://www.o2.co.uk",
        "EE": "https://ee.co.uk"
    }
    
    for name, url in carriers.items():
        if name.lower() in carrier_name.lower():
            return url
    
    return "No identificado"

def check_number_reputation(number):
    try:
        # Usar servicios públicos de reputación
        formatted_number = phonenumbers.format_number(
            phonenumbers.parse(number, None),
            phonenumbers.PhoneNumberFormat.E164
        ).replace("+", "")
        
        services = {
            "Numspy": f"https://numspy.io/number/{formatted_number}",
            "Sync.me": f"https://sync.me/search/?number={formatted_number}",
            "SpamCalls": f"https://spamcalls.net/en/search?q={formatted_number}",
            "Tellows": f"https://www.tellows.es/num/{formatted_number}"
        }
        
        # Verificar si el número está reportado como spam
        spam_reports = 0
        for service, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if "spam" in response.text.lower() or "scam" in response.text.lower():
                    spam_reports += 1
            except:
                continue
        
        return {
            "Servicios de reputación": services,
            "Reportes de spam": spam_reports,
            "Calificación de riesgo": "Alto" if spam_reports > 1 else "Moderado" if spam_reports == 1 else "Bajo"
        }
    except:
        return {"error": "No se pudo verificar reputación"}

def check_whatsapp(number):
    try:
        formatted_number = phonenumbers.format_number(
            phonenumbers.parse(number, None),
            phonenumbers.PhoneNumberFormat.E164
        ).replace("+", "")
        
        url = f"https://wa.me/{formatted_number}"
        
        return {
            "Enlace WhatsApp": url,
            "WhatsApp Business": f"https://api.whatsapp.com/send/?phone={formatted_number}&text&type=phone_number&app_absent=0"
        }
    except:
        return {"error": "No se pudo generar enlace de WhatsApp"}

def check_telegram(number):
    try:
        formatted_number = phonenumbers.format_number(
            phonenumbers.parse(number, None),
            phonenumbers.PhoneNumberFormat.E164
        ).replace("+", "")
        
        return {
            "Enlace Telegram": f"https://t.me/{formatted_number}"
        }
    except:
        return {"error": "No se pudo generar enlace de Telegram"}

def check_phone_blacklists(number):
    try:
        formatted_number = phonenumbers.format_number(
            phonenumbers.parse(number, None),
            phonenumbers.PhoneNumberFormat.E164
        ).replace("+", "")
        
        blacklists = {
            "ShouldIAnswer": f"https://www.shouldianswer.com/phone/{formatted_number}",
            "CallerCenter": f"https://callercenter.com/{formatted_number}",
            "PhoneBook": f"https://www.phonebook.com/phone/{formatted_number}"
        }
        
        return blacklists
    except:
        return {"error": "No se pudo verificar listas negras"}

def check_phone_format_variations(number):
    try:
        parsed_number = phonenumbers.parse(number, None)
        variations = {
            "E164": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164),
            "Internacional": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "Nacional": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL),
            "RFC3966": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.RFC3966),
            "Sin formato": str(parsed_number.national_number),
            "Sin código de área": str(parsed_number.national_number)[-7:],
            "Solo código de área": str(parsed_number.national_number)[:3] if len(str(parsed_number.national_number)) > 7 else "N/A"
        }
        return variations
    except:
        return {"error": "No se pudo generar variaciones"}

def save_to_file(number, data):
    filename = f"reporte_{number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Guardar en formato JSON para mejor estructura
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    # También crear una versión legible en texto
    txt_filename = filename.replace('.json', '.txt')
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write(f"Reporte para el número: {number}\n")
        f.write(f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for section, content in data.items():
            f.write(f"=== {section.upper()} ===\n")
            
            if isinstance(content, dict):
                for key, value in content.items():
                    if isinstance(value, (dict, list)):
                        f.write(f"{key}:\n")
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                f.write(f"  {subkey}: {subvalue}\n")
                        else:
                            for item in value:
                                f.write(f"  - {item}\n")
                    else:
                        f.write(f"{key}: {value}\n")
            elif isinstance(content, list):
                for item in content:
                    f.write(f"- {item}\n")
            else:
                f.write(f"{content}\n")
            
            f.write("\n")
    
    return txt_filename, filename

def parallel_check(number, functions):
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(func, number): name for name, func in functions.items()}
        
        for future in futures:
            name = futures[future]
            try:
                results[name] = future.result()
                time.sleep(random.uniform(0.5, 2))  # Evitar rate limiting
            except Exception as e:
                results[name] = {"error": str(e)}
    
    return results

def main():
    clear_screen()
    print("""
 /$$$$$$$   /$$$$$$  /$$   /$$ /$$   /$$ /$$$$$$$$ /$$     /$$       /$$$$$$$  /$$   /$$ /$$   /$$  /$$$$$$  /$$   /$$
| $$__  $$ /$$__  $$| $$$ | $$| $$  /$$/| $$_____/|  $$   /$$/      | $$__  $$| $$  | $$| $$$ | $$ /$$__  $$| $$  | $$
| $$  \ $$| $$  \ $$| $$$$| $$| $$ /$$/ | $$       \  $$ /$$/       | $$  \ $$| $$  | $$| $$$$| $$| $$  \__/| $$  | $$
| $$  | $$| $$  | $$| $$ $$ $$| $$$$$/  | $$$$$     \  $$$$/        | $$$$$$$/| $$  | $$| $$ $$ $$| $$      | $$$$$$$$
| $$  | $$| $$  | $$| $$  $$$$| $$  $$  | $$__/      \  $$/         | $$____/ | $$  | $$| $$  $$$$| $$      | $$__  $$
| $$  | $$| $$  | $$| $$\  $$$| $$\  $$ | $$          | $$          | $$      | $$  | $$| $$\  $$$| $$    $$| $$  | $$
| $$$$$$$/|  $$$$$$/| $$ \  $$| $$ \  $$| $$$$$$$$    | $$          | $$      |  $$$$$$/| $$ \  $$|  $$$$$$/| $$  | $$
|_______/  \______/ |__/  \__/|__/  \__/|________/    |__/          |__/       \______/ |__/  \__/ \______/ |__/  |__/
    """)
    print("Herramienta avanzada de análisis de números telefónicos - OSINT\n")
    
    while True:
        number = input("Ingrese el número telefónico con código de país (ej: +34123456789) o 'q' para salir: ")
        
        if number.lower() == 'q':
            break
            
        if not validate_phone_number(number):
            print("\n¡Número no válido! Por favor ingrese un número válido con código de país.\n")
            continue
            
        print("\nRecopilando información... Esto puede tomar unos minutos.\n")
        
        # Lista de funciones de verificación
        check_functions = {
            "Información básica": get_basic_info,
            "Búsqueda en Google": check_google_search,
            "Redes sociales": check_social_media,
            "Datos de filtraciones": check_breach_data,
            "Información de operadora": check_carrier_info,
            "Reputación del número": check_number_reputation,
            "WhatsApp/Telegram": lambda x: {"WhatsApp": check_whatsapp(x), "Telegram": check_telegram(x)},
            "Listas negras": check_phone_blacklists,
            "Directorios telefónicos": check_phone_book,
            "Variaciones de formato": check_phone_format_variations,
            "Registro de dominio": check_domain_registrar
        }
        
        # Ejecutar verificaciones en paralelo
        data = parallel_check(number, check_functions)
        
        # Guardar resultados
        txt_file, json_file = save_to_file(number, data)
        
        print("\n=== RESUMEN DE INFORMACIÓN OBTENIDA ===")
        print(f"\nPaís: {data['Información básica'].get('País', 'Desconocido')}")
        print(f"Operadora: {data['Información básica'].get('Operadora', 'Desconocida')}")
        print(f"Tipo de número: {data['Información básica'].get('Tipo de número', 'Desconocido')}")
        
        if 'Búsqueda en Google' in data and 'Menciones' in data['Búsqueda en Google']:
            print(f"\nMenciones en Google: {data['Búsqueda en Google']['Menciones']}")
            if data['Búsqueda en Google']['Enlaces relacionados']:
                print("Enlaces relevantes encontrados (ver reporte para detalles)")
        
        if 'Reputación del número' in data:
            print(f"\nReportes de spam: {data['Reputación del número'].get('Reportes de spam', 0)}")
            print(f"Calificación de riesgo: {data['Reputación del número'].get('Calificación de riesgo', 'Desconocido')}")
        
        if 'WhatsApp/Telegram' in data:
            print("\nEnlaces de mensajería disponibles (ver reporte)")
        
        if 'Directorios telefónicos' in data:
            print("\nDirectorios telefónicos verificados (ver reporte)")
        
        print(f"\nSe han guardado reportes completos en:")
        print(f"- Formato legible: {txt_file}")
        print(f"- Formato JSON: {json_file}\n")

if __name__ == "__main__":
    main()
