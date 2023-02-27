from typing import List, Tuple, Optional
from os import listdir, mkdir, remove
from os.path import getmtime, join, isdir, dirname, exists
from sys import argv
from shutil import rmtree
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydrive.files import GoogleDriveFile

with open('DRIVE_REPO.txt', 'r') as f:
    DRIVE_PROJECT = f.read()


def __get_authentication() -> Tuple[GoogleDrive, str]:

    auth = GoogleAuth()
    auth.LocalWebserverAuth()
    drive = GoogleDrive(auth)
    return drive, __get_project_id(drive)


def __get_remote_tree(drive: GoogleDrive,
                      parent_id: str) -> List[GoogleDriveFile]:

    return drive.ListFile({'q': f'"{parent_id}" in parents and trashed=false'}).GetList()


def __get_remote_file(remote_tree: List[GoogleDriveFile],
                      title: str) -> Optional[GoogleDriveFile]:

    if len(remote_file := list(filter(lambda f: f['title'] == title, remote_tree))) == 0:
        return None
    return remote_file[0]


def __get_project_id(drive: GoogleDrive) -> str:

    remote_path_id = 'root'
    remote_path = '/'
    for path in DRIVE_PROJECT.split('/'):
        remote_tree = __get_remote_tree(drive=drive, parent_id=remote_path_id)
        remote_folder = __get_remote_file(remote_tree=remote_tree, title=path)
        if remote_folder is None:
            raise ValueError(f"The folder '{path}' does not exists in '{remote_path}'.")
        remote_path += f'{path}/'
        remote_path_id = remote_folder['id']
    return remote_path_id


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


def upload_data():

    # Check data folder existence locally
    data_path = join(dirname(__file__), 'data')
    if not exists(data_path):
        raise ValueError(f"The path '{data_path}' does not exist.")

    # Authenticate
    drive, project_id = __get_authentication()

    # Check data folder existence remotely
    remote_tree = __get_remote_tree(drive=drive, parent_id=project_id)
    data_folder = __get_remote_file(remote_tree=remote_tree, title='data')
    if data_folder is None:
        data_folder = drive.CreateFile({'title': 'data', 'parents': [{'id': project_id}],
                                        'mimeType': 'application/vnd.google-apps.folder'})
        data_folder.Upload()

    # Upload data repository
    __upload_local_folder(drive=drive, folder_path=data_path, folder_id=data_folder['id'])


def download_data():

    # Check data folder existence locally
    data_path = join(dirname(__file__), 'data')
    if not exists(data_path):
        mkdir(data_path)

    # Authenticate
    drive, project_id = __get_authentication()

    # Check data folder existence remotely
    remote_tree = __get_remote_tree(drive=drive, parent_id=project_id)
    data_folder = __get_remote_file(remote_tree=remote_tree, title='data')
    if data_folder is None:
        raise ValueError("The remote folder 'data' does not exist.")

    # Download data repository
    __download_remote_folder(drive=drive, folder_path=data_path, folder_id=data_folder['id'])


# if __name__ == '__main__':
#
#     if len(argv) == 1:
#         print("Usage: python3 drive_sync.py [option] \nAvailable options: 'push', 'pull'")
#     elif argv[1].lower() == 'push':
#         upload_data()
#     elif argv[1].lower() == 'pull':
#         download_data()
#     else:
#         print("Usage: python3 drive_sync.py [option] \nAvailable options: 'push', 'pull'")
