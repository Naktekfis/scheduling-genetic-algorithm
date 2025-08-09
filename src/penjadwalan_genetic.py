import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import csv
import prettytable
import random
import pandas as pd
import time
import re
import copy
import numpy as np
from tqdm import tqdm
from src.type.time_slot_mapper import TimeSlotMapper
from src.constraints.constraints_loader import ConstraintLoader
from config import settings
from src.type import Room, Instructor, MeetingTime, Course, Class


# KONFIGURASI DAN PARAMETER UTAMA
DATA_DIR = os.path.join(BASE_DIR, 'data')

constraints_path = os.path.join(DATA_DIR, 'Constraints.csv')
constraints_loader = ConstraintLoader(constraints_path)

print("--- Sistem Cerdas Penjadwalan Kuliah Berbasis Algoritma Genetika ---")

# Parameter Algoritma Genetika (diambil dari config)
POPULATION_SIZE = settings.POPULATION_SIZE
TOURNAMENT_SELECTION_SIZE = settings.TOURNAMENT_SELECTION_SIZE
MAX_GENERATION = settings.MAX_GENERATION
NUMB_OF_ELITE_SCHEDULES = settings.NUMB_OF_ELITE_SCHEDULES
CROSSOVER_RATE = settings.CROSSOVER_RATE
MUTATION_RATE = settings.MUTATION_RATE

# LOAD KELAS DATA
class Data:
    try:
        DATA_PENJADWALAN_FILE = 'DK_133_TF_Semester3_2025.csv'
        
        # Memuat semua data sumber di awal
        ROOMS_DF = pd.read_csv(os.path.join(DATA_DIR, 'Ruangan.csv'), header=None)
        MEETING_TIMES_4JAM_DF = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_4jam.csv'), usecols=['Kode','Jadwal','Group1','Blocked'], converters={"Group1":int,"Blocked":int})
        MEETING_TIMES_2JAM_DF = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_2jam.csv'), usecols=['Kode','Jadwal','Group1','Group2','Group3','Blocked'], converters={"Group1":int,"Group2":int,"Group3":int,"Blocked":int})
        MEETING_TIMES_1JAM_DF = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_1jam.csv'), usecols=['Kode','Jadwal','Group1','Group2','Group3','Blocked','WaktuAkhir'], converters={"Group1":int,"Group2":int,"Group3":int,"Blocked":int,"WaktuAkhir":int})
        
        if not os.path.exists(os.path.join(DATA_DIR, DATA_PENJADWALAN_FILE)):
             raise FileNotFoundError(f"File '{DATA_PENJADWALAN_FILE}' tidak ditemukan di folder 'data/'.")

        # Membaca data utama, menganggap 0 sebagai nilai kosong (NaN)
        COURSE_DATA = pd.read_csv(
            os.path.join(DATA_DIR, DATA_PENJADWALAN_FILE),
            na_values=['0', 0] 
        )
        
    except FileNotFoundError as e:
        print(f"Error: File tidak ditemukan - {e}")
        sys.exit()
    except Exception as e:
        print(f"Terjadi error saat memuat data awal: {e}")
        sys.exit()

    def __init__(self):
        self._rooms, self._meeting_times_4jam, self._meeting_times_2jam, self._meeting_times_1jam, self._instructors, self._courses = [], [], [], [], [], []
        
        # Muat Ruangan & Waktu Pertemuan dari DataFrame
        for _, row in self.ROOMS_DF.iterrows(): self._rooms.append(Room(number=str(row[0]), seating_capacity=int(row[1])))
        for _, mt in self.MEETING_TIMES_4JAM_DF.iterrows(): self._meeting_times_4jam.append(MeetingTime(id=str(mt['Kode']), time=str(mt['Jadwal']), sks=4, groups={'g1': int(mt['Group1'])}, is_blocked=(int(mt['Blocked'])==1), is_edge_time=False))
        for _, mt in self.MEETING_TIMES_2JAM_DF.iterrows(): self._meeting_times_2jam.append(MeetingTime(id=str(mt['Kode']), time=str(mt['Jadwal']), sks=2, groups={'g1': int(mt['Group1']), 'g2': int(mt['Group2']), 'g3': int(mt['Group3'])}, is_blocked=(int(mt['Blocked'])==1), is_edge_time=False))
        for _, mt in self.MEETING_TIMES_1JAM_DF.iterrows(): self._meeting_times_1jam.append(MeetingTime(id=str(mt['Kode']), time=str(mt['Jadwal']), sks=1, groups={'g1': int(mt['Group1']), 'g2': int(mt['Group2']), 'g3': int(mt['Group3'])}, is_blocked=(int(mt['Blocked'])==1), is_edge_time=(int(mt['WaktuAkhir'])==1)))
        
        # Proses Dosen Unik dari Data
        instructor_map = {}
        # Regex untuk membersihkan nama dosen dari info SKS "(... SKS)"
        name_cleaner_pattern = re.compile(r"\s*\([\d.]+\s*SKS\)")

        for _, row in self.COURSE_DATA.iterrows():
            raw_initials = str(row['InisialDosen']).strip()
            raw_names_with_sks = str(row['NamaDosen']).strip()
            
            initials = [i.strip() for i in re.split(r'[,;\n]', raw_initials) if i.strip()]
            names_with_sks_list = [n.strip() for n in raw_names_with_sks.split('\n') if n.strip()]

            if len(initials) == len(names_with_sks_list):
                for i in range(len(initials)):
                    initial, name_sks_str = initials[i], names_with_sks_list[i]
                    if initial not in instructor_map:
                        # Hapus bagian "(... SKS)" dari nama untuk mendapatkan nama bersih
                        clean_name = name_cleaner_pattern.sub("", name_sks_str).strip()
                        instructor_map[initial] = Instructor(id=initial, name=clean_name)
        
        self._instructors = list(instructor_map.values())
        
        # Proses Mata Kuliah (Course) dan hubungkan dengan Dosen
        for _, row in self.COURSE_DATA.iterrows():
            raw_initials = str(row['InisialDosen']).strip()
            initials_for_this_course = [i.strip() for i in re.split(r'[,;\n]', raw_initials) if i.strip()]
            
            # Buat list objek dosen alternatif untuk mata kuliah ini
            dosen_objects = [instructor_map[initial] for initial in initials_for_this_course if initial in instructor_map]
            
            if not dosen_objects: continue # Lewati jika mata kuliah tidak punya dosen
            
            self._courses.append(Course(
                number=row['KodeMatkul'], name=row['NamaMatkul'], sks=int(row['sks']), 
                instructors=dosen_objects, max_students=int(row['KuotaMatkul']), 
                student_group=(int(row['Tingkat']), int(row['no_kelas'])), 
                is_fixed=(row.get('jadwalfix') == 1), is_difficult=(row.get('MatkulSusah') == 1), 
                course_type=int(row.get('Tipe', 1)), 
                fixed_schedule_4jam=row.get('jadwal4jam'), 
                fixed_schedule_2jam=row.get('jadwal2jam'), 
                fixed_schedule_1jam=row.get('jadwal1jam'),
                fixed_room_4jam=str(row.get('ruanganfix4jam')) if pd.notna(row.get('ruanganfix4jam')) else None,
                fixed_room_2jam=str(row.get('ruanganfix2jam')) if pd.notna(row.get('ruanganfix2jam')) else None,
                fixed_room_1jam=str(row.get('ruanganfix1jam')) if pd.notna(row.get('ruanganfix1jam')) else None,
            ))

        self._number_of_classes = len(self._courses)
        self._time_slot_mapper = TimeSlotMapper(self._meeting_times_1jam, self._meeting_times_2jam, self._meeting_times_4jam)
        print("Data berhasil dimuat (Logika Dosen Alternatif).")

    # --- Getter Methods ---
    def get_rooms(self): return self._rooms
    def get_instructors(self): return self._instructors
    def get_courses(self): return self._courses
    def get_meeting_times(self, sks):
        if sks == 4: return self._meeting_times_4jam
        if sks == 2: return self._meeting_times_2jam
        if sks == 1: return self._meeting_times_1jam
        return []
    def get_number_of_classes(self): return self._number_of_classes
    def get_time_slot_mapper(self): return self._time_slot_mapper

# KELAS UTAMA UNTUK ALGORITMA GENETIKA
class Schedule:
    def __init__(self):
        self._data = data
        self._classes = []
        self._is_fitness_changed = True
        
        # Atribut baru untuk sistem skor dan fitness
        self._fitness = -1.0
        self._score = -1
        self._hard_conflicts = 0
        self._soft_conflicts = 0

    def initialize(self):
        courses = self._data.get_courses()
        all_rooms = self._data.get_rooms()
        
        # Helper Functions
        def find_meeting_time(sks, time_str):
            if time_str is None or pd.isna(time_str): return None
            return next((mt for mt in self._data.get_meeting_times(sks) if mt.time == time_str), None)

        def find_room(room_number_from_csv):
            if room_number_from_csv is None or pd.isna(room_number_from_csv): return None
            try: clean_room_str = str(room_number_from_csv).strip().split('.')[0]
            except: clean_room_str = str(room_number_from_csv).strip()
            for r in all_rooms:
                if str(r.number).strip() == clean_room_str: return r
            print(f"--> PERINGATAN: Ruangan tetap ID '{clean_room_str}' tidak ditemukan di 'Ruangan.csv'.")
            return None

        self._classes = []
        for i, course in enumerate(courses):
            new_class = Class(i, course)
            
            if course.instructors:
                new_class.instructor = random.choice(course.instructors)
            else:
                new_class.instructor = Instructor(id="N/A", name="TIDAK ADA DOSEN")

            # Tetapkan Ruangan dan Waktu
            if course.is_fixed:
                # Jalur untuk jadwal yang sudah tetap
                mt1 = find_meeting_time(1, course.fixed_schedule_1jam)
                mt2 = find_meeting_time(2, course.fixed_schedule_2jam)
                mt4 = find_meeting_time(4, course.fixed_schedule_4jam)
                room1 = find_room(course.fixed_room_1jam)
                room2 = find_room(course.fixed_room_2jam)
                room4 = find_room(course.fixed_room_4jam)

                if course.sks == 1: new_class.meeting_times[1] = mt1 or random.choice(self._data.get_meeting_times(1))
                if course.sks == 2: new_class.meeting_times[2] = mt2 or random.choice(self._data.get_meeting_times(2))
                if course.sks == 4: new_class.meeting_times[4] = mt4 or random.choice(self._data.get_meeting_times(4))
                if course.sks == 3:
                    new_class.meeting_times[1] = mt1 or random.choice(self._data.get_meeting_times(1))
                    new_class.meeting_times[2] = mt2 or random.choice(self._data.get_meeting_times(2))
                
                final_room = room4 or room2 or room1
                new_class.room = final_room or random.choice(all_rooms)
            else:
                # Jalur untuk jadwal yang tidak tetap   
                if course.sks == 4:
                    if random.random() < 0.5:
                        # Jadwalkan sebagai 2+2 yang TIDAK BENTROK
                        meeting_times_2sks = self._data.get_meeting_times(2)
                        mt_a = random.choice(meeting_times_2sks)
                        mt_b = random.choice(meeting_times_2sks)
                        # Terus cari mt_b baru jika sama dengan mt_a
                        while mt_b.id == mt_a.id:
                            mt_b = random.choice(meeting_times_2sks)
                        
                        new_class.meeting_times['2a'] = mt_a
                        new_class.meeting_times['2b'] = mt_b
                    else:
                        new_class.meeting_times[4] = random.choice(self._data.get_meeting_times(4))
                
                elif course.sks == 3:
                    new_class.meeting_times[2] = random.choice(self._data.get_meeting_times(2))
                    new_class.meeting_times[1] = random.choice(self._data.get_meeting_times(1))
                elif course.sks == 2:
                    new_class.meeting_times[2] = random.choice(self._data.get_meeting_times(2))
                elif course.sks == 1:
                    new_class.meeting_times[1] = random.choice(self._data.get_meeting_times(1))
                
                # Tetapkan Ruangan yang Tersedia
                sks_utama = course.sks if course.sks != 3 else 2
                mt_utama = new_class.meeting_times.get(sks_utama) or new_class.meeting_times.get(4) or new_class.meeting_times.get('2a')
                new_class.room = self.find_available_room(new_class, sks_utama, mt_utama) if mt_utama else random.choice(all_rooms)
            
            if not new_class.room: new_class.room = random.choice(all_rooms)
            self._classes.append(new_class)
                
        return self

    def find_available_room(self, class_to_schedule, target_sks, target_meeting_time):
        time_mapper = self._data.get_time_slot_mapper()
        all_rooms = self._data.get_rooms()
        target_slots = set(time_mapper.get_1hr_slots(target_meeting_time.id))
        if not target_slots: return random.choice(all_rooms)
        room_occupancy_map = {}
        for existing_class in self._classes:
            if existing_class.id == class_to_schedule.id or not existing_class.room: continue
            room_id = existing_class.room.number
            if room_id not in room_occupancy_map: room_occupancy_map[room_id] = set()
            for mt in existing_class.meeting_times.values():
                if mt: room_occupancy_map[room_id].update(time_mapper.get_1hr_slots(mt.id))
        shuffled_rooms = random.sample(all_rooms, len(all_rooms))
        for room in shuffled_rooms:
            occupied_slots = room_occupancy_map.get(room.number, set())
            if target_slots.isdisjoint(occupied_slots) and room.seating_capacity >= class_to_schedule.course.max_students:
                return room
        for room in shuffled_rooms:
            occupied_slots = room_occupancy_map.get(room.number, set())
            if target_slots.isdisjoint(occupied_slots): return room
        return random.choice(all_rooms)

    def check_time_overlap(self, c1, c2):
        time_mapper = self._data.get_time_slot_mapper()
        c1_slots, c2_slots = set(), set()
        for mt in c1.meeting_times.values():
            if mt: c1_slots.update(time_mapper.get_1hr_slots(mt.id))
        for mt in c2.meeting_times.values():
            if mt: c2_slots.update(time_mapper.get_1hr_slots(mt.id))
        if not c1_slots or not c2_slots: return False
        return not c1_slots.isdisjoint(c2_slots)

    def calculate_fitness_and_score(self):
        hard_conflicts, soft_conflicts = 0, 0
        HARD_CONFLICT_PENALTY, SOFT_CONFLICT_PENALTY = 1000, 1
        time_mapper = self._data.get_time_slot_mapper()

        # Buat peta untuk booking sumber daya 
        # Kunci: (resource_type, resource_id, slot_id) -> Value: course_number
        # Contoh: ('room', 'R-01', 'Senin-08') -> 'TF2101'
        bookings = {}
        
        # Statistik Agregat
        dosen_daily_hours = {}  # K9
        group_daily_hours = {}  # K10
        group_schedule_list = {}  # L3
        dosen_teaching_days = {}  # L4
        dosen_sks_summary = {}

        # begin loop untuk setiap kelas
        for c in self._classes:
            course = c.course
            instructor = c.instructor
            room = c.room
            group_id = f"T{course.student_group[0]}-K{course.student_group[1]}"

            # --- A. Konflik Internal & Pengumpulan Data Awal ---
            # [K2] Kapasitas Ruangan
            if constraints_loader.is_enabled('K2') and course.course_type != 3 and room and room.seating_capacity < course.max_students:
                hard_conflicts += 1
            
            # [K11] Bentrok 4 SKS (2a & 2b)
            if constraints_loader.is_enabled('K11') and course.sks == 4:
                mt_a = c.meeting_times.get('2a')
                mt_b = c.meeting_times.get('2b')
                if mt_a and mt_b:
                    slots_a = set(time_mapper.get_1hr_slots(mt_a.id))
                    slots_b = set(time_mapper.get_1hr_slots(mt_b.id))
                    if not slots_a.isdisjoint(slots_b):
                        hard_conflicts += 1

            # [K8] Matkul 3 SKS di hari yang sama
            mt1 = c.meeting_times.get(1)
            mt2 = c.meeting_times.get(2)
            if constraints_loader.is_enabled('K8') and course.sks == 3 and mt1 and mt2:
                if mt1.time.split('-')[0] == mt2.time.split('-')[0]:
                    hard_conflicts += 1

            # Inisialisasi tracker statistik jika belum ada
            if group_id not in group_schedule_list: group_schedule_list[group_id] = []
            if instructor and instructor.id not in dosen_teaching_days: dosen_teaching_days[instructor.id] = set()
            if instructor and instructor.id not in dosen_sks_summary: dosen_sks_summary[instructor.id] = 0
        
            # Akumulasi SKS aktual untuk L5
            if instructor:
                dosen_sks_summary[instructor.id] += course.sks

            # --- B. Proses Setiap Sesi Waktu & Booking Sumber Daya ---
            for mt in c.meeting_times.values():
                if not mt: continue

                # [K6] Waktu Terlarang
                if constraints_loader.is_enabled('K6') and mt.is_blocked:
                    hard_conflicts += 1
                
                # [L1] Waktu Tepi
                if constraints_loader.is_enabled('L1') and mt.sks == 1 and mt.is_edge_time:
                    soft_conflicts += 1

                day = mt.time.split('-')[0]
                valid_slots = [s for s in time_mapper.get_1hr_slots(mt.id) if '-' in s]
                if not valid_slots: continue

                # Kumpulkan data untuk statistik agregat
                num_hours = len(valid_slots)
                jam_mulai = int(min(valid_slots, key=lambda s: int(s.split('-')[1])).split('-')[1])
                jam_selesai = int(max(valid_slots, key=lambda s: int(s.split('-')[1])).split('-')[1]) + 1

                if instructor:
                    key_dosen = (instructor.id, day); dosen_daily_hours[key_dosen] = dosen_daily_hours.get(key_dosen, 0) + num_hours
                    dosen_teaching_days[instructor.id].add(day)
                
                key_grup = (group_id, day); group_daily_hours[key_grup] = group_daily_hours.get(key_grup, 0) + num_hours
                group_schedule_list[group_id].append((jam_mulai, jam_selesai, day))
                
                # --- C. Proses Booking & Deteksi Bentrok Langsung ---
                for slot_id in valid_slots:
                    # [K1] Booking Kelompok Mahasiswa
                    if constraints_loader.is_enabled('K1'):
                        key = ('group', group_id, slot_id)
                        if key in bookings: hard_conflicts += 1
                        else: bookings[key] = course.number
                    
                    # [K3] Booking Dosen
                    if constraints_loader.is_enabled('K3') and instructor:
                        key = ('instructor', instructor.id, slot_id)
                        if key in bookings: hard_conflicts += 1
                        else: bookings[key] = course.number

                    # Booking Ruangan
                    if room:
                        key = ('room', room.number, slot_id)
                        if key in bookings: hard_conflicts += 1
                        else: bookings[key] = course.number

        # Evaluasi Konflik Agregat & Antar-Kelas Kompleks
        
        # K9 & K10 (Limit Jam Harian)
        if constraints_loader.is_enabled('K9'):
            for total_jam in dosen_daily_hours.values():
                if total_jam > 5: hard_conflicts += (total_jam - 5)
        if constraints_loader.is_enabled('K10'):
            for total_jam in group_daily_hours.values():
                if total_jam > 6: hard_conflicts += (total_jam - 6)

        # L3 (Jeda Antar Kuliah)
        if constraints_loader.is_enabled('L3'):
            for group_id, schedule_list in group_schedule_list.items():
                sorted_schedule = sorted(schedule_list, key=lambda x: (x[2], x[0]))
                consecutive_count = 1
                for i in range(len(sorted_schedule) - 1):
                    if sorted_schedule[i][2] == sorted_schedule[i+1][2] and sorted_schedule[i][1] == sorted_schedule[i+1][0]:
                        consecutive_count += 1
                        if consecutive_count > 2: soft_conflicts += 1
                    else: consecutive_count = 1
        
        # L4 (Hari Kosong Dosen)
        if constraints_loader.is_enabled('L4'):
            for teaching_days in dosen_teaching_days.values():
                if len(teaching_days) > 4: soft_conflicts += (len(teaching_days) - 4)

        # L5 (Beban SKS Dosen)
        if constraints_loader.is_enabled('L5') and dosen_sks_summary:
            # Ambil daftar SKS yang diajarkan oleh semua dosen yang terlibat dalam jadwal ini
            sks_values = list(dosen_sks_summary.values())
            
            if len(sks_values) > 1:
                # Hitung varians dari sebaran SKS.
                # Varians tinggi berarti beban kerja timpang.
                variance = np.var(sks_values)
                
                # Tambahkan varians ke soft conflicts. Bobot bisa disesuaikan.
                # Misal, varians 9 (std dev 3 SKS) akan menambah 9 penalti.
                soft_conflicts += variance

        # Konflik Antar-Kelas (K4, K5, L2)
        for i in range(len(self._classes)):
            for j in range(i + 1, len(self._classes)):
                c1, c2 = self._classes[i], self._classes[j]
                c1_course, c2_course = c1.course, c2.course
                if self.check_time_overlap(c1, c2):
                    if constraints_loader.is_enabled('K4') and c1_course.course_type == 3 and c2_course.course_type == 3 and {c1_course.student_group[0], c2_course.student_group[0]} == {2, 3}: hard_conflicts += 1
                    if constraints_loader.is_enabled('K5') and c1_course.student_group[0] == 4 and c2_course.student_group[0] == 4 and c1_course.course_type != c2_course.course_type: hard_conflicts += 1
                    if constraints_loader.is_enabled('L2') and c1_course.is_difficult and c2_course.is_difficult and {c1_course.student_group[0], c2_course.student_group[0]} == {2, 3}: soft_conflicts += 1

        # Finalisasi Skor dan Fitness
        score = (hard_conflicts * HARD_CONFLICT_PENALTY) + (soft_conflicts * SOFT_CONFLICT_PENALTY)
        fitness = 1.0 / (score + 1)
        return fitness, score, hard_conflicts, soft_conflicts
    
    # Getter Methods untuk Fitness dan Statistik
    def get_fitness(self):
        if self._is_fitness_changed:
            self._fitness, self._score, self._hard_conflicts, self._soft_conflicts = self.calculate_fitness_and_score()
            self._is_fitness_changed = False
        return self._fitness

    def get_score(self):
        self.get_fitness() # Memastikan semua nilai sudah terupdate
        return self._score

    def get_num_of_conflicts(self):
        self.get_fitness()
        return self._hard_conflicts + self._soft_conflicts

    def get_hard_conflicts(self):
        self.get_fitness()
        return self._hard_conflicts
    
    def get_soft_conflicts(self):
        self.get_fitness()
        return self._soft_conflicts

    def get_classes(self): 
        self._is_fitness_changed = True
        return self._classes

class Population:
    def __init__(self, size):
        self._size = size
        self._schedules = [Schedule().initialize() for _ in range(size)]
    def get_schedules(self): return self._schedules

class GeneticAlgorithm:
    def evolve(self, population):
        return self._mutate_population(self._crossover_population(population))
    def _crossover_population(self, pop):
        crossover_pop = Population(0)
        for i in range(NUMB_OF_ELITE_SCHEDULES):
            crossover_pop.get_schedules().append(pop.get_schedules()[i])
        for _ in range(NUMB_OF_ELITE_SCHEDULES, POPULATION_SIZE):
            parent1 = self._tournament_selection(pop).get_schedules()[0]
            parent2 = self._tournament_selection(pop).get_schedules()[0]
            child = self._crossover_schedule(parent1, parent2)
            crossover_pop.get_schedules().append(child)
        return crossover_pop
    def _mutate_population(self, population):
        for i in range(NUMB_OF_ELITE_SCHEDULES, POPULATION_SIZE):
            self._mutate_schedule(population.get_schedules()[i])
        return population
    def _crossover_schedule(self, parent1, parent2):
        # Buat anak sebagai salinan (deep copy) dari parent1
        child_schedule = copy.deepcopy(parent1)
        
        # Buat peta lokasi gen di anak
        # Key: ID kelas, Value: indeks/posisi di dalam list `child_genes`
        child_genes_list = child_schedule.get_classes()
        child_gene_map = {gene.id: i for i, gene in enumerate(child_genes_list)}

        # Loop melalui gen dari parent2
        for i in range(len(parent2.get_classes())):
            # Dengan probabilitas 50% (atau bisa disesuaikan), coba ambil gen dari parent2
            if random.random() < 0.5:
                # Gen yang ingin kita ambil dari parent2
                gene_from_parent2 = parent2.get_classes()[i]
                
                # Gen yang saat ini ada di posisi yang sama pada anak
                gene_in_child_at_pos_i = child_genes_list[i]
                
                # Jika gennya sudah sama, tidak perlu melakukan apa-apa
                if gene_from_parent2.id == gene_in_child_at_pos_i.id:
                    continue
                    
                # Proses Penukaran (Swap)
                # 1. Ambil gen dari parent2 dan letakkan di posisi `i` pada anak.
                child_genes_list[i] = gene_from_parent2
                
                # 2. Temukan di mana posisi lama dari gen yang baru kita masukkan. Gunakan peta untuk menemukan ini dengan cepat.
                original_pos_of_new_gene = child_gene_map[gene_from_parent2.id]
                
                # 3. Letakkan gen yang kita "usir" (gene_in_child_at_pos_i) ke posisi yang baru saja kosong tersebut.
                child_genes_list[original_pos_of_new_gene] = gene_in_child_at_pos_i
                
                # 4. Update peta untuk mencerminkan perubahan posisi
                child_gene_map[gene_from_parent2.id] = i
                child_gene_map[gene_in_child_at_pos_i.id] = original_pos_of_new_gene

        child_schedule._is_fitness_changed = True
        return child_schedule
    def _mutate_schedule(self, schedule):
        data = schedule._data
        something_changed = False

        for i in range(len(schedule.get_classes())):
            current_class = schedule.get_classes()[i]
            course = current_class.course

            if course.is_fixed:
                continue

            # Mutasi Representasi 4 SKS
            if course.sks == 4 and random.random() < MUTATION_RATE:
                if 4 in current_class.meeting_times:
                    current_class.meeting_times.clear()
                    meeting_times_2sks = data.get_meeting_times(2)
                    mt_a = random.choice(meeting_times_2sks)
                    mt_b = random.choice(meeting_times_2sks)
                    while mt_b.id == mt_a.id:
                        mt_b = random.choice(meeting_times_2sks)
                    current_class.meeting_times['2a'] = mt_a
                    current_class.meeting_times['2b'] = mt_b
                    something_changed = True
                elif '2a' in current_class.meeting_times:
                    current_class.meeting_times.clear()
                    current_class.meeting_times[4] = random.choice(data.get_meeting_times(4))
                    something_changed = True

            # Mutasi Waktu (MeetingTime)
            if random.random() < MUTATION_RATE:
                if course.sks == 3:
                    current_class.meeting_times[2] = random.choice(data.get_meeting_times(2))
                    current_class.meeting_times[1] = random.choice(data.get_meeting_times(1))
                elif course.sks == 2:
                    current_class.meeting_times[2] = random.choice(data.get_meeting_times(2))
                elif course.sks == 1:
                    current_class.meeting_times[1] = random.choice(data.get_meeting_times(1))
                # Untuk 4 SKS, biarkan mutasi representasi yang menanganinya, atau bisa juga ditambahkan di sini.
                # Untuk semplicitas, kita biarkan.
                something_changed = True

            # Mutasi Ruangan
            if random.random() < MUTATION_RATE:
                if course.sks == 4:
                    lab_rooms = [r for r in data.get_rooms() if "Lab" in r.number]
                    current_class.room = random.choice(lab_rooms) if lab_rooms else random.choice(data.get_rooms())
                else:
                    current_class.room = random.choice(data.get_rooms())
                something_changed = True

            # Mutasi Dosen
            if len(course.instructors) > 1 and random.random() < MUTATION_RATE:
                current_instructor = current_class.instructor
                if current_instructor:
                    other_instructors = [inst for inst in course.instructors if inst.id != current_instructor.id]
                else:
                    other_instructors = course.instructors
                if other_instructors:
                    current_class.instructor = random.choice(other_instructors)
                    something_changed = True

        # Setelah loop selesai, jika ada perubahan, tandai fitness untuk dihitung ulang
        if something_changed:
            schedule._is_fitness_changed = True
                
        return schedule
    def _tournament_selection(self, pop):
        tournament_pop = Population(0)
        for _ in range(TOURNAMENT_SELECTION_SIZE):
            tournament_pop.get_schedules().append(random.choice(pop.get_schedules()))
        tournament_pop.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
        return tournament_pop

class DisplayManager:
    def _split_schedule_time(self, schedule_string):
        """Memecah string jadwal menjadi hari dan jam dengan aman."""
        try:
            if not schedule_string or not isinstance(schedule_string, str):
                return 'N/A', 'N/A'
            parts = schedule_string.strip().split('-', 1)
            if len(parts) == 2:
                return parts[0], parts[1]
            else:
                # Fallback untuk format yang tidak terduga
                return parts[0] if parts else 'N/A', '-'
        except Exception:
            return 'N/A', 'N/A'

    def print_schedule_as_table(self, schedule, generation_number, elapsed_time):
        # Urutkan kelas berdasarkan SKS (menurun) dan kode mata kuliah
        classes = sorted(schedule.get_classes(), 
                         key=lambda c: (c.course.sks, c.course.number), 
                         reverse=True)
        
        # Header info (diperbarui untuk menyertakan skor)
        print(f"\n==================================================================================================================================================================\n JADWAL KULIAH TERBAIK (Generasi #{generation_number})\n > Skor: {schedule.get_score()} (Hard: {schedule.get_hard_conflicts()}, Soft: {schedule.get_soft_conflicts()})\n > Waktu Komputasi: {elapsed_time:.2f} detik\n==================================================================================================================================================================")
        
        # Buat header tabel yang generik dan informatif
        table = prettytable.PrettyTable([
            'No', 
            'Mata Kuliah (Kode, SKS, Kuota)', 
            'Kelompok', 
            'Ruangan (Kap.)', 
            'Dosen', 
            'Hari (Sesi 1)', 
            'Jam (Sesi 1)', 
            'Hari (Sesi 2)', 
            'Jam (Sesi 2)'
        ])
        
        # Loop melalui kelas yang sudah terurut dan isi tabel
        for i, current_class in enumerate(classes):
            course = current_class.course
            sks = course.sks
            
            # Inisialisasi semua kolom jadwal sebagai default
            hari1, jam1, hari2, jam2 = '-', '-', '-', '-'

            # Ambil semua kemungkinan meeting time dari objek Class
            mt_block_4 = current_class.meeting_times.get(4)
            mt_split_2a = current_class.meeting_times.get('2a')
            mt_split_2b = current_class.meeting_times.get('2b')
            mt_sesi_2 = current_class.meeting_times.get(2)
            mt_sesi_1 = current_class.meeting_times.get(1)

            # LOGIKA PENGISIAN KOLOM YANG CERDAS
            if sks == 4:
                if mt_block_4:
                    # Kasus blok 4 jam -> isi Sesi 1
                    hari1, jam1 = self._split_schedule_time(mt_block_4.time)
                elif mt_split_2a and mt_split_2b:
                    # Kasus 2+2 jam -> isi Sesi 1 dan Sesi 2
                    hari1, jam1 = self._split_schedule_time(mt_split_2a.time)
                    hari2, jam2 = self._split_schedule_time(mt_split_2b.time)
            
            elif sks == 3 and mt_sesi_2 and mt_sesi_1:
                # Kasus 3 SKS (2+1) -> isi Sesi 1 (2 jam) dan Sesi 2 (1 jam)
                hari1, jam1 = self._split_schedule_time(mt_sesi_2.time)
                hari2, jam2 = self._split_schedule_time(mt_sesi_1.time)

            elif sks == 2 and mt_sesi_2:
                # Kasus 2 SKS -> isi Sesi 1
                hari1, jam1 = self._split_schedule_time(mt_sesi_2.time)

            elif sks == 1 and mt_sesi_1:
                # Kasus 1 SKS -> isi Sesi 1
                hari1, jam1 = self._split_schedule_time(mt_sesi_1.time)
            
            # Ambil detail lain seperti ruangan dan dosen
            room_info = f"{current_class.room.number} ({current_class.room.seating_capacity})" if current_class.room else "N/A"
            instructor_info = current_class.instructor.name if current_class.instructor else "N/A"

            # Tambahkan baris yang sudah lengkap ke tabel
            table.add_row([
                str(i + 1),
                f"{course.name}\n({course.number}, {sks} SKS, {course.max_students} mhs)",
                f"Tingkat {course.student_group[0]} - Kelas {course.student_group[1]}",
                room_info,
                instructor_info,
                hari1,
                jam1,
                hari2,
                jam2
            ])
            
        print(table)
        
        # Simpan ke CSV dengan format yang sama
        df = pd.DataFrame(table.rows, columns=table.field_names)
        output_filename = "Jadwal_Final_Optimal_Terurut.csv"
        df.to_csv(output_filename, index=False)
        print(f"\nJadwal optimal telah disimpan ke file '{output_filename}'")

# MAIN EXECUTION BLOCK
if __name__ == '__main__':
    # PARAMETER BARU: AMBANG BATAS SKOR
    # Algoritma akan berhenti jika skor jadwal terbaik DI BAWAH ambang batas ini.
    # Skor hanya dihitung dari soft conflicts jika tidak ada hard conflicts.
    # Misal, jika ada 5 soft conflicts, skornya adalah 5.
    # Kita set ambang batas di 10, artinya kita terima solusi dengan < 10 soft conflicts.
    SCORE_THRESHOLD = 1.5
    
    start_time = time.time()
    data = Data()
    display_manager = DisplayManager()
    
    print("\nMembuat populasi awal...")
    population = Population(POPULATION_SIZE)
    # Pengurutan tetap berdasarkan fitness, karena GA bekerja dengan memaksimalkan fitness
    population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
    
    best_schedule = population.get_schedules()[0]
    print(f"Jadwal Awal Terbaik -> Skor: {best_schedule.get_score()} (H: {best_schedule.get_hard_conflicts()}, S: {best_schedule.get_soft_conflicts()})")

    print(f"\nMemulai proses evolusi untuk {MAX_GENERATION} generasi...")
    genetic_algorithm = GeneticAlgorithm()
    generation_num = 0
    
    with tqdm(total=MAX_GENERATION, desc="Evolusi Generasi") as pbar:
        for i in range(MAX_GENERATION):
            generation_num = i + 1
            population = genetic_algorithm.evolve(population)
            population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
            
            best_schedule = population.get_schedules()[0]
            
            # Update progress bar dengan informasi skor
            pbar.set_postfix({
                "Skor Terbaik": f"{best_schedule.get_score()}",
                "Hard": f"{best_schedule.get_hard_conflicts()}",
                "Soft": f"{best_schedule.get_soft_conflicts()}"
            })
            pbar.update(1)
            
            # Berhenti jika tidak ada hard conflict DAN skor (dari soft conflict) di bawah ambang batas
            if best_schedule.get_hard_conflicts() == 0 and best_schedule.get_score() < SCORE_THRESHOLD:
                pbar.n = MAX_GENERATION # Lompat ke akhir progress bar
                pbar.refresh()
                print(f"\n\nSolusi Cukup Baik (skor < {SCORE_THRESHOLD}) ditemukan pada generasi ke-{generation_num}!")
                break
                
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Modifikasi tampilan output akhir untuk menunjukkan skor
    best_schedule_final = population.get_schedules()[0]
    print(f"\n\n--- HASIL AKHIR EVOLUSI ---")
    print(f"Skor Terbaik Ditemukan : {best_schedule_final.get_score()}")
    print(f" > Hard Conflicts       : {best_schedule_final.get_hard_conflicts()}")
    print(f" > Soft Conflicts       : {best_schedule_final.get_soft_conflicts()}")

    # Tampilkan jadwal terbaik dalam format tabel
    display_manager.print_schedule_as_table(best_schedule_final, generation_num, elapsed_time)