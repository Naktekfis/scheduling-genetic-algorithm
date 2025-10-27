import pandas as pd
import numpy as np
import os

def parse_time(time_str):
    """
    Parses a time string like '13.00-15.00' into start time, end time, and duration in hours.
    Returns (None, None, 0) if the time string is invalid or empty.
    """
    if not isinstance(time_str, str) or '-' not in time_str:
        return None, None, 0
    try:
        start_str, end_str = time_str.split('-')
        start_time = float(start_str.replace('.', '.'))
        end_time = float(end_str.replace('.', '.'))
        duration = end_time - start_time
        # Handle cases like 15.00-17.00 which might result in 2.0000000001
        duration = round(duration, 2)
        return start_time, end_time, duration
    except (ValueError, IndexError):
        # Return 0 duration for any parsing errors
        return None, None, 0

def find_schedule_violations(schedule_file, rooms_file, mt_1h_file, mt_2h_file, mt_4h_file):
    """
    Analyzes a schedule file and checks for various violations against a set of constraints.

    Args:
        schedule_file (str): Path to the main schedule CSV file.
        rooms_file (str): Path to the room capacity CSV file.
        mt_1h_file (str): Path to the 1-hour meeting time constraints CSV.
        mt_2h_file (str): Path to the 2-hour meeting time constraints CSV.
        mt_4h_file (str): Path to the 4-hour meeting time constraints CSV.

    Returns:
        list: A list of strings, where each string describes a specific violation found.
    """
    violations = []
    
    # --- 1. Load Data ---
    try:
        schedule_df = pd.read_csv(schedule_file)
        # Add 'Ruangan' column if it doesn't exist to prevent errors later
        if 'Ruangan' not in schedule_df.columns:
            schedule_df['Ruangan'] = 'N/A'
            violations.append("[WARNING] 'Ruangan' column not found in schedule file. Room-related checks will be skipped.")

        rooms_df = pd.read_csv(rooms_file, header=None, names=['Ruangan', 'Kapasitas'])
        
        # Load meeting time constraints
        mt_1h_df = pd.read_csv(mt_1h_file)
        mt_2h_df = pd.read_csv(mt_2h_file)
        mt_4h_df = pd.read_csv(mt_4h_file)
        
        # Store constraints in a dictionary for easy access
        constraint_dfs = {1: mt_1h_df, 2: mt_2h_df, 4: mt_4h_df}
        
    except FileNotFoundError as e:
        return [f"[ERROR] File not found: {e.filename}. Please check your file paths."]

    # --- 2. Pre-process Data: Create a tidy DataFrame of individual sessions ---
    sessions_data = []
    for index, row in schedule_df.iterrows():
        # Process up to 3 sessions per course
        for i in range(1, 4):
            day_col = f'Hari (Sesi {i})'
            time_col = f'Jam (Sesi {i})'
            
            day = row.get(day_col)
            time_str = row.get(time_col)

            if pd.notna(day) and pd.notna(time_str):
                start_time, end_time, duration = parse_time(time_str)
                if duration > 0:
                    sessions_data.append({
                        'original_row': index + 2, # +2 to match spreadsheet row number (1-based index + header)
                        'course_code': row['Kode'],
                        'course_name': row['Mata Kuliah'],
                        'sks': row['SKS'],
                        'kuota': row['Kuota'],
                        'dosen': row['Dosen'],
                        'ruangan': row['Ruangan'],
                        'hari': day,
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration': duration
                    })
    
    sessions_df = pd.DataFrame(sessions_data)
    if sessions_df.empty:
        return ["[ERROR] No valid sessions could be parsed from the schedule file."]

    # --- 3. Perform Validation Checks ---

    # 3a. SKS (Credit) vs. Total Duration Check
    # Assumption: 1 SKS = 1 hour of scheduled class time
    course_hours = sessions_df.groupby(['course_code', 'course_name', 'sks']).duration.sum().reset_index()
    for index, row in course_hours.iterrows():
        if row['sks'] != row['duration']:
            violations.append(
                f"[SKS Mismatch] Course '{row['course_name']} ({row['course_code']})' "
                f"requires {row['sks']} hours but is scheduled for {row['duration']} hours."
            )
            
    # 3b. Room Capacity Check
    if 'Ruangan' in schedule_df.columns and 'N/A' not in schedule_df['Ruangan'].unique():
        # Ensure room codes are of the same type for merging
        sessions_df['ruangan'] = pd.to_numeric(sessions_df['ruangan'], errors='coerce')
        rooms_df['Ruangan'] = pd.to_numeric(rooms_df['Ruangan'], errors='coerce')
        
        sessions_with_capacity = pd.merge(sessions_df, rooms_df, left_on='ruangan', right_on='Ruangan', how='left')
        
        for index, row in sessions_with_capacity.iterrows():
            if pd.isna(row['Kapasitas']):
                 violations.append(
                    f"[Room Not Found] Row {row['original_row']}: Room '{row['ruangan']}' "
                    f"for course '{row['course_name']}' is not listed in the rooms file."
                )
            elif row['kuota'] > row['Kapasitas']:
                violations.append(
                    f"[Capacity Exceeded] Row {row['original_row']}: Course '{row['course_name']}' "
                    f"has {row['kuota']} students, but Room '{row['ruangan']}' only has capacity for {int(row['Kapasitas'])}."
                )
    
    # 3c. Blocked Time Slots Check
    for index, row in sessions_df.iterrows():
        duration = int(row['duration'])
        if duration in constraint_dfs:
            # Format time for lookup, e.g., 'Senin-07.00-09.00'
            jadwal_str = f"{row['hari']}-{row['start_time']:.2f}-{row['end_time']:.2f}".replace('.', '.')
            
            constraint_df = constraint_dfs[duration]
            match = constraint_df[constraint_df['Jadwal'] == jadwal_str]
            
            if not match.empty and match['Blocked'].iloc[0] == 1:
                violations.append(
                    f"[Blocked Time] Row {row['original_row']}: Course '{row['course_name']}' "
                    f"is scheduled at a blocked time: {jadwal_str}."
                )

    # 3d. Dosen and Room Conflicts Check
    # Iterate through all unique pairs of sessions
    for i in range(len(sessions_df)):
        for j in range(i + 1, len(sessions_df)):
            s1 = sessions_df.iloc[i]
            s2 = sessions_df.iloc[j]
            
            # Check if sessions are on the same day
            if s1['hari'] == s2['hari']:
                # Check for time overlap: (StartA < EndB) and (EndA > StartB)
                if s1['start_time'] < s2['end_time'] and s1['end_time'] > s2['start_time']:
                    # Check for Dosen conflict
                    if s1['dosen'] == s2['dosen']:
                        violations.append(
                            f"[Professor Conflict] Rows {s1['original_row']} and {s2['original_row']}: "
                            f"Professor '{s1['dosen']}' is double-booked for '{s1['course_name']}' and '{s2['course_name']}' "
                            f"at {s1['hari']} {s1['start_time']:.2f}-{s1['end_time']:.2f}."
                        )
                    # Check for Room conflict (and ensure room is valid)
                    if 'N/A' not in str(s1['ruangan']) and s1['ruangan'] == s2['ruangan']:
                        violations.append(
                            f"[Room Conflict] Rows {s1['original_row']} and {s2['original_row']}: "
                            f"Room '{s1['ruangan']}' is double-booked for '{s1['course_name']}' and '{s2['course_name']}' "
                            f"at {s1['hari']} {s1['start_time']:.2f}-{s1['end_time']:.2f}."
                        )

    return violations


# --- Main Execution Block ---
if __name__ == "__main__":
    # --- CONFIGURATION ---
    # Please place your CSV files in the same directory as this script,
    # or provide the full file path.
    SCHEDULE_FILE_PATH = "Jadwal_Final_Optimal6.csv"
    ROOMS_FILE_PATH = "Ruangan.csv"
    MEETING_TIME_1H_PATH = "MeetingTime_1jam.csv"
    MEETING_TIME_2H_PATH = "MeetingTime_2jam.csv"
    MEETING_TIME_4H_PATH = "MeetingTime_4jam.csv"
    
    # Check if the main schedule file exists before running
    if not os.path.exists(SCHEDULE_FILE_PATH):
        print(f"Error: The main schedule file was not found: '{SCHEDULE_FILE_PATH}'")
        print("Please make sure the file is in the correct location and the name is spelled correctly.")
    else:
        print(f"--- Running Schedule Validation on '{SCHEDULE_FILE_PATH}' ---\n")
        
        # Find all violations
        found_violations = find_schedule_violations(
            SCHEDULE_FILE_PATH,
            ROOMS_FILE_PATH,
            MEETING_TIME_1H_PATH,
            MEETING_TIME_2H_PATH,
            MEETING_TIME_4H_PATH
        )
        
        # --- Print Results ---
        if found_violations:
            print(f"Found {len(found_violations)} violations:\n")
            for i, violation in enumerate(found_violations, 1):
                print(f"{i}. {violation}")
        else:
            print("Congratulations! No violations were found in the schedule.")
            
        print("\n--- Validation Complete ---")