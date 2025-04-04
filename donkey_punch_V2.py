import re
import time
import json
import os
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse
import requests
from bs4 import BeautifulSoup
import random

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def validate_phone_number(number):
    """Valida el número telefónico con mayor precisión"""
    try:
        parsed_number = phonenumbers.parse(number, None)
        if not phonenumbers.is_valid_number(parsed_number):
            return False
        
        # Validación adicional basada en patrones
        national_num = str(parsed_number.national_number)
        
        # Rechazar números con demasiados dígitos repetidos
        if re.search(r'(\d)\1{6,}', national_num):
            return False
            
        # Rechazar secuencias simples
        simple_sequences = [
            '1234567', '2345678', '3456789', '4567890',
            '9876543', '8765432', '7654321', '6543210'
        ]
        if any(seq in national_num for seq in simple_sequences):
            return False
            
        return True
    except:
        return False

def get_basic_info(number):
    """Obtiene información básica mejorada con datos específicos por país"""
    try:
        parsed_number = phonenumbers.parse(number, None)
        if not phonenumbers.is_valid_number(parsed_number):
            return {"error": "Número no válido"}
        
        country_code = phonenumbers.region_code_for_number(parsed_number)
        country_name = geocoder.description_for_number(parsed_number, "es") or "Desconocido"
        carrier_name = carrier.name_for_number(parsed_number, "es") or "Desconocida"
        
        # Mapeo extendido de tipos de número
        number_type_map = {
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
            11: "Desconocido",
            12: "Emergencia",
            13: "Voicemail",
            14: "Servicio Corto"
        }
        
        basic_info = {
            "Número formateado": phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "País": country_name,
            "Código de país": country_code,
            "Operadora": carrier_name,
            "Zona horaria": timezone.time_zones_for_number(parsed_number),
            "Es posible número": phonenumbers.is_possible_number(parsed_number),
            "Es válido número": phonenumbers.is_valid_number(parsed_number),
            "Tipo de número": number_type_map.get(phonenumbers.number_type(parsed_number), "Desconocido"),
            "Código nacional": parsed_number.national_number,
            "Código de área": get_area_code(parsed_number, country_code),
            "Línea": get_line_number(parsed_number, country_code),
            "Formato local": get_local_format(parsed_number, country_code)
        }
        
        # Añadir información específica por país
        basic_info.update(get_country_specific_info(parsed_number, country_code))
        
        return basic_info
    except Exception as e:
        return {"error": f"Error al analizar número: {str(e)}"}

def get_country_specific_info(parsed_number, country_code):
    """Información específica según el país"""
    info = {}
    national_num = str(parsed_number.national_number)
    country_code = country_code.upper()
    
    # Base de datos de formatos locales por país
    local_formats = {
        "US": f"({national_num[:3]}) {national_num[3:6]}-{national_num[6:]}",
        "ES": f"{national_num[:3]} {national_num[3:6]} {national_num[6:]}",
        "MX": f"{national_num[:3]} {national_num[3:7]} {national_num[7:]}",
        "AR": f"{national_num[:4]} {national_num[4:8]}",
        "BR": f"({national_num[:2]}) {national_num[2:7]}-{national_num[7:]}",
        "CO": f"{national_num[:3]} {national_num[3:6]} {national_num[6:]}",
        "CL": f"{national_num[:1]} {national_num[1:5]} {national_num[5:]}",
        "PE": f"{national_num[:3]} {national_num[3:6]} {national_num[6:]}",
        "FR": f"{national_num[:1]} {national_num[1:2]} {national_num[2:4]} {national_num[4:6]} {national_num[6:8]}",
        "DE": f"{national_num[:2]}-{national_num[2:4]}-{national_num[4:]}",
        "IT": f"{national_num[:3]} {national_num[3:7]} {national_num[7:]}",
        "GB": f"{national_num[:4]} {national_num[4:6]} {national_num[6:]}"
    }
    
    if country_code in local_formats:
        info["Formato local"] = local_formats[country_code]
    
    # Información adicional por país
    if country_code == "US":
        info["Notas"] = "Código de área de 3 dígitos, número local de 7 dígitos"
    elif country_code == "ES":
        info["Notas"] = "Prefijo provincial de 3 dígitos, número local de 6 dígitos"
    elif country_code == "MX":
        info["Notas"] = "LADA de 3 dígitos, número local de 7 u 8 dígitos"
    
    return info

def get_area_code(parsed_number, country_code):
    """Obtiene el código de área con mayor precisión"""
    national_num = str(parsed_number.national_number)
    country_code = country_code.upper()
    
    # Mapeo de códigos de área por país
    area_code_rules = {
        "US": 3, "CA": 3, "BR": 2,
        "GB": 2, "DE": 2, "FR": 2, "ES": 3,
        "MX": 3, "AR": 4, "CO": 3, "CL": 1,
        "PE": 3, "AU": 1, "NZ": 1, "IN": 2
    }
    
    if country_code in area_code_rules:
        digits = area_code_rules[country_code]
        return national_num[:digits] if len(national_num) > digits else "N/A"
    
    return "N/A"

def get_line_number(parsed_number, country_code):
    """Obtiene el número de línea (últimos dígitos)"""
    national_num = str(parsed_number.national_number)
    country_code = country_code.upper()
    
    # Reglas por país para el número de línea
    line_rules = {
        "US": 7, "CA": 7, "BR": 8,
        "ES": 6, "MX": 7, "AR": 6,
        "CO": 7, "CL": 8, "PE": 6,
        "FR": 8, "DE": 8, "IT": 7,
        "GB": 7, "AU": 8, "NZ": 7
    }
    
    if country_code in line_rules:
        digits = line_rules[country_code]
        return national_num[-digits:] if len(national_num) >= digits else national_num
    
    return national_num[-7:] if len(national_num) >= 7 else national_num

def get_local_format(parsed_number, country_code):
    """Devuelve el formato local estándar para el número"""
    national_num = str(parsed_number.national_number)
    country_code = country_code.upper()
    
    # Formatos locales estándar
    formats = {
        "US": f"({national_num[:3]}) {national_num[3:6]}-{national_num[6:]}",
        "ES": f"{national_num[:3]} {national_num[3:6]} {national_num[6:]}",
        "MX": f"{national_num[:3]} {national_num[3:7]} {national_num[7:]}",
        "AR": f"{national_num[:4]} {national_num[4:8]}",
        "BR": f"{national_num[:2]} {national_num[2:7]}-{national_num[7:]}",
        "CO": f"{national_num[:3]} {national_num[3:6]} {national_num[6:]}",
        "CL": f"{national_num[:1]} {national_num[1:5]} {national_num[5:]}",
        "PE": f"{national_num[:3]} {national_num[3:6]} {national_num[6:]}",
        "FR": f"{national_num[:2]} {national_num[2:4]} {national_num[4:6]} {national_num[6:8]}",
        "DE": f"{national_num[:2]}/{national_num[2:4]}/{national_num[4:]}",
        "IT": f"{national_num[:3]} {national_num[3:7]} {national_num[7:]}",
        "GB": f"{national_num[:4]} {national_num[4:6]} {national_num[6:]}"
    }
    
    return formats.get(country_code, phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.NATIONAL))

def check_google_search(number):
    """Búsqueda en Google mejorada con múltiples formatos"""
    try:
        parsed = phonenumbers.parse(number, None)
        formats = [
            phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164).replace("+", ""),
            phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
            phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.RFC3966),
            str(parsed.national_number),
            str(parsed.national_number)[-7:]  # Últimos 7 dígitos
        ]
        
        # Eliminar duplicados
        formats = list(set(formats))
        
        results = {
            "Enlaces relacionados": set(),
            "Menciones": 0,
            "Formatos buscados": formats,
            "Resultados_por_formato": {}
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Buscar cada formato del número
        for num_format in formats:
            clean_num = re.sub(r'[^0-9]', '', num_format)
            if not clean_num:
                continue
                
            url = f"https://www.google.com/search?q={urllib.parse.quote(clean_num)}"
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Contar menciones
                mentions = response.text.count(clean_num)
                results["Menciones"] += mentions
                results["Resultados_por_formato"][num_format] = mentions
                
                # Extraer enlaces
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if "http" in href and not any(x in href for x in ["google.com", "youtube.com"]):
                        clean_link = re.sub(r'&sa=.*', '', href.replace("/url?q=", ""))
                        results["Enlaces relacionados"].add(urllib.parse.unquote(clean_link))
                
                time.sleep(random.uniform(1, 3))  # Evitar rate limiting
            except Exception as e:
                results["Resultados_por_formato"][num_format] = f"Error: {str(e)}"
                continue
        
        results["Enlaces relacionados"] = list(results["Enlaces relacionados"])[:10]
        return results
    except Exception as e:
        return {"error": f"Búsqueda fallida: {str(e)}"}

def check_social_media(number):
    """Genera enlaces para buscar en redes sociales"""
    try:
        parsed = phonenumbers.parse(number, None)
        clean_num = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164).replace("+", "")
        national_num = str(parsed.national_number)
        
        social_media = {
            "Facebook": f"https://www.facebook.com/login/identify/?ctx=recover&phone={clean_num}",
            "Twitter": f"https://twitter.com/search?q={clean_num}&src=typed_query",
            "Instagram": f"https://www.instagram.com/accounts/account_recovery/?phone_number={clean_num}",
            "LinkedIn": f"https://www.linkedin.com/pub/dir/?phone={clean_num}",
            "VK": f"https://vk.com/people/{clean_num}",
            "Telegram": f"https://t.me/{clean_num}",
            "WhatsApp": f"https://wa.me/{clean_num}",
            "Signal": f"https://signal.me/#p/{clean_num}",
            "TikTok": f"https://www.tiktok.com/search?q={clean_num}",
            "Snapchat": f"https://www.snapchat.com/add/{clean_num}"
        }
        
        return social_media
    except Exception as e:
        return {"error": f"No se pudo generar enlaces: {str(e)}"}

def check_carrier_info(number):
    """Información detallada de la operadora con base de datos local"""
    try:
        parsed_number = phonenumbers.parse(number, None)
        carrier_name = carrier.name_for_number(parsed_number, "en") or "Desconocida"
        country_code = phonenumbers.region_code_for_number(parsed_number)
        
        # Base de datos local de operadoras
        carriers_db = {
            "Movistar": {
                "países": ["ES", "AR", "CL", "PE", "CO", "EC", "UY", "VE"],
                "sitio": "movistar.{tld}",
                "tld": {"ES": "es", "AR": "com.ar", "CL": "cl", "PE": "pe", "CO": "co", "EC": "ec", "UY": "com.uy", "VE": "com.ve"},
                "tipo": ["Móvil", "Fijo", "Internet"]
            },
            "Vodafone": {
                "países": ["ES", "GB", "DE", "IT", "PT", "IE", "NL", "GR"],
                "sitio": "vodafone.{tld}",
                "tld": {"ES": "es", "GB": "co.uk", "DE": "de", "IT": "it", "PT": "pt", "IE": "ie", "NL": "nl", "GR": "gr"},
                "tipo": ["Móvil", "Fijo", "Internet"]
            },
            "Claro": {
                "países": ["BR", "MX", "AR", "CO", "CL", "PE", "EC", "DO", "PA", "NI", "GT", "SV", "HN", "CR"],
                "sitio": "claro{tld}",
                "tld": {"BR": ".com.br", "MX": ".com.mx", "AR": ".com.ar", "CO": ".com.co", "CL": ".cl", "PE": ".pe", "EC": ".com.ec"},
                "tipo": ["Móvil", "Fijo", "Internet", "TV"]
            },
            "T-Mobile": {
                "países": ["US", "DE", "PL", "CZ", "HU", "AT", "NL"],
                "sitio": "t-mobile.{tld}",
                "tld": {"US": "com", "DE": "de", "PL": "pl", "CZ": "cz", "HU": "hu", "AT": "at", "NL": "nl"},
                "tipo": ["Móvil", "Internet"]
            },
            "AT&T": {
                "países": ["US", "MX"],
                "sitio": "att.{tld}",
                "tld": {"US": "com", "MX": "com.mx"},
                "tipo": ["Móvil", "Fijo", "Internet", "TV"]
            },
            "Verizon": {
                "países": ["US"],
                "sitio": "verizon.com",
                "tipo": ["Móvil", "Fijo", "Internet", "TV"]
            },
            "Orange": {
                "países": ["ES", "FR", "PL", "BE", "RO", "SK", "MD"],
                "sitio": "orange.{tld}",
                "tld": {"ES": "es", "FR": "fr", "PL": "pl", "BE": "be", "RO": "ro", "SK": "sk", "MD": "md"},
                "tipo": ["Móvil", "Fijo", "Internet", "TV"]
            }
        }
        
        carrier_info = {"Operadora": carrier_name}
        
        # Buscar coincidencia en la base de datos
        for name, data in carriers_db.items():
            if name.lower() in carrier_name.lower():
                # Construir URL del sitio web
                tld = data.get("tld", {}).get(country_code, "com")
                sitio = data["sitio"].format(tld=tld)
                
                carrier_info.update({
                    "Sitio web oficial": f"https://www.{sitio}",
                    "Países de operación": data["países"],
                    "Servicios ofrecidos": data["tipo"],
                    "Identificada_en_BD": True
                })
                break
        else:
            carrier_info["Identificada_en_BD"] = False
        
        return carrier_info
    except Exception as e:
        return {"error": f"No se pudo obtener información: {str(e)}"}

def check_number_reputation(number):
    """Análisis de reputación mejorado con detección de patrones"""
    try:
        parsed = phonenumbers.parse(number, None)
        national_num = str(parsed.national_number)
        country_code = phonenumbers.region_code_for_number(parsed)
        
        # Patrones de números sospechosos
        suspicious_patterns = [
            r'(\d)\1{5,}',      # 6+ dígitos repetidos
            r'123456\d*',        # Secuencia ascendente
            r'654321\d*',        # Secuencia descendente
            r'(\d{3})\1',        # Patrones repetidos (ej: 123123)
            r'^0{5,}',           # Muchos ceros al inicio
            r'^1{5,}',           # Muchos unos al inicio
            r'^(\d)\d\1\d\1\d',  # Patrón alternante (ej: 121212)
            r'^555\d{4}',        # Números ficticios (US)
            r'^999\d{4}',        # Números ficticios (UK)
            r'^123123',          # Patrón obvio
            r'^321321',          # Patrón obvio inverso
            r'^(\d{2})\1\1',     # Repetición de pares (ej: 121212)
            r'^(\d)\1(\d)\2(\d)\3'  # Patrón AABBCC
        ]
        
        risk_factors = 0
        matched_patterns = []
        
        for pattern in suspicious_patterns:
            if re.search(pattern, national_num):
                risk_factors += 1
                matched_patterns.append(pattern)
        
        # Reglas específicas por país
        country_specific_risks = {
            "US": ["^555", "^800", "^900", "^456", "^411"],
            "GB": ["^999", "^555", "^4479", "^4480"],
            "ES": ["^900", "^901", "^902", "^803", "^806", "^807"],
            "MX": ["^900", "^800", "^555", "^123"]
        }
        
        if country_code in country_specific_risks:
            for pattern in country_specific_risks[country_code]:
                if re.search(pattern, national_num):
                    risk_factors += 2  # Más riesgo si coincide con patrones del país
                    matched_patterns.append(f"Específico_{country_code}:{pattern}")
        
        # Evaluar reputación basada en factores
        reputation = "Baja"
        if risk_factors > 3:
            reputation = "Muy Alta"
        elif risk_factors > 2:
            reputation = "Alta"
        elif risk_factors > 1:
            reputation = "Media"
        
        return {
            "Factores_de_riesgo": risk_factors,
            "Patrones_sospechosos": matched_patterns if matched_patterns else "Ninguno detectado",
            "Calificación_de_reputación": reputation,
            "Recomendación": "Extrema precaución" if risk_factors > 3 else 
                            "Precaución" if risk_factors > 1 else 
                            "Parece legítimo",
            "Notas": "Números con patrones repetitivos o secuenciales son comúnmente usados para spam/fraude" if risk_factors > 0 else ""
        }
    except Exception as e:
        return {"error": str(e)}

def check_phone_blacklists(number):
    """Verificación en listas negras públicas"""
    try:
        parsed = phonenumbers.parse(number, None)
        clean_num = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164).replace("+", "")
        national_num = str(parsed.national_number)
        
        blacklists = {
            "ShouldIAnswer": f"https://www.shouldianswer.com/phone/{clean_num}",
            "CallerCenter": f"https://callercenter.com/{clean_num}",
            "PhoneBook": f"https://www.phonebook.com/phone/{clean_num}",
            "SpamCalls": f"https://spamcalls.net/en/search?q={clean_num}",
            "Numspy": f"https://numspy.io/number/{clean_num}",
            "Tellows": f"https://www.tellows.es/num/{clean_num}",
            "Sync.me": f"https://sync.me/search/?number={clean_num}",
            "Truecaller": f"https://www.truecaller.com/search/{clean_num}"
        }
        
        return blacklists
    except Exception as e:
        return {"error": str(e)}

def check_phone_format_variations(number):
    """Genera todas las variaciones de formato posibles"""
    try:
        parsed = phonenumbers.parse(number, None)
        national_num = str(parsed.national_number)
        country_code = phonenumbers.region_code_for_number(parsed)
        
        variations = {
            "E164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
            "Internacional": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "Nacional": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
            "RFC3966": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.RFC3966),
            "Sin_formato": national_num,
            "Solo_código_de_área": get_area_code(parsed, country_code),
            "Solo_línea": get_line_number(parsed, country_code),
            "Sin_ceros": national_num.lstrip('0'),
            "Últimos_4_dígitos": national_num[-4:],
            "Últimos_7_dígitos": national_num[-7:] if len(national_num) >= 7 else national_num,
            "Con_guiones": re.sub(r'(\d{3})(\d{3})(\d{4})', r'\1-\2-\3', national_num) if len(national_num) == 10 else national_num,
            "Con_espacios": re.sub(r'(\d{3})(\d{3})(\d{4})', r'\1 \2 \3', national_num) if len(national_num) == 10 else national_num
        }
        
        return variations
    except Exception as e:
        return {"error": str(e)}

def save_to_file(number, data):
    """Guarda los resultados en formato JSON y texto con mejor formato"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_filename = f"reporte_{number}_{timestamp}.json"
    txt_filename = f"reporte_{number}_{timestamp}.txt"
    
    # Guardar en JSON
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    # Guardar en texto legible
    with open(txt_filename, 'w', encoding='utf-8') as f:
        f.write(f"╔{'═'*70}╗\n")
        f.write(f"║{'ANÁLISIS DE NÚMERO TELEFÓNICO':^70}║\n")
        f.write(f"╠{'═'*70}╣\n")
        f.write(f"║ Número: {number:<59}║\n")
        f.write(f"║ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<59}║\n")
        f.write(f"╚{'═'*70}╝\n\n")
        
        for section, content in data.items():
            f.write(f"■{' ' + section.upper() + ' ':{'■'}^70}\n\n")
            
            if isinstance(content, dict):
                for key, value in content.items():
                    if isinstance(value, dict):
                        f.write(f"  {key}:\n")
                        for subkey, subvalue in value.items():
                            f.write(f"    {subkey}: {subvalue}\n")
                    elif isinstance(value, list):
                        f.write(f"  {key}:\n")
                        for item in value:
                            f.write(f"    - {item}\n")
                    else:
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
            elif isinstance(content, list):
                for item in content:
                    f.write(f"- {item}\n")
                f.write("\n")
            else:
                f.write(f"{content}\n\n")
        
        f.write("\n" + "═"*70 + "\n")
        f.write("FIN DEL REPORTE\n")
    
    return txt_filename, json_filename

def parallel_check(number, functions):
    """Ejecuta verificaciones en paralelo con mejor manejo de errores"""
    results = {}
    priority_order = [
        "Información_básica",
        "Búsqueda_en_Google",
        "Información_de_operadora",
        "Reputación_del_número",
        "Redes_sociales",
        "Listas_negras",
        "Variaciones_de_formato"
    ]
    
    # Reordenar funciones según prioridad
    ordered_functions = {k: functions[k] for k in priority_order if k in functions}
    ordered_functions.update({k: functions[k] for k in functions if k not in priority_order})
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        
        # Ejecutar funciones prioritarias primero
        for name, func in ordered_functions.items():
            try:
                futures[executor.submit(func, number)] = name
                time.sleep(random.uniform(0.5, 1.5))  # Espaciar solicitudes
            except Exception as e:
                results[name] = {"error": f"Error al programar: {str(e)}"}
        
        # Procesar resultados a medida que completan
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"error": f"Error en ejecución: {str(e)}"}
    
    return results

def display_results(data, number):
    """Muestra los resultados de forma organizada"""
    clear_screen()
    print(f"""
╔{'═'*70}╗
║{'RESUMEN DE ANÁLISIS':^70}║
╠{'═'*70}╣
║ Número: {number:<59}║
║ Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<59}║
╚{'═'*70}╝
""")
    
    # Información básica
    basic = data.get("Información_básica", {})
    if not basic.get("error"):
        print(f"\n{' INFORMACIÓN BÁSICA ':=^70}")
        print(f"• País: {basic.get('País', 'Desconocido')}")
        print(f"• Operadora: {basic.get('Operadora', 'Desconocida')}")
        print(f"• Tipo: {basic.get('Tipo de número', 'Desconocido')}")
        print(f"• Zona horaria: {', '.join(basic.get('Zona horaria', []))}")
        print(f"• Formato local: {basic.get('Formato local', 'N/A')}")
    
    # Reputación
    reputation = data.get("Reputación_del_número", {})
    if not reputation.get("error"):
        print(f"\n{' REPUTACIÓN ':=^70}")
        print(f"• Calificación: {reputation.get('Calificación_de_reputación', 'Desconocida')}")
        print(f"• Factores de riesgo: {reputation.get('Factores_de_riesgo', 0)}")
        if reputation.get('Patrones_sospechosos') != "Ninguno detectado":
            print(f"• Patrones detectados: {len(reputation.get('Patrones_sospechosos', []))}")
        print(f"• Recomendación: {reputation.get('Recomendación', '')}")
    
    # Búsqueda en Google
    google = data.get("Búsqueda_en_Google", {})
    if not google.get("error"):
        print(f"\n{' BÚSQUEDA EN INTERNET ':=^70}")
        print(f"• Menciones encontradas: {google.get('Menciones', 0)}")
        if google.get("Enlaces_relacionados"):
            print(f"• Enlaces relevantes encontrados: {len(google['Enlaces_relacionados'])}")
    
    # Operadora
    carrier = data.get("Información_de_operadora", {})
    if not carrier.get("error"):
        print(f"\n{' INFORMACIÓN DE OPERADORA ':=^70}")
        print(f"• Nombre: {carrier.get('Operadora', 'Desconocida')}")
        if carrier.get('Sitio_web_oficial'):
            print(f"• Sitio web: {carrier['Sitio_web_oficial']}")
    
    # Advertencias
    if reputation.get("Calificación_de_reputación", "") in ["Alta", "Muy Alta"]:
        print(f"\n{'¡ADVERTENCIA!':!^70}")
        print("Este número muestra características sospechosas que podrían indicar:")
        print("- Número de spam/scam - Número virtual - Servicio premium costoso")
    
    print(f"\n{'═'*70}")
    print("Nota: Para detalles completos, consulte los archivos de reporte generados")

def main():
    clear_screen()
    print(f"""
╔{'═'*70}╗
║{'ANALIZADOR DE NÚMEROS TELEFÓNICOS (OSINT)':^70}║
╠{'═'*70}╣
║{'Versión optimizada - Sin APIs externas':^70}║
╚{'═'*70}╝
""")
    
    while True:
        number = input("\nIngrese el número telefónico (con código de país, ej: +34123456789) o 'q' para salir: ").strip()
        
        if number.lower() == 'q':
            break
            
        if not validate_phone_number(number):
            print("\n¡Número no válido! Por favor ingrese un número válido con código de país.\n")
            continue
            
        print("\nRecopilando información... Esto puede tomar unos minutos.\n")
        
        # Funciones de verificación
        check_functions = {
            "Información_básica": get_basic_info,
            "Búsqueda_en_Google": check_google_search,
            "Redes_sociales": check_social_media,
            "Información_de_operadora": check_carrier_info,
            "Reputación_del_número": check_number_reputation,
            "Listas_negras": check_phone_blacklists,
            "Variaciones_de_formato": check_phone_format_variations
        }
        
        # Ejecutar verificaciones
        data = parallel_check(number, check_functions)
        
        # Guardar resultados
        txt_file, json_file = save_to_file(number, data)
        
        # Mostrar resumen
        display_results(data, number)
        
        print(f"\nReportes guardados en:")
        print(f"- Formato texto: {txt_file}")
        print(f"- Formato JSON: {json_file}\n")

if __name__ == "__main__":
    main()
