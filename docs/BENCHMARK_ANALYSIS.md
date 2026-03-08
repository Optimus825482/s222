# Benchmark Sistemi — Detaylı Analiz

Bu dokümanda benchmark altyapısı, tespit edilen hatalar, iyileştirme önerileri ve yapılan düzeltmeler özetlenir.

---

## 1. Mimari Özet

| Katman | Dosya / Kaynak | Açıklama |
|--------|----------------|----------|
| **Senaryolar** | `tools/benchmark_suite.py` → `BENCHMARK_SCENARIOS` | 8 sabit senaryo: speed (2), quality (2), reasoning (2), tool_use (1), creativity (1) |
| **Çalıştırıcı** | `BenchmarkRunner` (aynı dosya) | `run_single`, `run_suite`, skorlama, SQLite’a yazma |
| **API** | `backend/routes/monitoring.py` | `/api/benchmarks/scenarios`, `/leaderboard`, `/results`, `/run`, `/compare`, `/history` |
| **Frontend** | `frontend/src/components/benchmark-panel.tsx` | Sıralama, Test Çalıştır, Sonuçlar, Karşılaştır sekmeleri |
| **Veri** | `data/benchmarks.db` (SQLite) | `benchmark_results` tablosu |

---

## 2. Tespit Edilen Hatalar ve Düzeltmeler

### 2.1 Backend: `_bench_runner` null iken çökme (Düzeltildi)

**Sorun:** `benchmark_suite` import hatası olduğunda `_bench_runner = None` atanıyordu; buna rağmen tüm endpoint’ler doğrudan `_bench_runner.get_leaderboard()` vb. çağırıyordu. Bu da `AttributeError: 'NoneType' object has no attribute 'get_leaderboard'` ile 500 hatasına yol açıyordu.

**Düzeltme:** Tüm benchmark endpoint’lerinden önce `_require_bench_runner()` çağrıldı; `_bench_runner is None` ise 503 ve açıklayıcı mesaj dönülüyor.

---

### 2.2 Token sayısı her zaman 0 (Düzeltildi)

**Sorun:** `agent.execute()` sadece `str` (cevap metni) döndürüyor; `output` / `tokens_used` içeren bir dict dönmüyor. Benchmark tarafında sadece dict gelirse `tokens_used` alınıyordu, bu yüzden gerçek çalıştırmalarda `tokens_used` hep 0 kalıyordu.

**Düzeltme:** `execute` tamamlandıktan sonra `thread.agent_metrics` kullanılıyor. İlgili agent için `agent_metrics.get(agent_role)` ile metrik alınıp `total_tokens` benchmark sonucuna yazılıyor. Böylece SQLite’taki `tokens_used` alanı anlamlı dolar.

---

### 2.3 Suite çalıştırmada hatalı koşu sonuçları (Kısmen)

**Sorun:** `run_suite` içinde bir senaryo exception fırlatırsa `all_results`’a sadece `{ "agent_role", "scenario_id", "error" }` ekleniyor; `score`, `latency_ms` yok. Özet istatistikler (`avg_score`, `avg_latency_ms`) yalnızca `"score" in r` olan kayıtlar üzerinden hesaplanıyor. Başarısız koşular özette “failed” sayısına yansıyor ama frontend’de tek tek hata detayı gösterilmiyor.

**Öneri:** Suite sonucu dönerken `results` içindeki `error` içeren öğeleri de UI’da (örn. “X senaryo başarısız: …”) göstermek veya özet objesine `errors: [{ agent_role, scenario_id, error }]` eklemek.

---

## 3. Geliştirilebilecek / Zayıf Noktalar

### 3.1 Skorlama mantığı (`_score_output`)

- **Substance (uzunluk):** Sadece karakter sayısına bakıyor. Çok uzun ama kaliteli cevap 3.5’ta sınırlandırılıyor; kısa ama öz cevap 4.0 alabiliyor. İsteğe bağlı iyileştirme: uzunluk bandları kategoriye göre (speed vs quality) ayrılabilir veya max cap kaldırılabilir.
- **Trait matching:** `expected_traits` içinde geçen alt string’ler aranıyor (case-insensitive). Türkçe karakter farkı (ör. “ölçeklen” vs “ölçeklendirme”) eksik eşleşmeye yol açabilir; normalizasyon veya daha esnek eşleme (token/kelime bazlı) düşünülebilir.
- **Reliability:** `[Error]`, `[Warning]`, `failed`, `timeout`, `exception` her biri −1 puan. Birden fazla geçişte skor 1’in altına inmiyor (max(..., 1.0)). Çoklu hata durumunda daha sert ceza istenirse ağırlık artırılabilir.
- **Speed:** Timeout’a oran (`latency_ms / timeout_ms`) kullanılıyor; hızlı cevap ödüllendiriliyor. Timeout’u aşan durumda zaten “Timeout” mesajı ile reliability cezalandırılıyor; ek bir “speed=0” kuralı konulabilir.

### 3.2 Senaryo / zaman aşımı

- Timeout değerleri (örn. quality 120s, tool_use 150s) önceki analizde artırıldı; ağır modellerde yine yetmeyebilir. İleride senaryo bazlı veya env üzerinden timeout override (örn. `BENCHMARK_TIMEOUT_QUALITY=180`) eklenebilir.
- `tool-use-search` web aramasına bağlı; ağ/API hatası tüm senaryoyu başarısız yapabilir. Retry veya “skip on external failure” gibi politika düşünülebilir.

### 3.3 Veri ve sorgular

- **SQLite:** Benchmark verisi `data/benchmarks.db`’de; uygulama geri kalanı PostgreSQL kullanıyorsa iki ayrı veri deposu var. Veri birleştirme veya raporlama ihtiyacı olursa migration veya senkronizasyon tasarlanmalı.
- **Tarih filtreleri:** `get_results`, `get_leaderboard`, `get_history` şu an tarih aralığı parametresi almıyor. Trend analizi için “son 7 gün”, “son 30 gün” gibi filtreler eklenebilir.
- **Leaderboard:** Tüm zamanların ortalaması alınıyor; “son N koşu” veya “son 30 gün” gibi bir kırılım yok. Karşılaştırma için zaman penceresi seçeneği faydalı olur.

### 3.4 Frontend

- **Run sonucu:** Suite çalıştırmada sonuç ham JSON olarak gösteriliyor. Özet (toplam/başarılı/başarısız, ortalama skor, ortalama gecikme) ve isteğe bağlı tek tek sonuç listesi kullanıcı deneyimini artırır.
- **Karşılaştır:** Aynı agent iki kez seçilebiliyor; “role_a === role_b” için uyarı veya butonun devre dışı bırakılması mantıklı.
- **History / trend:** `get_history` API’si var ama panelde zaman serisi (skorun zamana göre değişimi) grafiği yok; eklenebilir.
- **Progress:** “Test çalıştır” sırasında ilerleme çubuğu simüle (zamanlayıcı ile); gerçek koşu bitişine bağlı değil. Mümkünse WebSocket veya polling ile “N/M tamamlandı” gibi gerçek ilerleme gösterilebilir.

### 3.5 Agent / execute arayüzü

- `execute` şu an sadece `str` döndürüyor. İleride `{ "content": str, "tokens_used": int, "latency_ms": float }` gibi standart bir dict dönülürse hem benchmark hem diğer çağıranlar tek yerden token/süre bilgisini alabilir; şu an bu bilgi thread metriklerinden tamamlandı.

---

## 4. Özet Tablo

| Konu | Durum | Öncelik |
|------|--------|---------|
| `_bench_runner` null → 503 | Düzeltildi | — |
| `tokens_used` her zaman 0 | Düzeltildi (thread.agent_metrics) | — |
| Suite hata detayı UI’da yok | Açık | Orta |
| Skorlama: uzun cevap cezası | İyileştirme önerisi | Düşük |
| Tarih/aralık filtreleri | Öneri | Orta |
| Leaderboard zaman penceresi | Öneri | Orta |
| Run sonucu özet UI | Öneri | Orta |
| Karşılaştır: aynı agent uyarısı | Öneri | Düşük |
| History trend grafiği | Öneri | Düşük |
| Gerçek ilerleme (WS/polling) | Öneri | Düşük |

---

## 5. Yapılan Kod Değişiklikleri (Özet)

1. **backend/routes/monitoring.py**  
   - `_require_bench_runner()` eklendi; `_bench_runner` null ise 503 dönüyor.  
   - Tüm benchmark endpoint’leri bu kontrolü kullanıyor.

2. **tools/benchmark_suite.py**  
   - `run_single` içinde, `execute` bittikten sonra `tokens_used` hâlâ 0 ise `thread.agent_metrics.get(agent_role)` ile `total_tokens` alınıp sonuç kaydına yazılıyor.

Bu analiz, mevcut benchmark sisteminin durumunu ve sonraki adımlar için önerileri tek yerde toplar.
