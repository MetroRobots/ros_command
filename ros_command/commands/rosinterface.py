import argparse
import collections
import pathlib

import click

from ros_command.command_lib import get_output, run
from ros_command.workspace import get_ros_version

ACTION_PARTS = ['Goal', 'Result', 'Feedback']


async def list_actions(ii, distro, pkg=None):
    if pkg:
        packages = [pkg]
    else:
        # List all packages with any messages
        _, out, _ = await get_output(ii.get_base_command('packages', interface_type='msg'))
        packages = set(filter(None, out.split('\n')))

    results = []
    for pkg in packages:
        _, path_s, _ = await get_output([f'/opt/ros/{distro}/bin/rospack', 'find', pkg])
        path = pathlib.Path(path_s.strip()) / 'action'
        if path.exists():
            for filename in path.glob('*.action'):
                results.append((pkg, filename.stem))
    return sorted(results)


async def list_interfaces_ros2(ii, types=None):
    interfaces = []

    def out_cb(line):
        line = line.strip()
        pieces = line.split('/')
        if len(pieces) == 3:
            if types is not None and pieces[1] in types:
                interfaces.append(line)

    await run(ii.get_base_command('list'), stdout_callback=out_cb)
    return interfaces


async def list_interfaces_by_name_ros2(ii, types=None):
    interfaces = await list_interfaces_ros2(ii, types)

    stems = collections.defaultdict(list)
    for interface in interfaces:
        pieces = interface.split('/')
        stems[pieces[-1]].append(interface)

    return stems


async def translate_to_full_names(base_s, interface_type, ii):
    pieces = base_s.split('/')
    if len(pieces) == 3:
        # String already is full qualified
        return [base_s]
    elif len(pieces) == 2:
        # If the interface type is missing, insert it
        return [f'{pieces[0]}/{interface_type}/{pieces[1]}']
    else:
        # If only the interface name is specified, list all the interfaces and return the matches
        stems = await list_interfaces_by_name_ros2(ii, [interface_type])
        return stems[base_s]


class InterfaceInterface:
    def __init__(self, version, distro, interface_type):
        self.version = version
        self.distro = distro
        self.interface_type = interface_type

    def get_base_command(self, verb, interface_type=None):
        if interface_type is None:
            interface_type = self.interface_type
        if self.version == 1:
            return [f'/opt/ros/{self.distro}/bin/ros{interface_type}', verb]
        else:
            cmd = [f'/opt/ros/{self.distro}/bin/ros2', 'interface', verb]
            return cmd


async def main(interface_type):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='verb')
    show_parser = subparsers.add_parser('show', aliases=['info'])
    show_parser.add_argument('interface_name')
    subparsers.add_parser('list')
    md5_parser = subparsers.add_parser('md5')
    md5_parser.add_argument('interface_name')
    pkg_parser = subparsers.add_parser('package')
    pkg_parser.add_argument('package_name')
    subparsers.add_parser('packages')

    args = parser.parse_args()
    if args.verb == 'info':  # Alias
        args.verb = 'show'

    version, distro = get_ros_version()

    ii = InterfaceInterface(version, distro, interface_type)

    if version == 1:
        if interface_type != 'action':
            # Pass through for rosmsg/rossrv
            cmd = ii.get_base_command(args.verb)
            if args.verb in ['show', 'md5']:
                cmd.append(args.interface_name)
            elif args.verb == 'package':
                cmd.append(args.package_name)
            code = await run(cmd)
            exit(code)
        elif args.verb in ['show', 'md5']:
            for part in ACTION_PARTS:
                cmd = ii.get_base_command(args.verb)
                cmd.append(f'{args.interface_name}{part}')
                await run(cmd)
        elif args.verb == 'list':
            for pkg, action in await list_actions(ii, distro):
                print(f'{pkg}/{action}')
        elif args.verb == 'package':
            for pkg, action in await list_actions(ii, distro, pkg=args.package_name):
                print(f'{pkg}/{action}')
        elif args.verb == 'packages':
            seen = set()
            for pkg, action in await list_actions(ii, distro):
                if pkg not in seen:
                    print(pkg)
                    seen.add(pkg)

    elif args.verb == 'show':
        base_command = ii.get_base_command(args.verb)
        for full_name in await translate_to_full_names(args.interface_name, interface_type, ii):
            click.secho(f'[{full_name}]', fg='blue')
            await run(base_command + [full_name])
    elif args.verb in ['list', 'packages']:
        # Pass through to ros2 interface with appropriate args
        command = ii.get_base_command(args.verb)
        command.append('-' + interface_type[0])  # -m for msg, -s for srv, etc
        await run(command)
    elif args.verb == 'package':
        # Pass through to ros2 interface, but skip interfaces with the wrong type
        key = f'/{interface_type}'

        def package_output_cb(line):
            if key in line:
                click.secho(line, nl=False)
        command = ii.get_base_command(args.verb)
        await run(command + [args.package_name], stdout_callback=package_output_cb)
    else:
        raise NotImplementedError('No equivalent md5 command in ros2')
