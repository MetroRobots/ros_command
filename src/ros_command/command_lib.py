import asyncio
from asyncio import create_subprocess_exec
from asyncio.subprocess import DEVNULL, PIPE
import pathlib
import sys

import click

# Brought to you by https://stackoverflow.com/questions/803265/getting-realtime-output-using-subprocess


async def _read_stream(stream, callback, encoding='UTF8'):
    while True:
        line = await stream.readline()
        if line:
            callback(line.decode(encoding))
        else:
            break


def _default_stdout_callback(line):
    """Default callback for stdout that just prints."""
    click.echo(line, nl=False)


def _default_stderr_callback(line):
    """Default callback for stderr that prints to stdout in red."""
    click.secho(line, fg='red', nl=False)


async def run(command, stdout_callback=None, stderr_callback=None, cwd=None):
    """Run a command (array of strings) and process its output with callbacks."""
    process = await create_subprocess_exec(
        *command, stdout=PIPE, stderr=PIPE, cwd=cwd
    )

    if stdout_callback is None:
        stdout_callback = _default_stdout_callback
    if stderr_callback is None:
        stderr_callback = _default_stderr_callback

    await asyncio.wait([asyncio.create_task(_read_stream(process.stdout, stdout_callback)),
                        asyncio.create_task(_read_stream(process.stderr, stderr_callback))])

    return await process.wait()


async def run_silently(command, cwd=None):
    """Run a command (array of strings) and hide all output."""
    process = await create_subprocess_exec(
        *command, stdout=DEVNULL, stderr=DEVNULL, cwd=cwd
    )

    return await process.wait()


async def get_output(command, cwd=None):
    """Run a command (array of strings) and return its standard output and error."""
    out = []
    err = []

    def gather_callback(lines, line):
        lines.append(line)

    ret = await run(command, cwd=cwd,
                    stdout_callback=lambda line: gather_callback(out, line),
                    stderr_callback=lambda line: gather_callback(err, line))

    return ret, ''.join(out), ''.join(err)


async def get_overlayed_command(command):
    _, which_output, _ = await get_output(['which', '-a', command])
    cmds = which_output.splitlines()
    executing_folder_s = str(pathlib.Path(sys.argv[0]).parent)
    return next(r for r in cmds if not r.startswith(executing_folder_s))
