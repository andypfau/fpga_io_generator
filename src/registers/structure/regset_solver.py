from ...tools import clog2
from .types import RegisterSet

import math



class RegisterSetSolver:

    def __init__(self, regset: "RegisterSet"):
        self.regset = regset
        regset.check()
        self.assign_register_addresses()

    
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


    def assign_register_addresses(self):
        
        reg_addresses_in_use = []
        next_free_address = 0
        
        address_stride = self.regset.port_size // 8
        (bus_adr_lo, _) = self.regset.address_bit_range()
        forbidden_mask = (1 << bus_adr_lo) - 1
        
        # check assigned addresses
        for reg in self.regset.registers:
            addr = reg._requested_address
            if addr is Ellipsis:
                continue
                
            if (addr & forbidden_mask) != 0:
                raise RuntimeError(f'Register {reg.name}\' address (0x{addr:08X}) is not aligned with the required bus granularity')

            if addr in reg_addresses_in_use:
                raise RuntimeError(f'Register {reg.name}\'s address (0x{addr:08X}) is not unique')
            reg_addresses_in_use.append(addr)

            next_free_address = max(next_free_address, addr + address_stride)

            reg._rel_adr = addr
            reg._abs_adr = addr + self.regset.get_base_address()

        
        for reg in self.regset.registers:
            addr = reg._requested_address
            if addr is not Ellipsis:
                continue
                
            addr = next_free_address
            assert (addr & forbidden_mask) == 0
            next_free_address += address_stride

            reg._rel_adr = addr
            reg._abs_adr = addr + self.regset.get_base_address()
