from ...tools import clog2

import dataclasses
import enum
import math
import typing



class FieldType(enum.Enum):
    Unsigned8Bit = enum.auto()
    Unsigned16Bit = enum.auto()
    Unsigned32Bit = enum.auto()
    Unsigned64Bit = enum.auto()
    Signed8Bit = enum.auto()
    Signed16Bit = enum.auto()
    Signed32Bit = enum.auto()
    Signed64Bit = enum.auto()
    Boolean = enum.auto()
    Strobe = enum.auto()



class FieldChangeType(enum.Flag):
    Rising = 1
    Falling = 2
    High = 4
    Low = 8
    AnyChange = 3



class FieldFunction(enum.Flag):
    """ allow to read field from register (triggers a HW access) """
    Read = enum.auto()
    """
    allow to read field from local shadow register
    shadow register must be explicitly loaded with a function call
    """
    ReadShadow = enum.auto()
    """
    allow to write the field by overwriting the whole register
    BE CAREFUL if a register contains more than one field!
    """
    Overwrite = enum.auto()
    """ allow to write the field by using a mask, to ensure no other fields in the register are touched """
    WriteMasked = enum.auto()
    """
    allow to write the field by writing to a local shadow register first
    shadow register must be explicitly flushed to HW with a function call
    """
    WriteShadow = enum.auto()
    """ allow to write the field by using read-modify-write, to ensure no other fields in the register are touched """
    ReadModifyWrite = enum.auto()
    """ allow to strobe this bit """
    Strobe = enum.auto()



class RegType(enum.Enum):
    """ register is write-only """
    Write = enum.auto()
    """ register is read-only """
    Read = enum.auto()
    """ register is write-only, but can be read-back from hardware """
    WriteRead = enum.auto()
    """ register contains only strobed bits (strobes are asserted for a single clock cycle) """
    Strobe = enum.auto()
    """ register contains only strobed bits (strobes are asserted until an acknowledge is received) """
    Handshake = enum.auto()
    """ register is read-only, and latches events, e.g. rising-edge; register is cleared on read """
    ReadEvent = enum.auto()



class WriteEventType(enum.Enum):
    
    """ When the register is written, a strobe bit is set for a single clock cycle """
    StrobeOnWrite = enum.auto()
    
    """ When the register is written, when cyc goes low, a strobe bit is set for a single clock cycle """
    StrobeAfterWriteOnCycleEnd = enum.auto()



@dataclasses.dataclass
class Field:
    
    name: str
    
    description: str
    
    bits: list[int]
    
    datatype: FieldType
    
    """ SW functions to access this field """
    functions: "FieldFunction"
    
    default: int = dataclasses.field(default=0)
    
    comment: str = dataclasses.field(default=None)
    
    """ only used if register type is ReadEvent """
    trigger_on: FieldChangeType = dataclasses.field(default=0)



class Register:


    def __init__(self, name: str, description: str, address: "int|Ellipsis", regtype: RegType, fields: list[Field],
        write_event: WriteEventType = None, comment: str = None):
        """
        name:        
        description: 
        address:     
        regtype:     
        fields:      
        write_event: 
        comment:     
        """

        self.name, self.description, self._requested_address, self.regtype, self.fields, self.write_event, self.comment = \
            name, description, address, regtype, fields, write_event, comment
        self._rel_adr: typing.Optional[int] = None
        self._abs_adr: typing.Optional[int] = None
    

    def get_relative_address(self) -> int:
        if self._rel_adr is None:
            raise RuntimeError('This register was not properly initialized yet. Put it into a RegisterSet first.')
        return self._rel_adr
    

    def get_absolute_address(self) -> int:
        if self._abs_adr is None:
            raise RuntimeError('This register was not properly initialized yet. Put it into a RegisterSet first.')
        return self._abs_adr



class RegisterSet:

    def __init__(self, name: str, base_address: "int|Ellipsis", port_size: int, registers: "list[Register]"):
        """
        name:         Name of this register set
        base_address: The address of the 1st register inside of the bus
        port_size:    Port size, in bits (note that granularity will alyways be 8 bit)
        registers:    List of registers within this register set
        """

        self.name, self._requested_base_address, self.port_size, self.registers = name, base_address, port_size, registers
        
        # this
        self._base_address = Ellipsis
        
        self.check()
        self._update()
        
    
    def _update(self):
        from .regset_solver import RegisterSetSolver
        RegisterSetSolver(self)
    

    def get_base_address(self) -> int:
        if self._base_address is Ellipsis:
            if self._requested_base_address is Ellipsis:
                return 0
            else:
                return self._requested_base_address
        else:
            return self._base_address
    

    def check(self):
        
        if len(self.registers)<1:
            raise ValueError(f'Need at least one register')
        
        if len(self.registers) != len(set([s.name for s in self.registers])):
            raise RuntimeError(f'Register names must be unique')


    def granularity(self) -> int:
        return 8

    
    def address_bit_range(self) -> "tuple[int,int]":
        """
        Returns a tuple that represents the lowest and the highest address bit index
        
        Example:
        - there are 3 registers -> 2 bits needed
        - width is 32 bit (granularity is always 8) -> lowest address bit is by definition 2
        Then the adr_in port has the range [3:2], and this method returns (2,3)
        """
        
        n_regs = len(self.registers)
        adr_bits = max(1, int(math.ceil(math.log2(n_regs))))

        lowest_bit = clog2(self.port_size // 8)
        highest_bit = lowest_bit + adr_bits - 1

        return (lowest_bit, highest_bit)
