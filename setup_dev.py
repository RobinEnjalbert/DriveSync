from sys import argv, executable
from os import symlink, unlink, remove
from os.path import join, islink, dirname, sep
from shutil import which
from pathlib import Path
from site import getsitepackages
from pip._internal.operations.install.wheel import PipScriptMaker


# Package information
PROJECT = 'DriveSync'
root = join(Path(__file__).parent.absolute(), 'src')
USER_SITE = getsitepackages()[0]

# Check user entry
if len(argv) == 2 and argv[1] not in ['set', 'del']:
    raise ValueError(f"\nInvalid script option."
                     f"\nRun 'python3 dev.py set' to link {PROJECT} to your site package folder."
                     f"\nRun 'python3 dev.py del' to remove {PROJECT} link from your site package folder.")

# Option 1: create the symbolic links
if len(argv) == 1 or argv[1] == 'set':

    if not islink(join(USER_SITE, PROJECT)):
        symlink(src=join(root),
                dst=join(USER_SITE, PROJECT))
        print(f"Linked {join(USER_SITE, PROJECT)} -> {join(root)}")

    # Create the CLI
    if which('drive_sync') is None:
        # Generate the scripts
        maker = PipScriptMaker(None, dirname(executable))
        generated_scripts = maker.make_multiple(['dsync=DriveSync.drive_sync:execute_cli'])
        for script in generated_scripts:
            if script.split(sep)[-1].split('.')[0] != 'dsync':
                remove(script)

# Option 2: remove the symbolic links
else:
    if islink(join(USER_SITE, PROJECT)):
        unlink(join(USER_SITE, PROJECT))
        print(f"Unlinked {join(USER_SITE, PROJECT)} -> {join(root)}")
        remove(which('dsync'))
