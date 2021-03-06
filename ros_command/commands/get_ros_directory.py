import argparse
import sys

from ros_command.command_lib import get_output
from ros_command.workspace import BuildType, get_workspace_root


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('package', nargs='?')
    args = parser.parse_args()

    build_type, workspace_root = get_workspace_root()
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
