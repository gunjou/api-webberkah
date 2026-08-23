from math import radians, sin, cos, sqrt, atan2


def calculate_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(
        radians,
        [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return 6371000 * c


def find_valid_lokasi(
    latitude,
    longitude,
    lokasi_list,
    allowed_lokasi_ids=None
):
    """
    Cari lokasi absensi TERDEKAT.

    Algoritma:
    1. Hitung jarak user ke semua lokasi.
    2. Abaikan lokasi tanpa koordinat.
    3. Jika allowed_lokasi_ids diberikan,
       hanya hitung lokasi yang boleh diakses pegawai.
    4. Pilih lokasi dengan jarak paling dekat.
    5. Setelah lokasi terdekat ditemukan, cek radius.

    Return jika valid:
    {
        "valid": True,
        "id_lokasi": 2,
        "nama_lokasi": "Gudang GM",
        "jarak": 12.5,
        "radius_meter": 26,
        "jarak_di_luar_radius": 0
    }

    Return jika di luar radius:
    {
        "valid": False,
        "terdekat": {
            ...
        }
    }

    Return None jika tidak ada lokasi yang bisa dihitung.
    """

    lokasi_terdekat = None
    jarak_terdekat = float("inf")

    for lokasi in lokasi_list:

        # Skip lokasi tanpa koordinat
        # Contoh: WFH
        if (
            lokasi["latitude"] is None
            or lokasi["longitude"] is None
        ):
            continue

        # Jika diberikan lokasi yang boleh diakses pegawai,
        # abaikan lokasi lain
        if (
            allowed_lokasi_ids is not None
            and lokasi["id_lokasi"] not in allowed_lokasi_ids
        ):
            continue

        jarak = calculate_distance(
            latitude,
            longitude,
            lokasi["latitude"],
            lokasi["longitude"]
        )

        # Pastikan radius selalu memiliki nilai
        radius_meter = lokasi.get("radius_meter") or 50

        # HANYA simpan jika ini lebih dekat
        if jarak < jarak_terdekat:

            jarak_terdekat = jarak

            lokasi_terdekat = {
                "id_lokasi": lokasi["id_lokasi"],
                "nama_lokasi": lokasi["nama_lokasi"],
                "jarak": round(jarak, 2),
                "radius_meter": radius_meter,
                "jarak_di_luar_radius": round(
                    max(0, jarak - radius_meter),
                    2
                )
            }

    # Tidak ada lokasi yang dapat dihitung
    if lokasi_terdekat is None:
        return None

    # =====================================================
    # SETELAH SEMUA LOKASI DIPERIKSA,
    # BARU TENTUKAN VALID / TIDAK
    # =====================================================

    if (
        lokasi_terdekat["jarak"]
        <= lokasi_terdekat["radius_meter"]
    ):
        return {
            "valid": True,
            **lokasi_terdekat
        }

    return {
        "valid": False,
        "terdekat": lokasi_terdekat
    }