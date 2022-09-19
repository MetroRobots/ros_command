import click
import os
import pathlib
import re
from enum import Enum


class BuildType(Enum):
    CATKIN_MAKE = 1
    CATKIN_TOOLS = 2
    COLCON = 3


PACKAGE_NAME = re.compile(r'<name>(.*)</name>')


def _get_parent_dirs(cur_dir):
    """Iterate over all parent directories (including the starting directory)."""
    folder = cur_dir.resolve()
    while folder:
        yield folder
        if folder.parent == folder:
            return
        else:
            folder = folder.parent


def get_workspace_root(cur_dir=pathlib.Path('.')):
    """
    Return the workspace root and the type of workspace.

    If no build tool has been run yet, return the highest directory with a src subfolder
    If catkin_make or catkin build has been run, return the directory with the proper metadata.
    If colcon, there's no metadata, so we return the highest directory with a src subfolder AND a build subfolder.
    """
    prefix_path = os.environ.get('COLCON_PREFIX_PATH')
    if prefix_path:
        first = prefix_path.split(':')[0]
        install_dir = pathlib.Path(first)
        return BuildType.COLCON, install_dir.parent
    highest_candidate = None
    for folder in _get_parent_dirs(cur_dir):
        if (folder / '.catkin_workspace').exists():
            return BuildType.CATKIN_MAKE, folder
        elif (folder / '.catkin_tools').exists():
            return BuildType.CATKIN_TOOLS, folder
        elif (folder / 'src').exists():
            if (folder / 'build').exists():
                # If we're here, it is not CATKIN
                return BuildType.COLCON, folder
            highest_candidate = folder

    return None, highest_candidate


def get_package_name(folder):
    """If this folder is the root of a package, return the name of the package."""
    filename = folder / 'package.xml'
    if filename.exists():
        s = open(filename).read()
        m = PACKAGE_NAME.search(s)
        if m:
            return m.group(1)
        else:
            return folder.stem


def get_current_package_name(cur_dir=pathlib.Path('.')):
    """Return the name of the current package if currently within a (sub)folder of a package."""
    for folder in _get_parent_dirs(cur_dir):
        pkg_name = get_package_name(folder)
        if pkg_name:
            return pkg_name


def get_ros_version(fail_quietly=False):
    """Return ROS Version and Distro."""
    env = os.environ
    version = env.get('ROS_VERSION')
    distro = env.get('ROS_DISTRO')
    if version and distro:
        return int(version), distro

    if fail_quietly:
        return version, distro

    click.secho('Unable to determine ROS distro. Please source workspace.', fg='red')
    exit(-1)
