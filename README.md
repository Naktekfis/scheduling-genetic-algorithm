# Algoritma Genetika Penjadwalan

Proyek ini mengimplementasikan algoritma penjadwalan berbasis teknik algoritma genetika. Tujuan utamanya adalah menghasilkan jadwal kuliah yang optimal dengan tetap mematuhi berbagai aturan (constraint) yang berlaku.

## Struktur Proyek

Struktur folder proyek adalah sebagai berikut:

```
scheduling-genetic-algorithm
├── src
│   ├── penjadwalan_genetic.py           # Algoritma penjadwalan utama
│   ├── penjadwalan_genetic_adaptif.py   # Algoritma penjadwalan adaptif (parameternya berubah setiap waktu)
│   ├── constraints
│   │   └── constraints_loader.py        # Loader untuk constraint yang bisa dikustomisasi dari CSV
│   └── types
│       └── __init__.py                  # Tipe data dan struktur khusus
├── data
│   ├── DataPenjadwalan.csv               # Data mata kuliah
│   ├── Ruangan.csv                       # Data ruangan yang tersedia
│   ├── MeetingTime_4jam.csv              # Slot waktu untuk kelas 4 jam
│   ├── MeetingTime_2jam.csv              # Slot waktu untuk kelas 2 jam
│   ├── MeetingTime_1jam.csv              # Slot waktu untuk kelas 1 jam
│   └── Constraints.csv                    # Daftar aturan penjadwalan yang bisa dikustomisasi
├── requirements.txt                       # Daftar dependensi proyek
└── README.md                              # Dokumentasi proyek
```

## Langkah Instalasi

1. **Clone repository**:
   ```
   git clone <repository-url>
   cd scheduling-genetic-algorithm
   ```

2. **Instal dependensi**:
   Pastikan Python sudah terpasang, lalu jalankan:
   ```
   pip install -r requirements.txt
   ```

3. **Siapkan file data**:
   Pastikan semua file CSV di folder `data` sudah terisi dan diformat dengan benar sesuai kebutuhan algoritma penjadwalan.

## Cara Penggunaan

Untuk menjalankan algoritma penjadwalan, gunakan perintah berikut:
```
python src/penjadwalan_genetic2.py
```

Ikuti instruksi yang muncul untuk memasukkan parameter algoritma genetika seperti ukuran populasi, ukuran seleksi turnamen, dan tingkat mutasi.

## Kustomisasi Aturan Penjadwalan

Aturan penjadwalan dapat diubah dengan mengedit file `data/Constraints.csv`. Dengan cara ini, pengguna dapat menyesuaikan aturan penjadwalan tanpa perlu mengubah kode program.
