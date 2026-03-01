# GoalPredict Pro — Ürün Gereksinimleri Dokümanı (PRD)

**Doküman Versiyonu:** 1.0
**Son Güncelleme:** 1 Mart 2026
**Durum:** Taslak - Geliştirme Öncesi
**Proje Yöneticisi:** Product Team
**Hedef Kitle:** Geliştirme Ekibi, Stakeholderlar

---

## 1. Proje Kimliği

### 1.1 Proje Adı
**GoalPredict Pro** — Futbol Maç Skor Tahmin ve Analiz Platformu

### 1.2 Proje Vizyonu
Türkiye'nin önde gelen futbol tahmin platformu olarak, yarı-profesyonel bahisçilere, spor medyası profesyonellerine ve analiz ekiplerine kurumsal kalitede, şeffaf ve gerçek-zamanlı tahmin araçları sunmak. Platform, 4-agent orkestrasyon sistemi ile tahmin sürecini tamamen görünür kılarak, kullanıcıların "neden" sorusuna bilimsel cevaplar almasını sağlar.

### 1.3 Tek Cümle Değer Önerisi
Veri kaynaklarını entegre eden, şeffaf ML modelleriyle skor tahmini üreten ve bahis piyasası ile karşılaştırmalı "edge" analizi sunan, tek noktalı profesyonel futbol analiz platformu.

### 1.4 Versiyon Yol Haritası
| Versiyon | Kod Adı | Çıkış Tarihi | Kapsam |
|----------|---------|--------------|--------|
| v1.0 | MVP | Haziran 2026 | Temel tahmin, veri entegrasyonu, auth, ödeme |
| v2.0 | Live | Aralık 2026 | Real-time agent, self-learning, betting edge |
| v3.0 | Enterprise | Haziran 2027 | API, mobil app, multi-lig, simülasyon |

---

## 2. Problem Tanımı

### 2.1 Pazar Boşluğu
Futbol tahmin pazarı, farklı ihtiyaçlara yanıt veren çözümler sunmakta yetersiz kalmaktadır. Ücretsiz platformlar basit istatistiklerle sınırlı kalırken, kurumsal çözümler Opta ve StatsBomb gibi servisler yıllık 20.000 doların üzerinde maliyetle sadece ham veri sağlamaktadır. Kara kutu ML modelleri ise tahminin arkasındaki mantığı açıklayamamakta ve kullanıcı güvenini zedelemektedir. Bu durum, profesyonel düzeyde analiz arayan kullanıcıları 5-10 farklı platform arasında gezinmek zorunda bırakmaktadır.

### 2.2 Kullanıcı Problemleri

**Problem 1 — Veri Parçalanması:** Kullanıcılar xG verileri için Understat'a, kadro değerleri için Transfermarkt'a, sakatlık bilgileri için farklı sitelere gitmek zorunda kalıyor. Bu durum, tek bir maç analizi için ortalama 45-60 dakika harcanmasına neden oluyor ve veriler arasında tutarlılık sağlanamıyor.

**Problem 2 — Model Şeffaflığı Eksikliği:** Mevcut tahmin sistemleri "GS kazanacak" diyor ama nedenini açıklayamıyor. Kullanıcılar, modelin hangi verilere dayanarak bu sonuca ulaştığını göremiyor ve bu durum öğrenme ile güven inşasını engelliyor.

**Problem 3 — Statik Tahminler:** Maç öncesi oluşturulan tahminler, sakatlık açıklamaları, hava durumu değişiklikleri veya taktiksel haberlere rağmen güncellenmiyor. Bir forvetin maç öncesi sakatlanması tahmine yansımıyor.

**Problem 4 — Bahis Değeri Analizi Yokluğu:** Kullanıcılar, model tahminlerinin piyasa oranlarıyla karşılaştırmasını yapamıyor. "Bu bahiste gerçekten değer var mı?" sorusuna cevap veren bir sistem bulunmuyor.

**Problem 5 — Manuel Model Yönetimi:** Mevcut modeller sezon sonunda manuel olarak yeniden eğitiliyor. Sezon içi performans takibi ve otomatik kalibrasyon mekanizması eksik.

### 2.3 Problem Etki Matrisi

| Problem | Kullanıcı Etkisi | Sıklık | Çözüm Olmazsa |
|---------|------------------|--------|---------------|
| Veri parçalanması | Analiz süresi uzuyor, tutarsız veri | Her maç öncesi | Kullanıcı kaybı, düşük NPS |
| Şeffaflık eksikliği | Güven kaybı, öğrenememe | Her tahminde | Premium segment kaybı |
| Statik tahminler | Hatalı kararlar, kayıp bahisler | Haftada 2-3 kez | Finansal kayıp, itibar zararı |
| Değer analizi yokluğu | Fırsat kaçırma | Her bahis kararında | Düşüş ROI, kullanıcı terk |
| Manuel model yönetimi | Eskiyen tahminler | Sezon boyunca | Rekabet gücü kaybı |

---

## 3. Hedef Kullanıcılar ve Personas

### 3.1 Birincil Personas (MVP Hedefi)

**Persona 1: Yarı-Profesyonel Bahisçi — "Emre, 34, İstanbul"**

Emre, tam zamanlı bir bahisçi değil ama aylık 2.000-5.000 TL arasında bahis geliri elde ediyor. Haftada 3-4 maç analiz ediyor ve kararlarını veriye dayandırmak istiyor. Şu an Excel'de kendi analizlerini tutuyor ve 5-6 farklı siteden veri topluyor. Maç başına 30-45 dakika harcıyor ve bu süreyi 10 dakikaya indirmek istiyor. Bahis yaparken en çok "value bet" kavramına önem veriyor — piyasanın yanlış fiyatlandırdığı fırsatları arıyor. Aylık 100-200 dolar ödemeye hazır. Başarı metriği olarak ROI (Return on Investment) kullanıyor.

**Temel İhtiyaçları:** Hızlı ve güvenilir tahmin, betting edge analizi, model şeffaflığı, mobil erişim

**Kullanım Senaryosu:** Cumartesi sabahı kahvesini içerken GoalPredict'e giriyor, bugünün maçlarını görüyor, GS-FB derbisini seçiyor. Modelin %62 GS galibiyeti tahmin ettiğini, piyasanın %57 verdiğini görüyor. Edge analizini kontrol ediyor, önerilen stake'i not alıyor. Raporu PDF olarak indiriyor ve bahis stratejisini belirliyor.

---

**Persona 2: Spor Medyası Analisti — "Zeynep, 28, Ankara"**

Zeynep, bir spor haber sitesinde analist olarak çalışıyor. Haftada 5-10 maç için ön yazı hazırlıyor ve okuyuculara derinlemesine analiz sunmak istiyor. Kaynak olarak StatsBomb ve Opta verilerini kullanıyor ama bu verilere erişim için yüksek lisans ücreti ödüyor. İçerik üretirken "xG", "PPDA", "progressive passes" gibi ileri düzey metrikleri kullanıyor ama bunları okuyucular için anlaşılır hale getirmek zor oluyor. Aylık 200-400 dolar bütçe ayırabilir. Başarı metriği olarak sayfa görüntüleme ve okuyucu yorumları.

**Temel İhtiyaçları:** Şeffaf veri kaynakları, görselleştirme araçları, rapor indirme, çoklu lig desteği

**Kullanım Senaryosu:** Maç gecesi analiz yazısı yazacak. GoalPredict'ten GS-FB maçının detaylı raporunu indiriyor. xG karşılaştırması, PPDA metrikleri ve oyuncu bazlı performans verilerini kullanarak zengin bir analiz hazırlıyor. Raporun "Agent Pipeline" bölümünden metodoloji kısmını alıntılayarak yazısına ekliyor.

---

**Persona 3: Amatör Teknik Direktör — "Hakan, 42, İzmir"**

Hakan, bölgesel ligde bir takımı çalıştırıyor. Maç analizleri için profesyonel araçlara erişimi yok ama rakiplerini analiz etmek istiyor. Haftada 2-3 maç videosunu izliyor ve istatistikleri manuel not alıyor. Rakiplerin güçlü ve zayıf yönlerini anlamak, taktik kararlarını desteklemek istiyor. Aylık 50-100 dolar ödemeye hazır. Başarı metriği olarak takımının lig sıralaması ve puan ortalaması.

**Temel İhtiyaçları:** Basit arayüz, taktiksel metrikler, karşılaştırma raporları, düşük maliyet

**Kullanım Senaryosu:** Önümüzdeki haftaki rakibi analiz etmek istiyor. GoalPredict'ten rakip takımın son 5 maçının xG, PPDA ve form değerlerini görüyor. Rakip takımın savunma zaaflarını tespit ediyor ve antrenman planını buna göre şekillendiriyor.

---

### 3.2 İkincil Personas (v2/v3 Hedefi)

**Persona 4: Fantasy Premier League Oyuncuları — "Mert, 26, Londra"**

Mert, FPL'de her sezon 2.000.000 oyuncu arasında ilk 50.000'e girmeyi hedefliyor. Oyuncu seçimlerinde xG, xA ve fixture difficulty rating kullanıyor. Haftada 5-10 saat FPL araştırmasına ayırıyor. Ücretsiz tier'dan başlamak istiyor, premium özellikler için ödemeye açık. Başarı metriği olarak overall rank.

**Persona 5: Bahis Startup'ı — "BetTech Solutions, Londra"**

BetTech, yeni bir bahis platformu kuruyor ve oran hesaplama için ML modeli arıyor. API entegrasyonu, yüksek güvenilirlik ve SLA garantisi istiyor. Aylık 2.000-10.000 dolar bütçe ayırabilir. Başarı metriği olarak uptime, yanıt süresi ve model doğruluğu.

---

### 3.3 Kullanıcı Segmentasyonu ve Gelir Potansiyeli

| Segment | Hedef Sayı (Yıl 1) | ARPU | Yıllık Gelir Potansiyeli |
|---------|--------------------|------|--------------------------|
| Yarı-profesyonel bahisçiler (TR) | 500 | $120/yıl | $60.000 |
| Spor medyası analistleri (TR) | 100 | $240/yıl | $24.000 |
| Amatör teknik direktörler (TR) | 300 | $60/yıl | $18.000 |
| Uluslararası kullanıcılar (v2) | 200 | $180/yıl | $36.000 |
| Kurumsal API müşterileri (v3) | 5 | $6.000/yıl | $30.000 |
| **TOPLAM (Yıl 1)** | **1.105** | - | **$168.000** |

---

## 4. Fonksiyonel Gereksinimler

### 4.1 Kullanıcı Yönetimi ve Kimlik Doğrulama

**FR-001: Kullanıcı Kaydı ve Oturum Açma**
Öncelik: P0
Açıklama: Kullanıcılar email ve şifre ile kayıt olabilmeli, kayıtlı kullanıcılar email ve şifre ile giriş yapabilmelidir. Sosyal login (Google, Twitter) v2'de eklenecektir.
Kabul Kriterleri:
- Email formatı doğrulaması yapılmalı
- Şifre en az 8 karakter, 1 büyük harf, 1 rakam içermeli
- "Şifremi unuttum" fonksiyonu çalışmalı
- JWT token 24 saat geçerli olmalı
- Login attempt limit: 5 / 15 dakika (brute force koruması)

**FR-002: Kullanıcı Profili Yönetimi**
Öncelik: P1
Açıklama: Kullanıcılar profil bilgilerini görüntüleyebilmeli ve güncelleyebilmelidir.
Kabul Kriterleri:
- Email, isim, soyisim, telefon değiştirilebilir olmalı
- Şifre değiştirme akışı güvenli olmalı (eski şifre doğrulaması)
- Hesap silme (soft delete) seçeneği olmalı
- Profil fotoğrafı yüklenebilmeli

**FR-003: Abonelik Yönetimi**
Öncelik: P0
Açıklama: Kullanıcılar farklı planlar arasında seçim yapabilmeli ve ödemelerini yönetebilmelidir.
Kabul Kriterleri:
- Free, Pro ($10/ay), Enterprise ($50/ay) planları
- Stripe entegrasyonu ile güvenli ödeme
- Otomatik yenileme ve manuel iptal seçeneği
- Fatura geçmişi görüntülenebilmeli
- Plan değişikliği anlık olarak uygulanmalı

---

### 4.2 Maç Tahmin Modülü

**FR-004: Maç Seçimi ve Listeleme**
Öncelik: P0
Açıklama: Kullanıcılar yaklaşan maçları listeleyebilmeli ve filtreleyebilmelidir.
Kabul Kriterleri:
- Türkiye Süper Lig maçları varsayılan olarak görüntülenmeli
- Tarih aralığı filtresi (haftalık, aylık)
- Takım filtresi (tek takım, karşılaştırma)
- Lig filtresi (Süper Lig, TFF 1. Lig, Premier League)
- Maç kartları: takım isimleri, tarih/saat, lig logosu
- Sayfalama: max 20 maç/sayfa

**FR-005: Detaylı Tahmin Sayfası**
Öncelik: P0
Açıklama: Seçilen maç için tahmin detayları görüntülenmelidir.
Kabul Kriterleri:
- En olası skor (örn. "2-1") büyük punto gösterilmeli
- Beklenen gol sayısı (örn. "GS: 1.8 - FB: 1.3")
- Galibiyet