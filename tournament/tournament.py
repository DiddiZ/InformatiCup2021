import matplotlib.pyplot as plt
import itertools as it
from tqdm import tqdm
from pathlib import Path
from environments.simulator import simulate
from environments.simulator import SimulatedSpe_edEnv
from environments.logging import TournamentLogger
import tournament.tournament_config


class TournamentEnv(SimulatedSpe_edEnv):
    def __init__(self, width, height, policies, seed=None):
        SimulatedSpe_edEnv.__init__(self, width, height, policies[1:])
        self.policies = policies

    def step(self):
        actions = []
        for player in self.players:  # Compute actions of players
            if player.active:
                policy = self.policies[player.player_id - 2]
                obs = self._get_obs(player)
                actions.append(policy.act(*obs))
            else:
                actions.append("change_nothing")

        # Perform simulation step
        _, _, self.rounds = simulate(self.cells, self.players, self.rounds, actions)

        done = sum(1 for p in self.players if p.active) < 2
        if done:
            for p in self.players:
                p.name = str(policy)
        return done

    def game_state(self):
        """Get current game state as dict."""
        return {
            'width': self.width,
            'height': self.height,
            'cells': self.cells.tolist(),
            'players': dict(p.to_dict() for p in self.players),
            'you': None,
            'running': sum(1 for p in self.players if p.active) > 1,
        }


def play_game(env, policies, game_number, show=False, fps=10, logger=None):
    """Simulate a single game with the given environment and policies"""
    if show and not env.render(screen_width=720, screen_height=720):
        return
    if logger is not None:  # Log initial state
        states = [env.game_state()]

    done = False
    while not done:
        done = env.step()

        if show and not env.render(screen_width=720, screen_height=720):
            return
        if logger is not None:
            states.append(env.game_state())

    if logger is not None:  # log states together with a mapping of player_id to policy
        logger.log(states, [pol["name"] for pol in policies], game_number)
    if show:  # Show final state
        while True:
            if not env.render(screen_width=720, screen_height=720):
                return
            plt.pause(0.01)  # Sleep


def run_tournament(show, log_dir):
    '''Run a sequence of games in different combinations of given policies and log their results'''
    # Create logger
    if log_dir is not None:
        directory = Path(log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        logger = TournamentLogger(log_dir)
    else:
        logger = None

    #ToDo: file name with width height
    # games with 2 to 6 players
    with tqdm(total=5, desc="Number of players(2-6)", position=0) as player_number_pbar:
        for tournament.tournament_config.number_players in range(2, 7):
            player_constellations = list(
                it.combinations(tournament.tournament_config.policy_list, tournament.tournament_config.number_players)
            )  # maybe with replacements
            # games with different policy combinations
            with tqdm(
                total=len(player_constellations),
                desc="Combinations",
                position=tournament.tournament_config.number_players - 1
            ) as constellation_pbar:
                for constellation in player_constellations:
                    # games with different map size
                    for game_number, (width, height) in enumerate(tournament.tournament_config.width_height_pairs):
                        # do not run games when log already exists
                        log_file = directory / "_".join([pol["name"] for pol in constellation])
                        if logger is not None and Path(log_file.as_posix() + f"_{game_number}.json").is_file():
                            continue
                        env = TournamentEnv(width, height, [c["pol"] for c in constellation])
                        env.reset()
                        # number of games to be played
                        for game in range(tournament.tournament_config.number_games):
                            play_game(env, constellation, game_number, show=show, logger=logger)
                    constellation_pbar.update()
            player_number_pbar.update()
