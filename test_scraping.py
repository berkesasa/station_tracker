#!/usr/bin/env python3
"""
İETT Web Scraping Test Script
Bu script, web scraping fonksiyonlarını test eder
"""

import requests
from bs4 import BeautifulSoup
import sys
import logging

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_iett_scraping(station_code):
    """İETT web scraping testi"""
    try:
        url = f"https://iett.istanbul/StationDetail?dkod={station_code}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        
        print(f"🔍 Test URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📏 Content Length: {len(response.text)} bytes")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Title kontrol et
            title = soup.find('title')
            if title:
                print(f"📰 Title: {title.text.strip()}")
            
            # Script taglerini kontrol et
            scripts = soup.find_all('script')
            print(f"📜 Script tag sayısı: {len(scripts)}")
            
            # JavaScript içeriğinde veri ara
            for i, script in enumerate(scripts[:10]):  # İlk 10 script
                if script.string and len(script.string) > 100:
                    content = script.string[:200]
                    print(f"📄 Script {i}: {content}...")
                    
                    # Bus/arrival anahtar kelimelerini ara
                    if any(keyword in script.string.lower() for keyword in ['bus', 'arrival', 'hat', 'otobüs', 'dk']):
                        print(f"🚌 Script {i} otobüs verisi içeriyor olabilir")
            
            # HTML yapısını kontrol et
            tables = soup.find_all('table')
            divs = soup.find_all('div')
            
            print(f"📊 HTML yapısı:")
            print(f"  - {len(tables)} table")
            print(f"  - {len(divs)} div")
            
            # Class isimlerini kontrol et
            classes = set()
            for element in soup.find_all(['div', 'table', 'span']):
                if element.get('class'):
                    classes.update(element.get('class'))
            
            bus_related_classes = [cls for cls in classes if any(keyword in cls.lower() for keyword in ['bus', 'arrival', 'time', 'schedule'])]
            if bus_related_classes:
                print(f"🚌 Otobüs ile ilgili CSS classes: {bus_related_classes}")
            
            return True
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test Hatası: {e}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("🚌 İETT Web Scraping Test Başlıyor...")
    
    # Test durak kodları
    test_stations = [
        "127151",  # Firuzköy Sapağı - Avcılar
        "322001",  # İÜ Cerrahpaşa Avcılar
        "150104",  # Test için başka bir durak
    ]
    
    for station_code in test_stations:
        print(f"\n{'='*50}")
        print(f"🧪 Test Station: {station_code}")
        print('='*50)
        
        success = test_iett_scraping(station_code)
        print(f"✅ Test başarılı: {success}" if success else "❌ Test başarısız")
    
    print(f"\n{'='*50}")
    print("🏁 Test tamamlandı!")

if __name__ == "__main__":
    main()