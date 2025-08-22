import os
import sys
import re
import copy
import random
import time
import pandas as pd
import numpy as np
import prettytable
from tqdm import tqdm
from itertools import combinations

# Setup path agar bisa mengimpor modul dari direktori lain
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Impor semua komponen yang dibutuhkan dari proyek
from config import settings
from src.type import Instructor, MeetingTime, Course, Class, AssignedInstructor
from src.type.time_slot_mapper import TimeSlotMapper
from src.constraints.constraints_loader import ConstraintLoader

# Tentukan path direktori data
DATA_DIR = os.path.join(BASE_DIR, 'data')
# Muat daftar constraint dari file CSV
constraints_path = os.path.join(DATA_DIR, 'Constraints.csv')
constraints_loader = ConstraintLoader(constraints_path)

print("--- Sistem Cerdas Penjadwalan Kuliah Berbasis Algoritma Genetika ---")

class Data:
    try:
        # Nama file input utama
        DATA_PENJADWALAN_FILE = 'Input_Update_DK_133_TF_Semester3_2025.csv'
        
        # Muat semua data sumber, paksa kolom ID dibaca sebagai string untuk konsistensi
        MEETING_TIMES_4JAM_DF = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_4jam.csv'))
        MEETING_TIMES_2JAM_DF = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_2jam.csv'))
        MEETING_TIMES_1JAM_DF = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_1jam.csv'))
        
        if not os.path.exists(os.path.join(DATA_DIR, DATA_PENJADWALAN_FILE)):
             raise FileNotFoundError(f"File '{DATA_PENJADWALAN_FILE}' tidak ditemukan.")

        # Muat data mata kuliah, perlakukan semua kolom sebagai teks untuk menghindari error tipe data
        COURSE_DATA = pd.read_csv(
            os.path.join(DATA_DIR, DATA_PENJADWALAN_FILE),
            na_values=['0', 0],
            dtype=str
        ).replace('nan', None)
        
    except Exception as e:
        print(f"Error fatal saat memuat data awal: {e}"); sys.exit()

    def __init__(self):
        # Inisialisasi semua list penampung data
        self._meeting_times_1jam, self._meeting_times_2jam, self._meeting_times_4jam = [], [], []
        self._all_meeting_times, self._instructors, self._courses = [], [], []
        
        # Proses dan buat objek MeetingTime dari DataFrame
        for _, mt in self.MEETING_TIMES_4JAM_DF.iterrows(): self._meeting_times_4jam.append(MeetingTime(id=str(mt['Kode']), time=str(mt['Jadwal']), sks=4, groups={'g1': int(mt['Group1'])}, is_blocked=(int(mt['Blocked'])==1), is_edge_time=False))
        for _, mt in self.MEETING_TIMES_2JAM_DF.iterrows(): self._meeting_times_2jam.append(MeetingTime(id=str(mt['Kode']), time=str(mt['Jadwal']), sks=2, groups={'g1': int(mt['Group1']), 'g2': int(mt['Group2']), 'g3': int(mt['Group3'])}, is_blocked=(int(mt['Blocked'])==1), is_edge_time=False))
        for _, mt in self.MEETING_TIMES_1JAM_DF.iterrows(): self._meeting_times_1jam.append(MeetingTime(id=str(mt['Kode']), time=str(mt['Jadwal']), sks=1, groups={'g1': int(mt['Group1']), 'g2': int(mt['Group2']), 'g3': int(mt['Group3'])}, is_blocked=(int(mt['Blocked'])==1), is_edge_time=(int(mt['WaktuAkhir'])==1)))
        self._all_meeting_times.extend(self._meeting_times_1jam); self._all_meeting_times.extend(self._meeting_times_2jam); self._all_meeting_times.extend(self._meeting_times_4jam)

        # PASS 1: Bangun peta dosen unik dari data mata kuliah
        instructor_map = {}
        delimiter_pattern = re.compile(r'\s*\([\d.]+\s*SKS\)\s*')
        for index, row in self.COURSE_DATA.iterrows():
            if pd.isna(row['InisialDosen']) or pd.isna(row['NamaDosen']): continue
            raw_initials, raw_names = str(row['InisialDosen']).strip(), str(row['NamaDosen']).strip()
            initials = [i.strip() for i in re.split(r'[,;\n]', raw_initials) if i.strip()]
            split_names = delimiter_pattern.split(raw_names)
            clean_names_list = [name.strip() for name in split_names if name.strip()]
            if len(initials) == len(clean_names_list):
                for i in range(len(initials)):
                    initial, clean_name = initials[i], clean_names_list[i]
                    if initial not in instructor_map: instructor_map[initial] = Instructor(id=initial, name=clean_name)
        self._instructors = list(instructor_map.values())
        
        # PASS 2: Validasi dan buat objek Course menggunakan peta dosen yang sudah lengkap
        for index, row in self.COURSE_DATA.iterrows():
            course_code = row['KodeMatkul']
            if pd.isna(row['InisialDosen']): continue
            initials_in_order = [i.strip() for i in re.split(r'[,;\n]', str(row['InisialDosen'])) if i.strip()]
            if not all(initial in instructor_map for initial in initials_in_order): continue
            assigned_instructors = [AssignedInstructor(instructor=instructor_map[initial], role="utama" if i == 0 else "sekunder") for i, initial in enumerate(initials_in_order)]
            fixed_schedules = [row.get(f'hari-jam-sesi_{i+1}') for i in range(3)]
            fixed_schedules = [s for s in fixed_schedules if s and pd.notna(s)]
            self._courses.append(Course(
                number=course_code, name=row['NamaMatkul'], sks=int(row['sks']),
                assigned_instructors=assigned_instructors, max_students=int(row['KuotaMatkul']),
                student_group=(int(row['Tingkat']), int(row['no_kelas'])),
                is_fixed=(str(row.get('jadwalfix')) == '1'), is_difficult=(str(row.get('MatkulSusah')) == '1'),
                course_type=int(row.get('Tipe', 1)), fixed_schedules=fixed_schedules))
        self._number_of_classes = len(self._courses)
        self._time_slot_mapper = TimeSlotMapper(self._meeting_times_1jam, self._meeting_times_2jam, self._meeting_times_4jam)

    # Getter Methods untuk mengakses data dari luar kelas
    def get_instructors(self): return self._instructors
    def get_courses(self): return self._courses
    def get_meeting_times(self, sks):
        if sks == 2: return self._meeting_times_2jam
        if sks == 1: return self._meeting_times_1jam
        return []
    def get_all_meeting_times(self): return self._all_meeting_times
    def get_number_of_classes(self): return self._number_of_classes
    def get_time_slot_mapper(self): return self._time_slot_mapper

class Schedule:
    def __init__(self):
        self._data = data
        self._classes = []
        self._is_fitness_changed = True
        self._fitness, self._score, self._hard_conflicts, self._soft_conflicts = -1.0, -1, 0, 0

    def initialize(self):
        """Membangun satu individu jadwal secara acak atau dari data tetap (fixed)."""
        courses = self._data.get_courses()
        time_mapper = self._data.get_time_slot_mapper()
        def find_meeting_time(time_str):
            if time_str is None or pd.isna(time_str): return None
            return next((mt for mt in self._data.get_all_meeting_times() if mt.time.strip() == str(time_str).strip()), None)
        self._classes = []
        used_slots_in_this_schedule = set()
        for i, course in enumerate(courses):
            new_class = Class(i, course)
            available_instructors = [ai.instructor for ai in course.assigned_instructors]
            main_instructor = next((ai.instructor for ai in course.assigned_instructors if ai.role == 'utama'), None)
            if main_instructor and random.random() < 0.7: new_class.instructor = main_instructor
            elif available_instructors: new_class.instructor = random.choice(available_instructors)
            else: new_class.instructor = Instructor(id="N/A", name="TIDAK ADA DOSEN")
            if course.is_fixed:
                for schedule_str in course.fixed_schedules:
                    meeting_time = find_meeting_time(schedule_str)
                    if meeting_time:
                        new_class.meeting_times.append(meeting_time)
                        used_slots_in_this_schedule.update(time_mapper.get_1hr_slots(meeting_time.id))
            else:
                sks_split_rule = {1: [1], 2: [2], 3: [2, 1], 4: [2, 2]}.get(course.sks, [])
                for sks_val in sks_split_rule:
                    possible_times = self._data.get_meeting_times(sks_val)
                    if not possible_times: continue
                    random.shuffle(possible_times)
                    found_available_time = False
                    for mt_candidate in possible_times:
                        candidate_slots = set(time_mapper.get_1hr_slots(mt_candidate.id))
                        if candidate_slots.isdisjoint(used_slots_in_this_schedule):
                            new_class.meeting_times.append(mt_candidate)
                            used_slots_in_this_schedule.update(candidate_slots)
                            found_available_time = True
                            break
                    if not found_available_time:
                        fallback_mt = random.choice(possible_times)
                        new_class.meeting_times.append(fallback_mt)
                        used_slots_in_this_schedule.update(time_mapper.get_1hr_slots(fallback_mt.id))
            self._classes.append(new_class)
        return self

    def calculate_fitness_and_score(self):
        """Menghitung skor dan nilai fitness dari jadwal. Ini adalah 'juri' utama."""
        hard_conflicts, soft_conflicts = 0, 0
        HARD_CONFLICT_PENALTY, SOFT_CONFLICT_PENALTY = 1000, 1
        time_mapper = self._data.get_time_slot_mapper()
        bookings = {}
        dosen_daily_hours, group_daily_hours = {}, {}
        group_schedule_list, dosen_teaching_days = {}, {}
        slot_to_classes_map = {}

        def _parse_simple(time_str):
            try:
                day, times = time_str.split('-', 1); start_hour = int(times.split('.')[0]); return day, start_hour
            except: return None, None

        # Loop utama (single-pass) untuk memeriksa semua kelas dan sesi
        for c in self._classes:
            course, instructor = c.course, c.instructor
            group_id = f"T{course.student_group[0]}-K{course.student_group[1]}"
            if group_id not in group_schedule_list: group_schedule_list[group_id] = []
            if instructor and instructor.id not in dosen_teaching_days: dosen_teaching_days[instructor.id] = set()
            if constraints_loader.is_enabled('L5'):
                main_instructor = next((ai.instructor for ai in course.assigned_instructors if ai.role == 'utama'), None)
                if main_instructor and instructor and main_instructor.id != instructor.id: soft_conflicts += 1
            if constraints_loader.is_enabled('K6') and len(c.meeting_times) > 1:
                if len(set(mt.time.split('-')[0] for mt in c.meeting_times)) < len(c.meeting_times): hard_conflicts += 1

            for meeting_time in c.meeting_times:
                if constraints_loader.is_enabled('K5') and meeting_time.is_blocked: hard_conflicts += 1
                if constraints_loader.is_enabled('L1') and meeting_time.sks == 1 and meeting_time.is_edge_time: soft_conflicts += 1
                valid_slots = time_mapper.get_1hr_slots(meeting_time.id)
                if not valid_slots: continue
                day, start_hour = _parse_simple(meeting_time.time)
                if day is None: continue
                num_hours = len(valid_slots)
                end_hour = start_hour + num_hours
                for slot_id in valid_slots:
                    if constraints_loader.is_enabled('K1'):
                        key_group = ('group', group_id, slot_id); 
                        if key_group in bookings: hard_conflicts += 1
                        else: bookings[key_group] = course.number
                    if constraints_loader.is_enabled('K2') and instructor:
                        key_instr = ('instructor', instructor.id, slot_id); 
                        if key_instr in bookings: hard_conflicts += 1
                        else: bookings[key_instr] = course.number
                    if slot_id not in slot_to_classes_map: slot_to_classes_map[slot_id] = []
                    slot_to_classes_map[slot_id].append(c)
                if instructor:
                    key_dosen_hr = (instructor.id, day); dosen_daily_hours[key_dosen_hr] = dosen_daily_hours.get(key_dosen_hr, 0) + num_hours
                    dosen_teaching_days[instructor.id].add(day)
                key_grup_hr = (group_id, day); group_daily_hours[key_grup_hr] = group_daily_hours.get(key_grup_hr, 0) + num_hours
                group_schedule_list[group_id].append((start_hour, end_hour, day))

        # Evaluasi konflik agregat setelah semua data terkumpul
        if constraints_loader.is_enabled('K7'):
            for total_jam in dosen_daily_hours.values():
                if total_jam > 5: hard_conflicts += (total_jam - 5)
        if constraints_loader.is_enabled('K8'):
            for total_jam in group_daily_hours.values():
                if total_jam > 6: hard_conflicts += (total_jam - 6)
        if constraints_loader.is_enabled('L3'):
            for group_id, schedule_list in group_schedule_list.items():
                sorted_schedule = sorted(schedule_list, key=lambda x: (x[2], x[0]))
                consecutive_count = 1
                for i in range(len(sorted_schedule) - 1):
                    if sorted_schedule[i][2] == sorted_schedule[i+1][2] and sorted_schedule[i][1] == sorted_schedule[i+1][0]:
                        consecutive_count += 1
                        if consecutive_count > 2: soft_conflicts += 1
                    else: consecutive_count = 1
        if constraints_loader.is_enabled('L4'):
            for teaching_days in dosen_teaching_days.values():
                if len(teaching_days) > 4: soft_conflicts += (len(teaching_days) - 4)
        for slot_id, classes_in_slot in slot_to_classes_map.items():
            if len(classes_in_slot) > 1:
                for c1, c2 in combinations(classes_in_slot, 2):
                    c1_course, c2_course = c1.course, c2.course
                    if constraints_loader.is_enabled('K3') and c1_course.course_type == 3 and c2_course.course_type == 3 and {c1_course.student_group[0], c2_course.student_group[0]} == {2, 3}: hard_conflicts += 1
                    if constraints_loader.is_enabled('K4') and c1_course.student_group[0] == 4 and c2_course.student_group[0] == 4 and c1_course.course_type != c2_course.course_type: hard_conflicts += 1
                    if constraints_loader.is_enabled('L2') and c1_course.is_difficult and c2_course.is_difficult and {c1_course.student_group[0], c2_course.student_group[0]} == {2, 3}: soft_conflicts += 1
        
        score = (hard_conflicts * HARD_CONFLICT_PENALTY) + (soft_conflicts * SOFT_CONFLICT_PENALTY)
        fitness = 1.0 / (score + 1)
        return fitness, score, hard_conflicts, soft_conflicts

    # Getter Methods untuk mengakses skor dan fitness
    def get_fitness(self):
        if self._is_fitness_changed: self._fitness, self._score, self._hard_conflicts, self._soft_conflicts = self.calculate_fitness_and_score()
        self._is_fitness_changed = False
        return self._fitness
    def get_score(self): self.get_fitness(); return self._score
    def get_num_of_conflicts(self): self.get_fitness(); return self._hard_conflicts + self._soft_conflicts
    def get_hard_conflicts(self): self.get_fitness(); return self._hard_conflicts
    def get_soft_conflicts(self): self.get_fitness(); return self._soft_conflicts
    def get_classes(self): self._is_fitness_changed = True; return self._classes

class Population:
    def __init__(self, size):
        self._schedules = [Schedule().initialize() for _ in range(size)]
    def get_schedules(self): return self._schedules

class GeneticAlgorithm:
    def evolve(self, population):
        """Proses evolusi: Crossover, Mutasi, lalu Pencarian Lokal (Memetic)."""
        new_population = self._mutate_population(self._crossover_population(population))
        new_population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
        num_to_improve = max(1, int(len(new_population.get_schedules()) * settings.LOCAL_SEARCH_RATE))
        for i in range(num_to_improve):
            improved_schedule = self._local_search(new_population.get_schedules()[i])
            new_population.get_schedules()[i] = improved_schedule
        return new_population

    def _crossover_population(self, pop):
        """Membuat generasi baru melalui crossover."""
        crossover_pop = Population(0)
        schedules = pop.get_schedules()
        schedules.sort(key=lambda x: x.get_fitness(), reverse=True)
        for i in range(settings.NUMB_OF_ELITE_SCHEDULES):
            crossover_pop.get_schedules().append(schedules[i])
        for _ in range(settings.NUMB_OF_ELITE_SCHEDULES, settings.POPULATION_SIZE):
            parent1 = self._tournament_selection(pop).get_schedules()[0]
            parent2 = self._tournament_selection(pop).get_schedules()[0]
            crossover_pop.get_schedules().append(self._crossover_schedule(parent1, parent2))
        return crossover_pop

    def _mutate_population(self, population):
        """Menerapkan mutasi pada populasi (selain individu elit)."""
        schedules = population.get_schedules()
        for i in range(settings.NUMB_OF_ELITE_SCHEDULES, settings.POPULATION_SIZE):
            self._mutate_schedule(schedules[i])
        return population

    def _crossover_schedule(self, parent1, parent2):
        """Operator Crossover berbasis penukaran (swap) yang cepat dan menjaga integritas."""
        child_schedule = copy.deepcopy(parent1)
        child_genes_list = child_schedule.get_classes()
        child_gene_map = {gene.id: i for i, gene in enumerate(child_genes_list)}
        parent2_genes = parent2.get_classes()
        for i in range(len(parent2_genes)):
            if random.random() < settings.CROSSOVER_RATE:
                gene_from_parent2 = parent2_genes[i]
                gene_in_child_at_pos_i = child_genes_list[i]
                if gene_from_parent2.id != gene_in_child_at_pos_i.id:
                    original_pos = child_gene_map[gene_from_parent2.id]
                    child_genes_list[i], child_genes_list[original_pos] = gene_from_parent2, gene_in_child_at_pos_i
                    child_gene_map[gene_from_parent2.id], child_gene_map[gene_in_child_at_pos_i.id] = i, original_pos
        child_schedule._is_fitness_changed = True
        return child_schedule

    def _mutate_schedule(self, schedule):
        """Operator Mutasi: mengubah dosen atau salah satu sesi waktu."""
        data = schedule._data
        something_changed = False
        for i in range(len(schedule.get_classes())):
            current_class = schedule.get_classes()[i]
            course = current_class.course
            if course.is_fixed: continue
            if len(course.assigned_instructors) > 1 and random.random() < settings.MUTATION_RATE:
                available_instructors = [ai.instructor for ai in course.assigned_instructors]
                current_class.instructor = random.choice(available_instructors)
                something_changed = True
            if current_class.meeting_times and random.random() < settings.MUTATION_RATE:
                session_to_mutate = random.choice(current_class.meeting_times)
                sks_val = session_to_mutate.sks
                possible_new_times = data.get_meeting_times(sks_val)
                if possible_new_times and len(possible_new_times) > 1:
                    new_meeting_time = random.choice(possible_new_times)
                    while new_meeting_time.id == session_to_mutate.id: new_meeting_time = random.choice(possible_new_times)
                    try:
                        index_to_mutate = current_class.meeting_times.index(session_to_mutate)
                        current_class.meeting_times[index_to_mutate] = new_meeting_time
                        something_changed = True
                    except ValueError: pass
        if something_changed:
            schedule._is_fitness_changed = True
        return schedule

    def _tournament_selection(self, pop):
        """Memilih individu terbaik dari sejumlah kandidat acak."""
        tournament_pop = Population(0)
        schedules = pop.get_schedules()
        for _ in range(settings.TOURNAMENT_SELECTION_SIZE):
            tournament_pop.get_schedules().append(random.choice(schedules))
        tournament_pop.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
        return tournament_pop
    
    def _local_search(self, schedule):
        """Pencarian Lokal: melakukan perbaikan kecil pada jadwal (Memetic)."""
        best_schedule = copy.deepcopy(schedule)
        best_score = best_schedule.get_score()
        for _ in range(settings.LOCAL_SEARCH_ITERATIONS):
            current_copy = copy.deepcopy(best_schedule)
            non_fixed_classes = [c for c in current_copy.get_classes() if not c.course.is_fixed and c.meeting_times]
            if len(non_fixed_classes) < 2: continue
            class1, class2 = random.sample(non_fixed_classes, 2)
            class1.meeting_times, class2.meeting_times = class2.meeting_times, class1.meeting_times
            new_score = current_copy.get_score()
            if new_score < best_score:
                best_schedule, best_score = current_copy, new_score
        return best_schedule

class DisplayManager:
    def _split_schedule_time(self, schedule_string):
        """Memecah string jadwal menjadi (Hari, Jam)."""
        try:
            if not schedule_string or not isinstance(schedule_string, str): return 'N/A', 'N/A'
            parts = schedule_string.strip().split('-', 1)
            return (parts[0], parts[1]) if len(parts) == 2 else (parts[0] if parts else 'N/A', '-')
        except Exception: return 'N/A', 'N/A'

    def print_schedule_as_table(self, schedule, generation_number, elapsed_time):
        """Mencetak dan menyimpan jadwal terbaik ke file CSV."""
        classes = sorted(schedule.get_classes(), key=lambda c: c.course.student_group)
        print(f"\n================================================================================================================================================================================================\n JADWAL KULIAH TERBAIK (Generasi #{generation_number})\n > Skor: {schedule.get_score()} (Hard: {schedule.get_hard_conflicts()}, Soft: {schedule.get_soft_conflicts()})\n > Waktu Komputasi: {elapsed_time:.2f} detik\n================================================================================================================================================================================================")
        table = prettytable.PrettyTable(['No', 'Mata Kuliah', 'Kode', 'SKS', 'Kuota', 'Tingkat', 'Kelas', 'Dosen', 'Hari (Sesi 1)', 'Jam (Sesi 1)', 'Hari (Sesi 2)', 'Jam (Sesi 2)', 'Hari (Sesi 3)', 'Jam (Sesi 3)'])
        for i, current_class in enumerate(classes):
            course = current_class.course
            hari1, jam1, hari2, jam2, hari3, jam3 = '-', '-', '-', '-', '-', '-'
            meeting_times = current_class.meeting_times
            if len(meeting_times) > 0: hari1, jam1 = self._split_schedule_time(meeting_times[0].time)
            if len(meeting_times) > 1: hari2, jam2 = self._split_schedule_time(meeting_times[1].time)
            if len(meeting_times) > 2: hari3, jam3 = self._split_schedule_time(meeting_times[2].time)
            instructor_info = current_class.instructor.name if current_class.instructor else "N/A"
            table.add_row([
                str(i + 1), course.name, course.number, course.sks, course.max_students,
                course.student_group[0], course.student_group[1], instructor_info,
                hari1, jam1, hari2, jam2, hari3, jam3
            ])
        print(table)
        df = pd.DataFrame(table.rows, columns=table.field_names)
        output_filename = "Jadwal_Final_Optimal_Terurut.csv"
        final_path = os.path.join(BASE_DIR, output_filename)
        df.to_csv(final_path, index=False)
        print(f"\nJadwal optimal telah disimpan ke file '{final_path}'")

# BLOK EKSEKUSI UTAMA
if __name__ == '__main__':
    start_time = time.time()
    data = Data()
    display_manager = DisplayManager()
    
    # Inisialisasi beberapa populasi (pulau)
    islands = [Population(settings.POPULATION_SIZE) for _ in range(settings.NUM_ISLANDS)]

    # Cari jadwal terbaik di populasi awal
    initial_best = None
    for island in islands:
        island.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
        best_in_island = island.get_schedules()[0]
        if initial_best is None or best_in_island.get_score() < initial_best.get_score():
            initial_best = best_in_island
    
    if initial_best.get_score() == 0:
        print("\nSolusi Sempurna (Skor = 0) ditemukan di populasi awal!")
        display_manager.print_schedule_as_table(initial_best, 0, time.time() - start_time)
        sys.exit()

    print(f"Jadwal Awal Terbaik -> Skor: {initial_best.get_score()} (H: {initial_best.get_hard_conflicts()}, S: {initial_best.get_soft_conflicts()})")
    print(f"\nMemulai proses evolusi multi-pulau untuk MAKSIMAL {settings.MAX_GENERATION} generasi...")
    if settings.EARLY_STOPPING_PATIENCE > 0:
        print(f"   -> Akan berhenti lebih awal jika tidak ada perbaikan selama {settings.EARLY_STOPPING_PATIENCE} generasi.")
    
    # Jalankan proses evolusi
    genetic_algorithm = GeneticAlgorithm()
    generation_num = 0
    best_schedule_overall = copy.deepcopy(initial_best)
    last_improvement_generation = 0
    
    with tqdm(total=settings.MAX_GENERATION, desc="Evolusi Kepulauan") as pbar:
        for i in range(settings.MAX_GENERATION):
            generation_num = i + 1
            
            # Evolusikan setiap pulau secara terpisah
            for island_idx in range(settings.NUM_ISLANDS):
                islands[island_idx] = genetic_algorithm.evolve(islands[island_idx])

            # Lakukan Migrasi secara periodik
            if generation_num > 0 and generation_num % settings.MIGRATION_INTERVAL == 0:
                migrants = [isl.get_schedules()[0] for isl in islands]
                random.shuffle(migrants)
                migrant_idx = 0
                for island in islands:
                    for j in range(settings.MIGRATION_SIZE):
                        if migrant_idx < len(migrants):
                            island.get_schedules()[-(j+1)] = copy.deepcopy(migrants[migrant_idx])
                            migrant_idx += 1

            # Cari jadwal terbaik dari SEMUA pulau
            for island in islands:
                best_in_island = island.get_schedules()[0]
                if best_in_island.get_score() < best_schedule_overall.get_score():
                    best_schedule_overall = copy.deepcopy(best_in_island)
                    last_improvement_generation = generation_num
            
            # Update progress bar
            pbar.set_postfix({
                "Skor Terbaik": f"{best_schedule_overall.get_score()}",
                "Hard": f"{best_schedule_overall.get_hard_conflicts()}",
                "Soft": f"{best_schedule_overall.get_soft_conflicts()}",
                "Stagnasi": f"{generation_num - last_improvement_generation}/{settings.EARLY_STOPPING_PATIENCE}"
            })
            pbar.update(1)

            # Cek kondisi berhenti
            if best_schedule_overall.get_score() == 0:
                print(f"\n\nSolusi Sempurna (Skor = 0) ditemukan pada generasi ke-{generation_num}!")
                break
            if settings.EARLY_STOPPING_PATIENCE > 0 and (generation_num - last_improvement_generation) >= settings.EARLY_STOPPING_PATIENCE:
                print(f"\n\nEarly stopping tercapai pada generasi ke-{generation_num} karena stagnasi.")
                break
                
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Tampilkan hasil akhir
    print(f"\n\n--- HASIL AKHIR EVOLUSI ---")
    print(f"Ditemukan pada Generasi: {last_improvement_generation}")
    print(f"Skor Terbaik Ditemukan : {best_schedule_overall.get_score()}")
    print(f" > Hard Conflicts       : {best_schedule_overall.get_hard_conflicts()}")
    print(f" > Soft Conflicts       : {best_schedule_overall.get_soft_conflicts()}")

    display_manager.print_schedule_as_table(best_schedule_overall, generation_num, elapsed_time)