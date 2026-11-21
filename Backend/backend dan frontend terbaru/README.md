# DapurKu — Frontend Tkinter + Backend FastAPI + MySQL

## Susunan file
- `main.py` — backend FastAPI
- `db.py` — koneksi ke MySQL/MariaDB
- `main_frontend.py` — aplikasi desktop Tkinter sekaligus halaman login
- `gui_database2.py` — launcher alternatif untuk membuka halaman login
- `requirements.txt` — library
- `.env.example` — contoh pengaturan koneksi

## 1. Pastikan database sudah tersedia
Jalankan XAMPP Control Panel dan aktifkan **MySQL**. Buka phpMyAdmin, pastikan database `db_dapur` berisi tabel:
`recipes`, `ingredients`, `recipe_ingredients`, `recipe_favorites`, `users`.

**Jangan import ulang `db_dapur.sql` bila database sudah berisi data**, karena dump ini berisi perintah `DROP TABLE` dan dapat menghapus tabel/data yang ada.

## 2. Siapkan Python
Buka terminal pada folder proyek:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` menjadi `.env`, lalu sesuaikan password MySQL:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=db_dapur
API_BASE=http://127.0.0.1:8000
```

## 3. Jalankan backend
Terminal pertama:
```bash
uvicorn main:app --reload
```
Cek API:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

Health harus mengembalikan status connected. Kalau gagal, periksa MySQL aktif dan pengaturan `.env`.

## 4. Jalankan frontend
Terminal kedua, dari folder proyek yang sama:
```bash
python main_frontend.py
# atau gunakan launcher login:
python gui_database2.py
```
Frontend kini tidak membuka koneksi SQL sendiri. Operasi baca, tambah, edit, hapus resep dan favorit akan dikirim melalui API backend.

## Catatan
- Folder `assets/icons` dan folder `foto` dari proyek frontend lama perlu diletakkan di sebelah `main_frontend.py` agar ikon/foto lokal tampil.
- API ini dirancang untuk aplikasi desktop lokal. Endpoint CRUD belum memakai autentikasi pengguna.
- Foto disimpan sebagai nama/path lokal di kolom `recipes.foto`; file foto tetap berada di folder `foto` frontend.


## Login dan role akun

Aplikasi menampilkan login sebelum halaman resep. Login menggunakan tabel `users` di database `db_dapur` (`id_users`, `username`, `password_hash`, `role`). Role yang tersedia mengikuti enum pada database: `Chef`, `Ibu Rumah Tangga`, `Anak Kos`, `pembaca`, dan `pemula`.

- **Chef**: tambah, edit, dan hapus resep; sidebar menampilkan kategori Chef.
- **Ibu Rumah Tangga / Anak Kos**: tambah resep dan melihat resep; tidak bisa edit atau hapus resep. Sidebar menampilkan kategori masing-masing.
- **pembaca / pemula**: melihat resep dan mengelola favorit saja. Sidebar menampilkan kategori pembaca/pemula.

Menu sidebar tidak menggunakan ikon menu. Role akun ditampilkan sebagai label. Jika tabel `users` masih kosong, buat akun terlebih dahulu di phpMyAdmin. Password yang tersimpan dapat berupa hash SHA-256 (sesuai contoh script login lama) atau bcrypt.

Tambahkan `JWT_SECRET` pada `.env` dengan string acak panjang untuk keamanan token login.


### Login dan pendaftaran akun
- Halaman login sekarang memiliki label untuk Username dan Password, serta tombol menuju form Daftar.
- Form pendaftaran meminta Username, Password (minimal 6 karakter), dan Kategori/Role.
- Pilihan kategori diambil langsung dari definisi kolom `users.role` di MySQL melalui endpoint `/auth/roles`, sehingga dropdown mengikuti ENUM pada database.
- Pendaftaran menyimpan akun ke tabel `users`; setelah berhasil, pengguna kembali ke halaman login.
- Endpoint baru: `GET /auth/roles` dan `POST /auth/register`.
