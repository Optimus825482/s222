# FUTBOL SKOR TAHMİN SİSTEMİ — WEB UYGULAMASI PROJE ANALİZİ

---

## 1. PROBLEM TANIMI

**Ana Problem:** Futbol tahmin pazarı, profesyonel oyuncular, bahis firmaları ve analistler için yeterince sofistike, şeffaf ve gerçek-zamanlı araçlar sunamıyor. Mevcut çözümler ya çok basit (basit istatistikler) ya da çok pahalı (kurumsal Opta/StatsBomb abonelikleri) ya da şeffaf değil (kara kutu ML modelleri).

**Alt Problemler:**

| Problem | Etki | Frekans |
|---------|------|---------|
| Veri kaynakları dağınık | Analiz için 5-10 farklı platform gezmek gerekiyor | Her maç öncesi |
| Model şeffaflığı yok | Tahminin "neden"i açıklanamıyor | Her tahminde |
| Gerçek-zamanlı güncelleme eksikliği | Sakatlık/hava değişince tahmin sabit kalıyor | Her hafta |
| Bahis değeri analizi yok | Piyasa ile model karşılaştırması yapılamıyor | Her bahis kararında |
| Self-learning mekanizması yok | Model eskiyor, yeniden eğitim manuel | Sezon sonu |

**Çözüm Önerisi:** 4-agent orkestrasyon sistemi + şeffaf raporlama + gerçek-zamanlı güncelleme + betting edge analizi entegre web uygulaması.

---

## 2. HEDEF KİTLLE

### 2.1 Birincil Hedef Kullanıcılar (Yüksek Öncelik)

| Kullanıcı Profili | Sayı (Tahmini) | Ödeme Kapasitesi | Temel İhtiyaç |
|-------------------|----------------|------------------|---------------|
| **Yarı-profesyonel bahisçiler** | ~50,000 (TR) | $50-200/ay | Doğru tahmin + edge analizi |
| **Spor medyası / analistler** | ~5,000 (TR) | $100-500/ay | Şeffaf veri + raporlama |
| **Teknik direktör / analiz ekipleri** | ~2,000 (Avrupa) | $200-1000/ay | Detaylı taktik analiz |

### 2.2 İkincil Hedef Kullanıcılar (v2 İçin)

| Kullanıcı Profili | Ödeme Kapasitesi | Çekirdek Özellik |
|-------------------|------------------|------------------|
| **Fantasy Premier League oyuncuları** | Ücretsiz/Freemium | Oyuncu önerileri |
| **Spor bahisleri startup'ları** | $2000-10000/ay | API erişimi |
| **Takım taraftarları** | Ücretsiz | Maç öncesi içerik |

### 2.3 Hedef Pazar Büyüklüğü (TAM)

| Segment | TR Pazarı | Global Pazar (İngilizce) |
|---------|-----------|--------------------------|
| Yarı-profesyonel bahisçiler | $2-5M/yıl | $50-100M/yıl |
| Medya/Analiz | $1-2M/yıl | $20-40M/yıl |
| Kurumsal (API) | $0.5-1M/yıl | $30-60M/yıl |
| **TOPLAM (3 yıl)** | **$10-25M** | **$300-600M** |

---

## 3. CORE FEATURES (MVP)

### 3.1 MVP Kapsamı — "GoalPredict Pro v1.0"

MVP, 3 ay geliştirme süresi içinde çıkabilecek, temel değer önerisini kanıtlayacak özelliklerden oluşur.

**MVP Feature Listesi:**

| Özellik | Açıklama | Geliştirme Süresi | Öncelik |
|---------|----------|-------------------|---------|
| **Maç Tahmin Sayfası** | Seçilen maç için skor tahmini, olasılık matrisi, güven skoru | 2 hafta | P1 |
| **Veri Kaynakları Entegrasyonu** | StatsBomb + Understat + Transfermarkt API bağlantıları | 3 hafta | P1 |
| **Agent Pipeline Görselleştirme** | 4 agent'in çalışma süreci, ara çıktılar | 1 hafta | P1 |
| **Markdown Rapor İndirme** | PDF/HTML formatında detaylı rapor | 1 hafta | P1 |
| **Kullanıcı Kaydı/Auth** | Email + password, JWT auth | 1 hafta | P1 |
| **Ödeme Entegrasyonu** | Stripe abonelik sistemi | 2 hafta | P1 |
| **Maç Takvimi** | Yaklaşan maçları listele, filtrele | 1 hafta | P2 |
| **Takım Karşılaştırma** | İki takımın xG, form, H2H metriklerini yan yana göster | 1 hafta | P2 |
| **Özet Dashboard** | Son 10 tahminin doğruluk oranı, Brier Score | 1 hafta | P2 |

### 3.2 MVP Ekran Tasarımı

```
┌─────────────────────────────────────────────────────────────────┐
│  GOALPREDICT PRO v1.0                              [User: Pro] │
├─────────────────────────────────────────────────────────────────┤
│  [Dashboard] [Maçlar] [Tahminler] [Raporlar] [Ayarlar]         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ⚽ Galatasaray vs Fenerbahçe                              │  │
│  │  📅 15 Mart 2026, 20:00  📍 Ali Sami Yen                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │   SKOR TAHMİNİ      │  │   OLASILIK DAĞILIMI             │  │
│  │                     │  │                                 │  │
│  │   2 - 1             │  │   GS: ████████████████░ 62%     │  │
│  │   (en olası)        │  │   BER: ██████░░░░░░░░░ 24%      │  │
│  │                     │  │   FB:  ██████░░░░░░░░░ 14%      │  │
│  │   Beklenen: 1.8-1.3 │  │                                 │  │
│  │   Güven: 84%        │  │   En olası skorlar:             │  │
│  └─────────────────────┘  │   2-1 ████████████ 18%          │  │
│                           │   1-1 ██████████ 15%            │  │
│                           │   2-0 ████████ 12%              │  │
│                           └─────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  📊 MODEL DETAYLARI                          [Detaylı ↓]  │  │
│  │                                                           │  │
│  │  [Researcher: 12s] [Thinker: 8s] [Reasoner: 15s] [Speed: 10s] │
│  │                                                           │  │
│  │  xG Diff: +0.42  |  Form (5 maç): 7.2/10  |  PPDA: 8.5   │  │
│  │  H2H (son 10): 4GS - 3FB - 3B  |  Player Elo: 1650       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ⚠️ RİSK FAKTÖRLERİ                                        │  │
│  │  • GS forvet sakat (%15 xG düşüşü)                        │  │
│  │  • Yağmur olasılığı %70 (pas başarısı düşebilir)          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [📥 Rapor İndir]  [🔄 Yeni Tahmin]  [💰 Bahis Edge: +5%]     │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 MVP Teknik Gereksinimleri

| Bileşen | Teknoloji | Gerekçe |
|---------|-----------|---------|
| **Frontend** | React 18 + TypeScript + Tailwind CSS | Component reusability, type safety |
| **Backend** | FastAPI (Python) + Pydantic | ML modelleri ile uyum, async desteği |
| **Database** | PostgreSQL (relational) + Redis (cache) | User data, predictions, cache |
| **ML Pipeline** | scikit-learn + XGBoost + PyMC3 | Baseline modeller, uncertainty |
| **Auth** | JWT + FastAPI-Users | Güvenli, ölçeklenebilir auth |
| **Payments** | Stripe API | Abonelik yönetimi |
| **Hosting** | AWS EC2 + RDS + ElastiCache | Ölçeklenebilir, maliyet-etkin |
| **CI/CD** | GitHub Actions + Docker | Otomatik deployment |

---

## 4. V2 ÖZELLİKLERİ (6 AY SONRA)

### 4.1 V2 Feature Listesi

| Özellik | Açıklama | Etki (Tahmin Doğruluğu/Gelir) | Geliştirme |
|---------|----------|-------------------------------|------------|
| **Live Feed Agent** | Sakatlık/hava/tweet real-time monitoring | +8% doğruluk | 4 hafta |
| **Self-Learning Loop** | Online model güncelleme | +15% kalibrasyon | 3 hafta |
| **Context Engine** | Derby/kupa/motivasyon analizi | +20% derbi doğruluğu | 2 hafta |
| **Betting Edge Dashboard** | Piyasa vs model karşılaştırması | +Gelir potansiyeli | 2 hafta |
| **Match Simulation (3D)** | Monte Carlo simülasyon görselleştirme | +Kullanıcı bağlılığı | 4 hafta |
| **Oyuncu Bazlı Tahmin** | Bireysel oyuncu performans önerileri | +FPL kullanıcıları | 3 hafta |
| **API Servisi** | Kurumsal müşteriler için REST API | +B2B gelir | 3 hafta |
| **Mobil App** | React Native iOS/Android | +Kullanıcı tabanı %40 | 6 hafta |
| **Multi-lig Desteği** | Premier League, La Liga, Serie A, Bundesliga | +Global pazar | 2 hafta |

### 4.2 V2 Ekran Tasarımı — Simülasyon Modülü

```
┌─────────────────────────────────────────────────────────────────┐
│  MAÇ SİMÜLASYONU: GS vs FB (1000 simülasyon)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  📈 Skor Dağılımı                                           │  │
│  │                                                             │  │
│  │  320 kez: 2-1 GS ████████████████ 32%                      │  │
│  │  210 kez: 1-1    ██████████ 21%                            │  │
│  │  180 kez: 1-2 FB ████████ 18%                              │  │
│  │  150 kez: 0-0    ██████ 15%                                │  │
│  │  140 kez: 2-2    ██████ 14%                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  🎯 En Kritik Faktörler                                    │  │
│  │                                                             │  │
│  │  1. ⚠️ Sakatlık Etkisi (%22 xG düşüşü)                     │  │
│  │     → GS forvet (0.8 xG/maç) eksik                         │  │
│  │                                                             │  │
│  │  2. 🌧️ Hava Koşulları (%12 pas başarısı düşüşü)            │  │
│  │     → Yağmurlu havada kontrollü pas zorlaşıyor             │  │
│  │                                                             │  │
│  │  3. 📊 Form Farkı (GS: 7.2 vs FB: 6.1)                     │  │
│  │     → Son 5 maçta GS 3 galibiyet, 1 beraberlik             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  💰 BETTING EDGE ANALİZİ                                    │  │
│  │                                                             │  │
│  │  GS Galibiyeti: Model 62% | Piyasa 57% | Edge: +5% ✅      │  │
│  │  Bahis Önerisi: 2-1 skor bahisi (odds 6.5)                 │  │
│  │  Stake: Bankroll'un %2'si                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [▶️ Simülasyonu Oynat]  [📊 Detaylı Rapor]  [💰 Bahis Koy]   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. REKABET ANALİZİ

### 5.1 Mevcut Pazar Oyuncuları

| Ürün | Fiyat | Güçlü Yan | Zayıf Yan |
|------|-------|-----------|-----------|
| **FiveThirtyEight SPI** | Ücretsiz | Büyük marka, şeffaf metodoloji | Basit model, sadece lig tahmini |
| **Betfair Predictor** | $100+/ay | Piyasa verisi entegrasyonu | Sadece İngiltere ligleri |
| **StatsBomb** | $20K+/yıl | En kaliteli veri | Veri sağlayıcı, tahmin yok |
| **Understat** | Ücretsiz | xG verileri, ücretsiz | Sadece veri, analiz yok |
| **Football-API** | $50-200/ay | API erişimi | Sadece ham veri |
| **SmartBets** | $50/ay | Bahis ipuçları | Metodoloji şeffaf değil |

### 5.2 Rekabet Avantajımız

| Boyut | GoalPredict | Rakipler |
|-------|-------------|----------|
| **Şeffaflık** | Agent çıktıları, ara hesaplar açık | Kara kutu modeller |
| **Türkiye Ligi** | GS, FB, BJK, TS detaylı | Genellikle yok |
| **Bahis Edge** | Model vs piyasa karşılaştırması | Hiçbiri sunmuyor |
| **Gerçek-zamanlı** | Live Feed Agent (v2) | Statik tahminler |
| **Self-Learning** | Otomatik model güncelleme | Manuel yeniden eğitim |
| **Fiyat/Değer** | $100-200/ay, kurumsal kalite | Opta çok pahalı, ücretsizler basit |

### 5.3 Farklılaştırıcı Özellikler

1. **Agent Orkestrasyon Görünürlüğü:** Kullanıcı, tahminin "nasıl" yapıldığını adım adım görebilir — bu güven oluşturur.

2. **Türkiye Odaklı:** TR pazarı için özelleştirilmiş, Süper Lig detayı — yerel rakiplere göre global kalite.

3. **Betting Edge Entegrasyonu:** Sadece tahmin değil, "değerli bahis" önerisi — kullanıcı için doğrudan fayda.

4. **Simülasyon Tablı Anlatım:** "Neden bu tahmin?" sorusuna cevap veren görsel simülasyon — eğitici ve ikna edici.

---

## 6. TEKN