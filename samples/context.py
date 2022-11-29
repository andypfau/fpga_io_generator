import os
import sys
import shutil

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


import src


def workdir() -> str:
    return os.path.dirname(__file__)


def demo_output_folder() -> str:
    return os.path.join(workdir(), 'output')


def prepare_output_folder():
    os.makedirs(demo_output_folder(), exist_ok=True)
