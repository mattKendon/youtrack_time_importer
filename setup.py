from setuptools import setup, find_packages

setup(
    name='youtrack_time_importer',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'requests',
        'python-dateutil',
        'parsedatetime'
    ],
    entry_points='''
        [console_scripts]
        youtrack=youtrack_time_importer.cli:youtrack
    ''',
)