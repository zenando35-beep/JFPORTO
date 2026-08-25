"""
Scoreboard — recolha diária de estatísticas de futebol
--------------------------------------------------------
Este script vai buscar jogos terminados à API gratuita football-data.org
para um conjunto de competições, e calcula por equipa:
  - % vitórias / empates / derrotas
  - golos marcados / sofridos por jogo
  - % dos golos marcados na 1ª parte vs 2ª parte
  - % jogos com mais de 2.5 golos
  - % jogos em que ambas as equipas marcaram (BTTS)
"""

import json
import os
import time
import urllib.request
import urllib.error

API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
BASE_URL = "https://api.football-data.org/v4"

COMPETITIONS = {
    "PL":  ("Premier League", "1ª Divisão"),
    "PD":  ("La Liga", "1ª Divisão"),
    "BL1": ("Bundesliga", "1ª Divisão"),
    "SA":  ("Serie A", "1ª Divisão"),
    "FL1": ("Ligue 1", "1ª Divisão"),
    "PPL": ("Primeira Liga", "1ª Divisão"),
    "BSA": ("Brasileirão", "Série A"),
    "CL":  ("Champions League", "Fase de Liga"),
}


def api_get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"X-Auth-Token": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Erro HTTP {e.code} em {path}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        print(f"Erro em {path}: {e}")
        return None


def blank_stats():
    return {
        "jogos": 0, "v": 0, "e": 0, "d": 0,
        "gm": 0, "gs": 0,
        "gols_1p": 0, "gols_2p": 0,
        "jogos_over25": 0, "jogos_btts": 0,
    }


def process_competition(code, league_name, division_name, output):
    matches_data = api_get(f"/competitions/{code}/matches?status=FINISHED")
    if not matches_data or "matches" not in matches_data:
        print(f"Sem dados para {league_name}")
        return

    teams = {}

    for m in matches_data["matches"]:
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        full = m["score"].get("fullTime", {})
        half = m["score"].get("halfTime", {})

        gh, ga = full.get("home"), full.get("away")
        if gh is None or ga is None:
            continue
        hh, ha = half.get("home") or 0, half.get("away") or 0

        for team_name, gf, gc, gf_half in (
            (home, gh, ga, hh),
            (away, ga, gh, ha),
        ):
            s = teams.setdefault(team_name, blank_stats())
            s["jogos"] += 1
            s["gm"] += gf
            s["gs"] += gc
            s["gols_1p"] += gf_half
            s["gols_2p"] += max(gf - gf_half, 0)
            if gf > gc:
                s["v"] += 1
            elif gf == gc:
                s["e"] += 1
            else:
                s["d"] += 1
            if (gh + ga) > 2.5:
                s["jogos_over25"] += 1
            if gh > 0 and ga > 0:
                s["jogos_btts"] += 1

    rows = []
    for team_name, s in teams.items():
        j = s["jogos"]
        if j == 0:
            continue
        total_golos = s["gols_1p"] + s["gols_2p"]
        rows.append({
            "t": team_name,
            "v": round(100 * s["v"] / j),
            "e": round(100 * s["e"] / j),
            "d": round(100 * s["d"] / j),
            "gm": round(s["gm"] / j, 2),
            "gs": round(s["gs"] / j, 2),
            "p1": round(100 * s["gols_1p"] / total_golos) if total_golos else 0,
            "p2": round(100 * s["gols_2p"] / total_golos) if total_golos else 0,
            "o25": round(100 * s["jogos_over25"] / j),
            "btts": round(100 * s["jogos_btts"] / j),
            "jogos_analisados": j,
        })

    rows.sort(key=lambda r: -r["v"])
    output.setdefault(league_name, {})[division_name] = rows
    print(f"{league_name}: {len(rows)} equipas processadas")


def main():
    if not API_KEY:
        print("ERRO: variável FOOTBALL_API_KEY não definida.")
        return

    output = {}
    for code, (league_name, division_name) in COMPETITIONS.items():
        process_competition(code, league_name, division_name, output)
        time.sleep(7)

    os.makedirs("data", exist_ok=True)
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Concluído. Dados guardados em data/data.json")


if __name__ == "__main__":
    main()
