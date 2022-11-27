import math, warnings


def check_names(registers, test_fn: callable = None):
    
    regnames = set()
    for reg in registers.registers:

        if not isinstance(reg.name, str):
            raise RuntimeError('Register name "{reg.name}" must be a proper string')
        if test_fn:
            test_fn(reg.name)

        regnames.add(reg.name)
        
        fieldnames = set()
        for field in reg.fields:
            
            if not isinstance(field.name, str):
                raise RuntimeError('Register name "{reg.name}" must be a proper string')
            if test_fn:
                test_fn(field.name)

            fieldnames.add(field.name)
        
        if len(fieldnames) < len(reg.fields):
            raise RuntimeError(f'Field names in {registers.name}.{reg.name} are not unique')
    
    if len(regnames) < len(registers.registers):
        raise RuntimeError(f'Register names in {registers.name} are not unique')


def get_register_addresses(registers: "RegisterSet") -> "map[str, int]":
    
    reg_addresses = {}
    next_auto_address = 0
    
    for reg in registers.registers:
        
        if reg.address is Ellipsis:
            addr = next_auto_address
        else:
            addr = reg.address
        
        if addr in reg_addresses.values():
            raise RuntimeError(f'Register "{reg.name}" address (0x{addr:X}) is not unique')
        
        reg_addresses[reg.name] = addr
        next_auto_address = addr + (registers.port_size // 8)

    return reg_addresses


def clog2(x: float) -> int:
    return int(math.ceil(math.log2(x)))


def md_table(rows: "list[list[any]]") -> str:
    
    cols = zip(*rows)
    widths = [max([len(str(cell))+2 for cell in col]) for col in cols]

    def print_row(row):
        line = []
        for width,cell in zip(widths, row):
            s = ' ' + str(cell) + ' '
            while len(s) < width:
                s += ' '
            line.append(s)
        return '|' + '|'.join(line) + '|'

    def print_separator_row():
        line = []
        for width in widths:
            line.append('-'*width)
        return '|' + '|'.join(line) + '|'

    md = []
    for i, row in enumerate(rows):
        md.append(print_row(row))
        if i==0:
            md.append(print_separator_row())

    return md


def binary_si(n: int, unit: str = '') -> str:
    prefix, factor = '', 1
    for e,p in [(4,'Ti'), (3,'Gi'), (2,'Mi'), (1,'ki')]:
        f = pow(2, 10*e)
        if n > f:
            prefix, factor = p, f
            break
    num = str(round(n//factor))
    suffix = prefix + unit
    if len(suffix) == 0:
        return num
    else:
        return f'{num} {suffix}'
