# api/purchase_request/pdf.py

import os
from io import BytesIO
from decimal import Decimal
from datetime import datetime, date

import requests
from PIL import Image as PILImage

from pypdf import PdfReader, PdfWriter

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "..", "assets", "logo.png")

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 30
# CONTENT_WIDTH = PAGE_WIDTH - (MARGIN_X * 2)

PRIMARY = colors.HexColor("#E53935")
BORDER = colors.HexColor("#777777")
LIGHT_GREY = colors.HexColor("#F3F3F3")
ZEBRA_GREY = colors.HexColor("#FCFCFC")
DARK_GREY = colors.HexColor("#444444")
WHITE = colors.white

PRIORITY_COLORS = {
    "NORMAL": colors.HexColor("#757575"),
    "URGENT": colors.HexColor("#FB8C00"),
    "TOP URGENT": colors.HexColor("#E53935"),
}


def _format_currency(value):
    if value is None:
        return "Rp 0"
    value = float(value) if isinstance(value, Decimal) else value
    return f"Rp {value:,.0f}".replace(",", ".")


def _format_number(value):
    if value is None:
        return "0"
    value = float(value) if isinstance(value, Decimal) else value
    if float(value).is_integer():
        return f"{int(value):,}".replace(",", ".")
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _format_date(value):
    if not value:
        return "-"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value

    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        return f"{days[value.weekday()]}, {value.day} {months[value.month - 1]} {value.year}"

    return str(value)


def _format_datetime(value):
    if not value:
        return "-"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime("%d-%m-%Y %H:%M") if isinstance(value, datetime) else str(value)


def _format_approval_date(value):
    if not value:
        return "-"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value

    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    return str(value)


def _safe(value):
    return "-" if value is None or (isinstance(value, str) and not value.strip()) else str(value)


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=20, alignment=TA_CENTER, spaceAfter=3),
        "request_no": ParagraphStyle("RequestNo", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12, alignment=TA_CENTER, textColor=DARK_GREY, spaceAfter=10),
        "label": ParagraphStyle("Label", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=DARK_GREY),
        "value": ParagraphStyle("Value", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=12),
        "section": ParagraphStyle("Section", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13, spaceBefore=0, spaceAfter=0, leftIndent=0, rightIndent=0),
        "header": ParagraphStyle("Header", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=TA_CENTER, textColor=WHITE),
        "cell": ParagraphStyle("Cell", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10),
        "cell_center": ParagraphStyle("CellCenter", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10, alignment=TA_CENTER),
        "cell_right": ParagraphStyle("CellRight", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10, alignment=TA_RIGHT),
        "note_label": ParagraphStyle("NoteLabel", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9, leading=12),
        "note": ParagraphStyle("Note", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=13, leftIndent=14),
        "approval": ParagraphStyle("Approval", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.5, leading=10, alignment=TA_CENTER),
        "approval_date": ParagraphStyle("ApprovalDate", parent=base["Normal"], fontName="Helvetica", fontSize=7, leading=9, alignment=TA_CENTER, textColor=DARK_GREY),
        "payment_label": ParagraphStyle("PaymentLabel", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=10),
        "payment_value": ParagraphStyle("PaymentValue", parent=base["Normal"], fontName="Helvetica", fontSize=8, leading=10),
    }


def _draw_header(canvas, doc):
    canvas.saveState()
    canvas.setAuthor("PT. Berkah Angsana Teknika")
    canvas.setTitle("Approval Request - PT. Berkah Angsana Teknika")
    canvas.setSubject("Approval Request")
    canvas.setCreator("Webberkah System")

    width, height = A4

    if os.path.exists(LOGO_PATH):
        canvas.drawImage(LOGO_PATH, MARGIN_X, height - 90, width=55, height=55, preserveAspectRatio=True, mask="auto")

    canvas.setFont("Helvetica-Bold", 15)
    canvas.setFillColor(PRIMARY)
    canvas.drawString(100, height - 45, "PT. BERKAH ANGSANA TEKNIKA")

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.black)

    address = [
        "Perumahan Bukit Citra Kencana, Block B no. 35, Jl. Pengsong Raya,",
        "Desa Perampuan, Kecamatan Labuapi, Lombok Barat, NTB.",
    ]

    y = height - 60
    for line in address:
        canvas.drawString(100, y, line)
        y -= 12

    canvas.drawString(100, y, "Phone : 0370 785 3692, Email :")
    canvas.setFillColor(colors.blue)
    canvas.drawString(235, y, "admin@berkahangsana.com")

    canvas.setStrokeColor(colors.grey)
    canvas.setLineWidth(1)
    canvas.line(MARGIN_X, height - 100, width - MARGIN_X, height - 100)
    canvas.restoreState()


def _priority_badge(priority, styles):
    priority = str(priority or "NORMAL").strip().upper()
    background = PRIORITY_COLORS.get(priority, PRIORITY_COLORS["NORMAL"])

    badge_style = ParagraphStyle(
        "PriorityBadge",
        parent=styles["value"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=WHITE,
    )

    table = Table([[Paragraph(priority, badge_style)]], colWidths=[30 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _request_information(pr, styles, content_width):
    rows = [
        ("Nama", _safe(pr.get("nama_pegawai"))),
        ("Tanggal", _format_date(pr.get("tanggal_request"))),
        ("Departemen", _safe(pr.get("nama_departemen"))),
        ("Nama Pekerjaan", _safe(pr.get("nama_pekerjaan"))),
    ]

    data = [[Paragraph(label, styles["label"]), Paragraph(f": {value}", styles["value"])] for label, value in rows]
    table = Table(data, colWidths=[38 * mm, content_width - (38 * mm)], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, -1), 3),
        # ("LEFTPADDING", (1, 0), (1, -1), 0),
        ("LEFTPADDING", (0, 0), (0, -1), 14),
        ("RIGHTPADDING", (1, 0), (1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table


def _request_section(pr, styles, content_width):
    heading = Table(
        [[
            Paragraph("INFORMASI PENGAJUAN", styles["section"]),
            _priority_badge(pr.get("priority"), styles),
        ]],
        colWidths=[content_width - (30 * mm), 30 * mm],
        hAlign="LEFT",
    )

    heading.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    return [heading, _request_information(pr, styles, content_width)]


def _items_table(items, pr, styles):
    data = [[
        Paragraph("No", styles["header"]),
        Paragraph("Keterangan", styles["header"]),
        Paragraph("Unit", styles["header"]),
        Paragraph("Harga Satuan", styles["header"]),
        Paragraph("Jumlah", styles["header"]),
        Paragraph("Total", styles["header"]),
    ]]

    for item in items:
        data.append([
            Paragraph(_safe(item.get("item_no")), styles["cell_center"]),
            Paragraph(_safe(item.get("keterangan")), styles["cell"]),
            Paragraph(_safe(item.get("unit")), styles["cell_center"]),
            Paragraph(_format_currency(item.get("harga_satuan")), styles["cell_right"]),
            Paragraph(_format_number(item.get("jumlah")), styles["cell_right"]),
            Paragraph(_format_currency(item.get("total")), styles["cell_right"]),
        ])

    data.append([
        "", "", "", "",
        Paragraph("<b>TOTAL</b>", styles["cell_right"]),
        Paragraph(f"<b>{_format_currency(pr.get('total_amount', 0))}</b>", styles["cell_right"]),
    ])

    col_widths = [12 * mm, 84 * mm, 20 * mm, 28 * mm, 19 * mm, 25 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")

    commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_GREY),
        ("SPAN", (0, -1), (3, -1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]

    for row in range(1, len(data) - 1):
        if row % 2 == 0:
            commands.append(("BACKGROUND", (0, row), (-1, row), ZEBRA_GREY))

    table.setStyle(TableStyle(commands))
    return table


def _note_section(pr, styles):
    return [
        Paragraph("Catatan:", styles["note_label"]),
        Spacer(1, 3),
        Paragraph(_safe(pr.get("note")), styles["note"]),
    ]


def _approval_data(history):
    result = {status: {"date": None, "pegawai": None} for status in ["REQUESTED", "REVIEWED", "APPROVED", "PAID"]}

    for row in history or []:
        status = str(row.get("status") or "").strip().upper()
        if status in result:
            result[status] = {"date": row.get("created_at"), "pegawai": row.get("nama_pegawai")}

    return result


def _approval_table(history, styles):
    approvals = _approval_data(history)
    statuses = ["REQUESTED", "REVIEWED", "APPROVED", "PAID"]

    status_style = ParagraphStyle(
        "ApprovalStatus",
        parent=styles["approval"],
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
    )
    name_style = ParagraphStyle(
        "ApprovalName",
        parent=styles["approval_date"],
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
    )
    line_style = ParagraphStyle(
        "ApprovalLine",
        parent=styles["approval_date"],
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=DARK_GREY,
    )

    col_width = (PAGE_WIDTH - (MARGIN_X * 2)) / 4

    header = Table(
        [[Paragraph(status, status_style) for status in statuses]],
        colWidths=[col_width] * 4,
        hAlign="LEFT",
    )
    header.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    body = Table(
        [[
            Paragraph(
                f"{_format_approval_date(approvals[s]['date'])}"
                f"<br/><br/><br/><br/>"
                f"{_safe(approvals[s]['pegawai'])}"
                f"<br/>____________________",
                name_style,
            )
            for s in statuses
        ]],
        colWidths=[col_width] * 4,
        hAlign="LEFT",
    )
    body.setStyle(TableStyle([
        ("BOX", (0, 0), (0, 0), 0.5, BORDER),
        ("BOX", (1, 0), (1, 0), 0.5, BORDER),
        ("BOX", (2, 0), (2, 0), 0.5, BORDER),
        ("BOX", (3, 0), (3, 0), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    return [
        header,
        Spacer(1, 4),
        body,
    ]


def _payment_table(pr, styles):
    rows = [
        ("Bank", _safe(pr.get("payment_bank"))),
        ("No. Rekening", _safe(pr.get("payment_account_number"))),
        ("Atas Nama", _safe(pr.get("payment_account_name"))),
        ("Keterangan", _safe(pr.get("payment_description"))),
    ]

    data = [[
        Paragraph(label, styles["label"]),
        Paragraph(f": {value}", styles["value"]),
        # Paragraph(label, styles["payment_label"]),
        # Paragraph(f": {value}", styles["payment_value"]),
    ] for label, value in rows]

    table = Table(data, colWidths=[38 * mm, PAGE_WIDTH - (MARGIN_X * 2) - 38 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, -1), 3),
        ("LEFTPADDING", (0, 0), (0, -1), 14),
        ("RIGHTPADDING", (1, 0), (1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(colors.grey)

    printed_at = f"{datetime.now().day:02d}/{datetime.now().month:02d}/{datetime.now().year}"

    canvas.drawString(
        MARGIN_X,
        20,
        f"Dokumen ini dicetak otomatis melalui sistem PT. Berkah Angsana Teknika pada: {printed_at}",
    )
    # canvas.drawRightString(
    #     PAGE_WIDTH - MARGIN_X,
    #     20,
    #     f"Halaman {doc.page}",
    # )

    canvas.restoreState()


def generate_purchase_request_pdf(purchase_request, items, history):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=38 * mm,
        bottomMargin=15 * mm,
        title="Approval Request",
        author="PT. Berkah Angsana Teknika",
    )

    styles = _styles()
    content_width = doc.width

    story = [
        Paragraph("APPROVAL REQUEST", styles["title"]),
        Paragraph(f"No: {_safe(purchase_request.get('request_number'))}", styles["request_no"]),
        *_request_section(purchase_request, styles, content_width),
        Spacer(1, 10),

        Paragraph("DAFTAR BARANG / PEMBAYARAN", styles["section"]),
        Spacer(1, 3),
        _items_table(items, purchase_request, styles),
        Spacer(1, 10),

        *_note_section(purchase_request, styles),
        Spacer(1, 15),

        Paragraph("INFORMASI PEMBAYARAN", styles["section"]),
        Spacer(1, 3),
        _payment_table(purchase_request, styles),
        Spacer(1, 10),

        Paragraph("APPROVAL", styles["section"]),
        Spacer(1, 5),
        *(_approval_table(history, styles)),
    ]

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: (_draw_header(canvas, doc), _draw_footer(canvas, doc)),
        onLaterPages=lambda canvas, doc: (_draw_header(canvas, doc), _draw_footer(canvas, doc)),
    )
    buffer.seek(0)
    return buffer



# =====================================================
# ATTACHMENT
# =====================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

PDF_EXTENSIONS = {
    ".pdf",
}


def _get_attachment_extension(url):
    """
    Mengambil extension attachment dari URL CDN.
    """

    if not url:
        return ""

    url_lower = url.lower()

    # Buang query string CDN
    url_lower = url_lower.split("?")[0]

    _, extension = os.path.splitext(url_lower)

    return extension


def _download_attachment(url):
    """
    Download attachment dari CDN.
    """

    if not url:
        return None

    try:
        response = requests.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        return response.content

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Gagal mengambil attachment dari CDN: {exc}"
        )


def _image_to_flowable(image_bytes):
    """
    Mengubah image bytes menjadi ReportLab Image.

    Ukuran gambar dibatasi maksimal A5
    agar tidak memenuhi halaman A4.
    """

    image_reader = ImageReader(
        BytesIO(image_bytes)
    )

    image_width, image_height = image_reader.getSize()

    if image_width <= 0 or image_height <= 0:
        return None

    # =================================================
    # MAXIMUM IMAGE SIZE
    # =================================================

    # A5 portrait:
    # 148 x 210 mm
    #
    # Kita beri sedikit ruang agar gambar
    # tidak terlalu mepet dengan title.

    max_width = 130 * mm
    max_height = 175 * mm

    ratio = min(
        max_width / image_width,
        max_height / image_height,
        1
    )

    display_width = image_width * ratio
    display_height = image_height * ratio

    image = Image(
        BytesIO(image_bytes),
        width=display_width,
        height=display_height,
    )

    return image


def _draw_attachment_header(canvas, doc):
    """
    Header untuk halaman attachment.
    """

    _draw_header(
        canvas,
        doc
    )


def _draw_attachment_footer(canvas, doc):
    """
    Footer untuk halaman attachment.

    Nomor halaman mengikuti halaman PDF utama
    karena menggunakan doc.page.
    """

    _draw_footer(
        canvas,
        doc
    )


def _image_to_pdf(image_bytes):
    """
    Mengubah satu gambar menjadi PDF satu halaman A4.

    Layout:

    Header perusahaan
    -----------------

             LAMPIRAN

             [ IMAGE ]

    -----------------
    Footer
    Halaman X
    """

    image = _image_to_flowable(
        image_bytes
    )

    if image is None:
        return None

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,

        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,

        # Header perusahaan menggunakan
        # area sampai sekitar 100pt dari atas.
        topMargin=40 * mm,

        # Footer berada di sekitar 20pt.
        bottomMargin=25 * mm,
    )

    styles = _styles()

    attachment_title = ParagraphStyle(
        "AttachmentTitle",
        parent=styles["title"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=12,
    )

    story = [
        Spacer(
            1,
            2 * mm
        ),

        Paragraph(
            "LAMPIRAN",
            attachment_title
        ),

        Spacer(
            1,
            8 * mm
        ),

        image,
    ]

    doc.build(
        story,
        onFirstPage=lambda canvas, doc: (
            _draw_attachment_header(
                canvas,
                doc
            ),
            _draw_attachment_footer(
                canvas,
                doc
            )
        ),
        onLaterPages=lambda canvas, doc: (
            _draw_attachment_header(
                canvas,
                doc
            ),
            _draw_attachment_footer(
                canvas,
                doc
            )
        ),
    )

    output.seek(0)

    return output


def _merge_pdf_attachment(
    writer,
    attachment_pdf
):
    """
    Menambahkan seluruh halaman PDF attachment
    ke writer PDF utama.
    """

    if not attachment_pdf:
        return

    attachment_reader = PdfReader(
        attachment_pdf
    )

    for page in attachment_reader.pages:
        writer.add_page(page)


def generate_purchase_request_pdf_with_attachment(
    purchase_request,
    items,
    history
):
    """
    Generate Purchase Request PDF beserta attachment.

    Behaviour:

    - Tidak ada attachment
        → hanya PDF utama.

    - Image attachment
        → image dikonversi menjadi satu halaman A4
          dengan title LAMPIRAN.

    - PDF attachment
        → seluruh halaman PDF langsung di-merge.

    Attachment selalu berada setelah seluruh
    halaman PDF utama.
    """

    # =================================================
    # 1. GENERATE MAIN PDF
    # =================================================

    main_pdf = generate_purchase_request_pdf(
        purchase_request=purchase_request,
        items=items,
        history=history
    )

    # =================================================
    # 2. CHECK ATTACHMENT
    # =================================================

    attachment_path = purchase_request.get(
        "attachment_path"
    )

    if not attachment_path:
        return main_pdf

    # =================================================
    # 3. DOWNLOAD ATTACHMENT
    # =================================================

    attachment_buffer = _download_attachment(
        attachment_path
    )

    if not attachment_buffer:
        return main_pdf

    # =================================================
    # 4. CREATE PDF WRITER
    # =================================================

    writer = PdfWriter()

    # =================================================
    # 5. ADD MAIN PDF
    # =================================================

    main_reader = PdfReader(
        main_pdf
    )

    for page in main_reader.pages:
        writer.add_page(page)

    # =================================================
    # 6. GET EXTENSION
    # =================================================

    extension = _get_attachment_extension(
        attachment_path
    )

    # =================================================
    # 7. PDF ATTACHMENT
    # =================================================

    if extension in PDF_EXTENSIONS:

        _merge_pdf_attachment(
            writer=writer,
            attachment_pdf=BytesIO(
                attachment_buffer
            )
        )

    # =================================================
    # 8. IMAGE ATTACHMENT
    # =================================================

    elif extension in IMAGE_EXTENSIONS:

        image_pdf = _image_to_pdf(
            attachment_buffer
        )

        if image_pdf:
            _merge_pdf_attachment(
                writer=writer,
                attachment_pdf=image_pdf
            )

    # =================================================
    # 9. UNSUPPORTED FORMAT
    # =================================================

    else:
        raise ValueError(
            f"Format attachment tidak didukung: {extension}"
        )

    # =================================================
    # 10. FINAL PDF
    # =================================================

    output = BytesIO()

    writer.write(
        output
    )

    output.seek(0)

    return output