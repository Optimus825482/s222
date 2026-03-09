# Requirements Document

## Giriş

Bu doküman, multi-agent AI platformunun dört ana iyileştirme alanını kapsar: Memory İyileştirme, Agent İşbirliği, Performans İzleme ve Skill Genişletme. Mevcut sistem FastAPI backend, Next.js frontend, PostgreSQL + pgvector veritabanı ve Qdrant tabanlı vektör hafıza üzerine kuruludur. Agent'lar (thinker, speed, researcher, reasoner, critic, orchestrator, synthesizer) şu an bağımsız çalışmakta olup, bu iyileştirmeler ile daha koordineli, izlenebilir ve yetenekli bir sisteme dönüşecektir.

## Glossary

- **Memory_System**: `tools/memory.py` modülündeki hafıza yönetim katmanı. PostgreSQL + pgvector üzerinde vektör arama, kayıt, silme ve filtreleme işlemlerini yürütür.
- **Event_Bus**: `core/event_bus.py` modülündeki pub/sub mesajlaşma altyapısı. Channel bazlı subscribe, publish, broadcast ve middleware desteği sağlar.
- **Task_Delegation_Manager**: `core/task_delegation.py` modülündeki görev dağıtım sistemi. Agent'lar arası görev atama, fan-out, iptal ve ilerleme takibi yapar.
- **Performance_Collector**: `tools/performance_collector.py` modülündeki metrik toplama servisi. Agent ve skill bazlı response time, token usage, success rate kaydeder.
- **Skill_Registry**: `tools/dynamic_skills.py` modülündeki skill CRUD ve arama sistemi. Skill oluşturma, güncelleme, silme, arama ve disk'e yazma işlemlerini yönetir.
- **Domain_Module**: `tools/domain_skills.py` modülündeki alan bazlı skill paketi. Finance, legal, engineering gibi domain'lere özel tool setleri sunar.
- **Agent**: `agents/base.py` üzerinden türeyen LLM tabanlı otonom birim. Tool execution, context building, skill injection ve inter-agent iletişim yeteneklerine sahiptir.
- **Dashboard**: Frontend'deki (`frontend/src/`) performans metriklerini görselleştiren React bileşeni.
- **Message_Envelope**: Event_Bus üzerinden taşınan, sender, receiver, channel, payload ve metadata içeren mesaj yapısı.
- **Dead_Letter_Queue**: Event_Bus'taki teslim edilemeyen mesajların biriktirildiği kuyruk yapısı.
- **Middleware**: Event_Bus'ta mesajlar üzerinde publish öncesi dönüşüm veya filtreleme uygulayan katman.

---

## Requirements

### Requirement 1: Gelişmiş Hafıza Arama

**User Story:** Bir geliştirici olarak, agent hafızasında çoklu filtre ve tag kombinasyonlarıyla arama yapabilmek istiyorum, böylece ilgili bilgilere daha hızlı ve hassas erişebilirim.

#### Acceptance Criteria

1. WHEN bir arama sorgusu ve bir veya daha fazla tag filtresi verildiğinde, THE Memory_System SHALL yalnızca belirtilen tag'lere sahip kayıtları döndürecektir.
2. WHEN bir arama sorgusu, tarih aralığı ve similarity threshold birlikte verildiğinde, THE Memory_System SHALL üç filtreyi AND mantığıyla birleştirerek sonuç döndürecektir.
3. WHEN bir arama sorgusu verildiğinde, THE Memory_System SHALL sonuçları cosine similarity skoruna göre azalan sırada döndürecektir.
4. THE Memory_System SHALL her arama sonucunda memory_id, content, tags, similarity_score ve created_at alanlarını döndürecektir.
5. IF arama sorgusu boş string olarak verilirse, THEN THE Memory_System SHALL bir validation hatası döndürecektir.
6. WHEN bir arama sorgusu verildiğinde, THE Memory_System SHALL sonuçları 200ms içinde döndürecektir (1000 kayıt altı veri setlerinde).

---

### Requirement 2: Hafıza Tag Yönetimi

**User Story:** Bir geliştirici olarak, hafıza kayıtlarına tag ekleyip çıkarabilmek ve tag'leri listeleyebilmek istiyorum, böylece hafıza organizasyonunu kontrol edebilirim.

#### Acceptance Criteria

1. WHEN bir memory_id ve yeni tag listesi verildiğinde, THE Memory_System SHALL belirtilen tag'leri ilgili kayda ekleyecektir.
2. WHEN bir memory_id ve silinecek tag listesi verildiğinde, THE Memory_System SHALL belirtilen tag'leri ilgili kayıttan kaldıracaktır.
3. THE Memory_System SHALL sistemdeki tüm benzersiz tag'leri ve her tag'in kullanım sayısını listeleyecektir.
4. IF var olmayan bir memory_id ile tag işlemi yapılırsa, THEN THE Memory_System SHALL "memory not found" hatası döndürecektir.
5. WHEN bir tag eklendiğinde veya kaldırıldığında, THE Memory_System SHALL ilgili kaydın updated_at alanını güncelleyecektir.

---

### Requirement 3: Hafıza Deduplikasyon ve Temizlik

**User Story:** Bir geliştirici olarak, benzer veya süresi dolmuş hafıza kayıtlarının otomatik temizlenmesini istiyorum, böylece hafıza kalitesi yüksek kalır.

#### Acceptance Criteria

1. WHEN yeni bir hafıza kaydı eklenirken mevcut kayıtlarla cosine similarity skoru 0.85 üzerinde olan bir kayıt bulunursa, THE Memory_System SHALL yeni kaydı eklemeyip mevcut kaydın ID'sini döndürecektir.
2. WHEN yeni bir hafıza kaydı eklenirken mevcut kayıtlarla cosine similarity skoru 0.70 ile 0.85 arasında olan bir kayıt bulunursa, THE Memory_System SHALL mevcut kaydı güncelleyecektir.
3. WHEN yeni bir hafıza kaydı eklenirken mevcut kayıtlarla cosine similarity skoru 0.70 altında kalırsa, THE Memory_System SHALL yeni kaydı bağımsız olarak ekleyecektir.
4. THE Memory_System SHALL working_memory tipindeki kayıtları TTL süreleri dolduktan sonra otomatik olarak silecektir.
5. WHEN deduplikasyon işlemi tamamlandığında, THE Memory_System SHALL işlem sonucunu (skipped, updated, inserted) bir log kaydı olarak döndürecektir.

---

### Requirement 4: Agent Pub/Sub Mesajlaşma İyileştirmesi

**User Story:** Bir geliştirici olarak, agent'ların birbirleriyle topic bazlı mesajlaşabilmesini istiyorum, böylece agent'lar arası koordinasyon sağlanır.

#### Acceptance Criteria

1. WHEN bir Agent belirli bir channel'a subscribe olduğunda, THE Event_Bus SHALL o channel'a publish edilen tüm mesajları ilgili Agent'a iletecektir.
2. WHEN bir Agent bir mesaj publish ettiğinde, THE Event_Bus SHALL mesajı tüm subscriber'lara middleware zincirinden geçirerek iletecektir.
3. WHEN bir mesaj teslim edilemezse, THE Event_Bus SHALL mesajı Dead_Letter_Queue'ya ekleyecektir.
4. THE Event_Bus SHALL her channel için subscriber sayısı, toplam mesaj sayısı ve ortalama teslim süresini raporlayacaktır.
5. WHEN bir Agent wildcard pattern ile subscribe olduğunda (örn: "task.\*"), THE Event_Bus SHALL pattern'e uyan tüm channel'lardan mesaj iletecektir.
6. IF Dead_Letter_Queue kapasitesi dolduğunda yeni bir teslim edilemeyen mesaj gelirse, THEN THE Event_Bus SHALL en eski mesajı silerek yeni mesajı ekleyecektir.

---

### Requirement 5: Görev Kuyruğu ve Önceliklendirme

**User Story:** Bir geliştirici olarak, agent'lara atanan görevlerin öncelik sırasına göre işlenmesini istiyorum, böylece kritik görevler önce tamamlanır.

#### Acceptance Criteria

1. WHEN bir görev oluşturulurken priority değeri (1-5, 1 en yüksek) verildiğinde, THE Task_Delegation_Manager SHALL görevleri priority sırasına göre kuyruğa ekleyecektir.
2. WHEN bir Agent müsait olduğunda, THE Task_Delegation_Manager SHALL kuyruktaki en yüksek öncelikli görevi Agent'a atayacaktır.
3. WHEN aynı önceliğe sahip birden fazla görev varsa, THE Task_Delegation_Manager SHALL FIFO sırasına göre atama yapacaktır.
4. THE Task_Delegation_Manager SHALL her görev için oluşturulma zamanı, atanma zamanı, tamamlanma zamanı ve toplam bekleme süresini kaydedecektir.
5. WHEN bir görev iptal edildiğinde, THE Task_Delegation_Manager SHALL görevi kuyruktan kaldıracak ve iptal event'i yayınlayacaktır.
6. IF bir görev belirtilen timeout süresinde tamamlanmazsa, THEN THE Task_Delegation_Manager SHALL görevi "timed_out" durumuna geçirecek ve retry mekanizmasını tetikleyecektir.

---

### Requirement 6: Agent İşbirliği Protokolü

**User Story:** Bir geliştirici olarak, agent'ların karmaşık görevlerde birlikte çalışabilmesini istiyorum, böylece tek bir agent'ın kapasitesini aşan işler tamamlanabilir.

#### Acceptance Criteria

1. WHEN orchestrator Agent bir görevi fan-out olarak dağıttığında, THE Task_Delegation_Manager SHALL görevi belirtilen agent'lara paralel olarak atayacaktır.
2. WHEN fan-out görevlerinin tamamı tamamlandığında, THE Task_Delegation_Manager SHALL sonuçları birleştirip orchestrator Agent'a döndürecektir.
3. WHEN bir Agent başka bir Agent'a handoff yapmak istediğinde, THE Event_Bus SHALL mevcut context'i hedef Agent'a aktaracaktır.
4. THE Task_Delegation_Manager SHALL aktif görev sayısını, tamamlanan görev sayısını ve ortalama tamamlanma süresini raporlayacaktır.
5. IF fan-out görevlerinden biri başarısız olursa, THEN THE Task_Delegation_Manager SHALL başarısız görevi loglayacak ve kalan görevlerin sonuçlarını partial result olarak döndürecektir.

---

### Requirement 7: Performans Metrik Toplama

**User Story:** Bir geliştirici olarak, her agent'ın response time, token usage ve success rate metriklerini toplayabilmek istiyorum, böylece sistem performansını ölçebilirim.

#### Acceptance Criteria

1. WHEN bir Agent bir görevi tamamladığında, THE Performance_Collector SHALL response_time_ms, input_tokens, output_tokens, total_tokens ve success boolean değerlerini kaydedecektir.
2. WHEN bir Agent bir görevi tamamladığında, THE Performance_Collector SHALL kullanılan model adını ve skill_id bilgisini kaydedecektir.
3. THE Performance_Collector SHALL her Agent için son 1 saat, 24 saat ve 7 günlük ortalama response time değerlerini hesaplayacaktır.
4. THE Performance_Collector SHALL her Agent için success rate yüzdesini hesaplayacaktır.
5. WHEN metrik kaydı yapılırken, THE Performance_Collector SHALL Event_Bus üzerinden "metrics.recorded" event'i yayınlayacaktır.
6. IF metrik kaydı sırasında veritabanı bağlantı hatası oluşursa, THEN THE Performance_Collector SHALL metriği in-memory buffer'a yazacak ve bağlantı düzeldiğinde flush edecektir.

---

### Requirement 8: Performans Dashboard

**User Story:** Bir geliştirici olarak, agent performans metriklerini görsel bir dashboard üzerinden izleyebilmek istiyorum, böylece sistem sağlığını anlık takip edebilirim.

#### Acceptance Criteria

1. THE Dashboard SHALL her Agent için response time, token usage ve success rate metriklerini grafik olarak gösterecektir.
2. THE Dashboard SHALL son 1 saat, 24 saat ve 7 günlük zaman aralıklarında filtreleme yapabilecektir.
3. WHEN yeni bir metrik kaydedildiğinde, THE Dashboard SHALL 5 saniye içinde güncellenen veriyi gösterecektir.
4. THE Dashboard SHALL toplam sistem token kullanımını ve tahmini maliyeti gösterecektir.
5. THE Dashboard SHALL agent bazlı karşılaştırma tablosu sunacaktır (response time, success rate, task count sütunlarıyla).
6. WHEN bir Agent'ın success rate değeri %80 altına düştüğünde, THE Dashboard SHALL ilgili Agent'ı kırmızı renk ile vurgulayacaktır.
7. THE Dashboard SHALL dark theme ile uyumlu olacaktır.

---

### Requirement 9: Dashboard API Endpoint'leri

**User Story:** Bir geliştirici olarak, dashboard verilerini sunan REST API endpoint'leri istiyorum, böylece frontend performans verilerine erişebilir.

#### Acceptance Criteria

1. THE Backend SHALL `/api/metrics/agents` endpoint'i üzerinden tüm agent'ların özet metriklerini JSON formatında döndürecektir.
2. THE Backend SHALL `/api/metrics/agents/{agent_role}` endpoint'i üzerinden belirli bir agent'ın detaylı metriklerini döndürecektir.
3. WHEN `?period=1h|24h|7d` query parametresi verildiğinde, THE Backend SHALL metrikleri belirtilen zaman aralığına göre filtreleyecektir.
4. THE Backend SHALL `/api/metrics/system` endpoint'i üzerinden toplam token kullanımı, toplam görev sayısı ve sistem uptime bilgisini döndürecektir.
5. THE Backend SHALL `/api/metrics/agents/{agent_role}` endpoint'inden döndürülen JSON'u parse edip tekrar serialize ettiğinde aynı veri yapısını üretecektir (round-trip property).
6. IF geçersiz bir agent_role verilirse, THEN THE Backend SHALL 404 status kodu ve açıklayıcı hata mesajı döndürecektir.

---

### Requirement 10: Security Audit Skill

**User Story:** Bir geliştirici olarak, kod ve konfigürasyon dosyalarında güvenlik açıklarını tespit eden bir skill istiyorum, böylece güvenlik sorunlarını erken aşamada yakalayabilirim.

#### Acceptance Criteria

1. WHEN bir kod dosyası veya konfigürasyon verildiğinde, THE Skill_Registry SHALL security-audit skill'ini çalıştırarak OWASP Top 10 kategorilerinde tarama yapacaktır.
2. THE security-audit skill SHALL her bulguyu severity (critical, high, medium, low), kategori, dosya yolu ve satır numarası ile raporlayacaktır.
3. WHEN tarama tamamlandığında, THE security-audit skill SHALL bulguları severity'ye göre azalan sırada listeleyecektir.
4. THE security-audit skill SHALL .env dosyalarında hardcoded secret tespiti yapacaktır.
5. IF taranan dosyada güvenlik açığı bulunamazsa, THEN THE security-audit skill SHALL "no vulnerabilities found" mesajı ile temiz rapor döndürecektir.

---

### Requirement 11: Data Pipeline Skill

**User Story:** Bir geliştirici olarak, veri pipeline'ları tasarlayıp doğrulayabilen bir skill istiyorum, böylece ETL süreçlerini hızlıca oluşturabilirim.

#### Acceptance Criteria

1. WHEN bir veri kaynağı ve hedef tanımı verildiğinde, THE Skill_Registry SHALL data-pipeline skill'ini çalıştırarak pipeline şeması oluşturacaktır.
2. THE data-pipeline skill SHALL her pipeline adımı için input schema, output schema ve transformation logic tanımlayacaktır.
3. WHEN bir pipeline şeması doğrulanırken, THE data-pipeline skill SHALL schema uyumluluğunu kontrol edecektir (bir adımın output schema'sı sonraki adımın input schema'sıyla uyumlu olmalıdır).
4. THE data-pipeline skill SHALL PostgreSQL, CSV ve JSON veri formatlarını destekleyecektir.
5. IF pipeline şemasında schema uyumsuzluğu tespit edilirse, THEN THE data-pipeline skill SHALL uyumsuz adımları ve beklenen/gerçek schema'ları raporlayacaktır.

---

### Requirement 12: API Design Skill

**User Story:** Bir geliştirici olarak, REST API endpoint'lerini tasarlayıp OpenAPI spec oluşturabilen bir skill istiyorum, böylece API tasarım sürecini hızlandırabilirim.

#### Acceptance Criteria

1. WHEN bir API gereksinimi tanımı verildiğinde, THE Skill_Registry SHALL api-design skill'ini çalıştırarak OpenAPI 3.0 uyumlu spec oluşturacaktır.
2. THE api-design skill SHALL her endpoint için path, method, request body schema, response schema ve error response tanımlayacaktır.
3. THE api-design skill SHALL oluşturulan OpenAPI spec'i JSON formatında serialize edip tekrar parse ettiğinde aynı yapıyı üretecektir (round-trip property).
4. WHEN bir mevcut FastAPI route dosyası verildiğinde, THE api-design skill SHALL mevcut endpoint'leri analiz edip eksik dokümantasyonu tamamlayacaktır.
5. IF oluşturulan spec OpenAPI 3.0 standardına uygun değilse, THEN THE api-design skill SHALL validation hatalarını listeleyecektir.

---

### Requirement 13: Test Automation Skill

**User Story:** Bir geliştirici olarak, kod için otomatik test senaryoları oluşturabilen bir skill istiyorum, böylece test coverage'ı artırabilirim.

#### Acceptance Criteria

1. WHEN bir Python fonksiyonu veya sınıfı verildiğinde, THE Skill_Registry SHALL test-automation skill'ini çalıştırarak pytest uyumlu test dosyası oluşturacaktır.
2. THE test-automation skill SHALL her fonksiyon için en az bir happy path, bir edge case ve bir error case test senaryosu oluşturacaktır.
3. THE test-automation skill SHALL async fonksiyonlar için pytest-asyncio uyumlu test'ler oluşturacaktır.
4. WHEN bir test dosyası oluşturulduğunda, THE test-automation skill SHALL gerekli import'ları ve fixture'ları dahil edecektir.
5. IF verilen kod dosyası parse edilemezse, THEN THE test-automation skill SHALL parse hatasını ve beklenen format bilgisini döndürecektir.

---

### Requirement 14: Performance Profiling Skill

**User Story:** Bir geliştirici olarak, kod performansını analiz edip darboğazları tespit eden bir skill istiyorum, böylece optimizasyon fırsatlarını belirleyebilirim.

#### Acceptance Criteria

1. WHEN bir Python dosyası veya fonksiyonu verildiğinde, THE Skill_Registry SHALL performance-profiling skill'ini çalıştırarak zaman karmaşıklığı analizi yapacaktır.
2. THE performance-profiling skill SHALL tespit edilen her darboğaz için dosya yolu, fonksiyon adı, tahmini Big-O karmaşıklığı ve optimizasyon önerisi sunacaktır.
3. WHEN bir veritabanı sorgusu verildiğinde, THE performance-profiling skill SHALL N+1 query, eksik index ve full table scan tespiti yapacaktır.
4. THE performance-profiling skill SHALL bulguları impact seviyesine (critical, high, medium, low) göre sıralayacaktır.
5. IF analiz edilen kodda performans sorunu bulunamazsa, THEN THE performance-profiling skill SHALL "no performance issues found" mesajı ile temiz rapor döndürecektir.

---

### Requirement 15: Skill Kayıt ve Keşif Sistemi

**User Story:** Bir geliştirici olarak, yeni eklenen skill'lerin otomatik olarak sisteme kaydedilmesini ve aranabilir olmasını istiyorum, böylece skill yönetimi kolaylaşır.

#### Acceptance Criteria

1. WHEN yeni bir skill tanımı verildiğinde, THE Skill_Registry SHALL skill'i benzersiz bir skill_id ile veritabanına kaydedecektir.
2. THE Skill_Registry SHALL her skill için name, description, version, category, input_schema ve output_schema alanlarını saklayacaktır.
3. WHEN bir arama sorgusu verildiğinde, THE Skill_Registry SHALL skill adı ve açıklamasında fuzzy search yaparak eşleşen skill'leri döndürecektir.
4. THE Skill_Registry SHALL skill'leri category bazında filtrelemeye izin verecektir.
5. WHEN bir skill silindiğinde, THE Skill_Registry SHALL ilgili skill'in tüm referanslarını ve disk dosyalarını temizleyecektir.
6. FOR ALL geçerli skill tanımları, THE Skill_Registry SHALL skill'i kaydedip tekrar okuyarak aynı veri yapısını üretecektir (round-trip property).
