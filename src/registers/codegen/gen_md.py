from ...tools import check_names, md_table
from ..structure.types import RegType, RegisterSet, Register, WriteEventType, FieldChangeType, Field, FieldType, FieldFunction

import math
from dataclasses import dataclass
import enum



class RegisterMdGenerator:

    def __init__(self, registers: RegisterSet):
        self.registers = registers
        
        gen = RegisterMdGeneratorHelper(registers)
        self.md = gen.md
    

    def get_md(self) -> str:
        return self.md
    

    def save(self, filename: str):
        with open(filename, 'w') as fp:
            fp.write(self.get_md())



class RegisterMdGeneratorHelper:


    def __init__(self, registers: RegisterSet):
        self.registers = registers
        
        self.generate()
    

    def generate(self):
        
        md = []

        md.append(self.registers.name)
        md.append('==========')
        md.append('')
        md.append(f'Base address is 0x{self.registers.get_base_address():08X}.')
        md.append('')
        md.append(f'All registers are {self.registers.port_size} bit wide, granularity is 8 bit')


        md.append('')
        md.append('')
        md.append('## Registers')
        md.append('')

        table = [['Rel. Offset', 'Abs. Address', 'Name', 'Description', 'Access', 'Hardware', 'Comments']]
        comments = []
        for reg in self.registers.registers:
            
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

            if reg.comment is None:
                com = ''
            else:
                comments.append(reg.comment)
                com = len(comments)
            
            table.append([f'0x{reg.get_relative_address():08X}', f'0x{reg.get_absolute_address():08X}', reg.name, reg.description, typ, hw, com])

        md.extend(md_table(table))

        if len(comments) > 0:
            md.append('')
            for i,c in enumerate(comments):
                md.append(f'{i+1}. {c}')


        md.append('')
        md.append('')
        md.append('## Register Fields')
        for reg in self.registers.registers:
            
            md.append('')
            md.append('')
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
            if reg.write_event != 0 and reg.write_event is not None:
                md.append('Writing to this register triggers the hardware.')
            md.append('')
            
            table = [['Bits', 'Name', 'Description', 'Default', 'Access', 'Specials', 'Comments']]
            comments = []
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

                if field.comment is None:
                    com = ''
                else:
                    comments.append(field.comment)
                    com = len(comments)

                table.append([bits, field.name, field.description, default, access, special, com])
            md.extend(md_table(table))

            if len(comments) > 0:
                md.append('')
                for i,c in enumerate(comments):
                    md.append(f'{i+1}. {c}')

        md.append('')

        
        self.md = '\n'.join(md)
        


