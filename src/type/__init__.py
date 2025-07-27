# File: src/types/__init__.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# 'frozen=True' berarti objek ini tidak bisa diubah setelah dibuat.
# Ini membuat kode lebih aman karena data dasarnya tidak bisa diubah secara tidak sengaja.
@dataclass(frozen=True)
class Room:
    """Mewakili satu ruangan kelas."""
    number: str
    seating_capacity: int

    def __str__(self) -> str:
        return self.number

@dataclass(frozen=True)
class Instructor:
    """Mewakili seorang dosen."""
    id: str
    name: str

    def __str__(self) -> str:
        return self.name

@dataclass(frozen=True)
class MeetingTime:
    """Mewakili satu slot waktu."""
    id: str
    time: str
    sks: int
    groups: Dict[str, int]
    is_blocked: bool
    is_edge_time: bool

    def __str__(self) -> str:
        return self.time

@dataclass(frozen=True)
class Course:
    """Mewakili satu mata kuliah yang akan dijadwalkan."""
    number: str
    name: str
    sks: int
    instructors: List[Instructor]
    max_students: int
    student_group: tuple
    is_fixed: bool
    is_difficult: bool
    course_type: int
    fixed_schedule_4jam: Optional[str]
    fixed_schedule_2jam: Optional[str]
    fixed_schedule_1jam: Optional[str]

    def __str__(self) -> str:
        return f"{self.name} ({self.number})"

# Kelas ini TIDAK 'frozen' karena akan kita modifikasi selama algoritma berjalan.
@dataclass
class Class:
    """Mewakili satu sesi kelas spesifik dalam sebuah jadwal (kromosom)."""
    id: int
    course: Course
    instructor: Optional[Instructor] = None
    room: Optional[Room] = None
    # Menggunakan dictionary lebih fleksibel untuk menyimpan jadwal per SKS.
    meeting_times: Dict[int, MeetingTime] = field(default_factory=dict)

    def __str__(self) -> str:
        # Menggunakan f-string untuk output yang lebih bersih
        room_str = self.room.number if self.room else "N/A"
        instructor_str = self.instructor.id if self.instructor else "N/A"
        times_str = ", ".join(f"SKS{k}: {v.id}" for k, v in self.meeting_times.items()) if self.meeting_times else "N/A"
        return (f"Class ID {self.id} | Course: {self.course.number} | Room: {room_str} | "
                f"Instructor: {instructor_str} | Times: [{times_str}]")