from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita


def get_hutang_summary_base(status_hutang: str):
    """
    Ambil data hutang per pegawai (TANPA transaksi)
    """
    sql = text("""
        SELECT
            h.id_hutang,
            h.id_pegawai,
            p.nama_lengkap,
            p.nip,
            h.jumlah_awal,
            h.sisa_hutang,
            h.updated_at
        FROM hutang h
        JOIN pegawai p
            ON p.id_pegawai = h.id_pegawai
        WHERE h.status = 1
          AND h.status_hutang = :status_hutang
        ORDER BY p.nama_lengkap ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "status_hutang": status_hutang
        }).mappings().all()

def get_total_pembayaran_by_hutang(id_hutang_list: list[int]):
    """
    Ambil total pembayaran per id_hutang
    """
    if not id_hutang_list:
        return {}

    sql = text("""
        SELECT
            id_hutang,
            SUM(jumlah) AS total_bayar
        FROM hutang_transaksi
        WHERE status = 1
          AND jenis_transaksi = 'pembayaran'
          AND id_hutang = ANY(:id_hutang_list)
        GROUP BY id_hutang
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {"id_hutang_list": id_hutang_list}
        ).mappings().all()

    return {r["id_hutang"]: r["total_bayar"] for r in rows}



def get_hutang_by_pegawai(id_pegawai: int, status_hutang: str):
    sql = text("""
        SELECT
            h.id_hutang, p.nama_lengkap, h.tanggal_pengajuan, h.jumlah_awal, h.sisa_hutang, h.status_hutang, h.keterangan
        FROM hutang h
        INNER JOIN pegawai p ON p.id_pegawai = h.id_pegawai
        WHERE h.status = 1
            AND p.status = 1
            AND h.id_pegawai = :id_pegawai
            AND h.status_hutang = :status_hutang
        ORDER BY h.tanggal_pengajuan ASC
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "status_hutang": status_hutang
            }
        ).mappings().all()

def get_transaksi_by_hutang_ids(hutang_ids: list[int], jenis_transaksi: str | None = None):
    if not hutang_ids:
        return []

    sql = """
        SELECT
            id_transaksi, id_hutang, jenis_transaksi, jumlah, saldo_sebelum, saldo_setelah, tanggal, metode, keterangan
        FROM hutang_transaksi
        WHERE status = 1
          AND id_hutang = ANY(:hutang_ids)
    """

    params = {"hutang_ids": hutang_ids}

    if jenis_transaksi:
        sql += " AND jenis_transaksi = :jenis_transaksi"
        params["jenis_transaksi"] = jenis_transaksi

    sql += " ORDER BY tanggal ASC, id_transaksi ASC"

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()



def insert_hutang(id_pegawai: int, tanggal_pengajuan, jumlah_awal: float, keterangan: str) -> int:
    sql = text("""
        INSERT INTO hutang (
            id_pegawai, tanggal_pengajuan, jumlah_awal, sisa_hutang, status_hutang, keterangan, status, created_at, updated_at
        ) VALUES (
            :id_pegawai, :tanggal_pengajuan, :jumlah_awal, :jumlah_awal, 'aktif', :keterangan, 1, :now, :now
        )
        RETURNING id_hutang
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "tanggal_pengajuan": tanggal_pengajuan,
                "jumlah_awal": jumlah_awal,
                "keterangan": keterangan,
                "now": get_wita()
            }
        ).scalar()

def insert_hutang_penambahan(id_hutang: int, jumlah: float, tanggal, metode: str, keterangan: str):
    sql = text("""
        INSERT INTO hutang_transaksi (
            id_hutang, jenis_transaksi, jumlah, saldo_sebelum, saldo_setelah, tanggal, metode, sumber_transaksi, keterangan, status, created_at
        ) VALUES (
            :id_hutang, 'penambahan', :jumlah, 0, :jumlah, :tanggal, :metode, 'manual', :keterangan, 1, :now
        )
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_hutang": id_hutang,
                "jumlah": jumlah,
                "tanggal": tanggal,
                "metode": metode,
                "keterangan": keterangan,
                "now": get_wita()
            }
        )



def get_hutang_aktif_pegawai(id_pegawai: int):
    """
    Ambil hutang aktif pegawai (FIFO)
    """
    sql = text("""
        SELECT
            id_hutang,
            sisa_hutang
        FROM hutang
        WHERE id_pegawai = :id_pegawai
          AND status = 1
          AND status_hutang = 'aktif'
          AND sisa_hutang > 0
        ORDER BY tanggal_pengajuan ASC, id_hutang ASC
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_pegawai": id_pegawai}
        ).mappings().all()


def insert_hutang_pembayaran(
    id_hutang: int,
    jumlah: float,
    saldo_sebelum: float,
    saldo_setelah: float,
    tanggal,
    metode: str,
    keterangan: str
):
    sql = text("""
        INSERT INTO hutang_transaksi (
            id_hutang, jenis_transaksi, jumlah, saldo_sebelum, saldo_setelah, tanggal, metode, sumber_transaksi, 
            keterangan, status, created_at
        ) VALUES (
            :id_hutang, 'pembayaran', :jumlah, :saldo_sebelum, :saldo_setelah, :tanggal, :metode, 'manual', 
            :keterangan, 1, :now
        )
    """)
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_hutang": id_hutang,
                "jumlah": jumlah,
                "saldo_sebelum": saldo_sebelum,
                "saldo_setelah": saldo_setelah,
                "tanggal": tanggal,
                "metode": metode,
                "keterangan": keterangan,
                "now": get_wita()
            }
        )

def update_hutang_sisa(id_hutang: int, sisa_hutang: float):
    status_hutang = "lunas" if sisa_hutang == 0 else "aktif"

    sql = text("""
        UPDATE hutang
        SET
            sisa_hutang = :sisa_hutang,
            status_hutang = :status_hutang,
            updated_at = :now
        WHERE id_hutang = :id_hutang
    """)
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_hutang": id_hutang,
                "sisa_hutang": sisa_hutang,
                "status_hutang": status_hutang,
                "now": get_wita()
            }
        )
