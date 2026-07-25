# SÜRÜ — Bir Parite Belgeseli (çalışma adı)
### Storyboard v1 · hedef süre ~90 sn · 1080×1920 dikey (LinkedIn) + 1920×1080 yatay (web)

Veri: `data/cattle-parity.json` (US/EU/TR, 2015=100) + `data/cattle-us.json` (1971→)
Palet: US `#3987e5` · EU `#d95926` · TR `#199e70` (doğrulanmış, koyu zemin `#1a1a19`)
Tipografi: IBM Plex Sans (başlık 700, metin 400), IBM Plex Mono (sayılar)

| # | sn | Sahne | Ekranda | Kamera | Anlatım (TR) |
|---|----|-------|---------|--------|--------------|
| 1 | 0–8 | **Soğuk açılış** | Boş koyu ekran; tek satır sayaç: "1 kg sığır eti = ? kg yem". Sayı 0,58'den yukarı akar | statik | "Bir kilo et, kaç kilo yem eder? Bu tek oran, bir sektörün kaderini anlatır." |
| 2 | 8–22 | **55 yıl tek çizgide** | ABD çizgisi 1971'den itibaren kendini çizer (4-5 sn), eksenler sade | geniş açı | "Amerika, 1971'den bugüne. Yetmişlerin emtia şokları, seksenlerin çiftlik krizi… çizgi hep nefes aldı." |
| 3 | 22–34 | **2014 zirvesi** | Kamera 2012–2016'ya zumlar; zirve noktası pulse + etiket "2014: kuraklık sonrası kıtlık" | yavaş zum | "2014'te tarihî bir zirve: yıllarca süren kuraklık sürüyü küçültmüştü — az hayvan, pahalı et." |
| 4 | 34–50 | **2020→26 büyük sıkışma-patlama** | Kamera son on yıla kayar; 2020 covid çukuru gri bant, 2022→26 tırmanış turuncu-kırmızı ısı ile dolar; canlı sayaç 1,62'ye koşar | pan + zum | "Sonra pandemi… ve ardından tarihin en büyük sürü tasfiyesi. Bugün parite endeksi 1,62 — et, yeme karşı 2015'ten bu yana yüzde 62 değerlendi." |
| 5 | 50–62 | **AB sahneye girer** | Kamera geri çekilir, eksen 2015=100'e morfolur; AB çizgisi soldan süzülür, uçlara direkt etiket | geri çekilme | "Peki bu Amerika'ya özgü mü? Avrupa'da aynı rüzgâr esti — ama daha ılımlı: artı yüzde 23." |
| 6 | 62–74 | **TR sahneye girer** | TR çizgisi girer; üç uç etiket: 1,62 / 1,23 / 1,20 | statik geniş | "Türkiye'de et ve yem, enflasyonla birlikte uçtu — ama birbirine karşı sadece yüzde 20 açıldı. Aynı fırtına, üç kıta, üç farklı hasar." |
| 7 | 74–86 | **Kapanış kartı** | Üç çizgi donuk kalır; başlık: "Aynı fırtına, üç kıta." Kaynak satırı: FRED/BLS · EC Agrifood · TÜİK-EVDS | statik | "Üç kıtanın verisi tek soruda buluşuyor: yem mi eti besliyor, et mi yemi taşıyor?" |
| 8 | 86–90 | **Logo/CTA** | "namikakman.dev — veriyle anlatılmış" + QR/link | statik | (müzik sönümü) |

## Kalite kuralları
- Tüm hareketler tek GSAP master-timeline üzerinde; easing: power2.inOut varsayılan, vurgularda back.out
- Çizgi çizimi: stroke-dashoffset ile, hız sabit değil — olay yıllarında yavaşlar (anlatımla eşzamanlı)
- Kamera: SVG viewBox interpolasyonu; asla ani kesme, min 1,2 sn geçiş
- Metin: ekranda aynı anda en fazla 1 başlık + 1 alt satır; kelime kelime fade-in yok, satır bazlı
- Sayaçlar: IBM Plex Mono, tabular-nums
- Render: deterministik saat, 60 fps kare-kare Playwright yakalama → ffmpeg H.264 CRF 18
- Ses: anlatım kaydı senkron noktaları storyboard'daki sn aralıklarına kilitli; müzik -18 LUFS altı

## Kararlar (25 Tem)
- [x] Film adı: **Parite: Sığır** ("Parite" seri markası — broiler'ın devamı)
- [x] Anlatım sesi: **Namık'ın kendi kaydı** (senaryo netleşince kayıt istenecek)
- [x] Format: **Dikey 9:16 öncelikli** (LinkedIn native), yatay sonra türetilecek
