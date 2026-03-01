# 📄 MULTI-AGENT SİSTEM PROJESİ — ÜRÜN GEREKSİNİMLERİ DOKÜMANI (PRD)

---

## 1. PROJE TANIMI VE VİZYON

### 1.1 Proje Adı
**Proje Adı:** **AGENTIX** — Kurumsal Çoklu-Ajan İş Otomasyonu Platformu

### 1.2 One-Liner
> AGENTIX, karmaşık iş süreçlerini otonom ajanlar aracılığıyla otomatikleştiren, insan denetimi altında ölçeklenebilir ve güvenli bir çoklu-ajan iş birliği platformudur.

### 1.3 Vizyon
2027 yılına kadar Türkiye'nin önde gelen kurumlarının %30'unun operasyonel verimliliğini AGENTIX ile artırmak; yapay zeka destekli iş otomasyonunda referans noktası olmak.

---

## 2. PROBLEM TANIMI

### 2.1 Pazar Problemi

Günümüzde kurumlar, artan işlem hacmi ve karmaşıklaşan süreçlerle karşı karşıyadır. Geleneksel otomasyon çözümleri—RPA botları, tekil chatbot'lar, basit iş akışı araçları—bu karmaşıklığı yönetmekte yetersiz kalmaktadır. Birden fazla sistem arasında koordinasyon gerektiren görevler, hâlâ yoğun insan müdahalesine bağımlıdır ve bu durum hem maliyetleri artırmakta hem de ölçeklenebilirliği sınırlandırmaktadır.

### 2.2 Spesifik Problemler

| # | Problem | Etki | Mevcut Çözümün Yetersizliği |
|---|---------|------|----------------------------|
| **P1** | Tek ajanların sınırlı yetkinliği | Bir yapay zeka asistanı hem araştırma yapıp hem kod yazıp hem de stratejik karar veremez; bu da görev tamamlama süresini uzatır ve kaliteyi düşürür | Mevcut chatbot'lar ve tekil AI asistanları silo yapıda çalışır, görevler arası geçişte bağlam kaybeder |
| **P2** | Dağıtık sistemlerde koordinasyon başarısızlığı | Farklı departmanların sistemleri arasında veri akışı kesintilere uğrar, tutarsızlıklar oluşur | API entegrasyonları manuel olarak yönetilir, hata toleransı düşüktür |
| **P3** | İnsan-Ajan etkileşim kopukluğu | Kritik kararlarda otomatik sistemlerin ürettiği sonuçlar güvenilir bulunmaz, sürekli insan doğrulaması gerekir | Mevcut sistemlerde "human-in-the-loop" mekanizmaları ya yoktur ya da çok kaba granülaritede çalışır |
| **P4** | Ölçeklenebilirlik ve kaynak optimizasyonu dengesizliği | Yoğun dönemlerde sistem yanıt süreleri uzar, düşük dönemlerde kaynaklar boşa harcanır | Geleneksel sunucu altyapısı dinamik ölçeklendirmeyi desteklemez |

### 2.3 Problem İstatistikleri

Kurumların %78'i en az bir iş sürecinde yapay zeka kullanırken, bu kullanımın yalnızca %23'ü çoklu ajan koordinasyonunu içermektedir. Tek ajanlı sistemlerde ortalama görev tamamlama süresi karmaşık işlerde 4.2 saat iken, çoklu ajan sistemlerinde bu süre 47 dakikaya düşmektedir. Ancak mevcut çözümlerin %65'i kurumsal güvenlik gereksinimlerini tam olarak karşılayamamaktadır.

---

## 3. HEDEF KULLANICILAR VE PERSONA

### 3.1 Birincil Hedef Kitle

**Kurumsal Karar Vericiler** segmenti, AGENTIX'in birincil müşteri kitlesini oluşturmaktadır. Bu kullanıcılar operasyonel müdürler, dijital dönüşüm liderleri ve IT direktörlerinden oluşur. Temel motivasyonları iş süreçlerini otomatize ederek maliyet düşürmek, hız artırmak ve insan hatasını minimize etmektir. Karar döngüleri 3-6 ay arasında değişir ve satın alma kararlarında ROI hesaplamaları belirleyici rol oynar.

**Yazılım Geliştirme Takımları** ikinci kritik kullanıcı grubunu temsil etmektedir. DevOps mühendisleri, backend geliştiricileri ve AI/ML uzmanları bu kategoridedir. Onlar için kritik olan noktalar mevcut sistemlere kolay entegrasyon, detaylı dokümantasyon ve hata ayıklama araçlarının zenginliğidir. AGENTIX'i kendi projelerine entegre ederken minimal öğrenme eğrisi ve güçlü SDK desteği beklerler.

### 3.2 Detaylı Persona Profilleri

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PERSONA 1: AHMET — KURUMSAL IT DİREKTÖRÜ                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Yaş: 42  |  Şirket: 500+ çalışanlı finansal hizmetler şirketi              │
│                                                                             │
│  Hedefleri:                                                                  │
│  • Yıllık operasyonel maliyetları %25 azaltmak                               │
│  • IT ekibinin stratejik işlere odaklanmasını sağlamak                       │
│  • Regülasyon uyumluluğunu dijital araçlarla güçlendirmek                    │
│                                                                             │
│  Korkuları:                                                                  │
│  • Veri ihlali ve güvenlik açıkları                                          │
│  • Tedarikçi bağımlılığı (vendor lock-in)                                    │
│  • Ekibin yeni teknolojiye adaptasyon zorluğu                                │
│                                                                             │
│  Başarı Kriteri: 6 ay içinde ROI kanıtlanması, 18 ayda tam geri ödeme        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  PERSONA 2: ELİF — YAZILIM MİMARİ                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  Yaş: 31  |  Şirket: E-ticaret startup'ı (120 çalışan)                      │
│                                                                             │
│  Hedefleri:                                                                  │
│  • Mevcut mikroservis mimarisine non-invaziv entegrasyon                     │
│  • Hızlı prototipleme ve iteratif geliştirme                                 │
│  • Açık kaynak ekosistemi ile uyumluluk                                      │
│                                                                             │
│  Korkuları:                                                                  │
│  • "Black box" sistemler ve debug zorluğu                                    │
│  • Aşırı vendor abstraction katmanları                                       │
│  • Performans overhead ve gecikme                                              │
│                                                                             │
│  Başarı Kriteri: POC'un 2 hafta içinde çalışır hale gelmesi                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  PERSONA 3: MEHMET — VERİ ANALİSTİ                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Yaş: 28  |  Şirket: Büyük perakende zinciri                                │
│                                                                             │
│  Hedefleri:                                                                  │
│  • Karmaşık veri setlerinden otomatik içgörü üretimi                         │
│  • Self-servis analitik yetenekleri                                          │
│  • Raporlama süreçlerinin otomasyonu                                         │
│                                                                             │
│  Korkuları:                                                                  │
│  • Yanlış veya yanıltıcı AI çıktıları (hallucination)                        │
│  • Veri kalitesi ve tutarlılık sorunları                                     │
│  • Teknik olmayan kullanıcılar için karmaşık arayüzler                       │
│                                                                             │
│  Başarı Kriteri: Manuel raporlama süresinde %80 azalma                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Kullanıcı Yolculuğu Haritası

Kullanıcı yolculuğu dört ana fazdan oluşmaktadır. Keşif fazında kullanıcı platformu web sitesi ve demo üzerinden tanır, dokümantasyonu inceler ve ücretsiz deneme başlatır. Onboarding fazında API anahtarı alır, ilk ajanını konfigüre eder ve basit bir görev pipeline'ı oluşturur. Entegrasyon fazında mevcut sistemlere bağlanır, özel araçlarını tanımlar ve iş süreçlerini haritalandırır. Optimizasyon fazında ise ajan davranışlarını ince ayarlar, performans metriklerini izler ve sürekli iyileştirme döngüsüne girer.

---

## 4. FONKSİYONEL GEREKSİNİMLER

### 4.1 Önceliklendirme Metodolojisi

Gereksinimler üç seviyede önceliklendirilmiştir. **P0 (Critical)** gereksinimler MVP lansmanı için zorunludur; bunlar olmadan ürün çalışamaz. **P1 (High)** gereksinimler ilk sürümde olmalıdır; kullanıcı deneyimini önemli ölçüde etkiler. **P2 (Medium)** gereksinimler sonraki sürümlerde eklenebilir; iyileştirici niteliktedir.

### 4.2 P0 — Kritik Gereksinimler

**FR-001: Çoklu-Ajan Orkestrasyon Motoru**

Sistem, en az 4 farklı uzmanlık alanına sahip ajanın eşzamanlı çalışmasını koordine edebilmelidir. Orkestratör, görevleri dinamik olarak ajanlara dağıtmalı, ajanlar arası mesajlaşmayı yönetmeli ve bağımlılık ilişkilerini takip etmelidir. Herhangi bir ajanın başarısız olması durumunda sistem alternatif yollar denemeli veya görevi yeniden atamalıdır. Tolerans kriteri olarak tek nokta arızası (single point of failure) bulunmamalıdır.

**FR-002: Görev Tanımlama ve Parçalama**

Kullanıcılar doğal dilde görev tanımlayabilmeli ve sistem bu görevi otomatik olarak alt görevlere ayırmalıdır. Görev ağacı (task tree) görselleştirmesi sağlanmalı ve kullanıcı paralel çalışabilecek görevleri işaretleyebilmelidir. Her alt görev için bağımlılık grafiği otomatik oluşturulmalı, deadlock durumları önlenmelidir.

**FR-003: Harici API ve Araç Entegrasyonu**

Sistem, RESTful API'leri, GraphQL endpoint'lerini ve veritabanı bağlantılarını standart formatta tanımlayabilmelidir. Her ajan, görev sırasında harici araçları çağırabilmeli ve sonuçları entegre edebilmelidir. API çağrıları için retry logic, timeout yönetimi ve circuit breaker mekanizmaları yerleşik olmalıdır.

**FR-004: Güvenlik ve Erişim Kontrolü**

Çok katmanlı rol bazlı erişim kontrolü (RBAC) uygulanmalıdır. Kullanıcılar, ajanlar ve sistem bileşenleri için ayrı yetkilendirme seviyeleri tanımlanmalıdır. Tüm veri aktarımları TLS 1.3 ile şifrelenmeli, bekleyen veri AES-256 ile korunmalıdır. Audit logları değiştirilemez (immutable) formatta saklanmalı ve KVKK/GDPR uyumluluğu sağlanmalıdır.

**FR-005: İnsan-in-the-Loop Onay Mekanizması**

Kritik karar noktalarında sistem otomatik olarak insan onayı beklemelidir. Onay talepleri gerçek zamanlı olarak ilgili kullanıcılara iletilmelidir. Onay verilene kadar görev askıda kalmalı, reddedildiğinde alternatif akış tetiklenmelidir. Onay gecikmesi durumunda eskalasyon mekanizması çalışmalıdır.

### 4.3 P1 — Yüksek Öncelikli Gereksinimler

**FR-006: Hafıza ve Bağlam Yönetimi**

Sistem, kısa süreli hafızada mevcut görev için geçici veri, uzun süreli hafızada ise kalıcı öğrenilmiş bilgileri saklamalıdır. Semantic search yetenekleri ile geçmiş görevlerden ilgili bilgiler geri çağırılabilmelidir. Ajanlar arası paylaşımlı bağlam (shared context) mekanizması çalışmalıdır. Hafıza boyutu ve yaşam döngüsü konfigüre edilebilir olmalıdır.

**FR-007: RAG (Retrieval-Augmented Generation) Entegrasyonu**

Kurumsal dokümanlar ve bilgi tabanları sisteme yüklenebilmeli, ajanlar bu içeriklerden gerçek zamanlı olarak bilgi çekebilmelidir. Vector database entegrasyonu ile semantik arama yetenekleri sağlanmalıdır. Farklı kaynaklardan gelen bilgiler tutarlı bir şekilde birleştirilmelidir.

**FR-008: Gerçek Zamanlı İzleme ve Dashboard**

Tüm ajan aktiviteleri, görev durumları ve sistem metrikleri canlı olarak izlenebilmelidir. Görsel dashboard üzerinden sistem sağlığı, performans ve hata oranları takip edilmelidir. Özelleştirilebilir uyarı (alert) mekanizması ile anormal durumlar otomatik bildirilmelidir.

**FR-009: Çoklu Dil Desteği**

Sistem arayüzü, dokümantasyonu ve ajan etkileşimleri Türkçe dahil en az 5 dilde çalışabilmelidir. Dil algılama ve otomatik çevirme yetenekleri yerleşik olmalıdır. Kullanıcı tercihlerine göre ajan yanıt dili özelleştirilebilir olmalıdır.

**FR-010: Olay Tabanlı Tetikleme (Event-Driven Triggers)**

Belirli olaylar gerçekleştiğinde otomatik görev başlatma yeteneği sağlanmalıdır. Webhook entegrasyonları ile dış sistemlerden tetikleme yapılabilmelidir. Zamanlanmış (scheduled) görevler ve tekrarlayan iş akışları tanımlanabilmelidir.

### 4.4 P2 — Orta Öncelikli Gereksinimler

**FR-011: Self-Learning ve Adaptasyon**

Sistem, geçmiş görev sonuçlarından öğrenerek ajan