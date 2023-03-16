import argcomplete
import argparse

from ros_command.command_lib import run
from ros_command.completion import PackageCompleter, ExecutableNameCompleter
from ros_command.workspace import get_ros_version, get_workspace_root


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
        command.append(f'/opt/ros/{distro}/bin/rosrun')
    else:
        command.append(f'/opt/ros/{distro}/bin/ros2')
        command.append('run')

    command += [args.package_name, args.executable_name]

    if debug or args.debug:
        command += ['--prefix', 'gdb -ex run --args']

    command += args.argv

    code = await run(command)
    exit(code)
