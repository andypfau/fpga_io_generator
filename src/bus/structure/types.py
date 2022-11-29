from ...registers import RegisterSet

import math
import enum
import typing



class WbNode:


    def __init__(self, name: str, port_size: int, granularity: int, address_size: int):
        """
        name:          Name of this node
        port_size:     Port size, in bits
        granularity:   Bus granularity, in bits
        address_size:  The number of actual address bits (i.e. hi(sel)-lo(sel))
        """
        self.name, self.port_size, self.granularity, self.address_size = name, port_size, granularity, address_size
    

    def get_adr_bits(self):
        """
        Bit-indices of the address signal

        Example: a slave has a 32-bit bus, 8 bit granularity, and 16 addressable registers
        - due to bus width and granularity, its lowest address bit is 2
        - to address 16 registers, there must be a total of 4 address bits
        - so the address bit range must be [5:2]
        - then this method would return (2,5)
        """
        lo = int(math.ceil(math.log2(self.port_size//self.granularity)))
        return lo, lo+self.address_size-1


    def get_sel_bit_count(self):
        return self.port_size//self.granularity
    

    def _get_format(self) -> "tuple(int, int, int)":
        return (self.port_size, self.granularity, self.address_size)



class WbMaster(WbNode):


    def __init__(self, name: str, port_size: int, granularity: int, address_size: int):
        """
        name:          Name of this master
        port_size:     Port size, in bits
        granularity:   Bus granularity, in bits
        address_size:  The number of actual address bits (i.e. hi(sel)-lo(sel))
        """
        super().__init__(name, port_size, granularity, address_size)

        self._address_shift = None
    

    def get_address_shift(self) -> int:
        if self._address_shift is None:
            raise RuntimeError('This master was not properly initialized yet. Connect it to a bus first.')

        return self._address_shift



class WbSlave(WbNode):


    def __init__(self, name: str, port_size: int, granularity: int, address_size: int, base_address: "int|Ellipsis"):
        """
        name:          Name of this slave
        port_size:     Port size, in bits
        granularity:   Bus granularity, in bits
        address_size:  The number of actual address bits (i.e. hi(sel)-lo(sel))
        base_address:  Absolute base address; set to ... for automatic addressing
        """
        self._requested_base_address = base_address
        self._base_address = None
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
    

    def get_base_address(self) -> int:
        if self._base_address is None:
            raise RuntimeError('This slave was not properly initialized yet. Connect it to a bus first.')

        return self._base_address



class WbBusTopology(enum.Enum):

    ''' Shared bus topology; only one master can communicate with a slave at any given time '''
    SharedBus = enum.auto()
    
    ''' Crossbar-switch topology; multiple masters can communicate to different slaves (unless there are conflicts) '''
    Crossbar = enum.auto()



class WbBus:

    
    def __init__(self, name: str, masters: list[WbMaster], slaves: list[WbSlave], topology: WbBusTopology = WbBusTopology.SharedBus):
        """
        name:     Name of this bus
        masters:  Connected masters
        slaves:   Connected Slaves
        topology: Topology of the bus
        """
        self.name, self.masters, self.slaves, self.topology = name, masters, slaves, topology
        self.bus_format: typing.Optional[WbNode] = None
        self.check()
        
        from .bus_solver import WbBusSolver
        WbBusSolver(self)
    

    def check(self):
        
        if len(self.masters)<1 or len(self.slaves)<1:
            raise ValueError(f'Need at least one master and one slave')
        
        if len(self.slaves) != len(set([s.name for s in self.slaves])):
            raise RuntimeError(f'Slave names must be unique')
        if len(self.masters) != len(set([m.name for m in self.masters])):
            raise RuntimeError(f'Master names must be unique')
        
        for node in self.masters + self.slaves:
            if node.port_size not in [8, 16, 32, 64]:
                raise ValueError(f'Node {node.name} has invalid bus port size (must be 8 16, 32 or 64)')
            if node.granularity not in [8, 16, 32, 64]:
                raise ValueError(f'Node {node.name} has invalid bus granularity (must be 8 16, 32 or 64)')
            if node.granularity > node.port_size:
                raise ValueError(f'Node {node.name} has invalid bus granularity (must be >= port_size)')


    def get_adapter(self, node: "WbNode") -> "tuple[WbNode|WbNode]|None":
        """Returns either a tuple that describes the interfaces on each end of the adapter, or None, if no adapter is needed.
        The first element of the tuple is the interface of the node itself, the 2nd is that of the Bus"""
        if node.port_size == self.bus_format.port_size and node.granularity == self.bus_format.granularity:
            return None
        else:
            return node, self.bus_format
