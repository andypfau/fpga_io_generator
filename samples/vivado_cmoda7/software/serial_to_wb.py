from serialcomm import SerialComm


class SerialToWb:

    def __init__(self, comm: "SerialComm"):
        self.comm = comm

    def _fix_address(self, address: int) -> int:

        MAX_ADDRESS = (1 << 31) - 1

        if address < 0 or address > MAX_ADDRESS:
            raise ValueError(f'Address 0x{address:08X} is out of range')
        
        # LSB of address signal has index 2
        ADDRESS_SHIFT = 2
        FORBIDDEN_MASK = (1 << ADDRESS_SHIFT) - 1

        if (address & FORBIDDEN_MASK) != 0:
            raise ValueError(f'Address 0x{address:08X} is misaligned')
        shifted_address = address >> ADDRESS_SHIFT

        return shifted_address
    
    def write_reg_masked(self, address: int, data: int, mask: int=0xFFFFFFFF, hold_cyc: bool = False):
        if hold_cyc:
            raise NotImplementedError()
        self.comm.write_reg(self._fix_address(address), data, mask)
    
    def write_reg(self, address: int, data: int, hold_cyc: bool = False):
        self.comm.write_reg(self._fix_address(address), data)
    
    def read_reg(self, address: int, hold_cyc: bool = False):
        if hold_cyc:
            raise NotImplementedError()
        return self.comm.read_reg(self._fix_address(address))
