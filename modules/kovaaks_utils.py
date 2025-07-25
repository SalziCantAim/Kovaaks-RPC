import os
import shutil
import psutil


def is_kovaaks_running():
    for process in psutil.process_iter(['name']):
        try:
            if 'FPSAimTrainer.exe' in process.info['name']:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def extract_scenario_name(file_path):
    try:
        with open(file_path, 'rb') as file:
            data = file.read()
            key = b'FullScenarioPath'
            key_pos = data.find(key)
            if key_pos == -1:
                return "Unknown Scenario"
            end = key_pos
            while end > 0 and (data[end - 1] < 32 or data[end - 1] > 126):
                end -= 1
            start = end - 1
            while start > 0 and 32 <= data[start] <= 126:
                start -= 1
            start += 1
            scenario_name = data[start:end].decode('utf-8')
            return scenario_name
    except Exception as e:
        print(f"Error reading file: {e}")
    return "Unknown Scenario"


def get_current_scenario():
    try:
        temp_file_path = os.path.join(os.getenv('LOCALAPPDATA'), "Temp", "session_copy.sav")
        source_path = os.path.join(os.getenv('LOCALAPPDATA'), "FPSAimTrainer", "Saved", "SaveGames", "session.sav")

        if os.path.exists(source_path):
            shutil.copy(source_path, temp_file_path)
            scenario_name = extract_scenario_name(temp_file_path)
            return scenario_name
    except Exception as e:
        print(f"Error getting current scenario: {e}")

    return "Unknown Scenario"


def find_initial_scores(scenario_name, stats_directory):
    highscore = 0
    temp_checked_files = set()
    for file_name in os.listdir(stats_directory):
        if file_name.startswith(scenario_name) and file_name.endswith('.csv'):
            file_path = os.path.join(stats_directory, file_name)
            try:
                with open(file_path, 'r') as file:
                    for line in file:
                        if "Score:," in line:
                            score = float(line.split(',')[1])
                            highscore = max(highscore, score)
                temp_checked_files.add(file_name)
            except Exception as e:
                print(f"Error reading file {file_name}: {e}")
    return round(highscore, 1), temp_checked_files


def find_fight_time_and_score(scenario_name, stats_directory, checked_files):
    max_score = 0
    found_new_score = False
    try:
        for file_name in os.listdir(stats_directory):
            if file_name.startswith(scenario_name) and file_name.endswith('.csv') and file_name not in checked_files:
                file_path = os.path.join(stats_directory, file_name)
                with open(file_path, 'r') as file:
                    for row in file:
                        if "Score:," in row:
                            score = float(row.split(',')[1])
                            max_score = max(max_score, score)
                            found_new_score = True
                            checked_files.add(file_name)
    except Exception as e:
        print(f"Error finding fight time and score: {e}")
    return round(max_score, 1), found_new_score