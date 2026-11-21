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

# Tuple untuk jenis transaksi (isinya tidak berubah)
JENIS = ("pemasukan", "pengeluaran")

# List untuk menyimpan semua transaksi (tiap transaksi = dictionary)
daftar_transaksi = []

# Variabel untuk jendela edit (diisi saat tombol Edit ditekan)
jendela_edit = None
nomor_edit = 0


# ----------------------------------------------------------
# FUNGSI BANTU: Format angka jadi 1.000.000
# ----------------------------------------------------------
def format_rupiah(angka):
    teks = "{:,}".format(angka)
    return teks.replace(",", ".")


# ----------------------------------------------------------
# FUNGSI BANTU: Memeriksa input, mengembalikan jumlah (angka)
# atau None jika input tidak valid
# ----------------------------------------------------------
def cek_input(keterangan, jumlah_teks):
    # Pengkondisian: semua kolom harus diisi
    if keterangan == "" or jumlah_teks == "":
        messagebox.showwarning("Peringatan", "Semua kolom harus diisi!")
        return None

    # Penanganan error: jumlah harus angka
    try:
        jumlah = int(jumlah_teks)
    except ValueError:
        messagebox.showerror("Error", "Jumlah harus berupa angka!")
        return None

    # Pengkondisian: jumlah harus lebih dari 0
    if jumlah <= 0:
        messagebox.showerror("Error", "Jumlah harus lebih dari 0!")
        return None

    return jumlah


# ----------------------------------------------------------
# FUNGSI 1: Menambah transaksi
# ----------------------------------------------------------
def tambah_transaksi():
    jenis = combo_jenis.get()
    keterangan = entry_keterangan.get()
    jumlah = cek_input(keterangan, entry_jumlah.get())

    if jumlah is None:
        return

    transaksi = {
        "jenis": jenis,
        "keterangan": keterangan,
        "jumlah": jumlah
    }
    daftar_transaksi.append(transaksi)

    # Kosongkan kolom input
    entry_keterangan.delete(0, tk.END)
    entry_jumlah.delete(0, tk.END)

    perbarui_tampilan()


# ----------------------------------------------------------
# FUNGSI 2: Membuka jendela edit untuk transaksi yang dipilih
# ----------------------------------------------------------
def edit_transaksi():
    global jendela_edit, nomor_edit
    global combo_edit_jenis, entry_edit_keterangan, entry_edit_jumlah

    pilihan = tabel.selection()

    # Pengkondisian: harus ada baris yang dipilih
    if len(pilihan) == 0:
        messagebox.showwarning("Peringatan", "Pilih transaksi di tabel dulu!")
        return

    nomor_edit = tabel.index(pilihan[0])  # urutan baris (mulai dari 0)
    data = daftar_transaksi[nomor_edit]

    # Membuat jendela baru
    jendela_edit = tk.Toplevel(jendela)
    jendela_edit.title("Edit Transaksi")
    jendela_edit.geometry("320x190")
    jendela_edit.grab_set()  # jendela utama tidak bisa diklik dulu

    tk.Label(jendela_edit, text="Jenis").grid(row=0, column=0, sticky="w", padx=10, pady=8)
    combo_edit_jenis = ttk.Combobox(jendela_edit, values=JENIS, state="readonly", width=22)
    combo_edit_jenis.set(data["jenis"])
    combo_edit_jenis.grid(row=0, column=1, padx=5)

    tk.Label(jendela_edit, text="Keterangan").grid(row=1, column=0, sticky="w", padx=10, pady=8)
    entry_edit_keterangan = tk.Entry(jendela_edit, width=25)
    entry_edit_keterangan.insert(0, data["keterangan"])
    entry_edit_keterangan.grid(row=1, column=1, padx=5)

    tk.Label(jendela_edit, text="Jumlah (Rp)").grid(row=2, column=0, sticky="w", padx=10, pady=8)
    entry_edit_jumlah = tk.Entry(jendela_edit, width=25)
    entry_edit_jumlah.insert(0, str(data["jumlah"]))
    entry_edit_jumlah.grid(row=2, column=1, padx=5)

    tk.Button(jendela_edit, text="Simpan", width=12, bg="#2196F3", fg="white",
              command=simpan_edit).grid(row=3, column=0, columnspan=2, pady=12)


# ----------------------------------------------------------
# FUNGSI 3: Menyimpan hasil edit
# ----------------------------------------------------------
def simpan_edit():
    keterangan = entry_edit_keterangan.get()
    jumlah = cek_input(keterangan, entry_edit_jumlah.get())

    if jumlah is None:
        return

    # Ganti data lama dengan data baru
    daftar_transaksi[nomor_edit]["jenis"] = combo_edit_jenis.get()
    daftar_transaksi[nomor_edit]["keterangan"] = keterangan
    daftar_transaksi[nomor_edit]["jumlah"] = jumlah

    jendela_edit.destroy()
    perbarui_tampilan()


# ----------------------------------------------------------
# FUNGSI 4: Menghapus transaksi yang dipilih
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
# FUNGSI 5: Menghitung total pemasukan, pengeluaran, dan saldo
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
            "Rp " + format_rupiah(item["jumlah"]),
            item["keterangan"]
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
jendela.geometry("700x620")

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

tk.Label(frame_input, text="Jumlah (Rp)").grid(row=0, column=2, sticky="w", padx=(20, 0))
entry_jumlah = tk.Entry(frame_input, width=22)
entry_jumlah.grid(row=0, column=3, padx=5, pady=3)

tk.Button(frame_input, text="Tambah", width=12, bg="#4CAF50", fg="white",
          command=tambah_transaksi).grid(row=2, column=1, columnspan=2, pady=8)

# ---------------- Tabel transaksi ----------------
frame_tabel = tk.Frame(jendela)
frame_tabel.pack(padx=10, pady=5, fill="both", expand=True)

kolom = ("no", "jenis", "jumlah", "keterangan")
tabel = ttk.Treeview(frame_tabel, columns=kolom, show="headings", height=8)
tabel.heading("no", text="No")
tabel.heading("jenis", text="Jenis")
tabel.heading("jumlah", text="Jumlah")
tabel.heading("keterangan", text="Keterangan")
tabel.column("no", width=40, anchor="center")
tabel.column("jenis", width=110)
tabel.column("jumlah", width=140, anchor="e")
tabel.column("keterangan", width=250)

scroll = ttk.Scrollbar(frame_tabel, orient="vertical", command=tabel.yview)
tabel.configure(yscrollcommand=scroll.set)
tabel.pack(side="left", fill="both", expand=True)
scroll.pack(side="right", fill="y")

# ---------------- Tombol aksi ----------------
frame_tombol = tk.Frame(jendela)
frame_tombol.pack(pady=5)

tk.Button(frame_tombol, text="Edit", width=15, command=edit_transaksi).grid(row=0, column=0, padx=5)
tk.Button(frame_tombol, text="Hapus", width=15, command=hapus_transaksi).grid(row=0, column=1, padx=5)

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
