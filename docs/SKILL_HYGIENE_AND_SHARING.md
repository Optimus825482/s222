# Skill Hygiene & Cross-Agent Skill Sharing

## Skill hygiene

- **Manuel:** Yetenek Merkezi (Skills Hub) başlığındaki **"Skill hygiene"** butonu ile çalıştırılır.  
  - **Hygiene (kuru):** Sadece rapor döner; hiçbir skill silinmez/devre dışı bırakılmaz.  
  - **Skill hygiene:** Kalite kontrolü uygulanır; zayıf/çöp skill’ler devre dışı bırakılır, değerli bilgi mümkünse memory’e taşınır.
- **Otomatik:** Orchestrator her ~10 görevde bir (yaklaşık %10 olasılıkla) `run_hygiene_check(dry_run=False)` çağırır.
- **API:** `POST /api/skills/hygiene?dry_run=true|false` (auth gerekli).

## Skill oluşturma — sadece Orchestrator

- **create_skill** ve **research_create_skill** sadece **orchestrator** rolünde tanımlıdır (`tools/sandbox.py` ROLE_ALLOWLIST).
- Diğer agent’lar (thinker, speed, researcher, reasoner, critic) bu araçlara sahip değildir; skill oluşturamazlar.
- Görevde ihtiyaç duyulan skill’i **orchestrator** oluşturur ve alt agent’lara atar.

## Skill paylaşımı (cross-agent)

- Orchestrator bir skill’i **create_skill** veya **research_create_skill** ile oluşturur.
- Alt agent’lara vermek için:
  - **decompose_task:** `sub_tasks` içinde her alt göreve `skills: ["skill-id"]` ekler.
  - **spawn_subagent:** `skill_ids: ["skill-id", ...]` argümanı ile verir.
- Base agent (`agents/base.py`) görev çalıştırırken, atanmış `skill_ids` için `get_full_skill_context(sid)` ile SKILL.md içeriğini alır ve prompt’a `<skill id="...">` blokları olarak ekler. Böylece o görevi yapan agent skill’i kullanır.

## powers/skill-creator ile uyum

- **SKILL.md formatı:** `tools/dynamic_skills.py` Kiro formatında frontmatter (name, description, category, keywords) + gövde yazar; `powers/skill-creator/steering/skill-writing-guide.md` ile uyumludur.
- **Kalite:** `tools/skill_hygiene.py` çöp/tekrarlayan içeriği temizler; skill-creator’daki `validate_skill` (MCP) SKILL.md yapı/kalite değerlendirmesi için kullanılabilir (opsiyonel entegrasyon).
