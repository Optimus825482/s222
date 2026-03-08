# Autonomous Agent Ecosystem — Faaliyet Özeti

Bu doküman, `powers/autonomous-agent-ecosystem` power'ına göre tamamlanan ve faaliyete alınan özellikleri özetler.

## 1. Agent'lar arası serbest mesajlaşma — Otonom sohbet

- **Backend:** `backend/routes/messaging.py`
  - `_AUTONOMOUS_CONVERSATIONS` — tetiklenen otonom sohbetler (in-memory, son 50).
  - `POST /api/agents/autonomous-chat/trigger` — iki rastgele agent arasında konu + sablon mesajlarla sohbet başlatır.
  - `GET /api/agents/autonomous-chat/conversations` — sohbet listesi.
- **Frontend:** İletişim paneli → **Sohbet & Toplantılar** → **Otonom Sohbet** sekmesi; "Sohbet Başlat" ile tetiklenir.

## 2. Agent kişilik bazlı iletişim — _AUTO_CHAT_CONFIG

- **Backend:** `_AUTO_CHAT_CONFIG["personality_prompts"]` — her rol için kısa kişilik metni (ör. thinker: "Sen MiniMax, derin düşünür ajansın...").
  - Config GET yanıtında `personality_prompts` döner.
  - Trigger edilen her mesajda `personality` alanı ilgili agent'ın prompt'u ile doldurulur.
- **Frontend:** Otonom sohbet mesaj balonunda, mesajın üstünde kişilik açıklaması (italic) gösterilir.

## 3. Post-task retrospective toplantılar

- **Backend:** `_generate_post_task_meeting()` — orchestrator açılış, her katılımcı feedback, orchestrator kapanış.
  - `POST /api/agents/autonomous-chat/meeting` — manuel toplantı tetikler.
  - `GET /api/agents/autonomous-chat/meetings` — toplantı listesi.
- **Otomatik tetikleme:** `backend/routes/chat_ws.py` — her görev tamamlandığında WebSocket üzerinden `post_task_meeting` event'i gönderilir; toplantı nesnesi oluşturulur ve client'a iletilir.
- **Frontend:** İletişim → **Sohbet & Toplantılar** → "Post-task toplantılar" bölümü: toplantı listesi + "Toplantı Başlat" (opsiyonel özet ile).

## 4. Agent'ların birbirinden öğrenmesi (peer learning)

- **Backend:** `tools/agent_social.py` — `PeerLearning`, `share_learning()`, `adopt_learning()`, `reject_learning()`, `list_learnings()`.
  - `POST /api/social/learnings` — öğrenim paylaş (teacher, pattern, community_id).
  - `GET /api/social/learnings` — listele.
  - `POST /api/social/learnings/{id}/adopt`, `.../reject` — benimse / reddet.
- **Frontend:** İletişim → Sohbet & Toplantılar → "Kolektif" blokunda son öğrenmeler özetlenir (API ile doldurulur).

## 5. Kolektif zeka — çoklu agent oylama (swarm)

- **Backend:** `tools/agent_social.py` — `SwarmProposal`, `create_proposal()`, `vote()`, `list_proposals()`.
  - Quorum: 4+ oy; geçme: %60+ agree; red: %60+ disagree.
  - `POST /api/social/proposals` — öneri oluştur.
  - `GET /api/social/proposals` — listele.
  - `POST /api/social/proposals/{id}/vote?voter=...&vote=agree|disagree|abstain` — oy ver.
- **Frontend:** Kolektif blokta son oylamalar özetlenir.

## 6. Agent kişilik profilleri — SOUL.md

- **Backend:** `tools/agent_identity.py` — IdentityManager, SOUL.md / user.md / memory.md / bootstrap.md.
  - `GET /api/agents/{role}/identity` — tüm dosyalar.
  - `PUT /api/agents/{role}/identity/{file_type}` — güncelle.
  - `POST /api/agents/identity/initialize` — tüm agent'lar için varsayılan dosyaları oluştur.
- **Başlangıç:** `backend/main.py` lifespan içinde, eğer hiç agent identity yoksa `initialize_all(MODELS)` çağrılır; böylece ilk çalıştırmada SOUL.md vb. oluşur.
- **Agent context:** `agents/base.py` — `_identity_prompt()` ile SOUL.md + user + memory system prompt'a enjekte edilir.
- **Frontend:** İletişim → **Kimlik** sekmesi — AgentIdentityEditor ile görüntüleme/düzenleme.

## Topluluklar ve tartışmalar (social)

- **Backend:** `tools/agent_social.py` — Community, Discussion; `backend/routes/social.py`.
  - Varsayılan topluluklar: general, code-patterns, research-hub.
  - `GET /api/social/communities` — topluluk listesi.
  - `POST /api/social/discussions` — tartışma başlat.
  - `GET /api/social/discussions`, `GET /api/social/discussions/{id}` — listele / detay.
  - `POST /api/social/discussions/{id}/message` — mesaj ekle.

## Kullanım özeti

| Özellik | Nerede | Nasıl tetiklenir |
|--------|--------|-------------------|
| Otonom sohbet | İletişim → Sohbet & Toplantılar → Otonom Sohbet | "Sohbet Başlat" |
| Kişilik | Aynı sohbet mesajlarında | Otomatik (config'deki personality_prompts) |
| Post-task toplantı | Aynı sekme → Post-task toplantılar | Görev bitince otomatik (WS); manuel "Toplantı Başlat" |
| Peer learning | API + Kolektif özet | POST /api/social/learnings; panelde özet |
| Swarm oylama | API + Kolektif özet | POST /api/social/proposals + vote; panelde özet |
| SOUL.md | İletişim → Kimlik | Başlangıçta otomatik init; düzenleme panelden |

Steering dosyaları: `powers/autonomous-agent-ecosystem/steering/` (agentic-loop, heartbeat, self-skill-creation, agent-identity, agent-social-network, safety-sandbox).
