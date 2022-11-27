from ...tools import md_table, binary_si
from ..structure.types import WbBus, WbMaster, WbSlave, WbBusTopology

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
        
        if self.bus.topology == WbBusTopology.SharedBus:
            topo = 'shared bus'
        elif self.bus.topology == WbBusTopology.Crossbar:
            topo = 'crossbar'
        else: raise ValueError()
        
        md.append(f'Topology: {topo}')

        md.append('')
        md.append('')
        md.append('Masters')
        md.append('---------')
        md.append('')

        table = [['Name', 'Port Size', 'Granularity', 'Addresses', 'Signals']]
        for master in self.bus.masters:

            adr_lo, adr_hi = master.get_adr_bits()
            sel_hi = master.get_sel_bit_count() - 1
            n_adr = 1 << (adr_hi-adr_lo+1)
            sigs = f'`dat[{master.port_size-1}:0]`, `adr[{adr_hi}:{adr_lo}]`, `sel[{sel_hi}:0]`'
            
            table.append([master.name, master.port_size, master.granularity, binary_si(n_adr), sigs])

        md.extend(md_table(table))

        md.append('')
        md.append('')
        md.append('Slaves')
        md.append('---------')
        md.append('')

        table = [['Name', 'Port Size', 'Granularity', 'Addresses', 'Signals']]
        for slave in self.bus.slaves:

            adr_lo, adr_hi = slave.get_adr_bits()
            sel_hi = slave.get_sel_bit_count() - 1
            n_adr = 1 << (adr_hi-adr_lo+1)
            sigs = f'`dat[{slave.port_size-1}:0]`, `adr[{adr_hi}:{adr_lo}]`, `sel[{sel_hi}:0]`'
            
            table.append([slave.name, slave.port_size, slave.granularity, binary_si(n_adr), sigs])

        md.extend(md_table(table))
        md.append('')
        
        self.md = '\n'.join(md)
