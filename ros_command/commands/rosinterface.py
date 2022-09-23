import argparse
import collections
import pathlib

import click

from ros_command.command_lib import get_output, run
from ros_command.workspace import get_ros_version

ROSInterface = collections.namedtuple('ROSInterface', ['package', 'type', 'name'])

ACTION_PARTS = ['Goal', 'Result', 'Feedback']


def get_action_parts(base_interface):
    for action_part in ACTION_PARTS:
        yield ROSInterface(base_interface.package, 'msg', f'{base_interface.name}{action_part}')


def to_string(interface, two_piece=True):
    if two_piece:
        return f'{interface.package}/{interface.name}'
    else:
        return f'{interface.package}/{interface.type}/{interface.name}'


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
                results.append(ROSInterface(pkg, 'action', filename.stem))
    return sorted(results)


async def list_interfaces_ros2(ii, types=None):
    interfaces = []

    def out_cb(line):
        if line and line[0] != ' ' and line.endswith(':\n'):
            return
        interface = ii.parse_interface(line.strip())
        if types is not None and interface.type in types:
            interfaces.append(interface)

    await run(ii.get_base_command('list'), stdout_callback=out_cb)
    return interfaces


async def list_interfaces_by_name_ros2(ii, types=None):
    interfaces = await list_interfaces_ros2(ii, types)

    stems = collections.defaultdict(list)
    for interface in interfaces:
        stems[interface.name].append(interface)

    return stems


async def translate_to_full_names(base_s, interface_type, ii):
    pieces = base_s.split('/')

    # If no /, then only the interface name is specified and list all the interfaces that have the same name
    if len(pieces) == 1:
        stems = await list_interfaces_by_name_ros2(ii, [interface_type])
        return stems[base_s]
    else:
        return [ii.parse_interface(base_s)]


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

    def parse_interface(self, s):
        pieces = s.split('/')
        # If only two pieces, assume the interface_type is missing
        # i.e. convert geometry_msgs/Point to geometry_msgs/msg/Point
        if len(pieces) == 2:
            return ROSInterface(pieces[0], self.interface_type, pieces[1])
        # If three pieces, assume the interface type is specified
        elif len(pieces) == 3:
            return ROSInterface(*pieces)
        else:
            raise RuntimeError(f'Cannot parse interface for "{s}"')


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
            interface = ii.parse_interface(args.interface_name)
            for component in get_action_parts(interface):
                name = to_string(component)
                cmd = ii.get_base_command(args.verb, interface_type='msg')
                cmd.append(name)
                await run(cmd)
        elif args.verb == 'list':
            for interface in await list_actions(ii, distro):
                print(to_string(interface))
        elif args.verb == 'package':
            for interface in await list_actions(ii, distro, pkg=args.package_name):
                print(to_string(interface))
        elif args.verb == 'packages':
            seen = set()
            for interface in await list_actions(ii, distro):
                if interface.package not in seen:
                    print(interface.package)
                    seen.add(interface.package)

    elif args.verb == 'show':
        base_command = ii.get_base_command(args.verb)
        for interface in await translate_to_full_names(args.interface_name, interface_type, ii):
            click.secho(f'[{to_string(interface)}]', fg='blue')
            await run(base_command + [to_string(interface, two_piece=False)])
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
