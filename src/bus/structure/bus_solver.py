from ...tools import clog2
from .types import WbNode, WbBus
import warnings
import math



def ranges_overlap(lo1, hi1, lo2, hi2) -> bool:
    if lo2 >= lo1 and lo2 <= hi1:
        return True
    if hi2 >= lo1 and lo2 <= hi1:
        return True
    return False



class WbBusSolver:

    
    def __init__(self, bus: "WbBus"):
        self.bus = bus
        bus.check()
        self.define_bus_format()
        self.assign_slave_addresses()

    
    def define_bus_format(self):
        all_nodes = self.bus.masters + self.bus.slaves
        bus_port_size = max([n.port_size for n in all_nodes])
        bus_granularity = min([n.granularity for n in all_nodes])
        bus_address_size = max([n.address_size for n in all_nodes])
        self.bus.bus_format = WbNode('Bus', bus_port_size, bus_granularity, bus_address_size)
        
        highest_slave_address_size = max([s.address_size for s in self.bus.slaves])
        lowest_master_address_size = min([m.address_size for m in self.bus.masters])
        if highest_slave_address_size > lowest_master_address_size:
            warnings.warn(f'The smallest master address size ({lowest_master_address_size}) is less than the highest slave address size ({highest_slave_address_size}); not all slave addresses can be accessed', UserWarning)

    
    def assign_slave_addresses(self):
        
        bus_adr_hi, bus_adr_lo = self.bus.bus_format.address_size-1, int(round(math.log2(self.bus.bus_format.port_size // self.bus.bus_format.granularity)))
        bus_sel_hi, bus_sel_lo = self.bus.bus_format.port_size // self.bus.bus_format.granularity - 1, 0
        bus_sel_bits = bus_sel_hi + 1
        
        # addresses are absolute, i.e. they ignore those missing address LSBs
        # also, note that the addresses we define here are from the point of view of the bus, but the individual masters might differ
        next_free_address = 0
        slave_address_ranges = {}
        forbidden_mask = (1 << bus_adr_lo) - 1
        
        for slave in self.bus.slaves:
            if slave._requested_base_address is not Ellipsis:
                
                adr_lo = slave._requested_base_address
                adr_hi = adr_lo + (1<<(slave.address_size+bus_adr_lo-1)) - 1
                
                if (adr_lo & forbidden_mask) != 0:
                    raise RuntimeError(f'Slave {slave.name}\' base address is not aligned with the required bus granularity')
                
                for other_name,(other_adr_lo, other_adr_hi) in slave_address_ranges.items():
                    if ranges_overlap(adr_lo, adr_hi, other_adr_lo, other_adr_hi):
                        raise RuntimeError(f'Slave {slave.name}\'s address range overlaps with {other_name}\'s address range')
                
                slave_address_ranges[slave.name] = (adr_lo, adr_hi)
                slave._base_address = adr_lo
                
                next_free_address = max(next_free_address, adr_hi + 1)
        
        for slave in self.bus.slaves:
            if slave._requested_base_address is Ellipsis:
                
                assert (next_free_address & forbidden_mask) == 0
                
                adr_lo = next_free_address
                adr_hi = adr_lo + (1<<(slave.address_size+bus_adr_lo-1)) - 1
                
                slave_address_ranges[slave.name] = (adr_lo, adr_hi)
                slave._base_address = adr_lo
                
                next_free_address = adr_hi + 1
            
        for master in self.bus.masters:
            address_shift = clog2(self.bus.bus_format.port_size // master.port_size)
            master._address_shift = address_shift
