import argparse
from tqdm import tqdm
from environments import SimulatedSpe_edEnv
from policies import RandomPolicy


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


def show(env, pol, fps=1):
    obs = env.reset()
    done = False

    while not done:
        for _ in range(60 // fps):
            if not env.render(screen_width=720, screen_height=720):
                return

        action = pol.act(*obs)
        obs, reward, done, _ = env.step(action)
    print(f"Reward: {reward}")

    # Show final state
    while True:
        if env.render(screen_width=720, screen_height=720):
            return


def render(env, pol, output_file):
    """Render the execution of a given pilicy in an environment."""
    from imageio_ffmpeg import write_frames

    obs = env.reset()
    done = False

    writer = write_frames(output_file, (720, 720), fps=1, codec="libx264", quality=8)
    writer.send(None)  # seed the generator
    writer.send(env.render(mode="rgb_array", screen_width=720, screen_height=720).copy(order='C'))

    while not done:
        action = pol.act(*obs)
        obs, _, done, _ = env.step(action)
        writer.send(env.render(mode="rgb_array", screen_width=720, screen_height=720).copy(order='C'))
    writer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='spe_ed')
    parser.add_argument('--render', type=str, default=None, help='Render simulation video.')
    parser.add_argument('--show', action='store_true', help='Show simulation.')
    args = parser.parse_args()

    env = SimulatedSpe_edEnv(40, 40, [RandomPolicy() for _ in range(5)])
    pol = RandomPolicy()

    if args.render is not None:
        render(env, pol, args.render)
    elif args.show:
        show(env, pol)
    else:
        simulate(env, pol)