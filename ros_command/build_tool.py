import collections
import re
import sys
import time

import click

from ros_command.build_status_display import BuildStatusDisplay, STATUS_COLORS
from ros_command.command_lib import get_output, run
from ros_command.completion import PackageCompleter
from ros_command.workspace import BuildType
from ros_command.util import get_config


PKG_PATTERN = r'\s+([\w\-]+)\s+'
BRACKET_PATTERN = r'\[\s*(.*)\s*\]\s*'
STATUS_PATTERNS = [
    ('start', re.compile(r'Starting *>>>' + PKG_PATTERN)),
    ('stop', re.compile(r'Finished *<<<' + PKG_PATTERN + BRACKET_PATTERN)),
    ('fail', re.compile(r'Failed *<<<' + PKG_PATTERN + BRACKET_PATTERN)),
    ('abort', re.compile(r'Aborted *<<<' + PKG_PATTERN + BRACKET_PATTERN)),
    ('abort', re.compile(r'Abandoned *<<<' + PKG_PATTERN + BRACKET_PATTERN))
]
SKIPPABLE_PATTERNS = [
    re.compile(r'^Summary:.*'),
    re.compile(r'^\[build( [\d\.:]+ s)?\].*'),
    re.compile(r'^\[Processing: .*\]'),
    re.compile(r'^\s*\d+ packages? ([^\:]+):.*'),
    re.compile(r'^\s+\d+ packages? not processed.*')
]


class BuildStatus:
    def __init__(self):
        self.start_time = time.time()
        self.upstream_deps = {}
        self.pkg_lists = collections.defaultdict(list)
        self.error_buffer = []
        self.n = 0

    def out_callback(self, line):
        self.output_callback(line, False)

    def err_callback(self, line):
        self.output_callback(line, True)

    def output_callback(self, line, is_err):
        # Split by \r if needed
        if '\r' in line:
            for bit in line.split('\r'):
                if bit:
                    self.output_callback(bit, is_err)
            return

        for pattern in SKIPPABLE_PATTERNS:
            if pattern.match(line):
                return
        for name, pattern in STATUS_PATTERNS:
            m = pattern.search(line)
            if m:
                getattr(self, name)(m.group(1))
                return

        self.add_error_line(line.rstrip())

    def set_dependencies(self, upstream):
        self.upstream_deps = {}
        self.n = len(upstream)
        for pkg, deps in upstream.items():
            if deps:
                self.pkg_lists['blocked'].append(pkg)
                self.upstream_deps[pkg] = deps
            else:
                self.pkg_lists['queued'].append(pkg)

    def start(self, pkg):
        if pkg in self.pkg_lists['queued']:
            self.pkg_lists['queued'].remove(pkg)
        self.pkg_lists['active'].append(pkg)

    def stop(self, pkg):
        if pkg not in self.pkg_lists['active']:
            return
        self.pkg_lists['active'].remove(pkg)
        self.pkg_lists['finished'].append(pkg)
        for pkg2, deps in list(self.upstream_deps.items()):
            if pkg in deps:
                deps.remove(pkg)
                if not deps:
                    del self.upstream_deps[pkg2]
                    self.pkg_lists['blocked'].remove(pkg2)
                    self.pkg_lists['queued'].append(pkg2)

    def fail(self, pkg):
        self.pkg_lists['active'].remove(pkg)
        self.pkg_lists['failed'].append(pkg)
        for pkg2, deps in list(self.upstream_deps.items()):
            if pkg in deps:
                self.pkg_lists['blocked'].remove(pkg2)
                self.pkg_lists['skipped'].append(pkg2)
                if not deps:
                    del self.upstream_deps[pkg2]

    def abort(self, pkg):
        if pkg not in self.pkg_lists['blocked']:
            return
        self.pkg_lists['blocked'].remove(pkg)
        self.pkg_lists['skipped'].append(pkg)

    def add_error_line(self, line):
        self.error_buffer.append(line)

    def get_elapsed_time(self):
        dt = time.time() - self.start_time
        hours, remainder = divmod(dt, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours or minutes:
            hours = int(hours)
            minutes = int(minutes)
            seconds = int(seconds)
            s = f'{minutes:02d}:{seconds:02d}'
            if hours:
                return f'{hours}:' + s
            else:
                return s
        else:
            return f'{seconds:.1f} s'

    def get_all_packages(self):
        pkgs = []
        for pkg_list in self.pkg_lists.values():
            pkgs += pkg_list
        return pkgs

    def print_status(self):
        n_fin = len(self.pkg_lists['finished'])
        dt = self.get_elapsed_time()
        click.secho('Summary: ', fg='white', bold=True, nl=False)
        click.secho(f'{n_fin} packages finished ', nl=False, fg='blue', bold=False)
        click.secho(f'[{dt}]', fg='white', bold=False)
        for category, pkgs in self.pkg_lists.items():
            if not pkgs or category == 'finished':
                continue
            n = len(pkgs)
            suffix = '' if n == 1 else 's'
            pkgs_s = ' '.join(sorted(pkgs))
            click.secho(f' {n:4} package{suffix} {category}', fg=STATUS_COLORS.get(category, 'white'), nl=False)
            click.secho(f': {pkgs_s}')


def parse_colcon_graph(s):
    lines = [line for line in s.split('\n') if line]
    if not lines:
        return {}
    start_index = lines[0].index('+')
    pkgs = [line[:start_index].strip() for line in lines]
    upstream = {pkg: set() for pkg in pkgs}
    for i, line in enumerate(lines):
        dep = pkgs[i]
        for j in range(start_index + i, len(line)):
            c = line[j]
            pkg = pkgs[j - start_index]
            if c in '+ ':
                continue
            upstream[pkg].add(dep)
    return upstream


async def get_colcon_graph(workspace_root, package_selection_args):
    _, output, _ = await get_output(['colcon', 'graph'] + package_selection_args, cwd=workspace_root)
    return parse_colcon_graph(output)


async def get_catkin_tools_graph(workspace_root, package_selection_args):
    upstream = {}
    pkg_name = None
    build_depends = set()
    run_section = False
    error_text = ''

    def stdout_callback(line):
        nonlocal upstream, pkg_name, build_depends, run_section
        if line[0] != ' ':
            if pkg_name:
                upstream[pkg_name] = build_depends
            pkg_name = line.strip()
            if pkg_name[-1] == ':':
                pkg_name = pkg_name[:-1]
            build_depends = set()
            run_section = False
        elif line == '  build_depend:\n':
            return
        elif line == '  run_depend:\n':
            run_section = True
        elif run_section:
            return
        else:
            dep_name = line.strip()[2:]
            build_depends.add(dep_name)

    def stderr_callback(line):
        nonlocal error_text
        error_text += line

    cmd = ['catkin', 'list', '--rdeps', '--unformatted']
    if package_selection_args:
        cmd += [arg for arg in package_selection_args if arg != '--no-deps']

    ret = await run(cmd, cwd=workspace_root,
                    stdout_callback=lambda line: stdout_callback(line), stderr_callback=stderr_callback)

    if ret != 0 or error_text:
        click.secho(error_text, fg='red')
        raise RuntimeError('Error retrieving dependencies!')

    if pkg_name:
        upstream[pkg_name] = build_depends

    # Check package_selection_args, limit upstream as needed
    return upstream


def add_package_selection_args(parser, workspace_root=None):
    completer = PackageCompleter(workspace_root, local=True)

    parser.add_argument('--this', action='store_true')
    parser.add_argument('-n', '--no-deps', action='store_true')
    parser.add_argument('-s', '--skip-packages', nargs='+').completer = completer
    parser.add_argument('include_packages', metavar='include_package', nargs='*').completer = completer
    return parser


def get_package_selection_args(args, build_type, pkg_name):
    package_selection_args = []

    if args.this and not pkg_name:
        raise RuntimeError('Not currently in a package')
    elif args.no_deps and not (args.this or args.include_packages):
        raise RuntimeError('With --no-deps, you must specify packages to build.')

    if build_type == BuildType.COLCON:
        if args.no_deps:
            package_selection_args.append('--packages-select')
        elif args.this or args.include_packages:
            package_selection_args.append('--packages-up-to')
        if args.this:
            package_selection_args.append(pkg_name)
        if args.include_packages:
            package_selection_args += args.include_packages
        if args.skip_packages:
            package_selection_args.append('--packages-skip')
            package_selection_args += args.skip_packages
    elif build_type == BuildType.CATKIN_TOOLS:
        if args.no_deps:
            package_selection_args.append('--no-deps')
        if args.this:
            package_selection_args.append(pkg_name)
        if args.include_packages:
            package_selection_args += args.include_packages
        if args.skip_packages:
            raise NotImplementedError
    elif build_type == BuildType.CATKIN_MAKE:
        pkg_list = []
        if args.this:
            pkg_list.append(pkg_name)
        if args.include_packages:
            pkg_list += args.include_packages
        if pkg_list:
            if args.no_deps:
                package_selection_args.append('--pkg')
            else:
                package_selection_args.append('--only-pkg-with-deps')
            package_selection_args += pkg_list
        if args.skip_packages:
            pkg_s = ';'.join(args.skip_packages)
            package_selection_args.append(f'-DCATKIN_BLACKLIST_PACKAGES="{pkg_s}"')

    return package_selection_args


def generate_build_command(build_type, unknown_args, package_selection_args=[], continue_on_failure=False, jobs=None,
                           cmake_build_type=None, workspace_root=None):
    cmake_args = []
    if cmake_build_type is None:
        cmake_build_type = get_config('cmake_build_type', 'Release', workspace_root)
    if cmake_build_type:
        cmake_args.append(f'-DCMAKE_BUILD_TYPE={cmake_build_type}')

    cmake_args += get_config('extra_cmake_args', [], workspace_root)
    extra_build_args = get_config('extra_build_args', [], workspace_root)

    if build_type == BuildType.COLCON:
        command = ['colcon', 'build', '--event-handlers', 'desktop_notification-', 'status-']
        if continue_on_failure:
            command.append('--continue-on-error')
        command += package_selection_args
        if jobs is not None:
            command += ['--parallel-workers', str(jobs)]
        command += unknown_args + extra_build_args

        if cmake_args:
            command += ['--cmake-args'] + cmake_args
    elif build_type == BuildType.CATKIN_TOOLS:
        command = ['catkin', 'build']
        if continue_on_failure:
            command.append('--continue-on-failure')
        command += package_selection_args
        if jobs is not None:
            command += ['--jobs', str(jobs)]
        command += unknown_args + extra_build_args
        if cmake_args:
            command += ['--cmake-args'] + cmake_args
    elif build_type == BuildType.CATKIN_MAKE:
        command = ['catkin_make']
        if continue_on_failure:
            raise NotImplementedError()
        command += package_selection_args
        if jobs is not None:
            command += ['--jobs', str(jobs)]
        command += unknown_args + extra_build_args
        command += cmake_args
    else:
        raise NotImplementedError(f'Unsupported build type {build_type}')
    return command


async def run_build_command(build_type, workspace_root, extra_args=[], package_selection_args=[],
                            continue_on_failure=True, jobs=None, cmake_build_type=None, toggle_graphics=False,
                            return_build_status=False):
    command = generate_build_command(build_type, extra_args, package_selection_args, continue_on_failure, jobs,
                                     cmake_build_type, workspace_root)
    stdout_callback = None
    stderr_callback = None

    graphic_build = get_config('graphic_build', True)
    if toggle_graphics:
        graphic_build = not graphic_build

    if graphic_build and build_type != BuildType.CATKIN_MAKE:
        build_status = BuildStatus()
        display = BuildStatusDisplay(build_status)
        if build_type == BuildType.COLCON:
            build_status.set_dependencies(await get_colcon_graph(workspace_root, package_selection_args))
            stdout_callback = build_status.out_callback
            stderr_callback = build_status.err_callback
        elif build_type == BuildType.CATKIN_TOOLS:
            build_status.set_dependencies(await get_catkin_tools_graph(workspace_root, package_selection_args))
            stdout_callback = build_status.out_callback
            stderr_callback = build_status.err_callback
    else:
        # Graphical interface not implemented for catkin_make
        build_status = None
        display = None

    code = await run(command, cwd=workspace_root,
                     stdout_callback=stdout_callback, stderr_callback=stderr_callback)

    if display:
        display.finish()
        for line in build_status.error_buffer:
            print(line, file=sys.stderr)
        build_status.print_status()

    if return_build_status:
        return code, build_status
    else:
        return code
