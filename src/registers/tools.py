import math, warnings
from .structure.types import RegisterSet, Register


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


def get_register_addresses(registers: RegisterSet) -> "map[str, int]":
    
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
