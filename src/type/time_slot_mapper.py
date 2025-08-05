import re
from typing import List, Dict, Tuple, Any

class TimeSlotMapper:
    def __init__(self, mt_1jam: List[Any], mt_2jam: List[Any], mt_4jam: List[Any]):
        self._mapping = self._build_mapping(mt_1jam, mt_2jam, mt_4jam)

    def _parse_time(self, time_str: str) -> Tuple[str, int, int]:
        try:
            parts = time_str.split('-')
            day = parts[0]
            start_hour = int(parts[1].split('.')[0])
            end_hour = int(parts[2].split('.')[0])
            return day, start_hour, end_hour
        except (IndexError, ValueError):
            return "Unknown", 0, 0

    def _build_mapping(self, mt_1jam: List[Any], mt_2jam: List[Any], mt_4jam: List[Any]) -> Dict[str, List[str]]:
        mapping = {}
        slots_1jam_lookup = {}
        for mt in mt_1jam:
            day, start_hour, _ = self._parse_time(mt.time)
            slots_1jam_lookup[(day, start_hour)] = mt.id
        
        all_mts = mt_1jam + mt_2jam + mt_4jam
        for mt in all_mts:
            if mt.sks == 1:
                mapping[mt.id] = [mt.id]
            else:
                day, start_hour, end_hour = self._parse_time(mt.time)
                component_slots = []
                for hour in range(start_hour, end_hour):
                    if (day, hour) in slots_1jam_lookup:
                        component_slots.append(slots_1jam_lookup[(day, hour)])
                mapping[mt.id] = component_slots
        return mapping

    def get_1hr_slots(self, meeting_time_id: str) -> List[str]:
        return self._mapping.get(meeting_time_id, [])