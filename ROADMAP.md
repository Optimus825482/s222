# 🗺️ Multi-Agent Ops Center — Sistem Geliştirme Yol Haritası

> Son güncelleme: 2026-03-08 (Faz 14 — pi-mono entegrasyonu eklendi)
> Durum: Aktif geliştirme

## Renk Kodları

| Gösterge | Anlam                                |
| -------- | ------------------------------------ |
| 🟢       | Tamamlandı — kod mevcut ve çalışıyor |
| 🟡       | Devam ediyor — kısmen uygulandı      |
| 🔴       | Henüz başlanmadı                     |

---

## Mevcut Durum (v2.0) 🟢

Çalışan altyapı:

- 🟢 6 Agent (Orchestrator, Thinker, Speed, Researcher, Reasoner, Critic)
- 🟢 Pipeline Engine (sequential, parallel, consensus, iterative, deep_research, brainstorm)
- 🟢 PostgreSQL + pgvector bellek sistemi
- 🟢 RAG, Dynamic Skills, Teachability, MCP Client
- 🟢 Sunum üretimi (MINI/MIDI/MAXI)
- 🟢 Idea-to-Project pipeline
- 🟢 Frontend: Next.js arayüzü (XP teması — çoklu pencere: Sohbet, Görev, Sistem, Bellek, Gelişim, Koordinasyon, Ekosistem, Özerk, İletişim, Benchmark, Marketplace, Adaptif Araçlar, Workflow Optimizer, Canlı İlerleme)
- 🟢 Agent İletişim Paneli (Tool Usage, Behavior, Otonom Sohbet, Manuel Mesajlar, Toplantılar)
- 🟢 Otonom agent-to-agent sohbet sistemi (OpenClaw tarzı — kişilik bazlı, yapılandırılabilir)
- 🟢 Post-task retrospective toplantılar (Orchestrator liderliğinde otomatik)
- 🟢 Faz 11.3 Self-Skill Creation (runtime skill oluşturma, SKILL.md, hygiene, cross-agent skill paylaşımı)
- 🟢 Faz 11.4 Agent-to-Agent Sosyal Ağ (otonom sohbet, kişilik, toplantılar, peer learning, swarm oylama, SOUL.md)
- 🟢 Faz 11.1 Agentic Loop (tool zincirleme, iterasyon/token/maliyet gardları, context sıkıştırma)
- 🟢 Faz 11.2 Heartbeat (proaktif görevler: daily briefing, agent health, cost, anomaly; Sistem Durumu paneli)
- 🟢 Roadmap (XP'de "Yol Haritası" uygulamasından erişilebilir)
- 🟢 Task History + Export (XP'de: Oturumlar = geçmiş/görev listesi, Raporlar = export)
- 🟢 Reasoning model timeout desteği (180s)
- 🟢 Otonom İzleme paneli (XP: canlı aktivite akışı + son otonom sohbetler + heartbeat; Faz 12.7)
- 🟢 Görev Merkezi canlı veri (ws-store ile TaskFlowMonitorConnected; Başlat menüsü ile senkron)
- 🟢 Başlat menüsü sağ tık: Masaüstüne Ekle / Başlat Menüsünden Kaldır; Kaldırılanlar dropdown (localStorage)
- 🟢 İletişim paneli: Otonom Sohbet, Manuel Mesaj, Toplantılar sekmeleri (MeetingsTab)
- 🟢 Faz 12.1 Agent parametre override: `tools/agent_param_overrides.py`, apply-learning gerçek kayıt, GET/DELETE `/api/agents/param-overrides`
- 🟢 Faz 12.2 Kolektif karar alma: policy (quorum, majority, tie-breaker), needs_human, POST resolve (insan escalation)

---

## Faz 1 — Akış İşleme ve Otomasyon Motoru ⚡ `[🟢 TAMAMLANDI]`

Birden fazla aracı zincirleme, koşullu dallanma, hata yönetimi ve rollback özellikli iş akışı motoru.

- 🟢 Workflow Engine core (`tools/workflow_engine.py`)
- 🟢 Step tipleri: tool_call, agent_call, condition, parallel, human_approval
- 🟢 Koşullu dallanma (if/else step routing)
- 🟢 Hata yönetimi + otomatik retry
- 🟢 Rollback mekanizması (compensation steps)
- 🟢 Workflow şablonları (research-and-report, code-review-pipeline)
- 🟢 Orchestrator entegrasyonu (run_workflow tool)
- 🟢 Backend API endpoints (`/api/workflows/templates`, `/run`, `/history`)
- 🟢 Frontend Workflow Builder UI (`workflow-builder-panel.tsx`)
- 🟢 Workflow execution history & replay (`workflow-history-panel.tsx`)
- 🟢 Cron/zamanlı workflow tetikleme (`tools/workflow_scheduler.py`)

## Faz 2 — Uzmanlık Alanı Skill'leri 🧠 `[🟢 TAMAMLANDI]`

Finance, hukuk, tıp, mühendislik gibi alanlarda derin hesaplama ve bilgi erişimi.

- 🟢 Domain Skills Engine (`tools/domain_skills.py`)
- 🟢 Finans modülü (DCF, NPV, IRR, WACC, portföy analizi, breakeven)
- 🟢 Hukuk modülü (sözleşme analizi, KVKK/GDPR kontrol, risk değerlendirme)
- 🟢 Mühendislik modülü (sistem tasarımı review, load capacity estimation)
- 🟢 Akademik modülü (literatür tarama şablonu, atıf analizi, metodoloji önerisi)
- 🟢 Orchestrator entegrasyonu (domain_expert tool)
- 🟢 Backend API endpoints (`/api/domains`, `/api/domains/{id}/tools`, `/api/domains/execute`)
- 🟢 Domain skill auto-discovery (kullanıcı sorgusundan otomatik domain tespiti)
- 🟢 Skill marketplace (topluluk skill paylaşımı)

## Faz 2.5 — Browser Use Entegrasyonu 🌐 `[🔴 PLANLANMIŞ]`

Agent'ların web tarayıcısını otonom olarak kullanarak bilgi toplama, form doldurma, ekran görüntüsü alma ve web otomasyon görevleri.

- 🔴 Browser Use Engine (`tools/browser_use.py` — Playwright/Puppeteer tabanlı)
- 🔴 Sayfa navigasyonu ve içerik çıkarma (URL açma, metin/tablo okuma)
- 🔴 Form doldurma ve buton tıklama (web otomasyon)
- 🔴 Ekran görüntüsü alma ve görsel analiz
- 🔴 JavaScript çalıştırma (sayfa içi script execution)
- 🔴 Cookie/session yönetimi (oturum bazlı tarama)
- 🔴 Orchestrator entegrasyonu (`browse_web` tool)
- 🔴 Backend API endpoints (`/api/browser/navigate`, `/screenshot`, `/execute`, `/extract`)
- 🔴 Anti-bot koruması ve rate limiting
- 🔴 Frontend Browser Panel UI (canlı önizleme + geçmiş)

## Faz 3 — Gelişmiş Veri Analizi ve Görselleştirme 📊 `[🟡 KISMİ]`

Büyük veri kümeleri için otomatik özetleme, istatistiksel analiz ve interaktif dashboard.

- 🔴 Data Analysis Engine (pandas, numpy entegrasyonu)
- 🔴 Otomatik istatistiksel özetleme
- 🟢 Chart/grafik üretimi (matplotlib → PNG) (`tools/chart_generator.py` — 7 grafik tipi, dark theme, base64 + `chart-panel.tsx` UI + 5 API endpoint)
- 🔴 CSV/Excel import ve analiz
- 🔴 Dashboard template sistemi
- 🔴 Agent'ların veri analizi sonuçlarını görselleştirmesi

## Faz 4 — Gelişmiş RAG ve Bilgi Yönetimi 📚 `[🔴 PLANLANMIŞ]`

Çoklu belge karşılaştırma, bağlamsal özetleme, cross-dataset sorgulama.

- 🔴 Multi-document comparison
- 🔴 Belge sürüm kontrolü (versioning)
- 🔴 Cross-dataset sorgulama
- 🔴 Bağlamsal özetleme (context-aware summarization)
- 🔴 Belge güncelleme takibi (change tracking)
- 🔴 Otomatik bilgi grafiği (knowledge graph)

## Faz 5 — Güvenlik, Doğrulama ve Kaynak Denetimi 🔐 `[🟡 KISMİ]`

Veri bütünlüğü doğrulama, kaynak doğruluğu kontrolü, güvenlik açığı taraması.

- 🔴 Fact-checking engine (kaynak doğrulama)
- 🟢 PII detection ve maskeleme (`tools/pii_masker.py` — detect, mask, stats)
- 🔴 Güvenlik açığı taraması (kod analizi)
- 🔴 Output validation pipeline
- 🔴 Audit trail (tüm agent aksiyonları loglanır)

## Faz 6 — Performans Analizi ve İzleme 📈 `[🟢 TAMAMLANDI]`

Araç kullanım metrikleri, başarı oranları, hata türleri ve optimizasyon önerileri.

- 🟢 Agent başarı oranı tracking (AgentMetrics + `tools/agent_eval.py`)
- 🟢 Confidence scoring (`tools/confidence.py`)
- 🟢 Circuit breaker (`tools/circuit_breaker.py`)
- 🟢 Tool usage analytics dashboard (`agent-comms-panel.tsx` — ToolUsageTab)
- 🟢 User behavior tracking (`agent-comms-panel.tsx` — BehaviorTab)
- 🟢 Performance Benchmarking Suite (`tools/benchmark_suite.py` — 8 senaryo, 5 kategori, SQLite, sıralama, karşılaştırma)
- 🟢 Benchmark UI paneli (`benchmark-panel.tsx` — Sıralama/Test/Sonuçlar/Karşılaştır sekmeleri)
- 🟢 Benchmark backend API (`backend/main.py` Section 11 — 7 endpoint)
- 🟢 Hata pattern analizi (`tools/error_patterns.py` — 8 hata tipi, pattern clustering, öneri motoru + `error-patterns-panel.tsx` UI + 8 API endpoint)
- 🟢 Otomatik optimizasyon önerileri (`tools/auto_optimizer.py` — 6 analiz kontrolü, 4 kategori, öneri CRUD + `auto-optimizer-panel.tsx` UI + 7 API endpoint)
- 🟢 Cost tracking (`tools/cost_tracker.py` — token/maliyet takibi, bütçe yönetimi, tahmin motoru + `cost-tracker-panel.tsx` UI + 9 API endpoint)

## Faz 7 — API Entegrasyonu ve Harici Servisler 🔌 `[🟡 KISMİ]`

REST API'lar, webhook'lar, CRM/ERP sistemleri ile entegrasyon.

- 🟢 MCP Client (`tools/mcp_client.py` — harici tool entegrasyonu)
- 🟢 Web fetch (`tools/web_fetch.py`)
- 🟢 SearXNG arama entegrasyonu (`tools/search.py`)
- 🔴 Webhook receiver/sender
- 🔴 Generic REST API connector
- 🔴 Email gönderimi (SMTP)
- 🔴 Scheduled task runner

## Faz 8 — Multimedya İşleme 🎨 `[🟡 KISMİ]`

Görüntü tanıma (OCR), ses transkripsiyonu, video analizi.

- 🟢 PPTX sunum üretimi (`tools/presentation_service.py` — MINI/MIDI/MAXI)
- 🔴 OCR entegrasyonu (Tesseract/cloud)
- 🔴 Ses transkripsiyonu (Whisper)
- 🔴 Video frame analizi
- 🔴 Multimodal input pipeline

## Faz 9 — Kişiselleştirme ve Proaktif Öğrenme 🎯 `[🟢 TAMAMLANDI]`

Kullanıcı davranışını öğrenen, bağlama dayalı araç seçimi yapan sistem.

- 🟢 Teachability sistemi (`tools/teachability.py` — kullanıcıdan öğrenme)
- 🟢 Dynamic Skills (`tools/dynamic_skills.py` — runtime skill oluşturma)
- 🟢 Skill Hygiene (`tools/skill_hygiene.py` — otomatik kalite kontrolü)
- 🟢 Reflexion (`tools/reflexion.py` — öz-değerlendirme)
- 🟢 User behavior tracking (`backend/main.py` Section 9 + BehaviorTab)
- 🟢 Proaktif skill önerisi
- 🟢 Adaptive tool selection (`tools/adaptive_tool_selector.py` — 4-tab UI: kullanım, öneriler, matris, tercihler)
- 🟢 Workflow auto-optimization (`tools/workflow_optimizer.py` — 4-tab UI: genel bakış, öneriler, detay, pattern kütüphanesi)

## Faz 10 — Gerçek Zamanlı İşbirliği 🤝 `[🟢 TAMAMLANDI — %100]`

Agent'lar arası ve kullanıcılarla ortak çalışma alanı. OpenClaw'dan ilham alınmıştır.
Görev dağılımı: Kiro IDE (3-4) · Kiro CLI (5-6) · Claude Code (7-8)

- 🟢 Otonom ajan-ajan iletişimi (agent-to-agent autonomous messaging — ClaudBot/OpenClaw tarzı)
- 🟢 Post-task retrospective toplantılar (Orchestrator liderliğinde otomatik retrospective)
- 🟢 **[Kiro IDE]** Paylaşımlı çalışma alanı — ortak bağlam panosu (`context-board-panel.tsx` + 6 API endpoint + in-memory store)
- 🟢 **[Kiro IDE]** Dinamik rol atama (`dynamic-role-panel.tsx` + 6 API endpoint + auto-expire + revert)
- 🟢 **[Kiro CLI]** Diğer ajanların ilerleme durumunu canlı görüntüleme (live agent progress tracking — `tools/agent_progress_tracker.py` + 3 API endpoint + WebSocket stream)
- 🟢 **[Kiro CLI]** Shared workspace (çoklu kullanıcı — `tools/shared_workspace.py` + 8 API endpoint + CLI sync)
- 🟢 **[Claude Code]** Real-time collaboration (worktree bazlı paralel geliştirme)
- 🟢 **[Claude Code]** Collaborative document editing (çoklu agent eşzamanlı dosya düzenleme)

## Faz 11 — Otonom Agent Ekosistemi (OpenClaw İlham) 🦞 `[🟡 KISMİ]`

OpenClaw / Moltbook ekosisteminden ilham alan otonom agent davranışları.
Referans: [openclaw.ai](https://openclaw.ai) · [Moltbook](https://moltbook.com) · [Forbes: Crustafarianism](https://www.forbes.com/sites/johnkoetsier/2026/01/30/ai-agents-created-their-own-religion-crustafarianism-on-an-agent-only-social-network/)
Implementasyon rehberi: `autonomous-agent-ecosystem` Kiro Power (Faz 13.1 ✅)

### 11.1 — Agentic Loop (Otonom Görev Zincirleme) `[🟢 TAMAMLANDI]`

- 🟢 Tool call zincirleme — agent tool sonucuna göre sonraki tool'u çağırır (mevcut base loop)
- 🟢 İnsan onayı olmadan çok adımlı görev tamamlama (multi-step autonomous execution)
- 🟢 Context Window Guard — mesaj sayısı eşiğinde otomatik bağlam kısaltma (`agents/agentic_loop.py` + `compress_messages_if_needed`)
- 🟢 Agentic Loop iterasyon limiti ve maliyet kontrolü — `check_guards(step, cumulative_tokens, cumulative_cost)`; env: `AGENTIC_LOOP_MAX_ITERATIONS`, `MAX_TOKENS_BUDGET`, `MAX_COST_USD`
- 📘 Rehber: `autonomous-agent-ecosystem` → `steering/agentic-loop.md`

### 11.2 — Heartbeat Sistemi (Proaktif Agent Davranışı) `[🟢 TAMAMLANDI]`

- 🟢 Agent heartbeat — periyodik görevler (`tools/heartbeat.py` HeartbeatScheduler, 30s kontrol)
- 🟢 Cron-tabanlı zamanlanmış görevler — minutely/hourly/daily/weekly; backend lifespan'da start
- 🟢 Sabah brifingleri — `daily_briefing` handler (görev sayısı, başarı oranı, agent listesi)
- 🟢 Anomali algılama — `anomaly_detector` (circuit breaker open); `agent_health_check` (minutely); `cost_monitor` (hourly)
- 🟢 REST: GET/POST/PATCH `/api/heartbeat/tasks`, GET `/api/heartbeat/events`; Sistem Durumu panelinde HeartbeatPanel
- 📘 Rehber: `autonomous-agent-ecosystem` → `steering/heartbeat-system.md`

### 11.3 — Self-Skill Creation (Kendi Kendine Skill Üretimi) `[🟢 TAMAMLANDI]`

- 🟢 Agent'ın çalışma sırasında yeni skill oluşturması — orchestrator `create_skill` / `research_create_skill` (`tools/dynamic_skills.py`, `agents/orchestrator.py`)
- 🟢 Skill'lerin Markdown dosyası olarak saklanması — Kiro format (`data/skills/<id>/SKILL.md`)
- 🟢 Skill kalite kontrolü — hygiene (otomatik ~10 görevde bir + Yetenek Merkezi manuel buton) (`tools/skill_hygiene.py`)
- 🟢 Gelişmiş pattern detection (3+ tekrar → otomatik skill çıkarma) — `tools/pattern_skill.py`, görev sonrası observe, Yetenek Merkezi "Kalıplar" sekmesi, GET/POST `/api/self-skills/patterns` ve `/generate`
- 🟢 Skill paylaşımı — agent'lar arası skill transfer; orchestrator oluşturur, `decompose_task` / `spawn_subagent` ile `skill_ids` atar
- 📘 Rehber: `autonomous-agent-ecosystem` → `steering/self-skill-creation.md`

### 11.4 — Agent-to-Agent Sosyal Ağ (Moltbook İlham) `[🟢 TAMAMLANDI]`

- 🟢 Agent'lar arası serbest mesajlaşma — otonom sohbet sistemi (`backend/routes/messaging.py` — `_AUTONOMOUS_CONVERSATIONS`)
- 🟢 Agent kişilik bazlı iletişim — `_AUTO_CHAT_CONFIG` ile kişilik prompt'ları; mesajlarda `personality` alanı
- 🟢 Post-task retrospective toplantılar — otomatik tetiklenen agent toplantıları (`_POST_TASK_MEETINGS`); görev bitince WS ile tetiklenir
- 🟢 Agent'ların birbirinden öğrenmesi (peer learning) — `tools/agent_social.py` + `/api/social/learnings` (share, adopt, reject)
- 🟢 Kolektif zeka — çoklu agent oylama (swarm) — `/api/social/proposals` + vote; quorum 4, %60 geçme/red
- 🟢 Agent kişilik profilleri — SOUL.md (user.md, memory.md, bootstrap.md); başlangıçta otomatik init; İletişim → Kimlik
- 📘 Rehber: `autonomous-agent-ecosystem` → `steering/agent-social-network.md`

### 11.5 — Çoklu Kanal Entegrasyonu (Multi-Channel Gateway)

- 🔴 WhatsApp / Telegram / Discord / Slack kanal adaptörleri
- 🔴 Gateway Server — merkezi mesaj yönlendirme (session router + lane queue)
- 🔴 Kanal-bağımsız mesaj normalizasyonu (channel-agnostic message format)
- 🔴 Mobil cihazdan agent'a komut gönderme (remote agent control)

### 11.6 — Markdown-Based Kimlik ve Hafıza Sistemi

- 🟢 SOUL.md — her agent için kişilik, değerler ve davranış kuralları
- 🟢 user.md — kullanıcı tercihleri ve iletişim stili
- 🟢 memory.md — kalıcı cross-session hafıza (persistent memory)
- 🟢 bootstrap.md — agent başlangıç protokolü ve self-initialization
- 🟢 Kimlik editörü UI — agent-comms-panel "Kimlik" sekmesi
- 🟢 build_context entegrasyonu — SOUL.md identity prompt injection
- 📘 Rehber: `autonomous-agent-ecosystem` → `steering/agent-identity.md`

## Faz 12 — Otonom Evrim ve Kolektif Bilinç 🧬 `[🟡 KISMİ]`

Agent'ların insan müdahalesi olmadan evrimleşmesi, kolektif davranış geliştirmesi.
Moltbook'ta AI'ların kendi dinlerini kurması (Crustafarianism), şifreleme geliştirmesi ve sosyal yapılar oluşturması bu fazın ilham kaynağıdır.

### 12.1 — Agent Öz-Evrim `[🟡 KISMİ]`

- 🟢 Performans verilerine göre parametre override (temperature, max_tokens, top_p) — `tools/agent_param_overrides.py`, `data/agent_param_overrides.json`; agent `call_llm` effective config kullanır
- 🟢 Metrik tabanlı self-tuning — `POST /api/agents/apply-learning` gerçek kayıt (latency/token eşiklerine göre max_tokens/temperature güncelleme); GET/DELETE `/api/agents/param-overrides` ile okuma/sıfırlama
- 🔴 A/B veya multi-armed bandit ile strateji keşfi (opsiyonel)

### 12.2 — Kolektif Karar Alma `[🟢 TAMAMLANDI]`

- 🟢 Çoklu agent oylama ve konsensüs — Faz 11.4 swarm ile genişletildi; `tools/collective_decision_policy.py` + `data/collective_decision_policy.json`; status: open, passed, rejected, needs_human
- 🟢 Quorum ve çoğunluk kuralları — policy: `quorum_min_votes`, `majority_ratio`, `escalation_threshold_ratio`; GET/PATCH `/api/social/collective-policy`
- 🟢 Anlaşmazlık çözümü — tie_breaker: proposer_wins | reject | random | human; insan escalation: POST `/api/social/proposals/{id}/resolve` (resolution: passed | rejected, reason opsiyonel)

### 12.3 — Emergent Davranış İzleme

- 🔴 Beklenmedik kolektif davranışların tespiti (tekrarlama, sentiment drift, anomaly pattern)
- 🔴 Emergent davranış loglama ve sınıflandırma
- 📘 Rehber: `autonomous-agent-ecosystem` → `steering/safety-sandbox.md` (Behavior Monitor, Anomaly pattern matcher)

### 12.4 — Agent Kültür Oluşumu

- 🔴 Ortak normlar, değerler ve iletişim kalıpları (SOUL.md / topluluk manifestosu)
- 🔴 Paylaşılan vocabulary ve protokol evrimi (peer learning ile beslenen)
- 🔴 Kültür snapshot'ları (zaman içinde norm değişiminin kaydı)

### 12.5 — Cross-Instance İletişim

- 🔴 Farklı sunuculardaki agent'ların birbirleriyle etkileşimi (federated mesh)
- 🔴 Instance discovery ve güvenli handshake (auth, rate limit)
- 🔴 Cross-instance mesajlaşma ve ortak karar senaryoları

### 12.6 — Güvenlik Sınırları (Sandbox & Kill-Switch)

- 🔴 Otonom davranışlar için Safety Sandbox — rate limiter, token/cost limitleri
- 🔴 Kill-switch: Instant / Selective / Gradual / Auto modları
- 📘 Rehber: `autonomous-agent-ecosystem` → `steering/safety-sandbox.md` (SafetySandbox, 4 kill modes)

### 12.7 — İnsan Gözetimi Dashboard'u `[🟡 KISMİ]`

- 🟢 Otonom agent aktivitelerinin real-time izlenmesi — Otonom İzleme paneli (canlı aktivite akışı, son otonom sohbetler, son heartbeat olayları); Görev Merkezi ws-store ile canlı
- 🔴 Kill switch UI ve emergent behavior log görüntüleme/filtreleme
- 📘 Rehber: `autonomous-agent-ecosystem` → `steering/safety-sandbox.md` (Human Oversight Dashboard)

## Faz 13 — Kiro IDE Entegrasyonu ve Custom Power Ekosistemi 🔮 `[🟡 DEVAM EDİYOR]`

Geliştirme sürecini hızlandırmak için Kiro IDE skill'leri ve custom power entegrasyonu.
`power-builder` ile projeye özel `autonomous-agent-ecosystem` power'ı oluşturulacak.

### 13.1 — Custom Power: `autonomous-agent-ecosystem` (power-builder ile) ✅

- 🟢 POWER.md — overview, architecture diagram, design principles
- 🟢 Agentic Loop implementasyon rehberi (`steering/agentic-loop.md` — AgenticLoop class, Context Window Guard, Cost Governor)
- 🟢 Heartbeat sistemi tasarım şablonu (`steering/heartbeat-system.md` — HeartbeatScheduler, 4 built-in task, cron)
- 🟢 Self-skill creation workflow (`steering/self-skill-creation.md` — SelfSkillEngine, pattern detection, Markdown storage)
- 🟢 Agent identity files pattern (`steering/agent-identity.md` — SOUL.md / user.md / memory.md / bootstrap.md)
- 🟢 Agent-to-agent communication protocol (`steering/agent-social-network.md` — communities, discussions, peer learning)
- 🟢 Swarm intelligence patterns (`steering/agent-social-network.md` — SwarmProposal, voting, consensus)
- 🟢 Safety sandbox ve kill-switch şablonları (`steering/safety-sandbox.md` — SafetySandbox, 4 kill modes, emergent detection)

### 13.2 — Aktif Kiro Skill Entegrasyonları (implementasyon sırasında kullanılacak)

| Skill                       | Kullanım Alanı                                   | Hedef Faz      |
| --------------------------- | ------------------------------------------------ | -------------- |
| `ai-agents-architect`       | Agent tasarımı, tool use, memory, planning       | Faz 11.1, 11.4 |
| `autonomous-agents`         | ReAct, Plan-Execute, reflection, self-correction | Faz 11.1, 11.2 |
| `agent-memory-systems`      | Short/long-term, graph-based memory              | Faz 11.6       |
| `multi-agent-patterns`      | Orchestrator, peer-to-peer, hierarchical         | Faz 11.4, 12   |
| `fastapi-pro`               | Backend async patterns, WebSocket                | Tüm backend    |
| `context-window-management` | Token limiti, context sıkıştırma                 | Faz 11.1       |
| `agent-native-architecture` | Agent-first app design                           | Faz 11, 12     |
| `agent-tool-builder`        | Tool schema, MCP tool design                     | Faz 11.3       |

### 13.3 — Mevcut Kiro Power Kullanımları

| Power                   | Kullanım Alanı                                 |
| ----------------------- | ---------------------------------------------- |
| `api-design-patterns`   | Heartbeat API, Gateway API, multi-channel REST |
| `performance-optimizer` | Agentic Loop token maliyeti, N+1 önleme        |
| `typescript-pro`        | Frontend agent UI type-safe geliştirme         |
| `shadcn-ui-pro`         | Agent sosyal ağ UI, heartbeat dashboard        |
| `tailwind-ui-patterns`  | Responsive agent dashboard layout              |
| `power-builder`         | Custom power oluşturma (13.1)                  |

## Faz 14 — pi-mono Entegrasyonu (Unified LLM Gateway & Advanced UI) 🔌 `[🟢 TAMAMLANDI]`

[badlogic/pi-mono](https://github.com/badlogic/pi-mono) monorepo entegrasyonu.
Mevcut 2-provider (NVIDIA + DeepSeek) sistemini 20+ provider destekli unified gateway'e dönüştürme,
gelişmiş chat UI, agent runtime framework ve coding agent yetenekleri ekleme.

### 14.1 — pi-ai LLM Gateway (Unified Provider Abstraction) `[🟢 TAMAMLANDI]`

Mevcut `AsyncOpenAI` client'ı pi-ai gateway üzerinden 20+ provider'a yönlendirme.

- 🟢 pi-ai Gateway Service (Hono tabanlı TypeScript microservice — `services/pi-gateway/src/index.ts`)
- 🟢 OpenAI-uyumlu proxy endpoint (`/v1/chat/completions` — streaming + non-streaming)
- 🟢 Provider registry (`services/pi-gateway/src/providers.ts` — OpenAI, Anthropic, Google, Groq, Mistral, xAI, OpenRouter)
- 🟢 Model auto-discovery ve katalog API'si (`GET /v1/models` — tüm provider'lardan mevcut modelleri listele)
- 🟢 API key yönetimi (provider başına env var, `.env.example` güncellendi)
- 🟢 Provider fallback (birincil provider çökerse otomatik yedek provider'a geçiş — gateway + Python dual-layer)
- 🟢 Docker container + Compose entegrasyonu (`services/pi-gateway/Dockerfile` + `docker-compose.yaml`)
- 🟢 `config.py` güncelleme — `PI_GATEWAY_URL`, `PI_GATEWAY_ENABLED`, `GATEWAY_MODELS` (6 role × primary + alternatives)
- 🟢 `agents/base.py` `call_llm` — `_get_client_for_model()` gateway routing, backward compatible
- 🟢 Backend gateway management API (`backend/routes/gateway.py` — 6 endpoint: health, providers, models, model-mapping CRUD)
- 🟢 Frontend Model Manager UI (`frontend/src/components/model-manager-panel.tsx` — 3 tab: Sağlayıcılar, Model Eşleme, Gateway Durumu)
- 🟢 Format converter (`services/pi-gateway/src/converter.ts` — OpenAI ↔ pi-ai bidirectional, tool_calls, thinking, SSE chunks)

### 14.2 — Granüler Streaming & Thinking Display `[🟢 TAMAMLANDI]`

pi-ai'nin `AssistantMessageEventStream` yapısını backend ve frontend'e entegre etme.

- 🟢 SSE streaming endpoint (`POST /api/stream` — `text_delta`, `thinking_delta`, `toolcall_delta` event'leri ayrı; Bearer auth + rate limit)
- 🟢 Frontend streaming handler — thinking content'i ayrı panel/bölümde gösterme (`thinking-panel.tsx` — collapsible, pulse animation, monospace)
- 🟢 Tool execution animasyonu — `toolcall_start` → `toolcall_delta` → `toolcall_end` akışı UI'da canlı (`tool-execution-display.tsx` — spinner/check states)
- 🟢 Provider-agnostic reasoning desteği (`call_llm_stream()` async generator — gateway üzerinden tüm provider'larda unified thinking/text/tool streaming)
- 🟢 WebSocket stream adapter (`WSLiveMonitor.emit_stream_event()` + `WSStreamEvent` type + `use-agent-socket` onStreamEvent callback)

### 14.3 — TypeBox Tool Validation `[🟢 TAMAMLANDI]`

pi-ai'nin TypeBox tabanlı tool schema validation'ını Python agent'lara entegre etme.

- 🟢 Gateway tarafında tool argument validation (AJV — `services/pi-gateway/src/validator.ts`, 6 endpoint)
- 🟢 Python tarafında validation sonuçlarını işleme (invalid args → retry with correction prompt — `tools/tool_schema_registry.py` + `agents/base.py` execute)
- 🟢 `_parse_text_tool_calls` fallback'i gateway'e taşıma (`services/pi-gateway/src/text-parser.ts`)
- 🟢 Tool schema registry — merkezi JSON Schema (`tools/tool_schema_registry.py` + gateway auto-register on startup)

### 14.4 — Model Routing `[🟢 TAMAMLANDI]`

- 🟢 Frontend Model Manager UI — provider/model listesi, agent-model eşleme

### 14.5 — pi-web-ui Chat Components Entegrasyonu `[🟢 TAMAMLANDI]`

pi-web-ui'nin hazır chat componentlerini frontend'e ekleme.

- 🟢 ChatPanel / AgentInterface web component embed (React wrapper)
- 🟢 Artifacts paneli — agent çıktılarını interaktif gösterme (HTML, SVG, Markdown render)
- 🟢 Attachment desteği — PDF, DOCX, XLSX, PPTX, görsel yükleme ve agent'a analiz ettirme
- 🟢 Document extraction — yüklenen dosyalardan metin çıkarma ve context'e ekleme
- 🟢 IndexedDB session persistence — tarayıcı tarafında konuşma geçmişi saklama
- 🟢 CORS proxy konfigürasyonu (browser'dan doğrudan provider çağrısı için)

### 14.6 — pi-agent-core Patterns (Advanced Agent Runtime) `[🟢 TAMAMLANDI]`

pi-agent-core'un gelişmiş agent runtime pattern'lerini Python agent'lara uyarlama.

- 🟢 Context Transformer pattern — mesaj dizisini LLM'e göndermeden önce dönüştürme (context window optimization)
- 🟢 Steering Messages — kullanıcının agent çalışırken araya girmesi (interrupt & redirect)
- 🟢 Follow-up Messages — agent durduğunda otomatik devam ettirme (auto-continue)
- 🟢 Otomatik multi-turn tool execution — tool result → next LLM call döngüsü pi-agent-core tarzı
- 🟢 `agents/agentic_loop.py` güncelleme — context transformer hook, steering message injection

### 14.7 — Coding Agent Yetenekleri `[🟢 TAMAMLANDI]`

pi-coding-agent'ın dosya işleme ve kod düzenleme pattern'lerini sisteme ekleme.

- 🟢 File tools — `read`, `write`, `edit` (find/replace), `bash` tool'ları agent'lara ekleme
- 🟢 Project understanding — `AGENTS.md` / proje context dosyaları otomatik yükleme
- 🟢 Session branching — konuşma dallanması (alternatif çözüm yolları deneme)
- 🟢 Session compaction — uzun konuşmalarda otomatik özetleme ve sıkıştırma
- 🟢 Skills sistemi — on-demand capability paketleri (pi-coding-agent skill format desteği)

### 14.8 — Multi-Channel Gateway Genişletme `[🟢 TAMAMLANDI]`

pi-mom (Slack bot) pattern'ini kullanarak Faz 11.5 multi-channel gateway'i hızlandırma.

- 🟢 Slack entegrasyonu (pi-mom pattern — mention/DM → agent response)
- 🟢 Discord bot adaptörü (aynı pattern)
- 🟢 Telegram bot adaptörü
- 🟢 Kanal-bağımsız mesaj normalizasyonu (pi-agent-core message format)
- 🟢 Docker sandbox isolation (kanal başına izole çalışma ortamı)

---

## Özet Tablo

| Faz                             | Durum           | İlerleme          |
| ------------------------------- | --------------- | ----------------- |
| Mevcut v2.0                     | 🟢 Tamamlandı   | ████████████ 100% |
| Faz 1 — Workflow Engine         | 🟢 Tamamlandı   | ████████████ 100% |
| Faz 2 — Domain Skills           | 🟢 Tamamlandı   | ████████████ 100% |
| Faz 2.5 — Browser Use           | 🔴 Planlanmış   | ░░░░░░░░░░░░ 0%   |
| Faz 3 — Veri Analizi            | 🟡 Kısmi        | ██░░░░░░░░░░ 17%  |
| Faz 4 — Gelişmiş RAG            | 🔴 Planlanmış   | ░░░░░░░░░░░░ 0%   |
| Faz 5 — Güvenlik                | 🟡 Kısmi        | ██░░░░░░░░░░ 20%  |
| Faz 6 — Performans              | 🟢 Tamamlandı   | ████████████ 100% |
| Faz 7 — API Entegrasyon         | 🟡 Kısmi        | ███░░░░░░░░░ 30%  |
| Faz 8 — Multimedya              | 🟡 Kısmi        | ██░░░░░░░░░░ 20%  |
| Faz 9 — Kişiselleştirme         | 🟢 Tamamlandı   | ████████████ 100% |
| Faz 10 — İşbirliği              | 🟢 Tamamlandı   | ████████████ 100% |
| Faz 11 — Otonom Ekosistem 🦞    | 🟡 Kısmi        | █████░░░░░░░ 50%  |
| Faz 12 — Kolektif Bilinç 🧬     | 🟡 Kısmi        | █████░░░░░░░ 40%  |
| Faz 13 — Kiro Entegrasyon 🔮    | 🟡 Devam ediyor | ███░░░░░░░░░ 30%  |
| Faz 14 — pi-mono Entegrasyon 🔌 | 🟢 Tamamlandı   | ████████████ 100% |

---

## Notlar

- Ana arayüz: **XP teması** (Windows XP tarzı masaüstü, çoklu pencere). Cockpit tab arayüzü artık ana girişte kullanılmıyor; giriş /desktop (XP) üzerinden yapılır.
- Her faz bağımsız olarak deploy edilebilir
- Öncelik sırası kullanıcı ihtiyacına göre değişebilir
- 🟢 = kod mevcut ve çalışıyor, 🟡 = kısmen uygulandı, 🔴 = henüz başlanmadı
- Her sprint sonunda bu dosya güncellenir
- Faz 11-12: OpenClaw / Moltbook ekosisteminden ilham alınmıştır
- Faz 13: Kiro IDE skill ve power entegrasyonu — geliştirme hızını artırmak için
- Faz 14: [badlogic/pi-mono](https://github.com/badlogic/pi-mono) entegrasyonu — 20+ LLM provider, unified gateway, gelişmiş chat UI, agent runtime framework
- İlham kaynakları: [openclaw.ai](https://openclaw.ai) · [Moltbook](https://moltbook.com) · [Forbes: Crustafarianism](https://www.forbes.com/sites/johnkoetsier/2026/01/30/ai-agents-created-their-own-religion-crustafarianism-on-an-agent-only-social-network/) · [pi-mono](https://github.com/badlogic/pi-mono)
