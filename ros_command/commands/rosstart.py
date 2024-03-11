import argcomplete
import argparse

from ros_command.command_lib import run
from ros_command.completion import PackageCompleter
from ros_command.packages import find_executables_in_package, find_launch_files_in_package
from ros_command.workspace import get_ros_version, get_workspace_root


class StartCompleter:
    def __init__(self, version):
        self.version = version

    def __call__(self, parsed_args, **kwargs):
        ret = []
        ret += find_executables_in_package(parsed_args.package_name, self.version)
        ret += find_launch_files_in_package(parsed_args.package_name, self.version)
        return ret


async def main():
    build_type, workspace_root = get_workspace_root()
    version, distro = get_ros_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('package_name').completer = PackageCompleter(workspace_root)
    parser.add_argument('executable_or_launchfile').completer = StartCompleter(version)
    parser.add_argument('argv', nargs=argparse.REMAINDER)

    argcomplete.autocomplete(parser, always_complete_options=False)
    args = parser.parse_args()

    if args.executable_or_launchfile in find_executables_in_package(args.package_name, version):
        verb = 'run'
    else:
        verb = 'launch'

    command = []
    if version == 1:
        command.append(f'/opt/ros/{distro}/bin/ros{verb}')
    else:
        command.append(f'/opt/ros/{distro}/bin/ros2')
        command.append(verb)

    command += [args.package_name, args.executable_or_launchfile]

    command += args.argv

    code = await run(command)
    exit(code)
