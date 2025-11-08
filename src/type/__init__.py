from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass(frozen=True)
class Instructor:
    """Mewakili seorang dosen (identitasnya saja)."""
    id: str
    name: str

    def __str__(self) -> str:
        return self.name

@dataclass(frozen=True)
class MeetingTime:
    """Mewakili satu slot waktu yang telah ditentukan."""
    id: str
    time: str
    sks: int
    groups: Dict[str, int]
    is_blocked: bool
    is_edge_time: bool

    def __str__(self) -> str:
        return self.time

@dataclass(frozen=True)
class Room:
    """Mewakili sebuah ruangan dengan kapasitasnya."""
    id: str  # Kode/nama ruangan
    capacity: int
    
    def __str__(self) -> str:
        return f"{self.id} (Kapasitas: {self.capacity})"

@dataclass(frozen=True)
class AssignedInstructor:
    """Mengikat sebuah objek Instructor dengan perannya."""
    instructor: Instructor
    role: str  # Contoh: "utama", "sekunder"

@dataclass(frozen=True)
class Course:
    """
    Mewakili data mentah sebuah mata kuliah dari CSV.
    Urutan field di sini telah diperbaiki.
    """
    # SEMUA FIELD WAJIB (TANPA NILAI DEFAULT)
    number: str
    name: str
    sks: int
    max_students: int
    student_group: tuple
    is_fixed: bool
    is_difficult: bool
    course_type: int
    
    # SEMUA FIELD OPSIONAL (DENGAN NILAI DEFAULT)
    assigned_instructors: List[AssignedInstructor] = field(default_factory=list)
    fixed_schedules: List[Optional[str]] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.name} ({self.number})"


@dataclass
class Class:
    """
    Mewakili SATU mata kuliah dalam sebuah jadwal (kromosom).
    """
    id: int
    course: Course
    instructor: Optional[Instructor] = None 
    meeting_times: List[MeetingTime] = field(default_factory=list)
    rooms: List[Optional[Room]] = field(default_factory=list)  # Room untuk setiap sesi

    def __str__(self) -> str:
        # Tampilan string di-update untuk mencerminkan struktur baru
        instructor_str = self.instructor.id if self.instructor else "N/A"
        # Sekarang hanya menampilkan ID dari MeetingTime
        times_str = ", ".join(mt.id for mt in self.meeting_times)
        return (f"Class ID {self.id} | Course: {self.course.number} | "
                f"Instructor: {instructor_str} | Times: [{times_str}]")