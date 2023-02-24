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


def find_executables_in_package(package_name, version):
    if version == 1:
        from catkin.find_in_workspaces import find_in_workspaces
        execs = []
        for exec_folder in find_in_workspaces(['libexec'], package_name):
            for path in sorted(os.listdir(exec_folder)):
                full_path = os.path.join(exec_folder, path)
                if os.access(full_path, os.X_OK):
                    execs.append(path)
        return execs
    else:
        from ros2pkg.api import get_executable_paths, PackageNotFound
        try:
            paths = get_executable_paths(package_name=package_name)
        except PackageNotFound:
            return []
        return [os.path.basename(p) for p in paths]


def find_launch_files_in_package(package_name, version):
    if version == 1:
        from catkin.find_in_workspaces import find_in_workspaces
        launches = []
        for folder in find_in_workspaces(['share'], package_name):
            for name, subdirs, files in os.walk(folder):
                for filepath in files:
                    if filepath.endswith('.launch'):
                        launches.append(filepath)
        return launches
    else:
        from ament_index_python.packages import get_package_share_directory
        from ament_index_python.packages import PackageNotFoundError
        from ros2launch.api.api import get_launch_file_paths
        try:
            package_share_directory = get_package_share_directory(package_name)
            paths = get_launch_file_paths(path=package_share_directory)
        except PackageNotFoundError:
            return []
        return [os.path.basename(p) for p in paths]
