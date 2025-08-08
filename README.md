# Implementasi Algoritma Genetika untuk Penjadwalan Kuliah

Proyek ini adalah sebuah implementasi Algoritma Genetika (GA) yang bertujuan untuk mencari solusi penjadwalan mata kuliah. Sistem ini mencoba menyeimbangkan berbagai batasan (*constraints*) untuk menghasilkan jadwal yang fungsional dan memiliki sesedikit mungkin konflik.

## Fungsionalitas Inti

-   **Pencarian Berbasis GA**: Menggunakan pendekatan evolusioner (seleksi, crossover, mutasi) untuk menavigasi ruang pencarian jadwal yang sangat besar.
-   **Sistem Penilaian Konflik**: Kualitas sebuah jadwal diukur berdasarkan sistem skor. Pelanggaran aturan dibagi menjadi dua kategori:
    -   **Hard Constraints**: Pelanggaran fatal yang harus dihilangkan (misal: bentrok jadwal dosen). Diberi bobot penalti yang sangat tinggi.
    -   **Soft Constraints**: Pelanggaran preferensi yang sebaiknya dihindari (misal: dosen mengajar lebih dari 4 hari). Diberi bobot penalti rendah.
-   **Berhenti dengan Ambang Batas**: Algoritma dapat diatur untuk berhenti lebih awal jika ditemukan solusi yang sudah memenuhi semua *hard constraint* dan memiliki jumlah skor dari *soft constraint* di bawah ambang batas yang ditentukan.
-   **Konfigurasi Eksternal**:
    -   Parameter GA (ukuran populasi, laju mutasi, dll.) diatur di `config/settings.py`.
    -   Aturan penjadwalan dapat diaktifkan atau dinonaktifkan melalui file `data/Constraints.csv`.
-   **Penanganan Logika Penjadwalan**:
    -   Mendukung penugasan dosen dari beberapa alternatif yang valid untuk satu mata kuliah.
    -   Menggunakan operator Crossover (swap-based) yang dirancang untuk menjaga integritas jadwal (tidak ada kelas yang hilang atau terduplikasi).

## Struktur Proyek

Proyek ini diorganisir untuk memisahkan logika, data, dan konfigurasi.

```
scheduling-genetic-algorithm/
├── config/
│   └── settings.py               # Pengaturan parameter utama GA.
├── data/
│   ├── Constraints.csv           # Daftar aturan penjadwalan.
│   ├── DK_133_TF_Semester3_2025.csv # Data sumber mata kuliah, dosen, dll.
│   ├── MeetingTime_*.csv         # Definisi slot waktu.
│   └── Ruangan.csv               # Daftar ruangan dan kapasitas.
├── src/
│   ├── penjadwalan_genetic.py    # Skrip eksekusi utama.
│   └── types/
│       └── __init__.py           # Definisi dataclass (Course, Room, dll.).
├── .gitignore
├── requirements.txt
└── README.md
```

## Instalasi dan Penggunaan

**1. Environment**

Disarankan untuk menggunakan virtual environment.

```bash
# Clone repository
git clone https://github.com/Naktekfis/scheduling-genetic-algorithm/tree/master
cd scheduling-genetic-algorithm

# Buat dan aktifkan venv
python -m venv venv
source venv/bin/activate  # atau .\venv\Scripts\activate di Windows
```

**2. Instal Dependensi**

```bash
pip install -r requirements.txt
```

**3. Konfigurasi (Opsional)**

-   Sesuaikan parameter seperti `POPULATION_SIZE` atau `SCORE_THRESHOLD` di `config/settings.py`.
-   Atur `enabled` (1 atau 0) untuk setiap aturan di `data/Constraints.csv`.

**4. Menjalankan Algoritma**

Pastikan Anda berada di direktori root proyek dan virtual environment aktif.

```bash
python src/penjadwalan_genetic.py
```

Proses akan berjalan di terminal, menampilkan progres skor dan rincian konflik. Hasil akhir akan ditampilkan di konsol dan disimpan dalam file `Jadwal_Final_Optimal3.csv`.

## Catatan Implementasi

-   **Kualitas Solusi**: Kualitas jadwal yang dihasilkan sangat bergantung pada kualitas data input dan konfigurasi constraint yang digunakan. Algoritma ini bertujuan untuk menemukan solusi "cukup baik" yang meminimalkan konflik, bukan menjamin solusi "sempurna" tanpa konflik sama sekali.
-   **Performa**: Operator crossover telah dioptimalkan untuk kecepatan. Namun, ukuran populasi yang besar dan jumlah generasi yang tinggi secara alami akan meningkatkan waktu komputasi.
-   **Keterbatasan**: Sistem saat ini belum menangani beberapa skenario yang sangat kompleks seperti dependensi antar mata kuliah (prasyarat) atau optimasi jarak antar gedung. Penambahan fitur tersebut memerlukan modifikasi pada struktur data dan fungsi fitness.
