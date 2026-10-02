#!/usr/bin/env python3
"""
Generate synthetic US vendor invoices (one page each, PDF) for the Commercial
(Invoice-to-Pay) bootcamp. Three realistic layouts rotate across the vendors so
the IXP model sees the 8 target fields under different labels and positions, the way
real AP inboxes do: classic goods invoice, modern banded invoice, and a service
invoice with a remittance stub. All content is fictional; every page carries a
small synthetic-data notice.

Target fields: Vendor Name, Vendor Tax ID, Invoice Number, Invoice Date,
PO Number, Total Amount, Currency, Due Date.
"""
import os
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

W, H = letter

SYMBOL = {"USD": "$"}


def money(cur, amt):
    return f"{SYMBOL.get(cur, '')}{amt:,.2f}"


# Each invoice is one coherent scenario. Amounts are internally consistent
# (line items -> subtotal -> tax -> total). Some exceed the 10,000 USD approval
# threshold; one has a PO the ERP will not find (mismatch).
# 011 is reserved for the Maestro Flow homework challenge (reviewer path): a second
# Contoso Logistics invoice on PO-2026-0447 that matches within 2% and is over 10,000 USD.
INVOICES = [
    dict(seq="001", slug="northwind", vendor="Northwind Office Supplies Inc.",
         tax_id="47-2013865", invoice_no="NW-88214", invoice_date="03/04/2026",
         po="PO-2026-0431", currency="USD", terms="Net 30", due="04/03/2026",
         gl="6120 - Office Supplies", cc="CC-4400 Operations", approver="Dana Whitfield",
         addr="1420 Elm Ridge Pkwy, Columbus, OH 43215",
         bill_to="Globex Manufacturing - Accounts Payable\nPO Box 5591, Columbus, OH 43216",
         bank="Fifth Meridian Bank  ·  Routing 000000000  ·  Acct •••• 4821",
         lines=[("Multipurpose copy paper, 92 bright, letter", 40, "case", 31.00),
                ("Toner cartridge, HP 58X high yield", 12, "ea", 179.00),
                ("Breakroom coffee, 2 lb bags", 18, "ea", 15.25),
                ("Disposable cups & cutlery, assorted", 8, "case", 26.50)],
         tax_rate=0.0725),
    dict(seq="002", slug="contoso-logistics", vendor="Contoso Logistics LLC",
         tax_id="82-4471900", invoice_no="CLL-2026-3391", invoice_date="03/06/2026",
         po="PO-2026-0447", currency="USD", terms="Net 45", due="04/20/2026",
         gl="6410 - Freight & Delivery", cc="CC-5100 Distribution", approver="Marcus Reyes",
         addr="8800 Cargo Way, Bldg C, Memphis, TN 38118",
         bill_to="Globex Manufacturing - Accounts Payable\nPO Box 5591, Columbus, OH 43216",
         bank="Delta River Trust  ·  Routing 000000000  ·  Acct •••• 7710",
         lines=[("Full-truckload freight, lane MEM to COL", 10, "load", 982.00),
                ("Fuel surcharge, March index", 1, "lot", 2140.00),
                ("Detention at consignee", 6, "hr", 95.00),
                ("Liftgate & accessorial fees", 3, "ea", 70.00)],
         tax_rate=0.00),
    dict(seq="003", slug="ableton-fabrication", vendor="Ableton Fabrication, Inc.",
         tax_id="26-1509338", invoice_no="AF19427", invoice_date="03/09/2026",
         po="PO-2026-0452", currency="USD", terms="Net 30", due="04/08/2026",
         gl="5300 - Raw Materials", cc="CC-3200 Production", approver="Priya Nadkarni",
         addr="55 Foundry St, Worcester, MA 01604",
         bill_to="Globex Manufacturing - Accounts Payable\nPO Box 5591, Columbus, OH 43216",
         bank="Bay State Commerce Bank  ·  Routing 000000000  ·  Acct •••• 1093",
         lines=[("CNC-milled aluminum bracket, 6061-T6, P/N AB-4410", 500, "ea", 5.10),
                ("Setup & tooling, bracket run", 1, "lot", 600.00),
                ("Powder-coat finish, RAL 7016", 500, "ea", 1.28)],
         tax_rate=0.0625),
    dict(seq="004", slug="meridian-cloud", vendor="Meridian Cloud Services Corp.",
         tax_id="91-3320764", invoice_no="MCS-Q1-20418", invoice_date="03/01/2026",
         po="PO-2026-0399", currency="USD", terms="Net 30", due="03/31/2026",
         gl="7220 - Software & Cloud", cc="CC-6000 Information Technology", approver="Helena Fischer",
         addr="200 Bayfront Ave, Suite 1900, Seattle, WA 98121",
         bill_to="Globex Manufacturing - IT Procurement\nPO Box 5591, Columbus, OH 43216",
         bank="Cascade National Bank  ·  Routing 000000000  ·  Acct •••• 6642",
         lines=[("Managed compute, reserved vCPU, Q1", 400, "vCPU-mo", 31.00),
                ("Object storage, standard tier", 220, "TB-mo", 14.00),
                ("Premium support tier", 3, "mo", 500.00)],
         tax_rate=0.00),
    dict(seq="005", slug="blue-harbor-catering", vendor="Blue Harbor Catering Co.",
         tax_id="33-7788214", invoice_no="BHC-4471", invoice_date="03/11/2026",
         po="PO-2026-0461", currency="USD", terms="Net 15", due="03/26/2026",
         gl="6720 - Meals & Events", cc="CC-4400 Operations", approver="Dana Whitfield",
         addr="17 Wharf Lane, Portland, ME 04101",
         bill_to="Globex Manufacturing - Facilities\nPO Box 5591, Columbus, OH 43216",
         bank="Casco Bay Savings  ·  Routing 000000000  ·  Acct •••• 2250",
         lines=[("All-hands lunch buffet", 180, "guest", 11.50),
                ("Beverage station & dessert", 1, "lot", 190.00),
                ("Service staff", 6, "hr", 65.00),
                ("Delivery & setup", 1, "trip", 150.00)],
         tax_rate=0.055),
    dict(seq="006", slug="great-lakes-steel", vendor="Great Lakes Steel Supply Inc.",
         tax_id="38-4410927", invoice_no="GLS-2026-0442", invoice_date="03/05/2026",
         po="PO-2026-0470", currency="USD", terms="Net 30", due="04/04/2026",
         gl="5300 - Raw Materials", cc="CC-3200 Production", approver="Priya Nadkarni",
         addr="1400 Zug Island Rd, Detroit, MI 48209",
         bill_to="Globex Manufacturing - Accounts Payable\nPO Box 5591, Columbus, OH 43216",
         bank="Great Lakes Commerce Bank  ·  Routing 000000000  ·  Acct •••• 3120",
         lines=[("Cold-rolled steel coil, 1008 CR, 0.040 in", 18, "ton", 820.00),
                ("Cut-to-length processing", 18, "ton", 95.00),
                ("Protective packaging & strapping", 1, "lot", 500.00)],
         tax_rate=0.06),
    dict(seq="007", slug="liberty-print", vendor="Liberty Print & Signage LLC",
         tax_id="36-5127744", invoice_no="LPS-55210", invoice_date="03/09/2026",
         po="PO-2026-0476", currency="USD", terms="Net 30", due="04/08/2026",
         gl="6210 - Marketing & Print", cc="CC-7100 Marketing", approver="Oliver Grant",
         addr="4 Kingsway Trade Park, Elk Grove Village, IL 60007",
         bill_to="Globex Manufacturing - Accounts Payable\nPO Box 5591, Columbus, OH 43216",
         bank="Prairie State Bank  ·  Routing 000000000  ·  Acct •••• 3388",
         lines=[("Exhibition roller banners, 33 in", 12, "ea", 145.00),
                ("Modular stand graphics, 10 ft x 7 ft", 4, "panel", 420.00),
                ("Branded aluminum signage, powder-coated", 8, "ea", 145.00)],
         tax_rate=0.08),
    dict(seq="008", slug="summit-facilities", vendor="Summit Facilities Group",
         tax_id="45-6612093", invoice_no="SFG-2026-0771", invoice_date="03/12/2026",
         po="PO-2026-0468", currency="USD", terms="Net 30", due="04/11/2026",
         gl="6510 - Facilities & Maintenance", cc="CC-4400 Operations", approver="Dana Whitfield",
         addr="9 Cornerstone Blvd, Aurora, CO 80011",
         bill_to="Globex Manufacturing - Facilities\nPO Box 5591, Columbus, OH 43216",
         bank="Front Range Bank  ·  Routing 000000000  ·  Acct •••• 5501",
         lines=[("HVAC preventive maintenance visit, Q1", 4, "visit", 620.00),
                ("Rooftop unit coil cleaning", 2, "unit", 250.00),
                ("Filters, MERV 13, 24x24x2", 30, "ea", 14.50),
                ("Drive belts, replacement", 6, "ea", 30.00)],
         tax_rate=0.029),
    dict(seq="009", slug="vertex-analytics", vendor="Vertex Analytics Corp.",
         tax_id="88-2245107", invoice_no="VA-INV-40592", invoice_date="03/02/2026",
         po="PO-2026-0405", currency="USD", terms="Net 45", due="04/16/2026",
         gl="7410 - Professional Services", cc="CC-6000 Information Technology", approver="Helena Fischer",
         addr="410 Innovation Dr, Suite 700, Austin, TX 78701",
         bill_to="Globex Manufacturing - IT Procurement\nPO Box 5591, Columbus, OH 43216",
         bank="Lone Star Commerce Bank  ·  Routing 000000000  ·  Acct •••• 9014",
         lines=[("Data platform implementation, milestone 2", 1, "milestone", 18500.00),
                ("On-site enablement workshop", 3, "day", 1400.00)],
         tax_rate=0.00),
    dict(seq="010", slug="pacific-timber", vendor="Pacific Timber Company",
         tax_id="93-1180446", invoice_no="PTC-2026-2287", invoice_date="03/13/2026",
         po="PO-2026-0489", currency="USD", terms="Net 30", due="04/12/2026",
         gl="5300 - Raw Materials", cc="CC-3200 Production", approver="Priya Nadkarni",
         addr="2600 Millport Rd, Tacoma, WA 98421",
         bill_to="Globex Manufacturing - Accounts Payable\nPO Box 5591, Columbus, OH 43216",
         bank="Puget Sound Mutual  ·  Routing 000000000  ·  Acct •••• 4407",
         lines=[("Kiln-dried dimensional lumber 2x6x16, #2 & btr", 20, "pallet", 406.00),
                ("Freight, Tacoma to Columbus", 1, "load", 790.00),
                ("Handling & banding", 1, "lot", 150.00)],
         tax_rate=0.093),
    dict(seq="011", slug="contoso-logistics", vendor="Contoso Logistics LLC",
         tax_id="82-4471900", invoice_no="CLL-2026-3418", invoice_date="03/13/2026",
         po="PO-2026-0447", currency="USD", terms="Net 45", due="04/27/2026",
         gl="6410 - Freight & Delivery", cc="CC-5100 Distribution", approver="Marcus Reyes",
         addr="8800 Cargo Way, Bldg C, Memphis, TN 38118",
         bill_to="Globex Manufacturing - Accounts Payable\nPO Box 5591, Columbus, OH 43216",
         bank="Delta River Trust  ·  Routing 000000000  ·  Acct •••• 7710",
         lines=[("Full-truckload freight, lane MEM to COL, second half of March", 10, "load", 985.00),
                ("Fuel surcharge, late-March index", 1, "lot", 2210.00),
                ("Detention at consignee", 4, "hr", 95.00),
                ("Liftgate & accessorial fees", 4, "ea", 70.00)],
         tax_rate=0.00),
]


def amount(item):
    _desc, qty, _unit, unit_price = item
    return round(qty * unit_price, 2)


def computed(inv):
    subtotal = sum(amount(item) for item in inv["lines"])
    tax = round(subtotal * inv["tax_rate"], 2)
    total = round(subtotal + tax, 2)
    return subtotal, tax, total



M = 0.75 * inch            # page margin
CONTENT_W = W - 2 * M
NAVY = (0.09, 0.16, 0.28)
SLATE = (0.35, 0.40, 0.47)
LIGHT = (0.94, 0.95, 0.97)
RULE = (0.80, 0.83, 0.87)
INK = (0.10, 0.12, 0.15)


def fill(c, rgb):
    c.setFillColorRGB(*rgb)


def stroke(c, rgb, width=0.6):
    c.setStrokeColorRGB(*rgb)
    c.setLineWidth(width)


def text(c, x, y, s, size=9.5, font="Helvetica", rgb=INK, align="left"):
    c.setFont(font, size)
    fill(c, rgb)
    if align == "right":
        c.drawRightString(x, y, s)
    elif align == "center":
        c.drawCentredString(x, y, s)
    else:
        c.drawString(x, y, s)


def contact(inv):
    """Deterministic synthetic phone / email / web for the vendor letterhead."""
    n = int(inv["seq"])
    phone = f"({200 + n * 37 % 700:03d}) 555-{1000 + n * 811 % 9000:04d}"
    return phone, f"billing@{inv['slug']}.example", f"www.{inv['slug']}.example"


SHIP_TO = "Globex Manufacturing - Receiving Dock 3\n2200 Industrial Pkwy, Columbus, OH 43219"


def block(c, x, y, title, body, title_size=8, body_size=9.5, gap=12.5, title_rgb=SLATE):
    text(c, x, y, title, title_size, "Helvetica-Bold", title_rgb)
    yy = y - 13
    for ln in body.split("\n"):
        text(c, x, yy, ln, body_size)
        yy -= gap
    return yy


def synthetic_note(c, y=0.45 * inch):
    text(c, W / 2, y, "Synthetic sample for UiPath Commercial Bootcamp training. Vendor, amounts, tax and bank identifiers are fictional.", 6.8, "Helvetica-Oblique", SLATE, "center")


def totals_block(c, inv, x_label, x_value, y, label_size=9.5, total_size=11.5, boxed=False, box_rgb=LIGHT, total_label="TOTAL DUE"):
    subtotal, tax, total = computed(inv)
    cur = inv["currency"]
    text(c, x_label, y, "Subtotal", label_size, rgb=SLATE, align="right")
    text(c, x_value, y, money(cur, subtotal), label_size, align="right"); y -= 15
    text(c, x_label, y, f"Sales Tax ({inv['tax_rate'] * 100:g}%)", label_size, rgb=SLATE, align="right")
    text(c, x_value, y, money(cur, tax), label_size, align="right"); y -= 19
    if boxed:
        fill(c, box_rgb)
        c.rect(x_label - 96, y - 7, x_value - x_label + 104, 22, fill=1, stroke=0)
    text(c, x_label, y, total_label, total_size, "Helvetica-Bold", INK if not boxed or box_rgb == LIGHT else (1, 1, 1), "right")
    text(c, x_value, y, f"{money(cur, total)} {cur}", total_size, "Helvetica-Bold", INK if not boxed or box_rgb == LIGHT else (1, 1, 1), "right")
    return y


# ---------------------------------------------------------------- layout A: classic goods invoice
def layout_classic(c, inv):
    phone, email, web = contact(inv)
    cur = inv["currency"]
    y = H - M
    # letterhead left, INVOICE + meta box right
    text(c, M, y - 14, inv["vendor"], 17, "Helvetica-Bold")
    text(c, M, y - 29, inv["addr"], 8.8, rgb=SLATE)
    text(c, M, y - 41, f"{phone}   ·   {email}   ·   {web}", 8.8, rgb=SLATE)
    text(c, M, y - 53, f"Federal Tax ID (EIN): {inv['tax_id']}", 8.8, rgb=SLATE)
    text(c, W - M, y - 16, "INVOICE", 26, "Helvetica-Bold", NAVY, "right")

    box_w, box_x, box_y = 2.75 * inch, W - M - 2.75 * inch, y - 118
    stroke(c, RULE, 0.8)
    c.roundRect(box_x, box_y, box_w, 88, 4, fill=0, stroke=1)
    rows = [("Invoice #", inv["invoice_no"], True), ("Invoice Date", inv["invoice_date"], False),
            ("Due Date", inv["due"], False), ("PO Number", inv["po"], True), ("Terms", inv["terms"], False), ("Currency", cur, False)]
    ry = box_y + 88 - 14
    for label, val, bold in rows:
        text(c, box_x + 10, ry, label, 8.5, rgb=SLATE)
        text(c, box_x + box_w - 10, ry, val, 9.2, "Helvetica-Bold" if bold else "Helvetica", align="right")
        ry -= 13.6

    y = box_y - 22
    stroke(c, RULE); c.line(M, y + 8, W - M, y + 8)
    block(c, M, y - 8, "BILL TO", inv["bill_to"])
    block(c, M + CONTENT_W / 2, y - 8, "SHIP TO", SHIP_TO)

    # items table
    y -= 66
    cols = {"qty": M + 44, "desc": M + 58, "unit": M + 318, "price": M + 408, "amt": W - M}
    fill(c, LIGHT); c.rect(M, y - 6, CONTENT_W, 20, fill=1, stroke=0)
    text(c, cols["qty"], y, "QTY", 8, "Helvetica-Bold", SLATE, "right")
    text(c, cols["desc"], y, "DESCRIPTION", 8, "Helvetica-Bold", SLATE)
    text(c, cols["unit"], y, "UNIT", 8, "Helvetica-Bold", SLATE)
    text(c, cols["price"], y, "UNIT PRICE", 8, "Helvetica-Bold", SLATE, "right")
    text(c, cols["amt"], y, "AMOUNT", 8, "Helvetica-Bold", SLATE, "right")
    y -= 22
    for i, item in enumerate(inv["lines"]):
        desc, qty, unit, price = item
        if i % 2 == 1:
            fill(c, (0.985, 0.985, 0.99)); c.rect(M, y - 6, CONTENT_W, 19, fill=1, stroke=0)
        text(c, cols["qty"], y, f"{qty:g}", 9.5, align="right")
        text(c, cols["desc"], y, desc, 9.5)
        text(c, cols["unit"], y, unit, 9.2, rgb=SLATE)
        text(c, cols["price"], y, money(cur, price), 9.5, align="right")
        text(c, cols["amt"], y, money(cur, amount(item)), 9.5, align="right")
        y -= 19
    stroke(c, RULE); c.line(M, y + 6, W - M, y + 6)

    # totals right, payment info left
    ty = totals_block(c, inv, W - M - 110, W - M, y - 14, boxed=True)
    block(c, M, y - 10, "PAYMENT", f"Terms: {inv['terms']}. Please reference invoice {inv['invoice_no']} on your remittance.\nRemit to: {inv['bank']}\nMake checks payable to {inv['vendor']}", body_size=8.6, gap=12)
    text(c, M, ty - 44, "Thank you for your business.", 9, "Helvetica-Oblique", SLATE)
    synthetic_note(c)


# ---------------------------------------------------------------- layout B: modern banded invoice
def layout_banded(c, inv):
    phone, email, web = contact(inv)
    cur = inv["currency"]
    subtotal, tax, total = computed(inv)
    band_h = 1.05 * inch
    fill(c, NAVY); c.rect(0, H - band_h, W, band_h, fill=1, stroke=0)
    text(c, M, H - 0.5 * inch, inv["vendor"], 19, "Helvetica-Bold", (1, 1, 1))
    text(c, M, H - 0.5 * inch - 15, f"{inv['addr']}   ·   {phone}", 8.6, rgb=(0.78, 0.83, 0.90))
    text(c, W - M, H - 0.46 * inch, "INVOICE", 22, "Helvetica-Bold", (1, 1, 1), "right")
    text(c, W - M, H - 0.46 * inch - 16, f"No. {inv['invoice_no']}", 10, "Helvetica-Bold", (1, 0.62, 0.11), "right")

    y = H - band_h - 30
    # left: bill to / ship to; right: meta grid + amount due
    block(c, M, y, "BILL TO", inv["bill_to"])
    block(c, M, y - 56, "SHIP TO", SHIP_TO)
    gx = W - M - 2.6 * inch
    meta = [("Invoice Date", inv["invoice_date"]), ("Due Date", inv["due"]), ("PO Number", inv["po"]), ("Payment Terms", inv["terms"]), ("Vendor EIN", inv["tax_id"])]
    my = y
    for label, val in meta:
        text(c, gx, my, label, 8.5, rgb=SLATE)
        text(c, W - M, my, val, 9.2, "Helvetica-Bold", align="right")
        stroke(c, RULE, 0.5); c.line(gx, my - 5, W - M, my - 5)
        my -= 16
    fill(c, LIGHT); c.roundRect(gx, my - 26, W - M - gx, 30, 4, fill=1, stroke=0)
    text(c, gx + 8, my - 15, "AMOUNT DUE", 8.5, "Helvetica-Bold", SLATE)
    text(c, W - M - 8, my - 16, f"{money(cur, total)} {cur}", 12.5, "Helvetica-Bold", NAVY, "right")

    y = my - 60
    cols = {"desc": M, "qty": M + 300, "rate": M + 395, "amt": W - M}
    text(c, cols["desc"], y, "DESCRIPTION", 8, "Helvetica-Bold", NAVY)
    text(c, cols["qty"], y, "QTY", 8, "Helvetica-Bold", NAVY, "right")
    text(c, cols["rate"], y, "RATE", 8, "Helvetica-Bold", NAVY, "right")
    text(c, cols["amt"], y, "AMOUNT", 8, "Helvetica-Bold", NAVY, "right")
    stroke(c, NAVY, 1.2); c.line(M, y - 6, W - M, y - 6)
    y -= 24
    for item in inv["lines"]:
        desc, qty, unit, price = item
        text(c, cols["desc"], y, desc, 9.5)
        text(c, cols["desc"], y - 10, f"per {unit}", 7.5, rgb=SLATE)
        text(c, cols["qty"], y, f"{qty:g}", 9.5, align="right")
        text(c, cols["rate"], y, money(cur, price), 9.5, align="right")
        text(c, cols["amt"], y, money(cur, amount(item)), 9.5, align="right")
        stroke(c, RULE, 0.5); c.line(M, y - 16, W - M, y - 16)
        y -= 26
    ty = totals_block(c, inv, W - M - 110, W - M, y - 6, total_label="BALANCE DUE", boxed=True, box_rgb=NAVY)
    block(c, M, y - 2, "NOTES", f"Please include invoice number {inv['invoice_no']} with your payment.\nACH / wire: {inv['bank']}\nAll amounts in {cur}. Questions: {email}", body_size=8.6, gap=12)
    text(c, M, ty - 40, "We appreciate your business.", 9, "Helvetica-Oblique", SLATE)
    synthetic_note(c)


# ---------------------------------------------------------------- layout C: service invoice with remittance stub
def layout_service(c, inv):
    phone, email, web = contact(inv)
    cur = inv["currency"]
    subtotal, tax, total = computed(inv)
    y = H - M
    text(c, W / 2, y - 12, inv["vendor"], 16, "Helvetica-Bold", align="center")
    text(c, W / 2, y - 26, f"{inv['addr']}   ·   {phone}   ·   {web}", 8.6, rgb=SLATE, align="center")
    stroke(c, INK, 1.0); c.line(M, y - 36, W - M, y - 36)
    stroke(c, RULE, 0.5); c.line(M, y - 39, W - M, y - 39)

    y -= 66
    text(c, M, y, "INVOICE", 20, "Helvetica-Bold")
    block(c, M, y - 24, "INVOICE TO", inv["bill_to"])
    block(c, M, y - 80, "SERVICE / SHIP LOCATION", SHIP_TO)
    # right meta table with ruled rows
    tx = W - M - 2.7 * inch
    meta = [("Invoice Number:", inv["invoice_no"]), ("Invoice Date:", inv["invoice_date"]), ("Payment Due:", inv["due"]),
            ("Customer PO:", inv["po"]), ("Terms:", inv["terms"]), ("Tax ID:", inv["tax_id"]), ("Currency:", cur)]
    my = y + 4
    stroke(c, RULE, 0.6)
    c.rect(tx, my - len(meta) * 15 - 4, W - M - tx, len(meta) * 15 + 8, fill=0, stroke=1)
    for label, val in meta:
        text(c, tx + 8, my - 8, label, 8.5, rgb=SLATE)
        text(c, W - M - 8, my - 8, val, 9.2, "Helvetica-Bold", align="right")
        my -= 15

    # grid table
    y -= 132
    cols = [M, M + 40, M + 320, M + 370, M + 440, W - M]  # item | desc | qty | unit price | line total
    heads = ["ITEM", "DESCRIPTION", "QTY", "UNIT PRICE", "LINE TOTAL"]
    row_h = 20
    fill(c, LIGHT); c.rect(M, y - 6, CONTENT_W, row_h, fill=1, stroke=0)
    for i, hd in enumerate(heads):
        right = i >= 2
        text(c, cols[i + 1] - 6 if right else cols[i] + 6, y, hd, 8, "Helvetica-Bold", SLATE, "right" if right else "left")
    stroke(c, RULE, 0.6)
    n = len(inv["lines"])
    top = y + row_h - 6
    bottom = y - 6 - n * row_h
    c.rect(M, bottom, CONTENT_W, top - bottom, fill=0, stroke=1)
    for cx in cols[1:-1]:
        c.line(cx, top, cx, bottom)
    yy = y - row_h
    for i, item in enumerate(inv["lines"], start=1):
        desc, qty, unit, price = item
        c.line(M, yy + row_h - 6, W - M, yy + row_h - 6)
        text(c, cols[0] + 6, yy, f"{i:02d}", 9.2, rgb=SLATE)
        text(c, cols[1] + 6, yy, f"{desc} ({unit})", 9.3)
        text(c, cols[3] - 6, yy, f"{qty:g}", 9.3, align="right")
        text(c, cols[4] - 6, yy, money(cur, price), 9.3, align="right")
        text(c, cols[5] - 6, yy, money(cur, amount(item)), 9.3, align="right")
        yy -= row_h
    ty = totals_block(c, inv, W - M - 110, W - M - 6, bottom - 20, total_label=f"TOTAL ({cur})")
    bank_name, _, bank_rest = inv["bank"].partition("  ·  ")
    block(c, M, bottom - 16, "TERMS", f"{inv['terms']} from invoice date.\n1.5% monthly finance charge on past-due balances.\nRemit to: {bank_name}\n{bank_rest}", body_size=8.6, gap=12)

    # remittance stub
    sy = 1.55 * inch
    stroke(c, SLATE, 0.6); c.setDash(3, 3); c.line(M, sy + 62, W - M, sy + 62); c.setDash()
    text(c, W / 2, sy + 52, "✂  Please detach and return this stub with your payment", 7.5, "Helvetica-Oblique", SLATE, "center")
    text(c, M, sy + 30, "REMITTANCE", 9, "Helvetica-Bold", SLATE)
    text(c, M, sy + 15, f"{inv['vendor']}  ·  {inv['addr']}", 8.6)
    for i, (label, val) in enumerate([("Invoice #", inv["invoice_no"]), ("Customer PO", inv["po"]), ("Due Date", inv["due"]), ("Amount Due", f"{money(cur, total)} {cur}")]):
        x = M + 250 + i * 80
        text(c, x, sy + 30, label, 7.5, rgb=SLATE)
        text(c, x, sy + 15, val, 8.8, "Helvetica-Bold")
    text(c, M, sy - 4, "Amount enclosed: $ ______________", 8.6, rgb=SLATE)
    synthetic_note(c)


LAYOUTS = [layout_classic, layout_banded, layout_service]


def build(inv, path):
    c = canvas.Canvas(path, pagesize=letter)
    c.setTitle(f"Invoice {inv['invoice_no']} - {inv['vendor']} (synthetic)")
    c.setAuthor(inv["vendor"] + " (synthetic sample)")
    LAYOUTS[(int(inv["seq"]) - 1) % len(LAYOUTS)](c, inv)
    c.showPage()
    c.save()


def write_email(inv, pdf_path, eml_path):
    """The vendor's email to AP with the invoice attached — how invoices actually arrive."""
    _phone, email, _web = contact(inv)
    subtotal, tax, total = computed(inv)
    cur = inv["currency"]
    msg = EmailMessage()
    msg["From"] = f"{inv['vendor']} Billing <{email}>"
    msg["To"] = "Globex Manufacturing Accounts Payable <invoices@globex-ap.example>"
    msg["Subject"] = f"Invoice {inv['invoice_no']} for PO {inv['po']} - {inv['vendor']}"
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain=f"{inv['slug']}.example")
    msg.set_content(
        f"""Hello Accounts Payable,

Please find attached invoice {inv['invoice_no']} dated {inv['invoice_date']} against purchase order {inv['po']}.

    Amount due: {money(cur, total)} {cur}
    Terms:      {inv['terms']} (due {inv['due']})

Remittance details are on the invoice. Reply to this address with any questions.

Thank you,
{inv['vendor']} - Billing
{inv['addr']}

(Synthetic sample for UiPath Commercial Bootcamp training. Vendor, amounts and identifiers are fictional.)
"""
    )
    with open(pdf_path, "rb") as fh:
        msg.add_attachment(fh.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))
    with open(eml_path, "wb") as out:
        out.write(msg.as_bytes())


# Where each invoice lands: lab1 gets 006-010, lab2 gets 001-005 (original convention),
# and 011 goes to the homework challenge folder.
LAB1_SEQS = {"006", "007", "008", "009", "010"}
CHALLENGE_SEQS = {"011"}

# Invoice 011 must route to the reviewer path: matched against PO-2026-0447
# (openAmount 12,740.00, |total - open| <= 2%) and over the 10,000 USD threshold.
CHALLENGE_PO_OPEN_AMOUNT = 12740.00


def check_challenge_invoice(inv):
    _subtotal, _tax, total = computed(inv)
    low, high = CHALLENGE_PO_OPEN_AMOUNT * 0.98, CHALLENGE_PO_OPEN_AMOUNT * 1.02
    assert inv["po"] == "PO-2026-0447", inv["po"]
    assert low <= total <= high and total > 10000, f"invoice {inv['seq']} total {total} outside [{low:.2f}, {high:.2f}]"


def destination(out_root, seq):
    if seq in CHALLENGE_SEQS:
        return os.path.join(out_root, "challenge-maestro-flow")
    if seq in LAB1_SEQS:
        return os.path.join(out_root, "lab1-ixp")
    return os.path.join(out_root, "lab2-rpa")


def main():
    """Usage: generate_invoices.py <out_root> [seq ...]

    With no seq arguments every invoice is regenerated. Pass one or more seqs (for
    example `011`) to write only those, leaving the other PDFs and emails untouched.
    """
    out_root = sys.argv[1]
    only = set(sys.argv[2:])
    unknown = only - {inv["seq"] for inv in INVOICES}
    if unknown:
        sys.exit(f"unknown seq: {', '.join(sorted(unknown))}")
    for inv in INVOICES:
        if only and inv["seq"] not in only:
            continue
        if inv["seq"] in CHALLENGE_SEQS:
            check_challenge_invoice(inv)
        dest = destination(out_root, inv["seq"])
        os.makedirs(dest, exist_ok=True)
        fname = f"commercial-invoice-{inv['seq']}-{inv['slug']}.pdf"
        pdf_path = os.path.join(dest, fname)
        build(inv, pdf_path)
        print("wrote", os.path.join(os.path.basename(dest), fname))
        eml_dir = os.path.join(dest, "emails")
        os.makedirs(eml_dir, exist_ok=True)
        eml_path = os.path.join(eml_dir, fname.replace(".pdf", ".eml"))
        write_email(inv, pdf_path, eml_path)
        print("wrote", os.path.join(os.path.basename(dest), "emails", os.path.basename(eml_path)))


if __name__ == "__main__":
    main()
