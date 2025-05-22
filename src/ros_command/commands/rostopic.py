import argcomplete
import argparse
import asyncio

from betsy_ros import get_ros_version, get_workspace_root

from ros_command.command_lib import run, get_overlayed_command
from ros_command.completion import TopicCompleter
from ros_command.commands.rosinterface import InterfaceInterface, InterfaceCompleter


async def main(debug=False):
    build_type, workspace_root = get_workspace_root()
    version, distro = get_ros_version()

    ii = InterfaceInterface(version, distro, 'msg')

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='verb')

    bw_parser = subparsers.add_parser('bw')
    bw_parser.add_argument('topic').completer = TopicCompleter(version=version)

    delay_parser = subparsers.add_parser('delay')
    delay_parser.add_argument('topic').completer = TopicCompleter(version=version)

    echo_parser = subparsers.add_parser('echo')
    echo_parser.add_argument('topic').completer = TopicCompleter(version=version)

    find_parser = subparsers.add_parser('find')
    find_parser.add_argument('msg_type').completer = InterfaceCompleter(workspace_root, ii)

    hz_parser = subparsers.add_parser('hz')
    hz_parser.add_argument('topic').completer = TopicCompleter(version=version)

    info_parser = subparsers.add_parser('info')
    info_parser.add_argument('topic').completer = TopicCompleter(version=version)

    subparsers.add_parser('list')

    pub_parser = subparsers.add_parser('pub')
    pub_parser.add_argument('topic').completer = TopicCompleter(version=version)

    type_parser = subparsers.add_parser('type')
    type_parser.add_argument('topic').completer = TopicCompleter(version=version)

    parser.add_argument('argv', nargs=argparse.REMAINDER)

    argcomplete.autocomplete(parser, always_complete_options=False)
    args = parser.parse_args()

    command = []
    if version == 1:
        command.append(await get_overlayed_command('rostopic'))
    else:
        command.append(f'/opt/ros/{distro}/bin/ros2')
        command.append('topic')

    command.append(args.verb)

    if hasattr(args, 'topic'):
        command.append(args.topic)
    elif hasattr(args, 'msg_type'):
        full_names = ii.translate_to_full_names(args.msg_type)
        if len(full_names) == 1:
            interface = full_names[0].to_string(False)
        else:
            interface = args.msg_type
        command.append(interface)

    command += args.argv

    code = await run(command)
    exit(code)


def main_rostopic():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
