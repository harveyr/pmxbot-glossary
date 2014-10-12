#!/usr/bin/env python
from setuptools import setup, find_packages

import glossary

setup(
    name='pmxbot-glossary',
    version=glossary.__version__,
    description='A pmxbot glossary extension.',
    author='Harvey Rogers',
    author_email='harveyr@gmail.com ',
    url='https://github.com/harveyr/pmxbot-glossary/',
    license='MIT',
    packages=find_packages(),
    install_requires=['pmxbot'],
    entry_points=dict(
        pmxbot_handlers=[
            'Glossary = glossary.glossary:Glossary.initialize',
        ]
    ),
)
