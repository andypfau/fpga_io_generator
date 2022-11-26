import math


def get_adr_bits(component):
    lo = int(math.ceil(math.log2(component.port_size//component.granularity)))
    return lo+component.address_size-1, lo


def get_sel_bits(component):
    return component.port_size//component.granularity-1, 0
