# 🐜 Ant Colony — Karınca Kolonisi Çoklu Ajan (Multi-Agent) İş Birliği Eklentisi

> Gerçek karınca koloni ekosistemini modelleyen, özyinelemeli ve kendi kendini organize eden çoklu ajan sistemi. Uyarlanabilir eşzamanlılık, feromon tabanlı iletişim ve merkeziyetsiz zamanlama özelliklerine sahiptir.

------

## 🏗️ Mimari

Sistem, gerçek bir kolonideki iş bölümünü taklit eden farklı rollerden oluşur:

- **Kraliçe (Queen):** Ana süreç (pi süreci); hedefleri belirler ve yaşam döngüsünü yönetir.
- **🔍 İzci Karınca (Scout):** Hafif sıklet (Haiku); yolu keşfeder, kod yapısını analiz eder ve "yiyecek" (görev) kaynaklarını işaretler.
- **⚒️ İşçi Karınca (Worker):** Uygulayıcı (Sonnet); görevleri yerine getirir ve gerektiğinde alt görevler oluşturur.
- **🛡️ Asker Karınca (Soldier):** Denetleyici (Sonnet); kaliteyi kontrol eder ve gerekirse yeniden çalışma (fix) talep eder.
- **Feromon (Pheromone):** `.ant-colony/` dosya sistemi üzerinden ajanlar arası dolaylı iletişim.
- **Yuva (Nest):** Paylaşılan durum yönetimi; atomik dosya işlemleriyle süreçler arası güvenliği sağlar.

------

## 🔄 Yaşam Döngüsü

Süreç şu adımları izler:

**Hedef** → **Keşif** → **Görev Havuzu** → **İşçi Karıncaların Paralel İnfazı** → **Asker Denetimi** → **Onarım (Gerekirse)** → **Tamamlanma**

- **Feromon Uçuculuğu:** Bilgilerin güncelliğini korumak için feromonların 10 dakikalık bir yarılanma ömrü vardır.
- **Dinamik Görevler:** İş akışı sırasında otomatik olarak alt görevler üretilebilir.

------

## ⚡ Uyarlanabilir Eşzamanlılık (Adaptive Concurrency)

Gerçek karınca kolonilerindeki dinamik "işe alım" mekanizmasını simüle eder:

- **Soğuk Başlatma:** 1-2 karınca ile kademeli keşif.
- **Keşif Aşaması:** Verimlilik kırılma noktasına kadar her seferinde +1 ajan ekleme.
- **Kararlı Durum:** En iyi performans değerleri etrafında ince ayar.
- **Aşırı Yük Koruması:** CPU kullanımı > %85 veya boş bellek < 500MB ise ajan sayısını otomatik azaltma.
- **Esnek Ölçeklendirme:** Görev çoksa daha fazla ajan, azsa küçülme.

------

## 🛠️ Kullanım

### Tetikleme

Yapay zeka modeli (LLM), görevin karmaşıklığının yeterli olduğunu düşündüğünde `ant_colony` aracını otomatik olarak çağırır; manuel tetikleme gerekmez.

### Komutlar

- `/colony-stop`: Çalışan koloniyi durdurur.
- `Ctrl+Shift+A`: Karınca kolonisi detay panelini açar.

### Örnek Senaryolar

- `/colony Tüm projeyi CommonJS'den ESM'ye taşı, tüm import/export ve tsconfig yapılandırmalarını güncelle.`
- `/colony src/ altındaki tüm modüllere %80 kapsama hedefiyle birim testleri ekle.`
- `/colony Kimlik doğrulama sistemini session tabanlıdan JWT'ye taşı, API uyumluluğunu koru.`

------

## 🧬 Feromon Sistemi (Stigmergy)

Karıncalar doğrudan konuşmazlar, feromonlar aracılığıyla dolaylı iletişim kurarlar:

| **Tür**        | **Kaynak** | **Anlamı**                                        |
| -------------- | ---------- | ------------------------------------------------- |
| **discovery**  | İzci       | Keşfedilen kod yapısı ve bağımlılıklar.           |
| **progress**   | İşçi       | Tamamlanan değişiklikler, dosya modifikasyonları. |
| **warning**    | Asker      | Kalite sorunları, çakışma riskleri.               |
| **completion** | İşçi       | Görevin başarıyla bittiği işareti.                |
| **dependency** | Herhangi   | Dosyalar arası bağımlılık ilişkileri.             |

------

## 🔒 Dosya Kilitleme

Her görev, üzerinde işlem yapacağı dosyaları beyan eder. Kraliçe şunları garanti eder:

1. Bir dosya aynı anda sadece tek bir karınca tarafından değiştirilebilir.
2. Dosya çakışması olan görevler otomatik olarak `blocked` (engellendi) şeklinde işaretlenir ve kilit açıldığında devam eder.

------

## 📂 Modül Yapısı ve Dosya Sorumlulukları

| **Dosya**        | **Satır** | **Sorumluluk**                                             |
| ---------------- | --------- | ---------------------------------------------------------- |
| `types.ts`       | 117       | Karıncalar, görevler ve feromonlar için tip tanımlamaları. |
| `nest.ts`        | 196       | Paylaşılan durum, atomik okuma/yazma ve feromon yönetimi.  |
| `concurrency.ts` | 115       | Sistem örnekleme ve eşzamanlılık ayarlama.                 |
| `spawner.ts`     | 316       | Karınca süreç yönetimi ve çıktı analizi.                   |
| `queen.ts`       | 331       | Yaşam döngüsü planlama ve yineleme yönetimi.               |
| `index.ts`       | 324       | Eklenti girişi, araç kaydı ve arayüz (TUI) görselleştirme. |