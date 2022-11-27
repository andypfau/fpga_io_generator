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


    def generate(self):
        
        md = []

        md.append(self.bus.name)
        md.append('==========')
        md.append('')
        md.append(f'{self.bus.topology}')


        md.append('')
        md.append('')
        md.append('Slaves')
        md.append('---------')
        md.append('')

        
        self.md = '\n'.join(md)
