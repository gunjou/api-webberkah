from io import BytesIO
from flask import make_response
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.colors import HexColor

from api.shared.helper import safe_str
from api.templates.header_footer import header_landscape


def render_pegawai_pendidikan_pdf(pegawai_rows, filename):
    buffer = BytesIO()

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

    elements.append(Paragraph(
        "<b>DATA PENDIDIKAN PEGAWAI</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 14))

    table_data = [[
        "No",
        "NIP",
        "Nama Lengkap",
        "Jenjang",
        "Institusi",
        "Jurusan",
        "Tahun Masuk",
        "Tahun Lulus"
    ]]

    for idx, p in enumerate(pegawai_rows, start=1):
        table_data.append([
            idx,
            safe_str(p.get("nip")),
            safe_str(p.get("nama_lengkap")),
            safe_str(p.get("jenjang")),
            safe_str(p.get("institusi")),
            safe_str(p.get("jurusan")),
            safe_str(p.get("tahun_masuk")),
            safe_str(p.get("tahun_lulus")),
        ])

    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            30,
            80,
            140,
            70,
            180,
            160,
            80,
            80
        ]
    )

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), HexColor("#FADADD")),

        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ALIGN", (6,1), (7,-1), "CENTER"),

        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 9),

        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))

    elements.append(table)

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
