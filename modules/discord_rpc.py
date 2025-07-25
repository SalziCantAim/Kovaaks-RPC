import os
import json
from pypresence import Presence

CLIENT_ID = 'DiscordClientID'


def get_playlist_share_code(installation_path):
    playlist_file = os.path.join(installation_path, "Saved", "SaveGames", "PlaylistInProgress.json")
    if os.path.exists(playlist_file):
        try:
            with open(playlist_file, 'r', encoding="UTF-16") as f:
                data = json.load(f)
                share_code = data.get("shareCode", None)
                if share_code:
                    return share_code
        except Exception as e:
            print(f"Error reading playlist share code: {e}")
    return None


def update_presence(rpc, scenario_name, start_time, highscore, session_highscore, online_score, installation_path):
    try:
        share_code = get_playlist_share_code(installation_path)
        details_text = f"Playing: {scenario_name}"

        if online_score is not None:
            state_text = f"Current Highscore is {online_score}"
        else:
            state_text = f"Current Highscore is {highscore}"

        buttons = []
        if share_code:
            buttons.append({"label": "Play Playlist",
                            "url": f"steam://run/824270/?action=jump-to-playlist;sharecode={share_code}"})
        else:
            buttons.append({"label": "View Scenario",
                            "url": f"steam://run/824270/?action=jump-to-scenario;name={scenario_name.replace(' ', '+')}"})

        rpc.update(
            details=details_text,
            state=state_text,
            start=start_time,
            large_image="kovaak_image",
            large_text=f"Session Highscore: {session_highscore}",
            small_text=f"Session Highscore: {session_highscore}",
            buttons=buttons if buttons else None
        )
    except Exception as e:
        print(f"Error updating Rich Presence: {e}")
