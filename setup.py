#package configuration file
#!/usr/bin/env python3
from setuptools import setup
setup(
    name='megit',
    version='1.0',
    packages=['megit'],
    entry_points={
        'console_scripts':[
            'megit=megit.cli:main'
        ]
    }
)
