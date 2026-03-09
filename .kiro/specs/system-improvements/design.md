# Technical Design — System Improvements

## Genel Bakış

Bu doküman, 15 requirement'ı karşılayan teknik tasarımı tanımlar. Mevcut mimari zaten güçlü bir altyapıya sahip (EventBus, TaskDelegationManager, pgvector memory, dynamic skills). Tasarım, mevcut bileşenleri genişletmeye ve eksik parçaları eklemeye odaklanır.

## Mimari Kararlar

### Mevcut Bileşenler (Genişletilecek)

- `tools/memory.py` → Gelişmiş filtreleme, tag CRUD, dedup (Req 1-3)
- `core/event_bus.py` → Zaten pub/sub, DLQ, wildcard, middleware var (Req 4)
- `core/task_delegation.py` → Priority queue, timeout, retry eklenmesi (Req 5-6)
- `core/models.py` → AgentMetrics zaten var, genişletilecek (Req 7)
- `tools/dynamic_skills.py` → 5 yeni skill tanımı (Req 10-14)

### Yeni Bileşenler

- `tools/performance_collector.py` → Metrik toplama servisi (Req 7-9)
- `backend/routes/metrics.py` → Dashboard API endpoint'leri (Req 9)
- `frontend/src/components/performance-dashboard.tsx` → Dashboard UI (Req 8)
- `backend/migrations/005_performance_metrics.sql` → Metrics tablosu (Req 7)

---

## Bileşen Tasarımları

### 1. Memory System Genişletmesi (Req 1-3)

#### 1.1 Gelişmiş Arama — `tools/memory.py`

Mevcut `recall_memory()` fonksiyonu tag ve similarity threshold destekliyor ama tarih aralığı ve çoklu filtre kombinasyonu eksik.

```python
# Yeni fonksiyon imzası
async def advanced_recall(
    query: str,
    tags: list[str] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    similarity_threshold: float = 0.5,
    memory_type: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Çoklu filtre destekli gelişmiş hafıza arama.
    Tüm filtreler AND mantığıyla birleştirilir.
    Sonuçlar: memory_id, content, tags, similarity_score, created_at
    """
```

SQL sorgusu pgvector cosine distance + WHERE koşulları:

```sql
SELECT id, content, tags, created_at,
       1 - (embedding <=> $1::vector) AS similarity_score
FROM memories
WHERE ($2::text[] IS NULL OR tags && $2::text[])
  AND ($3::timestamptz IS NULL OR created_at >= $3)
  AND ($4::timestamptz IS NULL OR created_at <= $4)
  AND ($5::text IS NULL OR memory_type = $5)
  AND 1 - (embedding <=> $1::vector) >= $6
ORDER BY similarity_score DESC
LIMIT $7
```

#### 1.2 Tag Yönetimi — `tools/memory.py`

```python
async def add_tags(memory_id: int, tags: list[str]) -> dict:
    """Tag ekle, updated_at güncelle. Return: {memory_id, tags, updated_at}"""

async def remove_tags(memory_id: int, tags: list[str]) -> dict:
    """Tag kaldır, updated_at güncelle."""

async def list_all_tags() -> list[dict]:
    """Tüm benzersiz tag'ler ve kullanım sayıları. Return: [{tag, count}]"""
```

SQL — tag ekleme:

```sql
UPDATE memories
SET tags = array_cat(tags, $2::text[]),
    updated_at = NOW()
WHERE id = $1
RETURNING id, tags, updated_at
```

#### 1.3 Deduplikasyon — `tools/memory.py`

Mevcut `save_memory()` fonksiyonuna dedup mantığı eklenir:

```python
async def save_memory_with_dedup(
    content: str,
    memory_type: str = "semantic",
    tags: list[str] | None = None,
    metadata: dict | None = None,
    dedup_threshold_skip: float = 0.85,
    dedup_threshold_update: float = 0.70,
) -> dict:
    """
    Dedup protokolü:
    - similarity >= 0.85 → SKIP, mevcut ID döndür
    - 0.70 <= similarity < 0.85 → UPDATE mevcut kayıt
    - similarity < 0.70 → INSERT yeni kayıt
    Return: {action: "skipped"|"updated"|"inserted", memory_id: int}
    """
```

TTL temizliği — mevcut `cleanup_expired_working_memory()` zaten var, cron/startup'ta çağrılacak.

---

### 2. Event Bus & Task Delegation Genişletmesi (Req 4-6)

#### 2.1 Event Bus — Zaten Mevcut

`core/event_bus.py` analizi:

- ✅ Channel-based subscribe/publish
- ✅ Wildcard pattern matching (`_resolve_subscribers`)
- ✅ DeadLetterQueue (max_size=500, FIFO eviction)
- ✅ Middleware chain
- ✅ Channel stats (subscriber count, message count, avg delivery time)
- ✅ `send_to_agent()`, `broadcast()`, `request()` (request-reply)

Eksik: Yok. Req 4 zaten karşılanıyor. Sadece agent'ların startup'ta channel'lara subscribe olması gerekiyor.

#### 2.2 Task Delegation — Priority Queue (Req 5)

Mevcut `TaskDelegationManager` analizi:

- ✅ `delegate()`, `delegate_and_wait()`, `fan_out()`
- ✅ Task cancel
- ✅ Progress tracking
- ❌ Priority queue (şu an FIFO)
- ❌ Timeout + retry

Değişiklikler `core/task_delegation.py`:

```python
# DelegatedTask modeline priority eklenmesi
class DelegatedTask(BaseModel):
    priority: int = 3  # 1-5, 1 en yüksek (YENİ)
    timeout_seconds: float | None = None  # (YENİ)
    retry_count: int = 0  # (YENİ)
    max_retries: int = 2  # (YENİ)
    queued_at: datetime = Field(default_factory=_now)  # (YENİ)
    assigned_at: datetime | None = None  # (YENİ)
    completed_at: datetime | None = None  # (YENİ)

# delegate() fonksiyonuna priority parametresi
async def delegate(self, ..., priority: int = 3, timeout_seconds: float | None = None):
    # heapq ile priority queue
    # asyncio.wait_for ile timeout
```

Priority queue implementasyonu:

```python
import heapq

# _pending_queue: list[tuple[int, float, str]]  # (priority, timestamp, task_id)
# heapq.heappush / heappop ile FIFO within same priority
```

#### 2.3 Agent İşbirliği Protokolü (Req 6)

Mevcut `fan_out()` zaten paralel dağıtım yapıyor. Eksikler:

- Partial result handling (bir agent fail olursa diğerlerinin sonuçlarını döndür)
- Handoff context transfer

`fan_out()` güncelleme:

```python
async def fan_out(self, ..., allow_partial: bool = True):
    # asyncio.gather(return_exceptions=True)
    # Başarısız olanları logla, başarılı sonuçları birleştir
```

---

### 3. Performance Collector (Req 7-9)

#### 3.1 Veritabanı Şeması — `backend/migrations/005_performance_metrics.sql`

```sql
CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent_role VARCHAR(50) NOT NULL,
    model_name VARCHAR(100),
    skill_id VARCHAR(100),
    response_time_ms FLOAT NOT NULL,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_metrics_agent_role ON agent_metrics(agent_role);
CREATE INDEX idx_metrics_recorded_at ON agent_metrics(recorded_at);
CREATE INDEX idx_metrics_agent_time ON agent_metrics(agent_role, recorded_at);
```

#### 3.2 Performance Collector — `tools/performance_collector.py`

```python
class PerformanceCollector:
    def __init__(self, pool, event_bus: EventBus | None = None):
        self._pool = pool
        self._bus = event_bus
        self._buffer: list[dict] = []  # in-memory fallback

    async def record(
        self,
        agent_role: str,
        response_time_ms: float,
        input_tokens: int,
        output_tokens: int,
        success: bool,
        model_name: str = "",
        skill_id: str = "",
        error_message: str = "",
    ) -> None:
        """Metrik kaydet. DB hatası → buffer'a yaz."""

    async def flush_buffer(self) -> int:
        """Buffer'daki metrikleri DB'ye yaz."""

    async def get_agent_summary(
        self, agent_role: str | None = None, period: str = "24h"
    ) -> list[dict]:
        """Agent bazlı özet: avg_response_time, success_rate, total_tokens, task_count"""

    async def get_system_summary(self) -> dict:
        """Sistem geneli: total_tokens, total_tasks, uptime, cost_estimate"""
```

#### 3.3 Agent Entegrasyonu — `agents/base.py`

`call_llm()` fonksiyonunun sonunda metrik kaydı:

```python
# call_llm() return'den önce:
if self._perf_collector:
    await self._perf_collector.record(
        agent_role=self.role.value,
        response_time_ms=elapsed_ms,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        success=True,
        model_name=model_used,
    )
```

#### 3.4 API Endpoint'leri — `backend/routes/metrics.py`

```python
router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/agents")
async def get_all_agent_metrics(period: str = "24h"):
    """Tüm agent'ların özet metrikleri"""

@router.get("/agents/{agent_role}")
async def get_agent_metrics(agent_role: str, period: str = "24h"):
    """Belirli agent'ın detaylı metrikleri"""

@router.get("/system")
async def get_system_metrics():
    """Sistem geneli: total_tokens, total_tasks, uptime"""
```

#### 3.5 Dashboard UI — `frontend/src/components/performance-dashboard.tsx`

React bileşeni:

- Period selector (1h / 24h / 7d)
- Agent karşılaştırma tablosu (response time, success rate, task count)
- Token kullanımı + tahmini maliyet kartı
- Success rate < 80% → kırmızı vurgulama
- 5 saniyelik polling ile güncelleme
- Dark theme uyumlu (mevcut tema sistemiyle)

---

### 4. Yeni Skill'ler (Req 10-14)

5 yeni skill, mevcut `dynamic_skills.py` üzerinden `seed_builtin_skills()` fonksiyonuna eklenir. Her skill bir system prompt + tool tanımı olarak kaydedilir.

#### Skill Tanımları

| Skill ID                | Kategori     | Açıklama                                                  |
| ----------------------- | ------------ | --------------------------------------------------------- |
| `security-audit`        | security     | OWASP Top 10 tarama, secret detection, severity raporlama |
| `data-pipeline`         | data         | ETL pipeline şeması, schema validation, format desteği    |
| `api-design`            | development  | OpenAPI 3.0 spec oluşturma, endpoint analizi              |
| `test-automation`       | testing      | pytest test generation, async support, fixture'lar        |
| `performance-profiling` | optimization | Big-O analizi, N+1 detection, index önerisi               |

Her skill `tools/dynamic_skills.py` → `seed_builtin_skills()` içinde tanımlanır:

```python
{
    "name": "security-audit",
    "description": "OWASP Top 10 güvenlik taraması, secret detection, severity raporlama",
    "category": "security",
    "version": "1.0.0",
    "source": "builtin",
    "system_prompt": "...",  # Detaylı skill prompt'u
    "knowledge": "...",      # Skill-specific bilgi tabanı
}
```

#### Skill Kayıt ve Keşif (Req 15)

Mevcut `dynamic_skills.py` zaten:

- ✅ `create_skill()` — benzersiz skill_id ile kayıt
- ✅ `search_skills()` — fuzzy search
- ✅ `list_skills()` — category filtresi
- ✅ `delete_skill()` — silme
- ❌ `input_schema` / `output_schema` alanları

Eklenmesi gereken: `input_schema` ve `output_schema` JSON alanları skills tablosuna.

```sql
ALTER TABLE skills ADD COLUMN IF NOT EXISTS input_schema JSONB DEFAULT '{}';
ALTER TABLE skills ADD COLUMN IF NOT EXISTS output_schema JSONB DEFAULT '{}';
```

---

## Veri Akışı

```
Agent.call_llm()
    ├── LLM API çağrısı
    ├── PerformanceCollector.record()  ← metrik kayıt
    │       ├── PostgreSQL INSERT
    │       └── EventBus.publish("metrics.recorded")
    └── Return response

Dashboard Frontend
    ├── GET /api/metrics/agents  (5s polling)
    ├── GET /api/metrics/system
    └── Render charts + table
```

## Bağımlılık Sırası

1. Migration (005) → DB tablosu
2. PerformanceCollector → DB'ye bağımlı
3. Agent entegrasyonu → Collector'a bağımlı
4. API routes → Collector'a bağımlı
5. Dashboard UI → API'ye bağımlı
6. Memory genişletmesi → Bağımsız
7. Task delegation genişletmesi → Bağımsız
8. Yeni skill'ler → Bağımsız
