import math
import re
import enum


def check_names(registers: "WbRegisterSet"):
    
    regnames = set()
    for reg in registers.registers:

        if not isinstance(reg.name, str):
            raise RuntimeError('Register name "{reg.name}" must be a proper string')

        regnames.add(reg.name)
        
        fieldnames = set()
        for field in reg.fields:
            
            if not isinstance(field.name, str):
                raise RuntimeError('Register name "{reg.name}" must be a proper string')

            fieldnames.add(field.name)
        
        if len(fieldnames) < len(reg.fields):
            raise RuntimeError(f'Field names in {registers.name}.{reg.name} are not unique')
    
    if len(regnames) < len(registers.registers):
        raise RuntimeError(f'Register names in {registers.name} are not unique')


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
    assert n >= 0
    assert isinstance(n, int)
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


class NamingConvention(enum.Enum):
    snake_case = enum.auto()
    CONSTANT_CASE = enum.auto()
    PascalCase = enum.auto()


def make_sourcecode_name(name: str, convention: "NamingConvention" = NamingConvention.snake_case) -> str:

    # split at word boundaries
    is_mixed_case = re.search(r'[a-z]', name) is not None and re.search(r'[A-Z]', name) is not None
    contains_separators = re.search(r'[ _-]', name) is not None
    if is_mixed_case and not contains_separators:
        cuts = [m.span()[0] for m in re.finditer(r'[A-Z]+', name)]
        pos = 0
        parts = []
        for cut in cuts:
            a, b = pos, cut
            if b > a:
                parts.append(name[a:b])
            pos = b
        if pos < len(name):
            parts.append(name[pos:])
        parts = [p.lower() for p in parts]
    else:
        parts = re.split(r'[ _-]', name)

    # remove empty parts
    parts = [p for p in parts if len(p)>0]

    # remove invalid characters
    parts = [re.sub(r'[^a-zA-Z0-9]', r'', p) for p in parts]

    # convert to naming convention
    if convention is NamingConvention.snake_case:
        code = '_'.join([p.lower() for p in parts])
    elif convention is NamingConvention.CONSTANT_CASE:
        code = '_'.join([p.upper() for p in parts])
    elif convention is NamingConvention.PascalCase:
        code = ''
        for part in parts:
            code += part[0].upper() + part[1:].lower()

    # remote leading digits
    if re.match(r'^[0-9]*$', code):
        code = '_' + code

    return code
