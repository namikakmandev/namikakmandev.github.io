/* A small markdown renderer for the site's generated text: headings, paragraphs, bullets,
   bold, code, links. Everything is escaped first, so model output cannot inject markup.
   window.mdLite(text) -> HTML string. */
(function () {
  "use strict";
  function esc(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); }
  function inline(h) {
    h = h.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function (_, t, u) { return "<a href='" + u + "' target='_blank' rel='noopener'>" + t + "</a>"; });
    h = h.replace(/(^|[\s(])((https?:\/\/)[^\s<)]+)/g, function (_, pre, u) { return pre + "<a href='" + u + "' target='_blank' rel='noopener'>" + u + "</a>"; });
    h = h.replace(/\*\*([^*\n]+)\*\*/g, "<b>$1</b>").replace(/\*([^*\n]+)\*/g, "<em>$1</em>").replace(/`([^`\n]+)`/g, "<code>$1</code>");
    return h;
  }
  window.mdLite = function (text) {
    var lines = esc(text).split("\n"), out = "", inList = false, para = [];
    function flush() { if (para.length) { out += "<p>" + inline(para.join(" ")) + "</p>"; para = []; } }
    function closeList() { if (inList) { out += "</ul>"; inList = false; } }
    lines.forEach(function (ln) {
      var hd = /^\s*(#{1,4})\s+(.*)$/.exec(ln), li = /^\s*(?:[-*•]|\d+[.)])\s+(.*)$/.exec(ln);
      if (hd) { flush(); closeList(); var n = hd[1].length; out += "<h" + n + ">" + inline(hd[2]) + "</h" + n + ">"; return; }
      if (li) { flush(); if (!inList) { out += "<ul>"; inList = true; } out += "<li>" + inline(li[1]) + "</li>"; return; }
      if (!ln.trim()) { flush(); closeList(); return; }
      closeList(); para.push(ln.trim());
    });
    flush(); closeList();
    return out;
  };
})();
