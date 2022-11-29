from context import src, demo_output_folder, prepare_output_folder

from src.registers.structure import RegisterSet, Register, Field, FieldType, FieldFunction, RegType, WriteEventType, FieldChangeType
from src.registers.codegen import RegisterSvGenerator, RegisterPyGenerator, RegisterCGenerator, RegisterMdGenerator



if __name__ == '__main__':

    NAME = demo_output_folder() + '/01-03_advanced_regs'
    prepare_output_folder()


    regset = RegisterSet(name='My Registers', base_address=0x00, port_size=32, registers=[

        # This register can both read and write; this allows us to do read-modify-write accesses
        Register(name='Config 1', description='Config Data 1', address=..., regtype=RegType.WriteRead, fields=[

            # A read-modify-write access allows define three fields whose write-masks partially overlap, but we can still access them individually.
            # Also, note that we define multiple access functions (read and read-modify-write).
            Field(name='Speed', description='Speed Value', bits=[9,0], datatype=FieldType.Unsigned16Bit, functions=[FieldFunction.Read, FieldFunction.ReadModifyWrite]),
            Field(name='Offset', description='Offset Value', bits=[19,10], datatype=FieldType.Signed16Bit, functions=[FieldFunction.Read, FieldFunction.ReadModifyWrite]),
            Field(name='Gain', description='Gain Value', bits=[29,20], datatype=FieldType.Unsigned16Bit, functions=[FieldFunction.Read, FieldFunction.ReadModifyWrite]),
        ]),

        # This is another write-only register
        # Note that this one has the write_event set, which means an internal signal is strobed when the SW writes to this register; this can be
        #   used e.g. to trigger FSMs when a value changes
        Register(name='Config 2', description='Config Data 2', comment="HW is strobed after change", address=..., regtype=RegType.Write, write_event=WriteEventType.StrobeAfterWriteOnCycleEnd, fields=[

            # These fields can be written, but also be read back via a SW-based shadow register.
            # The shadow register also allows us to write the fields individually, even though their write-masks overlap.
            Field(name='Mode', description='Mode', bits=[2,0], datatype=FieldType.Unsigned8Bit, functions=[FieldFunction.ReadShadow, FieldFunction.WriteShadow]),
            Field(name='Delay', description='Delay in µs', bits=[20,3], datatype=FieldType.Unsigned32Bit, functions=[FieldFunction.ReadShadow, FieldFunction.WriteShadow]),
        ]),

        # And a read-only register
        Register(name='Status', description='Status data', address=..., regtype=RegType.Read, fields=[

            Field(name='Speed', description='Measured Speed', bits=[20,0], datatype=FieldType.Unsigned32Bit, functions=[FieldFunction.Read]),
        ]),

        # An event-read register
        # Every time something in hardware changes, this change is latched
        Register(name='Events', description='Event data', address=..., regtype=RegType.ReadEvent, fields=[

            Field(name='Active', description='Activity Indicator', comment="Set if activity bit toggles", bits=[0,0], datatype=FieldType.Boolean, functions=[FieldFunction.Read], trigger_on=FieldChangeType.AnyChange),
        ]),

        # This register is of type Strobe, which means when we write to it, a flag is set and auto-reset in hardware, e.g. to trigger a FSM
        Register(name='Control', description='Control', address=..., regtype=RegType.Strobe, fields=[
            Field(name='Start', description='Start FSM', bits=[0], datatype=FieldType.Strobe, functions=FieldFunction.Strobe),
            Field(name='Stop', description='Stop FSM', bits=[1], datatype=FieldType.Strobe, functions=FieldFunction.Strobe),
        ])
    ])

    
    # Just generate some code
    RegisterSvGenerator(regset).save(
        filename_instance_template=f'{NAME}_instance_template.sv',
        filename_code=f'{NAME}.sv')
    RegisterCGenerator(regset, NAME).save(
        filename_header=f'{NAME}.h',
        filename_code=f'{NAME}.c')
    RegisterPyGenerator(regset).save(f'{NAME}.py')
    RegisterMdGenerator(regset).save(f'{NAME}.md')
