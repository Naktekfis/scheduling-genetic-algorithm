# PARAMETER UNTUK ALGORITMA GENETIKA
# Sesuaikan nilai-nilai di bawah ini sesuai kebutuhan.

# Ukuran populasi (jumlah kromosom/jadwal dalam satu generasi)
POPULATION_SIZE = 110

# Ukuran individu yang dipilih untuk turnamen seleksi
TOURNAMENT_SELECTION_SIZE = 32

# Jumlah maksimum generasi yang akan dijalankan oleh algoritma
MAX_GENERATION = 2000

# Jumlah kromosom/jadwal terbaik (elit) yang akan langsung dibawa ke generasi berikutnya tanpa perubahan.
NUMB_OF_ELITE_SCHEDULES = 1

# Probabilitas terjadinya crossover antara dua parent.
# Nilai antara 0.0 dan 1.0.
CROSSOVER_RATE = 0.5

# Probabilitas terjadinya mutasi pada sebuah gen dalam kromosom.
# Nilai antara 0.0 dan 1.0.
MUTATION_RATE = 0.1