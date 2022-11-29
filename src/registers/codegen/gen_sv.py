from ...tools import check_names, clog2, make_sourcecode_name, NamingConvention
from ..structure.types import RegType, RegisterSet, Register, WriteEventType, FieldChangeType, Field, FieldType

import math
from dataclasses import dataclass
import enum



class VarnameType(enum.Enum):
    Port = enum.auto()
    AckPort = enum.auto()
    Register = enum.auto()
    DelayRegister = enum.auto()
    LatchRegister = enum.auto()



class RegisterSvGenerator:

    @dataclass
    class Format:
        field_prefix: str = ''
        field_suffix: str = '_field'
        flag_prefix: str = ''
        flag_suffix: str = '_flag'
        strobed_prefix: str = ''
        strobed_suffix: str = '_strobe'
        handshake_req_prefix: str = ''
        handshake_req_suffix: str = '_req'
        handshake_ack_prefix: str = ''
        handshake_ack_suffix: str = '_ack'


    def __init__(self, registers: RegisterSet, format: Format = None):
        self.registers = registers
        self.fmt = format if format is not None else RegisterSvGenerator.Format()
        
        gen = RegisterSvGeneratorHelper(registers, format)
        self.instance = gen.instance
        self.implementation = gen.implementation
    

    def get_instance_template_code(self) -> str:
        return self.instance
    

    def get_code(self) -> str:
        return self.implementation
    

    def save(self, filename_code: str = None, filename_instance_template: str = None):
        if filename_code is not None:
            with open(filename_code, 'w') as fp:
                fp.write(self.get_code())
        if filename_instance_template is not None:
            with open(filename_instance_template, 'w') as fp:
                fp.write(self.get_instance_template_code())



def module_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.snake_case)
def signal_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.snake_case)
def placeholder_name(name: str) -> str:
    return make_sourcecode_name(name, NamingConvention.CONSTANT_CASE)



class RegisterSvGeneratorHelper:


    def __init__(self, registers: RegisterSet, format: "RegisterSvGenerator.Format" = None):
        self.registers = registers
        self.fmt = format if format is not None else RegisterSvGenerator.Format()
        
        self.generate()


    def generate(self):
        
        check_names(self.registers)
        self.perform_pre_checks()
    
        _,_,addr_hi = self.calc_address_ranges()
        
        impl = []
        inst = []
        
        impl.append('// automatically generated code')
        impl.append('')
        impl.append('')

        for line in self.generate_overview_txt():
            impl.append(f'// {line}')

        impl.append('')
        impl.append('')
        impl.append(f'module {module_name(self.registers.name)} (')
        impl.append('')
        impl.append(f'\tinput rst_i,')
        impl.append(f'\tinput clk_i,')
        impl.append('')
        
        inst.append(f'wishbone #(.ADR_BITS({addr_hi+1}), .PORT_SIZE({self.registers.port_size}), .GRANULARITY({8})) __INTERFACE_PLACEHOLDER__();')
        inst.append(f'')
        inst.append(f'{module_name(self.registers.name)} __INSTANCENAME_PLACEHOLDER__ (')
        inst.append(f'\t.rst_i(__SIGNAL_PLACEHOLDER__),')
        inst.append(f'\t.clk_i(__SIGNAL_PLACEHOLDER__),')
        
        code_assignments = []
        code_registers = []
        code_initializations = []
        code_autoclears = []

        if self.has_any_strobed_regs():
            impl.append(f'\t// Register access strobes')
            inst.append(f'\t// Register access strobes')
            for reg in self.registers.registers:
                if reg.write_event is not None:
                    if self.is_strobed_after_write(reg.write_event):
                        portname = self.get_strobe_varname(reg.name, True)
                        regname = self.get_strobe_varname(reg.name, False)
                        regname_latch = self.get_strobe_varname(reg.name, False, True)
                        impl.append(f'\toutput {portname},')
                        inst.append(f'\t.{portname}(__SIGNAL_PLACEHOLDER__),')
                        code_registers.append(f'reg {regname};')
                        code_initializations.append(f'\t\t{regname} <= 0;')
                        code_autoclears.append(f'\t\t{regname} <= 0; // auto-clear')
                        code_assignments.append(f'assign {portname} = {regname};')
                        if reg.write_event==WriteEventType.StrobeAfterWriteOnCycleEnd:
                            code_registers.append(f'reg {regname_latch};')
                            code_initializations.append(f'\t\t{regname_latch} <= 0;')
                    else:
                        raise Exception(f'Register {self.registers.name}.{reg.name} event type {reg.write_event} not yet supported') 
            impl.append('')

        impl.append(f'\t// Register fields')
        inst.append(f'\t// Register fields')
        for reg in self.registers.registers:
            for field in reg.fields:
                f_lo,f_size,f_hi = self.get_field_size(field)

                if self.is_signed(field.datatype):
                    f_val_min, f_val_max = -(1<<(f_size-1)), (1<<(f_size-1))-1
                else:
                    f_val_min, f_val_max = 0, (1<<f_size)-1
                if field.default < f_val_min or field.default > f_val_max:
                    raise Exception(f'Default <{field.default}> for field {self.registers.name}.{reg.name}.{field.name} is out of range {f_val_min}..{f_val_max}')
                    
                if field.default < 0:
                    f_def_com = f' // {field.default}'
                    f_def = field.default & ((1<<f_size)-1)
                else:
                    f_def_com = ''
                    f_def = field.default

                if f_hi >= self.registers.port_size:
                    raise Exception(f'Field {self.registers.name}.{reg.name}.{field.name} is wider than the bus')
                    
                if self.is_strobed(field.datatype) and f_size>1:
                    raise Exception(f'Strobed field {self.registers.name}.{reg.name}.{field.name} must have a size of 1')
                
                if f_hi>f_lo:
                    f_dim = f'[{f_hi-f_lo}:0]'
                else:
                    f_dim = ''
                portname = self.get_varname(reg, field, VarnameType.Port)
                regname = self.get_varname(reg, field, VarnameType.Register)
                ackname = self.get_varname(reg, field, VarnameType.AckPort)
                
                if self.is_writable(reg.regtype):
                    impl.append(f'\toutput{f_dim} {portname},')
                else:
                    impl.append(f'\tinput{f_dim} {portname},')
                inst.append(f'\t.{portname}(__SIGNAL_PLACEHOLDER__),')
                
                if self.is_writable(reg.regtype):
                    code_assignments.append(f'assign {portname} = {regname};')
                    code_registers.append(f'reg{f_dim} {regname};')
                    code_initializations.append(f'\t\t{regname} <= {f_size}\'h{f_def:X};{f_def_com}')
                if self.is_event(reg.regtype):
                    f_hi,f_lo = field.bits[0], field.bits[-1]
                    if f_hi!=f_lo:
                        raise ValueError(f'Field {reg.name}.{field.name} must be exactly one bit wide, as it is in an event-type register')
                    regname_delay = self.get_varname(reg, field, VarnameType.DelayRegister)
                    regname_latch = self.get_varname(reg, field, VarnameType.LatchRegister)
                    code_registers.append(f'reg{f_dim} {regname_delay}, {regname_latch};')
                    code_initializations.append(f'\t\t{regname_delay} <= 0;')
                    code_initializations.append(f'\t\t{regname_latch} <= 0;')
                if self.is_strobed(reg.regtype):
                    if self.is_handshake(reg.regtype):
                        impl.append(f'\tinput {ackname},')
                        inst.append(f'\t.{ackname}(__SIGNAL_PLACEHOLDER__),')
                        code_autoclears.append(f'\t\tif ({ackname}) begin')
                        code_autoclears.append(f'\t\t\t{regname} <= {f_size}\'b{f_def:};')
                        code_autoclears.append(f'\t\tend')
                    else:
                        code_autoclears.append(f'\t\t{regname} <= {f_size}\'b{f_def:}; // auto-clear')
                
        impl.append('')

        inst.append(f'\t// Wishbone slave')
        inst.append(f'\t.wb_s(__INTERFACE_PLACEHOLDER__)')

        impl.append(f'\t// Wishbone slave')
        impl.append(f'\twishbone.slave wb_s')
        impl.append('')
        impl.append(f');')
        impl.append('')
        impl.append('')
        impl.extend(code_registers)
        impl.append('')
        impl.append(f'reg ack_r;')
        impl.append(f'reg[{self.registers.port_size-1}:0] wb_dat_r;')
        impl.append('')
        impl.append('')
        
        impl.append(f'always_ff @(posedge clk_i or posedge rst_i) begin')
        impl.append(f'\tif (rst_i) begin')
        impl.extend(code_initializations)
        impl.append(f'\t\twb_dat_r <= {self.registers.port_size}\'h0;')
        impl.append(f'\t\tack_r <= 0;')
        impl.append(f'\tend else begin')
        impl.append(f'\t\tack_r <= 0;')
        impl.append(f'\t\twb_dat_r <= {self.registers.port_size}\'h0;')
        impl.extend(code_autoclears)
        for reg in self.registers.registers:
            if self.is_event(reg.regtype):
                for field in reg.fields:
                    _,f_size,_ = self.get_field_size(field)
                    if f_size > 1:
                        raise ValueError(f'Field {reg.name}.{field.name} must be exactly one bit wide, as it is in an event-type register')
                    portname = self.get_varname(reg, field, VarnameType.Port)
                    regname_delay = self.get_varname(reg, field, VarnameType.DelayRegister)
                    regname_latch = self.get_varname(reg, field, VarnameType.LatchRegister)
                    impl.append(f'\t\t{regname_delay} <= {portname}; // latch current state')
                    if FieldChangeType.Rising in field.trigger_on:
                        impl.append(f'\t\tif (({portname} == 1) && ({regname_delay} == 0)) // rising edge')
                        impl.append(f'\t\t\t{regname_latch} <= 1;')
                    if FieldChangeType.Falling in field.trigger_on:
                        impl.append(f'\t\tif (({portname} == 0) && ({regname_delay} == 1)) // falling edge')
                        impl.append(f'\t\t\t{regname_latch} <= 1;')
                    if FieldChangeType.High in field.trigger_on:
                        impl.append(f'\t\tif ({portname} == 1) // high')
                        impl.append(f'\t\t\t{regname_latch} <= 1;')
                    if FieldChangeType.Low in field.trigger_on:
                        impl.append(f'\t\tif ({portname} == 0) // low')
                        impl.append(f'\t\t\t{regname_latch} <= 1;')
            else:
                for field in reg.fields:
                    if field.trigger_on != 0:
                        raise ValueError(f'Field {reg.name}.{field.name} cannot have an event type set (only valid for event type registers)')
            
        impl.append(f'\t\tif (wb_s.stb) begin')
        impl.append(f'\t\t\tif (wb_s.we) begin')

        def gen_reg_code(write):
            for i_reg,reg in enumerate(self.registers.registers):
                if reg.regtype not in [RegType.Write, RegType.WriteRead, RegType.Read, RegType.Strobe, RegType.Handshake, RegType.ReadEvent]:
                    raise Exception(f'Invalid regtype: {reg.regtype}')

                addr = reg.get_relative_address()

                forbidden_mask = self.registers.port_size//8 - 1
                if (addr & forbidden_mask) != 0:
                    raise Exception(f'register {reg.name} address misaligned: 0x{addr:X}')
                
                adr_lo = int(math.ceil(math.log2(self.registers.port_size//8)))

                endelse = 'end else ' if i_reg>0 else ''
                impl.append(f'\t\t\t\t{endelse}if (wb_s.adr== (\'h{addr:X} >> {adr_lo})) begin')

                added_field_code = False
                bits_in_use = 0
                for field in reg.fields:
                    f_hi,f_lo = field.bits[0], field.bits[-1]

                    for bit_offset in range(f_lo, f_hi+1):
                        mask = 1 << bit_offset
                        if bits_in_use & mask != 0:
                            raise RuntimeError(f'Field {reg.name}.{field.name} overlaps with other fields')
                        bits_in_use |= mask

                    bytewise = write or self.is_event(reg.regtype)
                    if bytewise:
                        bit_ranges = list(zip(list(range(7, self.registers.port_size, 8)), list(range(0, self.registers.port_size-7, 8))))
                    else:
                        bit_ranges = [(self.registers.port_size-1,0)]

                    if f_hi >= self.registers.port_size:
                        raise Exception(f'Field {reg.name}.{field.name} is wider than the register size')
                    
                    regname = self.get_varname(reg, field, VarnameType.Register)
                    
                    for bit_hi,bit_lo in bit_ranges:
                        
                        i_byte = bit_lo//8

                        wb_slice_lo = max(bit_lo, f_lo)
                        wb_slice_hi = min(bit_hi, f_hi)

                        if wb_slice_hi >= wb_slice_lo:

                            field_slice_lo = wb_slice_lo - f_lo
                            field_slice_hi = wb_slice_hi - f_lo

                            def get_slice_code(hi, lo, totsize):
                                if totsize <= 1:
                                    return ''
                                elif hi>lo:
                                    return f'[{hi}:{lo}]'
                                else:
                                    return f'[{lo}]'

                            f_slice = get_slice_code(field_slice_hi, field_slice_lo, f_hi-f_lo+1)
                            wb_slice = get_slice_code(wb_slice_hi, wb_slice_lo, self.registers.port_size)
                            
                            if (not write) and self.is_event(reg.regtype):
                                regname_latch = self.get_varname(reg, field, VarnameType.LatchRegister)
                                impl.append(f'\t\t\t\t\twb_dat_r{wb_slice} <= {regname_latch};')
                                impl.append(f'\t\t\t\t\tif (wb_s.sel[{i_byte}]) begin')
                                impl.append(f'\t\t\t\t\t\t{regname_latch} <= 0; // clear latch on read')
                                impl.append(f'\t\t\t\t\tend')
                                added_field_code = True
                            elif write and self.is_writable(reg.regtype):
                                regname = self.get_varname(reg, field, VarnameType.Register)
                                impl.append(f'\t\t\t\t\tif (wb_s.sel[{i_byte}]) begin')
                                impl.append(f'\t\t\t\t\t\t{regname}{f_slice} <= wb_s.dat_ms{wb_slice};')
                                impl.append(f'\t\t\t\t\tend')
                                added_field_code = True
                            elif (not write) and self.is_readable(reg.regtype):
                                if self.is_writable(reg.regtype):
                                    regname = self.get_varname(reg, field, VarnameType.Register)
                                else:
                                    regname = self.get_varname(reg, field, VarnameType.Port)
                                impl.append(f'\t\t\t\t\twb_dat_r{wb_slice} <= {regname}{f_slice};')
                                added_field_code = True
                    
                if added_field_code and self.is_strobed_after_write(reg.write_event):
                    is_latch = reg.write_event==WriteEventType.StrobeAfterWriteOnCycleEnd
                    regname = self.get_strobe_varname(reg.name, False, is_latch)
                    impl.append(f'\t\t\t\t\t{regname} <= 1;')

            if len(self.registers.registers)>0:
                impl.append(f'\t\t\t\tend')

        gen_reg_code(True)
        impl.append(f'\t\t\tend else begin // read')
        gen_reg_code(False)
        impl.append(f'\t\t\t\tack_r <= 1;')
        impl.append(f'\t\t\tend')
        impl.append(f'\t\tend')
        impl.append(f'\t\tif (~wb_s.cyc) begin')
        for reg in self.registers.registers:
            if reg.write_event==WriteEventType.StrobeAfterWriteOnCycleEnd:
                regname = self.get_strobe_varname(reg.name, False)
                regname_latch = self.get_strobe_varname(reg.name, False, True)
                impl.append(f'\t\t\t{regname} <= {regname_latch};')
                impl.append(f'\t\t\t{regname_latch} <= 0;')
        impl.append(f'\t\tend')
        impl.append(f'\tend')
        impl.append(f'end')
        impl.append('')
        impl.append('')
        impl.extend(code_assignments)
        impl.append('')
        impl.append('assign wb_s.dat_sm = wb_dat_r;')
        impl.append('assign wb_s.ack = wb_s.stb & (wb_s.we | ack_r);')
        impl.append('assign wb_s.err = \'0;')
        impl.append('assign wb_s.rty = \'0;')
        impl.append('')
        impl.append('')
        impl.append(f'endmodule')
        impl.append('')

        inst.append(');')
        inst.append('')

        self.implementation = '\n'.join(impl)
        self.instance = '\n'.join(inst)


    def has_any_strobed_regs(self):
        for reg in self.registers.registers:
            if reg.write_event is not None:
                return True
        return False
    

    def generate_overview_txt(self,) -> "list[str]":
        result = []
        for reg in self.registers.registers:
            if reg.regtype==RegType.Write:
                r_comment = 'write-only'
            elif reg.regtype==RegType.Read:
                r_comment = 'read-only'
            elif reg.regtype==RegType.WriteRead:
                r_comment = 'write + read-back'
            elif reg.regtype==RegType.Strobe:
                r_comment = 'strobe'
            elif reg.regtype==RegType.Handshake:
                r_comment = 'strobe with handshake'
            elif reg.regtype==RegType.ReadEvent:
                r_comment = 'event read-only'
            else:
                raise Exception(f'Unknown regtype: {field["regtype"]}')
            result.append(f'0x{reg.get_relative_address():08X}: <{reg.name}> ({r_comment}) {reg.description}')
            if reg.comment:
                result.append(f'    {reg.comment}')
            for field in reg.fields:
                f_lo,_,f_hi = self.get_field_size(field)
                result.append(f'    [{f_hi}:{f_lo}]: <{field.name}> {field.description}')
                if field.comment:
                    result.append(f'        {field.comment}')
        return result
    

    def calc_address_ranges(self) -> "tuple(int,int,int)":
        
        max_byteaddr = 0
        for reg in self.registers.registers:
            max_byteaddr = max(max_byteaddr, reg.get_relative_address())

        addr_lo = clog2(self.registers.port_size//8)
        addr_hi = max(addr_lo, clog2(max_byteaddr+1)-1)

        return max_byteaddr, addr_lo, addr_hi


    def perform_pre_checks(self):
        if self.registers.port_size not in [8, 16, 32, 64]:
            raise Exception(f'Invalid register size: {self.registers.port_size}')

    
    def is_signed(self, fieldtype):
        return fieldtype in [FieldType.Signed8Bit, FieldType.Signed16Bit, FieldType.Signed32Bit, FieldType.Signed64Bit]


    def is_strobed(self, regtype):
        return regtype in [RegType.Strobe, RegType.Handshake]


    def is_handshake(self, regtype):
        return regtype in [RegType.Handshake]


    def is_writable(self, regtype):
        return regtype in [RegType.Write, RegType.WriteRead, RegType.Strobe, RegType.Handshake]


    def is_readable(self, regtype):
        return regtype in [RegType.WriteRead, RegType.Read, RegType.ReadEvent]


    def is_event(self, regtype):
        return regtype in [RegType.ReadEvent]


    def is_strobed_after_write(self, regevent):
        return regevent in [WriteEventType.StrobeOnWrite, WriteEventType.StrobeAfterWriteOnCycleEnd]


    def get_strobe_varname(self, reg_name: str, is_io:bool, is_latch:bool=False):
        if is_io :
            sigil = '_o'
        elif is_latch :
            sigil = '_latch_o'
        else:
            sigil = '_r'
        return f'{self.fmt.strobed_prefix}{signal_name(reg_name)}_access{self.fmt.strobed_suffix}{sigil}'

    
    def get_field_size(self, field: Field) -> "tuple(int,int,int)":
        
        f_hi,f_lo = field.bits[0], field.bits[-1]
        f_size = f_hi - f_lo + 1

        return f_lo, f_size, f_hi


    def get_varname(self, reg: Register, field: Field, var_type: VarnameType) -> str:

        _,f_size,_ = self.get_field_size(field)
        name = signal_name(f'{reg.name}_{field.name}')

        if self.is_handshake(reg.regtype):
            if var_type == VarnameType.AckPort:
                prefix = self.fmt.handshake_ack_prefix
                suffix = self.fmt.handshake_ack_suffix
            else:
                prefix = self.fmt.handshake_req_prefix
                suffix = self.fmt.handshake_req_suffix
        elif self.is_strobed(reg.regtype):
            prefix = self.fmt.strobed_prefix
            suffix = self.fmt.strobed_suffix
        elif f_size>1:
            prefix = self.fmt.field_prefix
            suffix = self.fmt.field_suffix
        else:
            prefix = self.fmt.flag_prefix
            suffix = self.fmt.flag_suffix
        
        if var_type == VarnameType.DelayRegister:
            suffix += '_delay'
        elif var_type == VarnameType.LatchRegister:
            suffix += '_latch'
        
        if var_type == VarnameType.Port or var_type == VarnameType.AckPort:
            if self.is_handshake(reg.regtype) and var_type == VarnameType.AckPort:
                sigil = '_i'
            elif self.is_writable(reg.regtype):
                sigil = '_o'
            else:
                sigil = '_i'
        else:
            sigil = '_r'

        return f'{prefix}{name}{suffix}{sigil}'
