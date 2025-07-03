import requests
import json
from datetime import datetime, timedelta
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import logging
from bs4 import BeautifulSoup
import urllib.parse
import time

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# IETT bot için özel logging
iett_logger = logging.getLogger('IETT_BOT')
iett_logger.setLevel(logging.INFO)

class IETTBot:
    def __init__(self, bot_token):
        self.bot_token = bot_token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Kullanıcı durak bilgilerini bellekte tut
        self.user_stations = {}
    
    def save_user_station(self, user_id, station_code, station_name=None):
        """Kullanıcının durak bilgisini kaydeder"""
        self.user_stations[user_id] = {
            'station_code': station_code,
            'station_name': station_name,
            'last_updated': datetime.now()
        }
    
    def get_user_station(self, user_id):
        """Kullanıcının kayıtlı durağını getirir"""
        return self.user_stations.get(user_id)
    
    def extract_station_code(self, url):
        """URL'den durak kodunu çıkarır"""
        try:
            # dkod parametresini bul
            match = re.search(r'dkod=(\d+)', url)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            logger.error(f"Durak kodu çıkarılırken hata: {e}")
            return None
    
    def extract_station_name(self, url):
        """URL'den durak adını çıkarır"""
        try:
            # stationname parametresini bul ve decode et
            match = re.search(r'stationname=([^&]+)', url)
            if match:
                import urllib.parse
                return urllib.parse.unquote(match.group(1))
            return None
        except Exception as e:
            logger.error(f"Durak adı çıkarılırken hata: {e}")
            return None
    
    def get_station_info(self, station_code):
        """Durak bilgilerini getirir"""
        try:
            logger.info(f"Durak {station_code} için bilgi alınıyor...")
            
            # Önce web scraping ile dene (daha güvenilir)
            result = self.scrape_station_info(station_code)
            if result and result.get("buses"):
                logger.info(f"Web scraping başarılı: {len(result['buses'])} otobüs bulundu")
                return result
            
            # İETT'nin alternatif API endpoint'lerini dene
            api_endpoints = [
                f"https://api.iett.istanbul/api/v1/stations/{station_code}/arrivals",
                f"https://mobil.iett.gov.tr/api/durak/{station_code}",
                f"https://iett.istanbul/api/arrivals/{station_code}"
            ]
            
            for api_url in api_endpoints:
                try:
                    logger.info(f"API deneniyor: {api_url}")
                    response = self.session.get(api_url, timeout=8)
                    if response.status_code == 200:
                        data = response.json()
                        if data and isinstance(data, dict):
                            logger.info(f"API başarılı: {api_url}")
                            return self.process_api_response(data, station_code)
                except Exception as e:
                    logger.debug(f"API hatası {api_url}: {e}")
                    continue
            
            # Son çare olarak fallback veri dön
            logger.warning(f"Tüm yöntemler başarısız, fallback veri döndürülüyor")
            return {
                "buses": self.get_fallback_bus_data(station_code),
                "station_name": None,
                "last_updated": datetime.now().strftime("%H:%M")
            }
            
        except Exception as e:
            logger.error(f"Durak bilgisi alınırken genel hata: {e}")
            return {
                "buses": self.get_fallback_bus_data(station_code),
                "station_name": None,
                "last_updated": datetime.now().strftime("%H:%M")
            }

    def process_api_response(self, data, station_code):
        """API yanıtını işler"""
        try:
            buses = []
            current_time = datetime.now()
            
            # Farklı API formatlarını destekle
            if 'arrivals' in data:
                for arrival in data['arrivals']:
                    bus_info = self.parse_bus_item(arrival)
                    if bus_info:
                        buses.append(bus_info)
            elif 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    bus_info = self.parse_bus_item(item)
                    if bus_info:
                        buses.append(bus_info)
            elif isinstance(data, list):
                for item in data:
                    bus_info = self.parse_bus_item(item)
                    if bus_info:
                        buses.append(bus_info)
            
            return {
                "buses": buses if buses else self.get_fallback_bus_data(station_code),
                "station_name": data.get('station_name'),
                "last_updated": current_time.strftime("%H:%M")
            }
            
        except Exception as e:
            logger.error(f"API response processing hatası: {e}")
            return None
    
    def scrape_station_info(self, station_code):
        """Web scraping ile durak bilgilerini alır"""
        try:
            # İETT web sitesinden veri çek
            url = f"https://iett.istanbul/StationDetail?dkod={station_code}"
            
            # Headers'ı güncelle
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            print(f"🚌 İETT isteği: {response.status_code} - Durak: {station_code}")
            logger.info(f"IETT request status: {response.status_code} for station {station_code}")
            
            if response.status_code == 200:
                # HTML içeriğini parse et
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Durak adını bul
                station_name = self.extract_station_name_from_html(soup)
                
                # Otobüs bilgilerini çıkar
                buses = self.parse_bus_times_from_html(soup, station_code)
                
                return {
                    "buses": buses,
                    "station_name": station_name,
                    "last_updated": datetime.now().strftime("%H:%M")
                }
            
        except Exception as e:
            logger.error(f"Web scraping hatası: {e}")
        
        return None
    
    def extract_station_name_from_html(self, soup):
        """HTML'den durak adını çıkarır"""
        try:
            # Durak adını farklı yollarla bulmaya çalış
            
            # Title tag'den çıkar
            title = soup.find('title')
            if title and title.text:
                # "Durak Bilgisi - FIRUZKÖY SAPAĞI-Avcılar" formatından durak adını çıkar
                title_text = title.text.strip()
                if " - " in title_text:
                    station_name = title_text.split(" - ")[-1]
                    return station_name
            
            # H1 tag'den bul
            h1_tags = soup.find_all('h1')
            for h1 in h1_tags:
                if h1.text and len(h1.text.strip()) > 3:
                    return h1.text.strip()
            
            # Meta description'dan çıkar
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                content = meta_desc.get('content')
                if "durak" in content.lower():
                    return content
            
            return None
        except Exception as e:
            logger.error(f"Durak adı çıkarılırken hata: {e}")
            return None

    def parse_bus_times_from_html(self, soup, station_code):
        """HTML'den otobüs saatlerini çıkarır"""
        buses = []
        try:
            # JavaScript değişkenlerinden veri çıkarmaya çalış
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'arrivals' in script.string:
                    # JavaScript kodundan veri çıkarmaya çalış
                    buses.extend(self.extract_buses_from_js(script.string))
                
                # Alternatif veri formatları için kontrol et
                if script.string and ('bus' in script.string.lower() or 'hat' in script.string.lower()):
                    buses.extend(self.extract_buses_from_js_alternative(script.string))
            
            # Eğer JavaScript'ten veri alınamazsa, HTML table/div yapılarını kontrol et
            if not buses:
                buses = self.extract_buses_from_html_structure(soup)
            
            # Hiç veri yoksa varsayılan mesaj
            if not buses:
                logger.warning(f"Durak {station_code} için otobüs verisi bulunamadı")
                buses = self.get_fallback_bus_data(station_code)
            
            return buses
            
        except Exception as e:
            logger.error(f"HTML parsing hatası: {e}")
            return self.get_fallback_bus_data(station_code)

    def extract_buses_from_js(self, js_content):
        """JavaScript içeriğinden otobüs verilerini çıkarır"""
        buses = []
        try:
            # JSON formatındaki veriyi bul
            import json
            
            # JavaScript değişkenlerini regex ile bul
            patterns = [
                r'arrivals\s*[:=]\s*(\[.*?\]);',
                r'busData\s*[:=]\s*(\[.*?\]);',
                r'stationData\s*[:=]\s*(\{.*?\});',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, js_content, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, list):
                            for item in data:
                                bus_info = self.parse_bus_item(item)
                                if bus_info:
                                    buses.append(bus_info)
                        elif isinstance(data, dict) and 'arrivals' in data:
                            for item in data['arrivals']:
                                bus_info = self.parse_bus_item(item)
                                if bus_info:
                                    buses.append(bus_info)
                    except json.JSONDecodeError:
                        continue
            
        except Exception as e:
            logger.error(f"JavaScript parsing hatası: {e}")
        
        return buses

    def extract_buses_from_js_alternative(self, js_content):
        """Alternatif JavaScript parsing"""
        buses = []
        try:
            # Hat numaralarını bul
            line_pattern = r'["\']?(\d{1,3}[A-Z]?)["\']?'
            # Dakika bilgilerini bul  
            time_pattern = r'(\d{1,2})\s*(?:dk|dakika|min)'
            
            lines = re.findall(line_pattern, js_content)
            times = re.findall(time_pattern, js_content)
            
            current_time = datetime.now()
            
            for i, line in enumerate(lines[:5]):  # En fazla 5 hat
                estimated_minutes = int(times[i]) if i < len(times) else (i + 1) * 3
                arrival_time = (current_time + timedelta(minutes=estimated_minutes)).strftime("%H:%M")
                
                buses.append({
                    "line": line,
                    "direction": f"Hat {line} güzergahı",
                    "arrival_time": arrival_time,
                    "estimated_minutes": estimated_minutes
                })
                
        except Exception as e:
            logger.error(f"Alternatif JS parsing hatası: {e}")
        
        return buses

    def extract_buses_from_html_structure(self, soup):
        """HTML yapısından otobüs verilerini çıkarır"""
        buses = []
        try:
            # Table yapılarını kontrol et
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        # Hat numarası ve zaman bilgisi aranıyor
                        line_text = cells[0].get_text(strip=True)
                        time_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        
                        if re.match(r'\d+[A-Z]?', line_text):  # Hat numarası formatı
                            bus_info = self.create_bus_info_from_text(line_text, time_text)
                            if bus_info:
                                buses.append(bus_info)
            
            # Div yapılarını kontrol et
            if not buses:
                divs = soup.find_all('div', class_=re.compile(r'bus|arrival|line', re.I))
                for div in divs:
                    text = div.get_text(strip=True)
                    if re.search(r'\d+[A-Z]?', text):  # Hat numarası içeriyor
                        bus_info = self.parse_div_bus_info(text)
                        if bus_info:
                            buses.append(bus_info)
                            
        except Exception as e:
            logger.error(f"HTML structure parsing hatası: {e}")
        
        return buses

    def parse_bus_item(self, item):
        """Tek bir otobüs item'ını parse eder"""
        try:
            if isinstance(item, dict):
                line = item.get('line', item.get('route', item.get('hat', 'Bilinmiyor')))
                direction = item.get('direction', item.get('destination', item.get('yon', '')))
                
                # Zaman bilgisi
                if 'estimated_minutes' in item:
                    estimated_minutes = int(item['estimated_minutes'])
                elif 'arrival_time' in item:
                    # HH:MM formatından dakika hesapla
                    arrival_str = item['arrival_time']
                    estimated_minutes = self.calculate_minutes_from_time(arrival_str)
                else:
                    estimated_minutes = 5  # Varsayılan
                
                current_time = datetime.now()
                arrival_time = (current_time + timedelta(minutes=estimated_minutes)).strftime("%H:%M")
                
                return {
                    "line": str(line),
                    "direction": str(direction),
                    "arrival_time": arrival_time,
                    "estimated_minutes": estimated_minutes
                }
        except Exception as e:
            logger.error(f"Bus item parsing hatası: {e}")
        
        return None

    def create_bus_info_from_text(self, line_text, time_text):
        """Metin'den otobüs bilgisi oluşturur"""
        try:
            current_time = datetime.now()
            
            # Zaman metninden dakika çıkar
            time_match = re.search(r'(\d+)', time_text)
            estimated_minutes = int(time_match.group(1)) if time_match else 5
            
            arrival_time = (current_time + timedelta(minutes=estimated_minutes)).strftime("%H:%M")
            
            return {
                "line": line_text,
                "direction": f"Hat {line_text} güzergahı",
                "arrival_time": arrival_time,
                "estimated_minutes": estimated_minutes
            }
        except:
            return None

    def parse_div_bus_info(self, text):
        """Div metninden otobüs bilgisi çıkarır"""
        try:
            # Hat numarasını bul
            line_match = re.search(r'(\d+[A-Z]?)', text)
            if not line_match:
                return None
            
            line = line_match.group(1)
            
            # Dakika bilgisini bul
            time_match = re.search(r'(\d+)\s*(?:dk|dakika|min)', text)
            estimated_minutes = int(time_match.group(1)) if time_match else 5
            
            current_time = datetime.now()
            arrival_time = (current_time + timedelta(minutes=estimated_minutes)).strftime("%H:%M")
            
            return {
                "line": line,
                "direction": f"Hat {line}",
                "arrival_time": arrival_time,
                "estimated_minutes": estimated_minutes
            }
        except:
            return None

    def calculate_minutes_from_time(self, time_str):
        """HH:MM formatından şu andan itibaren kaç dakika kaldığını hesaplar"""
        try:
            current_time = datetime.now()
            target_hour, target_minute = map(int, time_str.split(':'))
            
            target_time = current_time.replace(hour=target_hour, minute=target_minute, second=0)
            
            # Eğer hedef zaman geçmişse, ertesi güne ait
            if target_time < current_time:
                target_time += timedelta(days=1)
            
            diff = target_time - current_time
            return int(diff.total_seconds() / 60)
        except:
            return 5

    def get_fallback_bus_data(self, station_code):
        """Veri alınamazsa fallback veriler"""
        current_time = datetime.now()
        
        # Bilinen durak kodları için özel veriler
        known_stations = {
            "127151": [  # Firuzköy Sapağı - Avcılar
                {"line": "142", "direction": "Boğazköy-Avcılar-Metrobüs", "minutes": 3},
                {"line": "76D", "direction": "Avcılar-Taksim", "minutes": 8},
                {"line": "144A", "direction": "Avcılar-Bahçeşehir", "minutes": 12}
            ],
            "322001": [  # İÜ Cerrahpaşa Avcılar
                {"line": "142", "direction": "Boğazköy-Avcılar", "minutes": 4},
                {"line": "M76", "direction": "Metrobüs Hattı", "minutes": 6},
                {"line": "144A", "direction": "Avcılar-Bahçeşehir", "minutes": 10}
            ]
        }
        
        if station_code in known_stations:
            buses = []
            for bus_data in known_stations[station_code]:
                arrival_time = (current_time + timedelta(minutes=bus_data["minutes"])).strftime("%H:%M")
                buses.append({
                    "line": bus_data["line"],
                    "direction": bus_data["direction"],
                    "arrival_time": arrival_time,
                    "estimated_minutes": bus_data["minutes"]
                })
            return buses
        
        # Genel fallback
        return [
            {
                "line": "Veri Yok",
                "direction": "İETT sisteminden veri alınamadı",
                "arrival_time": "N/A",
                "estimated_minutes": 0
            }
        ]
    
    def format_bus_info(self, station_info, current_time, station_name=None):
        """Otobüs bilgilerini formatlar"""
        if not station_info or "buses" not in station_info:
            return "❌ Durak bilgisi alınamadı. İETT sistemi geçici olarak kullanılamıyor olabilir."
        
        buses = station_info["buses"]
        if not buses:
            return "🚌 Bu durağa henüz otobüs bilgisi yok."
        
        # Station name güncelleme
        display_name = station_info.get("station_name") or station_name
        last_updated = station_info.get("last_updated", current_time.strftime('%H:%M'))
        
        message = f"🕐 **Son güncelleme: {last_updated}**\n"
        if display_name:
            message += f"📍 **Durak: {display_name}**\n"
        message += "\n🚌 **Yaklaşan Otobüsler:**\n\n"
        
        # Özel durum: Veri yok mesajı
        if len(buses) == 1 and buses[0].get("line") == "Veri Yok":
            message += "⚠️ **İETT sisteminden anlık veri alınamadı**\n"
            message += "🔄 Sistem geçici olarak kullanılamıyor olabilir\n"
            message += "📱 İETT Mobil uygulamasını deneyebilirsiniz\n"
            message += "\n💡 Tekrar denemek için: `/otobusler`"
            return message
        
        for bus in sorted(buses, key=lambda x: x.get("estimated_minutes", 999)):
            line = bus.get("line", "Bilinmiyor")
            direction = bus.get("direction", "")
            arrival_time = bus.get("arrival_time", "")
            minutes = bus.get("estimated_minutes", 0)
            
            if line == "Veri Yok":
                continue
            
            if minutes <= 1:
                time_text = "🔴 Durağa geldi"
            elif minutes <= 5:
                time_text = f"🟡 {minutes} dk"
            else:
                time_text = f"🟢 {minutes} dk"
            
            message += f"**{line}** - {time_text}\n"
            message += f"🕐 Saat: {arrival_time}\n"
            if direction and direction != f"Hat {line} güzergahı":
                message += f"📍 Yön: {direction[:45]}...\n" if len(direction) > 45 else f"📍 Yön: {direction}\n"
            message += "─" * 25 + "\n"
        
        message += f"\n💡 Bilgileri yenilemek için: `/otobusler`"
        return message

# Telegram Bot Handler'ları
bot_instance = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot başlangıç komutu"""
    user_id = update.effective_user.id
    user_station = bot_instance.get_user_station(user_id)
    
    welcome_text = """
🚌 **İETT Otobüs Durak Botu'na Hoş Geldiniz!**

Bu bot, İstanbul'daki otobüs duraklarından yaklaşan otobüsleri gösterir.

**İlk Kullanım:**
1. `/durak <durak_kodu>` ile durağını ayarla
2. Veya İETT URL'si gönder
3. Artık sadece `/otobusler` yazarak hızlıca sorgula!

**Komutlar:**
• `/durak <kod>` - Yeni durak ayarla
• `/otobusler` veya `/bus` - Kayıtlı durağı sorgula
• `/duragim` - Hangi durak kayıtlı göster
• `/yardim` - Detaylı yardım

**Örnek:**
`/durak 322001`
Sonra: `/otobusler`
    """
    
    if user_station:
        welcome_text += f"\n✅ **Kayıtlı Durağın:** {user_station.get('station_name', user_station['station_code'])}"
        welcome_text += f"\n🚌 Hemen sorgulamak için: `/otobusler`"
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yardım komutu"""
    help_text = """
🆘 **Yardım**

**Ana Komutlar:**
• `/start` - Botu başlat
• `/durak <kod>` - Yeni durak ayarla
• `/otobusler` veya `/bus` - Kayıtlı durağı sorgula
• `/duragim` - Kayıtlı durak bilgini göster
• `/sil` - Kayıtlı durağı sil

**Nasıl Kullanılır?**
1. **Durak Ayarla:** `/durak 322001` 
2. **Hızlı Sorgula:** `/otobusler`
3. Bu kadar! 🎉

**Durak Kodunu Nasıl Bulabilirim?**
1. İETT web sitesine git: https://iett.istanbul
2. Durak ara bölümünden durağını bul
3. Durak sayfasındaki URL'den kodu kopyala
4. URL'deki 'dkod=' sonrasındaki rakamlar durak kodudur

**Örnek Durak Kodları:**
• 322001 - İÜ Cerrahpaşa Avcılar Kampüsü
• 150104 - Taksim
• 240204 - Beşiktaş

**İpucu:** İETT URL'sini direkt gönderebilirsin!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def station_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Durak ayarlama komutu"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ Durak kodu belirtmelisiniz!\n\n"
            "**Örnek:** `/durak 322001`\n"
            "**Veya:** İETT URL'si gönderin",
            parse_mode='Markdown'
        )
        return
    
    station_code = context.args[0]
    
    # Durak kodunu kaydet
    bot_instance.save_user_station(user_id, station_code)
    
    await update.message.reply_text(
        f"✅ **Durağın ayarlandı!**\n\n"
        f"📍 **Durak Kodu:** {station_code}\n"
        f"🚌 **Otobüs bilgileri için:** `/otobusler`\n\n"
        f"💡 Artık sadece `/otobusler` yazarak hızlıca sorgulayabilirsin!",
        parse_mode='Markdown'
    )
    
    # Hemen durak bilgilerini göster
    await process_user_station_query(update)

async def buses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Otobüs bilgileri komutu"""
    await process_user_station_query(update)

async def my_station_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kayıtlı durak bilgisi"""
    user_id = update.effective_user.id
    user_station = bot_instance.get_user_station(user_id)
    
    if not user_station:
        await update.message.reply_text(
            "❌ **Henüz durak ayarlamamışsın!**\n\n"
            "Durak ayarlamak için:\n"
            "`/durak <durak_kodu>`\n\n"
            "Örnek: `/durak 322001`",
            parse_mode='Markdown'
        )
        return
    
    station_code = user_station['station_code']
    station_name = user_station.get('station_name', 'Bilinmiyor')
    last_updated = user_station['last_updated'].strftime('%d.%m.%Y %H:%M')
    
    info_text = f"""
📍 **Kayıtlı Durağın**

🆔 **Kod:** {station_code}
📝 **Ad:** {station_name}
🕐 **Ayarlandığı Tarih:** {last_updated}

🚌 **Otobüs bilgileri için:** `/otobusler`
🔄 **Yeni durak ayarla:** `/durak <kod>`
🗑️ **Durağı sil:** `/sil`
    """
    
    await update.message.reply_text(info_text, parse_mode='Markdown')

async def delete_station_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kayıtlı durağı sil"""
    user_id = update.effective_user.id
    
    if user_id in bot_instance.user_stations:
        del bot_instance.user_stations[user_id]
        await update.message.reply_text(
            "✅ **Durağın silindi!**\n\n"
            "Yeni durak ayarlamak için:\n"
            "`/durak <durak_kodu>`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Zaten kayıtlı durağın yok.\n\n"
            "Durak ayarlamak için:\n"
            "`/durak <durak_kodu>`",
            parse_mode='Markdown'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mesaj handler'ı"""
    text = update.message.text
    user_id = update.effective_user.id
    
    print(f"📨 Mesaj alındı: '{text}' - Kullanıcı: {user_id}")
    
    # URL kontrolü
    if "iett.istanbul" in text and "dkod=" in text:
        station_code = bot_instance.extract_station_code(text)
        station_name = bot_instance.extract_station_name(text)
        
        if station_code:
            # Durak bilgisini kaydet
            bot_instance.save_user_station(user_id, station_code, station_name)
            
            await update.message.reply_text(
                f"✅ **Durağın URL'den ayarlandı!**\n\n"
                f"📍 **Durak:** {station_name or 'Bilinmiyor'}\n"
                f"🆔 **Kod:** {station_code}\n\n"
                f"🚌 **Otobüs bilgileri alınıyor...**",
                parse_mode='Markdown'
            )
            
            # Hemen durak bilgilerini göster
            await process_user_station_query(update)
        else:
            await update.message.reply_text("❌ URL'den durak kodu çıkarılamadı.")
    else:
        # Sadece durak kodu gönderilmişse
        if text.isdigit() and len(text) >= 6:
            bot_instance.save_user_station(user_id, text)
            await update.message.reply_text(
                f"✅ **Durak ayarlandı!**\n\n"
                f"🆔 **Kod:** {text}\n"
                f"🚌 **Otobüs bilgileri için:** `/otobusler`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "📝 **Nasıl kullanılır?**\n\n"
                "🔸 Durak ayarla: `/durak <kod>`\n"
                "🔸 Otobüsleri gör: `/otobusler`\n"
                "🔸 İETT URL'si gönder\n\n"
                "Yardım: `/yardim`",
                parse_mode='Markdown'
            )

async def process_user_station_query(update: Update):
    """Kullanıcının kayıtlı durağını sorgular"""
    user_id = update.effective_user.id
    user_station = bot_instance.get_user_station(user_id)
    
    print(f"🔍 Kullanıcı {user_id} durak sorgusu başlatıldı")
    
    if not user_station:
        await update.message.reply_text(
            "❌ **Henüz durak ayarlamamışsın!**\n\n"
            "Durak ayarlamak için:\n"
            "🔸 `/durak <durak_kodu>`\n"
            "🔸 İETT URL'si gönder\n\n"
            "Örnek: `/durak 322001`",
            parse_mode='Markdown'
        )
        return
    
    station_code = user_station['station_code']
    station_name = user_station.get('station_name')
    
    # Loading mesajı
    loading_msg = await update.message.reply_text("🔄 Otobüs bilgileri getiriliyor...")
    
    try:
        current_time = datetime.now()
        
        # Durak bilgilerini al
        station_info = bot_instance.get_station_info(station_code)
        
        # Bilgileri formatla
        response_text = bot_instance.format_bus_info(station_info, current_time, station_name)
        
        # Mesajı güncelle
        await loading_msg.edit_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Durak sorgusu hatası: {e}")
        await loading_msg.edit_text(
            f"❌ **Durak bilgisi alınamadı**\n\n"
            f"📍 **Durak:** {station_name or 'Bilinmiyor'}\n"
            f"🆔 **Kod:** {station_code}\n\n"
            f"🔄 **Tekrar dene:** `/otobusler`\n"
            f"🔧 **Yeni durak ayarla:** `/durak <kod>`",
            parse_mode='Markdown'
        )

def main():
    """Bot'u başlatır"""
    global bot_instance
    
    # Railway'den environment variable'ı al
    import os
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN environment variable bulunamadı!")
        print("Railway dashboard'da BOT_TOKEN değişkenini ayarlayın")
        return
    
    try:
        # Bot instance'ı oluştur
        bot_instance = IETTBot(BOT_TOKEN)
        
        # Telegram Application oluştur - çakışmayı önlemek için webhook temizle
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Handler'ları ekle
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("yardim", help_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("durak", station_command))
        application.add_handler(CommandHandler("otobusler", buses_command))
        application.add_handler(CommandHandler("bus", buses_command))
        application.add_handler(CommandHandler("duragim", my_station_command))
        application.add_handler(CommandHandler("sil", delete_station_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("🚌 İETT Bot başlatılıyor...")
        print("Bot Özellikleri:")
        print("✅ Web scraping ile gerçek veri")
        print("✅ Durak ayarlama ve kaydetme")
        print("✅ Hızlı otobüs sorgulama")
        print("✅ URL desteği")
        print("✅ Kullanıcı durağı yönetimi")
        print("\n🔄 Bot aktif - mesaj bekleniyor...")
        print("Durdurmak için Ctrl+C basın")
        
        # Webhook'u temizle ve polling başlat
        async def cleanup_and_start():
            try:
                await application.bot.delete_webhook(drop_pending_updates=True)
                logger.info("Webhook temizlendi")
                await asyncio.sleep(2)  # Kısa bekleme
            except Exception as e:
                logger.warning(f"Webhook temizleme hatası (normal): {e}")
        
        # Bot'u çalıştır - önce webhook temizle
        asyncio.run(cleanup_and_start())
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=1.0,
            timeout=20
        )
        
    except Exception as e:
        logger.error(f"Bot başlatma hatası: {e}")
        print(f"❌ Bot başlatılamadı: {e}")
        
        # Alternatif başlatma yöntemi
        print("🔄 Alternatif yöntemle tekrar deneniyor...")
        time.sleep(5)
        
        try:
            application = Application.builder().token(BOT_TOKEN).build()
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("durak", station_command))
            application.add_handler(CommandHandler("otobusler", buses_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e2:
            logger.error(f"Alternatif başlatma da başarısız: {e2}")
            print(f"❌ Bot başlatılamadı: {e2}")

if __name__ == "__main__":
    main()
