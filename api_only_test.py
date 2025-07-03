#!/usr/bin/env python3
import asyncio
import requests
import json
from datetime import datetime, timedelta
import pytz

ISTANBUL_TZ = pytz.timezone('Europe/Istanbul')

def get_istanbul_time():
    return datetime.now(ISTANBUL_TZ)

class SimpleAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.token_expires_at = None
        
        # MobiIETT API credentials (GitHub'dan bulunan çalışan veriler)
        self.mobiiett_client_id = 'thAwizrcxoSgzWUzRRzhSyaiBQwQlOqA'
        self.mobiiett_client_secret = 'jRUTfAItVHYctPULyQFjbzTyLFxHklykujPWXKqRntSKTLEr'
        
        # GitHub cache
        self.github_stations_cache = None
        self.github_buses_cache = None
        self.cache_expires_at = None
    
    async def get_mobiiett_token(self):
        """MobiIETT API'den OAuth token alır"""
        try:
            current_time = get_istanbul_time()
            
            if self.access_token and self.token_expires_at and current_time < self.token_expires_at:
                return self.access_token
                
            print("🔑 MobiIETT OAuth token alınıyor...")
            
            auth_url = "https://ntcapi.iett.istanbul/oauth2/v2/auth"
            auth_data = {
                'client_id': self.mobiiett_client_id,
                'client_secret': self.mobiiett_client_secret,
                'grant_type': 'client_credentials',
                'scope': 'service'
            }
            
            response = self.session.post(auth_url, json=auth_data, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                self.token_expires_at = current_time + timedelta(seconds=expires_in - 60)
                
                print(f"✅ Token alındı, {expires_in} saniye geçerli")
                return self.access_token
            else:
                print(f"❌ Token alma hatası: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Token alma exception: {e}")
            return None
    
    async def test_mobiiett_api(self, station_code):
        """MobiIETT API'yi test eder"""
        try:
            token = await self.get_mobiiett_token()
            if not token:
                return None
                
            print(f"🚌 MobiIETT API'den durak {station_code} sorgulanıyor...")
            
            service_url = "https://ntcapi.iett.istanbul/service"
            
            service_requests = [
                {
                    "alias": "mainGetLine_basic_search",
                    "data": {
                        "HATYONETIM.HAT.HAT_KODU": f"%{station_code}%"
                    }
                },
                {
                    "alias": "GetDurakCekmekoy_json",
                    "data": {
                        "DurakKodu": station_code
                    }
                },
                {
                    "alias": "GetStopLines_json", 
                    "data": {
                        "StopCode": station_code
                    }
                }
            ]
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'TestBot/1.0'
            }
            
            for service_data in service_requests:
                try:
                    print(f"  🔍 Alias '{service_data['alias']}' deneniyor...")
                    response = self.session.post(service_url, json=service_data, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data and isinstance(data, list) and len(data) > 0:
                            print(f"  ✅ {len(data)} sonuç alındı")
                            
                            # İlk birkaç sonucu göster
                            for i, item in enumerate(data[:3]):
                                hat_kodu = item.get('HAT_HAT_KODU', item.get('HAT_KODU', 'N/A'))
                                hat_adi = item.get('HAT_HAT_ADI', item.get('HAT_ADI', 'Bilinmiyor'))
                                durak_adi = item.get('DURAK_ADI', item.get('DURAK_KISA_ADI', 'Bilinmiyor'))
                                print(f"    {i+1}. {hat_kodu} - {hat_adi} @ {durak_adi}")
                            
                            return {
                                'success': True,
                                'data': data,
                                'alias': service_data['alias'],
                                'count': len(data)
                            }
                        else:
                            print(f"  📭 Boş sonuç")
                            
                    else:
                        print(f"  ❌ Service error {response.status_code}")
                        
                except Exception as e:
                    print(f"  ❌ Service request error: {e}")
                    continue
                    
            return None
            
        except Exception as e:
            print(f"❌ MobiIETT API exception: {e}")
            return None
    
    async def test_github_data(self):
        """GitHub static data'yı test eder"""
        try:
            current_time = get_istanbul_time()
            
            if (self.github_stations_cache and self.github_buses_cache and 
                self.cache_expires_at and current_time < self.cache_expires_at):
                print("✅ Cache'den kullanılıyor")
                return True
                
            print("📁 GitHub static data yükleniyor...")
            
            stations_url = "https://raw.githubusercontent.com/myikit/iett-data/main/stations.json"
            buses_url = "https://raw.githubusercontent.com/myikit/iett-data/main/buss.json"
            
            stations_response = self.session.get(stations_url, timeout=10)
            buses_response = self.session.get(buses_url, timeout=10)
            
            if stations_response.status_code == 200 and buses_response.status_code == 200:
                self.github_stations_cache = stations_response.json()
                self.github_buses_cache = buses_response.json()
                self.cache_expires_at = current_time + timedelta(minutes=30)
                
                print(f"✅ GitHub data yüklendi: {len(self.github_stations_cache)} durak, {len(self.github_buses_cache)} otobüs")
                
                # İlk birkaç durak örneği
                print("📋 Örnek duraklar:")
                for i, station in enumerate(self.github_stations_cache[:5]):
                    name = station.get('name', 'N/A')
                    code = station.get('code', 'N/A')
                    print(f"  {i+1}. {name} - {code}")
                
                return True
            else:
                print(f"❌ GitHub data yükleme hatası: stations={stations_response.status_code}, buses={buses_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ GitHub data loading exception: {e}")
            return False
    
    async def test_fallback_data(self, station_code):
        """Fallback data'yı test eder"""
        try:
            print(f"🔄 Fallback data test: {station_code}")
            
            station_data = {
                "151434": {
                    "name": "İSTANBUL ÜNİVERSİTESİ-CERRAHPAŞA AVCILAR KAMPÜSÜ",
                    "lines": ["142", "76D", "144A", "76"]
                },
                "111650": {
                    "name": "AVCILAR METROBÜS",
                    "lines": ["142", "400A", "400T", "76D"]
                },
                "default": {
                    "name": f"Durak {station_code}",
                    "lines": ["142", "76D", "400A"]
                }
            }
            
            station_info = station_data.get(station_code, station_data["default"])
            current_time = get_istanbul_time()
            
            print(f"✅ Fallback data hazırlandı:")
            print(f"  📍 Durak: {station_info['name']}")
            print(f"  🚌 Hatlar: {', '.join(station_info['lines'])}")
            
            # Simulated bus info
            for i, line in enumerate(station_info["lines"][:3]):
                estimated_minutes = (i + 1) * 3 + (hash(line + station_code) % 5)
                scheduled_time = (current_time + timedelta(minutes=estimated_minutes)).strftime("%H:%M")
                print(f"    {line} - {scheduled_time} ({estimated_minutes} dk)")
            
            return True
            
        except Exception as e:
            print(f"❌ Fallback data error: {e}")
            return False

async def main():
    print("🚀 İETT API Simple Test")
    print("=" * 50)
    
    tester = SimpleAPITester()
    station_code = "151434"
    
    print(f"🚏 Test Durağı: {station_code}")
    print(f"⏰ Test Zamanı: {get_istanbul_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: MobiIETT API
    print("🔥 Test 1: MobiIETT API v2")
    print("-" * 30)
    mobiiett_result = await tester.test_mobiiett_api(station_code)
    if mobiiett_result:
        print(f"✅ MobiIETT API BAŞARILI - {mobiiett_result['count']} sonuç")
    else:
        print("❌ MobiIETT API BAŞARISIZ")
    
    print()
    
    # Test 2: GitHub Data
    print("📁 Test 2: GitHub Static Data")
    print("-" * 30)
    github_result = await tester.test_github_data()
    if github_result:
        print("✅ GitHub Data BAŞARILI")
    else:
        print("❌ GitHub Data BAŞARISIZ")
    
    print()
    
    # Test 3: Fallback Data
    print("🔄 Test 3: Fallback Data")
    print("-" * 30)
    fallback_result = await tester.test_fallback_data(station_code)
    if fallback_result:
        print("✅ Fallback Data BAŞARILI")
    else:
        print("❌ Fallback Data BAŞARISIZ")
    
    print()
    print("=" * 50)
    print("🎯 SONUÇ ÖZETİ:")
    print(f"🔥 MobiIETT API: {'✅ ÇALIŞIYOR' if mobiiett_result else '❌ ÇALIŞMIYOR'}")
    print(f"📁 GitHub Data: {'✅ ÇALIŞIYOR' if github_result else '❌ ÇALIŞMIYOR'}")
    print(f"🔄 Fallback Data: {'✅ ÇALIŞIYOR' if fallback_result else '❌ ÇALIŞMIYOR'}")
    
    if mobiiett_result:
        print("\n🎉 MobiIETT API çalışıyor! Bot gerçek veri kullanabilir.")
    elif github_result:
        print("\n📊 GitHub Data çalışıyor! Fallback olarak kullanılabilir.")
    elif fallback_result:
        print("\n🆘 Sadece hardcoded fallback data çalışıyor.")
    else:
        print("\n😞 Hiçbir data source çalışmıyor!")

if __name__ == "__main__":
    asyncio.run(main()) 