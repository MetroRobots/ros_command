import argcomplete
import argparse
import pathlib

from ros_command.command_lib import run


async def main(debug=False):
    parser = argparse.ArgumentParser()
    parser.add_argument('path', type=pathlib.Path, default='.', nargs='?')

    argcomplete.autocomplete(parser)

    args, unknown_args = parser.parse_known_args()

    command = ['rosdep', 'install', '--ignore-src', '-y', '-r', '--from-paths', str(args.path)]

    code = await run(command + unknown_args)
    exit(code)
