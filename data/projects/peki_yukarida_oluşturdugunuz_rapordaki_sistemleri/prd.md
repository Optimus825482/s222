# DESKAPP 3D CONVERTER — PRODUCT REQUIREMENTS DOCUMENT (PRD)

**Doküman Sürümü:** 1.0  
**Son Güncelleme:** 23 Şubat 2026  
**Durum:** Onaylı — Geliştirmeye Hazır  
**Proje Yöneticisi:** AI Assistant Team  

---

## 1. PROJE TANITIMI

### 1.1 Temel Bilgiler

| Alan | Değer |
|------|-------|
| **Proje Adı** | DeskApp 3D Converter |
| **Kısa Tanım** | GPU gerektirmeyen, CPU tabanlı masaüstü uygulaması ile tek tuşla 2D fotoğraflardan profesyonel 3D modeller oluşturma platformu |
| **Hedef Platform** | Windows 10/11, macOS 11+, Ubuntu 20.04+ |
| **Geliştirme Modeli** | Agile/Scrum (2 haftalık sprintler) |
| **Tahmini MVP Süre** | 8-12 hafta (tek geliştirici) |
| **Lisanslama Modeli** | Freemium (Ücretsiz + Tek Seferlik Pro Lisans) |

### 1.2 Vizyon

> "GPU'suz, aboneliksiz, karmaşıksız — herkes için erişilebilir 3D model oluşturma."

DeskApp, 3D model üretimini demokratikleştirir. Pahalı bulut hizmetlerine veya teknik uzmanlığa gerek kalmadan, sıradan kullanıcıların fotoğraflarını profesyonel kalitede 3D modellere dönüştürmesini sağlar.

---

## 2. PROBLEM TANIMI

### 2.1 Mevcut Durum Analizi

3D içerik üretimi, günümüzde giderek artan bir talep görmektedir. E-ticaret platformları ürünlerin 3D görselleştirilmesini talep etmekte, emlak sektörü sanal turlara yönelmekte ve dijital arşivleme ihtiyacı her geçen gün büyümektedir. Ancak mevcut çözümler, bu talebi karşılamakta yetersiz kalmaktadır.

| Çözüm | Maliyet | Teknik Eğitim | Donanım Gereksinimi | Kullanım Kolaylığı |
|-------|---------|---------------|---------------------|-------------------|
| **Meshroom** | Ücretsiz | Orta-Yüksek | CPU (yavaş) / GPU (hızlı) | Düşük (CLI tabanlı) |
| **COLMAP** | Ücretsiz | Yüksek | CPU | Düşük (CLI tabanlı) |
| **Luma AI** | $30/ay | Düşük | Yok (Bulut) | Yüksek |
| **Polycam** | $15/ay | Düşük | Yok (Bulut) | Yüksek |
| **Professional Tarayıcı** | $5,000+ | Düşük | Özel Donanım | Orta |
| **Blender** | Ücretsiz | Çok Yüksek | GPU Önerilir | Orta |

### 2.2 Kullanıcı Pain Points

**Pain Point 1: Maliyet Baskısı**
Küçük işletmeler ve bireysel kullanıcılar için aylık $15-30 abonelik maliyetleri sürdürülebilir değildir. Özellikle düşük hacimli kullanım senaryolarında bu maliyet, getiri sağlamamaktadır.

**Pain Point 2: Teknik Eğitim Gereksinimi**
COLMAP ve Meshroom gibi açık kaynaklı araçlar, komut satırı kullanımı ve 3D kavramları hakkında derinlemesine bilgi gerektirmektedir. Ortalama bir e-ticaret satıcısı bu araçları kullanamamaktadır.

**Pain Point 3: Donanım Bağımlılığı**
Modern derin öğrenme tabanlı çözümler GPU zorunluluğu getirmektedir. Yalnızca CPU kaynaklarına sahip kullanıcılar bu çözümlerden mahrum kalmaktadır.

**Pain Point 4: İnternet Bağımlılığı**
Bulut tabanlı çözümler, sürekli internet bağlantısı gerektirmektedir. Bu durum, gizlilik endişeleri olan kullanıcılar veya internet erişiminin sınırlı olduğu bölgelerde ciddi bir engel oluşturmaktadır.

### 2.3 DeskApp'in Çözümü

DeskApp, yukarıda belirtilen tüm pain point'leri ele almaktadır. GPU gerektirmeyen CPU-optimized bir pipeline ile yerel işlem kapasitesini maksimum düzeyde değerlendirir. Tek seferlik lisans modeli ile abonelik maliyetini ortadan kaldırır. Basit ve sezgisel kullanıcı arayüzü ile teknik bilgi gereksinimini minimize eder. Tamamen offline çalışarak internet bağımlılığını ortadan kaldırır.

---

## 3. HEDEF KULLANICILAR VE PERSONA

### 3.1 Birincil Persona: "Küçük E-Ticaret Satıcısı"

**Ad:** Ayşe  
**Yaş:** 32  
**Mesaj:** Shopify veya Etsy'de el yapımı ürünler satıyor.  
**Teknik Seviye:** Photoshop biliyor, Blender bilmiyor.  
**Bütçe:** $0-50/ay (tek seferlik ödeme tercih eder).  
**Kullanım Senaryosu:** Ürün fotoğraflarını yükleyip 3D model oluşturmak, ardından e-ticaret sitesine yüklemek.

**Temel İhtiyaçlar:**
- Sade ve anlaşılır arayüz
- Hızlı sonuç (günde 10-20 ürün işlemeli)
- OBJ/GLTF format desteği (Shopify uyumlu)
- Toplu işlem desteği

**Başarı Tanımı:** "5 dakikada 10 ürünün 3D modelini oluşturabilmeliyim."

### 3.2 İkincil Persona: "Emlak Danışmanı"

**Ad:** Mehmet  
**Yaş:** 45  
**Mesaj:** Gayrimenkul danışmanlığı yapıyor.  
**Teknik Seviye:** Düşük (sadece email ve temel internet kullanımı).  
**Bütçe:** $0-100/ay (kurumsal kart ile ödeme).  
**Kullanım Senaryosu:** Satılık/ kiralık evlerin fotoğraflarından 3D içerik üretmek.

**Temel İhtiyaçlar:**
- Tek tuşla işlem başlatma
- Rehberli workflow (adım adım yönlendirme)
- Mesh ve nokta bulutu export
- Görsel önizleme

**Başarı Tanımı:** "Tek bir tuşla evimin 3D modelini oluşturabilmeliyim."

### 3.3 Üçüncül Persona: "Müze/Arşiv Uzmanı"

**Ad:** Dr. Zeynep  
**Yaş:** 48  
**Mesaj:** Üniversite müzesinde dijitalleştirme projesi yürütüyor.  
**Teknik Seviye:** Orta (temel programlama bilgisi, 3D kavramlarına aşina).  
**Bütçe:** Kurumsal lisanslama (yıllık anlaşma).  
**Kullanım Senaryosu:** Tarihi eserlerin yüksek çözünürlüklü 3D taramalarını oluşturmak.

**Temel İhtiyaçlar:**
- Maksimum kalite (yüksek çözünürlük, detay koruma)
- Metadata desteği (eser bilgileri ile etiketleme)
- Toplu işlem (100+ eser)
- Standart format export (OBJ, PLY)

**Başarı Tanımı:** "Tarihi eserlerin en ince detaylarını yakalayan 3D modeller oluşturabilmeliyim."

---

## 4. FONKSİYONEL GEREKSİNİMLER

### 4.1 Giriş ve Dosya Yönetimi

| ID | Öncelik | Gereksinim | Açıklama |
|----|---------|------------|----------|
| FR-001 | **P0** | Tek görsel yükleme | Kullanıcı JPG, PNG, WEBP formatlarında tek bir görsel yükleyebilmeli. Dosya boyutu limiti 50MB. |
| FR-002 | **P0** | Toplu görsel yükleme | Kullanıcı aynı anda 100'e kadar görsel yükleyebilmeli. Batch upload progress bar ile gösterilmeli. |
| FR-003 | **P0** | Klasör izleme | Kullanıcı bir klasör seçebilmeli ve uygulama otomatik olarak yeni görselleri tespit edip işlemeye başlamalı. |
| FR-004 | **P1** | Drag-and-drop | Görseller doğrudan uygulama penceresine sürüklenerek yüklenebilmeli. |
| FR-005 | **P1** | Format doğrulama | Yüklenen dosyaların geçerli görsel formatı olup olmadığı kontrol edilmeli, hatalı dosyalar için uyarı verilmeli. |
| FR-006 | **P2** | Recent files | Son kullanılan dosyalar ve klasörler listelenmeli (history). |

### 4.2 Görsel Ön İşleme

| ID | Öncelik | Gereksinim | Açıklama |
|----|---------|------------|----------|
| FR-007 | **P0** | Otomatik boyutlandırma | Görseller modelin gerektirdiği çözünürlüğe otomatik olarak ölçeklendirilmeli (varsayılan: 518x518). |
| FR-008 | **P0** | Normalizasyon | Görsel piksel değerleri [0, 1] aralığına normalize edilmeli. |
| FR-009 | **P1** | Manuel crop | Kullanıcı gerektiğinde görseli manuel olarak kırpabilmeli. |
| FR-010 | **P1** | Otomatik contrast | Derinlik tahmini için optimal kontrast ayarı otomatik uygulanmalı. |
| FR-011 | **P2** | Batch preprocessing | Toplu işlem için görseller paralel olarak ön işlenmeli. |

### 4.3 Derinlik Tahmini

| ID | Öncelik | Gereksinim | Açıklama |
|----|---------|------------|----------|
| FR-012 | **P0** | Depth Anything V2 entegrasyonu | Depth Anything V2 modeli CPU-optimized olarak çalıştırılmalı. Small, Base, Large variant desteği. |
| FR-013 | **P0** | Metrik derinlik çıktısı | Tahmin edilen derinlik değerleri metre cinsinden metrik olmalı (ölçek faktörü ile). |
| FR-014 | **P0** | Derinlik haritası görselleştirme | Derinlik haritası false-color ile görselleştirilmeli ve kullanıcıya gösterilmeli. |
| FR-015 | **P1** | Model seçimi | Kullanıcı Small/Base/Large model arasında seçim yapabilmeli. |
| FR-016 | **P1** | Çözünürlük ayarı | Kullanıcı işlem çözünürlüğünü (384, 518, 640) seçebilmeli. |
| FR-017 | **P2** | Özel model yükleme | Kullanıcı kendi eğitilmiş ONNX modelini yükleyebilmeli. |

### 4.4 3D Reconstruction

| ID | Öncelik | Gereksinim | Açıklama |
|----|---------|------------|----------|
| FR-018 | **P0** | Depth-to-pointcloud | Derinlik haritası, kamera intrinsics kullanılarak 3D nokta bulutuna dönüştürülmeli. |
| FR-019 | **P0** | Pointcloud-to-mesh | Nokta bulutundan Poisson surface reconstruction ile mesh oluşturulmalı. |
| FR-020 | **P0** | Outlier removal | Gürültülü noktalar otomatik olarak filtrelenmeli (statistical outlier removal). |
| FR-021 | **P1** | Mesh smoothing | Oluşturulan mesh yumuşatılmalı (Laplacian smoothing). |
| FR-022 | **P1** | Hole filling | Küçük delikler otomatik olarak doldurulmalı. |
| FR-023 | **P2** | Mesh simplification | Poligon sayısı azaltılarak dosya boyutu optimize edilmeli. |

### 4.5 Export ve Çıktı

| ID | Öncelik | Gereksinim | Açıklama |
|----|---------|------------|----------|
| FR-024 | **P0** | OBJ export | Mesh OBJ formatında dışa aktarılabilmeli (MTL dosyası ile birlikte). |
| FR-025 | **P0** | PLY export | Nokta bulutu PLY formatında dışa aktarılabilmeli. |
| FR-026 | **P0** | STL export | Mesh STL formatında dışa aktarılabilmeli (3D yazıcı uyumlu). |
| FR-027 | **P1** | GLTF/GLB export | Game engine uyumlu GLTF formatı desteklenmeli. |
| FR-028 | **P1** | Texture export | Mesh ile birlikte texture dosyası da dışa aktarılmalı. |
| FR-029 | **P2** | FBX export | Autodesk FBX formatı desteklenmeli. |
| FR-030 | **P2** | Cloud upload | Kullanıcı modelleri doğrudan Sketchfab veya similar platformlara yükleyebilmeli. |

### 4.6 Kullanıcı Arayüzü

| ID | Öncelik | Gereksinim | Açıklama |
|----|---------|------------|----------|
| FR-031 | **P0** | Ana dashboard | Tüm işlevlere tek bir ekrandan erişim sağlanmalı. |
| FR-032 | **P0** | Progress indicator | Her işlem adımı için ilerleme çubuğu gösterilmeli (yüzde ve tahmini süre). |
| FR-033 | **P0** | Cancel button | Çalışan işlem iptal edilebilmeli. |
| FR-034 | **P0** | 3D viewer | Oluşturulan model interaktif olarak görüntülenebilmeli (rotate, zoom, pan). |
| FR-035 | **P1** | Settings panel | Thread sayısı, bellek limiti, varsayılan çözünürlük ayarlanabilmeli. |
| FR-036 | **P1** | Batch queue | Toplu işlem kuyruğu görüntülenmeli, sıralama ve öncelik değiştirilebilmeli. |
| FR-037 | **P1** | Theme support | Açık/koyu tema desteği. |
| FR-038 | **P2** | Localization | Türkçe, İngilizce, Almanca, Fransızca dil desteği. |

### 4.7 Sistem ve Performans

| ID | Öncelik | Gereksinim | Açıklama |
|----|---------|------------|----------|
| FR-039 | **P0** | Multi-threading | CPU thread sayısı yapılandırılabilir olmalı (varsayılan: tüm çekirdekler). |
| FR-040 | **P0** | Memory limit | Maksimum bellek kullanım