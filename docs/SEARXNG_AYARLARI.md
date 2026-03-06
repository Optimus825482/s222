# SearXNG Sunucu Ayarları (Multi-Agent Dashboard)

Dashboard’daki `web_search` aracı, arama isteklerini **SearXNG** instance’ına gönderir. “No results found” alıyorsan çoğu zaman instance tarafında motorlar kapalı veya ağ erişimi yoktur.

## 1. Instance’ın çalıştığını doğrula

Tarayıcıda veya backend’in çalıştığı makineden:

```bash
curl -s "http://searxng-pwcsc8ow08oks0ggokwoo8ww.77.42.68.4.sslip.io/search?q=test&format=json" | head -500
```

- **200 OK + JSON içinde `results` dolu** → Instance ve motorlar çalışıyor.
- **200 OK ama `results: []`** → Motorlar kapalı veya hepsi hata veriyor (aşağıdaki ayarlar).
- **Bağlantı hatası** → Ağ/firewall (backend’in bu URL’e erişebildiğinden emin ol).

## 2. Arama motorlarını aç (önemli)

SearXNG varsayılanda bazı motorları kapalı gelebilir. En az birkaç motorun **açık** olması gerekir.

### Docker / docker-compose ile kurulum

Genelde `settings.yml` veya ortam değişkeni ile yapılandırılır. Örnek `settings.yml` (veya container içi `/etc/searxng/settings.yml`):

```yaml
# Arama motorları — en az birkaçı true olmalı
engines:
  - name: duckduckgo
    engine: duckduckgo
    disabled: false
  - name: bing
    engine: bing
    disabled: false
  - name: google
    engine: google
    disabled: false
  # İstersen brave, startpage vb. ekle
```

- **Coolify / Docker**: Proje içinde `settings.yml` veya `settings.yaml` varsa `engines` bölümünde `disabled: false` olan motorlar olduğundan emin ol.
- **Resmi Docker image**: Bazen engine listesi environment ile override edilir; dokümantasyonda “enable engines” kısmına bak.

### Hızlı test (hangi motorlar açık?)

Tarayıcıda instance’a gir → **Preferences** → **Engines** (veya **Engine stats**). Açık ve yeşil görünen motorlar kullanılıyor; hepsi kapalı/kırmızıysa sonuç gelmez.

## 3. JSON API’nin açık olduğundan emin ol

Dashboard istekleri `format=json` ile yapar. Birçok public instance JSON’u varsayılan açıktır; eğer “format not allowed” benzeri bir kısıtlama yoksa ek ayar gerekmez.

## 4. Ağ (outgoing)

SearXNG sunucusunun **dışarıya** (Google, Bing, DuckDuckGo vb.) HTTPS isteği atabilmesi gerekir. Sunucu tamamen kapalı ağdaysa veya firewall dış erişimi engelliyorsa yine `results: []` gelir.

## 5. Dashboard tarafı (.env)

`.env` içinde URL’i **sonunda slash olmadan** ver:

```env
SEARXNG_URL=http://searxng-pwcsc8ow08oks0ggokwoo8ww.77.42.68.4.sslip.io
```

Uygulama buna otomatik `/search` ekler.

---

## 6. Sık görülen motor hataları (log’ta gördüklerin)

Sunucu log’unda aşağıdakileri görüyorsan ilgili motoru **kapat**, yerine çalışan motorları aç.

| Hata | Motor | Sebep | Ne yapmalı |
|------|--------|-------|------------|
| `401 Unauthorized` / `www.reuters.com` | **reuters** | Reuters API artık yetki istiyor | **reuters** motorunu **kapat** (disabled: true). |
| `SearxEngineCaptchaException: CAPTCHA (tr-tr)` | **duckduckgo** | DuckDuckGo sunucu IP’sine CAPTCHA gösteriyor | **duckduckgo**’yu kapat veya sadece düşük trafikte aç; **bing**, **startpage**, **mojeek** kullan. |
| `Too many request (suspended_time=3600)` | **brave** | Brave istek limiti (1 saat blok) | **brave**’i kapat veya çok az istek atacak şekilde kullan. |

### Önerilen motor seti (sunucudan çalışanlar)

Bu motorlar genelde datacenter IP’lerinden de sonuç döner; CAPTCHA/401 riski daha düşük:

- **bing** — Çoğu kurulumda çalışır.
- **startpage** — Proxy üzerinden arama, CAPTCHA daha seyrek.
- **mojeek** — Kendi indeksi, rate limit daha yumuşak.
- **qwant** — Avrupa odaklı, sunucudan deneyebilirsin.
- **wikipedia** — Genel bilgi sorguları için iyi (İngilizce/Türkçe).

**Kapatman iyi olanlar (log’unda hata varsa):** reuters (401), duckduckgo (CAPTCHA), brave (rate limit), gerekirse google.

### SearXNG’de motoru nasıl kapatırsın?

- **Settings dosyası (settings.yml):** İlgili motorun altına `disabled: true` ekle.
- **Coolify / env:** Bazı imajlar engine listesini env ile alır; reuters/duckduckgo/brave’i çıkar.
- **Arayüz:** Preferences → Engines → hata veren motorun yanındaki tik’i kaldır.

En az **bing + startpage** (veya mojeek) açık kalsın; tekrar arama atıp log’ta hata kalmadığını kontrol et.

### Görsel arayüzde (Preferences → Motorlar) yapılacaklar

1. **GENEL** sekmesine gir — “Şu anda kullanılan arama motorları” listesi açılır.
2. **Brave** — Sarı uyarı (~55) veya log’ta “Too many request” varsa: yanındaki **İzin ver** anahtarını **kapat** (gri X).
3. **DuckDuckGo** — Zaten kapalıysa dokunma. Açıksa ve kırmızı (örn. ! 30) ise **kapat**.
4. **Mojeek** — Kırmızı ! 0 ise sonuç dönmüyor demektir; **kapat**abilirsin. Bing + startpage yeterli.
5. **Bing, Startpage, Google, Yahoo** — Yeşil (! 100 / ! 95) ise **açık** kalsın; kapatma.
6. **HABERLER** sekmesine geç — **Reuters** varsa ve log’ta 401 görüyorsan **kapat**.
7. Sayfanın altındaki **Kaydet** butonuna bas — Ayarlar çerezde saklanır, kaydetmezsen motor değişiklikleri uygulanmaz.

---

**Özet:** “Araçlar çalışmıyor” / “No results” çoğu zaman SearXNG’de **hiç motor açık değil**, **motorlar hata veriyor** (Reuters 401, DuckDuckGo CAPTCHA, Brave rate limit) veya **outgoing erişim yok** demektir. Bölüm 6’daki gibi reuters/duckduckgo/brave’i kapat, bing/startpage/mojeek aç; Preferences → Engines’ten doğrula.
