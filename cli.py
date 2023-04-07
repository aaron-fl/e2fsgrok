#!/usr/bin/env python
import os, sys
from subprocess import call, Popen, PIPE, DEVNULL
from os.path import join, abspath, split, exists

VENV_DIR = '.python' # This can be moved if needed
REQ = 'requirements' # This can be moved/renamed


def capture(cmd):
    proc = Popen(cmd, stdout=PIPE, stderr=DEVNULL)
    out,_ = proc.communicate()
    if proc.returncode: return None
    return out.decode('utf8')


def hash(fname):
    for cmd,idx in [(('openssl','dgst','-md5','-hex','-r'),0), (('md5',),-1)]:
        try:
            v = capture((*cmd, fname))
            return v.strip().split(' ')[idx] if v else None
        except FileNotFoundError:
            continue
    return None


def exec():
    os.execvp('python', ['python', './cli.py'] + sys.argv[1:])


def abort(venv, *reason):
    import shutil
    print('\n'+'!'*75,'\nERROR:', *reason)
    print('Look above for the specific error.','\n'+'!'*75,'\n')
    shutil.rmtree(venv, ignore_errors=True)
    sys.exit(1)


os.chdir(split(abspath(__file__))[0]) # Make the cwd the same as this file
if sys.prefix == sys.base_prefix: # Not in the virtual env
    venv = join(VENV_DIR, hash(REQ+'.lock') or 'nolock')
    new = not exists(venv)
    if new and call(['python3', '-m','venv', venv]):
        abort(venv, "Couldn't create python3 virtual environment at", repr(venv))
    # We have a venv python
    os.environ['PATH'] = join(venv,'bin') + os.pathsep + os.environ['PATH']
    if not new: exec()
    # Initialize the new venv
    if call(['python', '-m', 'pip', 'install', '--require-virtualenv', '--compile', '-U', 'pip']):
        abort(venv, 'Pip upgrade failed.')
    # Install required modules
    have_lock = exists(REQ+'.lock')
    if call(['python', '-m', 'pip', 'install', '--require-virtualenv', '--compile', '-r', REQ+('.lock' if have_lock else '.txt')]):
        abort('Failed to install some requirements.')
    if have_lock: exec()
    # Lock the requirements and move the venv
    lock_data = capture(['python','-m','pip','freeze','--local'])
    if not lock_data: abort("Pip freeze failed")
    with open(REQ+'.lock', 'w') as f: f.write(lock_data)
    # Move it to the new lockfile location
    venv2 = join(VENV_DIR, hash(REQ+'.lock') or 'nolock')
    import shutil
    shutil.move(venv, venv2)
    os.environ['PATH'] = os.pathsep.join([join(venv2,'bin')] + os.environ['PATH'].split(os.pathsep)[1:])
    exec()

# Now we are running in the virtual environment.
# Install REQ requirements and run the main command.
import yaclipy as CLI
from print_ext import Printer, PrettyException

try:
    from pyutil.main import main
    CLI.Command(main)(sys.argv[1:]).run()
except PrettyException as e:
    Printer().pretty(e)

