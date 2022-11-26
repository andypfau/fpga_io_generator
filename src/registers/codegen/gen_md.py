from ..tools import check_names, get_register_addresses
from ..structure.types import RegType, RegisterSet, Register, WriteEventType, FieldChangeType, Field, FieldType, FieldFunction

import math
from dataclasses import dataclass
import enum



class RegisterMdGenerator:

    def __init__(self, registers: RegisterSet, name: str = None):
        self.registers = registers
        self.name = name if name is not None else 'Register Set'
        
        gen = RegisterMdGeneratorHelper(registers, name)
        self.md = gen.md
    

    def get_md(self) -> str:
        return self.md
    

    def save(self, filename: str):
        with open(filename, 'w') as fp:
            fp.write(self.get_md())



class RegisterMdGeneratorHelper:


    def __init__(self, registers: RegisterSet, name: str):
        self.registers = registers
        self.name = name
        
        self.reg_addresses = get_register_addresses(self.registers)
        self.generate()


    def generate(self):
        
        md = []

        md.append(self.name)
        md.append('==========')
        md.append('')
        md.append(f'Base address is 0x{self.registers.base_address:08X}.')
        md.append('')
        md.append(f'All registers are {self.registers.port_size} bit wide, granularity is 8 bit')
        md.append('')
        md.append('')


        md.append('Registers')
        md.append('---------')
        md.append('')
        md.append('| Address  | Absolute Address | Name      | Description       | Access    | Hardware      |')
        md.append('|--------- |------------------|-----------|-------------------|-----------|---------------|')
        for reg in self.registers.registers:
            addr = self.reg_addresses[reg.name]
            abs_addr = addr + self.registers.base_address
            if reg.regtype == RegType.Write:
                typ, hw = 'Write-Only', 'Out'
            elif reg.regtype == RegType.Read:
                typ, hw = 'Read-Only', 'In'
            elif reg.regtype == RegType.WriteRead:
                typ, hw = 'Write/Read', 'In/Out'
            elif reg.regtype == RegType.ReadEvent:
                typ, hw = 'Event', 'Input'
            elif reg.regtype == RegType.Strobe or reg.regtype == RegType.Handshake:
                typ, hw = 'Strobe', 'Output'
            else:
                raise ValueError()
            md.append(f'| 0x{addr:08X}  |  0x{abs_addr:08X}  | {reg.name}  | {reg.description}  | {typ}  | {hw}  |')
        md.append('')
        md.append('')


        md.append('Register Fields')
        md.append('---------------')
        md.append('')
        for reg in self.registers.registers:
            
            md.append(f'### {reg.description}')
            md.append('')

            if reg.comment is not None:
                md.append(reg.comment)
                md.append('')
            
            if reg.regtype == RegType.Write:
                md.append('This register is write-only.')
            elif reg.regtype == RegType.Read:
                md.append('This register is read-only.')
            elif reg.regtype == RegType.WriteRead:
                md.append('This register is write/read.')
            elif reg.regtype == RegType.ReadEvent:
                md.append('This register is read-only. It latches changes.')
            elif reg.regtype == RegType.Strobe or reg.regtype == RegType.Handshake:
                md.append('This register is write-only. It only sends triggers to the hardware.')
            if reg.write_event != 0:
                md.append('Writing to this register triggers the hardware.')
            md.append('')
            
            md.append('| Bits | Name      | Description       | Default | Access    | Specials      |')
            md.append('|------|-----------|-------------------|---------|-----------|---------------|')

            for field in reg.fields:
                
                if len(field.bits) == 1:
                    bits = f'[{field.bits[0]}]'
                else:
                    bits = f'[{field.bits[0]}:{field.bits[1]}]'
                
                if field.default is None:
                    default = 'N/A'
                elif field.datatype == FieldType.Boolean:
                    default = f'{field.default}'
                else:
                    default = f'0x{field.default:X}'

                accesses = []
                if FieldFunction.Read in field.functions:
                    accesses.append('Read')
                if FieldFunction.ReadShadow in field.functions:
                    accesses.append('Read (shadow)')
                if FieldFunction.Overwrite in field.functions:
                    accesses.append('Overwrite')
                if FieldFunction.WriteMasked in field.functions:
                    accesses.append('Write Masked')
                if FieldFunction.WriteShadow in field.functions:
                    accesses.append('Write (shadow)')
                if FieldFunction.ReadModifyWrite in field.functions:
                    accesses.append('RMW')
                if FieldFunction.Strobe in field.functions:
                    accesses.append('Strobe')
                access = ', '.join(accesses)

                specials = []
                if reg.regtype == RegType.ReadEvent:
                    events = []
                    if FieldChangeType.Rising in field.trigger_on:
                        events.append('rising')
                    if FieldChangeType.Falling in field.trigger_on:
                        events.append('falling')
                    if FieldChangeType.High in field.trigger_on:
                        events.append('high')
                    if FieldChangeType.Low in field.trigger_on:
                        events.append('low')
                    if len(events) != 0:
                        specials.append('Trigger on ' + '/'.join(events))
                special = ', '.join(specials)

                md.append(f'| {bits}  | {field.name}  | {field.description}  | {default}   | {access}   | {special}   |')
        md.append('')

        
        self.md = '\n'.join(md)
        


