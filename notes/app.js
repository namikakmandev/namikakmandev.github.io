"use strict";

/* ============================================================
   Notes app — offline-first, syncs through a private GitHub repo
   ============================================================ */

const LS_DATA   = "notes.data.v1";
const LS_CONFIG = "notes.config.v1";
const REMOTE_PATH = "notes-data.json";

const $ = (id) => document.getElementById(id);
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
const now = () => Date.now();

/* ---------- state ---------- */
let data = loadLocal();
let config = loadConfig();
let currentNbId = null;
let currentPgId = null;
let remoteSha = null;        // sha of notes-data.json on GitHub (for safe updates)
let saveTimer = null;
let syncTimer = null;

/* ---------- load / save local ---------- */
function loadLocal() {
  try {
    const raw = localStorage.getItem(LS_DATA);
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return { notebooks: [], updatedAt: now() };
}
function loadConfig() {
  try {
    const raw = localStorage.getItem(LS_CONFIG);
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return { repo: "", token: "", owner: "" };
}
function persistLocal() {
  data.updatedAt = now();
  localStorage.setItem(LS_DATA, JSON.stringify(data));
}
function persistConfig() {
  localStorage.setItem(LS_CONFIG, JSON.stringify(config));
}

/* ---------- helpers to find things ---------- */
const nb = (id) => data.notebooks.find((n) => n.id === id);
const pg = (n, id) => n && n.pages.find((p) => p.id === id);

/* ============================================================
   Rendering
   ============================================================ */
function renderNotebooks() {
  const ul = $("notebookList");
  ul.innerHTML = "";
  if (data.notebooks.length === 0) {
    ul.innerHTML = '<li style="cursor:default;color:var(--text-dim)">No notebooks yet</li>';
  }
  data.notebooks.forEach((n) => {
    const li = document.createElement("li");
    li.textContent = n.name || "Untitled notebook";
    if (n.id === currentNbId) li.classList.add("active");
    const del = document.createElement("span");
    del.className = "row-del";
    del.textContent = "✕";
    del.title = "Delete notebook";
    del.onclick = (e) => { e.stopPropagation(); deleteNotebook(n.id); };
    li.appendChild(del);
    li.onclick = () => selectNotebook(n.id);
    ul.appendChild(li);
  });
}

function renderPages() {
  const ul = $("pageList");
  ul.innerHTML = "";
  const n = nb(currentNbId);
  $("pagesLabel").textContent = n ? `Pages — ${n.name}` : "Pages";
  if (!n) return;
  const filter = $("search").value.trim().toLowerCase();
  let pages = n.pages.slice().sort((a, b) => b.updatedAt - a.updatedAt);
  if (filter) {
    pages = pages.filter(
      (p) =>
        (p.title || "").toLowerCase().includes(filter) ||
        stripHtml(p.html).toLowerCase().includes(filter)
    );
  }
  if (pages.length === 0) {
    ul.innerHTML = '<li style="cursor:default;color:var(--text-dim)">No pages</li>';
  }
  pages.forEach((p) => {
    const li = document.createElement("li");
    li.textContent = p.title || "Untitled page";
    if (p.id === currentPgId) li.classList.add("active");
    const del = document.createElement("span");
    del.className = "row-del";
    del.textContent = "✕";
    del.title = "Delete page";
    del.onclick = (e) => { e.stopPropagation(); deletePageById(p.id); };
    li.appendChild(del);
    li.onclick = () => selectPage(p.id);
    ul.appendChild(li);
  });
}

function renderEditor() {
  const n = nb(currentNbId);
  const p = pg(n, currentPgId);
  if (!p) {
    $("editor").style.display = "none";
    $("emptyState").style.display = "flex";
    $("pageTitle").value = "";
    $("pageTitle").disabled = true;
    return;
  }
  $("emptyState").style.display = "none";
  $("editor").style.display = "block";
  $("pageTitle").disabled = false;
  $("pageTitle").value = p.title || "";
  $("editor").innerHTML = p.html || "";
}

function renderAll() {
  renderNotebooks();
  renderPages();
  renderEditor();
}

/* ============================================================
   Selection
   ============================================================ */
function selectNotebook(id) {
  currentNbId = id;
  const n = nb(id);
  currentPgId = n && n.pages.length ? n.pages.slice().sort((a, b) => b.updatedAt - a.updatedAt)[0].id : null;
  renderAll();
}
function selectPage(id) {
  currentPgId = id;
  renderAll();
  closeSidebarMobile();
}

/* ============================================================
   CRUD
   ============================================================ */
function addNotebook() {
  const name = prompt("Notebook name:", "My Notebook");
  if (name === null) return;
  const n = { id: uid(), name: name.trim() || "Untitled notebook", createdAt: now(), updatedAt: now(), pages: [] };
  data.notebooks.push(n);
  persistLocal();
  selectNotebook(n.id);
  queueSync();
}
function deleteNotebook(id) {
  const n = nb(id);
  if (!n) return;
  if (!confirm(`Delete notebook "${n.name}" and all its pages?`)) return;
  data.notebooks = data.notebooks.filter((x) => x.id !== id);
  if (currentNbId === id) { currentNbId = null; currentPgId = null; }
  persistLocal();
  renderAll();
  queueSync();
}
function addPage() {
  if (!currentNbId) { alert("Create or pick a notebook first."); return; }
  const n = nb(currentNbId);
  const p = { id: uid(), title: "Untitled page", html: "", createdAt: now(), updatedAt: now() };
  n.pages.push(p);
  persistLocal();
  selectPage(p.id);
  $("pageTitle").focus();
  $("pageTitle").select();
  queueSync();
}
function deletePageById(id) {
  const n = nb(currentNbId);
  if (!n) return;
  const p = pg(n, id);
  if (!p) return;
  if (!confirm(`Delete page "${p.title}"?`)) return;
  n.pages = n.pages.filter((x) => x.id !== id);
  if (currentPgId === id) currentPgId = n.pages.length ? n.pages[0].id : null;
  persistLocal();
  renderAll();
  queueSync();
}

/* ---------- live edits ---------- */
function onEdit() {
  const n = nb(currentNbId);
  const p = pg(n, currentPgId);
  if (!p) return;
  p.title = $("pageTitle").value;
  p.html = $("editor").innerHTML;
  p.updatedAt = now();
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    persistLocal();
    renderNotebooks();
    renderPages();
    queueSync();
  }, 600);
}

/* ============================================================
   Rich-text toolbar
   ============================================================ */
function initToolbar() {
  $("toolbar").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    $("editor").focus();
    if (b.dataset.cmd) {
      document.execCommand(b.dataset.cmd, false, null);
    } else if (b.dataset.block) {
      document.execCommand("formatBlock", false, b.dataset.block);
    } else if (b.hasAttribute("data-hl")) {
      document.execCommand("hiliteColor", false, "#ff6500");
    } else if (b.hasAttribute("data-todo")) {
      insertTodo();
    }
    onEdit();
  });
}
function insertTodo() {
  const html =
    '<ul class="todo"><li><input type="checkbox">&nbsp;To-do item</li></ul><p><br></p>';
  document.execCommand("insertHTML", false, html);
}
/* checkbox state must stick when typed into HTML */
function fixCheckbox(e) {
  if (e.target && e.target.type === "checkbox") {
    if (e.target.checked) e.target.setAttribute("checked", "");
    else e.target.removeAttribute("checked");
    onEdit();
  }
}

/* ============================================================
   GitHub sync
   ============================================================ */
function b64encode(str) {
  return btoa(unescape(encodeURIComponent(str)));
}
function b64decode(b64) {
  return decodeURIComponent(escape(atob(b64)));
}
function ghHeaders() {
  return {
    Authorization: "Bearer " + config.token,
    Accept: "application/vnd.github+json",
  };
}
function ghUrl() {
  return `https://api.github.com/repos/${config.owner}/${config.repo}/contents/${REMOTE_PATH}`;
}
function isConfigured() {
  return config.token && config.repo && config.owner;
}

function setSync(text, cls) {
  const el = $("syncStatus");
  el.textContent = text;
  el.className = "sync-status" + (cls ? " " + cls : "");
}

/* merge remote + local by id, newest updatedAt wins (per notebook & page) */
function mergeData(remote, local) {
  const out = { notebooks: [], updatedAt: Math.max(remote.updatedAt || 0, local.updatedAt || 0) };
  const map = new Map();
  (remote.notebooks || []).forEach((n) => map.set(n.id, JSON.parse(JSON.stringify(n))));
  (local.notebooks || []).forEach((ln) => {
    const rn = map.get(ln.id);
    if (!rn) { map.set(ln.id, ln); return; }
    const winner = ln.updatedAt >= rn.updatedAt ? ln : rn;
    const merged = { ...winner, pages: [] };
    const pmap = new Map();
    rn.pages.forEach((p) => pmap.set(p.id, p));
    ln.pages.forEach((lp) => {
      const rp = pmap.get(lp.id);
      if (!rp || lp.updatedAt >= rp.updatedAt) pmap.set(lp.id, lp);
    });
    merged.pages = Array.from(pmap.values());
    map.set(ln.id, merged);
  });
  out.notebooks = Array.from(map.values());
  return out;
}

async function pullRemote() {
  const res = await fetch(ghUrl(), { headers: ghHeaders() });
  if (res.status === 404) return null;              // no file yet
  if (!res.ok) throw new Error("GitHub read failed (" + res.status + ")");
  const json = await res.json();
  remoteSha = json.sha;
  return JSON.parse(b64decode(json.content));
}

async function pushRemote(payload) {
  const body = {
    message: "Update notes " + new Date().toISOString(),
    content: b64encode(JSON.stringify(payload)),
  };
  if (remoteSha) body.sha = remoteSha;
  const res = await fetch(ghUrl(), {
    method: "PUT",
    headers: { ...ghHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error("GitHub save failed (" + res.status + "): " + t.slice(0, 120));
  }
  const json = await res.json();
  remoteSha = json.content.sha;
}

async function fullSync() {
  if (!isConfigured()) { setSync("Not synced", ""); return; }
  setSync("Syncing…", "busy");
  try {
    const remote = await pullRemote();
    if (remote) data = mergeData(remote, data);
    persistLocal();
    await pushRemote(data);
    renderAll();
    setSync("Synced ✓ " + new Date().toLocaleTimeString(), "ok");
  } catch (err) {
    console.error(err);
    setSync("Sync error", "err");
    alert("Sync problem:\n\n" + err.message);
  }
}

/* debounce auto-sync after edits */
function queueSync() {
  if (!isConfigured()) return;
  setSync("Pending changes…", "busy");
  clearTimeout(syncTimer);
  syncTimer = setTimeout(fullSync, 4000);
}

/* ============================================================
   Settings modal
   ============================================================ */
function openModal() {
  $("repoInput").value = config.repo || "my-notes-data";
  $("tokenInput").value = config.token || "";
  $("modalMsg").textContent = "";
  $("modalMsg").className = "modal-msg";
  $("modal").classList.remove("hidden");
}
function closeModal() { $("modal").classList.add("hidden"); }

async function saveSettings() {
  const repo = $("repoInput").value.trim();
  const token = $("tokenInput").value.trim();
  const msg = $("modalMsg");
  if (!repo || !token) {
    msg.textContent = "Please fill in both the repository name and the token.";
    msg.className = "modal-msg err";
    return;
  }
  msg.textContent = "Checking connection…";
  msg.className = "modal-msg";
  $("saveSettings").disabled = true;
  try {
    const who = await fetch("https://api.github.com/user", {
      headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json" },
    });
    if (!who.ok) throw new Error("That token was rejected by GitHub. Please re-check it.");
    const user = await who.json();
    config = { repo, token, owner: user.login };
    persistConfig();
    msg.textContent = "Connected as " + user.login + ". Syncing…";
    msg.className = "modal-msg ok";
    await fullSync();
    closeModal();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "modal-msg err";
  } finally {
    $("saveSettings").disabled = false;
  }
}
function disconnect() {
  if (!confirm("Disconnect sync? Notes stay on this device but stop syncing.")) return;
  config = { repo: "", token: "", owner: "" };
  persistConfig();
  remoteSha = null;
  setSync("Not synced", "");
  closeModal();
}

/* ============================================================
   Misc / mobile
   ============================================================ */
function stripHtml(html) {
  const d = document.createElement("div");
  d.innerHTML = html || "";
  return d.textContent || "";
}
function openSidebarMobile() { $("sidebar").classList.add("open"); }
function closeSidebarMobile() { $("sidebar").classList.remove("open"); }

/* ============================================================
   Wire up
   ============================================================ */
function init() {
  $("editor").setAttribute("data-ph", "Start writing…");

  $("addNotebook").onclick = addNotebook;
  $("addPage").onclick = addPage;
  $("deletePage").onclick = () => currentPgId && deletePageById(currentPgId);
  $("pageTitle").addEventListener("input", onEdit);
  $("editor").addEventListener("input", onEdit);
  $("editor").addEventListener("change", fixCheckbox);
  $("search").addEventListener("input", renderPages);

  $("settingsBtn").onclick = openModal;
  $("modalClose").onclick = closeModal;
  $("saveSettings").onclick = saveSettings;
  $("disconnectBtn").onclick = disconnect;
  $("syncBtn").onclick = fullSync;

  $("menuOpen").onclick = openSidebarMobile;
  $("menuClose").onclick = closeSidebarMobile;

  initToolbar();

  // pick first notebook/page if any
  if (data.notebooks.length) selectNotebook(data.notebooks[0].id);
  else renderAll();

  if (isConfigured()) fullSync();
  else setSync("Not synced", "");

  // sync when network returns / tab refocused
  window.addEventListener("online", () => isConfigured() && fullSync());
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && isConfigured()) fullSync();
  });
}

document.addEventListener("DOMContentLoaded", init);

/* service worker for offline + add-to-home-screen */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  });
}
