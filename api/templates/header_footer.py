import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "..", "assets", "logo.png")


def _set_pdf_metadata(canvas, title):
    canvas.setAuthor("PT. Berkah Angsana Teknika")
    canvas.setTitle(title)
    canvas.setSubject("Dokumen Internal HRIS")
    canvas.setCreator("Webberkah HRIS System")


def header_landscape(canvas, doc):
    """
    Header surat untuk dokumen A4 Landscape
    """
    canvas.saveState()
    _set_pdf_metadata(canvas, "Laporan HRIS Berkah Angsana")
    width, height = landscape(A4)
    _draw_header(canvas, width, height)
    canvas.restoreState()


def header_portrait(canvas, doc):
    """
    Header surat untuk dokumen A4 Portrait
    """
    canvas.saveState()
    _set_pdf_metadata(canvas, "Laporan HRIS Berkah Angsana")
    width, height = A4
    _draw_header(canvas, width, height)
    canvas.restoreState()


# =====================================================
# INTERNAL SHARED HEADER DRAWER
# =====================================================
def _draw_header(canvas, width, height):
    # ===============================
    # LOGO
    # ===============================
    if os.path.exists(LOGO_PATH):
        canvas.drawImage(
            LOGO_PATH,
            30, height - 90,
            width=55,
            height=55,
            preserveAspectRatio=True,
            mask="auto"
        )

    # ===============================
    # NAMA PERUSAHAAN
    # ===============================
    canvas.setFont("Helvetica-Bold", 15)
    canvas.setFillColor(colors.HexColor("#E53935"))
    canvas.drawString(
        100, height - 45,
        "PT. BERKAH ANGSANA TEKNIKA"
    )

    # ===============================
    # ALAMAT
    # ===============================
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.black)

    alamat = [
        "Ruko Bukit Citra Kencana No.6, Jl. Pengsong Raya, Desa Perampuan,",
        "Kecamatan Labuapi, Lombok Barat, NTB."
    ]

    y = height - 60
    for line in alamat:
        canvas.drawString(100, y, line)
        y -= 12

    # ===============================
    # PHONE & EMAIL
    # ===============================
    canvas.drawString(100, y, "Phone : 0370 785 3692, Email : ")
    canvas.setFillColor(colors.blue)
    canvas.drawString(235, y, "admin@berkahangsana.com")

    # ===============================
    # GARIS PEMISAH
    # ===============================
    canvas.setStrokeColor(colors.grey)
    canvas.setLineWidth(1)
    canvas.line(30, height - 100, width - 30, height - 100)
