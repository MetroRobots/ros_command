from ros_command.packages import get_all_packages, get_packages_in_folder


class PackageCompleter:
    def __init__(self, workspace_root=None, local=False):
        self.workspace_root = workspace_root
        self.local = local

    def __call__(self, **kwargs):
        if self.local:
            return get_packages_in_folder(self.workspace_root)
        else:
            return get_all_packages(self.workspace_root)
