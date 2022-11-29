from context import src, demo_output_folder, prepare_output_folder

from src.registers.structure import RegisterSet, Register, Field, FieldType, FieldFunction, RegType
from src.registers.codegen import RegisterSvGenerator, RegisterPyGenerator, RegisterCGenerator, RegisterMdGenerator



if __name__ == '__main__':

    NAME = demo_output_folder() + '/01-02_code_format'
    prepare_output_folder()


    # Same register as in the last demo
    regset = RegisterSet(name='My Registers', base_address=0x00, port_size=16, registers=[
        Register(name='Config', description='Config Data', address=0x00, regtype=RegType.Write, fields=[
            Field(name='Speed', description='Speed Value', bits=[7,0], datatype=FieldType.Unsigned8Bit, functions=FieldFunction.WriteMasked),
            Field(name='Offset', description='Offset Value', bits=[15,8], datatype=FieldType.Signed8Bit, functions=FieldFunction.WriteMasked)]),
        Register(name='Status', description='Status', address=0x02, regtype=RegType.Read, fields=[
            Field(name='Speed', description='Speed Value', bits=[0,0], datatype=FieldType.Boolean, functions=FieldFunction.Read)])])


    # This time, we apply some configuration
    # Check the Format class for more options
    # Note that the formatting is its own object, so it can be re-used for multiple code generator instances
    sv_fmt = RegisterSvGenerator.Format(
        flag_suffix = '_flg', # apply the suffix '_flg' to flag registers
    )
    sv = RegisterSvGenerator(regset, format=sv_fmt)
    sv.save(
        filename_instance_template=f'{NAME}_instance_template.sv',
        filename_code=f'{NAME}.sv')


    # The C code generator also allows formatting
    c_fmt = RegisterCGenerator.Format(
        read_func='hw_read_reg', # to read from the bus, call this function
        write_func='hw_write_reg', # to write to the bus, call this function
        write_masked_func='hw_write_reg_masked', # to write to the bus with a word-mask, call this function
        includes=['"hw_access.h"'], # include this file
    )
    c = RegisterCGenerator(regset, NAME, format=c_fmt)
    c.save(filename_header=f'{NAME}.h', filename_code=f'{NAME}.c')


    # And the same for Python
    py_fmt = RegisterPyGenerator.Format(
        read_func='rd', # to read from the bus, call this function
        write_func='wr', # to write to the bus, call this function
        write_masked_func='wrm', # to write to the bus with a word-mask, call this function
        accessor_obj=True, # we will get handed an object on which we can call the above methods
    )
    py = RegisterPyGenerator(regset, format=py_fmt)
    py.save(f'{NAME}_object.py')

    ################

    # And another example with imported hardware access methods
    py_fmt = RegisterPyGenerator.Format(
        read_func='hw_rd', # to read from the bus, call this function
        write_func='hw_wr', # to write to the bus, call this function
        write_masked_func='hw_wrm', # to write to the bus with a word-mask, call this function
        accessor_obj=False, # no object is handed over, we must rely on some global object
        import_clauses=['from MyHwAccess import hw_rd, hw_wr, hw_wrm'],
    )
    py = RegisterPyGenerator(regset, format=py_fmt)
    py.save(f'{NAME}_global.py')

    
    # The Markdown generator currently has no options
    md = RegisterMdGenerator(regset)
    md.save(f'{NAME}.md')
