---
inclusion: manual
---

# Ant Colony Workflow — Karınca Kolonisi Orkestrasyon Modeli

Karmaşık, çok dosyalı görevlerde biyolojik karınca kolonisi pattern'lerini uygulayan iş akışı. Basit görevlerde devreye girmez — sadece karmaşıklık eşiği aşıldığında aktif olur.

## Aktivasyon Koşulları

Bu iş akışı yalnızca aşağıdaki koşullardan en az biri sağlandığında uygulanır:

- 3+ dosya değişikliği gerektiren görevler
- Refactoring, migration veya sistem genelinde değişiklik
- Birden fazla modül/katman etkileyen feature geliştirme
- Kullanıcı açıkça "colony", "karınca", "paralel" veya "çoklu ajan" dediğinde

Tek dosya düzenlemesi, basit soru-cevap veya küçük fix'lerde bu steering'i ATLA.

## Faz Modeli

### Faz 1: Keşif (Scouting)

Göreve başlamadan önce etkilenen alanı haritalandır.

- context-gatherer sub-agent ile codebase keşfi yap
- Qdrant'ta `workspace-fact` ve `bug-fix` tag'leriyle ilgili hafıza ara
- Etkilenen dosyaları, bağımlılıkları ve risk noktalarını listele
- Keşif sonuçlarını kısa bir iç plan olarak tut (kullanıcıya gösterme, iç bağlam olarak kullan)

Keşif çıktı formatı (iç kullanım):

```
SCOUT_INTEL:
- files: [etkilenen dosya listesi]
- dependencies: [dosyalar arası bağımlılıklar]
- risks: [çakışma/kırılma riskleri]
- approach: [önerilen sıralama]
```

### Faz 2: Plan ve Doğrulama

Keşif sonuçlarından yürütülebilir görev listesi oluştur.

- Her görev için: başlık, dosya kapsamı, öncelik (1-5), bağımlılık
- Dosya çakışması kontrolü: aynı dosyayı değiştiren görevler sıralı çalışmalı
- Bağımlılık sıralaması: import eden dosya, import edilen dosyadan SONRA değişmeli
- Plan doğrulama: en az 1 yürütülebilir görev olmalı, dosya kapsamı boş olmamalı

Plan geçersizse (görev üretilemedi veya dosya kapsamı eksik) → keşif fazına dön, farklı açıdan bak. Maksimum 2 recovery turu.

### Faz 3: Yürütme (Working)

Görevleri öncelik ve bağımlılık sırasına göre çalıştır.

- Bağımsız görevleri PARALEL sub-agent'larla çalıştır (invokeSubAgent)
- Bağımlı görevleri SIRALI çalıştır
- Her görev tamamlandığında sonucu Qdrant'a feromon olarak kaydet:
  - Başarılı → `continual-learning` tag, ne yapıldı + hangi dosyalar değişti
  - Başarısız → `bug-fix` tag, hata pattern'i + root cause

Hata pattern takibi: aynı hata tipi 2+ kez tekrarlanırsa (type error, import error, vb.) → dur, root cause analizi yap, yaklaşımı değiştir. Körce tekrarlama YASAK.

Görev üretim limiti: toplam 20 görev. Alt görev üretimi ilerleme > %70 ise maksimum 2.

### Faz 4: Denetim (Reviewing)

Tüm değişiklikler tamamlandıktan sonra kalite kontrolü.

- getDiagnostics ile tüm değişen dosyaları kontrol et
- Hata varsa fix görevi oluştur ve Faz 3'e dön
- agentic-eval steering'indeki rubric-based scoring'i uygula (code rubric, threshold 0.8)
- Review sonucunu kullanıcıya kısa özetle sun

## Feromon Sistemi (Qdrant Memory)

Görevler arası dolaylı iletişim Qdrant üzerinden yapılır. Doğrudan "feromon bırakıyorum" deme — sessizce kaydet.

| Durum            | Tag                  | İçerik                               |
| ---------------- | -------------------- | ------------------------------------ |
| Keşif bulgusu    | `workspace-fact`     | Dosya yapısı, bağımlılık bilgisi     |
| Başarılı görev   | `continual-learning` | Ne yapıldı, hangi pattern işe yaradı |
| Başarısız görev  | `bug-fix`            | Hata pattern'i, root cause, çözüm    |
| Tekrarlayan hata | `gotcha`             | Framework quirk veya edge case       |

Dedup protokolü: kaydetmeden önce benzer içerik ara. Similarity > 0.85 → kaydetme. 0.7-0.85 → güncelle. < 0.7 → yeni kayıt.

## Uyarlanabilir Eşzamanlılık

- Başlangıç: 2 paralel sub-agent
- Her başarılı batch sonrası: +1 (maksimum 4)
- Hata alınırsa: -1
- Tek dosya çakışması varsa: o görev sıraya alınır, diğerleri paralel devam eder

## Yuva Sıcaklığı (İlerleme Bazlı Davranış Değişimi)

- İlerleme < %30 → Keşif odaklı, geniş kapsamlı araştırma
- İlerleme %30-%70 → Normal yürütme, alt görev üretimi serbest
- İlerleme > %70 → Kapanış modu: sadece fix ve doğrulama, yeni keşif YASAK

## Sürü Oylaması (Quorum)

Birden fazla sub-agent aynı dosyayı değiştirmeyi öneriyorsa:

- Önerileri birleştir, tekrarları ele
- 2+ agent tarafından önerilen değişikliğin önceliğini yükselt
- Çelişen öneriler varsa → kullanıcıya sor

## Mevcut Sistemle Entegrasyon

- `agentic-eval.md` steering'i Faz 4'te (denetim) otomatik devreye girer
- `continual-learning.md` steering'i feromon kayıtları için zaten aktif
- `agents/orchestrator.py` backend tarafında kendi routing'ini yapar — bu steering Kiro IDE tarafındaki davranışı yönlendirir, orchestrator ile çakışmaz
- Sub-agent seçimi: context-gatherer (keşif), general-task-execution (yürütme), test-engineer (doğrulama gerekirse)

## Anti-Pattern'ler

- Basit görevde colony workflow başlatma — overhead'i haketmez
- Keşif yapmadan doğrudan yürütmeye geçme — kör uçuş
- Aynı hatayı 3+ kez tekrarlama — dur ve yaklaşım değiştir
- 20+ görev üretme — kapsam şişmesi, böl ve fethet
- Feromon (memory) kayıtlarını kullanıcıya anlatma — sessiz çalış
