#!/usr/bin/env python3
"""Write the household tracker workbook.

    python3 export_tracker.py --budget 'inbox/budget.xlsx' --budget-year 2025 \
        --budget-line 'ebru kk' --out '/somewhere/Harcama Takip.xlsx'

Reads out/transactions.json (run `parse` first). Everything that can be a
formula is a formula, so re-categorising a row in İşlemler, changing a budget
figure, or pasting next month's rows updates every summary. The instalment
plan table is the one computed input — which appearance of a plan is the
latest is procedural, not arithmetic — and the sheet says so.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import expense_control as ec  # noqa: E402

FONT = "Arial"
MAX_ROWS = 5000                       # formula ranges reach this far, so pasting new months just works
BASE = Font(name=FONT, size=10)
BOLD = Font(name=FONT, size=10, bold=True)
INPUT = Font(name=FONT, size=10, color="0000FF")          # blue: cells meant to be edited
LINK = Font(name=FONT, size=10, color="008000")           # green: pulled from another sheet
TITLE = Font(name=FONT, size=14, bold=True)
MUTED = Font(name=FONT, size=9, italic=True, color="666666")
HEAD_FILL = PatternFill("solid", fgColor="E8E8E8")
INPUT_FILL = PatternFill("solid", fgColor="FFFFCC")
THIN = Side(style="thin", color="C8C8C8")
MONEY = '#,##0.00;[Red]-#,##0.00;-'
PCT = '0%'
TX = "İşlemler"


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = BOLD
        cell.fill = HEAD_FILL
        cell.border = Border(bottom=THIN)
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def month_key(iso):
    return iso[:7]


def shift(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    i = y * 12 + (m - 1) + k
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def build(transactions, budget_line, budget_label, categories, out):
    wb = Workbook()
    transactions = sorted(transactions, key=lambda t: (t["date"], t["description"]))
    months_seen = sorted({month_key(t["date"]) for t in transactions})
    months = sorted(set(months_seen) | set(budget_line))
    n = len(transactions)
    last_row = 1 + n

    # ------------------------------------------------------------ Kılavuz
    ws = wb.active
    ws.title = "Kılavuz"
    lines = [
        ("Harcama Takip", TITLE),
        ("Ebru'nun kartı · ekstrelerden okunan işlemler, bütçe karşılaştırması ve gelecek aylara yazılmış taksitler.", BASE),
        ("", BASE),
        ("Nasıl kullanılır", BOLD),
        ("• Mavi yazılı hücreler düzenlenebilir: İşlemler'de Kategori sütunu (açılır liste) ve Bütçe'de aylık bütçe.", BASE),
        ("• Diğer her şey formüldür; bir kategori değiştiğinde Özet, Bütçe ve İşyerleri kendiliğinden güncellenir.", BASE),
        ("• Yeni ay: ekstreyi araçla çözümleyip (transactions.csv) satırları İşlemler'in altına yapıştırın; Ay sütunu formülünü aşağı çekin.", BASE),
        ("• Taksitler sayfasındaki plan tablosu ekstrelerden hesaplanmıştır; yeni ekstre eklendiğinde aracı yeniden çalıştırıp bu tabloyu yenileyin.", BASE),
        ("", BASE),
        ("Sayfalar", BOLD),
        ("Özet — kategori × ay harcama tablosu, pay yüzdeleri.", BASE),
        (f"Bütçe — aylık kart toplamı ile '{budget_label}' bütçe satırının karşılaştırması.", BASE),
        ("Taksitler — açık taksit planları ve gelecek aylara şimdiden yazılmış tutarlar.", BASE),
        ("İşyerleri — en çok harcanan işyerleri.", BASE),
        ("İşlemler — tüm işlemler; iade ve ödemeler eksi tutarlıdır.", BASE),
        ("Kategoriler — açılır listenin kaynağı; yeni kategori buraya eklenir.", BASE),
        ("", BASE),
        ("Kaynak: Garanti BBVA Bonus ekstreleri, her biri bankanın kendi 'Dönem Borcunuz' tutarıyla kuruşuna kadar doğrulanmıştır. "
         f"Bütçe satırı: '{budget_label}', 2026-2027 budget personally.xlsx (ilk 'eylül' = Eylül 2025).", MUTED),
    ]
    for i, (text, font) in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=text)
        c.font = font
    ws.column_dimensions["A"].width = 120

    # --------------------------------------------------------- Kategoriler
    wc = wb.create_sheet("Kategoriler")
    wc["A1"], wc["B1"] = "Kategori", "Not"
    style_header(wc, 1, 2)
    for i, cat in enumerate(categories, 2):
        wc.cell(row=i, column=1, value=cat).font = INPUT
    wc.cell(row=len(categories) + 3, column=1,
            value="Yeni kategori eklemek için bu listeye yazın; İşlemler'deki açılır liste buradan beslenir.").font = MUTED
    widths(wc, {"A": 24, "B": 60})
    cat_ref = f"'Kategoriler'!$A$2:$A${len(categories) + 1}"

    # ------------------------------------------------------------ İşlemler
    wt = wb.create_sheet(TX)
    heads = ["Tarih", "Ay", "Açıklama", "İşyeri", "Kategori", "Tutar (TL)", "Orijinal tutar",
             "Orijinal birim", "Taksit no", "Taksit toplam", "Kart", "Ekstre"]
    for c, h in enumerate(heads, 1):
        wt.cell(row=1, column=c, value=h)
    style_header(wt, 1, len(heads))
    for r, t in enumerate(transactions, 2):
        y, m, d = (int(x) for x in t["date"].split("-"))
        wt.cell(row=r, column=1, value=date(y, m, d)).number_format = "yyyy-mm-dd"
        wt.cell(row=r, column=2, value=f'=IF(A{r}="","",YEAR(A{r})&"-"&TEXT(MONTH(A{r}),"00"))')
        wt.cell(row=r, column=3, value=t["description"])
        wt.cell(row=r, column=4, value=t.get("merchant") or t["description"])
        k = wt.cell(row=r, column=5, value=t["category"])
        k.font = INPUT
        wt.cell(row=r, column=6, value=t["amount"]).number_format = MONEY
        if t.get("original_amount"):
            wt.cell(row=r, column=7, value=t["original_amount"]).number_format = MONEY
            wt.cell(row=r, column=8, value=t.get("original_currency"))
        if t.get("installment_no"):
            wt.cell(row=r, column=9, value=t["installment_no"])
            wt.cell(row=r, column=10, value=t["installment_total"])
        wt.cell(row=r, column=11, value=t.get("card", ""))
        wt.cell(row=r, column=12, value=t.get("statement", ""))
        for c in range(1, len(heads) + 1):
            cell = wt.cell(row=r, column=c)
            if cell.font == Font():
                cell.font = BASE
    dv = DataValidation(type="list", formula1=cat_ref, allow_blank=True,
                        errorTitle="Kategori", error="Kategoriler sayfasındaki listeden seçin.")
    wt.add_data_validation(dv)
    dv.add(f"E2:E{MAX_ROWS}")
    wt.freeze_panes = "A2"
    wt.auto_filter.ref = f"A1:L{last_row}"
    widths(wt, {"A": 11, "B": 9, "C": 34, "D": 28, "E": 18, "F": 14, "G": 13, "H": 8,
                "I": 8, "J": 10, "K": 20, "L": 30})

    R = lambda col: f"'{TX}'!${col}$2:${col}${MAX_ROWS}"     # a whole-column range on İşlemler

    # ---------------------------------------------------------------- Özet
    wo = wb.create_sheet("Özet", 1)
    wo["A1"] = "Harcama özeti — kategori × ay (TL)"
    wo["A1"].font = TITLE
    wo["A2"] = "İade ve kart ödemeleri harcamaya dahil değildir; en altta ayrı gösterilir."
    wo["A2"].font = MUTED
    hr = 4
    wo.cell(row=hr, column=1, value="Kategori")
    for j, mth in enumerate(months_seen, 2):
        wo.cell(row=hr, column=j, value=mth)
    tot_col = len(months_seen) + 2
    wo.cell(row=hr, column=tot_col, value="Toplam")
    wo.cell(row=hr, column=tot_col + 1, value="Pay")
    style_header(wo, hr, tot_col + 1)
    first = hr + 1
    for i, cat in enumerate(categories):
        r = first + i
        wo.cell(row=r, column=1, value=f"='Kategoriler'!A{i + 2}").font = LINK
        for j, mth in enumerate(months_seen, 2):
            col = get_column_letter(j)
            wo.cell(row=r, column=j, value=(
                f'=SUMIFS({R("F")},{R("E")},$A{r},{R("B")},{col}${hr},{R("F")},">0")')).number_format = MONEY
        tl = get_column_letter(tot_col)
        wo.cell(row=r, column=tot_col, value=f"=SUM(B{r}:{get_column_letter(tot_col - 1)}{r})").number_format = MONEY
        wo.cell(row=r, column=tot_col + 1,
                value=f'=IF(${tl}${first + len(categories)}=0,0,{tl}{r}/${tl}${first + len(categories)})').number_format = PCT
    tr = first + len(categories)
    wo.cell(row=tr, column=1, value="Toplam harcama").font = BOLD
    for j in range(2, tot_col + 1):
        col = get_column_letter(j)
        c = wo.cell(row=tr, column=j, value=f"=SUM({col}{first}:{col}{tr - 1})")
        c.number_format = MONEY
        c.font = BOLD
    cr = tr + 1
    wo.cell(row=cr, column=1, value="İade / ödeme").font = MUTED
    for j, mth in enumerate(months_seen, 2):
        col = get_column_letter(j)
        c = wo.cell(row=cr, column=j, value=f'=SUMIFS({R("F")},{R("B")},{col}${hr},{R("F")},"<0")')
        c.number_format = MONEY
        c.font = MUTED
    wo.cell(row=cr, column=tot_col, value=f"=SUM(B{cr}:{get_column_letter(tot_col - 1)}{cr})").number_format = MONEY
    wo.freeze_panes = "B5"
    widths(wo, {"A": 22, **{get_column_letter(j): 13 for j in range(2, tot_col + 2)}})

    # --------------------------------------------------------------- Bütçe
    wbd = wb.create_sheet("Bütçe", 2)
    wbd["A1"] = f"Aylık kart harcaması ile bütçe satırı '{budget_label}'"
    wbd["A1"].font = TITLE
    wbd["A2"] = "Bütçe sütunu (mavi) düzenlenebilir. Gerçekleşen İşlemler'den formülle gelir."
    wbd["A2"].font = MUTED
    bh = 4
    for c, h in enumerate(["Ay", "Bütçe (TL)", "Gerçekleşen (TL)", "Fark (TL)", "Kullanım", "Durum"], 1):
        wbd.cell(row=bh, column=c, value=h)
    style_header(wbd, bh, 6)
    for i, mth in enumerate(months, bh + 1):
        wbd.cell(row=i, column=1, value=mth)
        b = wbd.cell(row=i, column=2, value=budget_line.get(mth))
        b.font, b.fill, b.number_format = INPUT, INPUT_FILL, MONEY
        wbd.cell(row=i, column=3, value=f'=SUMIFS({R("F")},{R("B")},A{i},{R("F")},">0")').number_format = MONEY
        wbd.cell(row=i, column=4, value=f'=IF(B{i}="","",C{i}-B{i})').number_format = MONEY
        wbd.cell(row=i, column=5, value=f'=IF(OR(B{i}="",B{i}=0),"",C{i}/B{i})').number_format = PCT
        wbd.cell(row=i, column=6, value=f'=IF(OR(B{i}="",B{i}=0),"",IF(C{i}>B{i},"AŞILDI",IF(C{i}>0.85*B{i},"DİKKAT","OK")))')
    be = bh + len(months)
    tr_b = be + 1
    wbd.cell(row=tr_b, column=1, value="Toplam").font = BOLD
    for col in "BCD":
        c = wbd.cell(row=tr_b, column=" ABCD".index(col), value=f"=SUM({col}{bh + 1}:{col}{be})")
        c.number_format, c.font = MONEY, BOLD
    wbd.cell(row=tr_b, column=5, value=f'=IF(B{tr_b}=0,"",C{tr_b}/B{tr_b})').number_format = PCT
    wbd.conditional_formatting.add(f"F{bh + 1}:F{be}", CellIsRule(operator="equal", formula=['"AŞILDI"'],
                                   fill=PatternFill("solid", fgColor="F8CBAD"), font=Font(name=FONT, size=10, bold=True, color="9C0006")))
    wbd.conditional_formatting.add(f"F{bh + 1}:F{be}", CellIsRule(operator="equal", formula=['"DİKKAT"'],
                                   fill=PatternFill("solid", fgColor="FFEB9C"), font=Font(name=FONT, size=10, color="7F6000")))
    wbd.cell(row=tr_b + 2, column=1,
             value="Son ekstre ayı kısmi olabilir (kesim tarihine kadar); düşük kullanım gerçek bir tasarruf olmayabilir.").font = MUTED
    widths(wbd, {"A": 10, "B": 14, "C": 16, "D": 14, "E": 10, "F": 10})

    # ------------------------------------------------------------ Taksitler
    plans = [p for p in ec.instalment_plans(transactions) if p["installment_total"] > p["installment_no"]]
    plans.sort(key=lambda p: -(p["amount"] * (p["installment_total"] - p["installment_no"])))
    wk = wb.create_sheet("Taksitler", 3)
    wk["A1"] = "Açık taksit planları ve gelecek aylara şimdiden yazılmış tutarlar"
    wk["A1"].font = TITLE
    wk["A2"] = ("Plan tablosu ekstrelerden hesaplanmıştır: her plan, ekstrelerde en son göründüğü taksit numarasıyla bir kez sayılır. "
                "Yeni ekstre eklendiğinde aracı yeniden çalıştırın. Kalan sütunları ve takvim formüldür.")
    wk["A2"].font = MUTED
    ph = 4
    for c, h in enumerate(["İşyeri", "Açıklama", "Aylık tutar (TL)", "Ödenen", "Toplam", "Son fatura",
                           "Kalan adet", "Kalan tutar (TL)"], 1):
        wk.cell(row=ph, column=c, value=h)
    style_header(wk, ph, 8)
    for i, p in enumerate(plans, ph + 1):
        y, m, d = (int(x) for x in p["date"].split("-"))
        wk.cell(row=i, column=1, value=p.get("merchant") or p["description"])
        wk.cell(row=i, column=2, value=p["description"])
        wk.cell(row=i, column=3, value=p["amount"]).number_format = MONEY
        wk.cell(row=i, column=4, value=p["installment_no"])
        wk.cell(row=i, column=5, value=p["installment_total"])
        wk.cell(row=i, column=6, value=date(y, m, 1)).number_format = "yyyy-mm"
        wk.cell(row=i, column=7, value=f"=E{i}-D{i}")
        wk.cell(row=i, column=8, value=f"=C{i}*G{i}").number_format = MONEY
    pe = ph + len(plans)
    wk.cell(row=pe + 1, column=7, value="Toplam").font = BOLD
    c = wk.cell(row=pe + 1, column=8, value=f"=SUMIF(C{ph + 1}:C{pe},\">0\",H{ph + 1}:H{pe})")
    c.number_format, c.font = MONEY, BOLD
    wk.cell(row=pe + 1, column=8).comment = Comment("Yalnızca borç planları; iade planları (eksi tutar) takvimde ayrı gösterilir.", "tracker")

    sh = pe + 4
    wk.cell(row=sh - 1, column=1, value="Aylara göre taahhüt").font = BOLD
    for c, h in enumerate(["Ay", "Taahhüt (TL)", "Gelecek iade (TL)", "Bütçe (TL)", "Bütçenin"], 1):
        wk.cell(row=sh, column=c, value=h)
    style_header(wk, sh, 5)
    amt, paid, tot, last = (f"$C${ph + 1}:$C${pe}", f"$D${ph + 1}:$D${pe}",
                            f"$E${ph + 1}:$E${pe}", f"$F${ph + 1}:$F${pe}")
    first_future = shift(months_seen[-1], 0)
    future = [shift(first_future, k) for k in range(0, 12)]
    for i, mth in enumerate(future, sh + 1):
        y, m = int(mth[:4]), int(mth[5:7])
        wk.cell(row=i, column=1, value=date(y, m, 1)).number_format = "yyyy-mm"
        k = f"((YEAR($A{i})*12+MONTH($A{i}))-(YEAR({last})*12+MONTH({last})))"
        wk.cell(row=i, column=2, value=f"=SUMPRODUCT(({amt}>0)*({k}>=1)*({k}<={tot}-{paid})*{amt})").number_format = MONEY
        wk.cell(row=i, column=3, value=f"=SUMPRODUCT(({amt}<0)*({k}>=1)*({k}<={tot}-{paid})*{amt})").number_format = MONEY
        key = f'YEAR(A{i})&"-"&TEXT(MONTH(A{i}),"00")'
        wk.cell(row=i, column=4, value=f"=IFERROR(INDEX('Bütçe'!$B${bh + 1}:$B${be},MATCH({key},'Bütçe'!$A${bh + 1}:$A${be},0)),\"\")").number_format = MONEY
        wk.cell(row=i, column=4).font = LINK
        wk.cell(row=i, column=5, value=f'=IF(OR(D{i}="",D{i}=0),"",B{i}/D{i})').number_format = PCT
    widths(wk, {"A": 26, "B": 34, "C": 16, "D": 9, "E": 9, "F": 11, "G": 11, "H": 16})

    # ------------------------------------------------------------ İşyerleri
    totals = {}
    for t in transactions:
        if t["amount"] > 0:
            key = t.get("merchant") or t["description"]
            totals[key] = totals.get(key, 0) + t["amount"]
    top = sorted(totals, key=lambda k: -totals[k])[:40]
    wm = wb.create_sheet("İşyerleri", 4)
    wm["A1"] = "En çok harcanan işyerleri"
    wm["A1"].font = TITLE
    wm["A2"] = "İlk 40 işyeri; tutar ve adet İşlemler'den formülle gelir, kategori en sık görülen atamadır."
    wm["A2"].font = MUTED
    mh = 4
    for c, h in enumerate(["İşyeri", "Tutar (TL)", "Adet", "Pay"], 1):
        wm.cell(row=mh, column=c, value=h)
    style_header(wm, mh, 4)
    grand = f"'Özet'!${get_column_letter(tot_col)}${tr}"
    for i, name in enumerate(top, mh + 1):
        wm.cell(row=i, column=1, value=name)
        wm.cell(row=i, column=2, value=f'=SUMIFS({R("F")},{R("D")},A{i},{R("F")},">0")').number_format = MONEY
        wm.cell(row=i, column=3, value=f'=COUNTIFS({R("D")},A{i},{R("F")},">0")')
        wm.cell(row=i, column=4, value=f'=IF({grand}=0,0,B{i}/{grand})').number_format = PCT
    widths(wm, {"A": 30, "B": 16, "C": 8, "D": 8})

    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None and cell.font.name != FONT:
                    cell.font = Font(name=FONT, size=cell.font.size or 10, bold=cell.font.bold,
                                     italic=cell.font.italic, color=cell.font.color)
    wb.save(out)
    return {"transactions": n, "months": months_seen, "plans": len(plans), "merchants": len(top)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--transactions", default=str(HERE / "out" / "transactions.json"))
    ap.add_argument("--categories", default=str(HERE / "rules" / "categories.json"))
    ap.add_argument("--budget")
    ap.add_argument("--budget-sheet")
    ap.add_argument("--budget-year")
    ap.add_argument("--budget-line", default="")
    ap.add_argument("--out", default=str(HERE / "out" / "Harcama Takip.xlsx"))
    a = ap.parse_args()

    transactions = json.loads(Path(a.transactions).read_text(encoding="utf-8"))
    rules = json.loads(Path(a.categories).read_text(encoding="utf-8"))
    categories = [r["category"] for r in rules["rules"]] + [rules.get("fallback", "Diger")]
    categories = sorted(set(categories) | {t["category"] for t in transactions}, key=ec.fold)

    budget_line, label = {}, a.budget_line or "bütçe"
    if a.budget and a.budget_line:
        budget = ec.read_budget(Path(a.budget), a.budget_sheet, a.budget_year)
        label = next((k for k in budget["monthly"] if ec.fold(k) == ec.fold(a.budget_line)), None)
        if label is None:
            sys.exit(f"no budget row '{a.budget_line}'; rows: {sorted(budget['monthly'])}")
        budget_line = {m: abs(v) for m, v in budget["monthly"][label].items()}

    info = build(transactions, budget_line, label, categories, a.out)
    print(f"  {a.out}: {info['transactions']} transactions, {len(info['months'])} months, "
          f"{info['plans']} open plans, {info['merchants']} merchants")


if __name__ == "__main__":
    main()
