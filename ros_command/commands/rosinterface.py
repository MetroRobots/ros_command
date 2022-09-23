import argparse
import collections
import pathlib

import click

from ros_command.command_lib import get_output, run
from ros_command.workspace import get_ros_version

ACTION_PARTS = ['Goal', 'Result', 'Feedback']


async def list_actions(distro, pkg=None):
    if pkg:
        packages = [pkg]
    else:
        # List all packages with any messages
        _, out, _ = await get_output([f'/opt/ros/{distro}/bin/rosmsg', 'packages'])
        packages = set(filter(None, out.split('\n')))

    results = []
    for pkg in packages:
        _, path_s, _ = await get_output([f'/opt/ros/{distro}/bin/rospack', 'find', pkg])
        path = pathlib.Path(path_s.strip()) / 'action'
        if path.exists():
            for filename in path.glob('*.action'):
                results.append((pkg, filename.stem))
    return sorted(results)


async def list_interfaces_ros2(distro, types=None):
    interfaces = []

    def out_cb(line):
        line = line.strip()
        pieces = line.split('/')
        if len(pieces) == 3:
            if types is not None and pieces[1] in types:
                interfaces.append(line)

    await run([f'/opt/ros/{distro}/bin/ros2', 'interface', 'list'], stdout_callback=out_cb)
    return interfaces


async def list_interfaces_by_name_ros2(distro, types=None):
    interfaces = await list_interfaces_ros2(distro, types)

    stems = collections.defaultdict(list)
    for interface in interfaces:
        pieces = interface.split('/')
        stems[pieces[-1]].append(interface)

    return stems


async def translate_to_full_names(base_s, interface_type, distro):
    pieces = base_s.split('/')
    if len(pieces) == 3:
        # String already is full qualified
        return [base_s]
    elif len(pieces) == 2:
        # If the interface type is missing, insert it
        return [f'{pieces[0]}/{interface_type}/{pieces[1]}']
    else:
        # If only the interface name is specified, list all the interfaces and return the matches
        stems = await list_interfaces_by_name_ros2(distro, [interface_type])
        return stems[base_s]


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

    if version == 1:
        if interface_type != 'action':
            # Pass through for rosmsg/rossrv
            cmd = [f'/opt/ros/{distro}/bin/ros{interface_type}', args.verb]
            if args.verb in ['show', 'md5']:
                cmd.append(args.interface_name)
            elif args.verb == 'package':
                cmd.append(args.package_name)
            code = await run(cmd)
            exit(code)
        elif args.verb in ['show', 'md5']:
            for part in ACTION_PARTS:
                await run([f'/opt/ros/{distro}/bin/rosmsg', args.verb, f'{args.interface_name}{part}'])
        elif args.verb == 'list':
            for pkg, action in await list_actions(distro):
                print(f'{pkg}/{action}')
        elif args.verb == 'package':
            for pkg, action in await list_actions(distro, pkg=args.package_name):
                print(f'{pkg}/{action}')
        elif args.verb == 'packages':
            seen = set()
            for pkg, action in await list_actions(distro):
                if pkg not in seen:
                    print(pkg)
                    seen.add(pkg)

    elif args.verb == 'show':
        base_command = [f'/opt/ros/{distro}/bin/ros2', 'interface', 'show']
        for full_name in await translate_to_full_names(args.interface_name, interface_type, distro):
            click.secho(f'[{full_name}]', fg='blue')
            await run(base_command + [full_name])
    elif args.verb in ['list', 'packages']:
        # Pass through to ros2 interface with appropriate args
        command = [f'/opt/ros/{distro}/bin/ros2', 'interface', args.verb]
        command.append('-' + interface_type[0])  # -m for msg, -s for srv, etc
        await run(command)
    elif args.verb == 'package':
        # Pass through to ros2 interface, but skip interfaces with the wrong type
        key = f'/{interface_type}'

        def package_output_cb(line):
            if key in line:
                click.secho(line, nl=False)
        command = [f'/opt/ros/{distro}/bin/ros2', 'interface', 'package']
        await run(command + [args.package_name], stdout_callback=package_output_cb)
    else:
        raise NotImplementedError('No equivalent md5 command in ros2')
