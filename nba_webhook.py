from flask import Flask, request, jsonify
from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import playercareerstats, teamdashboardbygeneralsplits
import time
import os

app = Flask(__name__)

# --- 헬퍼 함수들 ---

def get_team_id(team_name):
    for team in teams.get_teams():
        if team_name.lower() in team['full_name'].lower():
            return team['id'], team['full_name']
    return None, None

def get_player_id(player_name):
    for player in players.get_players():
        if player_name.lower() in player['full_name'].lower():
            return player['id'], player['full_name']
    return None, None

def get_team_off_rtg(team_id, season):
    try:
        time.sleep(1)
        stats = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
            team_id=team_id, season=season
        ).get_data_frames()[0]
        return round(stats['OffRtg'].values[0], 2)
    except Exception as e:
        print(f"[Error] get_team_off_rtg: {e}")
        return None

def get_player_season_avg(player_id, season):
    try:
        time.sleep(1)
        df = playercareerstats.PlayerCareerStats(player_id=player_id).get_data_frames()[0]
        season_id = f"2{season[2:4]}{season[5:7]}"  # 예: 2019-20 -> 21920
        row = df[df['SEASON_ID'] == season_id]
        if row.empty:
            return None
        return {
            "pts": round(row['PTS'].values[0], 1),
            "ast": round(row['AST'].values[0], 1),
            "reb": round(row['REB'].values[0], 1)
        }
    except Exception as e:
        print(f"[Error] get_player_season_avg: {e}")
        return None

def get_player_career_avg(player_id):
    try:
        time.sleep(1)
        df = playercareerstats.PlayerCareerStats(player_id=player_id).get_data_frames()[1]
        if df.empty:
            return None
        return {
            "pts": round(df['PTS'].values[0], 1),
            "ast": round(df['AST'].values[0], 1),
            "reb": round(df['REB'].values[0], 1)
        }
    except Exception as e:
        print(f"[Error] get_player_career_avg: {e}")
        return None

# --- 라우트들 ---

@app.route('/nba-stats', methods=['POST'])
def nba_team_stats():
    data = request.get_json()
    team_name = data.get('team')
    season = data.get('season')

    team_id, matched_name = get_team_id(team_name)
    if not team_id:
        return jsonify({"error": f"팀 '{team_name}'을 찾을 수 없습니다."}), 404

    off_rtg = get_team_off_rtg(team_id, season)
    if off_rtg is None:
        return jsonify({"error": "공격 효율성 데이터를 불러오는 데 실패했습니다."}), 500

    return jsonify({
        "team": matched_name,
        "season": season,
        "off_rtg": off_rtg
    })

@app.route('/nba-player', methods=['POST'])
def nba_player_stats():
    data = request.get_json()
    name = data.get("name")
    season = data.get("season")
    stat_type = data.get("stat_type")

    player_id, full_name = get_player_id(name)
    if not player_id:
        return jsonify({"error": f"선수 '{name}'을 찾을 수 없습니다."}), 404

    if stat_type == "career":
        stats = get_player_career_avg(player_id)
    elif stat_type == "season_avg" and season:
        stats = get_player_season_avg(player_id, season)
    else:
        return jsonify({"error": "stat_type이 잘못되었거나 시즌 정보가 없습니다."}), 400

    if stats is None:
        return jsonify({"error": "선수 통계를 불러오지 못했습니다."}), 500

    return jsonify({
        "player": full_name,
        "season": season,
        "stat_type": stat_type,
        "stats": stats
    })

@app.route('/nba-compare', methods=['POST'])
def nba_compare_players():
    data = request.get_json()
    player_names = data.get("players")
    season = data.get("season")
    stat_type = data.get("stat_type", "career")

    if not isinstance(player_names, list) or len(player_names) != 2:
        return jsonify({"error": "두 명의 선수 이름을 리스트로 입력해야 합니다."}), 400

    results = []
    for name in player_names:
        player_id, full_name = get_player_id(name)
        if not player_id:
            return jsonify({"error": f"선수 '{name}'을 찾을 수 없습니다."}), 404

        if stat_type == "career":
            stats = get_player_career_avg(player_id)
        elif stat_type == "season_avg" and season:
            stats = get_player_season_avg(player_id, season)
        else:
            return jsonify({"error": "stat_type이 잘못되었거나 시즌 정보가 없습니다."}), 400

        if stats is None:
            return jsonify({"error": f"선수 '{name}'의 통계를 불러오지 못했습니다."}), 500

        results.append({
            "name": full_name,
            "season": season,
            "stats": stats
        })

    return jsonify({"comparison": results})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
