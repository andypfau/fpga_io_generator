from ..structure.types import RegisterSet, RegType, FieldType, FieldFunction
from ...tools import check_names
from .gen_py import RegisterPyGeneratorHelper

import math, warnings
from dataclasses import dataclass
from abc import ABC, abstractmethod



class AbstractRegisterScripter(ABC):
    def define_basics(self, reg_size: int, addr_lo: int, addr_shift: "int|None"): ...
    def begin_register(self, name: str, description: str, comment: str, abs_addr: int, is_readable: bool, is_writable: bool, is_resettable: bool, is_strobed: bool, need_shadow_variable: bool): ...
    def begin_field(self, name: str, description: str, comment: str, f_offs: int, f_size: int, f_bitmask: int, f_wordmask: int, dtype: FieldType, default: int): ...
    def add_read_func(self): ...
    def add_read_shadow_func(self): ...
    def add_overwrite_func(self): ...
    def add_write_masked_func(self): ...
    def add_read_modify_write_func(self): ...
    def add_write_shadow_func(self): ...
    def add_strobe_func(self): ...
    def end_field(self): ...
    def end_register(self): ...



class RegisterSoftwareGenerator:


    def __init__(self, registers: RegisterSet, address_shift: int = 0):
        self.registers = registers
        self.address_shift = address_shift


    def _can_write_masked(self, fields: "list[Field]", field_index: int) -> bool:
        n_mask_bits = self.registers.port_size//8
        fields_per_maskbit = []
        for i in range(n_mask_bits):
            fields_per_maskbit.append([])
        for i_field,field in enumerate(fields):
            f_hi,f_lo = field.bits[0],field.bits[-1]
            for maskbit in range(n_mask_bits):
                mask_lo = maskbit*8
                mask_hi = mask_lo + 7
                if not ((f_lo<mask_lo and f_hi<mask_lo) or (f_lo>mask_hi and f_hi>mask_hi)):
                    if not i_field in fields_per_maskbit[maskbit]:
                        fields_per_maskbit[maskbit].append(i_field)
        for maskbit,fields_in_maskbit in enumerate(fields_per_maskbit):
            if field_index in fields_in_maskbit:
                if len(fields_in_maskbit)>1:
                    return False # another field is also affected by this mask-bit, cannot use mask
        return True
    

    def generate(self, scripter: AbstractRegisterScripter):

        check_names(self.registers)
        
        adr_lo = int(math.ceil(math.log2(self.registers.port_size//8)))

        scripter.define_basics(self.registers.port_size, adr_lo, abs(self.address_shift) if self.address_shift!=0 else None)
        
        for reg in self.registers.registers:

            abs_addr = reg.get_absolute_address()

            r_readable = reg.regtype in [RegType.Read, RegType.WriteRead]
            r_writable = reg.regtype in [RegType.Write, RegType.WriteRead]
            r_resettable = reg.regtype in [RegType.Write, RegType.WriteRead]        
            r_strobed = reg.regtype in [RegType.Strobe, RegType.Handshake]
            r_event = reg.regtype in [RegType.ReadEvent]

            need_shadow_variable = False
            for i_field,field in enumerate(reg.fields):
                if FieldFunction.ReadShadow in field.functions:
                    need_shadow_variable = True
                if FieldFunction.WriteShadow in field.functions:
                    need_shadow_variable = True
            if r_strobed:
                need_shadow_variable = False

            scripter.begin_register(reg.name, reg.description, reg.comment, abs_addr, r_readable, r_writable, r_resettable, r_strobed, need_shadow_variable)

            for i_field,field in enumerate(reg.fields):

                if len(field.bits)==1:
                    f_offs = field.bits[0]
                    f_size = 1
                    f_bitmask = 1 << f_offs
                else:
                    f_offs = field.bits[1]
                    f_size = field.bits[0] - field.bits[1] + 1
                    if f_size<1:
                        raise Exception(f'Invalid bits: {field.bits}')
                    f_bitmask = ((1 << f_size) - 1) << f_offs
                f_wordmask = 0
                for bit in range(f_offs, f_offs+f_size):
                    f_wordmask |= (1 << bit//8)
                
                scripter.begin_field(field.name, field.description, field.comment, f_offs, f_size, f_bitmask, f_wordmask, field.datatype, field.default)

                if FieldFunction.Read in field.functions:

                    if (not r_readable) and (not r_event):
                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do read (register {self.registers.name}.{reg.name} needs read access)')

                    scripter.add_read_func()
                
                if FieldFunction.ReadShadow in field.functions:

                    read_required = FieldFunction.Read in field.functions

                    if (read_required) and (not r_readable) and (not r_event):

                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do read (register {self.registers.name}.{reg.name} needs read access)')
                    
                    if read_required:
                        
                        scripter.add_read_shadow_func()

                
                if FieldFunction.Overwrite in field.functions:
                    
                    if not r_writable:
                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do write (register {self.registers.name}.{reg.name} needs write access)')
                    if len(reg.fields) > 1:
                        warnings.warn(f'Field {self.registers.name}.{reg.name}.{field.name} uses overwrite, but the register contains more than one field; writing will potentially cause side-effects', UserWarning)
                    
                    scripter.add_overwrite_func()

                
                if FieldFunction.WriteMasked in field.functions:
                    
                    if not r_writable:
                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do write (register {self.registers.name}.{reg.name} needs write access)')
                    if not self._can_write_masked(reg.fields, i_field):
                        warnings.warn(f'Mask of {reg.name}.{field.name} overlaps with other fields; writing will potentially cause side-effects', UserWarning)
                    
                    scripter.add_write_masked_func()
                    
                
                if FieldFunction.ReadModifyWrite in field.functions:
                    
                    if not r_writable:
                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do write (register {self.registers.name}.{reg.name} needs write access)')
                    if r_event:
                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do read-modify-write (register {self.registers.name}.{reg.name} is of event type)')
                    if not (r_readable and r_writable):
                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do read-modify-write (register {self.registers.name}.{reg.name} needs write+read access)')
                    
                    scripter.add_read_modify_write_func()
                
                if FieldFunction.WriteShadow in field.functions:
                    
                    if not r_writable:
                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do write (register {self.registers.name}.{reg.name} needs write access)')

                    scripter.add_write_shadow_func()
                
                if FieldFunction.Strobe in field.functions:
                    
                    if not r_strobed:
                        raise TypeError(f'Field {self.registers.name}.{reg.name}.{field.name} cannot do strobe (register {self.registers.name}.{reg.name} needs strobe access)')
                    
                    scripter.add_strobe_func()
       
                scripter.end_field()
        
            scripter.end_register()
