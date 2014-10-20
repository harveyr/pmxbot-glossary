#!/usr/bin/env python
from setuptools import setup, find_packages

import pmx_glossary

setup(
    name='pmxbot-glossary',
    version=pmx_glossary.__version__,
    description='A pmxbot glossary extension.',
    author='Harvey Rogers',
    author_email='harveyr@gmail.com ',
    url='https://github.com/harveyr/pmxbot-glossary/',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'pmxbot',
        'python-dateutil',
        'click',
    ],
    entry_points=dict(
        console_scripts=[
            'pmxglos = pmx_glossary.cli:cli'
        ],
        pmxbot_handlers=[
            'Glossary = pmx_glossary.glossary:Glossary.initialize',
        ]
    ),
)
