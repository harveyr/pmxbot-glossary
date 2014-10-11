#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='pmxbot-glossary',
    version='0.1',
    description='pmxbot glossary extension',
    author='Harvey Rogers',
    author_email='harveyr@gmail.com ',
    packages=find_packages(),
    entry_points=dict(
        pmxbot_handlers=[
            'Glossary = glossary.glossary:Glossary.initialize',
        ]
    ),
)
