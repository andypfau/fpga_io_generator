from ..tools import get_adr_bits

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..structure.types import WbBus, WbMaster, WbSlave

import math, warnings



class BusMdGenerator:

    def __init__(self, bus: 'WbBus'):
        self.bus = bus
        
        gen = BusMdGeneratorHelper(bus)
        self.md = gen.md
    

    def get_md(self) -> str:
        return self.md
    

    def save(self, filename: str):
        with open(filename, 'w') as fp:
            fp.write(self.get_md())
           


class BusMdGeneratorHelper:

    def __init__(self, bus: 'WbBus'):
        self.bus = bus

        self.generate()


    def md_table(self, rows):
        
        cols = zip(*rows)
        widths = [max([len(str(cell))+2 for cell in col]) for col in cols]

        def print_row(row):
            line = []
            for width,cell in zip(widths, row):
                s = ' ' + str(cell) + ' '
                while len(s) < width:
                    s += ' '
                line.append(s)
            return '|' + '|'.join(line) + '|'

        def print_separator_row():
            line = []
            for width in widths:
                line.append('-'*width)
            return '|' + '|'.join(line) + '|'

        md = []
        for i, row in enumerate(rows):
            md.append(print_row(row))
            if i==0:
                md.append(print_separator_row())

        return md


    def generate(self):
        
        md = []

        md.append(self.bus.name)
        md.append('==========')
        md.append('')

        
        self.md = '\n'.join(md)
