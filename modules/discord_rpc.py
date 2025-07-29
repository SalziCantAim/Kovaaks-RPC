import os
import json
import codecs
from pypresence import Presence

CLIENT_ID = '1321990331083784202'


def get_playlist_share_code(installation_path):
    playlist_file = os.path.join(installation_path, "Saved", "SaveGames", "PlaylistInProgress.json")
    if not os.path.exists(playlist_file):
        return None

    try:
        with open(playlist_file, 'rb') as f:
            raw = f.read()
        raw  = str(raw)
        raw = raw.split('"shareCode": "')[1].split(r'",\r\n\t"version": ')[0]
        return raw



    except (json.JSONDecodeError, Exception) as e:
        print(f"Error reading playlist file: {e}")
        return None


def update_presence(rpc, scenario_name, start_time, highscore, session_highscore, online_score, installation_path):
    if not rpc:
        print("RPC object is None, cannot update presence")
        return

    try:
        if not scenario_name or scenario_name == "Unknown Scenario":
            print("Invalid scenario name, skipping presence update")
            return

        share_code = get_playlist_share_code(installation_path)

        details_text = f"Playing: {scenario_name}"

        if online_score is not None:
            state_text = f"Highscore: {online_score}"
        else:
            state_text = f"Highscore: {highscore}"

        buttons = []
        if share_code:
            buttons.append({
                "label": "Play Playlist",
                "url": f"steam://run/824270/?action=jump-to-playlist;sharecode={share_code}"
            })
        else:
            encoded_scenario = scenario_name.replace(' ', '%20').replace('&', '%26')
            buttons.append({
                "label": "View Scenario",
                "url": f"steam://run/824270/?action=jump-to-scenario;name={encoded_scenario}"
            })

        presence_data = {
            "details": details_text,
            "state": state_text,
            "start": int(start_time) if start_time else None,
            "large_image": "kovaak_image",
            "large_text": f"Session Best: {session_highscore}",
            "small_text": f"Session Best: {session_highscore}",
        }

        if buttons:
            presence_data["buttons"] = buttons

        print(f"Updating presence for: {scenario_name}")
        rpc.update(**presence_data)

    except Exception as e:
        print(f"Error updating Rich Presence: {e}")
