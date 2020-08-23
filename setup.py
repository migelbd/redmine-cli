import os, sys
from setuptools import setup, find_packages

from redmine import __version__

requirements = [
    'attrs==20.1.0',
    'certifi==2020.6.20',
    'chardet==3.0.4',
    'click==7.1.2',
    'cmd2==1.3.4',
    'colorama==0.4.3',
    'commonmark==0.9.1',
    'idna==2.10',
    'importlib-metadata==1.7.0',
    'prettytable==0.7.2',
    'profig==0.5.1',
    'prompt-toolkit==3.0.6',
    'Pygments==2.6.1',
    'pyperclip==1.8.0',
    'pyreadline==2.1',
    'python-redmine==2.3.0',
    'questionary==1.5.2',
    'redmine-cli-tool==0.0.2',
    'requests==2.24.0',
    'rich==5.2.1',
    'typing-extensions==3.7.4.3',
    'urllib3==1.25.10',
    'wcwidth==0.2.5',
    'zipp==3.1.0',

]

if sys.version.startswith("2.6"):
    requirements.append("argparse==1.3.0")

setup(
    name="Redmine CLI Tool",
    version=".".join(map(str, __version__)),
    description="A command-line utility to interact with Redmine",
    url='https://github.com/migelbd/redmine-cli',
    license='MIT',
    author='migelbd',
    author_email='migel.bd@gmail.com',
    packages=['redmine'],
    include_package_data=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    install_requires=requirements,
    tests_require=[],
    entry_points={
        'console_scripts': [
            'redmine = redmine.main:main',
        ]
    }
)
