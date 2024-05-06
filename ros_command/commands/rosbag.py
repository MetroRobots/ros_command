import argcomplete
import argparse
import click
import pathlib
import re
import tempfile
import yaml

from ros_command.command_lib import run
from ros_command.workspace import get_ros_version
from ros_command.completion import TopicCompleter

TOPIC_PATTERN = re.compile(r'^(.*)Topic: ([^|]+) \| Type: ([^|]+) \| Count: (\d+) \| Serialization Format: (.*)$')


async def main(debug=False):
    version, distro = get_ros_version()

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='verb')
    subparsers.add_parser('check')
    compress_parser = subparsers.add_parser('compress')
    compress_parser.add_argument('bagfiles', metavar='bagfile', type=pathlib.Path, nargs='+')
    # --output-dir
    # --force
    decompress_parser = subparsers.add_parser('decompress')
    decompress_parser.add_argument('bagfiles', metavar='bagfile', type=pathlib.Path, nargs='+')
    subparsers.add_parser('decrypt')
    subparsers.add_parser('encrypt')
    subparsers.add_parser('filter')
    subparsers.add_parser('fix')
    info_parser = subparsers.add_parser('info')
    info_parser.add_argument('bagfile', type=pathlib.Path)

    play_parser = subparsers.add_parser('play')
    play_parser.add_argument('bagfile', type=pathlib.Path)
    play_parser.add_argument('--clock', action='store_true')
    play_parser.add_argument('-r', '--rate', type=float, default=1.0)
    play_parser.add_argument('-t', '--topics', metavar='topic', nargs='+')

    record_parser = subparsers.add_parser('record')
    record_parser.add_argument('topics', metavar='topic', nargs='*').completer = TopicCompleter(version)

    reindex_parser = subparsers.add_parser('reindex')
    reindex_parser.add_argument('bagfile', type=pathlib.Path)

    argcomplete.autocomplete(parser)

    args, unknown_args = parser.parse_known_args()

    if version == 1:
        command = []
        command.append(f'/opt/ros/{distro}/bin/rosbag')
        command.append(args.verb)
        if args.verb == 'record':
            command += args.topics
        elif 'compress' in args.verb:
            command += args.bagfiles
        elif args.verb in ['info', 'play', 'reindex']:
            command.append(args.bagfile)

            if args.verb == 'play':
                if args.clock:
                    command.append('--clock')

        code = await run(command + unknown_args)
        exit(code)

    if 'compress' in args.verb:
        for bagfile in args.bagfiles:
            outfile = bagfile.resolve().with_name(f'{bagfile.name}_{args.verb}ed')
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as tmpfile:
                config = {'uri': str(outfile),
                          'storage_id': 'sqlite3',
                          'all': True,
                          }
                if args.verb == 'compress':
                    config['compression_mode'] = 'file'
                    config['compression_format'] = 'zstd'
                else:
                    config['compression_mode'] = ''
                    config['compression_format'] = ''
                yaml.safe_dump({'output_bags': [config]}, tmpfile)
                await run(['ros2', 'bag', 'convert', '-i', str(bagfile), '-o', str(tmpfile)])
    elif args.verb == 'info':
        topic_info = []
        max_topic_len = 0
        max_type_len = 0

        def out_cb(line):
            nonlocal max_topic_len, max_type_len
            line = line.strip()
            m = TOPIC_PATTERN.match(line)
            if not m:
                click.secho(line, fg='cyan')
                return
            prefix, topic, type_, count, compression = m.groups()
            if prefix:
                click.secho(prefix)
            count = int(count)
            topic_info.append((topic, type_, count, compression))
            max_topic_len = max(max_topic_len, len(topic))
            max_type_len = max(max_type_len, len(type_))

        await run(['ros2', 'bag', 'info', str(args.bagfile)], out_cb)

        fmt_string = '\t{topic:' + str(max_topic_len + 2) + 's} | {type_:' + str(max_type_len + 2) + 's} | {count:5d}'
        for topic, type_, count, compression in sorted(topic_info):
            click.secho(fmt_string.format(**locals()), fg='bright_white' if count else 'bright_black')
    elif args.verb == 'record':
        await run(['ros2', 'bag', 'record'] + args.topics)
    elif args.verb == 'play':
        from rosbag2_py import SequentialReader
        from rosbag2_py import StorageOptions, StorageFilter, ConverterOptions
        from rosgraph_msgs.msg import Clock
        from rosidl_runtime_py.utilities import get_message
        import rclpy
        from rclpy.qos import QoSProfile
        from rclpy.node import Node
        from rclpy.serialization import deserialize_message

        import importlib
        import time
        import yaml

        rclpy.init()
        node = Node('rosbag_play')
        serialization_format = 'cdr'
        reader = SequentialReader()
        reader.open(StorageOptions(str(args.bagfile), 'sqlite3'),
                    ConverterOptions(serialization_format, serialization_format))

        if args.topics:
            storage_filter = StorageFilter(topics=args.topics)
            reader.set_filter(storage_filter)

        topic_types = reader.get_all_topics_and_types()
        pubs = {}
        for tmeta in topic_types:
            if args.topics and tmeta.name not in args.topics:
                continue
            pkg, itype, name = tmeta.type.split('/')
            module = importlib.import_module(f'{pkg}.{itype}')
            if tmeta.offered_qos_profiles:
                profiles = yaml.safe_load(tmeta.offered_qos_profiles)
                profile = profiles[0]
                qos = QoSProfile(depth=profile['depth'],
                                 durability=profile['durability'])
            else:
                qos = 1

            pubs[tmeta.name] = node.create_publisher(getattr(module, name), tmeta.name, qos)

        if args.clock and '/clock' not in pubs:
            pubs['/clock'] = node.create_publisher(Clock, '/clock', 1)

        type_map = {tmeta.name: tmeta.type for tmeta in topic_types}
        prev_time = None
        publish_rate_mult = 1 / args.rate
        while reader.has_next():
            (topic, rawdata, timestamp) = reader.read_next()
            ftime = timestamp / 1e9

            if args.clock:
                clock_msg = Clock()
                clock_msg.clock.sec = int(ftime)
                clock_msg.clock.nanosec = int(timestamp % 1e9)

                pubs['/clock'].publish(clock_msg)
            pub = pubs[topic]
            msg_type = get_message(type_map[topic])
            msg = deserialize_message(rawdata, msg_type)
            pub.publish(msg)

            if prev_time:
                delta = (ftime - prev_time) * publish_rate_mult
                time.sleep(delta)
            prev_time = ftime
    elif args.verb == 'reindex':
        import sqlite3
        from ruamel.yaml import YAML

        db_paths = sorted(args.bagfile.glob('*.db3'))
        metadata = {}
        metadata['version'] = 4
        metadata['storage_identifier'] = 'sqlite3'
        metadata['relative_file_paths'] = []
        metadata['duration'] = {'nanoseconds': 0}
        metadata['starting_time'] = {}
        metadata['message_count'] = 0
        metadata['topics_with_message_count'] = []
        t_map = {}
        for db_path in db_paths:
            con = sqlite3.connect(db_path)
            cur = con.cursor()

            metadata['relative_file_paths'].append(db_path.name)

            for row in cur.execute('SELECT * FROM topics'):
                m = {}
                topic_id, m['name'], m['type'], m['serialization_format'], m['offered_qos_profiles'] = row
                d = {'topic_metadata': m, 'message_count': 0}
                metadata['topics_with_message_count'].append(d)
                t_map[topic_id] = d

            for msg in cur.execute('SELECT topic_id, timestamp FROM messages ORDER BY timestamp'):
                topic_id, timestamp = msg
                t_map[topic_id]['message_count'] += 1
                metadata['message_count'] += 1

                st = metadata['starting_time']

                if 'nanoseconds_since_epoch' not in st:
                    st['nanoseconds_since_epoch'] = timestamp

                metadata['duration']['nanoseconds'] = timestamp - st['nanoseconds_since_epoch']

        meta_path = args.bagfile / 'metadata.yaml'
        if meta_path.exists():
            out_path = args.bagfile / 'gen_meta.yaml'
        else:
            out_path = meta_path

        metadata['compression_format'] = ''
        metadata['compression_mode'] = ''

        yaml = YAML()
        print(f'Writing to {out_path}')
        yaml.dump({'rosbag2_bagfile_information': metadata}, open(out_path, 'w'))
    else:
        raise NotImplementedError(f'Verb {args.verb} not implemented yet!')

"""Example merge:

$ ros2 bag convert -i bag1 -i bag2 -o out.yaml

# out.yaml
output_bags:
- uri: merged_bag
  storage_id: sqlite3
  all: true

Example split:

$ ros2 bag convert -i bag1 -o out.yaml

# out.yaml
output_bags:
- uri: split1
  storage_id: sqlite3
  topics: [/topic1, /topic2]
- uri: split2
  storage_id: sqlite3
  topics: [/topic3]

Example compress:

$ ros2 bag convert -i bag1 -o out.yaml

# out.yaml
output_bags:
- uri: compressed
  storage_id: sqlite3
  all: true
  compression_mode: file
  compression_format: zstd
"""
