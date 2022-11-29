from ...tools import md_table, binary_si
from ..structure.types import WbBus, WbNode, WbBusTopology



class BusMdGenerator:

    def __init__(self, bus: 'WbBus', graph_filename: "str|None" = None):
        self.bus = bus
        
        gen = BusMdGeneratorHelper(bus, graph_filename)
        self.md = gen.md
    

    def get_md(self) -> str:
        return self.md
    

    def save(self, filename: str):
        with open(filename, 'w') as fp:
            fp.write(self.get_md())
           


def get_signals_str(node: "WbNode") -> str:

    adr_lo, adr_hi = node.get_adr_bits()
    sel_hi = node.get_sel_bit_count() - 1
    return f'`dat[{node.port_size-1}:0]`, `adr[{adr_hi}:{adr_lo}]`, `sel[{sel_hi}:0]`'



class BusMdGeneratorHelper:

    def __init__(self, bus: 'WbBus', graph_filename: "str|None"):
        self.bus = bus
        self.graph_filename = graph_filename

        self.generate()


    def generate(self):
        
        md = []
        
        any_plurality = len(self.bus.slaves)>1 or len(self.bus.masters)>1

        md.append(self.bus.name)
        md.append('==========')
        md.append('')
        md.append('')

        if self.graph_filename is not None:
            md.append('## Overview')
            md.append('')
            md.append(f'<img src="{self.graph_filename}" />')
            md.append('')
            md.append('')

        md.append('## Masters')
        md.append('')

        table = [['Name', 'Port Size', 'Granularity', 'Addresses', 'Address Shift', 'Signals', 'Adapter']]
        any_adapters = False
        for master in self.bus.masters:

            adr_lo, adr_hi = master.get_adr_bits()
            n_adr = 1 << (adr_hi-adr_lo+1)
            sigs = get_signals_str(master)
            need_adapter = self.bus.get_adapter(master) is not None
            adapt_str = 'yes' if need_adapter else 'no'
            any_adapters |= need_adapter
            
            table.append([master.name, master.port_size, master.granularity, binary_si(n_adr), master.get_address_shift(), sigs, adapt_str])

        if not any_adapters:
            table = [row[:-1] for row in table]
        md.extend(md_table(table))

        if any_plurality:

            md.append('')
            md.append('')
            md.append('## Bus')
            md.append('')
            
            if self.bus.topology == WbBusTopology.SharedBus:
                topo = 'shared bus'
            elif self.bus.topology == WbBusTopology.Crossbar:
                topo = 'crossbar'
            else: raise ValueError()
            
            md.append(f'- Topology: {topo}')
            md.append(f'- Port size: {self.bus.bus_format.port_size}')
            md.append(f'- Granularity: {self.bus.bus_format.port_size}')
            md.append(f'- Signals: {get_signals_str(self.bus.bus_format)}')

            if any([m.get_address_shift()!=0 for m in self.bus.masters]):

                md.append('')
                md.append('')
                md.append('### Address Table')
                md.append('')
                md.append('Due to address shifting, each master might have its own addressing scheme, as shown below.')
                md.append('')

                highest_base_address = max([s.get_base_address() for s in self.bus.slaves])
                highest_address_shift = max([m.get_address_shift() for m in self.bus.masters])
                adr_strlen = len(f'{highest_base_address<<highest_address_shift:X}')
                
                table = [[''] + [m.name for m in self.bus.masters]]

                for slave in self.bus.slaves:
                    row = [f'0x{slave.get_base_address()<<m.get_address_shift():0{adr_strlen}X}' for m in self.bus.masters]
                    table.append([slave.name] + row)
                
                md.extend(md_table(table))

        md.append('')
        md.append('')
        md.append('## Slaves')
        md.append('')

        highest_base_address = max([s.get_base_address() for s in self.bus.slaves])
        adr_strlen = len(f'{highest_base_address:X}')

        table = [['Base Address', 'Name', 'Port Size', 'Granularity', 'Addresses', 'Signals', 'Adapter']]
        any_adapters = False
        for slave in self.bus.slaves:

            adr_lo, adr_hi = slave.get_adr_bits()
            n_adr = 1 << (adr_hi-adr_lo+1)
            sigs = get_signals_str(slave)
            need_adapter = self.bus.get_adapter(slave) is not None
            adapt_str = 'yes' if need_adapter else 'no'
            any_adapters |= need_adapter
            
            table.append([f'0x{slave.get_base_address():0{adr_strlen}X}', slave.name, slave.port_size, slave.granularity, binary_si(n_adr), sigs, adapt_str])

        if not any_adapters:
            table = [row[:-1] for row in table]
        md.extend(md_table(table))
        md.append('')
        md.append('Note that the base address is given from the bus\'s point of view; masters might have to shift the address.')
        md.append('')
        
        self.md = '\n'.join(md)
