/* ------------------------------------------------------------------- data
   The page is fixed; the record is data/vault.json in this artifact. Every
   edit publishes a new version of that one file, so whoever opens the page
   next — on any device — sees it. Nothing is stored in the browser. */
let VAULT = null, ART = null, READ_ONLY = false;

function emptyVault() { return { version: 2, transactions: [], budget: {}, cards: {}, budgets: {}, updated: null }; }

async function loadVault() {
  try {
    const res = await fetch('data/vault.json', { cache: 'no-store' });
    if (res.ok) return await res.json();
  } catch (err) { /* fall through */ }
  return emptyVault();
}

async function save() {
  VAULT.updated = new Date().toISOString();
  $('savedAt').textContent = 'kaydediliyor…';
  const art = ART || (ART = await (window.claude && window.claude.use ? window.claude.use('artifact') : null));
  if (!art) { markReadOnly('Bu görünümde kaydetme yok.'); return; }
  try {
    await art.publish({ 'data/vault.json': { content: JSON.stringify(VAULT), contentType: 'application/json' } });
    $('savedAt').textContent = 'kaydedildi ' + new Date().toLocaleTimeString('tr-TR');
  } catch (err) {
    const code = err && err.code;
    if (code === 'conflict') { $('savedAt').textContent = 'başka bir cihazdan güncellendi, yenileniyor…'; return; }
    if (code === 'not_writer' || code === 'not_granted' || code === 'capability_disabled' || code === 'not_declared') {
      markReadOnly(); return;
    }
    if (code === 'rate_limited') { $('savedAt').textContent = 'çok sık kayıt — biraz sonra tekrar deneyin'; return; }
    $('savedAt').textContent = 'kaydedilemedi (' + (code || 'hata') + ')';
  }
}
function markReadOnly(text) {
  READ_ONLY = true;
  $('ro').hidden = false;
  if (text) $('ro').textContent = text;
  $('savedAt').textContent = '';
}
function addTransactions(list) {
  const have = new Set(VAULT.transactions.map(t => t.id));
  let added = 0;
  for (const t of list) if (!have.has(t.id)) { have.add(t.id); VAULT.transactions.push(t); added++; }
  VAULT.transactions.sort((a, b) => a.date.localeCompare(b.date) || a.description.localeCompare(b.description));
  return { added, skipped: list.length - added };
}
/* @render */if (typeof pdfjsLib === 'undefined') {
  $('pdfNote').innerHTML = '<b>PDF okuyucu yüklenemedi.</b> Ekstreyi komut satırı aracıyla çözümleyip transactions.csv olarak ekleyin.';
  $('drop').style.opacity = .55;
} else {
  $('pdfNote').textContent = 'Dosya bu sayfada okunur; ekstrenin kendi dönem borcu ile karşılaştırılıp sonucu bildirilir.';
}
(async () => {
  VAULT = await loadVault();
  VAULT = migrateVault(Object.assign(emptyVault(), VAULT));
  renderAll();
})();
</script>
