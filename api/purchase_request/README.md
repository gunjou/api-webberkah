# Purchase Requests API

Prefix: `/purchase-requests` — Kode: `api/purchase_request/` (`endpoint.py`, `service.py`, `query.py`, `pdf.py`)

## Daftar Endpoint

| Method | Path                              | Akses                          | Fungsi                             |
| ------ | --------------------------------- | ------------------------------ | ---------------------------------- |
| POST   | `/purchase-requests/attachments`  | Admin, Pegawai                 | Upload dan satukan lampiran        |
| POST   | `/purchase-requests`              | Token apa pun\*                | Buat pengajuan untuk diri sendiri  |
| GET    | `/purchase-requests`              | Admin, Pegawai                 | List pengajuan (tanpa pagination)  |
| POST   | `/purchase-requests/admin`        | Admin                          | Buat pengajuan atas nama pegawai   |
| GET    | `/purchase-requests/history`      | Admin, Pegawai                 | Riwayat PAID/REJECTED (pagination) |
| GET    | `/purchase-requests/my-summary`   | Pegawai\*                      | Ringkasan dashboard pegawai        |
| GET    | `/purchase-requests/{id}`         | Admin, Pegawai (milik sendiri) | Detail pengajuan                   |
| PUT    | `/purchase-requests/{id}`         | Admin, Pegawai (milik sendiri) | Ubah pengajuan                     |
| DELETE | `/purchase-requests/{id}`         | Admin, Pegawai (milik sendiri) | Soft delete                        |
| POST   | `/purchase-requests/{id}/review`  | Admin                          | REQUESTED → REVIEWED               |
| POST   | `/purchase-requests/{id}/approve` | Admin                          | REVIEWED → APPROVED                |
| POST   | `/purchase-requests/{id}/reject`  | Admin                          | REQUESTED/REVIEWED → REJECTED      |
| POST   | `/purchase-requests/{id}/paid`    | Admin                          | APPROVED → PAID                    |
| GET    | `/purchase-requests/{id}/history` | Admin, Pegawai (milik sendiri) | Timeline status                    |
| GET    | `/purchase-requests/{id}/pdf`     | Admin, Pegawai (milik sendiri) | Unduh PDF                          |

\* Role tidak dicek; `id_pegawai` diambil dari identity token. Lihat [Catatan Perilaku](#catatan-perilaku) no. 4.

## Aturan Umum

Semua endpoint memerlukan header `Authorization: Bearer <access_token>`. Body dikirim sebagai `Content-Type: application/json`.

### Alur status

```
REQUESTED ──review──> REVIEWED ──approve──> APPROVED ──paid──> PAID
    │                    │
    └──────reject────────┴──> REJECTED ──PUT (edit)──> REQUESTED
```

Priority: `NORMAL`, `URGENT`, `TOP_URGENT`.

### Format respons sukses

Semua endpoint selain PDF memakai format ini, dengan HTTP 200 (termasuk saat create).

```json
{
  "code": 200,
  "success": true,
  "message": "...",
  "data": null,
  "meta": { "execution_time_ms": 12.34 }
}
```

Tipe nilai: angka desimal (`total_amount`, `harga_satuan`, `jumlah`, `total`) menjadi number, tanggal menjadi `YYYY-MM-DD`, dan datetime menjadi ISO 8601.

### Format respons error

| HTTP | `error_code` / `code` | Penyebab                                                 | Bentuk |
| ---- | --------------------- | -------------------------------------------------------- | ------ |
| 401  | `JWT_ERROR`           | Token tidak ada atau tidak valid                         | A      |
| 401  | `TOKEN_EXPIRED`       | Token kedaluwarsa, pesan `Token expired`                 | A      |
| 422  | `VALIDATION_ERROR`    | Validasi gagal, termasuk bukan admin pada endpoint admin | B      |
| 404  | `NOT_FOUND`           | Data tidak ada, atau bukan milik pegawai tersebut        | B      |
| 400  | -                     | Query param `GET /purchase-requests` tidak valid         | C      |
| 500  | -                     | Error tak tertangani                                     | D      |

```jsonc
// A: error JWT
{ "success": false, "message": "Token expired", "code": "TOKEN_EXPIRED", "errors": null }

// B: error aplikasi (code berisi HTTP status, error_code berisi jenis error)
{ "success": false, "message": "Priority tidak valid.", "code": 422, "error_code": "VALIDATION_ERROR", "errors": null }

// C: validasi query param oleh flask-restx
{ "errors": { "status": "..." }, "message": "Input payload validation failed" }

// D: error tak tertangani
{ "message": "Internal Server Error" }
```

### Pesan validasi item

Berlaku untuk create, admin create, dan update (`N` = urutan item, mulai dari 1). Semuanya 422.

- `Keterangan item ke-N wajib diisi.`
- `Unit item ke-N wajib diisi.`
- `Harga satuan item ke-N wajib diisi.`
- `Jumlah item ke-N wajib diisi.`
- `Harga satuan item ke-N tidak boleh negatif.`
- `Jumlah item ke-N harus lebih besar dari 0.`

---

## Upload Lampiran

### POST `/purchase-requests/attachments`

Menerima satu atau beberapa file, menyatukannya menjadi satu file, lalu menguploadnya ke CDN. Endpoint ini belum menyimpan apa pun ke database. Kirim `attachment_name` dan `attachment_path` dari responsnya ke `POST /purchase-requests`, `POST /purchase-requests/admin`, atau `PUT /purchase-requests/{id}`.

Body berupa `multipart/form-data`. Ulangi field `files` untuk setiap file; urutan pengiriman menentukan urutan hasil.

```bash
curl -X POST "$BASE_URL/purchase-requests/attachments" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@nota.pdf" \
  -F "files=@foto-barang.jpg"
```

| File yang dikirim | Hasil                                                        |
| ----------------- | ------------------------------------------------------------ |
| 1 PDF             | File yang sama                                               |
| 1 gambar          | 1 PDF berformat lampiran                                     |
| Beberapa gambar   | 1 PDF berformat lampiran, maksimal 4 gambar per halaman      |
| Beberapa PDF      | 1 PDF gabungan                                               |
| PDF dan gambar    | 1 PDF; urutan mengikuti upload, gambar berformat lampiran    |

Format lampiran berisi header perusahaan, judul LAMPIRAN, gambar yang ukurannya dibatasi, dan footer.

Hasil selalu PDF karena CDN dokumen menolak file gambar. Format yang diterima: PDF, JPG, PNG, WEBP. Maksimal 10 file dan 10 MB per file.

Respons `data`:

```json
{
  "attachment_name": "lampiran.pdf",
  "attachment_path": "https://cdn.example.com/lampiran.pdf",
  "mime_type": "application/pdf",
  "source_file_count": 2
}
```

Untuk mengganti lampiran pengajuan, upload ulang seluruh file yang diinginkan, karena file baru tidak ditambahkan ke hasil gabungan sebelumnya.

Error `422`: tidak ada file, lebih dari 10 file, file kosong atau terlalu besar, format tidak didukung, PDF rusak atau terkunci password, resolusi gambar lebih dari 50 MP, atau upload CDN gagal.

---

## Membuat Pengajuan

### POST `/purchase-requests`

Body:

```json
{
  "tanggal_request": "2026-11-05",
  "id_departemen": 1,
  "nama_pekerjaan": "Pembelian ATK",
  "priority": "NORMAL",
  "note": "Kebutuhan kantor",
  "items": [
    {
      "keterangan": "Kertas A4",
      "unit": "rim",
      "harga_satuan": 50000,
      "jumlah": 2
    }
  ],
  "payment_description": "Transfer vendor",
  "payment_bank": "BCA",
  "payment_account_number": "1234567890",
  "payment_account_name": "Toko ATK",
  "attachment_name": "nota.pdf",
  "attachment_path": "https://cdn.example.com/nota.pdf"
}
```

| Field                             | Wajib | Keterangan                                             |
| --------------------------------- | ----- | ------------------------------------------------------ |
| `id_departemen`, `nama_pekerjaan` | Ya    | Jika tidak dikirim, respons 500 (bukan 422)            |
| `priority`                        | Ya    | Default `NORMAL` di Swagger tidak diterapkan di server |
| `items`                           | Ya    | Minimal 1 item                                         |
| Lainnya                           | Tidak | Disimpan `NULL` jika kosong                            |

Sukses — `message`: `Purchase request berhasil dibuat.`

```json
{
  "id_request": 10,
  "request_number": "AR-2026-11-0001",
  "status": "REQUESTED",
  "total_amount": 100000.0
}
```

Error:

| HTTP | Pesan                                          |
| ---- | ---------------------------------------------- |
| 422  | `Minimal harus terdapat 1 item pengajuan.`     |
| 422  | `Priority tidak valid.`                        |
| 422  | Pesan validasi item                            |
| 404  | `Pegawai tidak ditemukan atau tidak aktif.`    |
| 404  | `Departemen tidak ditemukan atau tidak aktif.` |

### POST `/purchase-requests/admin`

Body sama dengan di atas, ditambah `id_pegawai` (wajib) sebagai pegawai pengaju. Datanya sama dengan `POST /purchase-requests`, dengan `message`: `Purchase request berhasil dibuat oleh admin.`

Error tambahan selain error create di atas:

| HTTP | Pesan                                            |
| ---- | ------------------------------------------------ |
| 422  | `Endpoint ini hanya dapat digunakan oleh admin.` |
| 422  | `Data pengajuan wajib diisi.`                    |
| 422  | `Pegawai pengaju wajib dipilih.`                 |

---

## Membaca Data

### GET `/purchase-requests`

Pegawai hanya melihat pengajuan miliknya, admin melihat semua. Diurutkan dari `tanggal_request` lalu `created_at` terbaru.

| Query                              | Default  | Keterangan                                                                                          |
| ---------------------------------- | -------- | --------------------------------------------------------------------------------------------------- |
| `status`                           | `ACTIVE` | `ACTIVE` (REQUESTED + REVIEWED + APPROVED), `REQUESTED`, `REVIEWED`, `APPROVED`, `REJECTED`, `PAID` |
| `id_departemen`                    | -        | Integer                                                                                             |
| `search`                           | -        | Nama pemohon, nama pekerjaan, priority, keterangan item                                             |
| `tanggal_mulai`, `tanggal_selesai` | -        | `YYYY-MM-DD`, memfilter `tanggal_request`                                                           |

Sukses — `message`: `List purchase request`. `data` berupa array, atau `[]` jika kosong:

```json
[
  {
    "id_request": 10,
    "request_number": "AR-2026-11-0001",
    "tanggal_request": "2026-11-05",
    "nama_pekerjaan": "Pembelian ATK",
    "priority": "NORMAL",
    "status": "REQUESTED",
    "note": "Kebutuhan kantor",
    "total_amount": 100000.0,
    "id_pegawai": 5,
    "nama_pegawai": "Nama Lengkap",
    "nama_panggilan": "Nama",
    "id_departemen": 1,
    "nama_departemen": "Umum",
    "payment_description": "Transfer vendor",
    "payment_bank": "BCA",
    "payment_account_number": "1234567890",
    "payment_account_name": "Toko ATK",
    "attachment_name": "nota.pdf",
    "attachment_path": "https://cdn.example.com/nota.pdf",
    "items": [
      {
        "id_item": 1,
        "item_no": 1,
        "keterangan": "Kertas A4",
        "unit": "rim",
        "harga_satuan": 50000.0,
        "jumlah": 2.0,
        "total": 100000.0
      }
    ],
    "created_at": "2026-11-05T10:00:00",
    "updated_at": "2026-11-05T10:00:00"
  }
]
```

Error:

| HTTP | Pesan                                                                                            |
| ---- | ------------------------------------------------------------------------------------------------ |
| 400  | `Input payload validation failed` (`status` di luar pilihan, atau `id_departemen` bukan integer) |
| 422  | `Account type tidak valid.`                                                                      |
| 422  | `Tanggal mulai tidak boleh lebih besar dari tanggal selesai.`                                    |

### GET `/purchase-requests/history`

| Query                                                         | Default | Keterangan             |
| ------------------------------------------------------------- | ------- | ---------------------- |
| `status`                                                      | `PAID`  | `PAID` atau `REJECTED` |
| `page`                                                        | `1`     | Minimal 1              |
| `per_page`                                                    | `10`    | 1 sampai 100           |
| `id_departemen`, `search`, `tanggal_mulai`, `tanggal_selesai` | -       | Sama dengan list       |

Sukses — `message`: `History purchase request berhasil diambil.` Field tiap baris sama dengan list, tetapi **tanpa `items`**.

```json
{
  "data": [
    { "id_request": 10, "request_number": "AR-2026-11-0001", "status": "PAID" }
  ],
  "page_info": { "page": 1, "per_page": 10, "total": 25, "total_pages": 3 }
}
```

Error (semua 422):

- `Status history purchase request tidak valid.`
- `Account type tidak valid.`
- `Page minimal adalah 1.`
- `Per page harus antara 1 sampai 100.`
- `Tanggal mulai tidak boleh lebih besar dari tanggal selesai.`

`page`, `per_page`, atau `id_departemen` yang bukan angka menghasilkan 500.

### GET `/purchase-requests/my-summary`

Tanpa parameter. Sukses — `message`: `Dashboard purchase request berhasil diambil.`

```json
{
  "summary": {
    "total": 12,
    "active": 8,
    "requested": 3,
    "reviewed": 2,
    "approved": 1,
    "rejected": 2,
    "paid": 4
  },
  "requests": [
    {
      "id_request": 10,
      "request_number": "AR-2026-11-0001",
      "nama_pekerjaan": "Pembelian ATK",
      "tanggal_request": "2026-11-05",
      "total_amount": 100000.0,
      "status": "REQUESTED",
      "priority": "NORMAL",
      "history": [
        {
          "status": "REQUESTED",
          "nama_pegawai": "Nama Lengkap",
          "tanggal": "2026-11-05T10:00:00"
        }
      ]
    }
  ]
}
```

- `summary.paid` hanya menghitung pengajuan yang dibayar pada bulan berjalan.
- `summary.active` adalah semua status selain PAID, jadi REJECTED ikut terhitung.
- `requests` tidak memuat pengajuan PAID dan REJECTED.

### GET `/purchase-requests/{id}`

Sukses — `message`: `Detail purchase request`

```json
{
  "id_request": 10,
  "request_number": "AR-2026-11-0001",
  "tanggal_request": "2026-11-05",
  "nama_pekerjaan": "Pembelian ATK",
  "priority": "NORMAL",
  "status": "PAID",
  "note": "Kebutuhan kantor",
  "total_amount": 100000.0,
  "pegawai": {
    "id_pegawai": 5,
    "nama_lengkap": "Nama Lengkap",
    "nama_panggilan": "Nama"
  },
  "departemen": { "id_departemen": 1, "nama_departemen": "Umum" },
  "payment": {
    "description": "Transfer vendor",
    "bank": "BCA",
    "account_number": "1234567890",
    "account_name": "Toko ATK",
    "bukti_bayar": "https://cdn.example.com/bukti.jpg"
  },
  "attachment": {
    "name": "nota.pdf",
    "path": "https://cdn.example.com/nota.pdf"
  },
  "items": [
    {
      "id_item": 1,
      "item_no": 1,
      "keterangan": "Kertas A4",
      "unit": "rim",
      "harga_satuan": 50000.0,
      "jumlah": 2.0,
      "total": 100000.0
    }
  ],
  "history": [
    {
      "id_history": 1,
      "status": "REQUESTED",
      "nama_pegawai": "Nama Lengkap",
      "note": "Kebutuhan kantor",
      "created_at": "2026-11-05T10:00:00"
    }
  ],
  "created_at": "2026-11-05T10:00:00",
  "updated_at": "2026-11-05T10:00:00"
}
```

`attachment` dan `payment.bukti_bayar` bernilai `null` jika tidak ada.

Error: 404 `Purchase request tidak ditemukan.`

### GET `/purchase-requests/{id}/history`

Sukses — `message`: `History pengajuan berhasil diambil.` Diurutkan dari yang terlama.

```json
[
  {
    "id_history": 1,
    "id_request": 10,
    "status": "REQUESTED",
    "nama_pegawai": "Nama Lengkap",
    "note": "Kebutuhan kantor",
    "created_at": "2026-11-05T10:00:00"
  }
]
```

Error:

| HTTP | Pesan                                         |
| ---- | --------------------------------------------- |
| 404  | `Pengajuan tidak ditemukan.`                  |
| 422  | `Anda tidak memiliki akses ke pengajuan ini.` |

### GET `/purchase-requests/{id}/pdf`

Sukses mengembalikan file biner `application/pdf`, bukan JSON, dengan nama `Pengajuan {nama_pegawai} - {nama_pekerjaan} - {tanggal_request}.pdf`.

Urutan halaman: dokumen utama, lampiran pengajuan (jika ada), lalu bukti transaksi (jika ada). Lampiran gambar dijadikan halaman A4.

Error:

| HTTP | Penyebab                                                       |
| ---- | -------------------------------------------------------------- |
| 404  | `Purchase request tidak ditemukan.`                            |
| 500  | Lampiran gagal diunduh dari CDN, atau formatnya tidak didukung |

---

## Mengubah Data

### PUT `/purchase-requests/{id}`

Partial update: hanya field yang dikirim yang diubah. Field yang tersedia sama dengan create.

```json
{
  "nama_pekerjaan": "Pembelian ATK Revisi",
  "items": [
    {
      "item_no": 1,
      "keterangan": "Kertas A4",
      "unit": "rim",
      "harga_satuan": 55000,
      "jumlah": 3
    }
  ]
}
```

Jika `items` dikirim, semua item lama dihapus dan diganti. `item_no` diberi nomor ulang sesuai urutan array, `id_item` berubah, dan `total_amount` dihitung ulang.

Sukses — `message`: `Pengajuan berhasil diperbarui.`, `data`: `null`

Error:

| HTTP | Pesan                                            |
| ---- | ------------------------------------------------ |
| 422  | `Data pengajuan wajib diisi.`                    |
| 422  | `Account type tidak valid.`                      |
| 404  | `Pengajuan tidak ditemukan.`                     |
| 422  | `Departemen tidak ditemukan atau tidak aktif.`   |
| 422  | `Priority tidak valid.`                          |
| 422  | `Items pengajuan wajib diisi minimal satu item.` |
| 422  | Pesan validasi item                              |

### DELETE `/purchase-requests/{id}`

Soft delete (`is_active = 0`). Pengajuan PAID tidak bisa dihapus.

Sukses — `message`: `Pengajuan berhasil dihapus.`, `data`: `null`

Error:

| HTTP | Pesan                                            |
| ---- | ------------------------------------------------ |
| 404  | `Pengajuan tidak ditemukan.`                     |
| 422  | `Pengajuan yang sudah PAID tidak dapat dihapus.` |

---

## Perubahan Status (Admin)

Keempat endpoint ini mengembalikan `data: null`, dan setiap perubahan dicatat ke history bersama tanda tangan admin.

| Endpoint             | Body                          | Status asal         | Pesan sukses                                |
| -------------------- | ----------------------------- | ------------------- | ------------------------------------------- |
| POST `/{id}/review`  | `{ "note": "..." }` opsional  | REQUESTED           | `Pengajuan berhasil direview.`              |
| POST `/{id}/approve` | `{ "note": "..." }` opsional  | REVIEWED            | `Pengajuan berhasil disetujui.`             |
| POST `/{id}/reject`  | `{ "note": "..." }` **wajib** | REQUESTED, REVIEWED | `Pengajuan berhasil ditolak.`               |
| POST `/{id}/paid`    | `{ "note": "..." }` opsional  | APPROVED            | `Pengajuan berhasil ditandai sebagai paid.` |

Error bersama:

| HTTP | Pesan                              |
| ---- | ---------------------------------- |
| 422  | `Identitas admin tidak ditemukan.` |
| 404  | `Pengajuan tidak ditemukan.`       |

Error per endpoint (semua 422, `{status}` = status saat ini):

| Endpoint | Bukan admin                                               | Status tidak sesuai                                                   |
| -------- | --------------------------------------------------------- | --------------------------------------------------------------------- |
| review   | `Hanya admin yang dapat melakukan review.`                | `Pengajuan dengan status {status} tidak dapat direview.`              |
| approve  | `Hanya admin yang dapat melakukan approval.`              | `Pengajuan dengan status {status} tidak dapat diapprove.`             |
| reject   | `Hanya admin yang dapat melakukan reject.`                | `Pengajuan dengan status {status} tidak dapat direject.`              |
| paid     | `Hanya admin yang dapat menandai pengajuan sebagai paid.` | `Pengajuan dengan status {status} tidak dapat ditandai sebagai paid.` |

Reject juga bisa mengembalikan 422 `Alasan reject wajib diisi.`

---

## Catatan Perilaku

Perilaku kode saat ini yang perlu diperhatikan frontend:

1. **Edit pengajuan REJECTED selalu gagal dengan 500.** `update_purchase_request_service` (`service.py:494`) memanggil `create_purchase_request_history` tanpa `signature_path`, padahal argumen itu wajib (`query.py:897`). Transaksi di-rollback, sehingga alur REJECTED → REQUESTED pada diagram belum bisa berjalan.
2. **Bukan admin mendapat 422, bukan 403**, pada endpoint khusus admin.
3. **Akses ke pengajuan milik orang lain berbeda-beda:** kebanyakan endpoint mengembalikan 404, sedangkan `/{id}/history` mengembalikan 422.
4. **`POST /purchase-requests` dan `/my-summary` tidak mengecek role.** Jika dipanggil dengan token admin, `id_admin` dipakai sebagai `id_pegawai`, sehingga bisa terbaca sebagai data pegawai lain yang ber-ID sama.
5. **PUT tidak membatasi status.** Pegawai pemilik dan admin bisa mengubah pengajuan berstatus apa pun, termasuk APPROVED dan PAID.
6. **`payment.bukti_bayar` di detail hanya berisi satu URL,** walaupun satu pengajuan bisa punya beberapa transaksi. PDF melampirkan semua bukti transaksi.
7. **Format tanggal tidak divalidasi.** `tanggal_mulai` dan `tanggal_selesai` yang bukan tanggal akan ditolak database dan menghasilkan 500.
8. **Selalu kirim `tanggal_request` saat create.** Field ini opsional di Swagger, tetapi server tidak mengisi default, sehingga nilainya `NULL` atau ditentukan oleh skema database.
9. **Admin yang tidak aktif mendapat 500** pada review, approve, reject, dan paid, karena tanda tangannya tidak ditemukan.
