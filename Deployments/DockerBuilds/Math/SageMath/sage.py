#!/usr/bin/env python3
"""Use installed Docker Sage: offline batch checks or authenticated local Jupyter."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import uuid


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', default='sagemath/sagemath:latest',
                   help='Already installed tag, digest or ID; never pulled/built')
    p.add_argument('--workdir', type=Path,
                   help='Existing directory mounted at /work (default: current directory)')
    p.add_argument('--write', action='store_true', help='Explicitly permit writes in /work')
    p.add_argument('--port', type=int, default=8889, help='Jupyter localhost port')
    p.add_argument('--timeout', type=int, default=180, help='Batch time limit, seconds')
    p.add_argument('--dry-run', action='store_true', help='Print command without Docker access')
    sub = p.add_subparsers(dest='mode', required=True)
    sub.add_parser('doctor', help='Inspect image and run an exact arithmetic smoke check')
    sub.add_parser('eval', help='Evaluate Sage-preparsed code').add_argument('expression')
    run = sub.add_parser('run', help='Run a .py or .sage file beneath --workdir')
    run.add_argument('script', type=Path)
    run.add_argument('args', nargs=argparse.REMAINDER)
    sub.add_parser('repl', help='Interactive Sage shell, no network')
    sub.add_parser('jupyter', help='Foreground token-authenticated notebook server')
    return p


def build_command(a, image, name):
    work = (a.workdir or Path.cwd()).resolve()
    if not work.is_dir():
        raise ValueError('--workdir must be an existing directory; create scratch storage first')
    if ',' in str(work):
        raise ValueError('Docker --mount cannot represent a workdir containing a comma')
    if not 1 <= a.port <= 65535 or a.timeout < 1:
        raise ValueError('Port must be 1..65535 and timeout must be positive')
    if a.mode == 'jupyter' and (not a.write or a.workdir is None):
        raise ValueError('Jupyter needs --write and an explicit scratch --workdir')
    command = ['docker', 'run', '--rm', '--name', name, '--pull=never',
               '--user', f'{os.getuid()}:{os.getgid()}', '-e', 'HOME=/tmp']
    if a.mode == 'jupyter':
        command += ['--publish', f'127.0.0.1:{a.port}:8888']
    else:
        command += ['--network=none']
    if a.mode == 'repl':
        command += ['-it']
    # Doctor needs no repository mount at all.
    if a.mode != 'doctor':
        mount = f'type=bind,src={work},dst=/work' + ('' if a.write else ',readonly')
        command += ['--mount', mount, '--workdir', '/work']
    else:
        command += ['--workdir', '/tmp']
    command += ['--entrypoint', 'sage', image]
    if a.mode == 'doctor':
        command += ['-python', '-c',
                    'import json; from sage.all import QQ, matrix; '
                    'from sage.version import version; '
                    'A=matrix(QQ, [[1,2],[3,4]]); assert A.det()==-2; '
                    'print(json.dumps({"sage_version":version,"exact_determinant":str(A.det()),"passed":True}))']
    elif a.mode == 'eval':
        command += ['-c', a.expression]
    elif a.mode == 'run':
        script = (work / a.script).resolve()
        relative = script.relative_to(work)  # Reject ../ and symlink escapes.
        if not script.is_file() or script.suffix not in ('.py', '.sage'):
            raise ValueError('Script must be an existing .py or .sage file beneath --workdir')
        command += (['-python'] if script.suffix == '.py' else [])
        command += [str(Path('/work') / relative), *a.args]
    elif a.mode == 'jupyter':
        command += ['-n', 'jupyter', '--no-browser', '--ip=0.0.0.0', '--port=8888']
    return command


def main(argv=None):
    p = parser()
    a = p.parse_args(argv)
    name = 'sage-local-' + uuid.uuid4().hex[:12]
    try:
        command = build_command(a, a.image, name)
        if a.dry_run:
            print(shlex.join(command))
            return 0
        image = subprocess.check_output(
            ['docker', 'image', 'inspect', a.image, '--format', '{{.Id}}'],
            text=True, timeout=15).strip()
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
            raise ValueError('Docker returned an invalid image ID')
        command = build_command(a, image, name)
        print(json.dumps({'image': image, 'container': name}), file=sys.stderr, flush=True)
        if a.mode == 'jupyter':
            print(f'Use the token from Jupyter with http://127.0.0.1:{a.port}. '
                  'Keep this terminal open; Ctrl+C stops this session.', file=sys.stderr, flush=True)
        try:
            return subprocess.run(command, timeout=None if a.mode in ('jupyter', 'repl')
                                  else a.timeout).returncode
        finally:
            # Only our uniquely named container; never another user session.
            subprocess.run(['docker', 'stop', '--time', '3', name],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Sage launcher: {exc}. No image was pulled or built.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
