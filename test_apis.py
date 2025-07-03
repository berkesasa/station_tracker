#!/usr/bin/env python3
import requests
import json
from datetime import datetime
import pytz

ISTANBUL_TZ = pytz.timezone('Europe/Istanbul')

def get_istanbul_time():
    return datetime.now(ISTANBUL_TZ)

class APITester:
    def __init__(self):
        self.session = requests.Session()
        
    def test_mobiiett_api_v2(self, station_code="151434"):
        """Güncellenmiş MobiIETT API'yi test eder (GitHub'dan bulduğum bilgilerle)"""
        print(f"\n🔥 MobiIETT API v2 Test - Durak: {station_code}")
        
        try:
            # Gerçek client credentials (GitHub'da bulduğum)
            auth_url = "https://ntcapi.iett.istanbul/oauth2/v2/auth"
            auth_data = {
                'client_id': 'thAwizrcxoSgzWUzRRzhSyaiBQwQlOqA',
                'client_secret': 'jRUTfAItVHYctPULyQFjbzTyLFxHklykujPWXKqRntSKTLEr',
                'grant_type': 'client_credentials',
                'scope': 'service'
            }
            
            print("📡 OAuth token alınıyor...")
            token_response = self.session.post(auth_url, json=auth_data, timeout=10)
            
            print(f"📊 Auth Status: {token_response.status_code}")
            
            if token_response.status_code == 200:
                token_data = token_response.json()
                access_token = token_data.get('access_token')
                print(f"✅ Token alındı: {access_token[:20]}...")
                
                # Servis endpoint'i ile durak bilgilerini al
                service_url = "https://ntcapi.iett.istanbul/service"
                
                # Durak detayları için request
                service_data = {
                    "alias": "mainGetLine_basic_search",
                    "data": {
                        "HATYONETIM.HAT.HAT_KODU": f"%{station_code}%"
                    }
                }
                
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                print("🚌 Durak bilgileri alınıyor...")
                response = self.session.post(service_url, json=service_data, headers=headers, timeout=15)
                
                print(f"📊 Status: {response.status_code}")
                print(f"📄 Content-Type: {response.headers.get('content-type', 'N/A')}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ JSON alındı: {type(data)}")
                        print(f"📄 Response: {str(data)[:200]}...")
                        return True
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON Parse Error: {e}")
                        print(f"📄 Raw response: {response.text[:200]}...")
                        
                else:
                    print(f"❌ Service Error: {response.status_code}")
                    print(f"📄 Response: {response.text[:200]}...")
                    
            else:
                print(f"❌ Auth Error: {token_response.status_code}")
                print(f"📄 Response: {token_response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            
        return False
        
    def test_mobiiett_api_old(self, station_code="151434"):
        """Eski MobiIETT API'yi test eder"""
        print(f"\n🔥 MobiIETT API (Eski) Test - Durak: {station_code}")
        
        try:
            # Eski token endpoint
            token_url = "https://ntcapi.iett.istanbul/oauth/token"
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': 'mobil',
                'client_secret': 'mobil'
            }
            
            print("📡 Token alınıyor...")
            token_response = self.session.post(token_url, data=token_data, timeout=10)
            
            if token_response.status_code == 200:
                token_data = token_response.json()
                access_token = token_data.get('access_token')
                print(f"✅ Token alındı: {access_token[:20]}...")
                
                # Durak bilgilerini al
                api_url = f"https://ntcapi.iett.istanbul/api/duraks/{station_code}/arrivals"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/json',
                    'User-Agent': 'MobiIETT/1.0'
                }
                
                print("🚌 Durak bilgileri alınıyor...")
                response = self.session.get(api_url, headers=headers, timeout=15)
                
                print(f"📊 Status: {response.status_code}")
                print(f"📄 Content-Type: {response.headers.get('content-type', 'N/A')}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ JSON alındı: {type(data)}")
                        
                        if isinstance(data, dict):
                            arrivals = data.get('arrivals', [])
                            print(f"🚏 Bulunan varış: {len(arrivals)}")
                            
                            for i, arrival in enumerate(arrivals[:3]):
                                line = arrival.get('line', 'N/A')
                                direction = arrival.get('direction', 'N/A')
                                arrival_time = arrival.get('arrival_time', 'N/A')
                                print(f"   {i+1}. {line} - {direction} ({arrival_time})")
                                
                        return True
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON Parse Error: {e}")
                        print(f"📄 Raw response: {response.text[:200]}...")
                        
                else:
                    print(f"❌ API Error: {response.status_code}")
                    print(f"📄 Response: {response.text[:200]}...")
                    
            else:
                print(f"❌ Token Error: {token_response.status_code}")
                print(f"📄 Response: {token_response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            
        return False
    
    def test_ibb_open_data_api(self, station_code="151434"):
        """İBB Open Data API'yi test eder"""
        print(f"\n🏛️ İBB Open Data API Test - Durak: {station_code}")
        
        try:
            # DurakDetay metodunu test et
            url = "https://api.ibb.gov.tr/iett/ibb/ibb.asmx"
            
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <DurakDetay_GYY xmlns="http://tempuri.org/">
      <DurakKodu>{station_code}</DurakKodu>
    </DurakDetay_GYY>
  </soap:Body>
</soap:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': '"http://tempuri.org/DurakDetay_GYY"',
                'User-Agent': 'Mozilla/5.0 (compatible; IETT-Bot/1.0)'
            }
            
            print("📡 SOAP isteği gönderiliyor...")
            response = self.session.post(url, data=soap_body, headers=headers, timeout=15)
            
            print(f"📊 Status: {response.status_code}")
            print(f"📄 Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            if response.status_code == 200:
                print(f"✅ SOAP Response alındı")
                print(f"📄 Response length: {len(response.text)}")
                print(f"📄 First 300 chars: {response.text[:300]}...")
                
                # XML içinde JSON arar
                if '"' in response.text and '{' in response.text:
                    print("🔍 JSON aranıyor...")
                    # JSON extraction logic burada olur
                    
                return True
            else:
                print(f"❌ SOAP Error: {response.status_code}")
                print(f"📄 Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            
        return False
        
    def test_github_static_data(self):
        """GitHub'daki static İETT verilerini test eder"""
        print(f"\n📁 GitHub Static Data Test")
        
        try:
            # GitHub'dan durak verilerini al
            stations_url = "https://raw.githubusercontent.com/myikit/iett-data/main/stations.json"
            buses_url = "https://raw.githubusercontent.com/myikit/iett-data/main/buss.json"
            
            print("📡 Durak verileri alınıyor...")
            stations_response = self.session.get(stations_url, timeout=10)
            
            if stations_response.status_code == 200:
                stations_data = stations_response.json()
                print(f"✅ {len(stations_data)} durak verisi alındı")
                
                # İlk birkaç durağı göster
                for i, station in enumerate(stations_data[:3]):
                    name = station.get('name', 'N/A')
                    code = station.get('code', 'N/A')
                    print(f"   {i+1}. {name} - {code}")
                
                print("📡 Otobüs verileri alınıyor...")
                buses_response = self.session.get(buses_url, timeout=10)
                
                if buses_response.status_code == 200:
                    buses_data = buses_response.json()
                    print(f"✅ {len(buses_data)} otobüs verisi alındı")
                    
                    # İlk birkaç otobüsü göster
                    for i, bus in enumerate(buses_data[:3]):
                        route = bus.get('route', 'N/A')
                        direction = bus.get('direction', 'N/A')
                        print(f"   {i+1}. {route} - {direction}")
                    
                    return True
                else:
                    print(f"❌ Buses Error: {buses_response.status_code}")
            else:
                print(f"❌ Stations Error: {stations_response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            
        return False
    
    def test_web_scraping_fallback(self, station_code="151434"):
        """Web scraping fallback'i test eder"""
        print(f"\n🌐 Web Scraping Test - Durak: {station_code}")
        
        try:
            url = f"https://iett.istanbul/StationDetail?dkod={station_code}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            print("📡 HTML sayfası alınıyor...")
            response = self.session.get(url, headers=headers, timeout=15)
            
            print(f"📊 Status: {response.status_code}")
            print(f"📄 Content-Type: {response.headers.get('content-type', 'N/A')}")
            print(f"📄 Page length: {len(response.text)}")
            
            if response.status_code == 200:
                # İçerikte JavaScript kontrolü
                has_js = 'javascript' in response.text.lower()
                has_line_list = 'line-list' in response.text
                has_line_item = 'line-item' in response.text
                
                print(f"🔍 JavaScript: {'✓' if has_js else '✗'}")
                print(f"🔍 line-list div: {'✓' if has_line_list else '✗'}")
                print(f"🔍 line-item div: {'✓' if has_line_item else '✗'}")
                
                # Sayfa başlığını kontrol et
                if '<title>' in response.text:
                    title_start = response.text.find('<title>') + 7
                    title_end = response.text.find('</title>', title_start)
                    if title_end > title_start:
                        title = response.text[title_start:title_end]
                        print(f"📄 Page title: {title}")
                
                return True
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            
        return False

def main():
    print("🚀 İETT API Test Suite v2")
    print("=" * 60)
    
    tester = APITester()
    
    # Test durağı: 151434 (Avcılar Metrobüs)
    test_station = "151434"
    
    print(f"⏰ Test Zamanı: {get_istanbul_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🚏 Test Durağı: {test_station}")
    
    # Test 1: Güncellenmiş MobiIETT API
    mobiiett_v2_success = tester.test_mobiiett_api_v2(test_station)
    
    # Test 2: Eski MobiIETT API (fallback)
    mobiiett_old_success = tester.test_mobiiett_api_old(test_station)
    
    # Test 3: GitHub Static Data
    github_success = tester.test_github_static_data()
    
    # Test 4: İBB Open Data API
    ibb_success = tester.test_ibb_open_data_api(test_station)
    
    # Test 5: Web Scraping Fallback
    scraping_success = tester.test_web_scraping_fallback(test_station)
    
    # Sonuçlar
    print("\n" + "=" * 60)
    print("📋 TEST SONUÇLARI")
    print("=" * 60)
    print(f"🔥 MobiIETT API v2: {'✅ BAŞARILI' if mobiiett_v2_success else '❌ BAŞARISIZ'}")
    print(f"🔄 MobiIETT API (Eski): {'✅ BAŞARILI' if mobiiett_old_success else '❌ BAŞARISIZ'}")
    print(f"📁 GitHub Static Data: {'✅ BAŞARILI' if github_success else '❌ BAŞARISIZ'}")
    print(f"🏛️ İBB Open Data API: {'✅ BAŞARILI' if ibb_success else '❌ BAŞARISIZ'}")
    print(f"🌐 Web Scraping: {'✅ BAŞARILI' if scraping_success else '❌ BAŞARISIZ'}")
    
    # Öneri sistemi
    if mobiiett_v2_success:
        print("\n🎉 MobiIETT API v2 çalışıyor! Bu en iyi seçenek.")
    elif mobiiett_old_success:
        print("\n🎉 Eski MobiIETT API çalışıyor! Bu iyi bir alternatif.")
    elif github_success:
        print("\n📊 GitHub static data çalışıyor! Fallback olarak kullanılabilir.")
    elif ibb_success:
        print("\n🏛️ İBB API çalışıyor! Bu da iyi bir alternatif.")
    elif scraping_success:
        print("\n⚠️ Sadece web scraping çalışıyor. JavaScript problemi var.")
    else:
        print("\n😞 Hiçbir API çalışmıyor. Hardcoded fallback data kullanılacak.")

if __name__ == "__main__":
    main() 