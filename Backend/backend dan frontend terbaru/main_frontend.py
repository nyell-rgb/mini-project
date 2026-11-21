"""Resep DapurKu - aplikasi resep makanan sederhana (Tkinter).

Judul jendela, tombol minimize, maximize, dan close memakai bar bawaan Windows.
Ikon dibaca dari folder assets/icons (format PNG, ukuran sekitar 24x24 piksel).
Data resep disimpan di database MySQL db_dapur (lihat bagian DATABASE di bawah).
"""

import os
import re
import shutil
import sys
import time
import tkinter as tk
import uuid
from tkinter import filedialog
from tkinter import font as tkfont
from tkinter import messagebox
from tkinter import ttk


from dotenv import load_dotenv
load_dotenv()

# Pillow dipakai untuk membaca JPG dan memotong/mengecilkan foto.
# Pasang dengan: pip install pillow
try:
    from PIL import Image, ImageOps, ImageTk

    PIL_ADA = True
except ImportError:
    PIL_ADA = False

# Agar tampilan tidak buram di Windows (layar dengan scaling 125% / 150%).
# Harus dijalankan sebelum tk.Tk() dibuat.
if sys.platform == "win32":
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ---------------------------------------------------------------- pengaturan
JUDUL_APP = "Resep DapurKu"
PLACEHOLDER = "Cari resep"

ORANYE = "#D14300"
ORANYE_HOVER = "#B93600"
SIDEBAR = "#F3F3F3"
LATAR = "#FAFAFA"
PUTIH = "#FFFFFF"
TEKS = "#1A1A1A"
REDUP = "#6E6E6E"
GARIS = "#D0D0D0"
FOKUS = "#1A6FD0"
MERAH = "#C42B1C"

# Warna kartu untuk resep baru (dipakai bergantian)
WARNA_KARTU = ["#E2AE58", "#5E3B70", "#C94A2E", "#B8793A", "#D9A441"]

# Folder ikon: assets/icons/<nama>.png
_BASE = os.path.dirname(os.path.abspath(__file__))
FOLDER_IKON = os.path.join(_BASE, "assets", "icons")
# Ikon dicari di beberapa lokasi (urutan ini), jadi tetap terbaca kalau foldernya sedikit berbeda
FOLDER_IKON_KANDIDAT = [FOLDER_IKON, os.path.join(_BASE, "icons"), _BASE]

# Folder tempat foto resep disalin (otomatis dibuat): foto/<nama_file>
FOLDER_FOTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foto")

# Nama file ikon di assets/icons (tanpa .png). Kalau file-nya tidak ada, ikon dibiarkan kosong.
NAMA_IKON = (
    "search", "plus", "home", "back",
    "save", "cancel", "edit", "trash", "star", "photo",
    "badge_28", "badge_32",  # lingkaran oranye untuk nomor langkah
)

# Ukuran foto di halaman detail (persegi, tetap walau jendela diubah)
UKURAN_FOTO_DETAIL = 398


# ------------------------------------------------------------------ transisi
DURASI_KELUAR = 0.11   # detik: halaman lama memudar
DURASI_MASUK = 0.24    # detik: halaman baru memudar masuk + bergeser
JARAK_GESER = 36       # piksel geseran halaman
DURASI_KARTU = 0.26    # detik: kartu bergeser masuk saat pindah tab Resep <-> Favorit
JARAK_KARTU = 64       # piksel geseran kartu
KEDALAMAN_HALAMAN = {"beranda": 0, "detail": 1, "form": 2}  # menentukan arah geser


# =====================================================================
# FRONTEND -> BACKEND API -> MySQL db_dapur (phpMyAdmin)
# =====================================================================
import requests

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000").rstrip("/")
API_TIMEOUT = 8
AUTH_TOKEN = None
AUTH_USER = None

def _api(method, path, **kwargs):
    try:
        headers = kwargs.pop("headers", {})
        if AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
        return requests.request(method, f"{API_BASE}{path}", timeout=API_TIMEOUT, headers=headers, **kwargs)
    except requests.RequestException as e:
        _pesan("error", "Backend tidak terhubung",
               f"Tidak bisa menghubungi API DapurKu di {API_BASE}.\n"
               "Pastikan backend sudah dijalankan.\n\nDetail: " + str(e))
        return None

def setup_database_dan_tabel():
    """Cek API dan koneksi database. Tidak membuat atau menghapus tabel."""
    response = _api("GET", "/health")
    if response is None:
        return False
    if response.ok:
        return True
    _pesan("error", "Database", response.text)
    return False

def tampil_data():
    response = _api("GET", "/recipes")
    if response is None or not response.ok:
        if response is not None:
            _pesan("error", "Gagal mengambil resep", response.text)
        return []
    try:
        rows=response.json()
        return [{
            "id": r["id_recipe"], "name": r["nama_resep"],
            "photo": r.get("foto") or "", "favorite": bool(r.get("favorit")),
            "cooking_time": r.get("waktu_masak"),
            "ingredients": [(b.get("jumlah_kebutuhan") or "", b["nama_bahan"]) for b in r.get("bahan",[])],
            "directions": r.get("langkah") or _pecah_langkah(r.get("langkah_pembuatan") or "")
        } for r in rows]
    except (ValueError, KeyError, TypeError) as e:
        _pesan("error", "Data API", f"Format data resep tidak sesuai: {e}")
        return []

def _payload_resep(nama, waktu_masak, foto, bahan, langkah):
    return {
        "nama_resep": nama.strip(),
        "waktu_masak": waktu_masak,
        "langkah_pembuatan": "\n".join(f"{i}. {s}" for i,s in enumerate(langkah,1)),
        "foto": foto or None,
        "bahan": [{"nama_bahan": name, "jumlah_kebutuhan": amount or None}
                  for amount,name in bahan if str(name).strip()]
    }

def simpan_data(nama, waktu_masak, foto, bahan, langkah):
    response=_api("POST","/recipes",json=_payload_resep(nama,waktu_masak,foto,bahan,langkah))
    if response is None: return None
    if response.status_code==201:
        return response.json().get("id_recipe")
    try: message=response.json().get("detail",response.text)
    except ValueError: message=response.text
    _pesan("error","Gagal menyimpan resep",str(message))
    return None

def ubah_data(id_resep, nama, waktu_masak, foto, bahan, langkah):
    response=_api("PUT",f"/recipes/{id_resep}",json=_payload_resep(nama,waktu_masak,foto,bahan,langkah))
    if response is not None and response.ok: return True
    if response is not None:
        _pesan("error","Gagal mengubah resep",response.text)
    return False

def hapus_data(id_resep):
    response=_api("DELETE",f"/recipes/{id_resep}")
    if response is not None and response.status_code==204: return True
    if response is not None: _pesan("error","Gagal menghapus resep",response.text)
    return False

def ubah_favorit_db(id_resep, favorit):
    response=_api("PUT",f"/recipes/{id_resep}/favorite",params={"favorit":str(bool(favorit)).lower()})
    if response is not None and response.ok: return True
    if response is not None: _pesan("error","Favorit",response.text)
    return False

# --- helper format data ---
def _hapus_nomor(langkah):
    """'1. Tumis bawang' -> 'Tumis bawang' (nomor ditampilkan sendiri oleh UI)."""
    return re.sub(r"^\s*\d+[\.\)]\s*", "", langkah).strip()


def _pecah_langkah(teks):
    return [_hapus_nomor(s) for s in teks.replace("\\n", "\n").splitlines() if s.strip()]


def _rapikan_bahan(nama):
    nama = " ".join(str(nama).split())
    return (nama[:1].upper() + nama[1:])[:100]


# Operasi database dikerjakan backend; helper SQL lokal lama sudah dihapus.

class AplikasiResep:
    def __init__(self, root):
        self.root = root
        self.font_nama = self.pilih_font()
        self.ikon = {}
        self.path_ikon = {}
        self.ikon_hilang = []
        self.muat_semua_ikon()

        self.resep = self.muat_resep()
        self.tab_aktif = "Resep"        # "Resep" atau "Favorit"
        self.resep_dipilih = None       # resep yang sedang dilihat
        self.resep_diedit = None        # resep yang sedang diedit (None = resep baru)
        self.placeholder_aktif = True   # True kalau kotak cari masih berisi "Cari resep"
        self.kolom_kartu = 5
        self.baris_bahan = []           # baris input bahan di form
        self.cache_foto = {}            # foto yang sudah dimuat (supaya tidak dibaca ulang)
        self.foto_form = None           # path foto yang sedang dipilih di form
        self.foto_form_baru = False     # True kalau foto baru dipilih dan belum disalin
        self.area_scroll = {}           # daftar area yang bisa di-scroll

        # Keadaan transisi antarhalaman
        self._halaman_aktif = None      # "beranda" / "detail" / "form"
        self._tahap = None              # None / "keluar" / "masuk"
        self._tujuan = None             # (nama, fungsi_bangun, arah)
        self._job = None                # id after() yang sedang berjalan
        self._job_kartu = None          # id after() animasi kartu
        self._t0 = 0.0
        self._alpha = 1.0
        self._alpha_awal = 1.0
        self._arah = 1
        self._alpha_ok = True           # False kalau sistem tidak mendukung transparansi jendela

        self.atur_jendela()
        # Satu Frame untuk halaman aktif; diposisikan dengan place() supaya bisa digeser
        self.halaman = tk.Frame(root, bg=LATAR)
        self.halaman.place(x=0, y=0, relwidth=1, relheight=1)
        root.bind_all("<MouseWheel>", self.saat_mouse_wheel)
        self.tampil_beranda()
        root.after(600, self.periksa_ikon)

    def logout(self):
        global AUTH_TOKEN, AUTH_USER
        if not messagebox.askyesno("Keluar", "Keluar dari akun DapurKu?", parent=self.root):
            return
        AUTH_TOKEN, AUTH_USER = None, None
        self.root.destroy()
        buka_login()

    # ------------------------------------------------------------ persiapan
    def muat_resep(self):
        """Ambil semua resep dari database MySQL (db_dapur).

        Bentuk tiap resep:
        {"id": int, "name": str, "color": str, "favorite": bool,
         "photo": nama file di folder foto/ ("" kalau tidak ada),
         "ingredients": [(takaran, bahan), ...], "directions": [langkah, ...]}
        """
        hasil = []
        for r in tampil_data():
            hasil.append({
                "id": r["id"],
                "name": r["name"],
                "color": WARNA_KARTU[(r["id"] - 1) % len(WARNA_KARTU)],
                "favorite": r["favorite"],
                "photo": r["photo"],
                "ingredients": r["ingredients"],
                "directions": r["directions"],
            })
        return hasil

    def pilih_font(self):
        tersedia = set(tkfont.families())
        for nama in ("Inter", "Segoe UI", "Helvetica", "Arial", "DejaVu Sans"):
            if nama in tersedia:
                return nama
        return "TkDefaultFont"

    def font(self, ukuran, tebal=False):
        # Ukuran negatif = piksel
        if tebal:
            return (self.font_nama, -ukuran, "bold")
        return (self.font_nama, -ukuran)

    def muat_semua_ikon(self):
        """Muat semua ikon PNG. Dicari di assets/icons, icons, lalu folder program."""
        for nama in NAMA_IKON:
            for folder in FOLDER_IKON_KANDIDAT:
                path = os.path.join(folder, nama + ".png")
                if not os.path.isfile(path):
                    continue
                try:
                    self.ikon[nama] = tk.PhotoImage(master=self.root, file=path)
                    self.path_ikon[nama] = path
                    break
                except tk.TclError:
                    continue
            else:
                self.ikon_hilang.append(nama)

    def periksa_ikon(self):
        """Beri tahu kalau ada ikon yang tidak ketemu (supaya tidak diam-diam kosong)."""
        if self.ikon_hilang:
            messagebox.showwarning(
                "Ikon tidak ditemukan",
                "Ikon berikut belum ketemu: " + ", ".join(self.ikon_hilang)
                + "\n\nTaruh file PNG-nya di folder:\n" + FOLDER_IKON,
                parent=self.root,
            )

    def ikon_terang(self, nama, ukuran):
        """Versi putih transparan dari sebuah ikon, untuk dipasang di atas blok warna."""
        kunci = ("terang", nama, ukuran)
        if kunci in self.cache_foto:
            return self.cache_foto[kunci]
        path = self.path_ikon.get(nama)
        if not PIL_ADA or not path:
            return None
        try:
            gambar = Image.open(path).convert("RGBA").resize((ukuran, ukuran), Image.LANCZOS)
            alfa = gambar.getchannel("A").point(lambda a: int(a * 0.85))
            putih = Image.new("RGBA", gambar.size, (255, 255, 255, 255))
            putih.putalpha(alfa)
            hasil = ImageTk.PhotoImage(putih, master=self.root)
        except Exception:
            return None
        self.cache_foto[kunci] = hasil
        return hasil

    def atur_jendela(self):
        lebar = min(1317, self.root.winfo_screenwidth() - 40)
        tinggi = min(867, self.root.winfo_screenheight() - 100)
        x = (self.root.winfo_screenwidth() - lebar) // 2
        y = max(0, (self.root.winfo_screenheight() - tinggi) // 2 - 20)
        self.root.title(JUDUL_APP)
        self.root.geometry(f"{lebar}x{tinggi}+{x}+{y}")
        self.root.minsize(760, 520)
        self.root.configure(bg=LATAR)

    def bersihkan_halaman(self):
        for widget in self.halaman.winfo_children():
            widget.destroy()
        self.area_scroll = {}
        self.root.unbind("<Escape>")

    # ------------------------------------------------------------ transisi
    # Alur: halaman lama memudar keluar -> halaman baru dibangun saat jendela hampir
    # transparan (jadi proses membangun tidak terlihat patah-patah) -> halaman baru
    # memudar masuk sambil bergeser sedikit. Semua berbasis waktu, bukan jumlah langkah,
    # sehingga durasinya sama di komputer cepat maupun lambat.
    def atur_alpha(self, nilai):
        nilai = max(0.0, min(1.0, nilai))
        self._alpha = nilai
        if self._alpha_ok:
            try:
                self.root.attributes("-alpha", nilai)
            except tk.TclError:
                self._alpha_ok = False

    def batalkan_job(self):
        if self._job is not None:
            try:
                self.root.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def ganti_isi(self, nama, bangun):
        """Ganti isi halaman sekarang juga (tanpa animasi)."""
        self.bersihkan_halaman()
        self._halaman_aktif = nama
        bangun()

    def pindah_halaman(self, nama, bangun):
        """Pindah ke halaman `nama` dengan transisi. `bangun` membuat isi halaman barunya."""
        if self._halaman_aktif is None:  # halaman pertama: tanpa transisi
            self.ganti_isi(nama, bangun)
            return
        selisih = KEDALAMAN_HALAMAN[nama] - KEDALAMAN_HALAMAN[self._halaman_aktif]
        arah = 1 if selisih >= 0 else -1  # masuk lebih dalam: dari kanan, kembali: dari kiri
        self._tujuan = (nama, bangun, arah)
        if self._tahap == "keluar":  # klik cepat: cukup ganti tujuan terbaru
            return
        self.mulai_keluar()

    def mulai_keluar(self):
        self.batalkan_job()
        self._tahap = "keluar"
        self._t0 = time.perf_counter()
        self._alpha_awal = self._alpha
        self.langkah_keluar()

    def langkah_keluar(self):
        t = min(1.0, (time.perf_counter() - self._t0) / DURASI_KELUAR)
        self.atur_alpha(self._alpha_awal * (1 - t * t))  # ease-in
        if t < 1.0:
            self._job = self.root.after(8, self.langkah_keluar)
        else:
            self._job = None
            self.selesai_keluar()

    def selesai_keluar(self):
        nama, bangun, arah = self._tujuan
        try:
            self.ganti_isi(nama, bangun)
        except Exception:
            self._tahap = None
            self.atur_alpha(1.0)
            self.halaman.place_configure(x=0)
            raise
        self.root.update_idletasks()  # tata letak selesai sebelum mulai memudar masuk
        self._arah = arah
        self.halaman.place_configure(x=arah * JARAK_GESER)
        self._tahap = "masuk"
        self._t0 = time.perf_counter()
        self.langkah_masuk()

    def langkah_masuk(self):
        t = min(1.0, (time.perf_counter() - self._t0) / DURASI_MASUK)
        e = 1 - (1 - t) ** 3  # ease-out: cepat di awal, melambat di akhir
        self.atur_alpha(e)
        self.halaman.place_configure(x=round(self._arah * JARAK_GESER * (1 - e)))
        if t < 1.0:
            self._job = self.root.after(8, self.langkah_masuk)
        else:
            self._job = None
            self._tahap = None

    def animasi_awal(self):
        """Dipanggil sekali setelah jendela tampil: aplikasi muncul dengan memudar masuk."""
        self._arah = 1
        self.halaman.place_configure(x=JARAK_GESER)
        self._tahap = "masuk"
        self._t0 = time.perf_counter()
        self.langkah_masuk()

    # ------------------------------------------------------ komponen umum
    def buat_ikon(self, induk, nama, latar):
        """Label berisi ikon PNG. Kalau file PNG-nya tidak ada, hasilnya kosong."""
        return tk.Label(induk, image=self.ikon.get(nama), bg=latar)

    def buat_tombol(self, induk, teks, ikon, perintah, utama=False, warna_teks=None):
        latar = ORANYE if utama else PUTIH
        hover = ORANYE_HOVER if utama else "#F5F5F5"
        warna = warna_teks or (PUTIH if utama else TEKS)
        gambar = self.ikon.get(ikon)
        tulisan = " " + teks if gambar else teks
        tombol = tk.Button(
            induk,
            text=tulisan,
            image=gambar,
            compound="left",
            command=perintah,
            bg=latar,
            fg=warna,
            activebackground=hover,
            activeforeground=warna,
            font=self.font(17),
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
            cursor="hand2",
            highlightthickness=0 if utama else 1,
            highlightbackground=GARIS,
            highlightcolor=GARIS,
        )
        tombol.bind("<Enter>", lambda e: tombol.config(bg=hover))
        tombol.bind("<Leave>", lambda e: tombol.config(bg=latar))
        return tombol

    def buat_kepala(self, judul, perintah_kembali):
        """Bar judul halaman (di bawah bar Windows) dengan tombol kembali."""
        kepala = tk.Frame(self.halaman, bg=SIDEBAR, height=70)
        kepala.pack(fill="x")
        kepala.pack_propagate(False)
        gambar = self.ikon.get("back")
        kembali = tk.Button(
            kepala,
            image=gambar,
            command=perintah_kembali,
            bg=SIDEBAR,
            fg=TEKS,
            activebackground="#E6E6E6",
            font=self.font(24),
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
        )
        kembali.pack(side="left", padx=(18, 0))
        tk.Label(kepala, text=judul, bg=SIDEBAR, fg=TEKS, font=self.font(30)).pack(
            side="left", padx=(8, 0)
        )
        return kepala

    def buat_panel(self, induk):
        return tk.Frame(
            induk, bg=PUTIH, highlightbackground=GARIS, highlightcolor=GARIS, highlightthickness=1
        )

    def buat_lingkaran(self, induk, nomor, ukuran, ukuran_font):
        """Lingkaran bernomor: gambar PNG badge_<ukuran>.png dengan angka tepat di tengahnya."""
        return tk.Label(
            induk,
            image=self.ikon.get(f"badge_{ukuran}"),
            text=str(nomor),
            compound="center",
            fg=PUTIH,
            bg=PUTIH,
            bd=0,
            font=self.font(ukuran_font, True),
        )

    def buat_entry(self, induk, variabel, lebar=20):
        return tk.Entry(
            induk,
            textvariable=variabel,
            width=lebar,
            bg=LATAR,
            fg=TEKS,
            insertbackground=TEKS,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=GARIS,
            highlightcolor=FOKUS,
            font=self.font(16),
        )

    def buat_area_scroll(self, induk, latar, dengan_scrollbar=False):
        """Area yang bisa di-scroll. Mengembalikan (wadah, canvas, isi)."""
        wadah = tk.Frame(induk, bg=latar)
        wadah.grid_rowconfigure(0, weight=1)
        wadah.grid_columnconfigure(0, weight=1)
        kanvas = tk.Canvas(
            wadah, width=1, height=1, bg=latar, highlightthickness=0, yscrollincrement=30
        )
        kanvas.grid(row=0, column=0, sticky="nsew")
        isi = tk.Frame(kanvas, bg=latar)
        jendela = kanvas.create_window((0, 0), window=isi, anchor="nw")

        scrollbar = None
        if dengan_scrollbar:
            scrollbar = ttk.Scrollbar(wadah, orient="vertical", command=kanvas.yview)
            kanvas.configure(yscrollcommand=scrollbar.set)

        def perbarui(_event=None):
            tinggi_isi = isi.winfo_reqheight()
            kanvas.configure(scrollregion=(0, 0, kanvas.winfo_width(), tinggi_isi))
            bisa_scroll = tinggi_isi > kanvas.winfo_height() > 1
            if not bisa_scroll:
                kanvas.yview_moveto(0)
            if scrollbar is not None:
                if bisa_scroll:
                    scrollbar.grid(row=0, column=1, sticky="ns")
                else:
                    scrollbar.grid_remove()

        def saat_kanvas_berubah(event):
            kanvas.itemconfigure(jendela, width=event.width)
            perbarui()

        kanvas.bind("<Configure>", saat_kanvas_berubah)
        isi.bind("<Configure>", perbarui)
        self.area_scroll[wadah] = kanvas
        return wadah, kanvas, isi

    def saat_mouse_wheel(self, event):
        """Scroll area yang sedang ditunjuk kursor."""
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        while widget is not None:
            if widget in self.area_scroll:
                kanvas = self.area_scroll[widget]
                if kanvas.winfo_exists() and kanvas.bbox("all"):
                    tinggi_isi = kanvas.bbox("all")[3]
                    if tinggi_isi > kanvas.winfo_height():
                        kanvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
                return
            widget = widget.master

    def path_foto(self, nama_file):
        """Path lengkap foto di folder foto/, atau None kalau resep tidak punya foto."""
        if not nama_file:
            return None
        return os.path.join(FOLDER_FOTO, os.path.basename(nama_file))

    def muat_foto(self, path, lebar, tinggi, simpan_cache=True):
        """Muat foto, potong dari tengah agar pas lebar x tinggi. None kalau gagal."""
        if not PIL_ADA or not path or lebar < 2 or tinggi < 2 or not os.path.isfile(path):
            return None
        kunci = (path, lebar, tinggi)
        if kunci in self.cache_foto:
            return self.cache_foto[kunci]
        try:
            gambar = Image.open(path)
            gambar = ImageOps.exif_transpose(gambar).convert("RGB")
            gambar = ImageOps.fit(gambar, (lebar, tinggi), Image.LANCZOS)
            hasil = ImageTk.PhotoImage(gambar)
        except Exception:
            return None
        if simpan_cache:
            self.cache_foto[kunci] = hasil
        return hasil

    def daftar_bahan(self, nilai):
        """Ubah data bahan jadi daftar (takaran, bahan)."""
        hasil = []
        if isinstance(nilai, str):
            for baris in nilai.splitlines():
                baris = baris.strip()
                if not baris:
                    continue
                if " | " in baris:
                    takaran, bahan = baris.split(" | ", 1)
                    hasil.append((takaran.strip(), bahan.strip()))
                else:
                    hasil.append(("", baris))
        elif isinstance(nilai, (list, tuple)):
            for item in nilai:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    hasil.append((str(item[0]), str(item[1])))
                else:
                    hasil.append(("", str(item)))
        return hasil

    def daftar_langkah(self, nilai):
        """Ubah data langkah jadi daftar teks (satu langkah per baris)."""
        if isinstance(nilai, str):
            nilai = nilai.splitlines()
        return [str(langkah).strip() for langkah in nilai if str(langkah).strip()]

    # ------------------------------------------------------------ BERANDA
    def tampil_beranda(self):
        self.pindah_halaman("beranda", self._bangun_beranda)

    def _bangun_beranda(self):
        self.resep_dipilih = None
        self.resep_diedit = None

        badan = tk.Frame(self.halaman, bg=LATAR)
        badan.pack(fill="both", expand=True)
        badan.grid_rowconfigure(0, weight=1)
        badan.grid_columnconfigure(1, weight=1)
        self.buat_sidebar(badan)
        self.buat_konten_utama(badan)
        badan.bind("<Button-1>", lambda e: self.root.focus_set())

    def buat_sidebar(self, induk):
        sidebar = tk.Frame(induk, bg=SIDEBAR, width=321)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.pack_propagate(False)
        sidebar.bind("<Button-1>", lambda e: self.root.focus_set())

        # Branding aplikasi
        tk.Label(sidebar, text="Resep DapurKu", bg=SIDEBAR, fg=ORANYE,
                 font=self.font(23, True), anchor="w").pack(fill="x", padx=20, pady=(20, 4))
        tk.Label(sidebar, text="Temukan dan simpan resep favorit", bg=SIDEBAR, fg=REDUP,
                 font=self.font(12), anchor="w").pack(fill="x", padx=20, pady=(0, 10))

        # Kotak pencarian
        batas = tk.Frame(sidebar, bg="#8A8A8A", height=40)
        batas.pack(fill="x", padx=17, pady=(14, 18))
        batas.pack_propagate(False)
        dalam = tk.Frame(batas, bg="#F9F9F9")
        dalam.pack(fill="both", expand=True, padx=1, pady=1)
        self.buat_ikon(dalam, "search", "#F9F9F9").pack(side="right", padx=(0, 10))

        # Sidebar dibuat ulang tiap pindah halaman, jadi status placeholder direset di sini
        self.placeholder_aktif = True
        self.kata_cari = tk.StringVar(value=PLACEHOLDER)
        self.entry_cari = tk.Entry(
            dalam,
            textvariable=self.kata_cari,
            bg="#F9F9F9",
            fg="#5F5F5F",
            insertbackground=TEKS,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=self.font(17),
        )
        self.entry_cari.pack(side="left", fill="both", expand=True, padx=(11, 4))
        self.entry_cari.bind("<FocusIn>", self.saat_fokus_cari)
        self.entry_cari.bind("<FocusOut>", self.saat_lepas_fokus_cari)
        self.entry_cari.bind("<KeyRelease>", lambda e: self.gambar_kartu())

        # Kategori pengguna ditentukan dari kolom role pada tabel users.
        role = (AUTH_USER or {}).get("role", "pemula")
        info_role = {
            "Chef": ("CHEF", "Mengelola resep", "Bisa menambah, mengubah, dan menghapus resep."),
            "Ibu Rumah Tangga": ("RUMAH TANGGA", "Berbagi resep", "Bisa melihat dan menambahkan resep."),
            "Anak Kos": ("ANAK KOS", "Resep praktis", "Bisa melihat dan menambahkan resep."),
            "pembaca": ("PEMBACA", "Akses membaca", "Bisa melihat resep dan menyimpan favorit."),
            "pemula": ("PEMULA", "Akses dasar", "Bisa melihat resep dan menyimpan favorit."),
        }
        kategori, subjudul, deskripsi = info_role.get(role, (role.upper(), "Pengguna", "Akses resep sesuai role akun."))
        tk.Label(sidebar, text="KATEGORI AKUN", bg=SIDEBAR, fg=REDUP,
                 font=self.font(10, True), anchor="w").pack(fill="x", padx=20, pady=(4, 3))
        tk.Label(sidebar, text=kategori, bg=SIDEBAR, fg=ORANYE,
                 font=self.font(15, True), anchor="w").pack(fill="x", padx=20, pady=(0, 3))
        tk.Label(sidebar, text=subjudul, bg=SIDEBAR, fg=TEKS,
                 font=self.font(11, True), anchor="w").pack(fill="x", padx=20)
        tk.Label(sidebar, text=deskripsi, bg=SIDEBAR, fg=REDUP,
                 font=self.font(10), anchor="w", justify="left", wraplength=275).pack(fill="x", padx=20, pady=(2, 12))

        if role in ("Chef", "Ibu Rumah Tangga", "Anak Kos"):
            self.buat_menu_item(sidebar, "Resep baru", False, lambda: self.tampil_form())
        self.buat_menu_item(sidebar, "Beranda", True, lambda: self.pilih_tab("Resep"))
        self.buat_menu_item(sidebar, "Keluar", False, self.logout)

    def buat_menu_item(self, induk, teks, aktif, perintah):
        warna = ORANYE if aktif else TEKS
        baris = tk.Frame(induk, bg=SIDEBAR, height=52, cursor="hand2")
        baris.pack(fill="x")
        baris.pack_propagate(False)
        if aktif:
            tk.Frame(baris, bg=ORANYE, width=4).place(x=0, y=4, height=44)
        label = tk.Label(baris, text=teks, bg=SIDEBAR, fg=warna, font=self.font(16), anchor="w")
        label.place(x=24, y=0, relheight=1, width=270)
        for widget in (baris, label):
            widget.bind("<Button-1>", lambda e: perintah())

    def buat_konten_utama(self, induk):
        utama = tk.Frame(induk, bg=LATAR)
        utama.grid(row=0, column=1, sticky="nsew")
        utama.bind("<Button-1>", lambda e: self.root.focus_set())

        self.judul_halaman = tk.Label(utama, bg=LATAR, fg=TEKS, font=self.font(26), anchor="w")
        self.judul_halaman.pack(fill="x", padx=30, pady=(16, 6))

        baris_tab = tk.Frame(utama, bg=LATAR)
        baris_tab.pack(fill="x", padx=30, pady=(0, 14))
        self.label_tab = {}
        for nama in ("Resep", "Favorit"):
            label = tk.Label(
                baris_tab,
                text=nama,
                bg=LATAR,
                fg=TEKS if nama == self.tab_aktif else REDUP,
                font=self.font(24),
                cursor="hand2",
            )
            label.pack(side="left", padx=(0, 40))
            label.bind("<Button-1>", lambda e, n=nama: self.pilih_tab(n))
            self.label_tab[nama] = label

        wadah, self.kanvas_kartu, self.isi_kartu = self.buat_area_scroll(
            utama, LATAR, dengan_scrollbar=True
        )
        wadah.pack(fill="both", expand=True, padx=(30, 10), pady=(0, 20))
        self.kanvas_kartu.bind("<Configure>", self.saat_ukuran_kartu_berubah, add="+")

        self.perbarui_judul()
        self.gambar_kartu()

    def saat_ukuran_kartu_berubah(self, event):
        kolom = max(1, (event.width + 10) // (177 + 10))
        if kolom != self.kolom_kartu:
            self.kolom_kartu = kolom
            self.gambar_kartu()

    def perbarui_judul(self):
        if self.tab_aktif == "Favorit":
            jumlah = sum(1 for r in self.resep if r["favorite"])
            self.judul_halaman.config(text=f"Favorit ({jumlah})")
        else:
            self.judul_halaman.config(text=f"Semua Resep ({len(self.resep)})")

    def pilih_tab(self, nama):
        if nama == self.tab_aktif:
            return
        arah = 1 if nama == "Favorit" else -1  # Favorit masuk dari kanan, Resep dari kiri
        self.tab_aktif = nama
        for n, label in self.label_tab.items():
            label.config(fg=TEKS if n == nama else REDUP)
        self.perbarui_judul()
        self.gambar_kartu(animasi=arah)

    def kata_pencarian(self):
        if self.placeholder_aktif:
            return ""
        return self.kata_cari.get().strip().casefold()

    def gambar_kartu(self, animasi=0):
        for widget in self.isi_kartu.winfo_children():
            widget.destroy()

        kata = self.kata_pencarian()
        tampil = []
        for r in self.resep:
            cocok = kata in r["name"].casefold()
            if self.tab_aktif == "Favorit" and not r["favorite"]:
                cocok = False
            if cocok:
                tampil.append(r)

        for nomor, r in enumerate(tampil):
            baris, kolom = divmod(nomor, self.kolom_kartu)
            self.buat_kartu(r, baris, kolom)

        if not tampil:
            if self.tab_aktif == "Favorit":
                pesan = "Belum ada resep favorit"
            elif not self.resep:
                pesan = "Belum ada resep. Klik “Resep baru” untuk menambahkan."
            else:
                pesan = "Resep tidak ditemukan"
            tk.Label(self.isi_kartu, text=pesan, bg=LATAR, fg=REDUP, font=self.font(16)).grid(
                row=0, column=0, sticky="w"
            )
        self.kanvas_kartu.yview_moveto(0)
        if animasi:
            self.geser_kartu(animasi)

    def geser_kartu(self, arah):
        """Kartu bergeser masuk dari kanan (arah=1) atau kiri (arah=-1) saat pindah tab."""
        kanvas = self.kanvas_kartu
        item = kanvas.find_all()
        if not item:
            return
        item = item[0]
        if self._job_kartu is not None:
            try:
                kanvas.after_cancel(self._job_kartu)
            except tk.TclError:
                pass
            self._job_kartu = None
        mulai = time.perf_counter()

        def langkah():
            try:
                t = min(1.0, (time.perf_counter() - mulai) / DURASI_KARTU)
                e = 1 - (1 - t) ** 3
                kanvas.coords(item, round(arah * JARAK_KARTU * (1 - e)), 0)
                self._job_kartu = kanvas.after(8, langkah) if t < 1.0 else None
            except tk.TclError:  # halaman sudah diganti
                self._job_kartu = None

        langkah()

    def buat_kartu(self, r, baris, kolom):
        kartu = tk.Frame(self.isi_kartu, bg=r["color"], width=177, height=177, cursor="hand2")
        kartu.grid(row=baris, column=kolom, sticky="nw", padx=(0, 10), pady=(0, 10))
        kartu.pack_propagate(False)
        bar = tk.Frame(kartu, bg=ORANYE, height=38, cursor="hand2")
        bar.place(x=0, y=139, width=177, height=38)
        bar.pack_propagate(False)
        nama = tk.Label(
            bar, text=r["name"], bg=ORANYE, fg=PUTIH, font=self.font(24), anchor="w", cursor="hand2"
        )
        nama.pack(side="left", padx=(8, 0))
        widget_klik = [kartu, bar, nama]
        gambar = self.muat_foto(self.path_foto(r.get("photo")), 177, 177)
        if gambar:
            label_foto = tk.Label(kartu, image=gambar, bg=r["color"], bd=0, cursor="hand2")
            label_foto.image = gambar
            label_foto.place(x=0, y=0)
            bar.lift()  # bar nama tetap di atas foto
            widget_klik.append(label_foto)
        else:  # belum ada foto: tampilkan ikon foto di tengah blok warna
            ikon_foto = self.ikon_terang("photo", 56)
            if ikon_foto:
                label_ikon = tk.Label(kartu, image=ikon_foto, bg=r["color"], bd=0, cursor="hand2")
                label_ikon.image = ikon_foto
                label_ikon.place(x=88, y=70, anchor="center")
                bar.lift()
                widget_klik.append(label_ikon)
        for widget in widget_klik:
            widget.bind("<Button-1>", lambda e, r=r: self.tampil_detail(r))

    # ------------------------------------------------------ pencarian
    def saat_fokus_cari(self, _event):
        if self.placeholder_aktif:
            self.kata_cari.set("")
            self.entry_cari.config(fg=TEKS)
            self.placeholder_aktif = False

    def saat_lepas_fokus_cari(self, _event):
        if not self.kata_cari.get().strip():
            self.kata_cari.set(PLACEHOLDER)
            self.entry_cari.config(fg="#5F5F5F")
            self.placeholder_aktif = True
            self.gambar_kartu()

    # ------------------------------------------------------ DETAIL RESEP
    def tampil_detail(self, r, animasi=True):
        bangun = lambda: self._bangun_detail(r)
        if animasi:
            self.pindah_halaman("detail", bangun)
        else:  # mis. tombol favorit: halaman sama, cukup dibangun ulang
            self.ganti_isi("detail", bangun)

    def _bangun_detail(self, r):
        self.resep_dipilih = r
        self.resep_diedit = None

        kepala = self.buat_kepala("Resep", self.tampil_beranda)
        teks_favorit = "Hapus Favorit" if r["favorite"] else "Tambah Favorit"
        self.buat_tombol(kepala, teks_favorit, "star", self.ubah_favorit).pack(
            side="right", padx=(0, 30), pady=15
        )
        if (AUTH_USER or {}).get("role") == "Chef":
            self.buat_tombol(kepala, "Hapus", "trash", self.hapus_resep, warna_teks=MERAH).pack(
                side="right", padx=(0, 12), pady=15
            )
            self.buat_tombol(kepala, "Edit", "edit", lambda: self.tampil_form(r)).pack(
                side="right", padx=(0, 12), pady=15
            )

        badan = tk.Frame(self.halaman, bg=SIDEBAR)
        badan.pack(fill="both", expand=True, padx=30, pady=(20, 30))
        badan.grid_columnconfigure(0, minsize=400)
        badan.grid_columnconfigure(1, weight=1)
        badan.grid_rowconfigure(0, minsize=400)
        badan.grid_rowconfigure(1, weight=1)

        # Foto (blok warna) + nama resep
        foto = self.buat_panel(badan)
        foto.grid(row=0, column=0, sticky="nsew", padx=(0, 20), pady=(0, 20))
        area_foto = tk.Frame(foto, bg=r["color"])
        area_foto.pack(fill="both", expand=True)
        gambar = self.muat_foto(
            self.path_foto(r.get("photo")), UKURAN_FOTO_DETAIL, UKURAN_FOTO_DETAIL
        )
        if gambar:
            label_foto = tk.Label(area_foto, image=gambar, bg=r["color"], bd=0)
            label_foto.image = gambar
            label_foto.place(x=0, y=0)
        else:  # belum ada foto: tampilkan ikon foto di tengah blok warna
            ikon_foto = self.ikon_terang("photo", 96)
            if ikon_foto:
                label_ikon = tk.Label(area_foto, image=ikon_foto, bg=r["color"], bd=0)
                label_ikon.image = ikon_foto
                label_ikon.place(relx=0.5, rely=0.42, anchor="center")
        bar_nama = tk.Frame(area_foto, bg=ORANYE, height=78)
        bar_nama.place(x=0, rely=1.0, anchor="sw", relwidth=1, height=78)
        bar_nama.pack_propagate(False)
        tk.Label(
            bar_nama, text=r["name"], bg=ORANYE, fg=PUTIH, font=self.font(24), anchor="w"
        ).pack(fill="x", padx=14, pady=(5, 0))
        waktu = r.get("cooking_time")
        tk.Label(
            bar_nama, text=(f"⏱ {waktu} menit" if waktu else "Waktu memasak belum diisi"),
            bg=ORANYE, fg=PUTIH, font=self.font(14), anchor="w"
        ).pack(fill="x", padx=14, pady=(0, 4))

        # Panel bahan
        panel_bahan = self.buat_panel(badan)
        panel_bahan.grid(row=1, column=0, sticky="nsew", padx=(0, 20))
        self.buat_judul_panel(panel_bahan, "Bahan")
        wadah, _kanvas, isi = self.buat_area_scroll(panel_bahan, PUTIH)
        wadah.pack(fill="both", expand=True, padx=19, pady=(0, 19))
        daftar = self.daftar_bahan(r["ingredients"])
        for nomor, (takaran, bahan) in enumerate(daftar):
            baris = tk.Frame(isi, bg=PUTIH)
            baris.pack(fill="x")
            tk.Label(
                baris, text=takaran, bg=PUTIH, fg=TEKS, font=self.font(17, True),
                width=14, anchor="w",
            ).pack(side="left", pady=16)
            tk.Label(
                baris, text=bahan, bg=PUTIH, fg=TEKS, font=self.font(17),
                anchor="w", justify="left", wraplength=210,
            ).pack(side="left", pady=16)
            if nomor < len(daftar) - 1:
                tk.Frame(isi, bg="#E6E6E6", height=1).pack(fill="x")
        if not daftar:
            tk.Label(wadah, text="Belum ada bahan", bg=PUTIH, fg=REDUP, font=self.font(17)).place(
                relx=0.5, rely=0.5, anchor="center"
            )

        # Panel langkah
        panel_langkah = self.buat_panel(badan)
        panel_langkah.grid(row=0, column=1, rowspan=2, sticky="nsew")
        self.buat_judul_panel(panel_langkah, "Langkah")
        wadah, _kanvas, isi = self.buat_area_scroll(panel_langkah, PUTIH)
        wadah.pack(fill="both", expand=True, padx=19, pady=(0, 19))
        langkah = self.daftar_langkah(r["directions"])
        for nomor, teks in enumerate(langkah):
            baris = tk.Frame(isi, bg=PUTIH)
            baris.pack(fill="x")
            self.buat_lingkaran(baris, nomor + 1, 32, 16).pack(
                side="left", anchor="n", padx=(0, 18), pady=18
            )
            label = tk.Label(
                baris, text=teks, bg=PUTIH, fg=TEKS, font=self.font(18),
                anchor="nw", justify="left", wraplength=600,
            )
            label.pack(side="left", fill="x", expand=True, anchor="n", pady=14)
            baris.bind(
                "<Configure>",
                lambda e, label=label: label.config(wraplength=max(200, e.width - 90)),
            )
            if nomor < len(langkah) - 1:
                tk.Frame(isi, bg="#E6E6E6", height=1).pack(fill="x")
        if not langkah:
            tk.Label(wadah, text="Belum ada langkah", bg=PUTIH, fg=REDUP, font=self.font(17)).place(
                relx=0.5, rely=0.5, anchor="center"
            )

    def buat_judul_panel(self, panel, judul):
        kepala = tk.Frame(panel, bg=PUTIH)
        kepala.pack(fill="x", padx=19, pady=(14, 8))
        tk.Frame(kepala, bg=ORANYE, width=4, height=22).pack(side="left")
        tk.Label(kepala, text=judul, bg=PUTIH, fg=TEKS, font=self.font(20, True)).pack(
            side="left", padx=(10, 0)
        )

    def ubah_favorit(self):
        r = self.resep_dipilih
        r["favorite"] = not r["favorite"]
        ubah_favorit_db(r["id"], r["favorite"])
        self.tampil_detail(r, animasi=False)

    def hapus_resep(self):
        if (AUTH_USER or {}).get("role") != "Chef":
            messagebox.showwarning("Akses dibatasi", "Hanya role Chef yang dapat menghapus resep.", parent=self.root)
            return
        r = self.resep_dipilih
        if not messagebox.askyesno("Hapus resep", f"Hapus resep “{r['name']}”?", parent=self.root):
            return
        if not hapus_data(r["id"]):
            return
        self.resep.remove(r)
        self.tampil_beranda()

    # ------------------------------------------------------ FORM RESEP
    def tampil_form(self, r=None):
        role = (AUTH_USER or {}).get("role", "pemula")
        if role not in ("Chef", "Ibu Rumah Tangga", "Anak Kos"):
            messagebox.showwarning("Akses dibatasi", "Role akun ini hanya dapat melihat resep.", parent=self.root)
            return
        if r is not None and role != "Chef":
            messagebox.showwarning("Akses dibatasi", "Mengubah resep hanya dapat dilakukan oleh Chef.", parent=self.root)
            return
        self.pindah_halaman("form", lambda: self._bangun_form(r))

    def _bangun_form(self, r):
        self.resep_diedit = r
        judul = "Edit Resep" if r else "Resep Baru"

        kepala = self.buat_kepala(judul, self.batal_form)
        self.buat_tombol(kepala, "Batal", "cancel", self.batal_form).pack(
            side="right", padx=(0, 30), pady=15
        )
        self.buat_tombol(kepala, "Simpan", "save", self.simpan_resep, utama=True).pack(
            side="right", padx=(0, 12), pady=15
        )
        self.root.bind("<Escape>", lambda e: self.batal_form())

        badan = tk.Frame(self.halaman, bg=SIDEBAR)
        badan.pack(fill="both", expand=True, padx=30, pady=(20, 30))
        badan.grid_columnconfigure(0, weight=459)
        badan.grid_columnconfigure(1, weight=776)
        badan.grid_rowconfigure(1, weight=1)

        # 1. Nama makanan
        kartu_nama = self.buat_panel(badan)
        kartu_nama.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        self.buat_judul_langkah(kartu_nama, 1, "Nama Makanan")
        self.var_nama = tk.StringVar(value=r["name"] if r else "")
        self.entry_nama = self.buat_entry(kartu_nama, self.var_nama)
        self.entry_nama.config(font=self.font(17))
        self.entry_nama.pack(fill="x", padx=19, pady=(0, 10), ipady=5)
        self.entry_nama.bind("<Return>", lambda e: self.fokus_bahan_pertama())

        # Waktu memasak
        tk.Label(kartu_nama, text="Waktu memasak (menit)", bg=PUTIH, fg=TEKS,
                 font=self.font(15), anchor="w").pack(fill="x", padx=19, pady=(0, 4))
        self.var_waktu = tk.StringVar(value=str(r.get("cooking_time") or "") if r else "")
        self.entry_waktu = self.buat_entry(kartu_nama, self.var_waktu)
        self.entry_waktu.config(font=self.font(16))
        self.entry_waktu.pack(fill="x", padx=19, pady=(0, 10), ipady=3)

        # Foto (opsional)
        self.foto_form = self.path_foto(r.get("photo")) if r else None
        self.foto_form_baru = False
        baris_foto = tk.Frame(kartu_nama, bg=PUTIH)
        baris_foto.pack(fill="x", padx=19, pady=(0, 15))
        self.label_pratinjau = tk.Label(baris_foto, bg=PUTIH, bd=0)
        self.label_pratinjau.pack(side="left", padx=(0, 12))
        self.buat_tombol(baris_foto, "Pilih foto", "photo", self.pilih_foto).pack(side="left")
        self.buat_tombol(baris_foto, "Hapus foto", "cancel", self.hapus_foto_form).pack(
            side="left", padx=(10, 0)
        )
        self.label_info_foto = tk.Label(
            baris_foto, bg=PUTIH, fg=REDUP, font=self.font(15), anchor="w"
        )
        self.label_info_foto.pack(side="left", padx=(14, 0))
        self.perbarui_pratinjau_foto()

        # 2. Bahan
        kartu_bahan = self.buat_panel(badan)
        kartu_bahan.grid(row=1, column=0, sticky="nsew", padx=(0, 20))
        self.buat_judul_langkah(kartu_bahan, 2, "Bahan")
        self.buat_editor_bahan(kartu_bahan, r)

        # 3. Langkah (satu langkah per baris)
        kartu_langkah = self.buat_panel(badan)
        kartu_langkah.grid(row=1, column=1, sticky="nsew")
        self.buat_judul_langkah(kartu_langkah, 3, "Langkah")
        self.teks_langkah = tk.Text(
            kartu_langkah,
            width=1,
            height=1,
            bg=LATAR,
            fg=TEKS,
            insertbackground=TEKS,
            font=self.font(16),
            wrap="word",
            undo=True,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=GARIS,
            highlightcolor=FOKUS,
            padx=9,
            pady=8,
        )
        self.teks_langkah.pack(fill="both", expand=True, padx=19, pady=(0, 19))
        if r:
            self.teks_langkah.insert("1.0", "\n".join(self.daftar_langkah(r["directions"])))

        self.entry_nama.focus_set()

    def buat_judul_langkah(self, panel, nomor, judul):
        kepala = tk.Frame(panel, bg=PUTIH)
        kepala.pack(fill="x", padx=19, pady=(12, 10))
        self.buat_lingkaran(kepala, nomor, 28, 15).pack(side="left")
        tk.Label(kepala, text=judul, bg=PUTIH, fg=TEKS, font=self.font(19)).pack(
            side="left", padx=(12, 0)
        )

    def buat_editor_bahan(self, kartu, r):
        """Daftar baris 'Takaran' + 'Bahan'. Tidak perlu tanda | lagi."""
        self.baris_bahan = []
        isi_kartu = tk.Frame(kartu, bg=PUTIH)
        isi_kartu.pack(fill="both", expand=True, padx=19, pady=(0, 19))

        judul_kolom = tk.Frame(isi_kartu, bg=PUTIH)
        judul_kolom.pack(fill="x", pady=(0, 6))
        tk.Label(
            judul_kolom, text="Takaran", width=12, anchor="w", bg=PUTIH, fg=REDUP, font=self.font(16)
        ).pack(side="left")
        tk.Label(judul_kolom, text="Bahan", anchor="w", bg=PUTIH, fg=REDUP, font=self.font(16)).pack(
            side="left", padx=(8, 0)
        )

        # Tombol tambah dipasang dulu di bawah supaya selalu terlihat
        self.buat_tombol(
            isi_kartu, "Tambah bahan", "plus", lambda: self.tambah_baris_bahan(fokus=True)
        ).pack(side="bottom", anchor="w", pady=(12, 0))

        wadah, self.kanvas_bahan, self.isi_bahan = self.buat_area_scroll(isi_kartu, PUTIH)
        wadah.pack(fill="both", expand=True)

        data = self.daftar_bahan(r["ingredients"]) if r else []
        for takaran, bahan in data or [("", "")]:
            self.tambah_baris_bahan(takaran, bahan)

    def tambah_baris_bahan(self, takaran="", bahan="", fokus=False):
        baris = tk.Frame(self.isi_bahan, bg=PUTIH)
        baris.pack(fill="x", pady=(0, 8))

        var_takaran = tk.StringVar(value=takaran)
        var_bahan = tk.StringVar(value=bahan)
        entry_takaran = self.buat_entry(baris, var_takaran, 12)
        entry_takaran.pack(side="left", ipady=5)

        gambar = self.ikon.get("cancel")
        tombol_hapus = tk.Button(
            baris,
            image=gambar,
            bg=PUTIH,
            activebackground="#F5F5F5",
            relief="flat",
            bd=0,
            padx=8,
            cursor="hand2",
        )
        tombol_hapus.pack(side="right", padx=(8, 0))

        entry_bahan = self.buat_entry(baris, var_bahan, 1)
        entry_bahan.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=5)

        item = {
            "baris": baris,
            "takaran": var_takaran,
            "bahan": var_bahan,
            "entry_takaran": entry_takaran,
            "entry_bahan": entry_bahan,
        }
        self.baris_bahan.append(item)

        def hapus_baris():
            self.baris_bahan.remove(item)
            baris.destroy()
            if not self.baris_bahan:
                self.tambah_baris_bahan()

        def saat_enter_bahan(_event):
            nomor = self.baris_bahan.index(item)
            if nomor < len(self.baris_bahan) - 1:
                self.baris_bahan[nomor + 1]["entry_takaran"].focus_set()
            elif var_takaran.get().strip() or var_bahan.get().strip():
                self.tambah_baris_bahan(fokus=True)

        tombol_hapus.config(command=hapus_baris)
        entry_takaran.bind("<Return>", lambda e: entry_bahan.focus_set())
        entry_bahan.bind("<Return>", saat_enter_bahan)

        if fokus:
            self.kanvas_bahan.update_idletasks()
            self.kanvas_bahan.yview_moveto(1.0)
            entry_takaran.focus_set()

    def pilih_foto(self):
        if not PIL_ADA:
            messagebox.showinfo(
                "Pillow belum terpasang",
                "Fitur foto membutuhkan Pillow.\nJalankan di terminal:\n\npip install pillow",
                parent=self.root,
            )
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Pilih foto makanan",
            filetypes=[
                ("Gambar", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
                ("Semua file", "*.*"),
            ],
        )
        if not path:
            return
        if self.muat_foto(path, 64, 64) is None:
            messagebox.showerror("Foto", "File ini tidak bisa dibuka sebagai gambar.", parent=self.root)
            return
        self.foto_form = path
        self.foto_form_baru = True
        self.perbarui_pratinjau_foto()

    def hapus_foto_form(self):
        self.foto_form = None
        self.foto_form_baru = False
        self.perbarui_pratinjau_foto()

    def perbarui_pratinjau_foto(self):
        gambar = self.muat_foto(self.foto_form, 64, 64) if self.foto_form else None
        if gambar:
            self.label_pratinjau.config(image=gambar)
            self.label_pratinjau.image = gambar
        else:
            self.label_pratinjau.config(image=self.ikon.get("photo", ""))
        if self.foto_form:
            self.label_info_foto.config(text=os.path.basename(self.foto_form))
        else:
            self.label_info_foto.config(text="Belum ada foto (opsional)")

    def simpan_foto_form(self):
        """Salin foto baru ke folder foto/ dan kembalikan nama filenya ("" = tanpa foto)."""
        if not self.foto_form:
            return ""
        if not self.foto_form_baru:
            return os.path.basename(self.foto_form)
        os.makedirs(FOLDER_FOTO, exist_ok=True)
        ekstensi = os.path.splitext(self.foto_form)[1].lower()
        nama_baru = uuid.uuid4().hex[:12] + ekstensi
        shutil.copyfile(self.foto_form, os.path.join(FOLDER_FOTO, nama_baru))
        return nama_baru

    def fokus_bahan_pertama(self):
        if self.baris_bahan:
            self.baris_bahan[0]["entry_takaran"].focus_set()

    def ambil_bahan(self):
        hasil = []
        for item in self.baris_bahan:
            takaran = item["takaran"].get().strip()
            bahan = item["bahan"].get().strip()
            if takaran or bahan:
                hasil.append((takaran, bahan))
        return hasil

    def batal_form(self):
        if self.resep_diedit is not None:
            self.tampil_detail(self.resep_diedit)
        else:
            self.tampil_beranda()

    def simpan_resep(self):
        nama = self.var_nama.get().strip()
        if not nama:
            self.entry_nama.config(highlightbackground=ORANYE, highlightcolor=ORANYE)
            self.entry_nama.focus_set()
            return

        waktu_text = self.var_waktu.get().strip()
        if not waktu_text.isdigit() or int(waktu_text) <= 0:
            messagebox.showwarning("Waktu memasak", "Isi waktu memasak dalam menit dengan angka lebih dari 0.", parent=self.root)
            self.entry_waktu.focus_set()
            return
        waktu_masak = int(waktu_text)

        try:
            nama_foto = self.simpan_foto_form()
        except OSError:
            messagebox.showerror("Foto", "Foto tidak bisa disimpan. Coba lagi.", parent=self.root)
            return

        data = {
            "name": nama,
            "cooking_time": waktu_masak,
            "photo": nama_foto,  # simpan nama file ini ke kolom foto (VARCHAR) di MySQL
            "ingredients": self.ambil_bahan(),
            "directions": self.daftar_langkah(self.teks_langkah.get("1.0", "end-1c")),
        }
        if self.resep_diedit is not None:
            if not ubah_data(self.resep_diedit["id"], nama, waktu_masak, nama_foto, data["ingredients"], data["directions"]):
                return
            self.resep_diedit.update(data)
            self.tampil_detail(self.resep_diedit)
            return

        id_baru = simpan_data(nama, waktu_masak, nama_foto, data["ingredients"], data["directions"])
        if id_baru is None:
            return
        warna = WARNA_KARTU[(id_baru - 1) % len(WARNA_KARTU)]
        self.resep.append({**data, "id": id_baru, "color": warna, "favorite": False})
        self.tab_aktif = "Resep"
        self.tampil_beranda()


def buka_aplikasi_sesudah_login(token, user):
    global AUTH_TOKEN, AUTH_USER
    AUTH_TOKEN, AUTH_USER = token, user
    login_root.destroy()
    root = tk.Tk()
    root.withdraw()
    if not setup_database_dan_tabel():
        root.destroy()
        buka_login()
        return
    app = AplikasiResep(root)
    app.atur_alpha(0.0)
    root.deiconify()
    app.animasi_awal()
    root.mainloop()

def buka_login():
    global login_root
    login_root = tk.Tk()
    login_root.title("Login - Resep DapurKu")
    login_root.configure(bg=LATAR)
    login_root.resizable(False, False)
    w, h = 500, 640
    x = (login_root.winfo_screenwidth() - w) // 2
    y = (login_root.winfo_screenheight() - h) // 2
    login_root.geometry(f"{w}x{h}+{x}+{y}")
    panel = tk.Frame(login_root, bg=PUTIH, highlightbackground=GARIS, highlightthickness=1)
    panel.pack(fill="both", expand=True, padx=24, pady=24)

    tk.Label(panel, text="🍲 Resep DapurKu", bg=PUTIH, fg=ORANYE,
             font=("Segoe UI", 23, "bold")).pack(pady=(14, 5))
    tk.Label(panel, text="Temukan dan simpan resep favoritmu", bg=PUTIH, fg=REDUP,
             font=("Segoe UI", 10)).pack(pady=(0, 8))

    mode_var=tk.StringVar(value="login")
    form_area=tk.Frame(panel,bg=PUTIH)
    form_area.pack(fill="both",expand=True,padx=30)

    def render_form():
        for child in form_area.winfo_children(): child.destroy()
        is_register=mode_var.get()=="register"
        tk.Label(form_area,text="Daftar Akun" if is_register else "Masuk ke Akun",
                 bg=PUTIH,fg=TEKS,font=("Segoe UI",15,"bold")).pack(pady=(2,12))
        tk.Label(form_area,text="Username",bg=PUTIH,fg=TEKS,font=("Segoe UI",10,"bold")).pack(anchor="w")
        username_var=tk.StringVar()
        ent_user=tk.Entry(form_area,textvariable=username_var,font=("Segoe UI",11),relief="flat",bg=LATAR,
                          highlightthickness=1,highlightbackground=GARIS,highlightcolor=FOKUS)
        ent_user.pack(fill="x",pady=(4,10),ipady=7)
        tk.Label(form_area,text="Password",bg=PUTIH,fg=TEKS,font=("Segoe UI",10,"bold")).pack(anchor="w")
        password_var=tk.StringVar()
        ent_pass=tk.Entry(form_area,textvariable=password_var,show="*",font=("Segoe UI",11),relief="flat",bg=LATAR,
                          highlightthickness=1,highlightbackground=GARIS,highlightcolor=FOKUS)
        ent_pass.pack(fill="x",pady=(4,10),ipady=7)
        role_var=tk.StringVar()
        role_combo=None
        if is_register:
            tk.Label(form_area,text="Kategori / Role",bg=PUTIH,fg=TEKS,font=("Segoe UI",10,"bold")).pack(anchor="w")
            role_combo=ttk.Combobox(form_area,textvariable=role_var,state="readonly",font=("Segoe UI",10))
            role_combo.pack(fill="x",pady=(4,12),ipady=3)
            role_response=_api("GET","/auth/roles")
            if role_response is not None and role_response.ok:
                roles=role_response.json()
                role_combo["values"]=roles
                if roles: role_var.set(roles[0])
            else:
                role_combo["values"]=[]
                tk.Label(form_area,text="Role tidak dapat dimuat dari database. Pastikan backend aktif.",
                         bg=PUTIH,fg=MERAH,font=("Segoe UI",9)).pack(anchor="w")

        def submit(event=None):
            username,password=username_var.get().strip(),password_var.get()
            if not username or not password:
                messagebox.showwarning("Form", "Username dan password wajib diisi.",parent=login_root); return
            if is_register:
                if len(username)<3:
                    messagebox.showwarning("Pendaftaran","Username minimal 3 karakter.",parent=login_root); return
                if len(password)<6:
                    messagebox.showwarning("Pendaftaran","Password minimal 6 karakter.",parent=login_root); return
                if not role_var.get():
                    messagebox.showwarning("Pendaftaran","Silakan pilih kategori akun.",parent=login_root); return
                response=_api("POST","/auth/register",json={"username":username,"password":password,"role":role_var.get()})
                if response is None: return
                if not response.ok:
                    try: detail=response.json().get("detail","Pendaftaran gagal")
                    except ValueError: detail="Pendaftaran gagal"
                    messagebox.showerror("Pendaftaran gagal",str(detail),parent=login_root); return
                messagebox.showinfo("Pendaftaran berhasil","Akun berhasil dibuat. Silakan masuk menggunakan akun baru.",parent=login_root)
                mode_var.set("login"); render_form(); return
            response=_api("POST","/auth/login",json={"username":username,"password":password})
            if response is None: return
            if not response.ok:
                try: detail=response.json().get("detail","Login gagal")
                except ValueError: detail="Login gagal"
                messagebox.showerror("Login gagal",str(detail),parent=login_root); return
            data=response.json()
            buka_aplikasi_sesudah_login(data["access_token"],data["user"])

        tk.Button(form_area,text="Daftar" if is_register else "Masuk",command=submit,bg=ORANYE,fg=PUTIH,
                  activebackground=ORANYE_HOVER,activeforeground=PUTIH,font=("Segoe UI",11,"bold"),
                  relief="flat",cursor="hand2").pack(fill="x",pady=(0,8),ipady=7)
        link_text="Sudah punya akun? Masuk" if is_register else "Belum punya akun? Daftar sekarang"
        tk.Button(form_area,text=link_text,command=lambda: (mode_var.set("login" if is_register else "register"),render_form()),
                  bg=PUTIH,fg=ORANYE,activebackground=PUTIH,activeforeground=ORANYE,
                  font=("Segoe UI",10,"underline"),relief="flat",cursor="hand2").pack(pady=(0,5))
        tk.Label(form_area,text="Pilihan kategori diambil dari kolom role tabel users pada db_dapur.",
                 bg=PUTIH,fg=REDUP,font=("Segoe UI",8),wraplength=350).pack(pady=(4,0))
        ent_user.focus_set()
        login_root.bind("<Return>",submit)

    render_form()
    login_root.mainloop()

if __name__ == "__main__":
    buka_login()
