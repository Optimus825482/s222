# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## 1. PROJECT NAME & ONE-LINER

**Proje Adı:** FutVision AI — Akıllı Futbol Maç Analiz ve Tahmin Platformu

**One-Liner:** Tek bir tıklamayla maç öncesi tüm istatistikleri, sakatlık durumlarını ve yapay zeka destekli skor tahminlerini gösteren, Türkiye'nin ilk kapsamlı futbol tahmin asistanı.

---

## 2. PROBLEM STATEMENT

### 2.1 Mevcut Durum

Günümüzde bahis kullanıcıları ve futbol analistleri, maç analizi için birden fazla platformu manuel olarak takip etmek zorundadır. ESPN'den kadro bilgisi, FotMob'dan sakatlık verisi, farklı istatistik sitelerinden form durumu — tüm bu parçalı bilgiler tek bir yerde birleştirilemiyor. Kullanıcılar, "Bu maçta neden X takımı kazanır?" sorusuna net bir yanıt alamıyor veya aldıkları yanıtlar sadece sayısal verilerden ibaret kalıyor.

### 2.2 Kullanıcı Pain Points

| Pain Point | Etkisi | Sonucu |
|------------|--------|--------|
| **Bilgi Parçalanması** | Her veri kaynağı ayrı bir platform, saatlerce araştırma gerektiriyor | Kullanıcı yorgunluğu, karar verememe |
| **Şeffaflık Eksikliği** | Tahminlerin neden yapıldığı açıklanmıyor | Güven kaybı, tekrar kullanım motivasyonu düşüklüğü |
| **Gecikmeli Veri** | Sakatlık/transfer haberleri anlık takip edilmiyor | Eski verilerle güncel tahmin yapma hatası |
| **Türkçe Eksikliği** | Yabancı platformlar lokal terminoloji kullanmıyor | Kullanıcı deneyimi kırılganlığı |
| **Güven Skoru Yokluğu** | Tahminlerin güvenilirliği ölçülemiyor | Risk yönetimi yapılamıyor |

### 2.3 Problem Tanımı

FutVision AI, parçalı futbol veri ekosistemini tek bir yapay zeka destekli platformda birleştirerek, kullanıcıların maç öncesi 30 saniyede kapsamlı analiz almasını, tahminlerin arkasındaki mantığı anlamasını ve güven skoru ile bilinçli kararlar vermesini sağlar.

---

## 3. TARGET USERS & PERSONAS

### 3.1 Primer Persona: aktif Bahis Kullanıcısı

**Ad:** Mehmet, 32, İstanbul
**Meslek:** Yazılım Mühendisi
**Davranış:** Haftada 3-5 maça bahis yapıyor, her maçtan önce 15-20 dakika araştırma yapıyor
**Motivasyon:** ROI (Yatırım Getirisi) maksimizasyonu, kayıp minimizasyonu
**Pain:** "Bir maçın analizini yapmak için 5 farklı site açmak zorundayım, bu çok zaman alıyor."
**Hedef:** Daha az zaman harcayarak daha isabetli tahminler yapmak
**Fiyat Hassasiyeti:** Premium özellikler için aylık 50-100 TL ödemeye hazır

### 3.2 Sekonder Persona: Fantasy Lig Oyuncusu

**Ad:** Elif, 24, Ankara
**Mesleh:** Üniversite Öğrencisi
**Davranış:** Fantasy Premier League ve Süper Lig fantasy oynuyor, kadro optimizasyonu yapıyor
**Motivasyon:** Lig sıralamasında yükselme, rekabet
**Pain:** "Hangi oyuncuyu alacağıma karar veremiyorum, sakatlık riskini bilmiyorum."
**Hedef:** Puan potansiyeli yüksek oyuncuları tespit etmek
**Fiyat Hassasiyeti:** Ücretsiz kullanım tercih ediyor, premium'a geçiş potansiyeli var

### 3.3 Tersiyer Persona: Casual Taraftar

**Ad:** Ali, 45, İzmir
**Meslek:** Emekli Öğretmen
**Davranış:** Maç öncesi sohbet için bilgi arıyor, bahis nadiren yapıyor
**Motivasyon:** Maçı daha iyi anlamak, sosyal ortamda konuşabilmek
**Pain:** "İstatistikleri anlamıyorum, sadece kolay bir özet istiyorum."
**Hedef:** 5 dakikada maç hakkında fikir sahibi olmak
**Fiyat Hassasiyeti:** Tamamen ücretsiz kullanım bekliyor

### 3.4 Kuartier Persona: İçerik Üreticisi

**Ad:** Burak, 28, İstanbul
**Meslek:** Bahis Youtuberı / Influencer
**Davranış:** Haftalık tahmin videoları çekiyor, takipçilerine içerik üretiyor
**Motivasyon:** Özgün içerik üretme, takipçi artırma
**Pain:** "Verilerimi doğrulayacak bir kaynak arıyorum, güvenilir referans lazım."
**Hedef:** Embeddable içerik ve doğrulanabilir kaynak kullanmak
**Fiyat Hassasiyeti:** B2B/API erişimi için ödemeye hazır

---

## 4. FUNCTIONAL REQUIREMENTS

### 4.1 P0 — MVP (Must-Have)

| ID | Requirement | Description | Priority |
|----|-------------|-------------|----------|
| **FR-P0-001** | Maç Listesi Görüntüleme | Bugün, yarın ve önümüzdeki 7 günün maçlarını listele | P0 |
| **FR-P0-002** | Lig Filtreleme | Süper Lig, Premier League, La Liga, Bundesliga, Serie A, Champions League filtreleri | P0 |
| **FR-P0-003** | Takım Kartı Görüntüleme | Takım temel istatistikleri: son 5 maç form, ev/deplasman performansı, gol averajı | P0 |
| **FR-P0-004** | ELO Rating Hesaplama | Takımlar için dinamik ELO rating hesapla ve göster | P0 |
| **FR-P0-005** | Sakatlık Verisi Entegrasyonu | FotMob API'den canlı sakatlık ve ceza durumlarını çek | P0 |
| **FR-P0-006** | AI Skor Tahmini | 3 model ensemble (Poisson + ELO + Form) ile 1-X-2 tahmini | P0 |
| **FR-P0-007** | Skor Olasılık Dağılımı | En olası 5 skorun olasılıklarını göster (örn: 1-0: 28%, 1-1: 22%...) | P0 |
| **FR-P0-008** | Güven Skoru | Tahminin güvenilirliğini 0-100% olarak göster | P0 |
| **FR-P0-009** | "Neden Bu Tahmin?" Açıklaması | LLM destekli doğal dil açıklaması ile tahmin mantığını açıkla | P0 |
| **FR-P0-010** | 2.5 Alt/Üst Tahmini | Maçta 2.5 gol altı/üstü olasılıklarını hesapla | P0 |
| **FR-P0-011** | KG (Karşılıklı Gol) Tahmini | İki takımın da gol atma olasılığını hesapla | P0 |
| **FR-P0-012** | Hızlı Arama | Takım adı ile hızlı maç bulma | P0 |
| **FR-P0-013** | Mobil Uyumluluk | Responsive tasarım ile mobil cihazlarda sorunsuz çalışma | P0 |
| **FR-P0-014** | Türkçe Arayüz | Tüm içerik Türkçe, lokal terminoloji kullanımı | P0 |

### 4.2 P1 — Beta (Should-Have)

| ID | Requirement | Description | Priority |
|----|-------------|-------------|----------|
| **FR-P1-001** | Kullanıcı Hesabı | Email ve sosyal medya ile kayıt/giriş | P1 |
| **FR-P1-002** | Takım Favorileri | İzlenen takımları kaydet, favori takımların maçlarını öne çıkar | P1 |
| **FR-P1-003** | Maç Bildirimleri | Favori takımların maçlarından 1 saat önce push notification | P1 |
| **FR-P1-004** | Historical Analiz | Takımların geçmiş karşılaşmalarındaki performans verisi | P1 |
| **FR-P1-005** | Odds Entegrasyonu | Bahis şirketlerinden güncel oranları göster (karşılaştırmalı) | P1 |
| **FR-P1-006** | Model Performans Takibi | Geçmiş tahminlerin isabet oranını kullanıcıya göster | P1 |
| **FR-P1-007** | Paylaşım Özelliği | Tahmin sonuçlarını sosyal medyada paylaş | P1 |
| **FR-P1-008** | Offline Cache | Son görüntülenen maç analizlerini offline göster | P1 |
| **FR-P1-009** | Arama Geçmişi | Son aranan takımları kaydet | P1 |
| **FR-P1-010** | Dark Mode | Karanlık tema desteği | P1 |

### 4.3 P2 — V2 (Nice-to-Have)

| ID | Requirement | Description | Priority |
|----|-------------|-------------|----------|
| **FR-P2-001** | Canlı Maç Analizi | Maç sırasında real-time istatistikler ve momentum analizi | P2 |
| **FR-P2-002** | Oyuncu Bazlı Analiz | Key oyuncuların form durumu, xG, pass completion | P2 |
| **FR-P2-003** | Custom Model Ağırlıkları | Kullanıcının kendi ağırlık sistemi ile model oluşturması | P2 |
| **FR-P2-004** | Parlay Builder | Çoklu maç kombine öneri motoru | P2 |
| **FR-P2-005** | Multi-Language | İngilizce, Almanca dil desteği | P2 |
| **FR-P2-006** | API Erişimi | 3. parti geliştiricilere API endpoint'leri | P2 |
| **FR-P2-007** | Embeddable Widget | Web sitelerine gömülebilir tahmin widget'ları | P2 |
| **FR-P2-008** | Sosyal Özellikler | Kullanıcı tahmin ligleri, liderlik tablosu | P2 |
| **FR-P2-009** | Prediction Injury Alerts | Sakatlık öncesi erken uyarı sistemi | P2 |
| **FR-P2-010** | Detaylı İstatistik Raporu | Maç başına PDF/Excel export | P2 |

---

## 5. NON-FUNCTIONAL REQUIREMENTS

### 5.1 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Page Load Time** | < 3 seconds (first contentful paint) | Lighthouse |
| **Full Analysis Time** | < 30 seconds (tüm fazlar tamamlandığında) | Internal monitoring |
| **API Response Time** | < 500ms (her API çağrısı için) | API Gateway metrics |
| **Concurrent Users** | 1000 eşzamanlı kullanıcı (MVP) | Load testing |
| **Uptime SLA** | 99.5% (aylık max 3.6 saat downtime) | Uptime monitoring |
| **Mobile Performance** | 80+ Lighthouse mobile score | Lighthouse |
| **Streaming Latency** | < 2 seconds (chunk yayını) | SSE monitoring |

### 5.2 Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Authentication** | JWT token-based auth, refresh token rotation |
| **Data Encryption** | TLS 1.3, AES-256 at rest |
| **API Security** | Rate limiting (100 req/min per user), API key management |
| **Input Validation** | All inputs sanitized, SQL injection prevention |
| **GDPR Compliance** | User data deletion on request, data portability |
| **Payment Security** | PCI-DSS compliant payment processor (Stripe/Iyzico) |
| **Audit Logging** | All critical actions logged for 90 days |
| **Dependency Scanning** | Weekly dependency vulnerability scans |

### 5.3 Scalability Requirements

| Scale Level | Target Users | Architecture |
|-------------|--------------|--------------|
| **MVP** | 0-1,000 | Single instance, basic caching |
| **Growth** | 1,000-10,000 | Load balancer, read replicas |
| **Scale** | 10,000-100,000 | Kubernetes, auto-scaling groups |
| **Enterprise** | 100,000+ | Multi-region deployment |

### 5.4 Reliability Requirements

| Scenario | Strategy |
|----------|----------|
| **Primary API Failure** | Fallback to secondary API source, cached data |
| **LLM Service Down** | Return cached prediction, graceful degradation |
| **Database Unavailable** | Redis cache fallback, read-only mode |
| **High Traffic Spike** | Auto-scaling, rate limiting, queue-based processing |
| **Data Inconsistency** | Eventual consistency model, reconciliation jobs |

### 5.5 Usability Requirements

| Requirement | Target |
|-------------|--------|
| **Learning Curve** | New user completes first analysis in < 2 minutes |
| **Accessibility** | WCAG 2.1 AA compliance |
| **Localization** | Full Turkish support, date/number formatting |
| **Error Messages** | User-friendly, actionable error messages in Turkish |
| **Loading States** | Progress indicator for all async operations |

---

## 6. USER STORIES

### 6.1 Bahis Kullanıcısı Persona

| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| **US-001** | "Bir bahisçi olarak, maç analizini 30 saniyeden kısa sürede almak istiyorum, böylece bahis kapanmadan karar verebileyim." | • Ana sayfa yüklenirken skeleton loader göster<br>• Analiz tamamlandığında notification<br>• Max 30s bekleme süresi |
| **US-002** | "Bir bahisçi olarak, tahminin neden yapıldığını anlamak istiyorum, böylece kendi analizimi yapabilirim." | • "Neden Bu Tahmin?" button'u her tahminde mevcut<br>• Açıklama en az 3 faktör içeriyor<br>• Faktörler veriye dayalı (kaynak gösterimi) |
| **US-003** | "Bir bahisçi olarak, güven skoru düşük tahminlerde uyarılmak istiyorum, böylece risk yönetimi yapabilirim." | • Güven skoru 0-100% gösteriliyor<br>• <50% için sarı uyarı<br>• <30% için kırmızı uyarı |
| **US-004** | "Bir bahisçi olarak, farklı bahis şirketlerinin oranlarını karşılaştırmak istiyorum, böylece en iyi değği bulabilirim." | • Min 3 bahis şirketi oranı gösteriliyor<br>• En yüksek oran highlight ediliyor<br>• Oranlar real-time güncelleniyor |

### 6.2 Fantasy Lig Kullanıcısı Persona

| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| **US-005** | "Bir fantasy oyuncusu olarak, sakat oyuncuları anlık