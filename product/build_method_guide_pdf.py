"""
Build the Method Guide PDF from ONE-PAGER-METHOD-GUIDE.txt
Print-ready, light background, Slate Studio brand-colour accents.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT

# Brand colours
BLUE   = colors.HexColor("#2F9BFF")
GREEN  = colors.HexColor("#19C37D")
ORANGE = colors.HexColor("#FF6500")
INK    = colors.HexColor("#0F172A")
MUTED  = colors.HexColor("#475569")

OUTPUT = r"C:\Users\Lenovo\OneDrive\Creative\portfolio-website\product\One-Page-Business-Review-Method-Guide.pdf"

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "Title", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=22, leading=26,
    textColor=INK, spaceAfter=4, alignment=TA_LEFT,
)
subtitle_style = ParagraphStyle(
    "Subtitle", parent=styles["Normal"],
    fontName="Helvetica", fontSize=11, leading=15,
    textColor=MUTED, spaceAfter=18,
)
h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=12, leading=15,
    textColor=BLUE, spaceBefore=14, spaceAfter=6,
)
body = ParagraphStyle(
    "Body", parent=styles["BodyText"],
    fontName="Helvetica", fontSize=10.5, leading=15,
    textColor=INK, spaceAfter=6,
)
bullet = ParagraphStyle(
    "Bullet", parent=body,
    leftIndent=14, bulletIndent=2, spaceAfter=2,
)
small = ParagraphStyle(
    "Small", parent=body,
    fontSize=9, textColor=MUTED, leading=12, spaceAfter=2,
)

def P(text, style=body):
    return Paragraph(text, style)

def H(text):
    return Paragraph(text, h2)

def B(text):
    return Paragraph("&bull;&nbsp;&nbsp;" + text, bullet)

story = []

story += [
    P("The One-Page Business Review", title_style),
    P("Method Guide &nbsp;|&nbsp; Slate Studio", subtitle_style),
    P("The template is the easy part. <b>This</b> is the part that makes a board read it and act. "
      "Five minutes &mdash; read it once.", body),
]

story += [H("WHAT'S INCLUDED")]
story += [
    B("<b>one-pager.html</b> &mdash; the builder (open in any browser)"),
    B("<b>One-Page-Business-Review-Method-Guide.pdf</b> &mdash; this guide"),
    B("<b>README.txt</b> &mdash; quick-start"),
]

story += [H("HOW TO USE THE BUILDER")]
story += [
    B("Open <b>one-pager.html</b> in any browser."),
    B("Fill the form on the left &mdash; header, 6 KPIs, the story, 3 decisions, outlook. "
      "The page on the right updates as you type."),
    B("Set your brand colour (top of the form)."),
    B("Click &ldquo;Print / Save as PDF&rdquo; &rarr; choose &ldquo;Save as PDF&rdquo;. "
      "You get one clean page. Send that."),
]

story += [H("THE 6 KPIs &mdash; PICK RUTHLESSLY")]
story += [
    P("Six, no more. A board does not read twelve numbers. Use the ones that answer "
      "<i>&ldquo;are we winning, and is anything on fire&rdquo;</i>:", body),
    B("one <b>growth</b> number (revenue / bookings)"),
    B("one <b>vs-plan</b> number (variance)"),
    B("one <b>profitability</b> number (margin or EBITDA)"),
    B("one <b>cash</b> number (cash / runway)"),
    B("<b>two that matter THIS month</b> (whatever the story is about)"),
    P(f'Set the tone: <font color="{GREEN.hexval()}"><b>good</b></font> (green), '
      f'<font color="{ORANGE.hexval()}"><b>bad</b></font> (orange), '
      f'<font color="{MUTED.hexval()}"><b>neutral</b></font> (grey). '
      "Honesty in the colours builds trust faster than good numbers do.", body),
]

story += [H("THE STORY &mdash; 3 SENTENCES, A FORMULA")]
story += [
    P("Most managers describe; leaders explain. Each line follows:", body),
    P(f'&nbsp;&nbsp;<b>WHAT</b> happened &rarr; <b>WHY</b> &rarr; '
      f'<b><font color="{ORANGE.hexval()}">SO WHAT</font></b> '
      "(is it timing, structural, fixable?)", body),
    P("<i>Example:</i>", body),
    P("&nbsp;&nbsp;&ldquo;Revenue grew 6% but landed 3% under plan as two deals slipped to Q2 "
      "&mdash; timing, not lost demand.&rdquo;", body),
    P("<b>Rules:</b>", body),
    B("Name the cause, not just the movement."),
    B("Say whether it is one-off or structural. Boards fear surprises, not bad numbers."),
    B("If something is bad, say it in line 1. Hiding it costs you more."),
]

story += [H("THE 3 DECISIONS &mdash; THIS IS THE WHOLE POINT")]
story += [
    P("A report nobody acts on is wallpaper. Every review must end in at most <b>three decisions</b>, "
      "each with an <b>owner</b> and a <b>date</b>. Test each one:", body),
    B("Is it a decision, or just an &ldquo;FYI&rdquo;? (Cut FYIs.)"),
    B("Does it have a single owner? (No owner = it won't happen.)"),
    B("Does it have a date? (No date = it won't happen.)"),
    P("If you cannot name 3 decisions, the month had no decisions &mdash; say so, and the review "
      "still took 30 seconds to read. <b>That is success.</b>", body),
]

story += [H("OUTLOOK &mdash; ONE HONEST SENTENCE")]
story += [
    P("Reaffirm or change guidance, and say what has to be true for it. No hedging paragraphs.", body),
]

story += [H("PUT IT IN FRONT OF PEOPLE")]
story += [
    B("Save as PDF and attach it, <b>or</b>"),
    B("Embed the live builder:"),
    P('&nbsp;&nbsp;<font face="Courier" size="9">'
      '&lt;iframe src=&quot;one-pager.html&quot; '
      'style=&quot;width:100%;height:900px;border:0&quot;&gt;&lt;/iframe&gt;</font>', body),
]

story += [H("LICENCE")]
story += [
    P("Single-user / single-company licence. Use it for your own or your company's reviews, "
      "unlimited times. Do not resell or redistribute the files. Consultants: you may produce "
      "client reviews with it; you may not resell the template itself.", body),
]

story += [Spacer(1, 14)]
story += [P("&copy; Slate Studio &nbsp;|&nbsp; slate-studio-onepage.netlify.app", small)]


def on_page(canvas, doc):
    # Top accent bar in brand blue
    canvas.saveState()
    canvas.setFillColor(BLUE)
    canvas.rect(0, A4[1] - 6, A4[0], 6, stroke=0, fill=1)
    # Footer page number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Page {doc.page}")
    canvas.drawString(18 * mm, 12 * mm, "The One-Page Business Review — Method Guide")
    canvas.restoreState()


doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=20 * mm, rightMargin=20 * mm,
    topMargin=22 * mm, bottomMargin=20 * mm,
    title="The One-Page Business Review — Method Guide",
    author="Slate Studio",
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("OK:", OUTPUT)
