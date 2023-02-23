import argcomplete
import argparse

from ros_command.command_lib import run
from ros_command.workspace import get_ros_version


async def main(debug=False):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    argcomplete.autocomplete(parser)
    args, unknown_args = parser.parse_known_args()

    version, distro = get_ros_version()

    command = []
    if version == 1:
        command.append(f'/opt/ros/{distro}/bin/rosrun')
    else:
        command.append(f'/opt/ros/{distro}/bin/ros2')
        command.append('run')

    if debug or args.debug:
        command += ['--prefix', 'gdb -ex run --args']

    code = await run(command + unknown_args)
    exit(code)
