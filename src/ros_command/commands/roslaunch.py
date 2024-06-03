import argcomplete
import argparse
import asyncio

from betsy_ros import get_ros_version, get_workspace_root

from ros_command.command_lib import run, get_overlayed_command
from ros_command.completion import PackageCompleter, LaunchArgCompleter, LaunchFileCompleter


async def main():
    build_type, workspace_root = get_workspace_root()
    version, distro = get_ros_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('package_name').completer = PackageCompleter(workspace_root)
    parser.add_argument('launch_file_name').completer = LaunchFileCompleter(version)
    parser.add_argument('argv', nargs=argparse.REMAINDER).completer = LaunchArgCompleter(workspace_root, version)

    argcomplete.autocomplete(parser, always_complete_options=False)
    args = parser.parse_args()

    command = []
    if version == 1:
        command.append(await get_overlayed_command('roslaunch'))
    else:
        command.append(f'/opt/ros/{distro}/bin/ros2')
        command.append('launch')

    command += [args.package_name, args.launch_file_name]
    command += args.argv

    code = await run(command)
    exit(code)


def main_launch():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
