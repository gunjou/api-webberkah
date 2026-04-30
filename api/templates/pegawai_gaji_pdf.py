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


def format_rp(value):
    try:
        value = int(value or 0)
        return f"Rp. {value:,.0f}".replace(",", ".")
    except:
        return "Rp. 0"


def render_pegawai_gaji_pdf(pegawai_rows, filename):
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
        "<b>LIST GAJI PEGAWAI</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 12))

    # ===============================
    # PREPARE DATA
    # ===============================
    komponen_map = {}
    pegawai_map = {}

    for row in pegawai_rows:
        id_pegawai = row["id_pegawai"]
        id_komponen = row["id_komponen"]

        # sekarang pakai NAMA KOMPONEN
        komponen_map[id_komponen] = row["nama_komponen"]

        if id_pegawai not in pegawai_map:
            pegawai_map[id_pegawai] = {
                "nip": row["nip"],
                "nama": row["nama_lengkap"],
                "status": row["status_pegawai"],
                "gaji_pokok": row["gaji_pokok"] or 0,
                "komponen": {}
            }

        pegawai_map[id_pegawai]["komponen"][id_komponen] = row["nilai"] or 0

    komponen_ids = sorted(komponen_map.keys())

    # ===============================
    # HEADER
    # ===============================
    header = [
        "No",
        "NIP",
        "Nama",
        "Status",
        "Gaji Pokok"
    ]

    for k_id in komponen_ids:
        header.append(komponen_map[k_id])

    header.append("Total")

    table_data = [header]

    # ===============================
    # ROW DATA
    # ===============================
    for idx, (id_pegawai, p) in enumerate(pegawai_map.items(), start=1):

        row_data = [
            idx,
            safe_str(p["nip"]),
            safe_str(p["nama"]),
            safe_str(p["status"]),
            format_rp(p["gaji_pokok"])
        ]

        total = p["gaji_pokok"]

        for k_id in komponen_ids:
            nilai = p["komponen"].get(k_id, 0)
            row_data.append(format_rp(nilai))
            total += nilai

        row_data.append(format_rp(total))

        table_data.append(row_data)

    # ===============================
    # TABLE
    # ===============================
    table = Table(table_data, repeatRows=1)

    style = TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), HexColor("#FADADD")),

        ("FONTSIZE", (0,0), (-1,-1), 8),

        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
    ])

    # ===============================
    # ZEBRA STRIPING
    # ===============================
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            style.add("BACKGROUND", (0, i), (-1, i), HexColor("#F5F5F5"))

    table.setStyle(style)

    elements.append(table)

    # ===============================
    # BUILD
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