# Multi-Agent Dashboard — Uygulama Analiz Raporu

**Tarih:** 6 Mart 2025  
**Kapsam:** Mimari, backend/API, frontend, güvenlik, test, DevOps, kod kalitesi  
**Yöntem:** Paralel orkestrasyon (explorer, backend, frontend, security auditor ajanları)

---

## 1. Yönetici Özeti

Multi-Agent Dashboard; **Next.js** tek arayüz, **tek FastAPI backend** ve **ortak Python agent/pipeline/tool katmanı** ile çalışan bir sistemdir. Thread’ler JSON dosyada, RAG/memory/skills PostgreSQL’de tutulmaktadır. Analiz sonucunda **kritik güvenlik açıkları** (yetkisiz erişim, zayıf auth, path traversal riski), **eksik test/CI altyapısı**, **frontend’te hata yönetimi ve erişilebilirlik eksiklikleri** ve **mimari borç** tespit edilmiştir. Bu raporda tüm bulgular, hatalar ve geliştirme önerileri özetlenmektedir.

---

## 2. Proje Yapısı ve Teknoloji Yığını

### 2.1 Dizin Yapısı

```
multi-agent-dashboard/
├── config.py              # Merkezi konfig (MODELS, DATABASE_URL, SEARXNG, paths)
├── requirements.txt       # Python bağımlılıkları (backend/agent)
├── docker-compose.yaml    # Postgres + backend + frontend
├── agents/                # LLM agent'ları (orchestrator, thinker, researcher, ...)
├── backend/               # FastAPI API + WebSocket (main.py ~960 satır)
├── core/                  # Thread, Task, Event modelleri; state (JSON); events
├── pipelines/             # PipelineEngine (sequential, parallel, consensus, ...)
├── tools/                 # RAG, memory, skills, MCP, export, idea_to_project, ...
├── frontend/              # Next.js 14 SPA (App Router, TypeScript, Tailwind, Radix) — tek UI
├── data/                  # threads/, projects/, presentations/
└── logs/, .vscode/
```

**Özet:** Kök klasörde tek `package.json` yok; monorepo değil. Python repo + ayrı Next.js frontend. Tek arayüz Next.js’tir.

### 2.2 Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind, Radix UI, Zustand, Lucide, PWA |
| **Backend** | FastAPI, Pydantic, CORS, WebSocket, lifespan |
| **Veritabanı** | PostgreSQL (pgvector); Thread’ler JSON dosya (`core/state.py` → `data/threads/`) |
| **LLM** | NVIDIA API (OpenAI uyumlu), Qwen3 80B, MiniMax, Step, GLM, Nemotron |
| **Araçlar** | SearXNG, MCP client, RAG, reportlab/openpyxl/python-pptx |

---

## 3. Mimari Analiz

### 3.1 Tek UI (Next.js), Tek Backend

- **Next.js** tek arayüzdür; HTTP + WebSocket ile backend’e bağlanır (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`).
- Thread’ler `core.state` (JSON) ile saklanır.

### 3.2 API Tasarımı

- **REST:** `/api/auth/*`, `/api/threads/*`, `/api/rag/*`, `/api/skills/*`, `/api/mcp/*`, `/api/teachability`, `/api/eval/stats`, `/api/memory/*`, `/api/projects/*`, `/api/presentations/*`, `/api/export/*`, `/api/health`, `/api/models`, `/api/pipelines`, `/api/db/health`.
- **WebSocket:** `/ws/chat` — mesaj gönderimi, canlı event’ler, result/error, stop/ping-pong.
- **Auth:** Basit token (in-memory), `Authorization: Bearer <token>`; şifre SHA256 ile saklanıyor.

### 3.3 Mimari Borç ve Tutarsızlıklar

- **UI–backend senkronu:** Pipeline/thread/event modelleri frontend ile backend arasında tutarlı takip edilmeli.
- **Thread persistence:** Sadece dosya (JSON); memories/teachings/documents/skills PostgreSQL. Thread’lerin PG’de tutulması ölçek ve tutarlılık için önerilir.
- **Port:** Backend Docker’da 8000, frontend default 8001; dokümantasyon veya tek port standardı gerekli.
- **Tip paylaşımı:** Backend (Pydantic) ve frontend (TypeScript) modelleri ayrı; sürüklenme riski var. OpenAPI → client veya ortak tip paketi önerilir.
- **Kök package.json / monorepo araçları yok.**

---

## 4. Backend ve API Bulguları

### 4.1 Yapı

- Tüm backend **tek dosyada:** `backend/main.py` (~960 satır). Controller/Service/Repository ayrımı yok; endpoint’ler doğrudan `core.state`, `tools.rag`, `tools.dynamic_skills`, `tools.memory` kullanıyor.
- REST + WebSocket aynı dosyada.

### 4.2 Veritabanı

- **ORM yok:** `tools/pg_connection.py` ile psycopg2 pool, ham SQL. Şema aynı dosyada; **versiyonlu migration yok**.
- Thread’ler DB’de değil, JSON dosyalarında.

### 4.3 Kritik: Kimlik Doğrulama ve Yetkilendirme

- **Login/logout/me** var; ancak **diğer REST endpoint’lerde token kontrolü yok.**
- `user_id` tamamen **client’tan** (query/body) alınıyor → **başka kullanıcının thread/RAG/memory’sine erişim mümkün (IDOR).**
- Şifre: **SHA256, tuz yok**; kullanıcılar ve hash’ler koda gömülü (`USERS` dict).
- Token’lar sadece bellekte; restart’ta siliniyor.

### 4.4 Güvenlik ve Validasyon

- **Path traversal:** `project_name`, `filename` (`/api/projects/{project_name}/export`, `/api/presentations/{filename}/download`, `/api/images/{filename}/download`) için `..` ile path kontrolü yok. `resolve()` + base path kontrolü eklenmeli.
- **CORS:** `allow_origins=["*"]` — production’da origin kısıtlaması yapılmalı.
- **Rate limiting yok.**
- SQL parametreli kullanıldığı için injection riski düşük.

### 4.5 Tip Güvenliği

- Backend: `core/models.py` (Pydantic). Frontend: `frontend/src/lib/types.ts`. Ortak paket/OpenAPI’den üretilmiş tipler yok.
- Request modellerinde max_length / pattern gibi ek validasyon eksik.

### 4.6 Eksik / Hatalar (Backend)

- Logout/me için Authorization’ın Header ile alınması (FastAPI’de `Header(..., alias="Authorization")`) net tanımlı değil.

---

## 5. Frontend Bulguları

### 5.1 Bileşen ve State

- **Routing:** Ana sayfa + `/login`. Bileşenler `frontend/src/components/` altında tek seviye; Atomic Design veya feature klasörü yok.
- **Zustand:** Sadece auth için (`lib/auth.ts`).
- **Sunucu verisi:** React state ile; React Query yok; cache, refetch, loading/error ayrımı zayıf.
- **Ana sayfa:** Çok büyük; thread CRUD ve socket mantığı custom hook’lara taşınabilir.

### 5.2 UI Kütüphanesi ve Stil

- **Radix** bağımlılıkları var ancak **projede Radix import’u kullanılmıyor.** Modal, sekmeler kendi button/div pattern’i ile yapılmış.
- **Tailwind** kullanılıyor; `globals.css` ile CSS değişkenleri tanımlı.
- **Tutarsızlık:** Login sayfası violet tonları; ana uygulama mavi/blue. PWA install prompt pink/violet gradient. Hard-coded renkler (`#0a0e1a` vb.) token yerine kullanılmış.

### 5.3 Erişilebilirlik (A11y)

- **İyi:** `role="tablist"`, `role="tab"`, `aria-selected`, `aria-label`, `aria-expanded`, `aria-live="polite"`, `role="log"`, `role="alert"`, `role="dialog"`, `aria-modal="true"`, `:focus-visible`, touch hedefleri.
- **Eksikler:**
  - **Skip link:** `globals.css`’te `.skip-link` tanımlı ama layout’ta kullanılmıyor.
  - **DetailModal:** Focus trap yok; kapatma sonrası focus geri dönüşü yok; klavye ile modal dışına çıkılabiliyor.
  - PWA install prompt: focus yönetimi yok.
  - Sidebar tab panel: `aria-labelledby` ile tab ilişkisi eksik.

### 5.4 Loading ve Hata Yönetimi

- Thread listesi yüklenirken ayrı skeleton/spinner yok.
- **API/thread hataları** (`handleLoadThread`, `handleDeleteThread`, `loadThreadList`) catch edilip **kullanıcıya gösterilmiyor.**
- **Error boundary yok:** `app/error.tsx` tanımlı değil; bileşen patlarsa tüm uygulama çöküyor.
- WebSocket kopunca kullanıcıya net “Bağlantı koptu” mesajı yok.

### 5.5 API Client ve Tipler

- `getMemoryStats`, `getMemoryLayers`, `deleteMemory`, `getAutoSkills`, `getDbHealth` **Authorization header göndermiyor.**
- API hatalarında toast veya global error state ile kullanıcı bilgilendirmesi yok.
- Tipler sadece frontend’te; backend ile paylaşılan contract yok.

### 5.6 Performans

- **Dinamik import / lazy:** Kullanılmıyor. Tüm bileşenler statik import.
- Ağır paneller (ToolsPanels, TaskHistory, ExportButtons) lazy yüklenmiyor.
- `next/dynamic` ile Sidebar, ActivityStream, InterAgentChat lazy önerilir.

### 5.7 Tespit Edilen Hatalar (Frontend)

1. **use-agent-socket.ts (~satır 80):** `onStatusChange?.(status)` — closure’daki `status` eski değer; callback’e yeni status parametre olarak verilmeli veya ref ile sonra okunmalı.
2. **api.ts:** Memory/DB fonksiyonları auth header kullanmıyor.
3. **page.tsx — loadThreadList:** Catch’te kullanıcıya “liste yüklenemedi” mesajı yok.
4. **handleLoadThread / handleDeleteThread / handleDeleteAllThreads:** Hata tamamen yutuluyor.
5. **Import path:** `"../components/mobile-nav"` vs `"@/components/..."` karışık; alias ile tutarlı olmalı.

---

## 6. Güvenlik Denetimi Özeti

### 6.1 Kritik / Yüksek

- **Yetkisiz erişim (IDOR):** Thread, RAG, memory, skills, MCP, projects endpoint’leri Authorization kontrolü yapmıyor; `user_id` client’tan alınıyor.
- **Şifre saklama:** SHA256 (tuzsuz), sabit kullanıcılar koda gömülü.
- **Varsayılan secret’lar:** `DATABASE_URL` / `POSTGRES_PASSWORD` default değerleri kod ve compose’ta; production’da risk.

### 6.2 Orta

- CORS `allow_origins=["*"]`.
- CSRF koruması yok (state-changing istekler için).
- Güvenlik başlıkları (CSP, X-Frame-Options, X-Content-Type-Options) tanımlı değil.

### 6.3 Düşük / Bilgi

- `.env.example` yok; gerekli env değişkenleri dokümante değil.
- XSS: `dangerouslySetInnerHTML` sadece sabit service worker için; kullanıcı girdisi yok.
- Code executor tehlikeli pattern’leri engelliyor; SQL parametreli.

---

## 7. Test ve DevOps

### 7.1 Test

- **Birim / entegrasyon:** Projede test dosyası veya jest/vitest config yok. **Test ve coverage yok.**
- **E2E:** Playwright/Cypress altyapısı yok.
- Auth, thread CRUD, WebSocket chat, RAG, skill/MCP API’leri için test tanımlı değil.

### 7.2 DevOps

- **CI/CD:** `.github/` altında workflow yok. Lint, test, build veya deploy adımı yok.
- **Ortam:** docker-compose ile postgres, backend, frontend tanımlı; farklı ortamlar için override/env esnekliği sınırlı.
- **`.env.example`** yok.
- Staging/production için ayrı compose veya rollback stratejisi yok.

---

## 8. Kod Kalitesi

- **TypeScript:** `strict: true` açık.
- **ESLint:** Sadece `next/core-web-vitals` ve `next/typescript`; ek kural/plugin yok.
- **Kullanılmayan kod:** Otomatik tarama yok; büyük bloklar atıl kalabilir.
- Backend Python, frontend TS; ortak tip/contract yok.

---

## 9. Hatalar ve Eksikler Özet Tablosu

| Alan | Durum | Örnek / Dosya |
|------|--------|----------------|
| **Auth / IDOR** | Kritik | Tüm veri endpoint’lerinde token yok; user_id client’tan |
| **Şifre** | Kritik | SHA256 tuzsuz; bcrypt/argon2 + tuz önerilir |
| **Path traversal** | Yüksek | projects/presentations/images export/download |
| **CORS / headers** | Orta | allow_origins=["*"]; güvenlik başlıkları yok |
| **Error boundary** | Eksik | `app/error.tsx` yok |
| **Skip link** | Eksik | CSS var, layout’ta kullanılmıyor |
| **Modal focus** | Eksik | DetailModal focus trap / return focus yok |
| **API hata gösterimi** | Eksik | Thread/load/delete hataları kullanıcıya yansımıyor |
| **Memory/DB API auth** | Eksik | getMemoryStats vb. Authorization header yok |
| **onStatusChange stale** | Bug | use-agent-socket.ts closure’da eski status |
| **Code splitting** | Eksik | dynamic/lazy kullanılmıyor |
| **Test / CI** | Yok | pytest, frontend unit, Playwright E2E yok |
| **.env.example** | Yok | Gerekli env’ler dokümante değil |
| **Migration** | Yok | DB şema için versiyonlu migration yok |
| **Tip paylaşımı** | Risk | Backend/Frontend modelleri elle senkron |

---

## 10. Geliştirme Önerileri (Öncelik Sırasıyla)

### 10.1 Kritik (Hemen)

1. **Tüm veri endpoint’lerinde token zorunlu yapın;** `user_id`’yi **yalnızca token’dan** türetin; client’tan gelen `user_id` kullanılmasın.
2. **Path traversal:** `project_name`, `filename` için `resolve()` + base path kontrolü ekleyin; `..` ile dışarı çıkışı engelleyin.
3. **Şifre:** Kullanıcı bilgisi env/DB’den okunsun; şifreler **bcrypt veya argon2** ile tuzlu hash’lensin.
4. **Error boundary:** En azından `frontend/src/app/error.tsx` (ve isteğe `global-error.tsx`) ekleyin.

### 10.2 Yüksek (Kısa Vadede)

5. **CORS:** Production’da `allow_origins` bilinen origin’lerle sınırlayın.
6. **Güvenlik başlıkları:** CSP, X-Frame-Options, X-Content-Type-Options ekleyin.
7. **Frontend API hataları:** Thread listesi, load, delete hatalarında kullanıcıya mesaj veya toast gösterin; `loadThreadList` catch’te bilgi verin.
8. **Memory/DB API:** İlgili endpoint’ler korumalıysa `getAuthToken()` ile Authorization header ekleyin.
9. **use-agent-socket:** `onStatusChange` callback’ine güncel status’u parametre veya ref ile verin; stale closure’ı kaldırın.
10. **Skip link:** Layout’ta ana içeriğe atlama linki ekleyin; `.skip-link` sınıfını kullanın.
11. **DetailModal:** Focus trap ve kapatma sonrası focus geri dönüşü ekleyin (veya Radix Dialog kullanın).

### 10.3 Orta (Orta Vadede)

12. **.env.example:** Kök dizinde gerekli env değişkenlerini (NVIDIA_API_KEY, DATABASE_URL, NEXT_PUBLIC_*, vb.) dokümante edin.
13. **Rate limiting:** Backend’de özellikle auth ve chat endpoint’leri için ekleyin.
14. **Test:** Backend için pytest + FastAPI TestClient (auth, thread, RAG); frontend için React Testing Library/Vitest; E2E için Playwright (login + thread + chat).
15. **CI/CD:** GitHub Actions (veya kullandığınız CI) ile lint, test, build pipeline’ı.
16. **Code splitting:** `next/dynamic` ile Sidebar, ActivityStream, InterAgentChat, ToolsPanels lazy yükleyin.
17. **React Query:** Thread listesi ve detay için cache, loading, error, refetch yönetimi.

### 10.4 Uzun Vadede

18. **Thread persistence:** Thread’leri PostgreSQL’e taşıyın; JSON dosya yerine tek kaynak.
19. **Tip paylaşımı:** OpenAPI schema + codegen ile frontend tip üretimi veya ortak tip paketi.
20. **Backend yapı:** main.py’yi controller/service/repository katmanlarına bölün; migration stratejisi (örn. Alembic) ekleyin.
21. **Radix kullanımı:** Modal ve sekmelerde Radix bileşenlerini kullanın; a11y ve tutarlılık için.
22. **Port ve ortam:** Backend port’u (8000/8001) ve ortam değişkenleri tek yerde dokümante edin; staging/production compose override’ları tanımlayın.

---

## 11. Sonuç

Uygulama, çift arayüz ve güçlü agent/pipeline altyapısı ile işlevseldir; ancak **yetkisiz erişim**, **zayıf auth**, **path traversal riski** ve **eksik hata/test/CI** ciddi risk oluşturmaktadır. Bu rapordaki **Kritik** ve **Yüksek** öncelikli maddelerin uygulanması, hem güvenlik hem kullanılabilirlik açısından önerilir. Paralel orkestrasyon ile elde edilen bulgular tek rapor altında toplanmış olup, ileride modül bazlı detay (örn. sadece RAG veya sadece MCP) istenirse o odakta ek analiz yapılabilir.
