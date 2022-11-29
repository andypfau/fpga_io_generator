import serial


BAUDRATE = 115384


class SerialComm:

    def __init__(self, port:str, verbose:bool=False):
        self.port = port
        self.verbose = verbose
        self.serial = serial.Serial(port, BAUDRATE)
        self.address_nibbles = 4
        self.data_nibbles = 8
        self.mask_nibbles = 1
        self.term_char = '\n'
        self.data_counter = 0
    
    def write_reg_masked(self, address: int, data: int, mask: int=0xFFFFFFFFFFFFFFFF, hold_cyc: bool = False):
        if hold_cyc:
            raise NotImplementedError()
        tx = self._get_buf('w', address, data, mask)
        rx = self._write_read(tx)
        self._parse_buf(rx)
    
    def write_reg(self, address: int, data: int, hold_cyc: bool = False):
        self.write_reg_masked(address, data, 0xFFFFFFFFFFFFFFFF, hold_cyc)
    
    def read_reg(self, address: int, hold_cyc: bool = False):
        if hold_cyc:
            raise NotImplementedError()
        tx = self._get_buf('r', address)
        rx = self._write_read(tx)
        data = self._parse_buf(rx)
        return data

    def _write_read(self, buf):
        self._write(buf)
        return self._read()
    
    def _write(self, buf):
        if self.verbose:
            print(f'-> {buf}')
        self.data_counter += len(buf)
        self.serial.write(buf)
        self.serial.flush()

    def _read(self):
        buf =  self.serial.read_until(expected=bytes(self.term_char, 'ascii'))
        if self.verbose:
            print(f'<- {buf}')
        self.data_counter += len(buf)
        return buf[:-1] # remove term char
    
    def _get_buf(self, command:int, address:int, data:int=None, mask:int=None):
        buf = command
        for i in reversed(range(self.address_nibbles)):
            buf += f'{(address>>(i*4))&0xF:x}'
        if data is not None:
            for i in reversed(range(self.data_nibbles)):
                buf += f'{(data>>(i*4))&0xF:x}'
        if mask is not None:
            for i in reversed(range(self.mask_nibbles)):
                buf += f'{(mask>>(i*4))&0xF:x}'
        buf += self.term_char
        return bytes(buf, 'ascii')
    
    def _parse_buf(self, buf):
        s = buf.decode('ascii')
        try:
            if len(s) >= 1:
                if s[0]=='e':
                    raise IOError('HW reports communication error')
                if s[0]=='t':
                    raise IOError('HW reports timeout error')
                if s[0]!='o':
                    raise IOError('HW reported unexpected state')
            else:
                raise IOError('HW did not respond')
            if len(s) == 1:
                return None
            elif len(s) == 1 + self.data_nibbles:
                data = int(s[1:], 16)
                if self.verbose:
                    print(f'<- ={data}')
                return data
            else:
                raise IOError('HW reports malformatted result')
        except IOError as ex:
            raise IOError(f'Unable to parse result "{s}": {str(ex)}')
