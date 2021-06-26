#!/usr/bin/env python3

from os import environ
from os.path import exists, join
from sys import stderr

import json

from numpy import nan
from pandas import concat, DataFrame
from requests import get

WD = join(environ["WD"], "model")
FILENAME = {
    "data": join(WD, "out", "data.json"),
    "players": join(WD, "out", "players.json"),
}
GAME_IDS = [
    "2020030171",
    "2020030172",
    "2020030173",
    "2020030174",
    "2020030175",
    "2020030176",
    "2020030177",
    "2020030241",
    "2020030242",
    "2020030243",
    "2020030244",
    "2020030311",
    "2020030312",
    "2020030313",
    "2020030314",
    "2020030315",
    "2020030316",
]


def load(path):
    print(f"`{path}`: loading", file=stderr)
    with open(path, "r") as file:
        return json.load(file)


def save(x, path):
    print(f"`{path}`: saving", file=stderr)
    with open(path, "w") as file:
        json.dump(x, file)


def download(url):
    print(f"`{url}`: downloading", file=stderr)
    response = get(url)
    assert response.status_code == 200
    return response.json()


def get_cache(game_id):
    path = {
        "game": join(WD, "out", f"game_{game_id}.json"),
        "shifts": join(WD, "out", f"shifts_{game_id}.json"),
    }
    if exists(path["game"]) and exists(path["shifts"]):
        game = load(path["game"])
        shifts = load(path["shifts"])
        if game["gameData"]["status"]["abstractGameState"] == "Final":
            return {
                "game": game,
                "shifts": shifts,
            }
    game = download("?".join([
        f"https://statsapi.web.nhl.com/api/v1/game/{game_id}/feed/live",
        "site=en_nhl",
    ]))
    shifts = download("?".join([
        "https://api.nhle.com/stats/rest/en/shiftcharts",
        f"cayenneExp=gameId={game_id}",
    ]))
    save(game, path["game"])
    save(shifts, path["shifts"])
    return {
        "game": game,
        "shifts": shifts,
    }


def to_seconds(time):
    assert len(time) == 5
    (minutes, seconds) = time.split(":")
    return (int(minutes) * 60) + int(seconds)


def unpack_game(blob):
    teams = []
    for venue in ["home", "away"]:
        team = blob["gameData"]["teams"][venue]
        teams.append({
            "team_id": team["id"],
            "venue": venue,
            "name": team["name"],
        })
    players = []
    for key in blob["gameData"]["players"].keys():
        player = blob["gameData"]["players"][key]
        players.append({
            "player_id": str(player["id"]),
            "first_name": player["firstName"],
            "last_name": player["lastName"],
            "handedness": player["shootsCatches"],
            "position": player["primaryPosition"]["name"],
        })
    shots = []
    for event in blob["liveData"]["plays"]["allPlays"]:
        event_result = event["result"]["event"]
        if event_result not in ["Blocked Shot", "Goal", "Missed Shot", "Shot"]:
            continue
        about = event["about"]
        team_id = event["team"]["id"]
        result = event["result"]
        player_id = None
        for player in event["players"]:
            if event_result == "Goal":
                if player["playerType"] == "Scorer":
                    player_id = str(player["player"]["id"])
                    break
            else:
                if player["playerType"] == "Shooter":
                    player_id = str(player["player"]["id"])
                    break
        shots.append({
            "event_id": about["eventId"],
            "period": about["period"],
            "time": to_seconds(about["periodTime"]),
            "team_id": team_id,
            "player_id": player_id,
            "type": result["event"],
            "secondary_type": result.get("secondaryType", ""),
            "goal": event_result == "Goal",
        })
    return {
        "teams": DataFrame(teams),
        "players": DataFrame(players),
        "shots": DataFrame(shots),
    }


def get_players_at(period_shifts, team_ids, second):
    subset = period_shifts.loc[
        (period_shifts.start_time <= second) &
        (second < period_shifts.end_time),
    ]
    blob = {
        "start_time": second,
    }
    goalie_rows = subset.position == "Goalie"
    for team in ["home", "away"]:
        team_rows = subset.team_id == team_ids[team]
        for (i, player_id) in enumerate(sorted(subset.loc[
            team_rows & (~goalie_rows),
            "player_id",
        ].unique())):
            blob[f"{team}_skater_id_{i}"] = player_id
        player_id = subset.loc[team_rows & goalie_rows, "player_id"].unique()
        assert len(player_id) <= 1
        if len(player_id) == 1:
            blob[f"{team}_goalie_id"] = player_id[0]
    return (subset.end_time.min(), blob)


def group_periods(teams, shifts):
    team_ids = {
        "home": teams.loc[teams.venue == "home", "team_id"].values[0],
        "away": teams.loc[teams.venue != "home", "team_id"].values[0],
    }
    assert team_ids["home"] in shifts.team_id.unique()
    assert team_ids["away"] in shifts.team_id.unique()
    assert shifts.team_id.nunique() == 2
    periods = []
    for period in shifts.period.unique():
        period_shifts = shifts.loc[shifts.period == period]
        assert period_shifts.start_time.min() == 0
        subsets = []
        end_time = period_shifts.end_time.max()
        i = 0
        while i < end_time:
            (i, subset_) = get_players_at(period_shifts, team_ids, i)
            subsets.append(subset_)
        subsets = DataFrame(subsets)
        subsets["period"] = period
        subsets["end_time"] = subsets.start_time \
            .astype("Int32") \
            .shift(-1) \
            .fillna(end_time) \
            .astype("int32")
        periods.append(subsets)
    periods = concat(periods, sort=True)
    for i in range(6):
        for column in [
            f"home_skater_id_{i}",
            f"away_skater_id_{i}",
        ]:
            if column not in periods.columns:
                periods[column] = nan
    periods["home_team_id"] = team_ids["home"]
    periods["away_team_id"] = team_ids["away"]
    periods["duration"] = periods.end_time - periods.start_time
    return periods


def unpack_shifts(teams, players, blob):
    assert 0 < blob["total"]
    shifts = DataFrame(blob["data"])
    shifts = shifts.loc[shifts.duration.notnull()].copy()
    assert (shifts.detailCode == 0).all()
    assert (shifts.typeCode == 517).all()
    assert shifts.eventDescription.isnull().all()
    assert shifts.eventDetails.isnull().all()
    shifts.drop(columns=[
        "gameId",
        "detailCode",
        "eventDescription",
        "eventDetails",
        "eventNumber",
        "hexValue",
        "typeCode",
        "teamAbbrev",
    ], inplace=True)
    shifts.rename(columns={
        "id": "shift_id",
        "startTime": "start_time",
        "endTime": "end_time",
        "teamId": "team_id",
        "teamName": "team_name",
        "playerId": "player_id",
        "firstName": "first_name",
        "lastName": "last_name",
        "shiftNumber": "shift_number",
    }, inplace=True)
    shifts.player_id = shifts.player_id.astype(str)
    for column in ["start_time", "end_time", "duration"]:
        shifts[column] = shifts[column].map(to_seconds)
    assert ((shifts.end_time - shifts.start_time) == shifts.duration).all()
    return group_periods(teams, shifts.merge(
        players[["player_id", "position"]],
        on="player_id",
        how="left",
    ))


def combine(shots, shifts):
    totals = []
    for row in shifts.itertuples():
        home_rows = shots.team_id == row.home_team_id
        away_rows = shots.team_id == row.away_team_id
        shared_rows = \
            (row.period == shots.period) & (row.start_time <= shots.time)
        if row.end_time == \
                shifts.loc[shifts.period == row.period, "end_time"].max():
            shared_rows &= shots.time <= row.end_time
        else:
            shared_rows &= shots.time < row.end_time
        home_shots = shots.loc[shared_rows & home_rows]
        away_shots = shots.loc[shared_rows & away_rows]
        totals.append({
            "period": row.period,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "home_shots": len(home_shots),
            "home_goals": home_shots.goal.sum(),
            "away_shots": len(away_shots),
            "away_goals": away_shots.goal.sum(),
        })
    totals = DataFrame(totals)
    shifts = shifts.merge(
        totals,
        on=["period", "start_time", "end_time"],
        how="outer",
    )
    assert shifts[["home_shots", "home_goals", "away_shots", "away_goals"]] \
        .notnull() \
        .values \
        .all()
    return shifts[[
        "period",
        "start_time",
        "end_time",
        "duration",
        "home_team_id",
        "away_team_id",
        "home_goalie_id",
        "home_skater_id_0",
        "home_skater_id_1",
        "home_skater_id_2",
        "home_skater_id_3",
        "home_skater_id_4",
        "home_skater_id_5",
        "away_goalie_id",
        "away_skater_id_0",
        "away_skater_id_1",
        "away_skater_id_2",
        "away_skater_id_3",
        "away_skater_id_4",
        "away_skater_id_5",
        "home_shots",
        "home_goals",
        "away_shots",
        "away_goals",
    ]]


def get_players_shifts(game_id):
    blob = get_cache(game_id)
    game = unpack_game(blob["game"])
    shifts = unpack_shifts(game["teams"], game["players"], blob["shifts"])
    return (game["players"], combine(game["shots"], shifts))


def get_all(game_ids):
    all_players = []
    all_shifts = []
    for game_id in game_ids:
        (players, shifts) = get_players_shifts(game_id)
        all_players.append(players[["player_id", "first_name", "last_name"]])
        all_shifts.append(shifts)
    all_players = concat(all_players)
    all_players.drop_duplicates("player_id", inplace=True)
    return (all_players, concat(all_shifts))


def export(players, shifts):
    players["index"] = 1
    players["index"] = players["index"].cumsum()
    player_id_to_index = {
        row.player_id: row.index for row in players.itertuples()
    }
    player_index_to_name = {
        row.index: " ".join([row.first_name, row.last_name])
        for row in players.itertuples()
    }
    with open(FILENAME["players"], "w") as file:
        json.dump(player_index_to_name, file)
    shifts = shifts.groupby([
        "home_team_id",
        "away_team_id",
        "home_goalie_id",
        "home_skater_id_0",
        "home_skater_id_1",
        "home_skater_id_2",
        "home_skater_id_3",
        "home_skater_id_4",
        "home_skater_id_5",
        "away_goalie_id",
        "away_skater_id_0",
        "away_skater_id_1",
        "away_skater_id_2",
        "away_skater_id_3",
        "away_skater_id_4",
        "away_skater_id_5",
    ], as_index=False, dropna=False).agg({
        "duration": "sum",
        "home_shots": "sum",
        "home_goals": "sum",
        "away_shots": "sum",
        "away_goals": "sum",
    })
    shifts = shifts.loc[
        shifts.home_goalie_id.notnull() &
        shifts.home_skater_id_0.notnull() &
        shifts.home_skater_id_1.notnull() &
        shifts.home_skater_id_2.notnull() &
        shifts.home_skater_id_3.notnull() &
        shifts.home_skater_id_4.notnull() &
        shifts.home_skater_id_5.isnull() &
        shifts.away_goalie_id.notnull() &
        shifts.away_skater_id_0.notnull() &
        shifts.away_skater_id_1.notnull() &
        shifts.away_skater_id_2.notnull() &
        shifts.away_skater_id_3.notnull() &
        shifts.away_skater_id_4.notnull() &
        shifts.away_skater_id_5.isnull(),
    ]
    for team in ["home", "away"]:
        shifts[f"{team}_goalie"] = \
            shifts[f"{team}_goalie_id"].map(player_id_to_index)
        for i in range(5):
            shifts[f"{team}_skater_{i}"] = \
                shifts[f"{team}_skater_id_{i}"].map(player_id_to_index)
    data = {
        "n_obs": len(shifts),
        "n_players": len(player_id_to_index),
        "home_goalie": shifts.home_goalie.tolist(),
        "home_skater_0": shifts.home_skater_0.tolist(),
        "home_skater_1": shifts.home_skater_1.tolist(),
        "home_skater_2": shifts.home_skater_2.tolist(),
        "home_skater_3": shifts.home_skater_3.tolist(),
        "home_skater_4": shifts.home_skater_4.tolist(),
        "away_goalie": shifts.away_goalie.tolist(),
        "away_skater_0": shifts.away_skater_0.tolist(),
        "away_skater_1": shifts.away_skater_1.tolist(),
        "away_skater_2": shifts.away_skater_2.tolist(),
        "away_skater_3": shifts.away_skater_3.tolist(),
        "away_skater_4": shifts.away_skater_4.tolist(),
        "duration": shifts.duration.tolist(),
        "home_shots": shifts.home_shots.tolist(),
        "away_shots": shifts.away_shots.tolist(),
        "home_goals": shifts.home_goals.tolist(),
        "away_goals": shifts.away_goals.tolist(),
    }
    with open(FILENAME["data"], "w") as file:
        json.dump(data, file)


def main():
    export(*get_all(GAME_IDS))


if __name__ == "__main__":
    main()
