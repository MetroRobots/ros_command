import argcomplete
import argparse

from ros_command.command_lib import run
from ros_command.completion import PackageCompleter, LaunchFileCompleter
from ros_command.workspace import get_ros_version, get_workspace_root


async def main():
    build_type, workspace_root = get_workspace_root()
    version, distro = get_ros_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('package_name').completer = PackageCompleter(workspace_root)
    parser.add_argument('launch_file_name').completer = LaunchFileCompleter(version)
    parser.add_argument('argv', nargs=argparse.REMAINDER)

    argcomplete.autocomplete(parser, always_complete_options=False)
    args = parser.parse_args()

    command = []
    if version == 1:
        command.append(f'/opt/ros/{distro}/bin/roslaunch')
    else:
        command.append(f'/opt/ros/{distro}/bin/ros2')
        command.append('launch')

    command += [args.package_name, args.launch_file_name]
    command += args.argv

    code = await run(command)
    exit(code)
