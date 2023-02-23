import argcomplete
import argparse
import pathlib
import shutil

import click

from ros_command.workspace import BuildType, get_workspace_root
from ros_command.util import sizeof_fmt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-y', '--yes-to-all', '--no-confirm', action='store_true')
    parser.add_argument('-c', '--just-checking', action='store_true')
    parser.add_argument('-n', '--no-sizes', action='store_true')
    parser.add_argument('packages', metavar='package', nargs='*')

    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    if args.packages:
        if args.packages[0] == 'check':
            args.just_checking = True
            args.packages.pop(0)
        elif args.packages[0] == 'purge':
            args.packages.pop(0)

    build_type, workspace_root = get_workspace_root()

    directories = []

    if not args.packages:
        directories.append(workspace_root / 'build')
        directories.append(workspace_root / 'log')
        if build_type == BuildType.COLCON:
            directories.append(workspace_root / 'install')
        else:
            directories.append(workspace_root / 'devel')
        directories.append(pathlib.Path('~/.ros/log').expanduser())
    else:
        if build_type != BuildType.COLCON:
            raise NotImplementedError()
        for package in args.packages:
            directories.append(workspace_root / 'build' / package)
            directories.append(workspace_root / 'install' / package)

    max_len = max(len(str(p)) for p in directories)

    try:
        for directory in directories:
            if not directory.exists():
                click.secho(f'{directory} does not exist!', fg='yellow')
                continue

            click.secho(str(directory).ljust(max_len + 2), nl=False)
            if not args.no_sizes:
                dir_size = sizeof_fmt(sum(f.stat().st_size for f in directory.glob('**/*') if f.is_file()))
                click.secho(dir_size, fg='bright_blue')
            else:
                click.secho('')
            if args.just_checking:
                continue
            if args.yes_to_all or click.confirm('Delete?'):
                shutil.rmtree(directory)
    except click.exceptions.Abort:
        click.echo()
