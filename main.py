import argparse
import time
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from environments import SimulatedSpe_edEnv, WebsocketEnv
from environments.logging import Spe_edLogger, CloudUploader
from environments.spe_ed import SavedGame
from policies import RandomPolicy
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


def simulate(env, pol):
    with tqdm() as pbar:
        runs, wins = 0, 0
        while True:
            obs = env.reset()
            done = False

            while not done:
                action = pol.act(*obs)
                obs, reward, done, _ = env.step(action)

            runs += 1
            if reward > 0:
                wins += 1
            pbar.update()
            pbar.set_description(f"{pol} {wins/runs:.2f}")


def show(env, pol, fps=None, keep_open=True):
    obs = env.reset()
    done = False

    start = time.time()
    with tqdm() as pbar:
        while not done:
            if fps is None or (time.time() - start) * fps < env.rounds:  # Only render if there is time
                if not env.render(screen_width=720, screen_height=720):
                    return
                if fps is not None and (time.time() - start) * fps < env.rounds:
                    plt.pause(1 / fps)  # Sleep

            action = pol.act(*obs)
            obs, reward, done, _ = env.step(action)
            pbar.update()

    if keep_open:
        # Show final state
        while True:
            if not env.render(screen_width=720, screen_height=720):
                return
            plt.pause(0.01)  # Sleep


def render(env, pol, output_file):
    """Render the execution of a given pilicy in an environment."""
    from imageio_ffmpeg import write_frames

    obs = env.reset()
    done = False

    writer = write_frames(output_file, (720, 720), fps=1, codec="libx264", quality=8)
    writer.send(None)  # seed the generator
    writer.send(env.render(mode="rgb_array", screen_width=720, screen_height=720).copy(order='C'))

    with tqdm() as pbar:
        while not done:
            action = pol.act(*obs)
            obs, _, done, _ = env.step(action)
            writer.send(env.render(mode="rgb_array", screen_width=720, screen_height=720).copy(order='C'))
            pbar.update()
    writer.close()


def render_logfile(log_file, fps=10):
    """Render logfile to mp4"""
    from visualization import Spe_edAx, render_video

    game = SavedGame.load(log_file)

    fig = plt.figure(
        figsize=(720 / 100, 720 / 100),
        dpi=100,
        tight_layout=True,
    )
    ax = plt.subplot(1, 1, 1)
    viewer = Spe_edAx(fig, ax, game.cell_states[0], game.player_states[0])

    def frames():
        """Draw all game states"""
        for i in tqdm(range(len(game.cell_states)), desc="Rendering"):
            viewer.update(game.cell_states[i], game.player_states[i])
            fig.canvas.draw()

            frame = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8).reshape(720, 720, 3)
            yield frame

    width, height = fig.canvas.get_width_height()
    render_video(log_file.parent / (log_file.name[:-5] + ".mp4"), frames(), width, height, fps=20)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='spe_ed')
    parser.add_argument('--render', type=str, default=None, help='Render simulation to video.')
    parser.add_argument('--render-logfile', type=str, default=None, help='Render logfile to video.')
    parser.add_argument('--show', action='store_true', help='Show simulation.')
    parser.add_argument('--sim', action='store_true', help='Use simulator.')
    parser.add_argument('--log_dir', type=str, default="logs/", help='Directory for logs.')
    parser.add_argument('--upload', action='store_true', help='Use simulator.')
    parser.add_argument('--fps', type=int, default=None, help='FPS for showing.')
    args = parser.parse_args()

    if args.render_logfile:
        render_logfile(Path(args.render_logfile))
        quit()

    if args.sim:
        env = SimulatedSpe_edEnv(40, 40, [RandomPolicy() for _ in range(5)])
    else:
        logger_callbacks = []
        if args.upload:
            logger_callbacks.append(
                CloudUploader(
                    os.environ["CLOUD_URL"], os.environ["CLOUD_USER"], os.environ["CLOUD_PASSWORD"], remote_dir="logs/"
                ).upload
            )

        env = WebsocketEnv(
            os.environ["URL"],
            os.environ["KEY"],
            logger=Spe_edLogger(args.log_dir, logger_callbacks),
        )
    pol = RandomPolicy()

    if args.render is not None:
        render(env, pol, args.render)
    elif args.show:
        show(env, pol, fps=args.fps)
    else:
        simulate(env, pol)
