from ..structure.types import RegisterSet, RegType, FieldType, FieldFunction
from ...tools import check_names, make_sourcecode_name, NamingConvention

from dataclasses import dataclass, field
import re
import typing



class RegisterPyGenerator:

    @dataclass
    class Format:
        
        """The function that is called to read from the bus"""
        read_func: str = 'read_register'
        
        """The function that is called to write to the bus"""
        write_func: str = 'write_register'
        
        """The function that is called to write to the bus with a word-mask"""
        write_masked_func: str = 'write_register_masked'
        
        """Set to True if you want to hand an object into the constructor, so that any bus access calls are done on that object"""
        accessor_obj: bool = False
        
        """Lines that are added to the top of the code to import Python modules"""
        import_clauses: list[str] = field(default_factory=lambda: [])


    def __init__(self, registers: RegisterSet, address_shift: int = 0, format: Format = None):
        """
        registers:     the register set to create Python code from
        address_shift: all bus address will be shifted by this amount (can be positive or negative)
        format:        a RegisterPyGenerator.Format object to control code generation
        """
        
        self.registers = registers
        self.address_shift = address_shift
        self.format = format if format is not None else RegisterPyGenerator.Format()

        check_names(self.registers)

        gen = RegisterPyGeneratorHelper(registers, address_shift, format)
        self.code = gen.final_code
    

    def get_code(self) -> str:
        """Returns the generated Python code as a string"""

        return self.code
    

    def save(self, filename: str):
        with open(filename, 'w') as fp:
            fp.write(self.get_code())



def class_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.PascalCase)

def fn_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.snake_case)

def var_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.snake_case)

def const_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.snake_case)



@dataclass
class ShadowVar:
    fn_name: str
    shadow_var: str
    dirty_var: str
    is_readable: bool
    shadow_read: bool
    shadow_write: bool



class RegisterPyGeneratorHelper:

    def __init__(self, registers: RegisterSet, address_shift: int = 0, format: "RegisterPyGenerator.Format" = None):

        self.registers = registers
        self.address_shift = address_shift
        self.format = format if format is not None else RegisterPyGenerator.Format()

        self.code_main = []
        self.code_defs = []
        self.code_public_funcs = []
        self.code_private_funcs = []
        self.code_reset = []
        self.shadow_vars: typing.Optional[list[ShadowVar]] = []

        self.prepare()
        self.generate()
        self.finish()        

    
    def prepare(self):

        # boilerplate code at the top

        for imp in self.format.import_clauses:
            self.code_main.append(imp)
        if len(self.format.import_clauses) > 0:
            self.code_main.append('')
    
        self.code_main.append('# automatically generated code')
        self.code_main.append('')
        self.code_main.append(f'class {class_name(self.registers.name)}:')
        if self.format.accessor_obj:
            
            self.code_main.append(f'\tdef __init__(self, hwaccess):')
            self.code_main.append(f'\t\tself.hw = hwaccess')
            
            self.read_func = f'self.hw.{self.format.read_func}'
            self.write_func = f'self.hw.{self.format.write_func}'
            self.write_masked_func = f'self.hw.{self.format.write_masked_func}'

        else:
            self.code_main.append(f'\tdef __init__(self):')
            
            self.read_func = self.format.read_func
            self.write_func =self.format.write_func
            self.write_masked_func = self.format.write_masked_func

        self.code_main.append('')


    def generate(self):
        from .gen_sw import RegisterSoftwareGenerator
        RegisterSoftwareGenerator(self.registers, self.address_shift).generate(self)
    

    def define_basics(self, reg_size: int, addr_lo: int, addr_shift: "int|None"):
        self.addr_dead_const = f'self._addr_deadbits'
        self.addr_shift_const = f'self._addr_shift'
        self.code_defs.append(f'\t\t{self.addr_dead_const} = {addr_lo} # address must be shifted this much to accomodate for the missing LSBs of the address vector')
        if addr_shift is not None:
            self.code_defs.append(f'\t\t{self.addr_shift_const} = {abs(addr_shift)} # shift to compensate e.g. for bus adapters')
        self.code_defs.append('')
    

    def begin_register(self, name: str, description: str, comment: str, abs_addr: int, is_readable: bool, is_writable: bool, is_resettable: bool, is_strobed: bool, need_shadow_read: bool, need_shadow_write: bool):
        
        self.r_readable = is_readable
        self.r_writable = is_writable
        self.r_resettable = is_resettable
        self.r_strobed = is_strobed
        self.r_shadow_read = need_shadow_read
        self.r_shadow_write = need_shadow_write

        self.r_shadow_var = f'self._register_{var_name(name)}_shadow'
        self.r_dirty_var = f'self._register_{var_name(name)}_dirty'
        if need_shadow_read or need_shadow_write:
            self.shadow_vars.append(ShadowVar(fn_name(name), self.r_shadow_var, self.r_dirty_var, is_readable, need_shadow_read, need_shadow_write))
        
        self.r_addr_const = f'self._register_{const_name(name)}_addr'

        self.code_defs.append(f'\t\t# {name}: {description}')
        if comment is not None:
            for line in comment.splitlines():
                self.code_defs.append(f'\t\t# {line}')
        if self.address_shift == 0:
            self.code_defs.append(f'\t\t{self.r_addr_const} = (0x{abs_addr:X} >> {self.addr_dead_const})')
        elif self.address_shift < 0:
            self.code_defs.append(f'\t\t{self.r_addr_const} = (0x{abs_addr:X} >> {self.addr_dead_const}) << {self.addr_shift_const}')
        else:
            self.code_defs.append(f'\t\t{self.r_addr_const} = (0x{abs_addr:X} >> {self.addr_dead_const}) >> {self.addr_shift_const}')
        if need_shadow_read or need_shadow_write:
            self.code_defs.append(f'\t\t{self.r_shadow_var} = 0')
            self.code_defs.append(f'\t\t{self.r_dirty_var} = False')
        self.code_defs.append('')

        self.f_default_consts = []
        self.reg_name = name


    def begin_field(self, name: str, description: str, comment: str, f_offs: int, f_size: int, f_bitmask: int, f_wordmask: int, dtype: FieldType, default: int):

        self.field_name = name
        self.f_type = dtype
        self.f_is_boolean = dtype is FieldType.Boolean

        self.f_offs_const = f'self._register_{const_name(self.reg_name)}_field_{const_name(name)}_offset'
        self.f_bitmask_const = f'self._register_{const_name(self.reg_name)}_field_{const_name(name)}_bitmask'
        if not self.r_strobed:
            self.f_wordmask_const = f'self._register_{const_name(self.reg_name)}_field_{const_name(name)}_wordmask'
        if self.r_resettable:
            self.f_def_const = f'self._register_{const_name(self.reg_name)}_field_{const_name(name)}_default'

        if self.r_resettable:
            self.f_default_consts.append(self.f_def_const)
        
        self.code_defs.append(f'\t\t# {self.reg_name}.{name}: {description}')
        if comment is not None:
            for line in comment.splitlines():
                self.code_defs.append(f'\t\t# {line}')
        self.code_defs.append(f'\t\t{self.f_offs_const} = {f_offs}')
        self.code_defs.append(f'\t\t{self.f_bitmask_const} = 0x{f_bitmask:X}')
        if not self.r_strobed:
            self.code_defs.append(f'\t\t{self.f_wordmask_const} = 0x{f_wordmask:X}')
        if self.r_resettable:
            if default < 0:
                self.code_defs.append(f'\t\t{self.f_def_const} = 0x{((default&((1<<f_size)-1))<<f_offs):X} # {default}')
            else:
                self.code_defs.append(f'\t\t{self.f_def_const} = 0x{(default<<f_offs):X}')
        self.code_defs.append('')

        self._field_comment = [f'\t\t""" {description} (<{self.reg_name}>.<{name}>)']
        if comment:
            for line in comment.splitlines():
                self._field_comment.append(f'\t\t {line}')
        self._field_comment[-1] += ' """'
    

    def add_read_func(self):
                    
        sig = f'\tdef get_{fn_name(self.reg_name)}_{fn_name(self.field_name)}(self) -> int:'

        self.code_public_funcs.append(sig)
        self.code_public_funcs.extend(self._field_comment)
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t\treturn ((self._read_{const_name(self.reg_name)}() & {self.f_bitmask_const}) != 0)')
        else:
            self.code_public_funcs.append(f'\t\treturn ((self._read_{const_name(self.reg_name)}() & {self.f_bitmask_const}) >> {self.f_offs_const})')
        self.code_public_funcs.append('')
    

    def add_read_shadow_func(self):
                    
        sig = f'\tdef get_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_shadow(self, load_shadow:bool=False) -> int:'
        
        self.code_public_funcs.append(sig)
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(f'\t\tif load_shadow:')
        self.code_public_funcs.append(f'\t\t\tself._read_{fn_name(self.reg_name)}()')
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t\treturn (({self.r_shadow_var} & {self.f_bitmask_const}) != 0)')
        else:
            self.code_public_funcs.append(f'\t\treturn (({self.r_shadow_var} & {self.f_bitmask_const}) >> {self.f_offs_const})')
        self.code_public_funcs.append('')
    

    def add_overwrite_func(self):
                    
        sig = f'\tdef set_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_overwrite(self, value:int):'
                            
        self.code_public_funcs.append(sig)
        self.code_public_funcs.extend(self._field_comment)
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t\tself._write_{fn_name(self.reg_name)}({self.f_bitmask_const} if value else 0)')
        else:
            self.code_public_funcs.append(f'\t\tself._write_{fn_name(self.reg_name)}((value << {self.f_offs_const}) & {self.f_bitmask_const})')
        self.code_public_funcs.append('')
    

    def add_write_masked_func(self):

        sig = f'\tdef set_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_masked(self, value:int):'
                            
        self.code_public_funcs.append(sig)
        self.code_public_funcs.extend(self._field_comment)
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t\tself._write_{fn_name(self.reg_name)}_masked({self.f_bitmask_const} if value else 0, {self.f_wordmask_const})')
        else:
            self.code_public_funcs.append(f'\t\tself._write_{fn_name(self.reg_name)}_masked((value << {self.f_offs_const}) & {self.f_bitmask_const}, {self.f_wordmask_const})')
        self.code_public_funcs.append('')
    

    def add_read_modify_write_func(self):
                    
        sig = f'\tdef set_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_rmw(self, value:int, lazy:bool=False):'
                            
        self.code_public_funcs.append(sig)
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(f'\t\tregOld = self._read_{fn_name(self.reg_name)}(hold_cyc=True)')
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t\tregNew = (regOld | {self.f_bitmask_const}) if value else (regOld & (~{self.f_bitmask_const}))')
        else:
            self.code_public_funcs.append(f'\t\tregNew = (regOld & (~{self.f_bitmask_const})) | ((value << {self.f_offs_const}) & {self.f_bitmask_const})')
        self.code_public_funcs.append(f'\t\tif (not lazy) or (regOld != regNew):')
        self.code_public_funcs.append(f'\t\t\tself._write_{fn_name(self.reg_name)}(regNew)')
        self.code_public_funcs.append('')
    

    def add_write_shadow_func(self):
                                                
        sig = f'\tdef set_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_shadow(self, value:int, flush:bool=False):'

        self.code_public_funcs.append(sig)
        self.code_public_funcs.extend(self._field_comment)
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t\t{self.r_shadow_var} |= ({self.f_bitmask_const} if value else 0)')
        else:
            self.code_public_funcs.append(f'\t\t{self.r_shadow_var} = ({self.r_shadow_var} & ~{self.f_bitmask_const}) | ((value << {self.f_offs_const}) & {self.f_bitmask_const})')
        self.code_public_funcs.append(f'\t\t{self.r_dirty_var} = True')
        self.code_public_funcs.append(f'\t\tif flush:')
        self.code_public_funcs.append(f'\t\t\tself._write_{fn_name(self.reg_name)}({self.r_shadow_var})')
        self.code_public_funcs.append('')


    def add_strobe_func(self):
    
        sig = f'\tdef strobe_{fn_name(self.reg_name)}_{fn_name(self.field_name)}(self):'
        
        self.code_public_funcs.append(sig)
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(f'\t\tself._write_{fn_name(self.reg_name)}({self.f_bitmask_const})')
        self.code_public_funcs.append('')


    def end_field(self):
        ...

    def end_register(self):

        if (self.r_resettable) and (len(self.f_default_consts)>0):
            self.code_reset.append(f'\t\tself._write_{fn_name(self.reg_name)}({" | ".join(self.f_default_consts)})')

        if self.r_writable:
            self.code_private_funcs.append(f'\t# Internal function to write to field <{self.field_name}>')
            self.code_private_funcs.append(f'\tdef _write_{fn_name(self.reg_name)}(self, value: int, hold_cyc: bool = False):')
            self.code_private_funcs.append(f'\t\t{self.write_func}({self.r_addr_const}, value, hold_cyc)')
            if self.r_shadow_write or self.r_shadow_read:
                self.code_private_funcs.append(f'\t\t{self.r_shadow_var} = value')
                self.code_private_funcs.append(f'\t\t{self.r_dirty_var} = False')
            self.code_private_funcs.append('')

        if self.r_writable and not self.r_strobed:
            self.code_private_funcs.append(f'\t# Internal function to do a masked write to field <{self.field_name}>')
            self.code_private_funcs.append(f'\tdef _write_{fn_name(self.reg_name)}_masked(self, value: int, mask: int):')
            self.code_private_funcs.append(f'\t\t{self.write_masked_func}({self.r_addr_const}, value, mask)')
            if self.r_shadow_write or self.r_shadow_read:
                self.code_private_funcs.append(f'\t\tfor b in range({self.registers.port_size//8}):')
                self.code_private_funcs.append(f'\t\t\tif mask&(1<<b):')
                self.code_private_funcs.append(f'\t\t\t\t{self.r_shadow_var} = ({self.r_shadow_var} & ~(0xFF<<(8*b))) | (value & (0xFF<<(8*b)))')
            self.code_private_funcs.append('')

        if self.r_readable:
            self.code_private_funcs.append(f'\t# Internal function to read from field <{self.field_name}>')
            self.code_private_funcs.append(f'\tdef _read_{fn_name(self.reg_name)}(self, hold_cyc: bool = False) -> int:')
            self.code_private_funcs.append(f'\t\tvalue = {self.read_func}({self.r_addr_const}, hold_cyc)')
            if self.r_shadow_write or self.r_shadow_read:
                self.code_private_funcs.append(f'\t\t{self.r_shadow_var} = value')
                self.code_private_funcs.append(f'\t\t{self.r_dirty_var} = False')
            self.code_private_funcs.append(f'\t\treturn value')
            self.code_private_funcs.append('')
                

    def finish(self):
        
        if len(self.code_reset)>0:
            self.code_public_funcs.append(f'\tdef reset(self):')
            self.code_public_funcs.append(f'\t\t""" set all self.registers to their default values """')
            self.code_public_funcs.extend(self.code_reset)
            self.code_public_funcs.append('')
        
        any_shadow_write = any([s.shadow_write for s in self.shadow_vars])
        if any_shadow_write:

            self.code_public_funcs.append(f'\tdef flush_shadow(self, force:bool=False):')
            self.code_public_funcs.append(f'\t\t"""')
            self.code_public_funcs.append(f'\t\twrite all dirty shadow register contents to hardware')
            self.code_public_funcs.append(f'\t\tset force=True to force flushing, even if nothing changed locally')
            self.code_public_funcs.append(f'\t\t"""')
            for s in self.shadow_vars:
                if not s.shadow_write: continue
                self.code_public_funcs.append(f'\t\tif force or {s.dirty_var}:')
                self.code_public_funcs.append(f'\t\t\tself._write_{s.fn_name}({s.shadow_var})')
                self.code_public_funcs.append(f'\t\t\t{s.dirty_var} = False')
            self.code_public_funcs.append('')
            
        any_shadow_read = any([s.shadow_read for s in self.shadow_vars])
        if any_shadow_read:
            self.code_public_funcs.append(f'\tdef load_shadow(self):')
            self.code_public_funcs.append(f'\t\t""" read all shadow register contents from hardware (only readable self.registers)"""')
            for s in self.shadow_vars:
                if not s.shadow_read: continue
                self.code_public_funcs.append(f'\t\tself._read_{s.fn_name}()')
            self.code_public_funcs.append('')
        
        self.code_main.extend(self.code_defs)
        self.code_main.extend(self.code_public_funcs)
        self.code_main.extend(['\t##################################################', ''])
        self.code_main.extend(self.code_private_funcs)

        self.final_code = '\n'.join(self.code_main)
