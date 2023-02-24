import os

from rosdep2.ament_packages import get_packages_with_prefixes, AMENT_PREFIX_PATH_ENV_VAR
from rosdep2.catkin_packages import find_catkin_packages_in

ROS_PACKAGE_PATH = 'ROS_PACKAGE_PATH'


def get_packages_in_folder(folder, verbose=False):
    """Wrapper for find_catkin_packages_in that returns a set.

    * Ignores folders with IGNORE_MARKERS
    * Returns paths with package.xml

    https://github.com/ros-infrastructure/rosdep/blob/master/src/rosdep2/catkin_packages.py#L19
    """
    return set(find_catkin_packages_in(folder, verbose=verbose))


def get_all_packages(folder=None, verbose=False):
    """Return the set of all packages in the environment."""
    universe = set()
    if folder:
        universe.update(get_packages_in_folder(folder, verbose))

    # Get Packages From Path
    if AMENT_PREFIX_PATH_ENV_VAR in os.environ:
        universe.update(get_packages_with_prefixes().keys())
    elif ROS_PACKAGE_PATH in os.environ:
        for path in os.environ[ROS_PACKAGE_PATH].split(os.pathsep):
            if not os.path.exists(path):
                continue
            universe.update(find_catkin_packages_in(path, verbose))
    return universe
