# Algoritma Genetika untuk Penjadwalan Kuliah

Sebuah implementasi Algoritma Genetika (GA) untuk mencari solusi jadwal mata kuliah. Proyek ini berevolusi menjadi arsitektur hibrida yang lebih kompleks untuk menangani batasan-batasan penjadwalan secara lebih efektif. Fokus utama dari sistem ini adalah pada penjadwalan **waktu**, dan tidak lagi memperhitungkan batasan ketersediaan **ruangan**.

## Fitur

*   **Arsitektur Hibrida**: Menggabungkan **Algoritma Genetika** dengan **Island Model** (beberapa populasi paralel) dan **Memetic Algorithm** (pencarian lokal) untuk meningkatkan kualitas solusi dan menghindari konvergensi prematur.
*   **Sistem Skor Berbobot**: Menggunakan `score` untuk mengevaluasi kualitas jadwal, dengan penalti yang jauh lebih tinggi untuk *hard conflict* (pelanggaran wajib) dibandingkan *soft conflict* (pelanggaran preferensi).
*   **Konfigurasi Terpusat**: Semua parameter utama (ukuran populasi, laju mutasi, parameter Island/Memetic) diatur melalui `config/settings.py`.
*   **Input Berbasis CSV**:
    -   Aturan penjadwalan (*constraints*) dapat diaktifkan/dinonaktifkan di `data/Constraints.csv`.
    -   Data penjadwalan utama, termasuk sesi-sesi per mata kuliah dan dosen, didefinisikan di `data/Input_Update_DK_133_TF_Semester3_2025.csv`.
*   **Logika Penugasan Dosen**: Mendukung skenario "Dosen Utama" dan "Dosen Sekunder", di mana penugasan Dosen Utama lebih diprioritaskan sebagai *soft constraint*.
*   **Autopilot Early Stopping**: Algoritma secara otomatis berhenti jika skor solusi terbaik tidak menunjukkan perbaikan (stagnasi) setelah sejumlah generasi yang ditentukan di `settings.py`.

## Struktur Proyek

```
scheduling-genetic-algorithm/
├── config/
│   └── settings.py
├── data/
│   ├── Constraints.csv
│   ├── Input_Update_DK_133_TF_Semester3_2025.csv
│   ├── MeetingTime_1jam.csv
│   ├── MeetingTime_2jam.csv
│   ├── MeetingTime_4jam.csv
│   └── Ruangan.csv
├── src/
│   ├── constraints/
│   │   └── constraints_loader.py
│   ├── type/
│   │   ├── __init__.py
│   │   └── time_slot_mapper.py
│   └── penjadwalan_genetic.py
├── Jadwal_Final_Optimal...csv
├── README.md
└── requirements.txt
```

## Instalasi dan Penggunaan

**1. Persiapan Lingkungan**
```bash
# Clone repository
git clone https://github.com/Naktekfis/scheduling-genetic-algorithm
cd scheduling-genetic-algorithm

# Buat dan aktifkan virtual environment
python -m venv venv
source venv/bin/activate  # atau .\venv\Scripts\activate di Windows
```

**2. Instal Dependensi**
```bash
pip install -r requirements.txt
```

**3. Konfigurasi (Opsional)**
Sesuaikan parameter di `config/settings.py` atau `data/Constraints.csv` sesuai kebutuhan sebelum menjalankan.

**4. Menjalankan Algoritma**
```bash
python src/penjadwalan_genetic.py
```
Proses akan berjalan di terminal. Hasil akhir akan ditampilkan di konsol dan disimpan dalam file `.csv` di direktori utama proyek.

## Catatan Implementasi
- Kualitas dan kecepatan konvergensi sangat dipengaruhi oleh parameter di `config/settings.py`. Pengaturan saat ini adalah kompromi antara kecepatan dan pencarian solusi yang mendalam.
- Sistem ini dirancang untuk menjadi "autopilot", berhenti secara otomatis ketika solusi sudah dianggap cukup baik atau tidak lagi mengalami kemajuan.````