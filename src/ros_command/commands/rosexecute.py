import argcomplete
import argparse
import asyncio

from betsy_ros import get_ros_version, get_workspace_root

from ros_command.command_lib import run, get_overlayed_command
from ros_command.completion import PackageCompleter, ExecutableNameCompleter, LaunchFileCompleter
from ros_command.packages import find_executables_in_package


class StartCompleter:
    def __init__(self, workspace_root=None, version=None):
        self.workspace_root = workspace_root
        self.version = version
        self.enc = ExecutableNameCompleter(workspace_root, version)
        self.lfc = LaunchFileCompleter(workspace_root, version)

    def __call__(self, **kwargs):
        return self.enc(**kwargs) + self.lfc(**kwargs)


async def main():
    build_type, workspace_root = get_workspace_root()
    version, distro = get_ros_version()

    parser = argparse.ArgumentParser()
    parser.add_argument('package_name').completer = PackageCompleter(workspace_root, version)
    parser.add_argument('executable_or_launchfile').completer = StartCompleter(workspace_root, version)
    parser.add_argument('argv', nargs=argparse.REMAINDER)

    argcomplete.autocomplete(parser, always_complete_options=False)
    args = parser.parse_args()

    if args.executable_or_launchfile in find_executables_in_package(args.package_name, version):
        verb = 'run'
    else:
        verb = 'launch'

    command = []
    if version == 1:
        command.append(await get_overlayed_command(f'ros{verb}'))
    else:
        command.append(f'/opt/ros/{distro}/bin/ros2')
        command.append(verb)

    command += [args.package_name, args.executable_or_launchfile]

    command += args.argv

    code = await run(command)
    exit(code)


def main_execute():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
