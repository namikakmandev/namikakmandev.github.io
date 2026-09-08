#!/usr/bin/env python3
"""Generate a statement PDF that mimics the real Garanti Bonus geometry.

Reproduces what makes the real file hard to read, so the parsers are tested
against the shape that actually matters:

  * Turkish long dates in a left column
  * two right-aligned money columns — Bonus (TL) at x=445 and Tutar (TL) at
    x=553 — so a bonus-only line must not be read as expenditure
  * a third column for the original amount and currency of a foreign charge
  * instalments written "1.760,00x3=5.280,00 1.Taksit"
  * a trailing "+" marking a credit
  * undated fee rows
  * invisible 2pt "bosluk" spacer glyphs glued to the right of an amount

No real statement is used or needed.
"""

from pathlib import Path

DATE_X, DESC_X, PLAN_X = 104.9, 170.1, 303.3
BONUS_RIGHT, FX_RIGHT, FX_CODE_X, AMOUNT_RIGHT = 445.0, 485.0, 486.9, 552.7

# date, description, plan, instalment, bonus, amount, credit, fx, currency
ROWS = [
    ("09 Aralık 2025", "BONUS KASIM KAMPANYASI", None, None, "1.050,00", None, False, None, None),
    ("16 Aralık 2025", "ÖDEMENİZ İÇİN TEŞEKKÜR EDERİZ", None, None, None, "149.340,29", True, None, None),
    ("10 Aralık 2025", "BRASSIRE PALLADIUM", None, None, "2,39", "795,00", False, None, None),
    ("05 Aralık 2025", "IYZICO/ZARA.COM", "1.760,00x3=5.280,00", "1.Taksit", "4,75", "1.760,00", True, None, None),
    ("12 Aralık 2025", "MOKAUNITED *ZARA GİYİM", "1.613,00x3=4.839,00", "1.Taksit", "2,42", "1.613,00", False, None, None),
    ("21 Ocak 2026", "BARBOUR", None, None, None, "23.022,30", False, "438,00", "EUR"),
    ("11 Aralık 2025", "TRENDYOL MARKET", None, None, "0,38", "1.901,07", False, None, None),
    ("08 Ocak 2026", "TURKISH AIRLINES", None, None, None, "2.050,00", False, None, None),
    ("08 Ocak 2026", "TURKISH AIRLINES", None, None, None, "2.050,00", False, None, None),
]
FEES = [("DÖNEM FAİZİ", "541,19"), ("KKDF + BSMV", "162,36")]
CARRIED = "149.340,29"


def _tr(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(text):
    return float(text.replace(".", "").replace(",", "."))


def period_total():
    """carried forward + charges - credits, computed so it cannot drift."""
    debits = sum(_num(r[5]) for r in ROWS if r[5] and not r[6])
    debits += sum(_num(v) for _, v in FEES)
    credits = sum(_num(r[5]) for r in ROWS if r[5] and r[6])
    return _num(CARRIED) + debits - credits


PERIOD_TOTAL = _tr(period_total())


FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
)


def _unicode_font():
    """The built-in Type-1 fonts silently drop ı, İ, ş, ğ — which is exactly
    what this fixture needs to render, so a real Unicode face is required."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            pdfmetrics.registerFont(TTFont("FixtureSans", candidate))
            return "FixtureSans"
    raise SystemExit("no Unicode TTF found; install fonts-dejavu to build the fixture")


def build(path: Path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    font = _unicode_font()
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setFont(font, 7)
    top = 780

    for label, value in (("Kart Numarası", "5549 60** **** 3053"),
                         ("Hesap Kesim Tarihi", "09 Ocak 2026"),
                         ("Son Ödeme Tarihi", "19 Ocak 2026"),
                         ("Dönem Borcunuz", PERIOD_TOTAL + " TL"),
                         ("Min. Ödeme Tutarı", "12.134,00 TL"),
                         ("Kart Limiti", "1.000.000,00 TL")):
        pdf.drawString(36, top, f"{label} {value}")
        top -= 12
    pdf.drawString(DATE_X, top, "İşlem Tarihi Dönem İçi İşlemler Kalan Borç / Taksit Bonus (TL) Tutar (TL)")
    top -= 14
    pdf.drawString(DESC_X, top, "ÖNCEKİ DÖNEMDEN DEVİR EDİLEN TUTAR")
    pdf.drawRightString(AMOUNT_RIGHT, top, CARRIED)
    top -= 12

    for date, desc, plan, index, bonus, amount, credit, fx, currency in ROWS:
        pdf.drawString(DATE_X, top, date)
        pdf.drawString(DESC_X, top, desc)
        if plan:
            pdf.drawString(PLAN_X, top, f"{plan} {index}")
        if bonus:
            pdf.drawRightString(BONUS_RIGHT, top, bonus + ("-" if credit else ""))
        if fx:
            # one run with a real space, as the statement does, so the amount and
            # the currency code come back as two words rather than one
            pdf.drawString(FX_RIGHT - pdf.stringWidth(fx, font, 7), top, f"{fx} {currency}")
        if amount:
            pdf.drawRightString(AMOUNT_RIGHT, top, amount + ("+" if credit else ""))
            if credit:                       # the invisible spacer the template paints
                pdf.setFont(font, 2)
                pdf.drawString(AMOUNT_RIGHT + 0.2, top - 2.5, "bosluk")
                pdf.setFont(font, 7)
        top -= 12

    for label, value in FEES:
        pdf.drawString(DESC_X, top, label)
        pdf.drawRightString(AMOUNT_RIGHT, top, value)
        top -= 12

    pdf.save()
    return path


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "statement-fixture.pdf")
    print("wrote", build(out))
