from setuptools import setup, find_packages

setup(
    name='manictime',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'requests',
        'python-dateutil'
    ],
    entry_points='''
        [console_scripts]
        yourscript=manictime.cli:youtrack
    ''',
)