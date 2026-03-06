# Backend ve API Katmanı Analiz Raporu

**Tarih:** 2025-03-06  
**Kapsam:** API yapısı, veritabanı, auth, hata/validasyon/güvenlik, tip güvenliği, eksikler ve hatalar.

---

## 1. API Rotaları, Controller ve Servis Yapısı

### 1.1 Genel Yapı

- **Tek dosya backend:** Tüm REST ve WebSocket mantığı `backend/main.py` içinde (≈960 satır).
- **Katman yok:** Controller → Service → Repository ayrımı yok; endpoint’ler doğrudan `core.state`, `tools.rag`, `tools.dynamic_skills`, `tools.mcp_client`, `tools.memory`, `tools.teachability`, `tools.idea_to_project`, `tools.export_service`, `tools.presentation_service` çağırıyor.
- **Pattern:** Her endpoint ya doğrudan import edilen fonksiyonu çağırıyor ya da (proje/sunum/export) dosya sistemi + yardımcı modül kullanıyor.

### 1.2 Endpoint Özeti

| Grup | Örnek Rotalar | Dosya |
|------|----------------|--------|
| Auth | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` | `backend/main.py` 150–181 |
| Config | `GET /api/models`, `GET /api/pipelines`, `GET /api/health` | 186–198, 583–586 |
| Threads | `GET/POST/DELETE /api/threads`, `GET/DELETE /api/threads/{id}` | 202–234 |
| RAG | `POST /api/rag/ingest`, `POST /api/rag/query`, `GET /api/rag/documents` | 238–258 |
| Skills | `GET/POST /api/skills`, `GET/DELETE /api/skills/{id}`, `GET /api/skills/auto`, `POST /api/skills/migrate` | 261–323 |
| MCP | `GET/POST /api/mcp/servers`, `GET /api/mcp/servers/{id}/tools`, `POST /api/mcp/seed` | 326–364 |
| Teachability | `GET/POST /api/teachability` | 367–380 |
| Eval | `GET /api/eval/stats` | 383–389 |
| Memory | `GET /api/memory/stats`, `GET /api/memory/layers`, `DELETE /api/memory/{id}` | 394–420 |
| DB | `GET /api/db/health` | 423–435 |
| Projects | `GET /api/projects`, `GET /api/projects/{name}/export`, `GET .../export/pdf` | 439–545 |
| Presentations | `POST /api/presentation/generate`, `GET /api/presentations`, `GET .../download`, `GET .../pdf` | 451–466, 548–726 |
| Export | `POST /api/export/pdf`, `POST /api/export/html` | 529–768 |
| WebSocket | `WS /ws/chat` | 823–578 |

**Öneri:** Uzun vadede route’ları router’lara böl (auth, threads, rag, skills, mcp, memory, projects, presentations, export), servis katmanını ayrı modüllerde topla; test ve bakım kolaylaşır.

---

## 2. Veritabanı Kullanımı

### 2.1 ORM ve Bağlantı

- **ORM yok:** Ham SQL, `psycopg2` (ThreadedConnectionPool) + `psycopg2.extras.RealDictCursor`.
- **Modül:** `tools/pg_connection.py` — pool (min 1, max 10), `get_conn()`, `release_conn()`, `db_conn()` context manager.
- **Config:** `config.py` içinde `DATABASE_URL` (varsayılan: `postgresql://agent:agent_secret_2024@localhost:5432/multiagent`).

```12:17:backend/../tools/pg_connection.py
from config import DATABASE_URL
// ...
_pool: psycopg2.pool.ThreadedConnectionPool | None = None
```

- **Lifespan:** `main.py` lifespan’da `init_database()` çağrılıyor; PG yoksa uygulama yine de ayağa kalkıyor (SQLite fallback başka modüllerde).

### 2.2 Şema ve Migrasyon

- **Şema:** `tools/pg_connection.py` içinde `_SCHEMA_SQL` (CREATE EXTENSION vector; memories, teachings, documents, chunks, skills tabloları + indeksler).
- **Migrasyon:** `init_database()` ile CREATE IF NOT EXISTS ve `ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id` çalıştırılıyor. Versiyonlu (up/down) migration yok.
- **SQLite → PG:** `migrate_from_sqlite()` (data/memory.db, teachings.db, rag.db, dynamic_skills.db) `POST /api/skills/migrate` ile tetikleniyor.

**Eksikler:** Resmi migration versiyonu yok; şema değişiklikleri elle SQL ile yapılıyor. İleride Alembic veya benzeri düşünülebilir.

### 2.3 Thread Persistence (ORM Değil)

- **Thread’ler:** Veritabanında değil, JSON dosyalarında. `core/state.py`: `data/threads/` (opsiyonel `data/threads/{user_id}/`), `save_thread`, `load_thread`, `list_threads`, `delete_thread`, `delete_all_threads`.

---

## 3. Kimlik Doğrulama ve Yetkilendirme

### 3.1 Mevcut Auth

- **Kullanıcılar:** `backend/main.py` içinde sabit sözlük:

```72:83:backend/main.py
USERS = {
    "erkan": {
        "password_hash": hashlib.sha256("518518".encode()).hexdigest(),
        ...
    },
    "yigit": { ... },
}
```

- **Token:** `secrets.token_hex(32)`, bellekte `_active_tokens: dict[str, str]` (token → user_id). Sunucu yeniden başlayınca tüm oturumlar düşer.
- **Login/Logout/Me:**  
  - `POST /api/auth/login` → token + user_id + full_name.  
  - `POST /api/auth/logout` → Header’dan token alınmalı ama parametre `authorization: str = ""` ile alınıyor; FastAPI bunu otomatik Header’a bağlamaz, client’ın `Authorization: Bearer <token>` göndermesi gerekir.  
  - `GET /api/auth/me` → aynı şekilde token bekleniyor.

### 3.2 Kritik: REST Endpoint’lerde Auth Zorunlu Değil

- **Hiçbir REST endpoint** token kontrolü yapmıyor. `/api/auth/me` hariç Authorization kullanılmıyor.
- **user_id** tamamen client’tan geliyor: query (`?user_id=`) veya body (RAG, WebSocket). Kimliği doğrulanmış kullanıcı ile eşleştirme yok.
- **Sonuç:** İsteyen herkes başka bir `user_id` ile thread’leri, RAG dokümanlarını listeleyebilir/silebilir; memory silinebilir; skills/MCP/teachability herkese açık.

### 3.3 WebSocket

- `/ws/chat` auth kontrolü yapmıyor; mesajdaki `user_id` doğrudan kullanılıyor.

**Öneri:**  
- Tüm veri taşıyan endpoint’lerde (threads, RAG, memory, skills, teachability, proje/sunum listesi vb.) token zorunlu olsun.  
- `user_id` sadece token’dan (örn. `_get_user_from_token`) alınsın; client’tan gelen `user_id` kullanılmasın veya sadece token’daki ile aynıysa kabul edilsin.  
- Logout’ta `Authorization` header’ı `Header(None)` veya `Header(..., alias="Authorization")` ile alınsın.

---

## 4. Hata Yönetimi, Validasyon ve Güvenlik

### 4.1 Hata Yönetimi

- **Merkezi exception handler yok.** Her endpoint kendi `try/except`’i ile 503/404 atıyor; iç hata mesajları bazen client’a gidiyor (örn. `f"Skills module error: {e}"`), bu da bilgi sızıntısı riski.
- **Örnek:**

```299:301:backend/main.py
    except Exception as e:
        raise HTTPException(503, f"Skills module error: {e}")
```

**Öneri:** Production’da genel handler ile 503’te sabit mesaj dönün; detayı sadece loglayın.

### 4.2 Validasyon

- **Pydantic request modelleri var:** LoginRequest, ChatRequest, SkillCreateRequest, RAGIngestRequest, RAGQueryRequest, MCPServerRequest, TeachRequest, PresentationRequest, ExportPdfRequest, ExportHtmlRequest.
- **Eksikler:**  
  - `skill_id`, `name`, `content`, `query`, `url` vb. için `max_length`, `min_length`, pattern yok.  
  - `limit` (thread list) üst sınırı yok (örn. 100).  
  - MCP `url` formatı kontrol edilmiyor.  
  - `memory_id` (path) sadece `int`; negatif veya çok büyük değerler için ek kısıt yok.

**Öneri:** Özellikle dışarıdan gelen string’lerde `Field(..., max_length=...)`, gerekirse `regex` veya `HttpUrl` kullanın.

### 4.3 Güvenlik

**Şifre:**

- SHA256 ile hash (tuz yok, tek yönlü ama hızlı kırılabilir):

```155:156:backend/main.py
    expected = hashlib.sha256(req.password.encode()).hexdigest()
    if user["password_hash"] != expected:
```

**Öneri:** En azından bcrypt veya argon2 + tuz kullanın; şifreleri kod içinde saklamayın, env veya güvenli secret store’dan alın.

**CORS:**

```61:67:backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    ...
)
```

- `allow_origins=["*"]` her origin’e izin veriyor. Production’da belirli origin’lerle kısıtlayın.

**Rate limiting:** Yok. Login ve ağır endpoint’lere brute-force / DoS riski var.  
**Öneri:** slowapi veya benzeri ile rate limit (özellikle login ve export/presentation).

**Path traversal:**

- Proje export: `project_dir = PROJECTS_DIR / project_name` — `project_name` içinde `..` olursa dizin dışına çıkılabilir. Sadece `project_dir.exists()` kontrolü var, `resolve()` ile base path’e göre kısıt yok.

```473:477:backend/main.py
@app.get("/api/projects/{project_name}/export")
async def api_export_project(project_name: str):
    ...
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")
```

- Sunum/Resim indirme: `filepath = pres_dir / filename` ve `filepath = images_dir / filename` — `filename` ile `..` verilirse yine path traversal mümkün.

**Öneri:**  
- `project_dir = (PROJECTS_DIR / project_name).resolve()` sonrası `not project_dir.is_relative_to(PROJECTS_DIR.resolve())` ise 404.  
- `filepath = (pres_dir / filename).resolve()`; `not filepath.is_relative_to(pres_dir.resolve())` veya `filename != filepath.name` ise 404.  
- `filename` için sadece basit karakterler (örn. `[a-zA-Z0-9_.-]+`) kabul edilebilir.

**SQL injection:**  
- `tools/rag.py`, `tools/memory.py`, `tools/dynamic_skills.py` parametreli sorgu (`%s`) kullanıyor.  
- `dynamic_skills.py` içinde `set_clause` sadece `allowed` key’lerinden oluşturuluyor; injection riski yok.

**Özet:** En büyük riskler: auth’sız endpoint’ler, path traversal, zayıf şifre hashi, CORS ve rate limit eksikliği.

---

## 5. Tip Güvenliği, Paylaşılan Tipler, DTO ve Validasyon Şemaları

### 5.1 Paylaşılan tipler

- **Backend:** `core/models.py` (Thread, Event, Task, SubTask, AgentRole, PipelineType, EventType, TaskStatus, AgentMetrics). Pydantic modelleri.
- **Frontend:** `frontend/src/lib/types.ts` — ModelConfig, ThreadSummary, Thread, AgentEvent, Task, SubTask, WS mesaj tipleri vb.
- **Ortak paket yok:** Backend (Python/Pydantic) ile frontend (TypeScript) ayrı tanımlar; API contract (OpenAPI) üzerinden senkron tutulmuyor. İsim ve alan uyumsuzlukları olabilir.

### 5.2 DTO / response modelleri

- Backend’de açık “response model” kullanımı az: çoğu endpoint `return` ile dict veya Pydantic `.model_dump(mode="json")` döndürüyor.  
- `ThreadSummary` modeli var ama `list_threads` dict listesi döndürüyor; tip olarak `list[ThreadSummary]` zorunlu değil.

### 5.3 Validasyon şemaları

- Request body Pydantic ile parse ediliyor; ek alan kısıtları (uzunluk, regex) yok (yukarıda belirtildi).

**Öneri:** OpenAPI (FastAPI’nin ürettiği) schema’yı export edip frontend’de client/tipler üretmek (openapi-typescript vb.) veya ortak bir API contract (ör. OpenAPI YAML) ile iki tarafta tutarlılık sağlanabilir.

---

## 6. Eksik / Yarım Kalanlar, Hatalar ve Güvenlik Açıkları

### 6.1 Kritik

| Konu | Konum | Açıklama |
|------|--------|----------|
| REST endpoint’lerde auth yok | `backend/main.py` (threads, RAG, skills, MCP, memory, teachability, projects, presentations, export) | Token kontrolü yapılmıyor; `user_id` client’tan alınıyor. Başka kullanıcının verisine erişim mümkün. |
| WebSocket auth yok | `backend/main.py` ws_chat | Token veya session kontrolü yok. |
| Path traversal | `backend/main.py` api_export_project, api_export_project_pdf, api_download_presentation, api_download_image, api_presentation_pdf | `project_name` ve `filename` ile `..` kullanılarak dizin dışına erişim denenebilir. |
| Zayıf şifre hash | `backend/main.py` 155–156, 74–81 | SHA256, tuz yok; şifreler koda gömülü. |
| Memory/DB API’de Authorization yok | `frontend/src/lib/api.ts` getMemoryStats, getMemoryLayers, deleteMemory, getAutoSkills, getDbHealth | Bu çağrılar `fetcher` kullanmıyor; header’da token gönderilmiyor. Backend zaten auth istemiyor; ek olarak frontend de tutarsız. |

### 6.2 Orta

| Konu | Konum | Açıklama |
|------|--------|----------|
| Logout/Me’de Header kullanımı | `backend/main.py` api_logout, api_me | `authorization: str = ""` ile alınıyor; FastAPI’de `Header(..., alias="Authorization")` veya dependency ile Authorization header’ı açıkça alınmalı. |
| İç hata mesajlarının dönmesi | `backend/main.py` birçok `HTTPException(503, f"... {e}")` | Production’da stack/hata detayı client’a gitmemeli. |
| CORS `*` | `backend/main.py` 63 | Production’da origin kısıtlanmalı. |
| Rate limiting yok | Tüm API | Login ve ağır endpoint’ler korunmalı. |
| Token’lar bellekte | `backend/main.py` _active_tokens | Restart’ta tüm oturumlar silinir; çok sunucu için uygun değil. Redis/session store düşünülmeli. |

### 6.3 Düşük / İyileştirme

| Konu | Konum | Açıklama |
|------|--------|----------|
| Monolitik main.py | `backend/main.py` | Router’lara ve servis katmanına bölünmesi bakımı kolaylaştırır. |
| Versiyonlu migration yok | `tools/pg_connection.py` | Şema değişiklikleri için Alembic vb. kullanılabilir. |
| Request validasyonu zayıf | Pydantic modelleri | max_length, pattern, HttpUrl eklenebilir. |
| Frontend–backend tip senkronu yok | `frontend/src/lib/types.ts` vs `core/models.py` | OpenAPI’den tip üretimi veya ortak contract ile tutarlılık sağlanabilir. |
| DATABASE_URL varsayılanı | `config.py` | Varsayılan şifre kodda; production’da mutlaka env. |

---

## 7. Özet ve Öncelik Sırası

1. **Auth:** Tüm veri endpoint’lerinde token zorunlu yapın; `user_id`’yi token’dan türetin.  
2. **Path traversal:** `project_name` ve `filename` için resolve + base path kontrolü (ve gerekirse whitelist karakter) ekleyin.  
3. **Şifre:** Bcrypt/argon2 + tuz; şifreleri env/secret store’dan alın.  
4. **Header:** Logout/Me için `Authorization` header’ı doğru alın.  
5. **Hata:** 503’te sabit mesaj; detayı sadece loglayın.  
6. **CORS ve rate limit:** Production için origin kısıtı ve rate limiting.  
7. **Frontend:** Memory/DB çağrılarında da Authorization header’ı kullanın (backend auth’u açtıktan sonra tutarlı olsun).

Bu sırayla uygulandığında hem güvenlik hem de sürdürülebilirlik belirgin şekilde iyileşir.
