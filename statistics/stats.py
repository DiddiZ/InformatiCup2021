from pathlib import Path
import pandas as pd
from tqdm import tqdm
from environments.spe_ed import SavedGame
from statistics.log_files import get_log_files


def fetch_statistics(log_dir, csv_file, key_column='date'):
    # Seach for unprocessed log files
    known_log_files = set(pd.read_csv(csv_file)[key_column]) if Path(csv_file).exists() else set()
    new_log_files = [
        f for f in get_log_files(log_dir) if f.name[:-5] not in known_log_files and f.name[:-5] != "_name_mapping"
    ]  # exclude name mapping

    if len(new_log_files) > 0:
        # Process new log files
        results = []
        for log_file in tqdm(new_log_files, desc="Parsing new log files"):
            game = SavedGame.load(log_file)

            results.append(
                (
                    log_file.name[:-5],  # name of game
                    game.rounds,  # rounds
                    game.winner.name if game.winner is not None else None,  # winner
                    game.names[game.you - 1] if game.you is not None else None,  # you
                    game.names,  # names
                    game.width,
                    game.height,
                )
            )

        # Append new statisics
        df = pd.DataFrame(results, columns=[key_column, "rounds", "winner", "you", "names", "width", "height"])
        df.to_csv(csv_file, mode='a', header=len(known_log_files) == 0, index=False)

    # Return all data from csv
    return pd.read_csv(
        csv_file,
        parse_dates=["date"] if key_column == "date" else None,
        converters={"names": lambda x: x.strip("[]").replace("'", "").split(", ")}
    )


def get_win_rate(policy, stats, number_of_players=None, matchup_opponent=None, grid_size=None):
    '''Returns overall win rate for the selected policy by default or specific for a given opponent or size of the grid.

    Args:
            policy: full name of policy
            stats: pandas df of statistics from fetch_statistics
            matchup_opponent: full name of policy to compare against
            grid_size: width-height tuple

    '''
    relevant_games = stats[stats["names"].apply(lambda x: policy in x)]
    if number_of_players is not None:
        relevant_games = relevant_games[relevant_games["names"].map(len) == number_of_players]
    if matchup_opponent is not None:
        if matchup_opponent == policy:
            return None
        relevant_games = relevant_games[relevant_games["names"].str.contains(matchup_opponent, regex=False)]
    if grid_size is not None:
        relevant_games = relevant_games[(relevant_games["width"] == grid_size[0]) &
                                        (relevant_games["height"] == grid_size[1])]
    if len(relevant_games) == 0:
        return None

    won = (relevant_games['winner'] == policy).agg(['mean', 'count', 'std'])
    return won["mean"], won["count"], won["std"]


def create_matchup_stats(policy_names, policy_nick_names, stats, csv_file):
    '''Creates a matchup table and saves it as a csv.

    Args:
            policy_names: full name of policy
            policy_nick_names: policy nick names
            stats: pandas df of statistics from fetch_statistics
            csv_file: path to csv

    '''
    matchup_win_rates = []
    for policy_name in policy_names:
        policy_matchups = []
        for opponent_policy in policy_names:
            policy_matchups.append(get_win_rate(policy_name, stats, matchup_opponent=opponent_policy))
        matchup_win_rates.append(policy_matchups)
    df = pd.DataFrame(
        [[policy_nick_names[i], policy_names[i]] + matchup_win_rates[i] for i in range(len(policy_names))],
        columns=["Policy short", "Policy full"] + [f"vs{nick}" for nick in policy_nick_names]
    )
    df.to_csv(csv_file, mode='w', index=False)
