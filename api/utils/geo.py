from math import radians, sin, cos, sqrt, atan2


def calculate_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return 6371000 * c  # meter


def find_valid_lokasi(latitude, longitude, lokasi_list):
    """
    Cari lokasi absensi yang valid berdasarkan radius
    (HANYA lokasi dengan koordinat)
    """
    for lokasi in lokasi_list:

        if lokasi["latitude"] is None or lokasi["longitude"] is None:
            continue

        jarak = calculate_distance(
            latitude,
            longitude,
            lokasi["latitude"],
            lokasi["longitude"]
        )

        if jarak <= lokasi.get("radius_meter", 50):
            return {
                "id_lokasi": lokasi["id_lokasi"],
                "nama_lokasi": lokasi["nama_lokasi"],
                "jarak": round(jarak, 2)
            }

    return None


