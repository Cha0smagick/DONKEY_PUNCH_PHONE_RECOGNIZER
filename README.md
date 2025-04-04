# DONKEY PUNCH OSINT Tool

Una herramienta avanzada de análisis de números telefónicos para investigación OSINT que recopila información detallada sobre cualquier número de teléfono válido.

## Características principales

- ✅ **Información básica del número**: País, operadora, zona horaria, tipo de número
- 🔍 **Búsqueda en Google**: Encuentra menciones públicas del número
- 📱 **Redes sociales**: Genera enlaces de búsqueda en plataformas sociales
- 🔓 **Verificación de filtraciones**: Comprueba si el número aparece en brechas de datos
- ⚠️ **Reputación**: Detecta reportes de spam/scam
- 📞 **Servicios de mensajería**: Enlaces directos a WhatsApp/Telegram
- 📚 **Directorios telefónicos**: Acceso rápido a páginas blancas y directorios
- 📊 **Variaciones de formato**: Diferentes formatos del mismo número
- 🖥️ **Información técnica**: Datos de operadora y registro de dominio

## Requisitos

- Python 3.7+
- Módulos Python:

pip install requests phonenumbers beautifulsoup4 python-whois dnspython

## Instalación

1. Clona el repositorio:
 ```bash
 git clone https://github.com/tu-usuario/phone-osint-tool.git
 cd phone-osint-tool
Instala las dependencias:

bash

pip install -r requirements.txt

Ejecuta la herramienta:

python phone_osint.py
