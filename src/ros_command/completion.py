import datetime
import pathlib
import re
import yaml

from ros_command.packages import get_all_packages, get_packages_in_folder, get_launch_file_arguments
from ros_command.packages import find_executables_in_package, find_launch_files_in_package
from ros_command.util import get_config

CACHE_PATH = pathlib.Path('~/.ros/ros_command_cache.yaml').expanduser()
THE_CACHE = None

# https://stackoverflow.com/a/51916936
DELTA_PATTERN = re.compile(r'^((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$')


def get_tab_timeout():
    timeout_s = get_config('tab_complete_timeout', '4h')
    m = DELTA_PATTERN.match(timeout_s)
    if m:
        time_params = {name: float(param) for name, param in m.groupdict().items() if param}
        return datetime.timedelta(**time_params)
    return datetime.timedelta(hours=4)


class Completer:
    def __init__(self, workspace_root=None, version=None):
        self.workspace_root = workspace_root
        self.version = version

    def get_cache_keys(self, **kwargs):
        raise NotImplementedError('Please implement this method')

    def get_completions(self, **kwargs):
        raise NotImplementedError('Please implement this method')

    def filter_values(self, values, **kwargs):
        # Overridable method
        return values

    def get_cached_completions(self, cache_keys):
        global THE_CACHE

        if cache_keys is None:
            return

        # Load cache
        if THE_CACHE is None:
            if CACHE_PATH.exists():
                THE_CACHE = yaml.safe_load(open(CACHE_PATH))
            else:
                THE_CACHE = {}

        # Get relevant part
        d = THE_CACHE
        for key in cache_keys:
            if key not in d:
                d[key] = {}
            d = d[key]

        # Check timing
        if 'stamp' not in d:
            return
        delta = datetime.datetime.now() - d['stamp']
        if delta < get_tab_timeout():
            return d['data']

    def write_to_cache(self, cache_keys, results):
        global THE_CACHE
        if cache_keys is None:
            return

        d = THE_CACHE
        for key in cache_keys:
            d = d[key]

        d['data'] = list(results)
        d['stamp'] = datetime.datetime.now()
        yaml.safe_dump(THE_CACHE, open(CACHE_PATH, 'w'))

    def __call__(self, **kwargs):
        cache_keys = self.get_cache_keys(**kwargs)

        results = self.get_cached_completions(cache_keys)
        if not results:
            results = self.get_completions(**kwargs)
            self.write_to_cache(cache_keys, results)

        return self.filter_values(results, **kwargs)


class PackageCompleter(Completer):
    def get_cache_keys(self, **kwargs):
        return [str(self.workspace_root), 'packages']

    def get_completions(self, **kwargs):
        return get_all_packages(self.workspace_root)


class LocalPackageCompleter(Completer):
    def get_cache_keys(self, **kwargs):
        return [str(self.workspace_root), 'local_packages']

    def get_completions(self, **kwargs):
        return get_packages_in_folder(self.workspace_root)


class ExecutableNameCompleter(Completer):
    def get_cache_keys(self, parsed_args, **kwargs):
        return [str(self.workspace_root), parsed_args.package_name, 'executables']

    def get_completions(self, parsed_args, **kwargs):
        return find_executables_in_package(parsed_args.package_name, self.version)


class LaunchFileCompleter(Completer):
    def get_cache_keys(self, parsed_args, **kwargs):
        return [str(self.workspace_root), parsed_args.package_name, 'launches']

    def get_completions(self, parsed_args, **kwargs):
        return find_launch_files_in_package(parsed_args.package_name, self.version)


class LaunchArgCompleter(Completer):
    def get_cache_keys(self, parsed_args, **kwargs):
        return [str(self.workspace_root), parsed_args.package_name, parsed_args.launch_file_name, 'arg']

    def get_completions(self, parsed_args, **kwargs):
        args = get_launch_file_arguments(parsed_args.package_name,
                                         parsed_args.launch_file_name,
                                         self.version)
        return [f'{a}:=' for a in args]

    def filter_values(self, values, parsed_args, **kwargs):
        existing_args = set()
        for arg_s in parsed_args.argv:
            if ':=' in arg_s:
                i = arg_s.index(':=')
                existing_args.add(arg_s[:i+2])
        return [a for a in values if a not in existing_args]
