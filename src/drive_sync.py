from typing import List, Dict, Optional
from os import listdir, mkdir, remove, getcwd, chdir, rename
from os.path import getmtime, join, isdir, isfile, exists, sep
from shutil import rmtree
from datetime import datetime
from json import load, dump
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile
from argparse import ArgumentParser, RawTextHelpFormatter


SYNC_INFO_DIR = '.dsync'
AUTH_FILE = 'client_secrets.json'
IGNORE_FILE = 'ignore.txt'
REMOTE_FILE = 'remote_root.txt'


def execute_cli() -> None:
    """
    Command Line Interface.
    """

    description = "Command Line Interface for DriveSync. Available commands:\n" \
                  "  * 'config': configure the Drive connexion and synchronization.\n" \
                  "  * 'push': synchronize the remote Drive repository with the local repository.\n" \
                  "  * 'pull': synchronize the local repository with the remote Drive repository."
    available_actions = ['config', 'push', 'pull']

    parser = ArgumentParser(prog='drive_sync', description=description, formatter_class=RawTextHelpFormatter)
    parser.add_argument('command', default='config', type=str, choices=available_actions, nargs='?')
    args = parser.parse_args()
    if args.command == 'config':
        configure()
    elif args.command == 'push':
        upload_data()
    elif args.command == 'pull':
        download_data()


def configure() -> None:
    """
    Configure the Google Drive token and the path to the remote repository to synchronize.
    """

    # 1. Set the local root repository
    print("\nGOOGLE DRIVE SYNCHRONIZATION - Configuration"
          "\n--------------------------------------------")
    local_root = getcwd()

    # 2. Configure Google Drive authentication
    print("\nTesting the authentication...")
    sync_info_dir = join(local_root, SYNC_INFO_DIR)
    # 2.1. First configuration
    if not exists(sync_info_dir):
        # 2.1.1. Check the auth file existence
        if not exists(join(local_root, AUTH_FILE)):
            raise FileNotFoundError(f"The file {join(local_root, AUTH_FILE)} does not exist."
                                    f"\nPlease provide the authentication information file (follow instructions: "
                                    f"https://github.com/RobinEnjalbert/DriveSync#using-the-project)")
        # 2.1.2. Try to authenticate
        auth = GoogleAuth()
        auth.LocalWebserverAuth()
        # 2.1.3. Create the sync folder
        mkdir(sync_info_dir)
        rename(src=join(local_root, AUTH_FILE),
               dst=join(sync_info_dir, AUTH_FILE))
        with open(join(sync_info_dir, REMOTE_FILE), 'w') as f:
            f.write(local_root.split(sep)[-1])
        with open(join(sync_info_dir, IGNORE_FILE), 'w') as f:
            default = '\n'.join(['/.dsync', '/.git', '/.idea', '/__pycache__', '/venv'])
            f.write(f"# Extensions to ignore (ex: *.txt, *.pdf)\n\n\n"
                    f"# Folders to ignore (ex: /data, /tmp)\n{default}\n\n"
                    f"# Files to ignore (ex: my_txt.txt, my_pdf.pdf)\n\n\n")
    # 2.2. Existing configuration
    else:
        __get_authentication()

    # 2. Configure remote repository
    with open(join(sync_info_dir, REMOTE_FILE), 'r') as f:
        print(f"Current remote root repository in your Google Drive: /{f.read()}")
    while (u := input("Update the current remote root path ? (y/n): ").lower()) not in ['y', 'yes', 'n', 'no']:
        pass
    if u in ['y', 'yes']:
        with open(join(sync_info_dir, REMOTE_FILE), 'w') as file:
            file.write(input("New remote root path: "))

    __get_local_ignore()


def upload_data() -> None:
    """
    Synchronize the remote Drive repository with the local repository.
    """

    print("\nGOOGLE DRIVE SYNCHRONIZATION - Upload"
          "\n-------------------------------------")

    # 1. Authenticate
    print("\nAuthenticate...")
    drive = __get_authentication()
    project_id = __get_project_id(drive)

    # 2. Upload the local repository
    print("\nUploading...")
    __upload_local_folder(drive=drive, folder_path=getcwd(), folder_id=project_id)


def download_data() -> None:
    """
    Synchronize the local repository with the remote Drive repository.
    """

    print("\nGOOGLE DRIVE SYNCHRONIZATION - Download"
          "\n---------------------------------------")

    # 1. Authenticate
    print("\nAuthenticate...")
    drive = __get_authentication()
    project_id = __get_project_id(drive)
    print(project_id)

    # 2. Download the remote repository
    print("\nDownloading...")
    __download_remote_folder(drive=drive, folder_path=getcwd(), folder_id=project_id)


def __get_authentication() -> GoogleDrive:

    # 1. Check the sync information repository (for upload / download cases)
    local_root = getcwd()
    sync_info_dir = join(local_root, SYNC_INFO_DIR)
    if not exists(sync_info_dir) or False in [exists(join(sync_info_dir, file)) for file in
                                              (AUTH_FILE, REMOTE_FILE, IGNORE_FILE)]:
        raise FileNotFoundError("Missing authentication information. Please run '$dsync configure'.")

    # 2. Get authentication
    chdir(sync_info_dir)
    auth = GoogleAuth()
    auth.LocalWebserverAuth()
    chdir(local_root)

    return GoogleDrive(auth)


def __get_project_id(drive: GoogleDrive) -> str:

    # 1. Get the path to the remote folder
    with open(join(getcwd(), SYNC_INFO_DIR, REMOTE_FILE), 'r') as file:
        remote_root_path = file.read()
        if len(remote_root_path) > 0 and remote_root_path[0] == '/':
            remote_root_path = remote_root_path[1:]

    # 2. Get the id of the sub-folders step by step (starting from 'root')
    remote_folder_id = 'root'
    for sub_folder in remote_root_path.split('/'):
        # 2.1. Get the next sub-folder
        remote_tree = __get_remote_tree(drive=drive, parent_id=remote_folder_id)
        remote_folder = __get_remote_file(remote_tree=remote_tree, title=sub_folder)
        # 2.2. If it does not exist, create it
        if remote_folder is None:
            remote_folder = drive.CreateFile({'title': sub_folder, 'parents': [{'id': remote_folder_id}],
                                              'mimeType': 'application/vnd.google-apps.folder'})
            remote_folder.Upload()
        # 2.3 Get the sub-folder id
        remote_folder_id = remote_folder['id']

    return remote_folder_id


def __get_local_ignore() -> Dict[str, List[str]]:

    # Get the ignore file content, then sort the items
    ignore = {'extensions': [], 'files': [], 'folders': []}
    with open(join(getcwd(), SYNC_INFO_DIR, IGNORE_FILE), 'r') as f:
        for item in f.readlines():
            # Comments or empty lines
            if item == '\n' or item[0] == '#':
                pass
            # Extensions
            elif item[0] == '*':
                ignore['extensions'].append(item[2:-1])
            # Folders
            elif item[0] == '/':
                ignore['folders'].append(item[1:-1])
            # Entry without extension are considered as folders
            elif len(item.split('.')) == 0:
                ignore['folders'].append(item[:-1])
            # Files
            else:
                ignore['files'].append(item[:-1])

    return ignore


def __get_remote_tree(drive: GoogleDrive,
                      parent_id: str) -> List[GoogleDriveFile]:

    # 1. Get the list of file in the current remote folder
    return drive.ListFile({'q': f'"{parent_id}" in parents and trashed=false'}).GetList()


def __get_remote_file(remote_tree: List[GoogleDriveFile],
                      title: str) -> Optional[GoogleDriveFile]:

    # 1. Get the file named 'title' in the list of file in the current remote folder
    if len(remote_file := list(filter(lambda f: f['title'] == title, remote_tree))) == 0:
        return None
    return remote_file[0]


def __get_last_modified(remote_file: GoogleDriveFile,
                        local_file: str) -> str:

    # 1. Remote date format: <year>-<month>-<day>T<hour>:<minute>:<second>.<millisecond>
    remote_date = remote_file['modifiedDate']
    remote_day, remote_time = remote_date.split('T')[0], remote_date.split('T')[1].split('.')[0]

    # 2. Local date format: <year>-<month>-<day> <hour>:<minute>:<second>.<millisecond>
    local_date = str(datetime.fromtimestamp(getmtime(local_file)))
    local_day, local_time = local_date.split(' ')[0], local_date.split(' ')[1].split('.')[0]

    # 3. Compare each element
    for remote, local in zip(remote_day.split('-') + remote_time.split(':'),
                             local_day.split('-') + local_time.split(':')):
        if int(remote) == int(local):
            pass
        else:
            return 'remote' if int(remote) > int(local) else 'local'


def __upload_local_folder(drive: GoogleDrive,
                          folder_path: str,
                          folder_id: str,
                          space: str = '') -> None:

    # 0. Get the ignored items
    ignore = __get_local_ignore()

    # 1. Get local and remote list of files in the current folder
    local_tree = sorted(listdir(folder_path))
    remote_tree = __get_remote_tree(drive=drive, parent_id=folder_id)

    # 2. Check for local removed files
    for remote_file in remote_tree:
        if remote_file['title'] not in local_tree:
            remote_file.Delete()

    # 3. Check for new or modified files
    for local_file in local_tree:
        local_path = join(folder_path, local_file)

        # 3.1. Upload a folder
        if isdir(local_path) and local_file not in ignore['folders'] and local_file.split('.')[-1] not in ignore['extensions']:
            # 3.1.1. Check that the remote folder exists
            remote_dir = __get_remote_file(remote_tree=remote_tree, title=local_file)
            if remote_dir is None:
                remote_dir = drive.CreateFile({'title': local_file, 'parents': [{'id': folder_id}],
                                               'mimeType': 'application/vnd.google-apps.folder'})
                remote_dir.Upload()
            # 3.1.2. Upload the local folder
            print(f'{space}Uploading {local_path}...')
            __upload_local_folder(drive=drive, folder_path=local_path, folder_id=remote_dir['id'], space=f'{space}   ')

        # 3.2. Upload a file
        elif isfile(local_path) and local_file not in ignore['files'] and local_file.split('.')[-1] not in ignore['extensions']:
            # 3.2.1. Check that the remote file exists
            remote_file = __get_remote_file(remote_tree=remote_tree, title=local_file)
            if remote_file is None:
                print(f'{space}... file: {local_path}')
                remote_file = drive.CreateFile({'title': local_file, 'parents': [{'id': folder_id}]})
                remote_file.SetContentFile(local_path)
                remote_file.Upload()
            # 3.2.2. The remote file already exists but was modified locally
            elif __get_last_modified(remote_file=remote_file, local_file=local_path) == 'local':
                print(f'{space}... file: {local_path}')
                remote_file.Delete()
                remote_file = drive.CreateFile({'title': local_file, 'parents': [{'id': folder_id}]})
                remote_file.SetContentFile(local_path)
                remote_file.Upload()


def __download_remote_folder(drive: GoogleDrive,
                             folder_path: str,
                             folder_id: str,
                             space: str = '') -> None:

    # 0. Get the ignored items
    ignore = __get_local_ignore()

    # 1. Get local and remote list of files in the current folder
    local_tree = sorted(listdir(folder_path))
    remote_tree = __get_remote_tree(drive=drive, parent_id=folder_id)

    # 2. Check for remote removed files
    for local_file in local_tree:
        if local_file not in [remote_file['title'] for remote_file in remote_tree]:
            local_path = join(folder_path, local_file)
            if isdir(local_path) and local_file not in ignore['folders']  and local_file.split('.')[-1] not in ignore['extensions']:
                rmtree(local_path)
            elif isfile(local_path) and local_file not in ignore['files'] and local_file.split('.')[-1] not in ignore['extensions']:
                remove(local_path)

    # 3. Check for new or modified files
    for remote_file in remote_tree:
        path = join(folder_path, remote_file['title'])

        # 3.1. Download a folder
        if 'folder' in remote_file['mimeType']:
            # 3.1.1. Check that the local folder exists
            if not exists(path):
                mkdir(path)
            # 3.1.2. Download the remote folder
            print(f'{space}Downloading {path}...')
            __download_remote_folder(drive=drive, folder_path=path, folder_id=remote_file['id'], space=f'{space}   ')

        # 3.2. Download a file
        else:
            # 3.2.1. Check that the local file exists
            if not exists(path):
                print(f'{space}... file: {path}')
                remote_file.GetContentFile(path)
            # 3.2.2. The local file already exists but was modified remotely
            elif __get_last_modified(remote_file=remote_file, local_file=path) == 'remote':
                print(f'{space}... file: {path}')
                remove(path)
                remote_file.GetContentFile(path)
