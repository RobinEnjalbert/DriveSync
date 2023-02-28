# DriveSync

**DriveSync** is a small Python module that enable to easily synchronize a local repository with a Google Drive folder.
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

*In progress*
