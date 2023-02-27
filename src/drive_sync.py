from typing import List, Tuple, Optional
from os import listdir, mkdir, remove, getcwd, chdir
from os.path import getmtime, join, isdir, dirname, exists
from shutil import rmtree
from datetime import datetime
from json import load, dump
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile
from argparse import ArgumentParser, RawTextHelpFormatter


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
    else:
        download_data()


def configure() -> None:
    """
    Configure the Google Drive token and the path to the remote repository to synchronize.
    """

    # 1. Configure Drive token
    update_token = True
    token_path = join(dirname(__file__), 'client_secrets.json')
    print(token_path)
    # 1.1. Check existing token
    if exists(token_path):
        with open(token_path, 'r') as file:
            token = load(file)
        print(f"\nYou already have an authentication configuration file with the following information:\n"
              f"  - 'project_id': {token['installed']['project_id']}\n"
              f"  - 'client_id': {token['installed']['client_id']}\n"
              f"  - 'client_secret': {token['installed']['client_secret']}")
        while (change := input("Update authentication: ").lower()) not in ['y', 'yes', 'n', 'no']:
            pass
        if change in ['n', 'no']:
            update_token = False
    # 1.2. Define a new token
    if update_token:
        token = {'installed': {'client_id': '',
                               'project_id': '',
                               'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                               'token_uri': 'https://oauth2.googleapis.com/token',
                               'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                               'client_secret': '',
                               'redirect_uris': ['http://localhost']}}
        print("\nAuthentication:")
        token['installed']['project_id'] = input("  - 'project_id': ")
        token['installed']['client_id'] = input("  - 'client_id': ")
        token['installed']['client_secret'] = input("  - 'client_secret': ")
        with open(token_path, 'w') as file:
            dump(token, file)

    # 2. Configure remote repository
    update_repo = True
    repo_file = join(dirname(__file__), 'DRIVE_REPO.txt')
    # 2.1. Check existing remote repository
    if exists(repo_file):
        with open(repo_file, 'r') as file:
            drive_repo = file.read()
        print(f"\nYou already defined the remote repository path to '{drive_repo}'.")
        while (change := input("Update remote repository path: ").lower()) not in ['y', 'yes', 'n', 'no']:
            pass
        if change in ['n', 'no']:
            update_repo = False
    # 2.2. Define a new remote repository
    if update_repo:
        with open(repo_file, 'w') as file:
            drive_repo = input("\nRemote repository path: ")
            file.write(drive_repo)

    # 3. Test the configuration
    __get_authentication()


def upload_data() -> None:
    """
    Synchronize the remote Drive repository with the local repository.
    """

    # 1. Check data folder existence locally
    # todo: not 'data'
    data_path = join(dirname(__file__), 'data')
    if not exists(data_path):
        raise ValueError(f"The path '{data_path}' does not exist.")

    # 2. Authenticate
    drive, project_id = __get_authentication()

    # 3. Check data folder existence remotely
    remote_tree = __get_remote_tree(drive=drive, parent_id=project_id)
    data_folder = __get_remote_file(remote_tree=remote_tree, title='data')
    if data_folder is None:
        data_folder = drive.CreateFile({'title': 'data', 'parents': [{'id': project_id}],
                                        'mimeType': 'application/vnd.google-apps.folder'})
        data_folder.Upload()

    # 4. Upload data repository
    __upload_local_folder(drive=drive, folder_path=data_path, folder_id=data_folder['id'])


def download_data() -> None:
    """
    Synchronize the local repository with the remote Drive repository.
    """

    # 1. Check data folder existence locally
    # todo: not 'data'
    data_path = join(dirname(__file__), 'data')
    if not exists(data_path):
        mkdir(data_path)

    # 2. Authenticate
    drive, project_id = __get_authentication()

    # 3. Check data folder existence remotely
    remote_tree = __get_remote_tree(drive=drive, parent_id=project_id)
    data_folder = __get_remote_file(remote_tree=remote_tree, title='data')
    if data_folder is None:
        raise ValueError("The remote folder 'data' does not exist.")

    # 4. Download data repository
    __download_remote_folder(drive=drive, folder_path=data_path, folder_id=data_folder['id'])


def __get_authentication() -> Tuple[GoogleDrive, str]:

    # 1. Check authentication files in the module repository
    working_directory = getcwd()
    chdir(dirname(__file__))
    if not exists('client_secrets.json'):
        raise FileNotFoundError("Authentication file not found. Please run '$drive_sync configure'.")
    elif not exists('DRIVE_REPO.txt'):
        raise FileNotFoundError("Remote repository name not found. Please run '$drive_sync configure'.")

    # 2. Get authentication
    auth = GoogleAuth()
    auth.LocalWebserverAuth()
    drive = GoogleDrive(auth)
    project_id = __get_project_id(drive)

    # 3. Return to the previous working directory
    chdir(working_directory)
    return drive, project_id


def __get_project_id(drive: GoogleDrive) -> str:

    remote_path_id = 'root'
    remote_path = '/'
    with open(join(dirname(__file__), 'DRIVE_REPO.txt'), 'r') as file:
        drive_repo = file.read()
    for path in drive_repo.split('/'):
        remote_tree = __get_remote_tree(drive=drive, parent_id=remote_path_id)
        remote_folder = __get_remote_file(remote_tree=remote_tree, title=path)
        if remote_folder is None:
            raise ValueError(f"The folder '{path}' does not exists in '{remote_path}'.")
        remote_path += f'{path}/'
        remote_path_id = remote_folder['id']
    return remote_path_id


def __get_remote_tree(drive: GoogleDrive,
                      parent_id: str) -> List[GoogleDriveFile]:

    return drive.ListFile({'q': f'"{parent_id}" in parents and trashed=false'}).GetList()


def __get_remote_file(remote_tree: List[GoogleDriveFile],
                      title: str) -> Optional[GoogleDriveFile]:

    if len(remote_file := list(filter(lambda f: f['title'] == title, remote_tree))) == 0:
        return None
    return remote_file[0]


def __get_last_modified(remote_file: GoogleDriveFile,
                        local_file: str) -> str:

    # Remote format: <year>-<month>-<day>T<hour>:<minute>:<second>.<millisecond>
    remote_date = remote_file['modifiedDate']
    remote_day, remote_time = remote_date.split('T')[0], remote_date.split('T')[1].split('.')[0]

    # Local format: <year>-<month>-<day> <hour>:<minute>:<second>.<millisecond>
    local_date = str(datetime.fromtimestamp(getmtime(local_file)))
    local_day, local_time = local_date.split(' ')[0], local_date.split(' ')[1].split('.')[0]

    # Compare each number
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

    local_tree = sorted(listdir(folder_path))
    remote_tree = __get_remote_tree(drive=drive, parent_id=folder_id)

    # Check removed files
    for remote_file in remote_tree:
        if remote_file['title'] not in local_tree:
            remote_file.Delete()

    # Check new files and modified files
    for local_file in local_tree:
        local_path = join(folder_path, local_file)

        # Upload a folder
        if isdir(local_path):
            remote_dir = __get_remote_file(remote_tree=remote_tree, title=local_file)
            # The folder does not exist remotely
            if remote_dir is None:
                remote_dir = drive.CreateFile({'title': local_file, 'parents': [{'id': folder_id}],
                                               'mimeType': 'application/vnd.google-apps.folder'})
                remote_dir.Upload()
            print(f'{space}Uploading {local_path}...')
            __upload_local_folder(drive=drive, folder_path=local_path, folder_id=remote_dir['id'], space=f'{space}   ')

        # Upload a file
        else:
            remote_file = __get_remote_file(remote_tree=remote_tree, title=local_file)
            # The file does not exist remotely
            if remote_file is None:
                print(f'{space}... file: {local_path}')
                remote_file = drive.CreateFile({'title': local_file, 'parents': [{'id': folder_id}]})
                remote_file.SetContentFile(local_path)
                remote_file.Upload()
            # The file is already existing remotely but was modified locally
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

    local_tree = sorted(listdir(folder_path))
    remote_tree = __get_remote_tree(drive=drive, parent_id=folder_id)

    # Check removed files
    for local_file in local_tree:
        if local_file not in [remote_file['title'] for remote_file in remote_tree]:
            local_path = join(folder_path, local_file)
            if isdir(local_path):
                rmtree(local_path)
            else:
                remove(local_path)

    # Check new files and modified files
    for remote_file in remote_tree:
        path = join(folder_path, remote_file['title'])

        # Download a folder
        if 'folder' in remote_file['mimeType']:
            # The folder does not exist locally
            if not exists(path):
                mkdir(path)
            print(f'{space}Downloading {path}...')
            __download_remote_folder(drive=drive, folder_path=path, folder_id=remote_file['id'], space=f'{space}   ')

        # Download a file
        else:
            # The file does not exist locally
            if not exists(path):
                print(f'{space}... file: {path}')
                remote_file.GetContentFile(path)
            # The file is already existing locally but was modified remotely
            elif __get_last_modified(remote_file=remote_file, local_file=path) == 'remote':
                print(f'{space}... file: {path}')
                remove(path)
                remote_file.GetContentFile(path)
