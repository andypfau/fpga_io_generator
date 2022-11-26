from ..codegen.gen_sv import BusSvGenerator
from ..codegen.gen_graph import BusGraphGenerator
from ...registers import RegisterSet, RegisterPyGenerator, RegisterCGenerator, RegisterSvGenerator

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


@dataclasses.dataclass
class WbSlave:
    name: str
    ''' Absolute base address '''
    base_address: int
    ''' Port size, in bits '''
    port_size: int
    ''' Bus granularity, in bits '''
    granularity: int
    ''' Address size, in bits (the highest address bit index will be this minus 1; the lowest index depends on bus width and granularity)'''
    address_size: int

    ''' used internally for code generation purposes '''
    _register_set: 'RegisterSet' = None

    @staticmethod    
    def from_register_set(register_set: 'RegisterSet') -> 'WbSlave':
        ''' Create a WbSlave from a RegisterSet '''
        n_regs = len(register_set.registers)
        min_adr_bits = max(1, int(math.ceil(math.log2(n_regs))))
        slave = WbSlave(register_set.name, register_set.base_address, register_set.port_size, RegisterSet.granularity(), min_adr_bits)
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

    def get_sv_gen(self) -> BusSvGenerator:
        return BusSvGenerator(self, self.name)

    def get_graph_gen(self) -> BusGraphGenerator:
        return BusGraphGenerator(self, self.name+'.gv')

    def get_reg_sv_gens(self, format: RegisterSvGenerator.Format = None) -> RegisterSvGenerator:
        return [s._register_set.get_sv_gen(format) for s in self.slaves if s._register_set is not None]

    def get_reg_py_gens(self, reference_master_port_size: int, format: RegisterPyGenerator.Format = None) -> RegisterPyGenerator:
        bus_port_size = max([c.port_size for c in self.masters+self.slaves])
        address_shift = int(round(math.log2(reference_master_port_size / bus_port_size))) # the required Wishbone adapter will swallow this number of bits
        result = []
        for slave in self.slaves:
            if slave._register_set is not None:
                result.append(slave._register_set.get_py_gen(address_shift, format))
        return result

    def get_reg_c_gens(self, reference_master_port_size: int, format: RegisterCGenerator.Format = None) -> RegisterCGenerator:
        bus_port_size = max([c.port_size for c in self.masters+self.slaves])
        address_shift = int(round(math.log2(reference_master_port_size / bus_port_size))) # the required Wishbone adapter will swallow this number of bits
        result = []
        for slave in self.slaves:
            if slave._register_set is not None:
                result.append(slave._register_set.get_c_gen(address_shift, format))
        return result
