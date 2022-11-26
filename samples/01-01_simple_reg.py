from context import src, demo_output_folder, prepare_output_folder

from src.registers.structure import RegisterSet, Register, Field, FieldType, FieldFunction, RegType
from src.registers.codegen import RegisterSvGenerator, RegisterPyGenerator, RegisterCGenerator, RegisterMdGenerator



if __name__ == '__main__':

    NAME = demo_output_folder() + '/01-01_simple_reg'
    prepare_output_folder()


    # The top-level must be a register set, which contains one or more equally-sized registers
    regset = RegisterSet(
        # - This set of registers starts at base address 0x00
        # - It registers are 16 bit each
        # - The granularity will always be 8 bit (cannot be configured)
        name='my_registers', base_address=0x00, port_size=16, registers=[

        # This is the first register
        Register(
            # - It is at address offset 0
            # - It is writable (but not readable)
            name='config', description='Config Data', address=0x00, regtype=RegType.Write, fields=[

                # Iniside this register, we define a field (a slice of bits that represent some information)
                Field(
                    # - It represents an unsigned 8-bit value, which spans bits 7:0
                    # - It can be written using a mask (i.e. writing to it won't affect neighbouring fields)
                    name='speed', description='Speed Value', bits=[7,0], datatype=FieldType.Unsigned8Bit, functions=FieldFunction.WriteMasked),

                # Iniside this register, we define a field (a slice of bits that represent some information)
                Field(
                    # - It represents a signed 8-bit value, which spans bits 15:8
                    # - It can be written using a mask
                    name='offset', description='Offset Value', bits=[15,8], datatype=FieldType.Signed8Bit, functions=FieldFunction.WriteMasked),
            ],
        ),

        # This is another register
        Register(
            # - It is at the next free address offset (the ellipsis means that the address is auto-incremented)
            # - It is readable (but not writable)
            name='status', description='Status', address=..., regtype=RegType.Read, fields=[

                Field(
                    # - This field represents a boolean flag, which resides in bit 0
                    name='speed', description='Speed Value', bits=[0,0], datatype=FieldType.Boolean, functions=FieldFunction.Read),
            ],
        ),
    ])


    # Now we generate SystemVerilog code from that
    sv = RegisterSvGenerator(regset, modulename='my_registers')
    sv_inst = sv.get_instance_template_code()
    sv_impl = sv.get_code()

    # Let's save that to a file
    sv.save(
        filename_instance_template=f'{NAME}_instance_template.sv',
        filename_code=f'{NAME}.sv')
    
    # Alternatively, we could obtain the code as a string
    sv_code = sv.get_code()

    # In the same way, we can generate C code to control that register from an MCU.
    # The interface between the C-program and the register is up to the developer.
    # This generator asks for the intended filename, so that it can put the proper names into the imports.
    c = RegisterCGenerator(regset, NAME)
    c.save(filename_header=f'{NAME}.h', filename_code=f'{NAME}.c')

    # Alternatively, we can generate Python code
    py = RegisterPyGenerator(regset, 'MyRegisters')
    py.save(f'{NAME}.py')

    
    # And we generate a documentation in Markdown format.
    md = RegisterMdGenerator(regset, 'My Registers')
    md.save(f'{NAME}.md')
    
    # Note that the generated C/Py code currently makes some assumptions about some included files. This will
    #   be improved in the next demo.
