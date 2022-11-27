from ...registers import RegisterSet

import math, dataclasses, enum



class WbNode:


    def __init__(self, name: str, port_size: int, granularity: int, address_size: int):
        """
        name:          Name of this node
        port_size:     Port size, in bits
        granularity:   Bus granularity, in bits
        address_size:  The number of actual address bits (i.e. hi(sel)-lo(sel))
        """
        self.name, self.port_size, self.granularity, self.address_size = name, port_size, granularity, address_size
    

    def get_adr_bits(component):
        """
        Bit-indices of the address signal

        Example: a slave has a 32-bit bus, 8 bit granularity, and 16 addressable registers
        - due to bus width and granularity, its lowest address bit is 2
        - to address 16 registers, there must be a total of 4 address bits
        - so the address bit range must be [5:2]
        - then this method would return (2,5)
        """
        lo = int(math.ceil(math.log2(component.port_size//component.granularity)))
        return lo, lo+component.address_size-1


    def get_sel_bit_count(component):
        return component.port_size//component.granularity



class WbMaster(WbNode):


    def __init__(self, name: str, port_size: int, granularity: int, address_size: int):
        """
        name:          Name of this master
        port_size:     Port size, in bits
        granularity:   Bus granularity, in bits
        address_size:  The number of actual address bits (i.e. hi(sel)-lo(sel))
        """
        super().__init__(name, port_size, granularity, address_size)



class WbSlave(WbNode):


    def __init__(self, name: str, port_size: int, granularity: int, address_size: int, base_address: int):
        """
        name:          Name of this slave
        port_size:     Port size, in bits
        granularity:   Bus granularity, in bits
        address_size:  The number of actual address bits (i.e. hi(sel)-lo(sel))
        base_address:  Absolute base address
        """
        self.base_address = base_address
        self._register_set = None # dtype: RegisterSet
        super().__init__(name, port_size, granularity, address_size)

    
    @staticmethod    
    def from_register_set(register_set: "RegisterSet") -> "WbSlave":
        ''' Create a WbSlave from a RegisterSet '''
        adr_lo,adr_hi = register_set.address_bit_range()
        n_addresses = adr_hi-adr_lo+1
        slave = WbSlave(register_set.name, register_set.base_address, register_set.port_size, RegisterSet.granularity(), n_addresses)
        slave._register_set = register_set
        return slave



class WbBusTopology(enum.Enum):

    ''' Shared bus topology; only one master can communicate with a slave at any given time '''
    SharedBus = enum.auto()
    
    ''' Crossbar-switch topology; multiple masters can communicate to different slaves (unless there are conflicts) '''
    Crossbar = enum.auto()



@dataclasses.dataclass
class WbBus:
    name: str
    masters: list[WbMaster]
    slaves: list[WbSlave]
    topology: WbBusTopology = WbBusTopology.SharedBus
