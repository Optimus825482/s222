# PRD: CPU-Tab2D-to-3D Dönüşüm Aracı

---

## 1. Proje Adı ve Özet

**Proje Adı:** Depth2Mesh (veya önerilen alternatif: **CPU2Three**)

**One-Liner:** GPU gerektirmeden, tamamen yerel işlemci gücüyle 2D fotoğrafları dakikalar içinde 3D mesh modellerine dönüştüren açık kaynak masaüstü uygulaması.

**Versiyon:** v1.0.0 (MVP)
**Durum:** Tasarım Aşaması
**Son Güncelleme:** 23 Şubat 2026

---

## 2. Problem Tanımı

### 2.1 Mevcut Durum Analizi

Günümüzde 2D görselleri 3D modele dönüştürmek için kullanılan çözümlerin büyük çoğunluğu GPU zorunluluğu taşımaktadır. Bu durum, özellikle şu kullanıcı grupları için ciddi bir engel oluşturmaktadır:

| Sorun Kategorisi | Açıklama | Etki Alanı |
|------------------|----------|------------|
| **Donanım Maliyeti** | Yüksek performanslı GPU'lar 10.000-50.000+ TL arasında maliyet gerektirir | Bütçe kısıtlı kullanıcılar, gelişmekteki ülkeler |
| **Bulut Bağımlılığı** | Mevcut çözümlerin %90'ı bulut tabanlı işleme gerektirir | Gizlilik hassas kullanıcılar, çevrimdışı ortam |
| **Enerji Tüketimi** | GPU tabanlı işlemler yüksek elektrik tüketimi yarat | Mobil çalışanlar, sınırlı güç kaynağı olanlar |
| **Öğrenme Eşiği** | Profesyonel araçlar (Blender, Maya) karmaşık öğrenme süreci gerektirir | Hobi kullanıcıları, acil ihtiyaç sahipleri |

### 2.2 Kullanıcı Anket Verileri (Simüle Edilmiş)

Yapılan ön araştırmaya göre potansiyel kullanıcıların:
- **%67'si** mevcut GPU tabanlı çözümleri "çok pahalı" buluyor
- **%78'i** fotoğraflarının sunuculara yüklenmesini "gizlilik riski" olarak değerlendiriyor
- **%54'ü** dönüşüm süresinin 2 dakikanın altında olmasını talep ediyor
- **%89'u** basit, tek tuşla çalışan bir arayüz tercih ediyor

### 2.3 Problem İfadesi (Hikaye Formatında)

> "Elinde sadece集成 işlemcili dizüstü bilgisayar olan bir sosyal medya içerik üreticisi, ürün fotoğraflarını 3D formatına dönüştürmek istiyor. Ancak mevcut çözümler ya GPU gerektiriyor, ya aylık abonelik ücreti talep ediyor, ya da fotoğraflarını yabancı sunuculara yüklemesini zorunlu kılıyor. Bu kullanıcı, hem uygun maliyetli hem de gizlilik odaklı bir çözüme ihtiyaç duyuyor."

---

## 3. Hedef Kullanıcılar ve Persona'lar

### 3.1 Birincil Persona'lar

```
┌─────────────────────────────────────────────────────────────────────┐
│  PERSONA 1: "Hobi Sanatçı Mehmet"                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Demografi:                                                          │
│  • Yaş: 28                                                          │
│  • Meslek: Yazılım mühendisi (tam zamanlı), 3D sanat (hobi)         │
│  • Konum: Türkiye, İstanbul                                         │
│  • Gelir: Orta-üst segment                                          │
│                                                                     │
│  Donanım:                                                            │
│  • Dizüstü bilgisayar (entegre Intel UHD Graphics)                  │
│  • 16GB RAM, Intel i7-1165G7                                        │
│  • Harici GPU yok                                                    │
│                                                                     │
│  İhtiyaçlar:                                                         │
│  • Sokakta çektiği fotoğrafları hızlıca 3D modele çevirmek          │
│  • Blender'da manuel modelleme yapmadan hızlı prototip              │
│  • Çalışmalarını sosyal medyada paylaşmak için içerik üretmek       │
│                                                                     │
│  Pain Points:                                                        │
│  • "NVIDIA GPU'um olmadığı için çoğu araç çalışmıyor"               │
│  • "Online araçlara fotoğraflarımı yüklemek istemiyorum"            │
│                                                                     │
│  Başarı Kriteri:                                                     │
│  • Tek tuşla dönüşüm, 2 dakika içinde sonuç                        │
└─────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────┐
│  PERSONA 2: "KOBİ Sahibi Ayşe"                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Demografi:                                                          │
│  • Yaş: 42                                                          │
│  • Meslek: El yapımı ürün satış işletme sahibi                      │
│  • Konum: Türkiye, Ankara                                           │
│  • Gelir: Orta segment                                              │
│                                                                     │
│  Donanım:                                                            │
│  • Ofis bilgisayarı (dahili grafik kartı)                          │
│  • 8GB RAM, Intel Core i5-10400                                     │
│  • Teknik bilgi: Temel düzey                                        │
│                                                                     │
│  İhtiyaçlar:                                                         │
│  • Ürün fotoğraflarını 3D olarak e-ticaret sitesinde göstermek      │
│  • Profesyonel 3D modelleme yazılımı öğrenmeden çözüm               │
│  • Minimum maliyetle maksimum görsel kalite                         │
│                                                                     │
│  Pain Points:                                                        │
│  • "3D model için profesyonel fotoğrafçı kiralayamıyorum"          │
│  • "Karmaşık yazılımları öğrenemiyorum"                             │
│                                                                     │
│  Başarı Kriteri:                                                     │
│  • 5 adımda ürün fotoğrafından 3D model elde etme                  │
└─────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────┐
│  PERSONA 3: "Eğitimci Dr. Kemal"                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Demografi:                                                          │
│  • Yaş: 45                                                          │
│  • Meslek: Üniversite öğretim üyesi (Bilgisayar Bilimleri)          │
│  • Konum: Türkiye, İzmir                                           │
│  • Gelir: Akademik maaş                                             │
│                                                                     │
│  Donanım:                                                            │
│  • Laboratuvar bilgisayarı                                          │
│  • Sınırlı bütçe, GPU upgrade izni yok                              │
│  • 32GB RAM, AMD Ryzen 7 3700X                                      │
│                                                                     │
│  İhtiyaçlar:                                                         │
│  • Öğrencilere 3D modelleme derslerinde örnek göstermek             │
│  • Araştırma için eski fotoğrafları 3D ortama aktarmak              │
│  • Açık kaynak araçlar kullanmak (kurumsal politikalar nedeniyle)   │
│                                                                     │
│  Pain Points:                                                        │
│  • "Kurum politikaları nedeniyle bulut araçları kullanamıyorum"     │
│  • "Öğrencilerin hepsinin GPU'lu bilgisayarı yok"                   │
│                                                                     │
│  Başarı Kriteri:                                                     │
│  • Tamamen çevrimdışı çalışabilen araç                             │
│  • Açık kaynak lisans (GPL/MIT)                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 İkincil Persona'lar

| Persona | Özellik | Kullanım Senaryosu |
|---------|---------|-------------------|
| **Game Dev Burak** | Bağımsız oyun geliştiricisi | Hızlı prototipleme, placeholder asset üretimi |
| **Mimar Deniz** | İç mimar | Eski fotoğraflardan mekansal rekonstrüksiyon |
| **Arkeolog Fatma** | Akademisyen | Tarihi eser fotoğraflarının dijital arşivlenmesi |

### 3.3 Kullanıcı Segmentasyonu

```
KULLANICI DAĞILIMI TAHMİNİ (İLK 12 AY)

                    ┌──────────────────────┐
                    │    Hobbyist %40      │
                    │   ┌──────────────┐   │
                    │   │              │   │
     ┌──────────────┴──┤  KOBİ %25    ├──┴──────────────┐
     │                 │              │                   │
     │   Profesyonel   └──────────────┘   Eğitim %15     │
     │      %20                                              │
     │                                                      │
     └──────────────────────────────────────────────────────┘
```

---

## 4. Fonksiyonel Gereksinimler

### 4.1 Giriş ve Dönüşüm Modülü

| ID | Gereksinim | Öncelik | Açıklama |
|----|------------|---------|----------|
| **FR-001** | Görsel Yükleme | P0 | Kullanıcı PNG, JPG, WEBP formatlarında tek veya çoklu görsel yükleyebilmeli |
| **FR-002** | Sürükle-Bırak Desteği | P0 | Dosya gezgininden doğrudan uygulama alanına sürükle-bırak ile yükleme |
| **FR-003** | Görsel Önizleme | P0 | Yüklenen görsellerin thumbnail önizlemesi gösterilmeli |
| **FR-004** | Çözünürlük Seçimi | P1 | Kullanıcı çıktı çözünürlüğünü seçebilmeli (480p, 720p, 1080p) |
| **FR-005** | Batch Processing | P2 | Aynı anda 10+ görsel toplu işleme desteği |
| **FR-006** | Format Dönüşümü | P0 | Girdi: PNG, JPG, WEBP / Çıktı: OBJ, GLTF, STL |

### 4.2 Depth Estimation Modülü

| ID | Gereksinim | Öncelik | Açıklama |
|----|------------|---------|----------|
| **FR-007** | Depth Map Üretimi | P0 | DepthAnything V2 modeli kullanılarak derinlik haritası üretimi |
| **FR-008** | CPU Inference | P0 | Tüm işlemler CPU üzerinde gerçekleşmeli (GPU gerektirmemeli) |
| **FR-009** | Inference Optimizasyonu | P1 | ONNX Runtime ile CPU optimizasyonu (INT8 quantization) |
| **FR-010** | Kalite Seçenekleri | P1 | Hızlı (düşük kalite), Normal, Yüksek (detaylı) mod seçenekleri |
| **FR-011** | Depth Map Görüntüleme | P0 | Üretilen depth map'in önizlemesi gösterilmeli |

### 4.3 Mesh Üretim Modülü

| ID | Gereksinim | Öncelik | Açıklama |
|----|------------|---------|----------|
| **FR-012** | Point Cloud Oluşturma | P0 | Depth map'ten 3D point cloud üretimi |
| **FR-013** | Mesh Yüzey Oluşturma | P0 | Point cloud'tan mesh (yüzey) oluşturma |
| **FR-014** | Mesh Temizleme | P1 | Otomatik mesh düzeltme (hole filling, smoothing) |
| **FR-015** | UV Mapping | P2 | Temel UV haritası oluşturma |
| **FR-016** | Texture Projection | P2 | Orijinal görselin mesh üzerine texture olarak yansıtılması |

### 4.4 Kullanıcı Arayüzü Gereksinimleri

| ID | Gereksinim | Öncelik | Açıklama |
|----|------------|---------|----------|
| **FR-017** | Ana Ekran | P0 | Temiz, anlaşılır ana ekran tasarımı |
| **FR-018** | İlerleme Çubuğu | P0 | Dönüşüm sürecinde anlık ilerleme göstergesi |
| **FR-019** | İşlem İptali | P0 | Devam eden işlemi iptal edebilme |
| **FR-020** | Çıktı Önizleme | P0 | 3D modelin interaktif önizlemesi (döndürme, yakınlaştırma) |
| **FR-021** | Dosya Kaydetme | P0 | Kullanıcının istediği konuma OBJ/GLTF dosyası kaydetme |
| **FR-022** | Geçmiş | P2 | Son işlemlerin kaydı ve tekrar erişim |
| **FR-023** | Tema Desteği | P2 | Açık/Koyu tema seçeneği |
| **FR-024** | Dil Desteği | P2 | Türkçe, İngilizce, Almanca dil desteği |

### 4.5 Sistem ve Yardım Modülü

| ID | Gereksinim | Öncelik | Açıklama |
|----|------------|---------|----------|
| **FR-025** | Sistem Gereksinimleri Gösterimi | P1 | Başlangıçta sistem kontrolü ve uyarılar |
| **FR-026** | Hata Mesajları | P0 | Anlaşılır hata mesajları ve çözüm önerileri |
| **FR-027** | Güncelleme Kontrolü | P2 | Yeni versiyon kontrolü |
| **FR-028** | Dokümantasyon | P1 | Yerleşik yardım menüsü ve kullanım kılavuzu |

---

## 5. Non-Fonksiyonel Gereksinimler

### 5.1 Performans Gereksinimleri

| Metrik | Hedef | Ölçüm Yöntemi |
|--------|-------|---------------|
| **Startup Süresi** | < 5 saniye | Uygulama açılışından ana ekran yüklenene kadar |
| **Inference Süresi (1080p)** | < 90 saniye | Depth estimation başlangıç-bitiş arası süre |
| **Inference Süresi (720p)** | < 45 saniye | Aynı, düşük çözünürlük için |
| **Mesh Üretim Süresi** | < 30 saniye | Depth map'ten mesh oluşum süresi |
| **Toplam İşlem Süresi** | < 120 saniye (1080p) | Giriş yüklemeden çıktı hazır olana kadar |
| **Bellek Kullanımı** | < 4GB RAM | Maksimum anlık bellek tüketimi |
| **CPU Kullanımı** | %80-100 (optimize) | Çoklu çekirdek kullanım oranı |

### 5.2 Ölçeklenebilirlik Gereksinimleri

```
ÖLÇEKLENEBİLİRLİK HEDEFLERİ

Kullanıcı Hacmi:
├── Küçük ölçek: 100 aktif kullanıcı/ay → Sorunsuz
├── Orta ölçek: 1.000 aktif kullanıcı/ay → Sorunsuz
└── Büyük ölçek: 10.000 aktif kullanıcı/ay → Sunucu altyapısı gerekir (v2)

İşlem Kapasitesi:
├── Tek işlem: 1 görsel → Destekleniyor
├── Batch işlem: 10 görsel →