# Implementation Tasks — System Improvements

## Task 1: Performance Metrics DB Migration

- [x] `backend/migrations/005_performance_metrics.sql` oluştur
- [x] `agent_metrics_log` tablosu: id, agent_role, model_name, skill_id, response_time_ms, input_tokens, output_tokens, total_tokens, success, error_message, recorded_at, metadata (JSONB)
- [x] Index'ler: agent_role, recorded_at, (agent_role + recorded_at) composite
- [x] `skills` tablosuna `input_schema JSONB` ve `output_schema JSONB` kolonları ekle (ALTER TABLE)
- [x] Migration'ı `backend/main.py` lifespan'de çalıştır

### Requirements: 7, 15

### Design Reference: §3.1, §4

---

## Task 2: Performance Collector Service

- [x] `tools/performance_collector.py` oluştur
- [x] `PerformanceCollector` class: pool + event_bus dependency injection
- [x] `record()` metodu: agent_role, response_time_ms, tokens, success, model_name, skill_id kaydet
- [x] DB hatası durumunda in-memory `_buffer` listesine fallback
- [x] `flush_buffer()` metodu: buffer'daki metrikleri DB'ye batch INSERT
- [x] `get_agent_summary(agent_role, period)` metodu: avg_response_time, success_rate, total_tokens, task_count döndür
- [x] `get_system_summary()` metodu: total_tokens, total_tasks, uptime, cost_estimate döndür
- [x] EventBus üzerinden `metrics.recorded` event'i publish et
- [x] `backend/main.py` lifespan'de collector instance oluştur ve `shared_state`'e kaydet

### Requirements: 7, 9

### Design Reference: §3.2

---

## Task 3: Agent Base — Performance Collector Entegrasyonu

- [x] `agents/base.py` → `__init__` içinde `_perf_collector` referansı ekle (lazy, shared_state'den)
- [x] `call_llm()` fonksiyonunun başarılı return'ünden önce `_perf_collector.record()` çağır
- [x] `call_llm()` exception handler'ında `success=False` ile `record()` çağır
- [x] Elapsed time hesaplaması: `time.perf_counter()` ile start/end
- [x] Token bilgisi: response `usage` dict'inden `prompt_tokens`, `completion_tokens` al

### Requirements: 7

### Design Reference: §3.3

---

## Task 4: Metrics API Endpoints

- [x] `backend/routes/metrics.py` oluştur
- [x] `GET /api/metrics/agents` → tüm agent'ların özet metrikleri (period query param: 1h|24h|7d)
- [x] `GET /api/metrics/agents/{agent_role}` → belirli agent detaylı metrikleri
- [x] `GET /api/metrics/system` → toplam token, görev sayısı, uptime
- [x] Geçersiz agent_role → 404 + açıklayıcı hata mesajı
- [x] Router'ı `backend/main.py`'da register et

### Requirements: 9

### Design Reference: §3.4

---

## Task 5: Performance Dashboard UI

- [x] `frontend/src/components/performance-dashboard.tsx` oluştur
- [x] Period selector: 1h / 24h / 7d butonları
- [x] Agent karşılaştırma tablosu: agent_role, avg_response_time, success_rate, task_count, total_tokens
- [x] Success rate < 80% → satırı kırmızı vurgula
- [x] Sistem özet kartları: toplam token, tahmini maliyet, toplam görev
- [x] 5 saniyelik polling ile otomatik güncelleme (useEffect + setInterval)
- [x] Dark theme uyumlu (mevcut CSS variables kullan)
- [x] Dashboard'u sidebar navigation'a ekle

### Requirements: 8

### Design Reference: §3.5

---

## Task 6: Memory — Gelişmiş Arama

- [x] `tools/memory.py` → `advanced_recall()` fonksiyonu ekle
- [x] Parametreler: query, tags, date_from, date_to, similarity_threshold, memory_type, limit
- [x] pgvector cosine distance + WHERE koşulları (AND mantığı)
- [x] Boş query → ValidationError raise et
- [x] Return format: memory_id, content, tags, similarity_score, created_at
- [x] Sonuçlar similarity_score DESC sıralı
- [x] Agent tool tanımına `memory_advanced_search` ekle (`agents/base.py` handle_tool_call)

### Requirements: 1

### Design Reference: §1.1

---

## Task 7: Memory — Tag Yönetimi

- [x] `tools/memory.py` → `add_tags(memory_id, tags)` fonksiyonu
- [x] `tools/memory.py` → `remove_tags(memory_id, tags)` fonksiyonu
- [x] `tools/memory.py` → `list_all_tags()` fonksiyonu: benzersiz tag'ler + kullanım sayısı
- [x] Var olmayan memory_id → "memory not found" hatası
- [x] Tag işlemlerinde `updated_at` alanını güncelle
- [x] Agent tool tanımına `memory_add_tags`, `memory_remove_tags`, `memory_list_tags` ekle

### Requirements: 2

### Design Reference: §1.2

---

## Task 8: Memory — Deduplikasyon

- [x] `tools/memory.py` → `save_memory_with_dedup()` fonksiyonu
- [x] Yeni kayıt öncesi mevcut kayıtlarla cosine similarity hesapla
- [x] similarity >= 0.85 → SKIP, mevcut ID döndür
- [x] 0.70 <= similarity < 0.85 → UPDATE mevcut kayıt
- [x] similarity < 0.70 → INSERT yeni kayıt
- [x] Return: `{action: "skipped"|"updated"|"inserted", memory_id: int}`
- [x] Mevcut `save_memory()` çağrılarını `save_memory_with_dedup()` ile değiştir (opt-in flag)
- [x] `cleanup_expired_working_memory()` fonksiyonunu startup'ta çağır

### Requirements: 3

### Design Reference: §1.3

---

## Task 9: Task Delegation — Priority Queue & Timeout

- [x] `core/task_delegation.py` → `DelegatedTask` modeline `priority`, `timeout_seconds`, `retry_count`, `max_retries`, `queued_at`, `assigned_at`, `completed_at` alanları ekle
- [x] `delegate()` fonksiyonuna `priority: int = 3` ve `timeout_seconds: float | None` parametreleri ekle
- [x] `heapq` ile priority queue implementasyonu (aynı priority → FIFO)
- [x] `asyncio.wait_for()` ile timeout desteği
- [x] Timeout → `timed_out` status + retry mekanizması (max_retries'a kadar)
- [x] İptal edilen görev → kuyruktan kaldır + EventBus'a `task.cancelled` event'i publish et
- [x] `get_stats()` fonksiyonuna ortalama bekleme süresi ekle

### Requirements: 5, 6

### Design Reference: §2.2

---

## Task 10: Fan-out — Partial Result Handling

- [x] `core/task_delegation.py` → `fan_out()` fonksiyonuna `allow_partial: bool = True` parametresi ekle
- [x] `asyncio.gather(return_exceptions=True)` ile paralel çalıştır
- [x] Başarısız görevleri logla, başarılı sonuçları birleştir
- [x] Handoff context transfer: `Event_Bus.send_to_agent()` ile mevcut context'i hedef agent'a aktar
- [x] `get_stats()` fonksiyonuna aktif/tamamlanan görev sayısı ve ortalama tamamlanma süresi ekle

### Requirements: 6

### Design Reference: §2.3

---

## Task 11: Yeni Skill'ler — Seed Tanımları

- [x] `tools/dynamic_skills.py` → `seed_builtin_skills()` fonksiyonuna 5 yeni skill ekle
- [x] `security-audit`: OWASP Top 10 tarama, secret detection, severity raporlama system prompt'u
- [x] `data-pipeline`: ETL pipeline şeması, schema validation, format desteği system prompt'u
- [x] `api-design`: OpenAPI 3.0 spec oluşturma, endpoint analizi system prompt'u
- [x] `test-automation`: pytest test generation, async support, fixture system prompt'u
- [x] `performance-profiling`: Big-O analizi, N+1 detection, index önerisi system prompt'u
- [x] Her skill için category, version, knowledge alanlarını doldur

### Requirements: 10, 11, 12, 13, 14

### Design Reference: §4

---

## Task 12: Skill Registry — Schema Desteği

- [x] `tools/dynamic_skills.py` → `create_skill()` fonksiyonuna `input_schema` ve `output_schema` parametreleri ekle
- [x] `search_skills()` fonksiyonunda fuzzy search'ü description + name üzerinde genişlet
- [x] `list_skills()` fonksiyonunda category filtresi zaten var — doğrula
- [x] `delete_skill()` fonksiyonunda disk dosyalarını da temizle (zaten var — doğrula)
- [x] Round-trip property: skill kaydet → oku → aynı yapı kontrolü

### Requirements: 15

### Design Reference: §4

---

## Task 13: Agent Channel Subscriptions

- [x] Her agent'ın `__init__` veya startup'ında ilgili channel'lara subscribe olmasını sağla
- [x] Orchestrator: `task.*`, `metrics.*` channel'larına subscribe
- [x] Diğer agent'lar: `task.{role}`, `broadcast` channel'larına subscribe
- [x] EventBus channel stats'ı doğrula (subscriber count, message count, avg delivery time)

### Requirements: 4

### Design Reference: §2.1
