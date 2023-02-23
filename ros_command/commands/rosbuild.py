import argcomplete
import argparse
import os

from ros_command.build_tool import generate_build_command, get_package_selection_args, run_build_command
from ros_command.command_lib import run
from ros_command.workspace import BuildType, get_current_package_name, get_workspace_root
from ros_command.util import get_config


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--continue-on-failure', action='store_true')
    parser.add_argument('-j', '--jobs', type=int)
    parser.add_argument('-b', '--cmake-build-type')
    parser.add_argument('-t', '--test', action='store_true')
    parser.add_argument('-g', '--toggle-graphics', action='store_true')

    argcomplete.autocomplete(parser)

    args, unknown_args = parser.parse_known_args()

    build_type, workspace_root = get_workspace_root()
    if build_type is None:
        ros_version = int(os.environ.get('ROS_VERSION', 1))
        if ros_version == 2:
            build_type = BuildType.COLCON
        else:
            build_type = BuildType.CATKIN_TOOLS  # Defaults to catkin tools

    pkg_name = get_current_package_name()

    unknown_args, package_selection_args = get_package_selection_args(unknown_args, build_type, pkg_name)

    if args.test:
        command = generate_build_command(build_type, unknown_args, package_selection_args,
                                         args.continue_on_failure, args.jobs, args.cmake_build_type, workspace_root)
        print(' '.join(command))
        exit(0)

    code = await run_build_command(build_type, workspace_root, unknown_args, package_selection_args,
                                   args.continue_on_failure, args.jobs,
                                   args.cmake_build_type, args.toggle_graphics)

    # Sound Notification
    sound_path = None
    if code == 0:
        sound_path = get_config('success_sound')
    else:
        sound_path = get_config('fail_sound')
    if sound_path:
        await run(['aplay', '-q', sound_path])
    exit(code)
