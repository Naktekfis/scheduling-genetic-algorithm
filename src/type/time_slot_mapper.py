import re
from typing import List, Dict, Tuple, Any

class TimeSlotMapper:
    def __init__(self, mt_1jam: List[Any], mt_2jam: List[Any], mt_4jam: List[Any]):
        self._mapping, self._lookup_1hr = self._build_mapping(mt_1jam, mt_2jam, mt_4jam)

    def _parse_time(self, time_str: str) -> Tuple[str, int, int]:
        """
        Mengubah string seperti 'Senin-07.00-09.00' menjadi ('Senin', 7, 9)
        """
        try:
            match = re.match(r'(\w+)-(\d{2})\.\d{2}-(\d{2})\.\d{2}', time_str)
            if match:
                day = match.group(1)
                start_hour = int(match.group(2))
                end_hour = int(match.group(3))
                if end_hour == 0: end_hour = 24
                return day, start_hour, end_hour
        except Exception as e:
            print(f"[PARSE ERROR] Tidak bisa parse '{time_str}': {e}")
        return "Unknown", 0, 0

    def _build_mapping(self, mt_1jam: List[Any], mt_2jam: List[Any], mt_4jam: List[Any]) -> Tuple[Dict[str, List[str]], Dict[Tuple[str, int, int], str]]:
        mapping = {}
        slots_1jam_lookup = {}

        # Bangun lookup slot 1-jam: (day, start_hour, end_hour) -> id
        for mt in mt_1jam:
            day, start_hour, end_hour = self._parse_time(mt.time)
            if day != "Unknown":
                slots_1jam_lookup[(day, start_hour, end_hour)] = mt.id

        # Bangun mapping untuk semua MeetingTime
        all_mts = mt_1jam + mt_2jam + mt_4jam
        for mt in all_mts:
            if mt.sks == 1:
                mapping[mt.id] = [mt.id]
            else:
                day, start_hour, end_hour = self._parse_time(mt.time)
                component_slots = []
                for hour in range(start_hour, end_hour):
                    key = (day, hour, hour+1)
                    if key in slots_1jam_lookup:
                        component_slots.append(slots_1jam_lookup[key])
                    else:
                        print(f"    [PERINGATAN] Slot 1-jam tidak ditemukan untuk {mt.id} ({mt.time}) pada {key}")
                mapping[mt.id] = component_slots

        sample_keys = list(mapping.keys())[:5]
        return mapping, slots_1jam_lookup

    def get_1hr_slots(self, meeting_time_id: str) -> List[str]:
        """
        Mengembalikan list ID slot 1-jam fundamental untuk sebuah MeetingTime ID.
        """
        return self._mapping.get(meeting_time_id, [])