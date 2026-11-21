# ==========================================================
# PROGRAM KEUANGAN PRIBADI (VERSI GUI TKINTER)
# UAS Praktek Pemrograman Dasar - Politeknik Negeri Samarinda
# ==========================================================
# Materi yang dipakai:
# 1. Struktur data (list, dictionary, tuple)
# 2. Fungsi
# 3. Pengkondisian (if/elif/else)
# 4. Perulangan (for)
# 5. Penanganan error (try/except)
# 6. GUI dengan Tkinter (nilai tambah)
# ==========================================================

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog

# Tuple untuk jenis transaksi (isinya tidak berubah)
JENIS = ("pemasukan", "pengeluaran")

# List untuk menyimpan semua transaksi (tiap transaksi = dictionary)
daftar_transaksi = []


# ----------------------------------------------------------
# FUNGSI 1: Menambah transaksi
# ----------------------------------------------------------
def tambah_transaksi():
    jenis = combo_jenis.get()
    keterangan = entry_keterangan.get()
    kategori = entry_kategori.get()
    jumlah_teks = entry_jumlah.get()

    # Pengkondisian: cek semua kolom sudah diisi
    if keterangan == "" or kategori == "" or jumlah_teks == "":
        messagebox.showwarning("Peringatan", "Semua kolom harus diisi!")
        return

    # Penanganan error: jumlah harus angka
    try:
        jumlah = int(jumlah_teks)
    except ValueError:
        messagebox.showerror("Error", "Jumlah harus berupa angka!")
        return

    # Pengkondisian: jumlah harus lebih dari 0
    if jumlah <= 0:
        messagebox.showerror("Error", "Jumlah harus lebih dari 0!")
        return

    transaksi = {
        "jenis": jenis,
        "keterangan": keterangan,
        "kategori": kategori,
        "jumlah": jumlah
    }
    daftar_transaksi.append(transaksi)

    # Kosongkan kolom input
    entry_keterangan.delete(0, tk.END)
    entry_kategori.delete(0, tk.END)
    entry_jumlah.delete(0, tk.END)

    perbarui_tampilan()


# ----------------------------------------------------------
# FUNGSI 2: Mengubah jumlah transaksi yang dipilih
# ----------------------------------------------------------
def ubah_transaksi():
    pilihan = tabel.selection()

    # Pengkondisian: harus ada baris yang dipilih
    if len(pilihan) == 0:
        messagebox.showwarning("Peringatan", "Pilih transaksi di tabel dulu!")
        return

    nomor = tabel.index(pilihan[0])  # urutan baris (mulai dari 0)

    jumlah_baru = simpledialog.askinteger("Ubah Jumlah", "Masukkan jumlah baru (Rp):", minvalue=1)

    # Jika pengguna menekan Cancel, hasilnya None
    if jumlah_baru is not None:
        daftar_transaksi[nomor]["jumlah"] = jumlah_baru
        perbarui_tampilan()


# ----------------------------------------------------------
# FUNGSI 3: Menghapus transaksi yang dipilih
# ----------------------------------------------------------
def hapus_transaksi():
    pilihan = tabel.selection()

    if len(pilihan) == 0:
        messagebox.showwarning("Peringatan", "Pilih transaksi di tabel dulu!")
        return

    nomor = tabel.index(pilihan[0])

    yakin = messagebox.askyesno("Konfirmasi", "Yakin ingin menghapus transaksi ini?")
    if yakin:
        daftar_transaksi.pop(nomor)
        perbarui_tampilan()


# ----------------------------------------------------------
# FUNGSI 4: Menghitung total pemasukan, pengeluaran, dan saldo
# ----------------------------------------------------------
def hitung_saldo():
    total_masuk = 0
    total_keluar = 0

    for item in daftar_transaksi:
        if item["jenis"] == "pemasukan":
            total_masuk = total_masuk + item["jumlah"]
        else:
            total_keluar = total_keluar + item["jumlah"]

    saldo = total_masuk - total_keluar
    return total_masuk, total_keluar, saldo


# ----------------------------------------------------------
# FUNGSI 5: Ringkasan pengeluaran per kategori
# ----------------------------------------------------------
def ringkasan_kategori():
    ringkasan = {}  # dictionary: kategori -> total pengeluaran

    for item in daftar_transaksi:
        if item["jenis"] == "pengeluaran":
            kategori = item["kategori"]
            if kategori in ringkasan:
                ringkasan[kategori] = ringkasan[kategori] + item["jumlah"]
            else:
                ringkasan[kategori] = item["jumlah"]

    if len(ringkasan) == 0:
        messagebox.showinfo("Ringkasan", "Belum ada data pengeluaran.")
        return

    teks = ""
    for kategori in ringkasan:
        teks = teks + kategori + " : Rp " + format_rupiah(ringkasan[kategori]) + "\n"
    messagebox.showinfo("Pengeluaran per Kategori", teks)


# ----------------------------------------------------------
# FUNGSI BANTU: Format angka jadi 1.000.000
# ----------------------------------------------------------
def format_rupiah(angka):
    teks = "{:,}".format(angka)
    return teks.replace(",", ".")


# ----------------------------------------------------------
# FUNGSI BANTU: Memperbarui tabel dan label saldo
# ----------------------------------------------------------
def perbarui_tampilan():
    # Hapus semua baris lama di tabel
    for baris in tabel.get_children():
        tabel.delete(baris)

    # Isi ulang tabel dari list
    nomor = 1
    for item in daftar_transaksi:
        tabel.insert("", tk.END, values=(
            nomor,
            item["jenis"],
            item["keterangan"],
            item["kategori"],
            "Rp " + format_rupiah(item["jumlah"])
        ))
        nomor = nomor + 1

    # Hitung dan tampilkan saldo
    masuk, keluar, saldo = hitung_saldo()
    label_masuk.config(text="Total Pemasukan: Rp " + format_rupiah(masuk))
    label_keluar.config(text="Total Pengeluaran: Rp " + format_rupiah(keluar))

    # Pengkondisian: warna dan pesan sesuai saldo
    if saldo < 0:
        label_saldo.config(text="Saldo: -Rp " + format_rupiah(-saldo) + "  (Defisit!)", fg="red")
    elif saldo == 0:
        label_saldo.config(text="Saldo: Rp 0", fg="orange")
    else:
        label_saldo.config(text="Saldo: Rp " + format_rupiah(saldo), fg="green")


# ==========================================================
# MEMBUAT JENDELA UTAMA
# ==========================================================
jendela = tk.Tk()
jendela.title("Keuangan Pribadi")
jendela.geometry("700x560")

# Judul
tk.Label(jendela, text="KEUANGAN PRIBADI", font=("Arial", 16, "bold")).pack(pady=10)

# ---------------- Bagian input ----------------
frame_input = tk.LabelFrame(jendela, text="Tambah Transaksi", padx=10, pady=10)
frame_input.pack(padx=10, pady=5, fill="x")

tk.Label(frame_input, text="Jenis").grid(row=0, column=0, sticky="w")
combo_jenis = ttk.Combobox(frame_input, values=JENIS, state="readonly", width=18)
combo_jenis.current(0)
combo_jenis.grid(row=0, column=1, padx=5, pady=3)

tk.Label(frame_input, text="Keterangan").grid(row=1, column=0, sticky="w")
entry_keterangan = tk.Entry(frame_input, width=22)
entry_keterangan.grid(row=1, column=1, padx=5, pady=3)

tk.Label(frame_input, text="Kategori").grid(row=0, column=2, sticky="w", padx=(20, 0))
entry_kategori = tk.Entry(frame_input, width=22)
entry_kategori.grid(row=0, column=3, padx=5, pady=3)

tk.Label(frame_input, text="Jumlah (Rp)").grid(row=1, column=2, sticky="w", padx=(20, 0))
entry_jumlah = tk.Entry(frame_input, width=22)
entry_jumlah.grid(row=1, column=3, padx=5, pady=3)

tk.Button(frame_input, text="Tambah", width=12, bg="#4CAF50", fg="white",
          command=tambah_transaksi).grid(row=2, column=1, columnspan=2, pady=8)

# ---------------- Tabel transaksi ----------------
frame_tabel = tk.Frame(jendela)
frame_tabel.pack(padx=10, pady=5, fill="both", expand=True)

kolom = ("no", "jenis", "keterangan", "kategori", "jumlah")
tabel = ttk.Treeview(frame_tabel, columns=kolom, show="headings", height=10)
tabel.heading("no", text="No")
tabel.heading("jenis", text="Jenis")
tabel.heading("keterangan", text="Keterangan")
tabel.heading("kategori", text="Kategori")
tabel.heading("jumlah", text="Jumlah")
tabel.column("no", width=40, anchor="center")
tabel.column("jenis", width=100)
tabel.column("keterangan", width=200)
tabel.column("kategori", width=120)
tabel.column("jumlah", width=120, anchor="e")

scroll = ttk.Scrollbar(frame_tabel, orient="vertical", command=tabel.yview)
tabel.configure(yscrollcommand=scroll.set)
tabel.pack(side="left", fill="both", expand=True)
scroll.pack(side="right", fill="y")

# ---------------- Tombol aksi ----------------
frame_tombol = tk.Frame(jendela)
frame_tombol.pack(pady=5)

tk.Button(frame_tombol, text="Ubah Jumlah", width=15, command=ubah_transaksi).grid(row=0, column=0, padx=5)
tk.Button(frame_tombol, text="Hapus", width=15, command=hapus_transaksi).grid(row=0, column=1, padx=5)
tk.Button(frame_tombol, text="Ringkasan Kategori", width=18, command=ringkasan_kategori).grid(row=0, column=2, padx=5)

# ---------------- Bagian saldo ----------------
frame_saldo = tk.LabelFrame(jendela, text="Ringkasan Keuangan", padx=10, pady=10)
frame_saldo.pack(padx=10, pady=10, fill="x")

label_masuk = tk.Label(frame_saldo, text="", font=("Arial", 11))
label_masuk.pack(anchor="w")
label_keluar = tk.Label(frame_saldo, text="", font=("Arial", 11))
label_keluar.pack(anchor="w")
label_saldo = tk.Label(frame_saldo, text="", font=("Arial", 13, "bold"))
label_saldo.pack(anchor="w")

# Tampilkan kondisi awal lalu jalankan program
perbarui_tampilan()
jendela.mainloop()
