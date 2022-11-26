import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


import src


def demo_output_folder() -> str:
    return os.path.join(os.path.dirname(__file__), 'output')


def prepare_output_folder():
    os.makedirs(demo_output_folder(), exist_ok=True)
