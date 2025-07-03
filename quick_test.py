#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import IETTBot, get_istanbul_time

async def test_new_apis():
    """Test the new API implementations"""
    print("🚀 Yeni API Implementasyonları Test Ediliyor...")
    print("=" * 60)
    
    # Dummy token ile bot oluştur (sadece API testleri için)
    bot = IETTBot("dummy_token")
    
    # Test station code
    station_code = "151434"
    
    print(f"🚏 Test Durağı: {station_code}")
    print(f"⏰ Test Zamanı: {get_istanbul_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: MobiIETT API
    print("🔥 Test 1: MobiIETT API v2")
    print("-" * 30)
    try:
        result = await bot.get_station_info_from_mobiiett(station_code)
        if result:
            print(f"✅ BAŞARILI!")
            print(f"📍 Durak: {result['station_name']}")
            print(f"🚌 Otobüs sayısı: {len(result['buses'])}")
            print(f"📊 Data source: {result['data_source']}")
            if result['buses']:
                for i, bus in enumerate(result['buses'][:3], 1):
                    print(f"   {i}. {bus['line']} - {bus['destination']} ({bus['estimated_minutes']} dk)")
        else:
            print(f"❌ BAŞARISIZ veya boş sonuç")
    except Exception as e:
        print(f"❌ HATA: {e}")
    
    print()
    
    # Test 2: GitHub Static Data
    print("📁 Test 2: GitHub Static Data")
    print("-" * 30)
    try:
        result = await bot.get_station_info_from_github(station_code)
        if result:
            print(f"✅ BAŞARILI!")
            print(f"📍 Durak: {result['station_name']}")
            print(f"🚌 Otobüs sayısı: {len(result['buses'])}")
            print(f"📊 Data source: {result['data_source']}")
            if result['buses']:
                for i, bus in enumerate(result['buses'][:3], 1):
                    print(f"   {i}. {bus['line']} - {bus['destination']} ({bus['estimated_minutes']} dk)")
        else:
            print(f"❌ BAŞARISIZ veya boş sonuç")
    except Exception as e:
        print(f"❌ HATA: {e}")
    
    print()
    
    # Test 3: Fallback Data
    print("🔄 Test 3: Fallback Data")
    print("-" * 30)
    try:
        result = await bot.get_station_info_fallback(station_code)
        if result:
            print(f"✅ BAŞARILI!")
            print(f"📍 Durak: {result['station_name']}")
            print(f"🚌 Otobüs sayısı: {len(result['buses'])}")
            print(f"📊 Data source: {result['data_source']}")
            if result['buses']:
                for i, bus in enumerate(result['buses'][:3], 1):
                    print(f"   {i}. {bus['line']} - {bus['destination']} ({bus['estimated_minutes']} dk)")
        else:
            print(f"❌ BAŞARISIZ veya boş sonuç")
    except Exception as e:
        print(f"❌ HATA: {e}")
    
    print()
    
    # Test 4: Multi-Strategy (ana method)
    print("🎯 Test 4: Multi-Strategy System")
    print("-" * 30)
    try:
        result = await bot.get_station_info(station_code)
        if result:
            print(f"✅ BAŞARILI!")
            print(f"📍 Durak: {result['station_name']}")
            print(f"🚌 Otobüs sayısı: {len(result['buses'])}")
            print(f"📊 Data source: {result['data_source']}")
            
            # Formatlanmış mesajı test et
            formatted_message = bot.format_bus_info(result)
            print("\n📝 Formatlanmış Mesaj:")
            print("-" * 40)
            print(formatted_message[:300] + "..." if len(formatted_message) > 300 else formatted_message)
            
        else:
            print(f"❌ BAŞARISIZ veya boş sonuç")
    except Exception as e:
        print(f"❌ HATA: {e}")
    
    print()
    print("=" * 60)
    print("🎉 Test tamamlandı!")

if __name__ == "__main__":
    asyncio.run(test_new_apis()) 