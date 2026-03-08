---
inclusion: manual
---

# Agent SOUL.md Context

Bu steering dosyası, multi-agent dashboard'daki agent kimlik dosyalarını Kiro'ya entegre eder.
`#agent-soul-context` ile chat'e eklendiğinde aktif olur.

## Agent Identity Sistemi

Her agent `data/agents/{role}/` altında 4 kimlik dosyasına sahip:

| Dosya          | İçerik                                                     |
| -------------- | ---------------------------------------------------------- |
| `SOUL.md`      | Kişilik, değerler, uzmanlık, iletişim stili, sınırlar      |
| `user.md`      | Kullanıcı tercihleri (Erkan: Türkçe, samimi, sprint-bazlı) |
| `memory.md`    | Cross-session hafıza — görev sonrası otomatik güncellenir  |
| `bootstrap.md` | Başlangıç protokolü                                        |

## Mevcut Agent'lar

- `orchestrator` — Görev analizi, decomposition, routing, synthesis
- `thinker` — Derin analiz, çok adımlı problem çözme
- `speed` — Hızlı yanıt, kod formatlama, pratik çözümler
- `researcher` — Web araştırma, kaynak doğrulama, sentez
- `reasoner` — Mantıksal doğrulama, chain-of-thought, matematiksel ispat
- `critic` — Kalite değerlendirme, fact-check, iyileştirme önerileri

## Memory Auto-Update

`agents/base.py` → `execute()` → görev tamamlandığında `IdentityManager.update_memory()` çağrılır.
Her başarılı görev `memory.md`'nin `## Recent Learnings` bölümüne eklenir.

## Kiro İçin Kullanım

Bir agent'ın kimliğini veya hafızasını görmek için:

```
data/agents/orchestrator/SOUL.md
data/agents/orchestrator/memory.md
```

Tüm agent'ların kimlik dosyaları `tools/agent_identity.py` → `IdentityManager` üzerinden yönetilir.
`get_system_prompt(role)` → SOUL.md + user.md + memory.md birleşik system prompt döner.
