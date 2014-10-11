#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='pmxbot-glossary',
    version='0.1',
    description='A pmxbot glossary extension.',
    author='Harvey Rogers',
    author_email='harveyr@gmail.com ',
    url='https://github.com/harveyr/pmxbot-glossary/',
    license='MIT',
    packages=find_packages(),
    entry_points=dict(
        pmxbot_handlers=[
            'Glossary = glossary.glossary:Glossary.initialize',
        ]
    ),
)
