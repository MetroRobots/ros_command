from ros_command.environment import get_topics
from ros_command.packages import get_all_packages, get_packages_in_folder
from ros_command.packages import find_executables_in_package


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


class TopicCompleter:
    def __init__(self, version):
        self.version = version

    def __call__(self, prefix, parsed_args, **kwargs):
        matches = []
        for topic in get_topics(self.version):
            if topic.startswith(prefix) and topic not in parsed_args.topics:
                matches.append(topic)
        return matches
