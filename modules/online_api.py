import requests
import json
import os
from datetime import datetime, timedelta, timezone


class OnlineScoreAPI:
    CACHE_DIR = os.path.expanduser(os.path.join("~", ".kovaaks_cache"))
    CACHE_TTL = timedelta(weeks=1)

    def __init__(self):
        self.base_url = "https://kovaaks.com/webapp-backend"
        os.makedirs(self.CACHE_DIR, exist_ok=True)

        self.local_scores_file = "online_highscores.json"

    def _cache_path(self, username):
        safe_user = username.replace("/", "_")
        return os.path.join(self.CACHE_DIR, f"{safe_user}_scores.json")

    def _load_cache(self, username):
        path = self._cache_path(username)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            fetched_at_str = data.get('fetched_at')
            if not fetched_at_str:
                return None
            fetched_at = datetime.fromisoformat(fetched_at_str)
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - fetched_at < self.CACHE_TTL:
                return data.get('scores', {})
        except Exception:
            pass
        return None

    def _save_cache(self, username, scores):
        path = self._cache_path(username)
        data = {
            'fetched_at': datetime.now(timezone.utc).isoformat(),
            'scores': scores
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load_local_scores(self):
        if os.path.exists(self.local_scores_file):
            try:
                with open(self.local_scores_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('scores', {})
            except Exception as e:
                print(f"Error loading local scores: {e}")
        return {}

    def save_local_scores(self, scores, username):
        data = {
            'username': username,
            'last_updated': datetime.now().isoformat(),
            'scores': scores
        }
        try:
            with open(self.local_scores_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"Saved {len(scores)} scores to local file")
        except Exception as e:
            print(f"Error saving local scores: {e}")

    def update_local_score(self, scenario_name, new_score, username):
        local_scores = self.load_local_scores()
        current_score = local_scores.get(scenario_name, 0)

        if new_score > current_score:
            local_scores[scenario_name] = new_score
            self.save_local_scores(local_scores, username)
            print(f"Updated local score for '{scenario_name}': {current_score} -> {new_score}")
            return True
        return False

    def fetch_all_pages(self, username, max_per_page=100):
        url = f"{self.base_url}/user/scenario/total-play"
        all_data = []
        page = 0
        while True:
            params = {
                "username": username,
                "page": page,
                "max": max_per_page,
                "sort_param[]": "count"
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                break
            data = resp.json().get('data', [])
            if not data:
                break
            all_data.extend(data)
            if len(data) < max_per_page:
                break
            page += 1
        return all_data

    def extract_highest_scores(self, entries):
        scenario_scores = {}
        for entry in entries:
            scenario = entry.get('scenarioName', '').strip()
            score = entry.get('score') or entry.get('attributes', {}).get('score')
            try:
                score = float(score)
            except Exception:
                continue
            if scenario:
                scenario_scores[scenario] = max(scenario_scores.get(scenario, 0), score)
        return scenario_scores

    def fetch_user_scenario_scores(self, username):
        if not username:
            return {}


        local_scores = self.load_local_scores()


        cached = self._load_cache(username)
        if cached is not None:

            if not local_scores or len(cached) > len(local_scores):
                self.save_local_scores(cached, username)
            return cached


        print(f"Fetching online scores for user: {username}")
        entries = self.fetch_all_pages(username)
        scores = self.extract_highest_scores(entries)


        self._save_cache(username, scores)
        self.save_local_scores(scores, username)

        return scores

    def get_online_score(self, username, scenario_name):
        if not username or not scenario_name:
            return None


        local_scores = self.load_local_scores()
        if scenario_name in local_scores:
            return local_scores[scenario_name]


        all_scores = self.fetch_user_scenario_scores(username)
        return all_scores.get(scenario_name)

    def is_scenario_available_online(self, username, scenario_name):
        if not username or not scenario_name:
            return False


        local_scores = self.load_local_scores()
        if scenario_name in local_scores:
            return True


        scores = self.fetch_user_scenario_scores(username)
        return scenario_name in scores