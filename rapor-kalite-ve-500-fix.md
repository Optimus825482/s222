# rapor-kalite-ve-500-fix

## Overview

Multi-agent-dashboard için iki kritik başlığı tek program altında yürütmek:

1) Rapor kalitesini kalıcı iyileştirmek
2) Görsel oluşturma/indirme akışındaki HTTP 500 hatalarını düşürmek ve gözlemlenebilir hale getirmek

## Project Type

BACKEND + ORKESTRASYON + KALITE GUVENCE

## Success Criteria

- Rapor kalite skoru için ölçülebilir metrik seti tanımlı ve pipeline'a bağlı
- HTTP 500 oranı belirlenen hedefin altına iner ve kök neden kategorileri raporlanır
- Kalite gate ve hata gate CI/operasyon akışına eklenir
- Sonuç raporu standart formatta üretilebilir

## Task Breakdown

- [ ] T1: Baseline ve metrik sözleşmesi (Thinker)
  - INPUT: Mevcut rapor örnekleri, hata logları
  - OUTPUT: Kalite KPI listesi + 500 hata sınıflandırma matrisi
  - VERIFY: KPI ve sınıflar dokümante, ekip onayı alınmış

- [ ] T2: Kök neden analizi ve hipotez doğrulama (Reasoner)
  - INPUT: 500 stack trace/istek örnekleri, akış haritası
  - OUTPUT: Önceliklendirilmiş kök neden listesi ve doğrulama senaryoları
  - VERIFY: Her kök neden için yeniden üretim adımı veya güçlü kanıt

- [ ] T3: Uygulama düzeltmeleri (Speed)
  - INPUT: Onaylı kök neden listesi
  - OUTPUT: HTTP 500 azaltan kod/akış düzeltmeleri + koruyucu kontroller
  - VERIFY: Kritik senaryolarda 5xx üretilemez, hata durumları kontrollü 4xx/uygun mesaj

- [ ] T4: Kalıcı rapor kalite iyileştirmesi (Researcher + Speed)
  - INPUT: KPI sözleşmesi, mevcut rapor üretim akışı
  - OUTPUT: Şablon/puanlama/validasyon iyileştirmeleri
  - VERIFY: Örnek raporlarda kalite KPI hedeflerinin sağlanması

- [ ] T5: Kalite kapısı ve gözlemlenebilirlik (Critic)
  - INPUT: KPI, hata matrisi, test sonuçları
  - OUTPUT: Quality gate kriterleri + 500 alarm/eşik kontrol listesi
  - VERIFY: Gate fail/pass kuralları çalışır, eksik kalite durumunda bloklama olur

- [ ] T6: Koordinasyon ve teslim raporu (Orchestrator)
  - INPUT: T1-T5 çıktıları
  - OUTPUT: Tekil sonuç raporu, kararlar, kalan aksiyonlar
  - VERIFY: Tüm DoD'ler karşılandı işaretli, bağımlılıklar kapalı

## Done When

- [ ] Rapor kalite KPI'ları sürekli ölçülür durumda
- [ ] HTTP 500 hataları için kök nedenler kapatılmış ve regresyon koruması var
- [ ] Operasyonel gate/alarmlar aktif
- [ ] Sonuç raporu üretildi ve paylaşılabilir

## Delegasyon Matrisi

- T1 -> Thinker (metrik sözleşmesi, KPI tanımı)
- T2 -> Reasoner (kök neden analizi, kanıt)
- T3 -> Speed (hızlı ve kontrollü düzeltme implementasyonu)
- T4 -> Researcher + Speed (rapor kalite iyileştirmeleri)
- T5 -> Critic (quality gate, bloklama kuralları, alarm eşikleri)
- T6 -> Orchestrator (sentez, nihai teslim)

## Zorunlu Quality Gate (Çıktı Üretmeden Önce)

1. Kapsam kapısı

- Değişen dosyalar görev kapsamı ile eşleşmeli.
- Kapsam dışı değişiklik varsa çıktı bloklanır.

1. Statik kalite kapısı

- Frontend: `npm --prefix frontend run lint`
- Frontend: `npm --prefix frontend run build`

1. Davranış kapısı

- Backend: `pytest tests -q`
- Smoke backend: `Invoke-WebRequest http://localhost:8001/api/db/health`
- Smoke frontend: `Invoke-WebRequest http://localhost:3015`

1. Yayın öncesi kanıt kapısı

- En son çalıştırılan lint/test/build/smoke çıktıları saklanmış olmalı.
- Bu kanıtlar yoksa "tamamlandı" denmez.

## Anlık Kritik Riskler (Öncelikli)

- Kritik-1: Agent image kaydı ile backend indirme dizini uyumsuz olabilir.
  - Agent yazımı: `data/images`
  - Backend indirme beklentisi: `backend/data/images`
- Kritik-2: Model whitelist tutarsızlığı (agent vs backend) nedeniyle öngörülemez fallback davranışı.
- Kritik-3: Retry + timeout toplam süresi uzun; kullanıcı tarafında başarısızlık algısını artırabilir.

## Karar Ağacı (Gate Fail Durumu)

- Lint fail -> ilgili dosya düzelt -> lint tekrar.
- Build fail -> tip/sınır ihlali düzelt -> build tekrar.
- Test fail -> kırılan senaryoyu kök nedenle düzelt -> tam test tekrar.
- Smoke fail -> servis/port/route doğrula -> smoke tekrar.
- Herhangi bir fail durumunda çıktı statüsü: "bloklu + sonraki aksiyon".
