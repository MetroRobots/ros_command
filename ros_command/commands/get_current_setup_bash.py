import sys

from ros_command.workspace import BuildType, get_workspace_root


def main():
    build_type, workspace_root = get_workspace_root()
    if workspace_root is None:
        print('Cannot find your ROS workspace!', file=sys.stderr)
        exit(-1)

    # Check for a setup.bash in the root, which can be used to override additional variables
    # (i.e. set annoying things like IGN_GAZEBO_RESOURCE_PATH)
    root_setup = workspace_root / 'setup.bash'
    if root_setup.exists():
        print(root_setup)
        return

    if build_type == BuildType.COLCON:
        print(workspace_root / 'install/setup.bash')
    else:
        print(workspace_root / 'devel/setup.bash')
