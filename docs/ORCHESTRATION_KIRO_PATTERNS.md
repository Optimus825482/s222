# Kiro'dan Alınan Orkestrasyon ve Agent Referansları

Bu dokümanda `~/.kiro/skills` ve `~/.kiro/agents` dizinlerinden projeye alınan pattern'ler ve kurallar özetlenir. Detaylar ilgili skill'lerin `reference.md` dosyalarında.

## Alınan Kaynaklar

| Kaynak (Kiro) | Projede nerede |
|---------------|----------------|
| **orchestrating-swarms** | Paralel specialist, pipeline, swarm pattern'leri → `agent-orchestration-multi-agent-optimize/reference.md` |
| **resolve_parallel** | Analiz → plan (bağımlılıklar) → paralel invoke akışı → `agent-orchestration-multi-agent-optimize/reference.md` |
| **orchestrator / master-orchestrator** | Plan kontrolü, domain boundary, agent seçim tablosu → `agent-orchestration-multi-agent-optimize/reference.md` |
| **prompt-engineer** | Prompt analiz yapısı (reasoning, structure, few-shot, complexity) → `agent-orchestration-improve-agent/reference.md` |
| **performance-oracle** | Metrik çerçevesi, benchmark'lar, çıktı formatı → `agent-orchestration-multi-agent-optimize/reference.md` |

## Kısa Özet

- **Orkestrasyon pattern'leri:** Paralel uzmanlar, pipeline (task bağımlılıkları), swarm (görev havuzu + worker'lar).
- **Paralel çözüm akışı:** Analiz → plan (TodoWrite + mermaid) → her item için ayrı agent paralel → commit/resolve.
- **Orchestrator kuralları:** PLAN/plan kontrolü, proje tipi (WEB/MOBILE/BACKEND), agent sınırları, çakışma çözümü.
- **Prompt analizi:** Simple change, reasoning, structure, examples, complexity, specificity, prioritization, conclusion; çıktı yapısı.
- **Performans çerçevesi:** Algoritma, DB, bellek, cache, ağ, frontend; benchmark kuralları; özet → kritik konular → öneriler.

## İlgili skill'ler

- `.cursor/skills/agent-orchestration-improve-agent/` — Tekil agent iyileştirme (metrik, prompt, test, rollout).
- `.cursor/skills/agent-orchestration-multi-agent-optimize/` — Çoklu agent optimizasyonu (profil, orkestrasyon, maliyet).

## Uygulamada kullanım

- **Performance baseline:** `GET /api/eval/baseline` ve sidebar’daki Eval panelinde “Performance baseline” kartı (task success %, satisfaction, latency, token ratio + skill’deki hedef metin).
- **Orkestrasyon pattern etiketleri:** Pipeline seçicide her pipeline tipi Kiro pattern’ine eşlendi (Paralel uzmanlar, Pipeline, Swarm); mobilde açıklama açıldığında “Orkestrasyon: …” satırı gösterilir.
- **Agent geliştirme tool'ları:** Orchestrator ve Thinker `get_agent_baseline` (performans baseline) kullanabilir; Orchestrator `get_best_agent` ile task tipine göre en iyi agent'ı seçebilir.
- **Yeni skill'ler (SKILL_REGISTRY):** `code-review` (kod/PR inceleme), `agent-improvement` (baseline → failure analysis → prompt/rollout), `changelog-release` (changelog ve release notları).
