# DriveSync

**DriveSync** is a small Python package that enable to easily synchronize a local repository with a Google Drive folder.
The behavior was inspired from GitHub (`push` and `pull` commands) to manage only the files / folders that were 
created or modified locally / remotely.


## Prerequisites

1. You first need to create your credentials to access the Google Services API. The steps are detailed in 
   [this article](https://medium.com/@chingjunetao/simple-way-to-access-to-google-service-api-a22f4251bb52).
2. The project is using [PyDrive](https://github.com/googledrive/PyDrive) as a wrapper library of 
   [google-api-python-client](https://github.com/googleapis/google-api-python-client):
   ```bash
   $ pip3 install pydrive
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

For this example, we will synchronize the following repositories:
* local folder path: `/home/bob/my_project/data`
* remote folder path: `/Code/my_project/data`

The project can be used with the **Command Line Interface** or with a **Python interpreter**.

1. Configure the **DriveSync** using you Google Drive credentials and the remote folder path:
   ```bash
   $ drive_sync config
   >> Authentication:
        - project_id: ***
        - client_id: ***
        - client_secret: ***
   >> Remote repository path: /Code/my_project/data
   ```

   > **Warning**
   > For now, the configuration only stores a single local / remote folders pair.
   > If you need to synchronize several folders, you must run the configuration again to change the remote repository 
   > path.

2. Upload data from the local repository to the remote repository.
   The whole tree under this local repository will be managed.
   Only the new or modified files and folders will be uploaded. 
   If some files or folders were deleted locally, they will be removed remotely as well.
   ```bash
   $ cd /home/bob/my_project/data
   $ drive_sync push
   >> Uploading /home/bob/my_project/data...
        ... file: ***
        ... file: ***
        Uploading /home/bob/my_project/data/***...
          ... file: ***
          ... file: ***
   ```

3. Download data from the remote repository to the local repository.
   The whole tree under this remote repository will be managed.
   Only the new or modified files and folder will be downloaded.
   If some files or folders were deleted remotely, they will be removed locally as well.
   ```bash
   $ cd /home/bob/my_project/data
   $ drive_sync pull
   >> Downloading /home/bob/my_project/data...
        ... file: ***
        ... file: ***
        Downloading /home/bob/my_project/data/***...
          ... file: ***
          ... file: ***
   ```

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
