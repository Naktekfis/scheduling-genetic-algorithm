# PARAMETER UNTUK ALGORITMA GENETIKA
# Sesuaikan nilai-nilai di bawah ini sesuai kebutuhan.

# Ukuran populasi (jumlah kromosom/jadwal dalam satu generasi)
POPULATION_SIZE = 100

# Ukuran individu yang dipilih untuk turnamen seleksi
TOURNAMENT_SELECTION_SIZE = 3

# Jumlah maksimum generasi yang akan dijalankan oleh algoritma
MAX_GENERATION = 2000

# Jumlah kromosom/jadwal terbaik (elit) yang akan langsung dibawa ke generasi berikutnya tanpa perubahan.
NUMB_OF_ELITE_SCHEDULES = 2

# Probabilitas terjadinya crossover antara dua parent.
# Nilai antara 0.0 dan 1.0.
CROSSOVER_RATE = 0.9

# Probabilitas terjadinya mutasi pada sebuah gen dalam kromosom.
# Nilai antara 0.0 dan 1.0.
MUTATION_RATE = 0.05

# Parameter untuk Island Model
NUM_ISLANDS = 4  # Jumlah populasi yang berjalan paralel (misal: 4, 5, atau 8)
MIGRATION_INTERVAL = 10 # Setiap bbrp generasi, lakukan migrasi
MIGRATION_SIZE = 5 # Berapa individu terbaik yang akan bermigrasi dari setiap pulau (misal: 5% dari POP_SIZE)

# Parameter untuk Memetic Algorithm (Pencarian Lokal)
LOCAL_SEARCH_RATE = 0.05 # Terapkan pencarian lokal pada 10% individu terbaik di setiap pulau
LOCAL_SEARCH_ITERATIONS = 10 # Jumlah percobaan perbaikan dalam satu kali pencarian lokal

# Berhenti jika skor terbaik tidak membaik selama N generasi berturut-turut.
EARLY_STOPPING_PATIENCE = 25