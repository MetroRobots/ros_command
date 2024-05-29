import argcomplete
import argparse
import asyncio

from betsy_ros import get_ros_version, get_workspace_root

from ros_command.command_lib import run, get_overlayed_command
from ros_command.completion import PackageCompleter, ExecutableNameCompleter


async def main(debug=False):
    build_type, workspace_root = get_workspace_root()
    version, distro = get_ros_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('package_name').completer = PackageCompleter(workspace_root)
    parser.add_argument('executable_name').completer = ExecutableNameCompleter(version)
    parser.add_argument('argv', nargs=argparse.REMAINDER)

    argcomplete.autocomplete(parser, always_complete_options=False)
    args = parser.parse_args()

    command = []
    if version == 1:
        rosrun = get_overlayed_command('rosrun')
        command.append(rosrun)
    else:
        command.append(f'/opt/ros/{distro}/bin/ros2')
        command.append('run')

    command += [args.package_name, args.executable_name]

    if debug or args.debug:
        command += ['--prefix', 'gdb -ex run --args']

    command += args.argv

    code = await run(command)
    exit(code)


def main_rosrun():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())


def main_rosdebug():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(debug=True))
