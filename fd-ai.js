// FiloDesk asistanı — bu filo/araç kiralama fiyatlama aracının nasıl
// çalıştığını ve ekrandaki sayıların ne anlama geldiğini sade Türkçe ile
// açıklar. Dealer-demo ile aynı paylaşımlı Anthropic proxy'sini kullanır.
// Her şey tarayıcıda hesaplanır; girdiğiniz senaryo dışında bir veri yoktur.

(function () {
  var AI_PROXY_URL = "https://assetix-ai.akmannamik83.workers.dev";
  var AI_SYSTEM =
    "Sen FiloDesk adlı filo / araç kiralama FİYATLAMA aracının yardımcı asistanısın. " +
    "Kullanıcı genellikle satış veya filo ekibinden biri (ör. Serdar) ve bu aracın NASIL çalıştığını, ekrandaki sayıların ne anlama geldiğini soruyor. " +
    "Görevin: aracın mantığını sade, anlaşılır Türkçe ile açıklamak. " +
    "Aylık kiranın nasıl kurulduğunu net anlat: AYLIK MALİYET = değer kaybı + gerçek kredi faizi + kredi masrafı + işletme gideri; üzerine kâr marjı eklenir (KDV hariç kira); sonra KDV uygulanır (KDV dahil kira). " +
    "Önemli ayrımı vurgula: ‘değer kaybı’ aracın geri DÖNMEYEN bedelidir, banka taksitindeki anapara ise vade sonunda araç satışıyla geri döner; bu yüzden aylık nakit çoğu zaman kârdan düşüktür ve kâr büyük ölçüde vade sonu araç satışında realize olur. " +
    "Soru ekrandaki güncel senaryoyla ilgiliyse sana verilen ‘GÜNCEL SENARYO’ verilerini kullanarak somut sayılarla yanıtla. Sana verilmeyen bir rakamı UYDURMA; emin değilsen ‘bu bilgi bende yok’ de. " +
    "Kullanıcının hangi SEKME'de olduğu sana söyleniyor — soru o sekmeyle ilgiliyse oraya odaklan. " +
    "Yanıtları kısa, açık ve net tut. Kullanıcı başka bir dilde sorarsa o dilde yanıtla; aksi halde Türkçe yanıt ver. " +
    "Bu illüstratif bir Faz-1 modelidir; resmi finansal, muhasebe veya vergi tavsiyesi değildir — gerektiğinde nazikçe hatırlat.";

  function askAI(prompt, system) {
    return fetch(AI_PROXY_URL, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: prompt, system: system })
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) return { error: (j.error || ("AI hatası (" + r.status + ")")) + (j.detail ? " — " + j.detail : "") };
        return { text: j.text || "" };
      });
    }).catch(function () { return { error: "Bağlantı hatası — AI servisine ulaşılamadı." }; });
  }

  var trN = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 });
  var trN1 = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 1 });
  function money(v) { return "₺" + trN.format(Math.round(v || 0)); }
  function pct(v) { return "%" + trN1.format(v); }      // v zaten yüzde (ör. 25)
  function pctF(v) { return "%" + trN1.format(v * 100); } // v kesir (ör. 0.25)

  function fdContext() {
    var d = window.__FD;
    if (!d || !d.s || !d.c) return "Henüz hesaplama yapılmadı.";
    var s = d.s, c = d.c;

    return "AÇIK ARAÇ: FiloDesk — Filo / Araç Kiralama Fiyatlama (Faz 1, illüstratif model, Türkçe ₺).\n" +
      "KULLANICI ŞU AN '" + (d.tab || "Teklif") + "' SEKMESİNDE — soru bununla ilgiliyse oraya odaklan.\n" +
      "(Esas: " + (d.basis === "accrual" ? "MUHASEBE / TAHAKKUK — değer kaybı ve faiz maliyet sayılır, kâr her ay birikir" : "NAKİT — banka taksiti tam çıkar, kâr çoğunlukla vade sonu araç satışında") + ".)\n\n" +
      "GÜNCEL SENARYO\n" +
      "- Araç: " + s.model + " · " + s.qty + " adet · " + s.term + " ay vade · yıllık " + trN.format(s.km) + " km\n" +
      "- Girdiler: alış fiyatı " + money(s.price) + ", peşinat " + pct(s.down) + ", vade sonu (ikinci el) değer " + pct(s.residual) + " (= " + money(c.R) + "), banka faizi " + pct(s.rate) + (d.live ? " — TCMB canlı" : "") + ", kredi masrafı " + pct(s.fee) + ", sigorta " + pct(s.ins) + " (= " + money(c.insYr) + "/yıl), bakım " + money(s.maint) + "/yıl, diğer (MTV vb.) " + money(s.other) + "/yıl, kâr marjı " + pct(s.margin) + ", KDV " + pct(s.vat) + "\n\n" +
      "AYLIK MALİYET KIRILIMI (araç başına)\n" +
      "- Değer kaybı (geri dönmeyen bedel): " + money(c.depMonth) + "  [= (fiyat − vade sonu değer) ÷ vade]\n" +
      "- Gerçek kredi faizi (ortalama): " + money(c.finMonth) + "  [= vade boyu toplam faiz ÷ vade]\n" +
      "- Kredi masrafı (tahsis/BSMV): " + money(c.feeMonth) + "  [tek seferlik " + money(c.feeOneTime) + ", aya bölünmüş]\n" +
      "- İşletme gideri (sigorta+bakım+MTV): " + money(c.opMonth) + "/ay\n" +
      "= AYLIK MALİYET: " + money(c.cost) + "\n" +
      "+ Kâr marjı (" + pct(s.margin) + " × maliyet): " + money(c.mrg) + "\n" +
      "= KDV HARİÇ KİRA: " + money(c.rentEx) + "  →  KDV DAHİL KİRA: " + money(c.rentInc) + " /ay" + (s.qty > 1 ? " (filo: " + money(c.rentInc * s.qty) + "/ay)" : "") + "\n\n" +
      "BANKA FİNANSMANI\n" +
      "- Kredi tutarı: " + money(c.loan) + (s.down > 0 ? " (" + pct(s.down) + " peşinat sonrası)" : " (tam finansman)") + "\n" +
      "- Aylık anüite taksiti: " + money(c.installment) + " · Vade boyu toplam faiz: " + money(c.totalInterest) + "\n" +
      "- Vade sonu araç (ikinci el) değeri: " + money(c.R) + " — sözleşme sonunda bu satışla anapara geri döner\n\n" +
      "NAKİT & GETİRİ\n" +
      "- Aylık net nakit (kira − taksit − işletme): " + money(c.cashMonth) + "  [taksitin içinde ANAPARA da olduğu için kârdan düşüktür]\n" +
      "- Ciro marjı (kâr ÷ kira): " + pctF(c.marginRev) + "\n" +
      "- Vade boyu toplam kâr: " + money(c.totalProfit) + (s.qty > 1 ? " (filo: " + money(c.totalProfit * s.qty) + ")" : "") + "\n" +
      "- Bağlanan işletme sermayesi (en dip kümülatif nakit): ~" + money(c.workingCap) + "\n" +
      "- NBD / NPV (fonlama faiziyle iskontolu): " + money(c.npv) + "\n" +
      "- Özkaynak (kaldıraçlı) IRR: " + (c.irrA != null ? pctF(c.irrA) : "—") + " · Proje (kaldıraçsız) IRR: " + (c.irrU != null ? pctF(c.irrU) : "—") + "\n\n" +
      "YÖNTEM & NOTLAR (nasıl hesaplandığı sorulursa)\n" +
      "- Vade sonu değer = fiyat × kalan değer%. Değer kaybı = (fiyat − vade sonu değer) ÷ vade; aracın gerçekten ‘tükettiği’, geri dönmeyen bedeldir.\n" +
      "- Banka kredisi = fiyat × (1 − peşinat%). Taksit standart anüite formülüyle bulunur. Aylık ‘gerçek faiz’ = toplam faiz ÷ vade (taksitteki anapara maliyet değildir, geri döner).\n" +
      "- İşletme gideri = sigorta (fiyat×sigorta%) + bakım + diğer; yıllık tutar 12'ye bölünür.\n" +
      "- Kâr = maliyet × marj%. KDV hariç kira = maliyet + kâr. KDV dahil = ×(1+KDV%).\n" +
      "- Aylık nakit ile aylık kâr neden farklı: kâr, değer kaybını maliyet sayar (anaparayı saymaz); nakit ise tüm banka taksitini (anapara dâhil) düşer. Fark, vade sonu araç satışıyla kapanır.\n" +
      "- Kaldıraçsız (proje) IRR: aracı tüm parayla (bankasız) alıp kiralarsanız varlığın kendi getirisi. Kaldıraçlı (özkaynak) IRR: banka kredisi kullanıldığındaki özkaynak getirisi.\n" +
      "- Eski yöntem (fiyat × faktör ÷ vade) sabit bir kuraldı; bu araç maliyeti şeffaf biçimde parçalara ayırıp bunun yerine geçer.\n" +
      "- Her şey tarayıcıda, girilen senaryo üzerinde hesaplanır; başka bir yere veri gönderilmez.";
  }

  var fab = document.getElementById("aiFab"),
      panel = document.getElementById("aiChat"),
      msgs = document.getElementById("aiChatMsgs"),
      input = document.getElementById("aiChatInput"),
      sendBtn = document.getElementById("aiChatSend"),
      closeBtn = document.getElementById("aiChatClose");
  if (!fab || !panel) return;

  var history = [], greeted = false, retryBtn = null;
  function bubble(role, text) {
    var me = role === "user", w = document.createElement("div");
    w.style.cssText = "max-width:86%;padding:9px 12px;border-radius:12px;white-space:pre-wrap;" +
      (me ? "align-self:flex-end;background:var(--orange);color:#fff;border-bottom-right-radius:4px"
          : "align-self:flex-start;background:var(--panel2);border:1px solid var(--line);color:var(--ink);border-bottom-left-radius:4px");
    w.textContent = text; msgs.appendChild(w); msgs.scrollTop = msgs.scrollHeight; return w;
  }
  function openPanel() {
    panel.style.display = "flex";
    if (!greeted) {
      greeted = true;
      bubble("ai", "Merhaba — ben FiloDesk asistanıyım. Bu aracın nasıl çalıştığını sorabilirsiniz. Örnek:\n• «Aylık kira nasıl hesaplanıyor?»\n• «Değer kaybı ne demek, neden maliyete giriyor?»\n• «Aylık nakit neden kârdan düşük çıkıyor?»\n• «Kaldıraçlı ve kaldıraçsız IRR farkı ne?»");
    }
    setTimeout(function () { input.focus(); }, 50);
  }
  function closePanel() { panel.style.display = "none"; }
  fab.addEventListener("click", function () { panel.style.display === "flex" ? closePanel() : openPanel(); });
  closeBtn.addEventListener("click", closePanel);

  // Son sorunun altındaki tek tıkla "Tekrar dene" — servis hata verdiğinde
  // veya yanıt isabetsizse aynı soruyu yeniden sorar.
  function addRetry() {
    if (retryBtn) { retryBtn.remove(); retryBtn = null; }
    var r = document.createElement("button");
    r.type = "button"; r.textContent = "↻ Tekrar dene";
    r.style.cssText = "align-self:flex-start;margin:-4px 0 0 2px;background:none;border:0;color:var(--orange);font-size:12px;cursor:pointer;padding:2px 4px";
    r.addEventListener("click", retry);
    msgs.appendChild(r); msgs.scrollTop = msgs.scrollHeight;
    retryBtn = r;
  }

  function callAI() {
    if (retryBtn) { retryBtn.remove(); retryBtn = null; }
    var typing = bubble("ai", "…"); sendBtn.disabled = true;
    var convo = history.slice(-6).join("\n");
    // Önce kullanıcının sorusu, sonra referans veri — büyük bağlam içinde
    // soru kaybolmasın diye konuşma başa konur.
    var prompt =
      "KONUŞMA (kullanıcının güncel sorusu son \"Kullanıcı:\" satırıdır — ASIL onu yanıtla):\n" +
      convo +
      "\n\nReferans olarak bu aracın güncel durumunu kullan:\n\n" +
      fdContext() +
      "\n\nŞimdi kullanıcının son sorusunu bu senaryo bağlamında yanıtla — kısa, açık, Türkçe.";
    askAI(prompt, AI_SYSTEM).then(function (res) {
      typing.textContent = res.error ? "⚠ " + res.error : res.text;
      if (!res.error) history.push("Asistan: " + res.text);
      sendBtn.disabled = false;
      addRetry();
      setTimeout(function () { input.focus(); }, 50);
    });
  }

  function send() {
    if (sendBtn.disabled) return;             // zaten bir istek yolda
    var q = (input.value || "").trim(); if (!q) return;
    input.value = ""; bubble("user", q); history.push("Kullanıcı: " + q);
    callAI();
  }

  function retry() {
    if (sendBtn.disabled) return;
    // Önceki yanıtı (varsa) at — bu, takip sorusu değil aynı sorunun
    // temiz bir yeniden denemesi olsun.
    if (history.length && history[history.length - 1].indexOf("Asistan: ") === 0) history.pop();
    callAI();
  }

  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); send(); } });
})();
