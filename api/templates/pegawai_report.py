from io import BytesIO
from flask import make_response
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

from api.shared.helper import safe_str
from api.templates.header_footer import header_landscape


# =====================================================
# MAIN PDF RENDERER
# =====================================================
def render_pegawai_report_pdf(pegawai_rows, filename):
    buffer = BytesIO()

    # ===============================
    # LANDSCAPE A4
    # ===============================
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=110,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elements = []

    # ===============================
    # JUDUL DOKUMEN
    # ===============================
    elements.append(Paragraph(
        "<b>DATA PEGAWAI</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 12))

    # ===============================
    # STYLE KECIL (WRAP TEXT)
    # ===============================
    small_style = ParagraphStyle(
        "small",
        fontSize=7,
        leading=9
    )

    # ===============================
    # HEADER TABEL
    # ===============================
    table_data = [[
        "No", "NIP", "Nama", "JK",
        "Status", "Departemen", "Jabatan",
        "Telepon", "Email", "Alamat"
    ]]

    # ===============================
    # ISI DATA
    # ===============================
    for idx, p in enumerate(pegawai_rows, start=1):
        table_data.append([
            idx,
            safe_str(p.get("nip")),
            safe_str(p.get("nama_lengkap")),
            safe_str(p.get("jenis_kelamin")),
            safe_str(p.get("status_pegawai")),
            safe_str(p.get("nama_departemen")),
            safe_str(p.get("nama_jabatan")),
            Paragraph(safe_str(p.get("no_telepon")), small_style),
            Paragraph(safe_str(p.get("email_pribadi")), small_style),
            Paragraph(safe_str(p.get("alamat")), small_style),
        ])

    # ===============================
    # TABEL
    # ===============================
    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            25,   # No
            60,   # NIP
            100,   # Nama
            25,   # JK
            75,   # Status
            70,   # Dept
            75,   # Jabatan
            70,   # Telepon
            105,  # Email
            140   # Alamat
        ]
    )

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND", (0,0), (-1,0), HexColor("#FADADD")),

        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ALIGN", (3,1), (3,-1), "CENTER"),

        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 7),

        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    elements.append(table)

    # ===============================
    # BUILD PDF
    # ===============================
    doc.build(
        elements,
        onFirstPage=header_landscape,
        onLaterPages=header_landscape
    )

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response