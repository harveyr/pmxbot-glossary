#!/usr/bin/env python
import os
from pip.req import parse_requirements
from setuptools import setup, find_packages

import glossary

BASE_PATH = os.path.dirname(__file__)

reqs = parse_requirements(os.path.join(BASE_PATH, 'requirements.txt'))
reqs_strs = [str(r.req) for r in reqs]

setup(
    name='pmxbot-glossary',
    version=glossary.__version__,
    description='A pmxbot glossary extension.',
    author='Harvey Rogers',
    author_email='harveyr@gmail.com ',
    url='https://github.com/harveyr/pmxbot-glossary/',
    license='MIT',
    packages=find_packages(),
    install_requires=reqs_strs,
    entry_points=dict(
        pmxbot_handlers=[
            'Glossary = glossary.glossary:Glossary.initialize',
        ]
    ),
)
