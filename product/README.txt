EMBEDDABLE ROI / SAVINGS CALCULATOR
===================================
A drop-in lead-magnet calculator. One HTML file, no dependencies,
no build step, no tracking. Works on any website and on mobile.

WHAT'S INCLUDED
- roi-calculator-template.html  (the calculator — this is the product)
- README.txt                    (this file)

QUICK START (2 minutes)
1. Open roi-calculator-template.html in any text editor.
2. Find the CONFIG block near the bottom (clearly marked).
3. Change:
   - currency   : "$", "€", "£", "₺" ...
   - title / subtitle
   - labels     : the four input names
   - defaults   : the starting numbers your visitors see
   - ctaText / ctaUrl : your button text and your booking/contact link
4. Save. Done — open the file in a browser to check.

PUT IT ON YOUR SITE — pick one:
A) Easiest: upload the file and link to it, or embed it:
   <iframe src="roi-calculator-template.html"
           style="width:100%;height:760px;border:0"></iframe>
B) Inline: copy everything inside <body>...</body> (including the
   <style> and <script>) into your own page.

CUSTOMISE THE LOOK
At the top of the <style> block, the :root variables set the colours:
   --brand    your primary / button colour
   --brand-2  the positive result colour
Change those two to match your brand.

CHANGE THE MATH
The formula lives in the calc() function (well commented):
   net monthly  = gain - running cost
   total return = net monthly x months
   net gain     = total return - upfront cost
   ROI %        = net gain / upfront cost
   payback      = upfront cost / net monthly
Adjust freely for your use case (savings, software ROI, equipment, etc.).

LICENCE
Single-business licence: use on websites you or your company own,
unlimited pages. Do not resell or redistribute the file itself.

SUPPORT
It's a single static file by design — nothing to break. Questions:
use the contact link on the page you bought this from.
