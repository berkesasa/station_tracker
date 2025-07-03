# İETT Bot Web Scraping Güncellemesi

## 🚌 Yapılan Değişiklikler

### 1. Web Scraping Implementasyonu
- **BeautifulSoup** ile HTML parsing
- **Gerçek İETT verileri** için web scraping
- Mock data yerine **dinamik veri çekme**

### 2. Çoklu Veri Kaynağı Desteği
```python
# Öncelik sırası:
1. Web Scraping (İETT web sitesi)
2. API Endpoints (mobil, ana API)
3. Fallback Data (bilinen duraklar için)
```

### 3. Gelişmiş Hata Yönetimi
- **Telegram bot çakışması** çözümü
- **Webhook temizleme** işlemi
- **Alternatif başlatma** yöntemleri
- **Detaylı logging** sistemi

### 4. Yeni Fonksiyonlar

#### `scrape_station_info(station_code)`
- İETT web sitesinden veri çekme
- Modern browser headers kullanımı
- Timeout ve hata yönetimi

#### `parse_bus_times_from_html(soup, station_code)`
- HTML'den otobüs verilerini çıkarma
- JavaScript parsing
- Table/div yapılarını analiz

#### `extract_buses_from_js(js_content)`
- JavaScript içeriğinden JSON veri çıkarma
- Regex pattern matching
- Çoklu veri formatı desteği

#### `get_fallback_bus_data(station_code)`
- Bilinen duraklar için varsayılan veriler
- Gerçekçi zaman hesaplamaları
- Hata durumunda güvenli fallback

### 5. Bot Başlatma İyileştirmeleri

```python
# Telegram bot çakışması çözümü
await application.bot.delete_webhook(drop_pending_updates=True)

# Geliştirilmiş polling parametreleri
application.run_polling(
    allowed_updates=Update.ALL_TYPES,
    drop_pending_updates=True,
    poll_interval=1.0,
    timeout=20
)
```

### 6. URL Parsing Geliştirmeleri
- Durak kodları ve isimleri çıkarma
- URL decode işlemleri
- Hata toleransı

## 🔧 Teknik Detaylar

### Dependencies
```
python-telegram-bot==20.7
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
```

### Test Edilmiş Durak Kodları
- `127151` - Firuzköy Sapağı-Avcılar
- `322001` - İÜ Cerrahpaşa Avcılar Kampüsü

### İETT Web Sitesi Yapısı
- Modern JavaScript tabanlı sayfa
- AJAX ile yüklenen veriler
- Anti-bot korumaları
- Dinamik içerik yükleme

## 🚀 Deployment Notları

### Railway Platform
1. **Environment Variables**:
   - `BOT_TOKEN` - Telegram bot token'i

2. **Startup Process**:
   ```bash
   python main.py
   ```

3. **Webhook Temizleme**:
   - Her başlangıçta webhook otomatik temizlenir
   - Çakışma engellemesi

### Bilinen Limitasyonlar
1. **İETT Sistem Kapatma**: Gece 00:15'ten sonra servis kapatılıyor
2. **Rate Limiting**: Çok sık istek engellenebilir
3. **JavaScript Loading**: Bazı veriler AJAX ile yükleniyor
4. **Anti-Bot**: Cloudflare koruması olabilir

## 📊 Test Sonuçları

### Web Scraping Test
```bash
python test_scraping.py
```

### Beklenen Çıktı:
- HTTP 200 response
- HTML parsing başarılı
- JavaScript içerik tespit edildi
- CSS class'lar analiz edildi

## 🔍 Debug ve Monitoring

### Log Seviyeleri:
- `INFO`: Normal işlemler
- `WARNING`: Fallback kullanımı
- `ERROR`: Kritik hatalar
- `DEBUG`: Detaylı debugging

### Önemli Log Mesajları:
```
🚌 IETT request status: 200 for station 127151
✅ Web scraping başarılı: 3 otobüs bulundu
⚠️ Tüm yöntemler başarısız, fallback veri döndürülüyor
```

## 🛠️ Sorun Giderme

### 1. "Conflict: terminated by other getUpdates request"
**Çözüm**: Bot restart edildiğinde webhook otomatik temizlenir

### 2. "Durak bilgisi alınamadı"
**Nedenleri**:
- İETT sistemi kapalı (gece 00:15+)
- Rate limiting
- Network bağlantı sorunu

**Çözüm**: Fallback data otomatik olarak gösterilir

### 3. Yavaş Yanıt
**Nedenleri**:
- İETT web sitesi yavaş
- Çoklu API denemesi
- Network latency

**Optimizasyon**: Timeout değerleri ayarlandı (15s)

## 📈 Gelecek Geliştirmeler

1. **Caching**: Redis ile veri önbellekleme
2. **Async Scraping**: Asenkron web scraping
3. **Multiple Stations**: Çoklu durak desteği
4. **Real-time Updates**: Periyodik veri güncelleme
5. **Error Analytics**: Hata analizi ve raporlama

## 🤝 Katkıda Bulunma

Bot sürekli geliştirilmektedir. Öneriler:
1. Yeni durak kodları test etme
2. Hata raporları
3. Performance optimizasyonları
4. Yeni özellik önerileri

---
**Son Güncelleme**: 03.07.2025
**Versiyon**: 2.0 - Web Scraping Edition