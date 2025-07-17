import csv
import prettytable
import random
import pandas as pd
import time
import os
from tqdm import tqdm
from constraints.constraints_loader import ConstraintLoader

constraints_loader = ConstraintLoader('D:/Coding/Algoritma Genetika/scheduling-genetic-algorithm/data/Constraints.csv')

# KONFIGURASI DAN PARAMETER UTAMA
# Mengatur direktori kerja ke lokasi file script ini agar file CSV mudah ditemukan.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

print("--- Sistem Cerdas Penjadwalan Kuliah Berbasis Algoritma Genetika ---")
print("Silakan masukkan parameter untuk Algoritma Genetika:\n")

# Parameter Algoritma Genetika (diambil dari input pengguna)
POPULATION_SIZE = int(input("Ukuran Populasi (contoh: 10, 50, 100): "))
TOURNAMENT_SELECTION_SIZE = int(input("Ukuran Seleksi Turnamen (contoh: 4, 32): "))
MAX_GENERATION = int(input("Jumlah Generasi Maksimum (contoh: 9000, 2000, 1000): "))
NUMB_OF_ELITE_SCHEDULES = int(input("Jumlah Kromosom Elit (contoh: 1): "))
CROSSOVER_RATE = float(input("Probabilitas Crossover (contoh: 0.1, 0.5, 0.9): "))
MUTATION_RATE = float(input("Probabilitas Mutasi (contoh: 0.1, 0.5, 0.9): "))

# DEFINISI KELAS-KELAS DATA (ENTITAS)

class Data:
    """
    Kelas ini bertanggung jawab untuk memuat semua data awal dari file CSV.
    Data ini bersifat statis dan menjadi sumber informasi untuk pembuatan jadwal.
    """
    # Memuat data dari file CSV sekali saja saat kelas didefinisikan
    try:
        ROOMS = pd.read_csv(os.path.join(DATA_DIR, 'Ruangan.csv'), header=None).values.tolist()
        MEETING_TIMES_4JAM = pd.read_csv(
            os.path.join(DATA_DIR, 'MeetingTime_4jam.csv'), usecols=['Kode','Jadwal','Group1','Blocked'],
            converters={"Group1":int,"Blocked":int}
        ).values.tolist()
        MEETING_TIMES_2JAM = pd.read_csv(
            os.path.join(DATA_DIR, 'MeetingTime_2jam.csv'), usecols=['Kode','Jadwal','Group1','Group2','Group3','Blocked'],
            converters={"Group1":int,"Group2":int,"Group3":int,"Blocked":int}
        ).values.tolist()
        MEETING_TIMES_1JAM = pd.read_csv(
            os.path.join(DATA_DIR, 'MeetingTime_1jam.csv'), usecols=['Kode','Jadwal','Group1','Group2','Group3','Blocked','WaktuAkhir'],
            converters={"Group1":int,"Group2":int,"Group3":int,"Blocked":int,"WaktuAkhir":int}
        ).values.tolist()
        COURSE_DATA = pd.read_csv(os.path.join(DATA_DIR, 'DataPenjadwalan.csv'))
        INSTRUCTORS = COURSE_DATA[['InisialDosen','NamaDosen']].drop_duplicates().values.tolist()
    except FileNotFoundError as e:
        print(f"Error: File tidak ditemukan - {e}. Pastikan semua file CSV ada di direktori yang sama.")
        exit()


    def __init__(self):
        self._rooms = []
        self._meeting_times_4jam = []
        self._meeting_times_2jam = []
        self._meeting_times_1jam = []
        self._instructors = []
        self._courses = []
        
        # Mengubah data mentah menjadi objek
        for num, cap in self.ROOMS:
            self._rooms.append(Room(num, int(cap)))
            
        for mt in self.MEETING_TIMES_4JAM:
            self._meeting_times_4jam.append(MeetingTime(mt[0], mt[1], sks=4, groups={'g1': mt[2]}, blocked=mt[3]))
            
        for mt in self.MEETING_TIMES_2JAM:
            self._meeting_times_2jam.append(MeetingTime(mt[0], mt[1], sks=2, groups={'g1': mt[2], 'g2': mt[3], 'g3': mt[4]}, blocked=mt[5]))
            
        for mt in self.MEETING_TIMES_1JAM:
            self._meeting_times_1jam.append(MeetingTime(mt[0], mt[1], sks=1, groups={'g1': mt[2], 'g2': mt[3], 'g3': mt[4]}, blocked=mt[5], is_edge_time=mt[6]))

        # Membuat dictionary untuk mapping inisial dosen ke objek Instructor
        instructor_map = {ins[0]: Instructor(ins[0], ins[1]) for ins in self.INSTRUCTORS}
        self._instructors = list(instructor_map.values())

        # Membuat objek Course dari data yang dibaca
        for _, row in self.COURSE_DATA.iterrows():
            # Temukan objek dosen yang sesuai
            dosen_obj = [instructor_map.get(row['InisialDosen'])]
            self._courses.append(Course(row, dosen_obj))

        self._number_of_classes = len(self._courses)

    # Getter methods
    def get_rooms(self): return self._rooms
    def get_instructors(self): return self._instructors
    def get_courses(self): return self._courses
    def get_meeting_times(self, sks):
        if sks == 4: return self._meeting_times_4jam
        if sks == 2: return self._meeting_times_2jam
        if sks == 1: return self._meeting_times_1jam
        return []
    def get_number_of_classes(self): return self._number_of_classes

class Course:
    """Mewakili satu mata kuliah yang akan dijadwalkan."""
    def __init__(self, data_row, instructors):
        self._data = data_row
        self._instructors = instructors

    def get_number(self): return self._data['KodeMatkul']
    def get_name(self): return self._data['NamaMatkul']
    def get_instructors(self): return self._instructors
    def get_sks(self): return self._data['sks']
    def get_max_students(self): return self._data['KuotaMatkul']
    def get_student_group(self): return (self._data['Tingkat'], self._data['Kelas'])
    # Batasan & Properti Khusus
    def is_fixed(self): return self._data['jadwalfix'] == 1
    def is_difficult(self): return self._data['MatkulSusah'] == 1
    def get_type(self): return self._data['Tipe'] # 1: wajib, 2: pilihan, 3: praktikum
    # Getter untuk jadwal yang sudah fix (jika ada)
    def get_fixed_schedule(self, sks):
        if sks == 4: return self._data['jadwal4jam']
        if sks == 2: return self._data['jadwal2jam']
        if sks == 1: return self._data['jadwal1jam']
    def __str__(self): return f"{self.get_name()} ({self.get_number()})"

class Instructor:
    """Mewakili seorang dosen."""
    def __init__(self, id, name):
        self._id = id
        self._name = name
    def get_id(self): return self._id
    def get_name(self): return self._name
    def __str__(self): return self._name

class Room:
    """Mewakili satu ruangan kelas."""
    def __init__(self, number, seating_capacity):
        self._number = number
        self._seating_capacity = seating_capacity
    def get_number(self): return self._number
    def get_seating_capacity(self): return self._seating_capacity
    def __str__(self): return str(self._number)

class MeetingTime:
    """Mewakili satu slot waktu."""
    def __init__(self, id, time, sks, groups, blocked, is_edge_time=0):
        self._id = id
        self._time = time
        self._sks = sks 
        self._groups = groups # Dictionary
        self._is_blocked = (blocked == 1)
        self._is_edge_time = (is_edge_time == 1) # Untuk batasan lunak
    def get_id(self): return self._id
    def get_time(self): return self._time
    def get_group(self, key): return self._groups.get(key)
    def is_blocked(self): return self._is_blocked
    def is_edge_time(self): return self._is_edge_time
    def get_sks(self): return self._sks
    def __str__(self): return self._time

class Class:
    """Mewakili satu sesi kelas spesifik (gabungan Course, Room, Dosen, Waktu)."""
    def __init__(self, id, course):
        self._id = id
        self._course = course
        self._instructor = None
        self._meeting_time_1 = None # Untuk 1 SKS atau bagian 1 SKS dari 3 SKS
        self._meeting_time_2 = None # Untuk 2 SKS atau bagian 2 SKS dari 3 SKS
        self._meeting_time_4 = None # Untuk 4 SKS
        self._room = None
    
    # Getters
    def get_id(self): return self._id
    def get_course(self): return self._course
    def get_instructor(self): return self._instructor
    def get_room(self): return self._room
    def get_meeting_time(self, sks_part):
        if sks_part == 1: return self._meeting_time_1
        if sks_part == 2: return self._meeting_time_2
        if sks_part == 4: return self._meeting_time_4
        return None
        
    # Setters
    def set_instructor(self, instructor): self._instructor = instructor
    def set_room(self, room): self._room = room
    def set_meeting_time(self, sks_part, meeting_time):
        if sks_part == 1: self._meeting_time_1 = meeting_time
        elif sks_part == 2: self._meeting_time_2 = meeting_time
        elif sks_part == 4: self._meeting_time_4 = meeting_time

    def __str__(self):
        return (f"Course: {self._course.get_number()}, "
                f"Room: {self._room}, "
                f"Dosen: {self._instructor.get_id()}, "
                f"Waktu1: {self._meeting_time_1}, "
                f"Waktu2: {self._meeting_time_2}, "
                f"Waktu4: {self._meeting_time_4}")

# KELAS UTAMA UNTUK ALGORITMA GENETIKA

class Schedule:
    def __init__(self):
        self._data = data
        self._classes = []
        self._num_of_conflicts = 0
        self._fitness = -1
        self._is_fitness_changed = True

    def initialize(self):
        """Inisialisasi jadwal dengan alokasi acak untuk setiap kelas."""
        courses = self._data.get_courses()
        for i, course in enumerate(courses):
            new_class = Class(i, course)
            new_class.set_instructor(course.get_instructors()[0])
            if course.get_sks() == 4:
                new_class.set_meeting_time(4, random.choice(self._data.get_meeting_times(4)))
                new_class.set_room(Room("Lab Komputer", 45))
            else:
                new_class.set_room(random.choice(self._data.get_rooms()))
                if course.get_sks() == 3:
                    new_class.set_meeting_time(2, random.choice(self._data.get_meeting_times(2)))
                    new_class.set_meeting_time(1, random.choice(self._data.get_meeting_times(1)))
                elif course.get_sks() == 2:
                    new_class.set_meeting_time(2, random.choice(self._data.get_meeting_times(2)))
                elif course.get_sks() == 1:
                    new_class.set_meeting_time(1, random.choice(self._data.get_meeting_times(1)))
            self._classes.append(new_class)
        return self

    def calculate_fitness(self):
        hard_conflicts = 0
        soft_conflicts = 0

        # Struktur data untuk tracking jadwal
        dosen_times = {}
        room_times = {}
        group_times = {}

        for c in self._classes:
            course = c.get_course()
            sks = course.get_sks()
            instructor_id = c.get_instructor().get_id()
            room_num = c.get_room().get_number()
            group = course.get_student_group()

            # Ambil semua slot waktu yang dipakai kelas ini
            times = [c.get_meeting_time(s) for s in [1,2,4] if c.get_meeting_time(s) is not None]

            # K2: Kapasitas ruangan
            if constraints_loader.is_enabled('K2'):
                if course.get_type() != 3 and c.get_room().get_seating_capacity() < course.get_max_students():
                    hard_conflicts += 1

            # K6, K7, K_internal, L1: Cek per kelas
            if sks == 3:
                if constraints_loader.is_enabled('K_internal'):
                    if c.get_meeting_time(2).get_group('g1') == c.get_meeting_time(1).get_group('g1'):
                        hard_conflicts += 1
                if constraints_loader.is_enabled('K6') or constraints_loader.is_enabled('K7'):
                    if c.get_meeting_time(2).is_blocked() or c.get_meeting_time(1).is_blocked():
                        hard_conflicts += 1
                if constraints_loader.is_enabled('L1'):
                    if c.get_meeting_time(1).is_edge_time():
                        soft_conflicts += 1
            elif sks == 2:
                if constraints_loader.is_enabled('K6'):
                    if c.get_meeting_time(2).is_blocked():
                        hard_conflicts += 1
            elif sks == 4:
                if constraints_loader.is_enabled('K6'):
                    if c.get_meeting_time(4).is_blocked():
                        hard_conflicts += 1

            # Cek bentrok dosen, ruangan, kelompok mahasiswa
            for t in times:
                # K3: Dosen tidak boleh bentrok
                if constraints_loader.is_enabled('K3'):
                    key = (instructor_id, t.get_id())
                    if key in dosen_times:
                        hard_conflicts += 1
                    else:
                        dosen_times[key] = c

                # K_internal: Ruangan tidak boleh bentrok
                if constraints_loader.is_enabled('K_internal'):
                    key = (room_num, t.get_id())
                    if key in room_times:
                        hard_conflicts += 1
                    else:
                        room_times[key] = c

                # K1: Kelompok mahasiswa tidak boleh bentrok
                if constraints_loader.is_enabled('K1'):
                    key = (group, t.get_id())
                    if key in group_times:
                        hard_conflicts += 1
                    else:
                        group_times[key] = c

        # Loop kedua untuk constraint yang butuh dua kelas sekaligus (K4, K5, L2)
        for i in range(len(self._classes)):
            c1 = self._classes[i]
            for j in range(i + 1, len(self._classes)):
                c2 = self._classes[j]
                if self.check_time_overlap(c1, c2):
                    # K4
                    if constraints_loader.is_enabled('K4'):
                        c1_course, c2_course = c1.get_course(), c2.get_course()
                        if (c1_course.get_type() == 3 and c1_course.get_student_group()[0] == 2 and c2_course.get_student_group()[0] == 3) or \
                           (c2_course.get_type() == 3 and c2_course.get_student_group()[0] == 2 and c1_course.get_student_group()[0] == 3):
                            hard_conflicts += 1
                    # K5
                    if constraints_loader.is_enabled('K5'):
                        c1_course, c2_course = c1.get_course(), c2.get_course()
                        if c1_course.get_student_group()[0] == 4 and c2_course.get_student_group()[0] == 4 and c1_course.get_type() != c2_course.get_type():
                            hard_conflicts += 1
                    # L2
                    if constraints_loader.is_enabled('L2'):
                        c1_course, c2_course = c1.get_course(), c2.get_course()
                        if (c1_course.is_difficult() and c1_course.get_student_group()[0] == 2 and c2_course.get_student_group()[0] == 3) or \
                           (c2_course.is_difficult() and c2_course.get_student_group()[0] == 2 and c1_course.get_student_group()[0] == 3):
                            soft_conflicts += 1

        self._num_of_conflicts = hard_conflicts + soft_conflicts
        return 1 / (self._num_of_conflicts + 1)
    
    def check_time_overlap(self, c1, c2):
        """Helper function untuk memeriksa apakah dua kelas (c1, c2) memiliki waktu yang tumpang tindih."""
        # Kumpulkan semua slot waktu untuk setiap kelas
        c1_times = [c1.get_meeting_time(sks) for sks in [1, 2, 4] if c1.get_meeting_time(sks) is not None]
        c2_times = [c2.get_meeting_time(sks) for sks in [1, 2, 4] if c2.get_meeting_time(sks) is not None]

        for t1 in c1_times:
            for t2 in c2_times:
                # Pengecekan overlap paling dasar: ID waktu sama persis
                if t1.get_id() == t2.get_id(): return True
                
                # Pengecekan overlap berdasarkan 'group'
                # Group ini menandakan slot-slot yang saling tumpang tindih.
                # Contoh: Senin 07-09 (2jam) akan overlap dengan Senin 07-11 (4jam)
                if t1.get_sks() == 4 or t2.get_sks() == 4: # Jika ada slot 4 jam
                    if t1.get_group('g1') == t2.get_group('g3'): return True
                    if t2.get_group('g1') == t1.get_group('g3'): return True
                if t1.get_sks() != 4 and t2.get_sks() != 4: # Jika hanya slot 1 dan 2 jam
                    if t1.get_group('g2') == t2.get_group('g2'): return True
        return False

    def get_fitness(self):
        if self._is_fitness_changed:
            self._fitness = self.calculate_fitness()
            self._is_fitness_changed = False
        return self._fitness
    
    def get_classes(self): 
        self._is_fitness_changed = True
        return self._classes
    
    def get_num_of_conflicts(self): return self._num_of_conflicts

class Population:
    """Mewakili kumpulan individu (Schedule) pada satu generasi."""
    def __init__(self, size):
        self._size = size
        self._schedules = [Schedule().initialize() for _ in range(size)]

    def get_schedules(self): return self._schedules

class GeneticAlgorithm:
    """Kelas yang menjalankan proses evolusi."""
    
    def evolve(self, population):
        """Satu siklus evolusi: crossover diikuti mutasi."""
        return self._mutate_population(self._crossover_population(population))

    def _crossover_population(self, pop):
        """Melakukan crossover pada populasi untuk menciptakan generasi baru."""
        crossover_pop = Population(0)
        
        # Elitisme: Bawa individu terbaik langsung ke generasi berikutnya
        for i in range(NUMB_OF_ELITE_SCHEDULES):
            crossover_pop.get_schedules().append(pop.get_schedules()[i])
            
        # Crossover sisa populasi
        for _ in range(NUMB_OF_ELITE_SCHEDULES, POPULATION_SIZE):
            # Pilih 2 parent menggunakan seleksi turnamen
            parent1 = self._tournament_selection(pop).get_schedules()[0]
            parent2 = self._tournament_selection(pop).get_schedules()[0]
            
            # Lakukan crossover dan tambahkan anak ke populasi baru
            child = self._crossover_schedule(parent1, parent2)
            crossover_pop.get_schedules().append(child)
            
        return crossover_pop

    def _mutate_population(self, population):
        """Melakukan mutasi pada setiap individu di populasi (kecuali kaum elit)."""
        for i in range(NUMB_OF_ELITE_SCHEDULES, POPULATION_SIZE):
            self._mutate_schedule(population.get_schedules()[i])
        return population

    def _crossover_schedule(self, parent1, parent2):
        """
        Melakukan 'single-point crossover' pada dua jadwal (parent).
        Membuat satu jadwal baru (child) dengan mengambil gen dari kedua parent.
        """
        child_schedule = Schedule().initialize()
        for i in range(len(child_schedule.get_classes())):
            # Jika random number < Crossover Rate, ambil gen dari parent 1, jika tidak, dari parent 2
            if random.random() < CROSSOVER_RATE:
                child_schedule.get_classes()[i] = parent1.get_classes()[i]
            else:
                child_schedule.get_classes()[i] = parent2.get_classes()[i]
        return child_schedule

    def _mutate_schedule(self, schedule_to_mutate):
        """
        Melakukan mutasi pada satu jadwal.
        Mengganti beberapa gen (alokasi kelas) dengan alokasi acak baru.
        """
        temp_schedule = Schedule().initialize()
        for i in range(len(schedule_to_mutate.get_classes())):
             # Jika random number < Mutation Rate, ganti gen ini dengan gen acak baru
            if random.random() < MUTATION_RATE:
                schedule_to_mutate.get_classes()[i] = temp_schedule.get_classes()[i]
        return schedule_to_mutate

    def _tournament_selection(self, pop):
        """
        Memilih individu terbaik dari 'turnamen'.
        Sebuah sub-set acak dari populasi dipilih, dan yang terbaik dari sub-set itu menang.
        """
        tournament_pop = Population(0)
        for _ in range(TOURNAMENT_SELECTION_SIZE):
            tournament_pop.get_schedules().append(random.choice(pop.get_schedules()))
            
        # Urutkan peserta turnamen berdasarkan fitness dan kembalikan yang terbaik
        tournament_pop.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
        return tournament_pop

class DisplayManager:
    """Kelas untuk menampilkan hasil penjadwalan dalam format tabel."""
    def print_schedule_as_table(self, schedule, generation_number, elapsed_time):
        classes = schedule.get_classes()
        print("\n======================================================================================")
        print(f" JADWAL KULIAH TERBAIK (Generasi #{generation_number})")
        print(f" > Fitness: {schedule.get_fitness():.5f}")
        print(f" > Jumlah Konflik: {schedule.get_num_of_conflicts()}")
        print(f" > Waktu Komputasi: {elapsed_time:.2f} detik")
        print("======================================================================================")

        table = prettytable.PrettyTable([
            'No', 'Mata Kuliah (Kode, SKS, Kuota)', 'Kelompok', 'Ruangan (Kap.)', 'Dosen', 'Jadwal'
        ])
        
        for i, current_class in enumerate(classes):
            course = current_class.get_course()
            sks = course.get_sks()
            
            # Gabungkan jadwal berdasarkan SKS
            if sks == 3:
                jadwal_str = (f"{current_class.get_meeting_time(2).get_time()} & "
                              f"{current_class.get_meeting_time(1).get_time()}")
            elif sks == 2:
                jadwal_str = current_class.get_meeting_time(2).get_time()
            elif sks == 4:
                jadwal_str = current_class.get_meeting_time(4).get_time()
            else: # 1 SKS
                jadwal_str = current_class.get_meeting_time(1).get_time()

            table.add_row([
                str(i + 1),
                f"{course.get_name()}\n({course.get_number()}, {sks} SKS, {course.get_max_students()} mhs)",
                f"Tingkat {course.get_student_group()[0]} - Kelas {course.get_student_group()[1]}",
                f"{current_class.get_room().get_number()} ({current_class.get_room().get_seating_capacity()})",
                current_class.get_instructor().get_name(),
                jadwal_str
            ])
        print(table)

        # Simpan ke file CSV
        df = pd.DataFrame(table.rows, columns=table.field_names)
        df.to_csv("Jadwal_Final_Optimal.csv", index=False)
        print("\nJadwal optimal telah disimpan ke file 'Jadwal_Final_Optimal.csv'")


# MAIN EXECUTION BLOCK
if __name__ == '__main__':
    start_time = time.time()
    
    data = Data()
    display_manager = DisplayManager()
    
    # 1. Inisialisasi Populasi Awal
    print("\nMembuat populasi awal...")
    population = Population(POPULATION_SIZE)
    
    # Urutkan populasi awal dan cetak jadwal terbaik dari generasi 0
    population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
    best_schedule = population.get_schedules()[0]

    # 2. Proses Evolusi
    print(f"\nMemulai proses evolusi untuk {MAX_GENERATION} generasi...")
    genetic_algorithm = GeneticAlgorithm()
    generation_num = 0

    with tqdm(total=MAX_GENERATION, desc="Evolusi Generasi") as pbar:
        for i in range(MAX_GENERATION):
            generation_num = i + 1
            
            # Evolve the population
            population = genetic_algorithm.evolve(population)
            
            # Urutkan populasi baru
            population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
            
            # Cek kondisi berhenti
            best_schedule = population.get_schedules()[0]
            pbar.set_postfix({"Fitness Terbaik": f"{best_schedule.get_fitness():.4f}", "Konflik": best_schedule.get_num_of_conflicts()})
            pbar.update(1)

            if best_schedule.get_fitness() == 1.0:
                pbar.n = MAX_GENERATION # Complete the progress bar
                pbar.refresh()
                print(f"\n\nSolusi optimal (fitness = 1.0) ditemukan pada generasi ke-{generation_num}!")
                break
    
    # 3. Tampilkan Hasil Akhir
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    display_manager.print_schedule_as_table(best_schedule, generation_num, elapsed_time)