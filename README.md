# Algoritma Genetika untuk Penjadwalan Kuliah

Proyek ini mengimplementasikan Algoritma Genetika untuk menyelesaikan masalah penjadwalan kuliah yang kompleks. Tujuannya adalah untuk menghasilkan jadwal yang optimal dengan meminimalkan konflik berdasarkan serangkaian aturan (constraints) yang dapat dikustomisasi.

## Fitur Utama

-   **Optimasi Berbasis Algoritma Genetika**: Menggunakan proses evolusi (seleksi, crossover, mutasi) untuk mencari solusi terbaik.
-   **Konfigurasi Terpusat**: Parameter utama algoritma (ukuran populasi, laju mutasi, dll.) diatur dalam satu file konfigurasi agar mudah diubah.
-   **Aturan yang Dapat Dikustomisasi**: Aturan penjadwalan (constraints) dimuat dari file CSV eksternal, memungkinkan pengguna untuk mengaktifkan/menonaktifkan aturan tanpa mengubah kode.
-   **Struktur Kode Modular**: Kode diorganisir ke dalam modul-modul terpisah untuk data, logika, dan konfigurasi, membuatnya lebih mudah dipelihara dan dikembangkan.

## Struktur Proyek

Struktur proyek telah diorganisir untuk memisahkan antara logika, data, dan konfigurasi.

```
scheduling-genetic-algorithm/
├── config/
│   └── settings.py               # File konfigurasi untuk parameter algoritma
├── data/
│   ├── Constraints.csv           # Daftar aturan penjadwalan (bisa diaktifkan/dinonaktifkan)
│   ├── DataPenjadwalan.csv       # Data utama mata kuliah, dosen, dan kuota
│   ├── MeetingTime_1jam.csv      # Slot waktu untuk kelas 1 SKS
│   ├── MeetingTime_2jam.csv      # Slot waktu untuk kelas 2 SKS
│   ├── MeetingTime_4jam.csv      # Slot waktu untuk kelas 4 SKS
│   └── Ruangan.csv               # Data ruangan yang tersedia beserta kapasitasnya
├── src/
│   ├── __init__.py               # (Bisa ditambahkan agar src menjadi package)
│   ├── penjadwalan_genetic.py    # Skrip utama untuk menjalankan algoritma
│   ├── constraints/
│   │   └── constraints_loader.py # Logika untuk memuat aturan dari Constraints.csv
│   └── types/
│       └── __init__.py           # Definisi tipe data/objek (Course, Room, Instructor, dll.)
├── other/
│   └── penjadwalan_genetic_adaptif.py # (Eksperimental) Algoritma adaptif
├── .gitignore                    # Mengabaikan file yang tidak perlu di-commit
├── requirements.txt              # Daftar dependensi Python yang dibutuhkan
└── README.md                     # Dokumentasi ini
```

## Langkah Instalasi

1.  **Clone Repository**
    ```bash
    git clone <https://github.com/Naktekfis/scheduling-genetic-algorithm/tree/master>
    cd scheduling-genetic-algorithm
    ```

2.  **Buat dan Aktifkan Virtual Environment**
    ```bash
    # Membuat virtual environment
    python -m venv .venv

    # Mengaktifkan di Windows
    .\.venv\Scripts\activate

    # Mengaktifkan di macOS/Linux
    source .venv/bin/activate
    ```

3.  **Instal Dependensi**
    Pastikan virtual environment Anda sudah aktif, lalu jalankan:
    ```bash
    pip install -r requirements.txt
    ```

## Konfigurasi

Sebelum menjalankan, Anda dapat menyesuaikan parameter algoritma dan aturan penjadwalan:

1.  **Parameter Algoritma**: Buka file `config/settings.py` untuk mengubah nilai seperti `POPULATION_SIZE`, `MAX_GENERATION`, `CROSSOVER_RATE`, dan `MUTATION_RATE`.

2.  **Aturan Penjadwalan**: Buka file `data/Constraints.csv`. Ubah nilai di kolom `enabled` menjadi `1` untuk mengaktifkan aturan atau `0` untuk menonaktifkannya.

## Cara Penggunaan

Untuk menjalankan algoritma penjadwalan, pastikan Anda berada di direktori root proyek (`scheduling-genetic-algorithm/`) dan virtual environment sudah aktif.

Gunakan perintah berikut:

```bash
python src/penjadwalan_genetic.py
```

Algoritma akan berjalan, menampilkan progress bar evolusi di terminal. Setelah selesai, jadwal terbaik akan ditampilkan dalam bentuk tabel dan juga disimpan ke dalam file `Jadwal_Final_Optimal.csv`.
