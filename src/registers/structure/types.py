from ...tools import clog2

import dataclasses
import enum
import math



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
    functions: FieldFunction
    
    default: int = dataclasses.field(default=0)
    
    comment: str = dataclasses.field(default=None)
    
    """ only used if register type is ReadEvent """
    trigger_on: FieldChangeType = dataclasses.field(default=0)



@dataclasses.dataclass
class Register:
    
    name: str
    
    description: str
    
    """ Relative addess of this register; set to ... for automatic numbering """
    address: "int|Ellipsis"
    
    """ HW access to this register """
    regtype: RegType
    
    fields: list[Field]
    
    """ Add a flag which is strobed when this register is written """
    write_event: WriteEventType = dataclasses.field(default=None)
    
    comment: str = dataclasses.field(default=None)



@dataclasses.dataclass
class RegisterSet:

    name: str
    """  Absolute base address """
    base_address: int
    """ Wishbone port size, in bits (note that granularity will alyways be 8 bit)"""
    port_size: int
    registers: list[Register]


    @staticmethod
    def granularity() -> int:
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
