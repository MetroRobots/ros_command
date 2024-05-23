import argcomplete
import argparse
import asyncio
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


def main_rosdep():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
