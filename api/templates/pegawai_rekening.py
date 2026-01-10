from io import BytesIO
from flask import make_response
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

from api.shared.helper import safe_str
from api.templates.header_footer import header_portrait


# =====================================================
# MAIN PDF RENDERER - REKENING PEGAWAI
# =====================================================
def render_pegawai_rekening_pdf(pegawai_rows, filename):
    buffer = BytesIO()

    # ===============================
    # A4 PORTRAIT
    # ===============================
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=110,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elements = []

    # ===============================
    # JUDUL DOKUMEN
    # ===============================
    elements.append(Paragraph(
        "<b>LIST REKENING PEGAWAI</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 14))

    # ===============================
    # STYLE ISI
    # ===============================
    body_style = ParagraphStyle(
        "body",
        fontSize=9,
        leading=11
    )

    # ===============================
    # HEADER TABEL
    # ===============================
    table_data = [[
        "No",
        "NIP",
        "Nama Lengkap",
        "Bank",
        "Nomor Rekening",
        "Atas Nama"
    ]]

    # ===============================
    # ISI DATA
    # ===============================
    for idx, p in enumerate(pegawai_rows, start=1):
        table_data.append([
            idx,
            safe_str(p.get("nip")),
            safe_str(p.get("nama_lengkap")),
            safe_str(p.get("nama_bank")),
            Paragraph(safe_str(p.get("no_rekening")), body_style),
            safe_str(p.get("atas_nama")),
        ])

    # ===============================
    # TABEL
    # ===============================
    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            30,   # No
            70,   # NIP
            140,  # Nama
            80,   # Bank
            120,  # No Rekening
            110   # Atas Nama
        ]
    )

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), HexColor("#FADADD")),

        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

        ("FONTSIZE", (0,0), (-1,-1), 9),

        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))

    elements.append(table)

    # ===============================
    # BUILD PDF
    # ===============================
    doc.build(
        elements,
        onFirstPage=header_portrait,
        onLaterPages=header_portrait
    )

    pdf = buffer.getvalue()
    buffer.close()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
