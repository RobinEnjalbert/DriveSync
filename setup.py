from setuptools import setup

PROJECT = 'DriveSync'
package = [PROJECT]
package_dir = {PROJECT: 'src'}

with open('README.md') as f:
    long_description = f.read()

# Installation
setup(name=PROJECT,
      version='1.0',
      description='A Python module to synchronize a local folder with a Google Drive folder.',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='R. Enjalbert',
      author_email='robin.enjalbert@inria.fr',
      url='https://github.com/RobinEnjalbert/DriveSync',
      packages=package,
      package_dir=package_dir,
      package_data={PROJECT: ['*.txt', '*.json']},
      install_requires=['pydrive'],
      entry_points={'console_scripts': ['drive_sync=DriveSync.drive_sync:execute_cli']})
