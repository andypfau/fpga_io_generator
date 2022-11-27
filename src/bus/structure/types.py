from ...registers import RegisterSet

import math, dataclasses, enum


@dataclasses.dataclass
class WbMaster:
    name: str
    ''' Port size, in bits '''
    port_size: int
    ''' Bus granularity, in bits '''
    granularity: int
    ''' Address size, in bits (the highest address bit index will be this minus 1; the lowest index depends on bus width and granularity)'''
    address_size: int


class WbSlave:

    def __init__(self, name: str, base_address: int, port_size: int, granularity: int, address_size: int):
        """
        name:         Name of this master
        base_address: Absolute base address
        port_size:    Port size, in bits
        granularity:  Bus granularity, in bits
        address_size: Address size, in bits (the highest address bit index will be this minus 1; the lowest index depends on bus width and granularity)
        """
        self.name, self.base_address, self.port_size, self.granularity, self.address_size = name, base_address, port_size, granularity, address_size

        self._register_set = None # dtype: RegisterSet

    
    @staticmethod    
    def from_register_set(register_set: "RegisterSet") -> "WbSlave":
        ''' Create a WbSlave from a RegisterSet '''
        _,adr_hi = register_set.address_bit_range()
        slave = WbSlave(register_set.name, register_set.base_address, register_set.port_size, RegisterSet.granularity(), adr_hi)
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
