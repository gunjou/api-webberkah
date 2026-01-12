from datetime import time


def hitung_menit_terlambat(jam_masuk: time, jam_mulai_kerja: time = time(8, 0)) -> int:
    """
    Hitung keterlambatan dalam menit
    - Detik diabaikan
    - Jika <= jam_mulai_kerja → 0
    """
    masuk_detik = (jam_masuk.hour * 3600 + jam_masuk.minute * 60 + jam_masuk.second)
    mulai_detik = (jam_mulai_kerja.hour * 3600 + jam_mulai_kerja.minute * 60)

    if masuk_detik <= mulai_detik:
        return 0

    selisih_detik = masuk_detik - mulai_detik
    return selisih_detik // 60


def hitung_durasi_menit(jam_mulai, jam_selesai):
    """
    Hitung durasi menit (detik diabaikan)
    """
    mulai = (jam_mulai.hour * 3600 + jam_mulai.minute * 60 + jam_mulai.second)
    selesai = (jam_selesai.hour * 3600 + jam_selesai.minute * 60 + jam_selesai.second)

    if selesai <= mulai:
        return 0

    return (selesai - mulai) // 60


def hitung_terlambat_istirahat(
    jam_selesai_istirahat,
    batas_selesai: time = time(14, 0)
) -> int:
    """
    Hitung keterlambatan selesai istirahat (menit)
    - Jika <= 14:00 → 0
    - Jika > 14:00 → selisih menit (floor)
    - Detik diabaikan
    """
    if not jam_selesai_istirahat:
        return 0

    selesai_detik = (jam_selesai_istirahat.hour * 3600 + jam_selesai_istirahat.minute * 60 + jam_selesai_istirahat.second)
    batas_detik = (batas_selesai.hour * 3600 + batas_selesai.minute * 60)

    if selesai_detik <= batas_detik:
        return 0

    return (selesai_detik - batas_detik) // 60


def hitung_total_menit_kerja(jam_masuk, jam_keluar, total_menit_istirahat: int):
    masuk = (jam_masuk.hour * 3600 + jam_masuk.minute * 60 + jam_masuk.second)
    keluar = (jam_keluar.hour * 3600 + jam_keluar.minute * 60 + jam_keluar.second)

    if keluar <= masuk:
        return 0

    total_menit = (keluar - masuk) // 60
    return max(total_menit - (total_menit_istirahat or 0), 0)
