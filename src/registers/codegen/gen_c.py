from ..structure.types import RegisterSet, RegType, FieldType, FieldFunction
from ...tools import check_names, make_sourcecode_name, NamingConvention

from dataclasses import dataclass, field
import math
import re
import typing


def field_type(t):
    if t is FieldType.Unsigned8Bit:
        return 'unsigned char'
    elif t is FieldType.Unsigned16Bit:
        return 'unsigned short'
    elif t is FieldType.Unsigned32Bit:
        return 'unsigned int'
    elif t is FieldType.Unsigned64Bit:
        return 'unsigned long long'
    elif t is FieldType.Signed8Bit:
        return 'signed char'
    elif t is FieldType.Signed16Bit:
        return 'signed short'
    elif t is FieldType.Signed32Bit:
        return 'signed int'
    elif t is FieldType.Signed64Bit:
        return 'signed long long'
    elif t is FieldType.Boolean:
        return 'int'
    elif t is FieldType.Strobe:
        return None
    else:
        raise Exception(f'Invalid type: {t}')


def reg_type(n_bytes):
    if n_bytes==8:
        return field_type(FieldType.Unsigned8Bit)
    elif n_bytes==16:
        return field_type(FieldType.Unsigned16Bit)
    elif n_bytes==32:
        return field_type(FieldType.Unsigned32Bit)
    elif n_bytes==64:
        return field_type(FieldType.Unsigned64Bit)
    else:
        raise Exception(f'Invalid register size: {n_bytes} bytes')


def fn_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.snake_case)

def var_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.snake_case)

def const_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.CONSTANT_CASE)


@dataclass
class ShadowVar:
    fn_name: str
    shadow_var: str
    dirty_var: str
    is_readable: bool
    shadow_read: bool
    shadow_write: bool


class RegisterCGenerator:

    @dataclass
    class Format:
        
        """The function that is called to read from the bus"""
        read_func: str = 'read_register'
        
        """The function that is called to write to the bus"""
        write_func: str = 'write_register'
        
        """The function that is called to write to the bus with a word-mask"""
        write_masked_func: str = 'write_register_masked'
        
        """Headers (including quotes or brackets) that are included at the top of the code"""
        includes: list[str] = field(default_factory=lambda: ['"adapt_me_please.h"'])

    def __init__(self, registers: RegisterSet, filename: str = 'Registers', format: Format = None):
        """
        registers:     the register set to create C-code from
        filename:      the intended name of the file (so that the "#include ..." is correct)
        format:        a RegisterCGenerator.Format object to control code generation
        """
        
        self.registers = registers
        self.filename = filename
        self.format = format if format is not None else RegisterCGenerator.Format()

        gen = RegisterCGeneratorHelper(registers, filename, format)
        self.code_header = gen.code_header
        self.code_source = gen.code_source
    

    def get_code(self) -> str:
        """Returns the generated C-code as a string"""

        return self.code_source
    

    def get_header(self) -> str:
        """Returns the generated C-header as a string"""

        return self.code_header
    

    def save(self, filename_header: str = None, filename_code: str = None):
        if filename_header is not None:
            with open(filename_header, 'w') as fp:
                fp.write(self.get_header())
        if filename_code is not None:
            with open(filename_code, 'w') as fp:
                fp.write(self.get_code())



class RegisterCGeneratorHelper:

    def __init__(self, registers: RegisterSet, filename: str = 'Registers', format: "RegisterCGenerator.Format" = None):

        self.registers = registers
        self.filename = filename
        self.format = format if format is not None else RegisterCGenerator.Format()

        self.code_header = []
        self.code_main = []
        self.code_defs = []
        self.code_public_funcs = []
        self.code_private_funcs = []
        self.code_reset = []
        self.shadow_vars: typing.Optional[list[ShadowVar]] = []

        check_names(self.registers)

        self.prepare()
        self.generate()
        self.finish()        

    
    def prepare(self):

        # boilerplate code at the top
    
        self.code_header.append('// automatically generated code')
        self.code_header.append('')
        self.code_header.append(f'#pragma once')
        self.code_header.append('')

        self.code_main.append('// automatically generated code')
        self.code_main.append('')
        self.code_main.append(f'#include "{self.filename}.h"')
        for include in self.format.includes:
            self.code_main.append(f'#include {include}')
        self.code_main.append('')


    def generate(self):
        from .gen_sw import RegisterSoftwareGenerator
        RegisterSoftwareGenerator(self.registers).generate(self)
    

    def define_basics(self, reg_size: int):
        
        self.reg_size = reg_size
        self.reg_type = reg_type(reg_size)
    

    def begin_register(self, name: str, description: str, comment: str, abs_addr: int, is_readable: bool, is_writable: bool, is_resettable: bool, is_strobed: bool, need_shadow_read: bool, need_shadow_write: bool):
        
        self.r_readable = is_readable
        self.r_writable = is_writable
        self.r_resettable = is_resettable
        self.r_strobed = is_strobed
        self.r_shadow_read = need_shadow_read
        self.r_shadow_write = need_shadow_write

        self.r_shadow_var = f'register_{var_name(name)}_shadow'
        self.r_dirty_var = f'register_{var_name(name)}_dirty'
        if need_shadow_read or need_shadow_write:
            self.shadow_vars.append(ShadowVar(fn_name(name), self.r_shadow_var, self.r_dirty_var, is_readable, need_shadow_read, need_shadow_write))
        
        self.r_addr_const = f'REGISTER_{const_name(name)}_ADDRESS'

        self.code_defs.append(f'// {name}: {description}')
        if comment is not None:
            for line in comment.splitlines():
                self.code_defs.append(f'// {line}')
        self.code_defs.append(f'#define {self.r_addr_const} (0x{abs_addr:X})')
        if need_shadow_read or need_shadow_write:
            self.code_defs.append(f'int {self.r_shadow_var} = 0;')
            self.code_defs.append(f'{self.reg_type} {self.r_dirty_var} = 0;')
        self.code_defs.append('')

        self.f_default_consts = []
        self.reg_name = name


    def begin_field(self, name: str, description: str, comment: str, f_offs: int, f_size: int, f_bitmask: int, f_wordmask: int, dtype: FieldType, default: int):

        self.field_name = name
        self.f_type = field_type(dtype)
        self.f_is_boolean = dtype is FieldType.Boolean

        self.f_offs_const = f'REGISTER_{const_name(self.reg_name)}_FIELD_{const_name(name)}_OFFSET'
        self.f_bitmask_const = f'REGISTER_{const_name(self.reg_name)}_FIELD_{const_name(name)}_BITMASK'
        if not self.r_strobed:
            self.f_wordmask_const = f'REGISTER_{const_name(self.reg_name)}_FIELD_{const_name(name)}_WORDMASk'
        if self.r_resettable:
            self.f_def_const = f'REGISTER_{const_name(self.reg_name)}_FIELD_{const_name(name)}_DEFAULT'

        if self.r_resettable:
            self.f_default_consts.append(self.f_def_const)
        
        self.code_defs.append(f'// {self.reg_name}.{name}: {description}')
        if comment is not None:
            for line in comment.splitlines():
                self.code_defs.append(f'// {line}')
        self.code_defs.append(f'#define {self.f_offs_const} ({f_offs})')
        self.code_defs.append(f'#define {self.f_bitmask_const} (0x{f_bitmask:X})')
        if not self.r_strobed:
            self.code_defs.append(f'#define {self.f_wordmask_const} (0x{f_wordmask:X})')
        if self.r_resettable:
            if default < 0:
                self.code_defs.append(f'#define {self.f_def_const} (0x{((default&((1<<f_size)-1))<<f_offs):X})')
            else:
                self.code_defs.append(f'#define {self.f_def_const} (0x{(default<<f_offs):X})')
        self.code_defs.append('')

        self._field_comment = [f'/* {description} (<{self.reg_name}>.<{name}>)']
        if comment:
            for line in comment.splitlines():
                self._field_comment.append(f'   {line}')
        self._field_comment[-1] += ' */'
    

    def add_read_func(self):
                    
        sig = f'{self.f_type} get_{fn_name(self.reg_name)}_{fn_name(self.field_name)}()'

        self.code_header.extend(self._field_comment)
        self.code_header.append(sig + ';')
        self.code_header.append('')
        
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(sig)
        self.code_public_funcs.append('{')
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\treturn ((_read_{fn_name(self.reg_name)}() & {self.f_bitmask_const}) != 0);')
        else:
            self.code_public_funcs.append(f'\treturn ((_read_{fn_name(self.reg_name)}() & {self.f_bitmask_const}) >> {self.f_offs_const});')
        self.code_public_funcs.append('}')
        self.code_public_funcs.append('')
    

    def add_read_shadow_func(self):
                    
        sig = f'{self.f_type} get_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_shadow(int load_shadow)'
        
        self.code_header.extend(self._field_comment)
        self.code_header.append(sig + ';')
        self.code_header.append('')
        
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(sig)
        self.code_public_funcs.append('{')
        self.code_public_funcs.append(f'\tif (load_shadow)')
        self.code_public_funcs.append(f'\t\t_read_{fn_name(self.reg_name)}();')
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\treturn (({self.r_shadow_var} & {self.f_bitmask_const}) != 0);')
        else:
            self.code_public_funcs.append(f'\treturn (({self.r_shadow_var} & {self.f_bitmask_const}) >> {self.f_offs_const});')
        self.code_public_funcs.append('}')
        self.code_public_funcs.append('')
    

    def add_overwrite_func(self):
                    
        sig = f'void set_{fn_name(self.reg_name)}_{fn_name(self.field_name)}(_overwrite({self.f_type} value)'
                            
        self.code_header.extend(self._field_comment)
        self.code_header.append(sig + ';')
        self.code_header.append('')
        
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(sig)
        self.code_public_funcs.append('{')
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t_write_{fn_name(self.reg_name)}(value = {self.f_bitmask_const} : 0);')
        else:
            self.code_public_funcs.append(f'\t_write_{fn_name(self.reg_name)}((value << {self.f_offs_const}) & {self.f_bitmask_const});')
        self.code_public_funcs.append('}')
        self.code_public_funcs.append('')
    

    def add_write_masked_func(self):

        sig = f'void set_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_masked({self.f_type} value)'
                            
        self.code_header.extend(self._field_comment)
        self.code_header.append(sig + ';')
        self.code_header.append('')
        
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(sig)
        self.code_public_funcs.append('{')
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t_write_{fn_name(self.reg_name)}_masked(value ? {self.f_bitmask_const} : 0, {self.f_wordmask_const});')
        else:
            self.code_public_funcs.append(f'\t_write_{fn_name(self.reg_name)}_masked((value << {self.f_offs_const}) & {self.f_bitmask_const}, {self.f_wordmask_const});')
        self.code_public_funcs.append('}')
        self.code_public_funcs.append('')
    

    def add_read_modify_write_func(self):
                    
        sig = f'void set_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_rmw({self.f_type} value, int lazy)'
                            
        self.code_header.extend(self._field_comment)
        self.code_header.append(sig + ';')
        self.code_header.append('')
        
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(sig)
        self.code_public_funcs.append('{')
        self.code_public_funcs.append(f'\t{self.f_type} regOld = self._read_{fn_name(self.reg_name)}(1);')
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t{self.f_type} regNew = (regOld | (value ? {self.f_bitmask_const}) : (regOld & (~{self.f_bitmask_const})));')
        else:
            self.code_public_funcs.append(f'\t{self.f_type} regNew = (regOld & (~{self.f_bitmask_const})) | ((value << {self.f_offs_const}) & {self.f_bitmask_const});')
        self.code_public_funcs.append(f'\tif ((!lazy) || (regOld != regNew))')
        self.code_public_funcs.append(f'\t\t_write_{fn_name(self.reg_name)}(regNew);')
        self.code_public_funcs.append('}')
        self.code_public_funcs.append('')
    

    def add_write_shadow_func(self):
                                                
        sig = f'void set_{fn_name(self.reg_name)}_{fn_name(self.field_name)}_shadow({self.f_type} value, int flush)'

        self.code_header.extend(self._field_comment)
        self.code_header.append(sig + ';')
        self.code_header.append('')
        
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(sig)
        self.code_public_funcs.append('{')
        if self.f_is_boolean:
            self.code_public_funcs.append(f'\t{self.r_shadow_var} |= (value ? {self.f_bitmask_const} : 0);')
        else:
            self.code_public_funcs.append(f'\t{self.r_shadow_var} = ({self.r_shadow_var} & ~{self.f_bitmask_const}) | ((value << {self.f_offs_const}) & {self.f_bitmask_const});')
        self.code_public_funcs.append(f'\t{self.r_dirty_var} = 1;')
        self.code_public_funcs.append(f'\tif (flush)')
        self.code_public_funcs.append(f'\t\t_write_{fn_name(self.reg_name)}({self.r_shadow_var});')
        self.code_public_funcs.append('}')
        self.code_public_funcs.append('')


    def add_strobe_func(self):
    
        sig = f'void strobe_{fn_name(self.reg_name)}_{fn_name(self.field_name)}((void)'
        
        self.code_header.extend(self._field_comment)
        self.code_header.append(sig + ';')
        self.code_header.append('')
        
        self.code_public_funcs.extend(self._field_comment)
        self.code_public_funcs.append(sig)
        self.code_public_funcs.append('{')
        self.code_public_funcs.append(f'\t_write_{fn_name(self.reg_name)}({self.f_bitmask_const});')
        self.code_public_funcs.append('}')
        self.code_public_funcs.append('')


    def end_field(self):
        ...

    def end_register(self):

        if (self.r_resettable) and (len(self.f_default_consts)>0):
            self.code_reset.append(f'\t_write_{self.reg_name}({" | ".join(self.f_default_consts)});')

        if self.r_writable:
            self.code_private_funcs.append(f'/* Intenal function to write to field <{self.field_name}> */')
            self.code_private_funcs.append(f'void _write_{fn_name(self.reg_name)}({self.f_type} value, int hold_cyc)')
            self.code_private_funcs.append('{')
            self.code_private_funcs.append(f'\t{self.format.write_func}({self.r_addr_const}, value, hold_cyc);')
            if self.r_shadow_write or self.r_shadow_read:
                self.code_private_funcs.append(f'\t{self.r_shadow_var} = value;')
                self.code_private_funcs.append(f'\t{self.r_dirty_var} = 0;')
            self.code_private_funcs.append('}')
            self.code_private_funcs.append('')

        if self.r_writable and not self.r_strobed:
            self.code_private_funcs.append(f'/* Intenal function to do a masked write to field <{self.field_name}> */')
            self.code_private_funcs.append(f'void _write_{fn_name(self.reg_name)}_masked({self.f_type} value, int mask)')
            self.code_private_funcs.append('{')
            self.code_private_funcs.append(f'\t{self.format.write_masked_func}({self.r_addr_const}, value, mask);')
            if self.r_shadow_write or self.r_shadow_read:
                self.code_private_funcs.append(f'\tfor (int b = 0; b < {self.registers.port_size//8}; b++)')
                self.code_private_funcs.append(f'\t\tif (mask&(1<<b))')
                self.code_private_funcs.append(f'\t\t\t{self.r_shadow_var} = ({self.r_shadow_var} & ~(0xFF<<(8*b))) | (value & (0xFF<<(8*b)));')
            self.code_private_funcs.append('}')
            self.code_private_funcs.append('')

        if self.r_readable:
            self.code_private_funcs.append(f'/* Intenal function to read from field <{self.field_name}> */')
            self.code_private_funcs.append(f'{self.f_type} _read_{fn_name(self.reg_name)}(int hold_cyc)')
            self.code_private_funcs.append('{')
            self.code_private_funcs.append(f'\t{self.f_type} value = {self.format.read_func}({self.r_addr_const}, hold_cyc);')
            if self.r_shadow_write or self.r_shadow_read:
                self.code_private_funcs.append(f'\t{self.r_shadow_var} = value;')
                self.code_private_funcs.append(f'\t{self.r_dirty_var} = 0;')
            self.code_private_funcs.append(f'\treturn value;')
            self.code_private_funcs.append('}')
            self.code_private_funcs.append('')
                

    def finish(self):
        
        if len(self.code_reset)>0:
            
            com = '// set all registers to their default values'
            sig = 'void reset(void)'
            
            self.code_header.append(com)
            self.code_header.append(sig + ';')
            self.code_header.append('')
            
            self.code_public_funcs.append(com)
            self.code_public_funcs.append(sig)
            self.code_public_funcs.append('{')
            self.code_public_funcs.extend(self.code_reset)
            self.code_public_funcs.append('}')
            self.code_public_funcs.append('')
        
        if len(self.shadow_vars)>0:

            any_shadow_write = any([s.shadow_write for s in self.shadow_vars])
            if any_shadow_write:
                com = [
                    '// write all dirty shadow register contents to hardware',
                    '// set force=1 to force flushing, even if nothing changed locally'
                ]
                sig = 'void flush_shadow(int force)'
                
                self.code_header.extend(com)
                self.code_header.append(sig + ';')
                self.code_header.append('')
                
                self.code_public_funcs.extend(com)
                self.code_public_funcs.append(sig)
                self.code_public_funcs.append('{')
                for s in self.shadow_vars:
                    if not s.shadow_write: continue
                    self.code_public_funcs.append(f'\tif (force || {s.dirty_var})')
                    self.code_public_funcs.append('\t{')
                    self.code_public_funcs.append(f'\t\t_write_{s.fn_name}({s.shadow_var});')
                    self.code_public_funcs.append(f'\t\t{s.dirty_var} = 0;')
                    self.code_public_funcs.append('\t}')
                self.code_public_funcs.append('}')
                self.code_public_funcs.append('')

            any_shadow_read = any([s.shadow_read for s in self.shadow_vars])
            if any_shadow_read:
                com = '// read all shadow register contents from hardware (only readable registers)'
                sig = 'void load_shadow(void)'
                
                self.code_header.append(com)
                self.code_header.append(sig + ';')
                self.code_header.append('')
                
                self.code_public_funcs.append(com)
                self.code_public_funcs.append(sig)
                self.code_public_funcs.append('{')
                for s in self.shadow_vars:
                    if not s.shadow_read: continue
                    self.code_public_funcs.append(f'\t_read_{s.fn_name}();')
                self.code_public_funcs.append('}')
                self.code_public_funcs.append('')

        self.code_main.extend(self.code_defs)
        self.code_main.extend(self.code_public_funcs)
        self.code_main.extend(['//////////////////////////////////////////////////', ''])
        self.code_main.extend(self.code_private_funcs)

        self.code_header = '\n'.join(self.code_header)
        self.code_source = '\n'.join(self.code_main)
