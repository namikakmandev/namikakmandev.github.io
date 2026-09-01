#!/usr/bin/env python3
"""Wrap the self-contained report in real encryption, for sharing by file.

This is NOT the usual "password box on a web page", which hides content that is
still sitting in the source and is worth nothing. The report is encrypted with
AES-256-GCM under a key derived from the passphrase with PBKDF2-SHA256. What
ships is ciphertext: without the passphrase the file contains no readable
prices, no venue list, and no way to recover them short of guessing the
passphrase. Decryption happens in the reader's own browser via Web Crypto, so
there is no server, no upload, and it works offline.

The security is therefore exactly the strength of the passphrase and of how it
is passed to the reader. A short or guessable one, or one mailed alongside the
file, gives an attacker everything.

Usage:
    python scripts/build_locked_report.py [--password ...] [--in F] [--out F]

With no --password, one is read from PHARMA_REPORT_PASSWORD, or generated and
printed once. The passphrase is never written into the output.

Output: pharma-report-locked.html
"""
import argparse
import base64
import hashlib
import json
import os
import pathlib
import secrets
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ITERATIONS = 600_000          # OWASP's PBKDF2-SHA256 floor at time of writing
WORDS = ("harbour tangent oxide meridian cobalt lantern prairie quartz vellum "
         "thicket saffron kestrel bramble marlin cinder juniper fathom nimbus "
         "gossamer tundra").split()


def phrase():
    """Five words from a 20-word list is only ~21 bits - not enough on its own,
    so a random block is appended. Readable enough to dictate over a phone."""
    picked = "-".join(secrets.choice(WORDS) for _ in range(4))
    return f"{picked}-{secrets.token_hex(4)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--password")
    ap.add_argument("--in", dest="src", default="pharma-report.html")
    ap.add_argument("--out", dest="out", default="pharma-report-locked.html")
    a = ap.parse_args()

    src = ROOT / a.src
    if not src.exists():
        sys.exit(f"{a.src} is missing - run scripts/build_pharma_report.py first")

    pw = a.password or os.environ.get("PHARMA_REPORT_PASSWORD")
    shown = None
    if not pw:
        pw = shown = phrase()

    payload = src.read_bytes()
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    key = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, ITERATIONS, 32)

    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        sys.exit("needs `pip install cryptography` to encrypt")
    blob = AESGCM(key).encrypt(iv, payload, None)

    b64 = base64.b64encode
    doc = LOCK_HTML.replace("__SALT__", b64(salt).decode()) \
                   .replace("__IV__", b64(iv).decode()) \
                   .replace("__ITER__", str(ITERATIONS)) \
                   .replace("__DATA__", b64(blob).decode())
    out = ROOT / a.out
    out.write_text(doc, encoding="utf-8")

    print(f"wrote {out.name}: {out.stat().st_size/1024:.0f} KB "
          f"({len(payload)/1024:.0f} KB encrypted)")
    if shown:
        print("\n  passphrase:  " + shown)
        print("  It is NOT stored anywhere. Put it in a password manager now;\n"
              "  if it is lost the file cannot be opened, by me or by anyone.\n"
              "  Send it to colleagues by a different channel than the file.")


LOCK_HTML = r"""<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Animal Pharma Price Tracker — locked</title>
<style>
  :root{color-scheme:dark}
  body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0B1220;color:#E8EEF7;
       font:15px/1.55 "Segoe UI",system-ui,-apple-system,sans-serif;padding:24px}
  .box{width:100%;max-width:420px;background:#121B2C;border:1px solid #1E2A40;border-radius:14px;
       padding:26px 24px}
  h1{font-size:19px;margin:0 0 6px;letter-spacing:-.01em}
  p{color:#9FB0C8;font-size:13.5px;margin:0 0 16px}
  input{width:100%;box-sizing:border-box;background:#0F1726;border:1px solid #1E2A40;border-radius:9px;
        color:#E8EEF7;font-size:15px;padding:11px 13px;font-family:inherit}
  input:focus{outline:none;border-color:#3987E5}
  button{width:100%;margin-top:10px;background:#3987E5;border:0;border-radius:9px;color:#fff;
         font-size:14px;font-weight:600;padding:11px;cursor:pointer;font-family:inherit}
  button[disabled]{opacity:.6;cursor:default}
  .msg{margin-top:12px;font-size:13px;min-height:19px;color:#E66767}
  .note{margin-top:16px;color:#64748B;font-size:11.5px;line-height:1.5}
</style>
<div class="box">
  <h1>Animal Pharma Price Tracker</h1>
  <p>This report is encrypted. Enter the passphrase to open it.</p>
  <form id="f">
    <input id="pw" type="password" autocomplete="current-password" placeholder="Passphrase" autofocus>
    <button id="go" type="submit">Open report</button>
  </form>
  <div class="msg" id="msg"></div>
  <div class="note">The contents are AES-256-GCM ciphertext inside this file. Nothing is uploaded and
    nothing is checked against a server &mdash; the passphrase is turned into a key in your browser and
    used to decrypt the page locally, so this works offline. There is no recovery: without the
    passphrase the file cannot be opened.</div>
</div>
<script>
const B = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const SALT = B("__SALT__"), IV = B("__IV__"), DATA = B("__DATA__"), ITER = __ITER__;
const msg = document.getElementById('msg'), go = document.getElementById('go');

document.getElementById('f').addEventListener('submit', async e => {
  e.preventDefault();
  const pw = document.getElementById('pw').value;
  if(!pw) return;
  // 600k PBKDF2 rounds take a moment on purpose - that cost is what makes
  // guessing expensive - so the button has to say something meanwhile.
  go.disabled = true; go.textContent = 'Decrypting…'; msg.textContent = '';
  try {
    if(!crypto.subtle) throw new Error('insecure-context');
    const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(pw),
                                               'PBKDF2', false, ['deriveKey']);
    const key = await crypto.subtle.deriveKey(
      {name:'PBKDF2', salt:SALT, iterations:ITER, hash:'SHA-256'},
      base, {name:'AES-GCM', length:256}, false, ['decrypt']);
    // GCM authenticates as it decrypts, so a wrong passphrase throws here
    // rather than yielding plausible-looking rubbish.
    const plain = await crypto.subtle.decrypt({name:'AES-GCM', iv:IV}, key, DATA);
    const html = new TextDecoder().decode(plain);
    document.open(); document.write(html); document.close();
  } catch (err) {
    go.disabled = false; go.textContent = 'Open report';
    msg.textContent = err && err.message === 'insecure-context'
      ? 'This browser will not decrypt over plain http. Open the file directly, or use https.'
      : 'That passphrase does not open this file.';
    document.getElementById('pw').select();
  }
});
</script>
"""

if __name__ == "__main__":
    main()
