import os
import sys

# Menambahkan direktori root proyek ke path agar import berfungsi
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import csv
import prettytable
import random
import pandas as pd
import time
from tqdm import tqdm

from src.constraints.constraints_loader import ConstraintLoader
from config import settings
from src.type import Room, Instructor, MeetingTime, Course, Class  # <-- FIX 1: Typo 'types'

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
        ROOMS = pd.read_csv(os.path.join(DATA_DIR, 'Ruangan.csv'), header=None).values.tolist()
        MEETING_TIMES_4JAM = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_4jam.csv'), usecols=['Kode','Jadwal','Group1','Blocked'], converters={"Group1":int,"Blocked":int}).values.tolist()
        MEETING_TIMES_2JAM = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_2jam.csv'), usecols=['Kode','Jadwal','Group1','Group2','Group3','Blocked'], converters={"Group1":int,"Group2":int,"Group3":int,"Blocked":int}).values.tolist()
        MEETING_TIMES_1JAM = pd.read_csv(os.path.join(DATA_DIR, 'MeetingTime_1jam.csv'), usecols=['Kode','Jadwal','Group1','Group2','Group3','Blocked','WaktuAkhir'], converters={"Group1":int,"Group2":int,"Group3":int,"Blocked":int,"WaktuAkhir":int}).values.tolist()
        COURSE_DATA = pd.read_csv(os.path.join(DATA_DIR, 'DataPenjadwalan.csv'))
        INSTRUCTORS = COURSE_DATA[['InisialDosen','NamaDosen']].drop_duplicates().values.tolist()
    except FileNotFoundError as e:
        print(f"Error: File tidak ditemukan - {e}.")
        exit()

    def __init__(self):
        self._rooms, self._meeting_times_4jam, self._meeting_times_2jam, self._meeting_times_1jam, self._instructors, self._courses = [], [], [], [], [], []
        for num, cap in self.ROOMS:
            self._rooms.append(Room(number=num, seating_capacity=int(cap)))
        for mt in self.MEETING_TIMES_4JAM:
            self._meeting_times_4jam.append(MeetingTime(id=mt[0], time=mt[1], sks=4, groups={'g1': mt[2]}, is_blocked=(mt[3]==1), is_edge_time=False))
        for mt in self.MEETING_TIMES_2JAM:
            self._meeting_times_2jam.append(MeetingTime(id=mt[0], time=mt[1], sks=2, groups={'g1': mt[2], 'g2': mt[3], 'g3': mt[4]}, is_blocked=(mt[5]==1), is_edge_time=False))
        for mt in self.MEETING_TIMES_1JAM:
            self._meeting_times_1jam.append(MeetingTime(id=mt[0], time=mt[1], sks=1, groups={'g1': mt[2], 'g2': mt[3], 'g3': mt[4]}, is_blocked=(mt[5]==1), is_edge_time=(mt[6]==1)))
        instructor_map = {ins[0]: Instructor(id=ins[0], name=ins[1]) for ins in self.INSTRUCTORS}
        self._instructors = list(instructor_map.values())
        for _, row in self.COURSE_DATA.iterrows():
            dosen_obj = [instructor_map.get(row['InisialDosen'])]
            self._courses.append(Course(number=row['KodeMatkul'], name=row['NamaMatkul'], sks=row['sks'], instructors=dosen_obj, max_students=row['KuotaMatkul'], student_group=(row['Tingkat'], row['Kelas']), is_fixed=(row['jadwalfix'] == 1), is_difficult=(row['MatkulSusah'] == 1), course_type=row['Tipe'], fixed_schedule_4jam=row['jadwal4jam'], fixed_schedule_2jam=row['jadwal2jam'], fixed_schedule_1jam=row['jadwal1jam']))
        self._number_of_classes = len(self._courses)

    def get_rooms(self): return self._rooms
    def get_instructors(self): return self._instructors
    def get_courses(self): return self._courses
    def get_meeting_times(self, sks):
        if sks == 4: return self._meeting_times_4jam
        if sks == 2: return self._meeting_times_2jam
        if sks == 1: return self._meeting_times_1jam
        return []
    def get_number_of_classes(self): return self._number_of_classes

# KELAS UTAMA UNTUK ALGORITMA GENETIKA
class Schedule:
    def __init__(self):
        self._data = data
        self._classes = []
        self._num_of_conflicts = 0
        self._fitness = -1
        self._is_fitness_changed = True

    def initialize(self):
        courses = self._data.get_courses()
        for i, course in enumerate(courses):
            new_class = Class(i, course)
            new_class.instructor = course.instructors[0]
            if course.sks == 4:
                new_class.meeting_times[4] = random.choice(self._data.get_meeting_times(4))
                new_class.room = Room("Lab Komputer", 45) # Asumsi Lab Komputer ada, bisa dibuat lebih dinamis
            else:
                new_class.room = random.choice(self._data.get_rooms())
                if course.sks == 3:
                    new_class.meeting_times[2] = random.choice(self._data.get_meeting_times(2))
                    new_class.meeting_times[1] = random.choice(self._data.get_meeting_times(1))
                elif course.sks == 2:
                    new_class.meeting_times[2] = random.choice(self._data.get_meeting_times(2))
                elif course.sks == 1:
                    new_class.meeting_times[1] = random.choice(self._data.get_meeting_times(1))
            self._classes.append(new_class)
        return self

    def calculate_fitness(self):
        hard_conflicts, soft_conflicts = 0, 0
        dosen_times, room_times, group_times = {}, {}, {}

        for c in self._classes:
            course, sks, instructor_id, room_num = c.course, c.course.sks, c.instructor.id, c.room.number
            group = course.student_group
            # <-- FIX 2: Menggunakan .meeting_times.get()
            times = [c.meeting_times.get(s) for s in [1, 2, 4] if c.meeting_times.get(s) is not None]

            if constraints_loader.is_enabled('K2') and course.course_type != 3 and c.room.seating_capacity < course.max_students:
                hard_conflicts += 1
            
            mt2 = c.meeting_times.get(2)
            mt1 = c.meeting_times.get(1)
            mt4 = c.meeting_times.get(4)

            if sks == 3 and mt1 and mt2:
                if constraints_loader.is_enabled('K_internal') and mt2.groups.get('g1') == mt1.groups.get('g1'): hard_conflicts += 1 # <-- FIX 5
                if (constraints_loader.is_enabled('K6') or constraints_loader.is_enabled('K7')) and (mt2.is_blocked or mt1.is_blocked): hard_conflicts += 1
                if constraints_loader.is_enabled('L1') and mt1.is_edge_time: soft_conflicts += 1 # <-- FIX 6
            elif sks == 2 and mt2 and constraints_loader.is_enabled('K6') and mt2.is_blocked:
                hard_conflicts += 1
            elif sks == 4 and mt4 and constraints_loader.is_enabled('K6') and mt4.is_blocked:
                hard_conflicts += 1

            for t in times:
                if constraints_loader.is_enabled('K3'):
                    if (instructor_id, t.id) in dosen_times: hard_conflicts += 1
                    else: dosen_times[(instructor_id, t.id)] = c
                if constraints_loader.is_enabled('K_internal'):
                    if (room_num, t.id) in room_times: hard_conflicts += 1
                    else: room_times[(room_num, t.id)] = c
                if constraints_loader.is_enabled('K1'):
                    if (group, t.id) in group_times: hard_conflicts += 1
                    else: group_times[(group, t.id)] = c

        for i in range(len(self._classes)):
            for j in range(i + 1, len(self._classes)):
                c1, c2 = self._classes[i], self._classes[j]
                if self.check_time_overlap(c1, c2):
                    c1_course, c2_course = c1.course, c2.course
                    if constraints_loader.is_enabled('K4') and c1_course.course_type == 3 and c2_course.course_type == 3:
                        if (c1_course.student_group[0] == 2 and c2_course.student_group[0] == 3) or \
                           (c2_course.student_group[0] == 2 and c1_course.student_group[0] == 3): # <-- FIX 4
                            hard_conflicts += 1
                    if constraints_loader.is_enabled('K5') and c1_course.student_group[0] == 4 and c2_course.student_group[0] == 4 and c1_course.course_type != c2_course.course_type:
                        hard_conflicts += 1
                    if constraints_loader.is_enabled('L2') and c1_course.is_difficult and c2_course.is_difficult:
                        if (c1_course.student_group[0] == 2 and c2_course.student_group[0] == 3) or \
                           (c2_course.student_group[0] == 2 and c1_course.student_group[0] == 3):
                            soft_conflicts += 1
        
        self._num_of_conflicts = hard_conflicts + soft_conflicts
        return 1 / (self._num_of_conflicts + 1)
    
    def check_time_overlap(self, c1, c2):
        c1_times = [c1.meeting_times.get(sks) for sks in [1, 2, 4] if c1.meeting_times.get(sks) is not None]
        c2_times = [c2.meeting_times.get(sks) for sks in [1, 2, 4] if c2.meeting_times.get(sks) is not None]
        for t1 in c1_times:
            for t2 in c2_times:
                if t1.id == t2.id: return True
                if t1.sks == 4 or t2.sks == 4:
                    if t1.groups.get('g1') == t2.groups.get('g3'): return True
                    if t2.groups.get('g1') == t1.groups.get('g3'): return True
                if t1.sks != 4 and t2.sks != 4:
                    if t1.groups.get('g2') == t2.groups.get('g2'): return True
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
        child_schedule = Schedule().initialize()
        for i in range(len(child_schedule.get_classes())):
            if random.random() < CROSSOVER_RATE:
                child_schedule.get_classes()[i] = parent1.get_classes()[i]
            else:
                child_schedule.get_classes()[i] = parent2.get_classes()[i]
        return child_schedule
    def _mutate_schedule(self, schedule_to_mutate):
        temp_schedule = Schedule().initialize()
        for i in range(len(schedule_to_mutate.get_classes())):
            if random.random() < MUTATION_RATE:
                schedule_to_mutate.get_classes()[i] = temp_schedule.get_classes()[i]
        return schedule_to_mutate
    def _tournament_selection(self, pop):
        tournament_pop = Population(0)
        for _ in range(TOURNAMENT_SELECTION_SIZE):
            tournament_pop.get_schedules().append(random.choice(pop.get_schedules()))
        tournament_pop.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
        return tournament_pop

class DisplayManager:
    def print_schedule_as_table(self, schedule, generation_number, elapsed_time):
        classes = schedule.get_classes()
        print(f"\n======================================================================================\n JADWAL KULIAH TERBAIK (Generasi #{generation_number})\n > Fitness: {schedule.get_fitness():.5f}\n > Jumlah Konflik: {schedule.get_num_of_conflicts()}\n > Waktu Komputasi: {elapsed_time:.2f} detik\n======================================================================================")
        table = prettytable.PrettyTable(['No', 'Mata Kuliah (Kode, SKS, Kuota)', 'Kelompok', 'Ruangan (Kap.)', 'Dosen', 'Jadwal'])
        for i, current_class in enumerate(classes):
            course, sks = current_class.course, current_class.course.sks
            # <-- FIX 3: Menggunakan .meeting_times.get() dan .time
            mt2 = current_class.meeting_times.get(2)
            mt1 = current_class.meeting_times.get(1)
            mt4 = current_class.meeting_times.get(4)
            if sks == 3 and mt1 and mt2: jadwal_str = f"{mt2.time} & {mt1.time}"
            elif sks == 2 and mt2: jadwal_str = mt2.time
            elif sks == 4 and mt4: jadwal_str = mt4.time
            elif sks == 1 and mt1: jadwal_str = mt1.time
            else: jadwal_str = "N/A"
            table.add_row([
                str(i + 1),
                f"{course.name}\n({course.number}, {sks} SKS, {course.max_students} mhs)",
                f"Tingkat {course.student_group[0]} - Kelas {course.student_group[1]}", # <-- FIX 4
                f"{current_class.room.number} ({current_class.room.seating_capacity})",
                current_class.instructor.name,
                jadwal_str
            ])
        print(table)
        df = pd.DataFrame(table.rows, columns=table.field_names)
        df.to_csv("Jadwal_Final_Optimal.csv", index=False)
        print("\nJadwal optimal telah disimpan ke file 'Jadwal_Final_Optimal.csv'")

# MAIN EXECUTION BLOCK
if __name__ == '__main__':
    start_time = time.time()
    data = Data()
    display_manager = DisplayManager()
    print("\nMembuat populasi awal...")
    population = Population(POPULATION_SIZE)
    population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
    best_schedule = population.get_schedules()[0]
    print(f"\nMemulai proses evolusi untuk {MAX_GENERATION} generasi...")
    genetic_algorithm = GeneticAlgorithm()
    generation_num = 0
    with tqdm(total=MAX_GENERATION, desc="Evolusi Generasi") as pbar:
        for i in range(MAX_GENERATION):
            generation_num = i + 1
            population = genetic_algorithm.evolve(population)
            population.get_schedules().sort(key=lambda x: x.get_fitness(), reverse=True)
            best_schedule = population.get_schedules()[0]
            pbar.set_postfix({"Fitness Terbaik": f"{best_schedule.get_fitness():.4f}", "Konflik": best_schedule.get_num_of_conflicts()})
            pbar.update(1)
            if best_schedule.get_fitness() == 1.0:
                pbar.n = MAX_GENERATION
                pbar.refresh()
                print(f"\n\nSolusi optimal (fitness = 1.0) ditemukan pada generasi ke-{generation_num}!")
                break
    end_time = time.time()
    elapsed_time = end_time - start_time
    display_manager.print_schedule_as_table(best_schedule, generation_num, elapsed_time)