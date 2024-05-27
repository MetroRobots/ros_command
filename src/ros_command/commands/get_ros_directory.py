import argcomplete
import argparse
import asyncio
import sys

from betsy_ros import BuildType, get_workspace_root

from ros_command.command_lib import get_output
from ros_command.completion import PackageCompleter


async def main():
    build_type, workspace_root = get_workspace_root()

    parser = argparse.ArgumentParser()
    parser.add_argument('package', nargs='?').completer = PackageCompleter(workspace_root)

    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    if workspace_root is None:
        print('Cannot find your ROS workspace!', file=sys.stderr)
        exit(-1)

    if args.package is None:
        print(workspace_root.resolve())
        exit(0)

    if build_type == BuildType.COLCON:
        # ROS 2
        ret, out, err = await get_output(['ros2', 'pkg', 'prefix', args.package])
        if ret:
            print(err.strip())
        elif '/opt/ros' in out:
            out = out.strip()
            print(f'{out}/share/{args.package}')
        else:
            _, out, _ = await get_output(['colcon', 'list', '--packages-select', args.package, '--paths-only'],
                                         cwd=workspace_root)
            src_path = workspace_root / out.strip()
            print(src_path)
    else:
        # ROS 1
        _, out, _ = await get_output(['rospack', 'find', args.package])
        print(out.strip())


def main_get_dir():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
