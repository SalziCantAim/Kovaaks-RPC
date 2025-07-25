import requests


class OnlineScoreAPI:
    def __init__(self):
        self.base_url = "https://kovaaks.com/webapp-backend"

    def search_scenario(self, scenario_name, max_results=1, page=0):
        try:
            encoded_name = scenario_name.replace(' ', '+')
            url = f"{self.base_url}/scenario/popular?page={page}&max={max_results}&scenarioNameSearch={encoded_name}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error searching scenario: {e}")
        return None

    def find_leaderboard_id(self, scenario_name):
        for page in range(5):
            for max_results in [1, 5]:
                data = self.search_scenario(scenario_name, max_results, page)
                if data and 'data' in data:
                    for scenario in data['data']:
                        if scenario.get('scenarioName') == scenario_name:
                            return scenario.get('leaderboardId')
        return None

    def get_user_score(self, leaderboard_id, username):
        try:
            url = f"{self.base_url}/leaderboard/scores/global?leaderboardId={leaderboard_id}&page=0&max=1&usernameSearch={username}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    return data['data'][0].get('score')
        except Exception as e:
            print(f"Error getting user score: {e}")
        return None

    def get_online_highscore(self, scenario_name, username):
        if not username:
            return None

        leaderboard_id = self.find_leaderboard_id(scenario_name)
        if leaderboard_id:
            return self.get_user_score(leaderboard_id, username)
        return None