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
# MAIN PDF RENDERER - LOKASI ABSENSI (DESIGN B)
# =====================================================
def render_pegawai_lokasi_absensi_pdf(rows, filename):
    buffer = BytesIO()

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
    # JUDUL
    # ===============================
    elements.append(Paragraph(
        "<b>DATA LOKASI ABSENSI PEGAWAI</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 14))

    # ===============================
    # GROUP DATA (pegawai → lokasi[])
    # ===============================
    pegawai_map = {}

    for row in rows:
        pid = row["id_pegawai"]

        pegawai_map.setdefault(pid, {
            "nip": row["nip"],
            "nama": row["nama_lengkap"],
            "status": row["status_pegawai"],
            "lokasi": []
        })

        if row.get("nama_lokasi"):
            pegawai_map[pid]["lokasi"].append(row["nama_lokasi"])

    # ===============================
    # STYLE UNTUK WRAP LOKASI
    # ===============================
    wrap_style = ParagraphStyle(
        "wrap",
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
        "Jumlah Lokasi",
        "Lokasi Absensi"
    ]]

    # ===============================
    # ISI TABEL
    # ===============================
    for idx, pegawai in enumerate(pegawai_map.values(), start=1):
        if pegawai["lokasi"]:
            lokasi_text = "<br/>".join(
                f"• {safe_str(l)}" for l in pegawai["lokasi"]
            )
        else:
            lokasi_text = "-"

        jumlah_lokasi = len(pegawai["lokasi"])

        table_data.append([
            idx,
            safe_str(pegawai["nip"]),
            safe_str(pegawai["nama"]),
            jumlah_lokasi,
            Paragraph(lokasi_text, wrap_style),
        ])

    # ===============================
    # TABEL
    # ===============================
    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[
            30,   # No
            80,   # NIP
            140,  # Nama
            90,   # Status
            160   # Lokasi (wrap)
        ]
    )

    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("BACKGROUND", (0,0), (-1,0), HexColor("#FADADD")),

        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ALIGN", (3,1), (3,-1), "CENTER"),

        ("VALIGN", (0,0), (-1,-1), "TOP"),
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
