import pathlib

import yaml

CONFIG_PATH = pathlib.Path('~/.ros/ros_command.yaml').expanduser()
CONFIG = None


def get_config(key, default_value=None, workspace_root=None):
    if workspace_root:
        local_config_path = workspace_root / 'ros_command.yaml'
        if local_config_path.exists():
            local_config = yaml.safe_load(open(local_config_path))
            if key in local_config:
                return local_config[key]

    global CONFIG
    if CONFIG is None:
        if CONFIG_PATH.exists():
            CONFIG = yaml.safe_load(open(CONFIG_PATH))
        else:
            CONFIG = {}

    return CONFIG.get(key, default_value)


def sizeof_fmt(num, suffix='B'):
    # https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
    BASE = 1024.0
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < BASE:
            return f'{num:3.1f} {unit}{suffix}'
        num /= BASE
    return '{num:.1f} Yi{suffix}'
