# IDEA-TO-PROJECT: PHASE 1 — IDEA ANALYSIS

## 📌 Temel Sorun Analizi

**Kullanıcının amacı:** CPU kullanarak 2D görselleri 3D formatına dönüştürmek

### 1. Çözülen Problem
| Problem | Açıklama |
|---------|----------|
| **Erişilebilirlik** | GPU olmayan kullanıcılar 2D→3D dönüşüm yapamıyor |
| **Maliyet** | Bulut/GPU tabanlı çözümler pahalı |
| **Gizlilik** | Fotoğrafları sunuculara yüklemek istemeyenler için yerel çözüm |
| **Hız** | Basit görseller için anlık dönüşüm ihtiyacı |

---

### 2. Hedef Kitle

```
┌─────────────────────────────────────────────────────────┐
│  ANA KİTLENİNİN %70'İ                                   │
├─────────────────────────────────────────────────────────┤
│  • Hobbyist 3D sanatçıları                               │
│  • Sosyal medya içerik üreticileri                       │
│  • Küçük işletme sahipleri (ürün görselleştirme)         │
│  • Eğitim amaçlı kullanıcılar                            │
├─────────────────────────────────────────────────────────┤
│  PROFESYONEL %30                                        │
├─────────────────────────────────────────────────────────┤
│  • Oyun geliştiricileri (hızlı prototipleme)             │
│  • E-ticaret ürün 3D görselleştirme                      │
│  • Mimari görselleştirme (eskiz→3D)                      │
└─────────────────────────────────────────────────────────┘
```

---

### 3. MVP Özellikleri (v1)

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| **Tek görsel → 3D** | PNG/JPG yükle, depth map üret, OBJ/GLTF çıktı al | 🔴 Zorunlu |
| **DepthAnything V2 entegrasyonu** | Açık kaynak depth estimation modeli | 🔴 Zorunlu |
| **CPU-only mod** | GPU gerektirmeden çalışma (optimize edilmiş) | 🔴 Zorunlu |
| **Temel format desteği** | Girdi: JPG/PNG, Çıktı: OBJ/GLTF | 🟡 Önemli |
| **Basit UI** | Drag-drop arayüzü | 🟡 Önemli |
| **İlerleme göstergesi** | Dönüşüm sürecini göster | 🟢 İsteğe bağlı |

---

### 4. Gelecek Özellikler (v2)

```
V2 ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 Video desteği      → 2D video → 3D video (anaglif/sbs)
🎨 Mesh düzenleme     → Basit mesh cleanup/edit
📱 Web API            → Backend servis olarak sunma
🔄 Toplu işleme       → 100+ görsel batch processing
🌐 WebAssembly        → Tarayıcıda CPU-only çalışma
📦 Plugin sistemi     → Blender/Unity pluginleri
```

---

### 5. Rakip Analizi

| Araç | GPU/CPU | Açık/Kapalı | Fiyat | CPU-Only Destek |
|------|---------|-------------|-------|-----------------|
| **TripoSR** | GPU | Kapalı | Freemium | ❌ |
| **Alpha3D** | GPU | Kapalı | Ücretli | ❌ |
| **DepthAnything V2** | Her ikisi | Açık | Ücretsiz | ✅ |
| **Owl3D** | GPU | Kapalı | Abonelik | ❌ |
| **IN AIR Spatial** | Özel donanım | Kapalı | Ücretli | ❌ |

**FARKLILAŞTIRICI UNSURLAR:**
- ✅ CPU-only odaklı (pazar boşluğu)
- ✅ Tam açık kaynak
- ✅ Yerel/gizlilik odaklı
- ✅ Hafif sistem gereksinimi

---

### 6. Teknik Zorluklar

```
ZORLUK SEVİYESİ: ORTA-YÜKSEK ⚡⚡⚡⚡○

┌────────────────────────────────────────────────────────────┐
│  1. PERFORMANS OPTİMİZASYONU                               │
│     → DepthAnything V2 normalde GPU'da çalışır             │
│     → CPU inference için ONNX Runtime / OpenVINO gerekli   │
│     → 1080p görsel işleme süresi: 30-60 sn (tahmini)       │
├────────────────────────────────────────────────────────────┤
│  2. DEPTH MAP KALİTESİ                                      │
│     → CPU'da model çalıştırma, kalite kaybı riski          │
│     → Edge detection ve mesh düzeltme algoritmaları         │
├────────────────────────────────────────────────────────────┤
│  3. MESH GENERASYONU                                        │
│     → Depth map → Point cloud → Mesh dönüşümü              │
│     → Poisson reconstruction veya Marching Cubes           │
├────────────────────────────────────────────────────────────┤
│  4. ÇAPRAZ PLATFORM UYUMLULUĞU                              │
│     → Windows/Mac/Linux CPU farklılıkları                  │
│     → ARM (Apple Silicon) desteği                          │
└────────────────────────────────────────────────────────────┘
```

---

### 7. Karmaşıklık Değerlendirmesi

```
KOMPLEKSİTE: ORTA ⚡⚡⚡○○

    KÜÇÜK        ORTA           BÜYÜK
      │            │              │
      ▼            ▼              ▼
    [██░░]      [████░░]      [██████]
    
    Tek katman    Çoklu         Tam
    basit script  katmanlı      enterprise
                  proje         sistem
```

---

### 8. Önerilen Tech Stack

```
┌────────────────────────────────────────────────────────────┐
│  FRONTEND                                                   │
│  ├─ PyQt6 veya Tkinter (masaüstü uygulama)                 │
│  └─ Streamlit (hızlı prototype)                            │
├────────────────────────────────────────────────────────────┤
│  BACKEND / CORE                                             │
│  ├─ Python 3.11+                                           │
│  ├─ DepthAnything V2 (depth estimation)                    │
│  ├─ Open3D veya PyVista (3D mesh işleme)                   │
│  ├─ ONNX Runtime (CPU inference optimization)              │
│  └─ OpenCV (görüntü işleme)                                │
├────────────────────────────────────────────────────────────┤
│  DAĞITIM                                                    │
│  ├─ PyInstaller (tek dosya executable)                     │
│  └─ Conda environment                                       │
└────────────────────────────────────────────────────────────┘
```

---

### 9. Sonuç & Öneriler

| Değerlendirme | Puan |
|---------------|------|
| **Pazar potansiyeli** | 7/10 |
| **Teknik uygulanabilirlik** | 8/10 |
| **Rekabet avantajı** | 9/10 |
| **MVP zaman tahmini** | 4-6 hafta |

**Karar:** Proje başlatmaya değer. CPU-only 2D→3D dönüşüm pazarında belirgin bir boşluk var ve açık kaynak DepthAnything V2 modeli güçlü bir temel sağlıyor.

---

**NEXT STEP:** Phase 2 — Architecture Design için devam ediyor muyuz?