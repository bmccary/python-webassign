
from setuptools import setup

setup(
        name='webassign',
        version='0.1',
        description='Utilities for WebAssign',
        url='http://github.com/bmccary/python-webassign',
        author='Brady McCary',
        author_email='brady.mccary@gmail.com',
        license='MIT',
        packages=['webassign'],
        install_requires=[
            ],
        scripts=[
                    'bin/webassign-to-csv',
                    'bin/webassign-to-meta',
                ],
        zip_safe=False
    )
