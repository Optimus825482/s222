# 📋 ÜRÜN GEREKSİNİMLERİ DOKÜMANI (PRD)

## 2D Görselden 3D Model Oluşturma Uygulaması

---

## 1. PROJE TANITIMI

### 1.1 Proje Adı
**Img2Mesh** — Yerel İşlem Gücüyle Görselden 3D Model Oluşturma Platformu

### 1.2 One-Liner
Tek bir fotoğraftan yapay zeka destekli saniyeler içinde profesyonel kalitede 3D model oluşturan, tamamen yerel çalışan, GPU ve CPU modlarıyla çift donanım uyumlu, gizlilik odaklı 3D içerik üretim aracı.

### 1.3 Versiyon Bilgisi
| Versiyon | Tarih | Açıklama |
|----------|-------|----------|
| 1.0 | Şubat 2026 | İlk PRD dokümanı |

---

## 2. PROBLEM İFADESİ

### 2.1 Pazar Problemi

Günümüz dijital ekonomisinde 3D içerik talebi katlanarak artmaktadır. Ancak 3D model üretimi, teknik bilgi gerektiren, zaman alan ve maliyetli bir süreçtir. Mevcut çözümler bu sorunu yeterince çözmemektedir:

| Mevcut Çözüm | Problem |
|--------------|---------|
| **Manuel Modelleme** | Blender, Maya, ZBrush gibi araçlar öğrenme eğrisi gerektirir; tek model 2-10 saat sürer |
| **Fotogrametri** | Çoklu fotoğraf (20-50+ adet) ve özel ekipman gerektirir |
| **Bulut Tabanlı AI** | Veriler sunuculara gönderilir (gizlilik riski), abonelik ücretlidir, API maliyetleri yüksektir |
| **Profesyonel Hizmetler** | Model başına $100-$1000+ maliyet, teslimat günler-haftalar alır |

### 2.2 Kullanıcı Pain Points

```
┌────────────────────────────────────────────────────────────────────────┐
│                        KULLANICI SORUNLARI                             │
├────────────────────────────────────────────────────────────────────────┤
│ ⚠️  Yüksek Giriş Bariyeri                                               │
│    → 3D modelleme bilgisi olmayan profesyoneller fırsatları kaçırıyor │
├────────────────────────────────────────────────────────────────────────┤
│ ⚠️  Maliyet Baskısı                                                     │
│    → Küçük işletmeler, indie geliştiriciler bütçeyi karşılayamıyor     │
├────────────────────────────────────────────────────────────────────────┤
│ ⚠️  Gizlilik Endişeleri                                                 │
│    → Özel tasarımlar, ürün fotoğrafları dış sunucılara yüklenemez     │
├────────────────────────────────────────────────────────────────────────┤
│ ⚠️  Donanım Kısıtları                                                  │
│    → GPU'suz sunucular ve düşük VRAM'li kartlar mevcut çözümleri      │
│       desteklemiyor                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Çözümümüzün Değer Önerisi

Img2Mesh, bu problemleri şu şekillerde çözer:

1. **Anlık Dönüşüm**: 5 saniye içinde tek görselden 3D model
2. **Sıfır Öğrenme Eğrisi**: Tarayıcı tabanlı basit arayüz
3. **%100 Gizlilik**: Tüm işlemler yerel makinede, veri buluta gitmez
4. **Evrensel Donanım Desteği**: GPU'lu sistemlerde hızlı, CPU'lu sistemlerde optimize
5. **Ücretsiz**: Açık kaynak modeller üzerine inşa, sonsuz kullanım

---

## 3. HEDEF KULLANICILAR & PERSONA'LAR

### 3.1 Birincil Hedef Kitle

| Persona | Demografi | Motivasyon | Kullanım Senaryosu |
|---------|-----------|------------|-------------------|
| **🎮 Indie Oyun Geliştiricisi** | 22-35 yaş, tek başına veya küçük ekip | Hızlı prototipleme, düşük maliyet | Oyun objeleri, karakterler, çevre elemanları |
| **🛒 E-ticaret Satıcısı** | 25-45 yaş, KOBİ sahibi | Ürün görselleştirme, rekabet avantajı | Ürün 360° görüntüleme, katalog içerikleri |
| **🎨 Dijital Sanatçı** | 20-35 yaş, freelancer/yaratıcı | Konsept hızlandırma | Konsept art → 3D base mesh dönüşümü |
| **🏗️ Mimar/İç Tasarımcı** | 28-50 yaş, profesyonel | Müşteri sunumları | Mobilya, dekorasyon objeleri görselleştirme |

### 3.2 İkincil Hedef Kitle

| Persona | Demografi | Motivasyon | Kullanım Senaryosu |
|---------|-----------|------------|-------------------|
| **📱 AR/VR Geliştiricisi** | 24-38 yaş, tech odaklı | İçerik üretimi hızlandırma | Metaverse objeleri, interaktif deneyimler |
| **🖨️ 3D Baskı Meraklısı** | 18-50 yaş, hobi odaklı | Özel parça üretimi | Kişiselleştirilmiş objeler, yedek parçalar |
| **📺 İçerik Üreticisi** | 20-35 yaş, sosyal medya | Viral içerik | 3D avatar, animasyonlu içerikler |
| **🎓 Eğitimci/Araştırmacı** | 25-55 yaş, akademi | Görselleştirme, analiz | Bilimsel modeller, tarihi eserler |

### 3.3 Kullanıcı Yolculuğu Haritası

```
AŞAMA 1: KEŞİF                    AŞAMA 2: DENEYİM                   AŞAMA 3: BAĞLILIK
────────────────────────────────────────────────────────────────────────────────────────────
• Web'de araştırma               • İlk modeli oluşturur              • Düzenli kullanıcı olur
• Alternatifleri karşılaştırır   • Sonucu indirir                    • Önerilerde bulunur
• Ücretsiz dener                 • Sosyal medya'da paylaşır          • Premium özellik ister
• Yerel işlem dikkat çeker       • Tekrar dener                      • Topluluğa katılır
```

---

## 4. FONKSİYONEL GEREKSİNİMLER

### 4.1 Öncelik Matrisi

```
ÖNCELİK ANLAMI:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 P0 (Must Have)     → MVP için zorunlu, olmazsa uygulama çalışmaz
🟡 P1 (Should Have)   → Kullanıcı deneyimi için önemli
🟢 P2 (Nice to Have)  → Gelecek versiyonlar için iyileştirme
```

### 4.2 P0 - Zorunlu Gereksinimler

| ID | Gereksinim | Açıklama | Doğrulama Kriteri |
|----|------------|----------|-------------------|
| **FR-001** | Görsel Yükleme | Kullanıcı JPG, PNG, WEBP formatında görsel yükleyebilmelidir | Desteklenen formatlar yüklenebilmeli, hata mesajı verilmeli |
| **FR-002** | Tek Görsel → 3D Dönüşüm | Tek bir görselden 3D model oluşturulabilmelidir | TripoSR/LGM modeli başarıyla çalışmalı |
| **FR-003** | GPU Hızlandırma | NVIDIA CUDA destekli kartlarda hızlandırma aktif olmalıdır | GPU kullanımı %50+ artmalı, süre %60+ kısalmalı |
| **FR-004** | CPU Modu Desteği | GPU olmayan sistemlerde CPU ile çalışabilmelidir | 8GB RAM sunucuda model oluşturulabilmeli |
| **FR-005** | GLB/OBJ Export | Oluşturulan model GLB veya OBJ formatında indirilebilmelidir | Dosyalar açılabilir, doğru mesh yapısı içermeli |
| **FR-006** | Web Arayüzü | Tarayıcı tabanlı kullanıcı arayüzü olmalıdır | Chrome, Firefox, Edge'de sorunsuz çalışmalı |
| **FR-007** | İlerleme Takibi | Model oluşturma sürecinde ilerleme gösterilmelidir | %, adım adım durum, tahmini süre |
| **FR-008** | 3D Önizleme | Oluşturulan model interaktif olarak görüntülenebilmelidir | Döndürme, yakınlaştırma, kaydırma çalışmalı |
| **FR-009** | Yerel İşleme | Tüm işlemler yerel makinede gerçekleşmelidir | Ağ isteği yapılmamalı, veri dışarı çıkmamalı |
| **FR-010** | Çoklu Donanım Uyumu | Hem GPU'lu hem GPU'suz sistemlerde çalışmalıdır | Otomatik donanım algılama ve mod seçimi |

### 4.3 P1 - Önemli Gereksinimler

| ID | Gereksinim | Açıklama | Doğrulama Kriteri |
|----|------------|----------|-------------------|
| **FR-011** | Toplu İşleme | Aynı anda birden fazla görsel işlenebilmelidir | Batch queue, paralel işleme |
| **FR-012** | STL/FBX Export | Ek 3D formatları desteklenmelidir | 3D yazıcı veya Unity/Blender uyumluluğu |
| **FR-013** | Görsel Ön İşleme | Otomatik arka plan temizleme | RemBG veya benzeri entegrasyon |
| **FR-014** | Kalite Ayarları | Düşük/Orta/Yüksek kalite seçenekleri | VRAM kullanımı ayarlanabilmeli |
| **FR-015** | Geçmiş Yönetimi | Oluşturulan modeller listelenebilmeli | İndirme, silme, yeniden adlandırma |
| **FR-016** | Tema Desteği | Açık/Koyu tema seçeneği | Sistem tercihine uyum |
| **FR-017** | Türkçe Arayüz | Tam Türkçe lokalizasyon | Tüm metinler Türkçe |
| **FR-018** | Mobil Uyumluluk | Telefon tarayıcısında çalışabilmeli | Responsive tasarım |

### 4.4 P2 - İyi Olması Gerekenler

| ID | Gereksinim | Açıklama |
|----|------------|----------|
| **FR-019** | Çoklu Görsel Girişi | Birden fazla açıdan çekilmiş fotoğraflardan daha kaliteli model |
| **FR-020** | Model Düzenleme | Temel mesh düzenleme (pürüz azaltma, basitleştirme) |
| **FR-021** | API Servisi | REST API ile dış uygulama entegrasyonu |
| **FR-022** | Animasyon Desteği | Temel rigging ve animasyon |
| **FR-023** | Stil Transferi | 3D modele sanatsal stil uygulama |
| **FR-024** | Kullanıcı Hesapları | Kayıt, giriş, bulut geçmişi (opsiyonel) |
| **FR-025** | Topluluk Paylaşımı | Model galerisi, paylaşım linkleri |
| **FR-026** | Video → 3D | Video karelerinden model oluşturma |

---

## 5. FONKSİYONEL OLMAYAN GEREKSİNİMLER

### 5.1 Performans Gereksinimleri

| Metrik | Hedef | Koşul |
|--------|-------|-------|
| **GPU Inference Süresi** | < 10 saniye | 8GB+ VRAM, 512x512 görsel |
| **CPU Inference Süresi** | < 5 dakika | 8GB RAM, optimize edilmiş model |
| **İlk Yükleme Süresi** | < 3 saniye | Model cache warm olmalı |
| **3D Önizleme FPS** | > 30 FPS | 1M poly mesh için |
| **Eşzamanlı İşlem** | 1 model | GPU modu; CPU modu queue destekli |
| **Bellek Kullanımı (GPU)** | < 6 GB | Tam çözünürlük model için |
| **Bellek Kullanımı (CPU)** | < 6 GB | Swap olmadan işlem |

### 5.2 Güvenlik Gereksinimleri

| Gereksinim | Açıklama |
|------------|----------|
| **Veri Yerelliği** | Kullanıcı verileri asla dış sunucuya gönderilmemeli |
| **Otomatik Temizleme** | İşlem sonrası geçici dosyalar otomatik silinmeli |
| **İzolasyon** | Her işlem izole ortamda (container/sandbox) çalışmalı |
| **Şifreleme** | Disk üzerinde geçici dosyalar şifrelenmeli (opsiyonel) |
| **Erişim Kontrolü** | Localhost dışından erişim engellenmeli |

### 5.3 Ölçeklenebilirlik Gereksinimleri

| Senaryo | Destek |
|---------|--------|
| **Tek Kullanıcı** | Optimal performans |
| **Küçük Ekip (2-5)** | Sıralı işlem, queue sistemi |
| **Kurumsal (10+)** | Harici load balancer ile dağıtık yapı (v2) |
| **Düşük VRAM (4GB)** | Quantized model, CPU offloading |
| **Yüksek VRAM (16GB+)** | Full precision, batch processing |

### 5.4 Uyumluluk Gereksinimleri

| Platform | Versiyon | Durum |
|----------|----------|-------|
| **Ubuntu** | 20.04+ | ✅ Tam Destek |
| **Windows** | 10+ | ✅ Tam Destek (WSL2 önerilir) |
| **macOS** | 12+ (Apple Silicon) | ⚠️ Sınırlı (ROCm yok, CPU modu) |
| **Python** | 3.10 - 3.12 | ✅ Desteklenen sürümler |
| **NVIDIA CUDA** | 11.8+ | ✅ GPU modu için |
| **AMD ROCm** | 5.6+ | ⚠️ Deneysel |

### 5.5 Kullanılabilirlik Gereksinimleri

| Kriter | Hedef |
|--------|-------|
| **Öğrenme Eğrisi**