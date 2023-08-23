# DriveSync

**DriveSync** is a small Python package that enable to easily synchronize a local repository with a Google Drive folder.
The behavior was inspired from GitHub (`push` and `pull` commands) to manage only the files / folders that were 
created or modified locally / remotely.


## Prerequisites

1. You first need to create your credentials to access the Google Services API. The steps are detailed in 
   [this article](https://medium.com/@chingjunetao/simple-way-to-access-to-google-service-api-a22f4251bb52). Download the `.json` client authentication file and rename it to `client_secrets.json`.

1. The project is using [PyDrive2](https://github.com/iterative/PyDrive2) as a wrapper library of 
   [google-api-python-client](https://github.com/googleapis/google-api-python-client). Install it using pip:
   ```bash
   $ pip3 install pydrive2
   ```
   

## Installation

The project can be easily installed with `pip`:
```bash
$ git clone https://github.com/RobinEnjalbert/DriveSync
$ cd DriveSync
$ pip3 install .
```

To install the project for developers (editable mode):
```bash
$ git clone https://github.com/RobinEnjalbert/DriveSync
$ cd DriveSync
$ python3 setup_dev.py
```


## Using the project

For this example, we will synchronize the following fictive repositories:
* local folder path: `/home/bob/my_project`
* remote folder path: `/my_project`

The project can be used with the **Command Line Interface** or with a **Python interpreter**.

### Command Line Interface

1. Copy the `client_secrets.json` file in the local repository that you want to synchronize with Google Drive.

2. Configure the synchronization (test Google Drive credentials and define the remote folder path):
   ```bash
   $ dsync config
   >> Authenticate...
   >> Authentification successful.
   >> Remote repository path: /my_project
   ```
   A new folder `.dsync` will be created, it contains the synchronization information.

3. Edit the file `.dsync\ignore.txt` to add the files, folders and extensions that you don't want to synchronize.
   
   > **Warning**
   > An folder must start with `/` and an extension must start with `*`.

4. Upload data from the local repository to the remote repository.
   The whole tree under this local repository will be managed.
   Only the new or modified files and folders will be uploaded. 
   If some files or folders were deleted locally, they will be removed remotely as well.
   ```bash
   $ cd /home/bob/my_project
   $ drive_sync push
   >> Uploading /home/bob/my_project...
        ... file: ***
        ... file: ***
        Uploading /home/bob/my_project/data...
          ... file: ***
          ... file: ***
   ```

5. Download data from the remote repository to the local repository.
   The whole tree under this remote repository will be managed.
   Only the new or modified files and folder will be downloaded.
   If some files or folders were deleted remotely, they will be removed locally as well.
   ```bash
   $ cd /home/bob/my_project
   $ drive_sync pull
   >> Downloading /home/bob/my_project...
        ... file: ***
        ... file: ***
        Downloading /home/bob/my_project/data...
          ... file: ***
          ... file: ***
   ```

### Python Interpreter

If you want to use the project as a Python package, you can use the following functions:
```python
from DriveSync import configure, upload_data, download_data

# 1. Configure
configure()

# 2. Upload data from the current local repository
upload_data()

# 3. Download data in the current local repository
download_data()
```
