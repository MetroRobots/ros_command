from ros_command.packages import get_all_packages, get_packages_in_folder, get_launch_file_arguments
from ros_command.packages import find_executables_in_package, find_launch_files_in_package


class PackageCompleter:
    def __init__(self, workspace_root=None, local=False):
        self.workspace_root = workspace_root
        self.local = local

    def __call__(self, **kwargs):
        if self.local:
            return get_packages_in_folder(self.workspace_root)
        else:
            return get_all_packages(self.workspace_root)


class ExecutableNameCompleter:
    def __init__(self, version):
        self.version = version

    def __call__(self, parsed_args, **kwargs):
        return find_executables_in_package(parsed_args.package_name, self.version)


class LaunchFileCompleter:
    def __init__(self, version):
        self.version = version

    def __call__(self, parsed_args, **kwargs):
        return find_launch_files_in_package(parsed_args.package_name, self.version)


class LaunchArgCompleter:
    def __init__(self, workspace_root, version):
        self.version = version
        self.workspace_root = workspace_root

    def __call__(self, parsed_args, **kwargs):
        return get_launch_file_arguments(parsed_args.package_name,
                                         parsed_args.launch_file_name,
                                         parsed_args.argv,
                                         self.version)
