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

    return 6371000 * c  # meter


def find_valid_lokasi(
    latitude,
    longitude,
    lokasi_list,
    allowed_lokasi_ids=None
):
    """
    Cari lokasi absensi berdasarkan radius.

    allowed_lokasi_ids:
        Set ID lokasi yang boleh digunakan pegawai.

    Return:
        Lokasi valid:
        {
            "id_lokasi": ...,
            "nama_lokasi": ...,
            "jarak": ...,
            "radius_meter": ...,
            "jarak_di_luar_radius": 0
        }

        Tidak valid:
        {
            "terdekat": {...}
        }

        Tidak ada lokasi:
            None
    """

    lokasi_terdekat = None
    jarak_terdekat = None

    for lokasi in lokasi_list:

        # Skip lokasi tanpa koordinat
        if (
            lokasi["latitude"] is None
            or lokasi["longitude"] is None
        ):
            continue

        # Jika diberikan daftar lokasi yang diperbolehkan,
        # hanya evaluasi lokasi tersebut
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

        radius_meter = lokasi.get("radius_meter") or 50

        jarak_di_luar_radius = max(
            0,
            jarak - radius_meter
        )

        lokasi_data = {
            "id_lokasi": lokasi["id_lokasi"],
            "nama_lokasi": lokasi["nama_lokasi"],
            "jarak": round(jarak, 2),
            "radius_meter": radius_meter,
            "jarak_di_luar_radius": round(
                jarak_di_luar_radius,
                2
            )
        }

        # Simpan lokasi terdekat
        if (
            jarak_terdekat is None
            or jarak < jarak_terdekat
        ):
            jarak_terdekat = jarak
            lokasi_terdekat = lokasi_data

        # Sudah masuk radius
        if jarak <= radius_meter:
            return lokasi_data

    if lokasi_terdekat:
        return {
            "terdekat": lokasi_terdekat
        }

    return None