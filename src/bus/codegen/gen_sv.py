from ..tools import get_adr_bits
from ...tools import make_sourcecode_name, NamingConvention
from ..structure.types import WbBus, WbMaster, WbSlave, WbNode

import math
import re



class BusSvGenerator:

    def __init__(self, bus: 'WbBus'):
        self.bus = bus
        
        gen = BusSvGeneratorHelper(bus)
        self.instance = gen.instance
        self.implementation = gen.implementation
    

    def get_instance_template_code(self) -> str:
        return self.instance
    

    def get_code(self) -> str:
        return self.implementation
    

    def save(self, filename_code: str = None, filename_instance_template: str = None):
        if filename_code is not None:
            with open(filename_code, 'w') as fp:
                fp.write(self.get_code())
        if filename_instance_template is not None:
            with open(filename_instance_template, 'w') as fp:
                fp.write(self.get_instance_template_code())
           


class BusSvGeneratorHelper:

    def __init__(self, bus: 'WbBus'):
        self.bus = bus

        self.bus.check()
        self.update()
     
    
    def update(self):

        def module_name(name: str) -> str:
            return make_sourcecode_name(name, NamingConvention.snake_case)
        def signal_name(name: str) -> str:
            return make_sourcecode_name(name, NamingConvention.snake_case)
        def placeholder_name(name: str) -> str:
            return make_sourcecode_name(name, NamingConvention.CONSTANT_CASE)
        
        from ..structure.types import WbBusTopology

        bus_port_size = self.bus.bus_format.port_size
        bus_granularity = self.bus.bus_format.granularity
        bus_address_size = self.bus.bus_format.address_size
            
        bus_adr_hi, bus_adr_lo = bus_address_size-1, int(round(math.log2(bus_port_size//bus_granularity)))
        bus_sel_hi = bus_port_size//bus_granularity-1
        
        inst = []

        for master in self.bus.masters:
            inst.append(f'wishbone #(.ADR_BITS({master.address_size}), .PORT_SIZE({master.port_size}), .GRANULARITY({master.granularity})) __INTERFACE_{placeholder_name(master.name)}_PLACEHOLDER__();')
        for slave in self.bus.slaves:
            inst.append(f'wishbone #(.ADR_BITS({slave.address_size}), .PORT_SIZE({slave.port_size}), .GRANULARITY({slave.granularity})) __INTERFACE_{placeholder_name(slave.name)}_PLACEHOLDER__();')
        inst.append(f'')
        inst.append(f'{module_name(self.bus.name)} __INSTANCENAME_PLACEHOLDER__ (')
        inst.append(f'\t.rst_i(__SIGNAL_RESET_PLACEHOLDER__),')
        inst.append(f'\t.clk_i(__SIGNAL_CLOCK_PLACEHOLDER__),')
        for master in self.bus.masters:
            inst.append(f'\t.{signal_name(master.name)}_mi(__INTERFACE_{placeholder_name(master.name)}_PLACEHOLDER__),')
        for slave in self.bus.slaves:
            inst.append(f'\t.{signal_name(slave.name)}_so(__INTERFACE_{placeholder_name(slave.name)}_PLACEHOLDER__),')
        inst[-1] = inst[-1][0:-1] # remove the last comma
        inst.append(');')
        inst.append('')

        impl = []

        impl.append(f'// automatically generated code')
        impl.append(f'')
        impl.append(f'')
        impl.append(f'// masters:')
        for master in self.bus.masters:
            impl.append(f'// - {master.name} (width {master.port_size} b, granularity {master.granularity} b, addres {master.address_size} b)')
        impl.append(f'// slaves:')
        for slave in self.bus.slaves:
            impl.append(f'// - 0x{slave.get_base_address():08X}: {slave.name} (width {slave.port_size} b, granularity {slave.granularity} b, address {slave.address_size} b)')
        impl.append(f'')
        impl.append(f'')
        impl.append(f'module {module_name(self.bus.name)} (')
        impl.append(f'')
        impl.append(f'\tinput wire clk_i,')
        impl.append(f'\tinput wire rst_i,')
        impl.append(f'\t')

        for master in self.bus.masters:
            impl.append(f'\twishbone.slave {module_name(master.name)}_mi,')
        
        impl.append(f'\t')
        
        for slave in self.bus.slaves:
            impl.append(f'\twishbone.master {module_name(slave.name)}_so,')
        
        impl.append(f'\t')
        
        # remove the last comma
        impl[-2] = impl[-2][0:-1]
        
        impl.append(f');')
        impl.append(f'')
        impl.append(f'')

        if self.bus.topology == WbBusTopology.SharedBus:
            impl.append(f'/////////////////////////////////////////////////////////////')
            impl.append(f'// common bus')
            impl.append(f'')
            impl.append(f'')
            impl.append(f'logic[{bus_adr_hi}:{bus_adr_lo}] bus_adr_l;')
            impl.append(f'logic[{bus_port_size-1}:0] bus_dat_ms_l;')
            impl.append(f'logic[{bus_port_size-1}:0] bus_dat_sm_l;')
            impl.append(f'logic[{bus_sel_hi}:0] bus_sel_l;')
            impl.append(f'logic bus_stb_l;')
            impl.append(f'logic bus_cyc_l;')
            impl.append(f'logic bus_we_l;')
            impl.append(f'logic bus_ack_l;')
            impl.append(f'logic bus_err_l;')
            impl.append(f'logic bus_rty_l;')

        adapter_decls = []
        adapter_impls = []
        def adapt(components:"WbNode", is_master:bool):
            adapted_names = {}
            for component in components:
                if self.bus.get_adapter(component) is None: # can be connected directly
                    suffix = '_mi' if is_master else '_so'
                    adapted_names[component.name] = signal_name(component.name) + suffix
                else: # need adapter
                    comp_name = signal_name(component.name) + '_adapted_w'
                    adapted_names[component.name] = comp_name
                    if is_master:
                        comp_addr_size, comp_port_size, comp_gran = bus_address_size, bus_port_size, bus_granularity
                    else:
                        comp_addr_size, comp_port_size, comp_gran = component.address_size, component.port_size, component.granularity
                    adapter_decls.append(f'wishbone #(.ADR_BITS({comp_addr_size}), .PORT_SIZE({comp_port_size}), .GRANULARITY({comp_gran})) {comp_name}();')
                    adapter_impls.append(f'')
                    adapter_impls.append(f'wb_adapter #(')
                    if is_master:
                        adapter_impls.append(f'\t.MASTER_ADR_BITS({component.address_size}),')
                        adapter_impls.append(f'\t.MASTER_PORT_SIZE({component.port_size}),')
                        adapter_impls.append(f'\t.MASTER_GRANULARITY({component.granularity}),')
                        adapter_impls.append(f'\t.SLAVE_ADR_BITS({bus_address_size}),')
                        adapter_impls.append(f'\t.SLAVE_PORT_SIZE({bus_port_size}),')
                        adapter_impls.append(f'\t.SLAVE_GRANULARITY({bus_granularity})')
                        adapter_impls.append(f') wb_adapter_bus_to_slave_{module_name(component.name)} (')
                        adapter_impls.append(f'\t.master_m({module_name(component.name)}_mi),')
                        adapter_impls.append(f'\t.slave_s({comp_name})')
                    else:
                        adapter_impls.append(f'\t.MASTER_ADR_BITS({bus_address_size}),')
                        adapter_impls.append(f'\t.MASTER_PORT_SIZE({bus_port_size}),')
                        adapter_impls.append(f'\t.MASTER_GRANULARITY({bus_granularity}),')
                        adapter_impls.append(f'\t.SLAVE_ADR_BITS({component.address_size}),')
                        adapter_impls.append(f'\t.SLAVE_PORT_SIZE({component.port_size}),')
                        adapter_impls.append(f'\t.SLAVE_GRANULARITY({component.granularity})')
                        adapter_impls.append(f') wb_adapter_slave_{module_name(component.name)}_to_bus (')
                        adapter_impls.append(f'\t.master_m({comp_name}),')
                        adapter_impls.append(f'\t.slave_s({module_name(component.name)}_so)')
                    adapter_impls.append(f');')
            return adapted_names
        adapted_names = {}
        adapted_names |= adapt(self.bus.masters, True)
        adapted_names |= adapt(self.bus.slaves, False)
        
        if len(adapter_decls)>0:
            impl.append(f'')
            impl.append(f'')
            impl.append(f'/////////////////////////////////////////////////////////////')
            impl.append(f'// bus size adaptation')
            impl.append(f'')
            impl.append(f'')
            impl.extend(adapter_decls)
        if len(adapter_impls)>0:
            impl.append(f'')
            impl.extend(adapter_impls)
        
        impl.append(f'')
        impl.append(f'')

        if self.bus.topology == WbBusTopology.SharedBus:
                
            if len(self.bus.masters) == 1:
                master = self.bus.masters[0]

                impl.append(f'/////////////////////////////////////////////////////////////')
                impl.append(f'// single master')
                impl.append(f'')
                impl.append(f'')
                impl.append(f'assign bus_adr_l = {adapted_names[master.name]}.adr;')
                impl.append(f'assign bus_dat_ms_l = {adapted_names[master.name]}.dat_i;')
                impl.append(f'assign {adapted_names[master.name]}.dat_o = bus_dat_sm_l;')
                impl.append(f'assign bus_sel_l = {adapted_names[master.name]}.sel;')
                impl.append(f'assign bus_stb_l = {adapted_names[master.name]}.stb;')
                impl.append(f'assign bus_cyc_l = {adapted_names[master.name]}.cyc;')
                impl.append(f'assign bus_we_l = {adapted_names[master.name]}.we;')
                impl.append(f'assign {adapted_names[master.name]}.ack = bus_ack_l;')
                impl.append(f'assign {adapted_names[master.name]}.err = bus_err_l;')
                impl.append(f'assign {adapted_names[master.name]}.rty = bus_rty_l;')
            
            else:
                m_cycs = [f'{adapted_names[m.name]}.cyc' for m in self.bus.masters]

                impl.append(f'/////////////////////////////////////////////////////////////')
                impl.append(f'// multi-master arbiter')
                impl.append(f'')
                impl.append(f'')
                impl.append(f'wire[{len(self.bus.masters)-1}:0] arbiter_grant_w;')
                impl.append(f'')
                impl.append(f'')
                impl.append(f'wb_bus_arbiter #(')
                impl.append(f'\t.N({len(self.bus.masters)})')
                impl.append(f') arbiter_inst (')
                impl.append(f'    .clk_i(clk_i),')
                impl.append(f'    .rst_i(rst_i),')
                impl.append(f'\t.cyc_i({{ { ", ".join(reversed(m_cycs)) } }}),')
                impl.append(f'    .cyc_common_o(bus_cyc_l),')
                impl.append(f'\t.gnt_o(arbiter_grant_w)')
                impl.append(f');')
                impl.append(f'')
                impl.append(f'')
                impl.append(f'always_comb begin')
                impl.append(f'\t')
                for i,master in enumerate(self.bus.masters):
                    adr_hi,_ = get_adr_bits(master)
                    if i==0:
                        impl.append(f'\tif (arbiter_grant_w[{i}]) begin')
                    elif i==len(self.bus.masters)-1:
                        impl.append(f'\tend else begin')
                    else:
                        impl.append(f'\tend else if (arbiter_grant_w[{i}]) begin')
                    if adr_hi==bus_adr_hi:
                        impl.append(f'\t\tbus_adr_l <= {adapted_names[master.name]}.adr;')
                    else:
                        impl.append(f'\t\tbus_adr_l <= {{ {bus_adr_hi-adr_hi}\'b0, {adapted_names[master.name]}.adr }};')
                    impl.append(f'\t\tbus_dat_ms_l <= {adapted_names[master.name]}.dat_ms;')
                    impl.append(f'\t\tbus_sel_l <= {adapted_names[master.name]}.sel;')
                    impl.append(f'\t\tbus_stb_l <= {adapted_names[master.name]}.stb;')
                    impl.append(f'\t\tbus_we_l <= {adapted_names[master.name]}.we;')
                impl.append(f'\tend')
                impl.append(f'\t')
                for i,master in enumerate(self.bus.masters):
                    impl.append(f'\t{adapted_names[master.name]}.ack <= bus_ack_l & arbiter_grant_w[{i}];')
                    impl.append(f'\t{adapted_names[master.name]}.err <= bus_err_l & arbiter_grant_w[{i}];')
                    impl.append(f'\t{adapted_names[master.name]}.rty <= bus_rty_l & arbiter_grant_w[{i}];')
                    impl.append(f'\t')
                impl.append(f'end')
                impl.append(f'')
                impl.append(f'')
                for master in self.bus.masters:
                    impl.append(f'assign {adapted_names[master.name]}.dat_sm = bus_dat_sm_l;')

            impl.append(f'')
            impl.append(f'')

            if len(self.bus.slaves)==1:
                slave = self.bus.slaves[0]
                
                impl.append(f'/////////////////////////////////////////////////////////////')
                impl.append(f'// single slave')
                impl.append(f'')
                impl.append(f'')
                impl.append(f'assign {adapted_names[slave.name]}.adr = bus_adr_l;')
                impl.append(f'assign {adapted_names[slave.name]}.dat_o = bus_dat_ms_l;')
                impl.append(f'assign bus_dat_sm_l = {adapted_names[slave.name]}.dat_i;')
                impl.append(f'assign {adapted_names[slave.name]}.sel = bus_sel_l;')
                impl.append(f'assign {adapted_names[slave.name]}.stb = bus_stb_l;')
                impl.append(f'assign {adapted_names[slave.name]}.we = bus_we_l;')
                impl.append(f'assign {adapted_names[slave.name]}.cyc = bus_cyc_l;')
                impl.append(f'assign bus_ack_l = {adapted_names[slave.name]}.ack;')
                impl.append(f'assign bus_err_l = {adapted_names[slave.name]}.err;')
                impl.append(f'assign bus_rty_l = {adapted_names[slave.name]}.rty;')

            else:
                impl.append(f'/////////////////////////////////////////////////////////////')
                impl.append(f'// multi-slave demux')
                impl.append(f'')
                impl.append(f'logic[{len(self.bus.slaves)-1}:0] addrcomp_en_l;')
                impl.append(f'')
                
                impl.append(f'always_comb begin')
                slave_addr_mask = 0
                for slave in self.bus.slaves:
                    slave_addr_mask |= slave.get_base_address()
                for i,slave in enumerate(self.bus.slaves):
                    ee = 'end else ' if i>0 else ''
                    impl.append(f'\t{ee}if ((bus_adr_l & \'h{slave_addr_mask>>bus_adr_lo:X}) == \'h{slave.get_base_address()>>bus_adr_lo:X}) begin')
                    impl.append(f'\t\taddrcomp_en_l <= {len(self.bus.slaves)}\'b{1<<i:0{len(self.bus.slaves)}b}; // select {slave.name}')
                impl.append(f'\tend else begin')
                impl.append(f'\t\taddrcomp_en_l <= {len(self.bus.slaves)}\'b{0:0{len(self.bus.slaves)}b}; // de-select all')
                impl.append(f'\tend')
                impl.append(f'end')

                impl.append(f'')
                impl.append(f'')
                impl.append(f'always_comb begin')
                impl.append(f'')
                for i,slave in enumerate(self.bus.slaves):
                    impl.append(f'\t{adapted_names[slave.name]}.stb <= bus_stb_l & addrcomp_en_l[{i}];')
                impl.append(f'\t')
                for i,slave in enumerate(self.bus.slaves):
                    if i==0:
                        impl.append(f'\tif (addrcomp_en_l[{i}]) begin')
                    elif i==len(self.bus.slaves)-1:
                        impl.append(f'\tend else begin')
                    else:
                        impl.append(f'\tend else if (addrcomp_en_l[{i}]) begin')
                    impl.append(f'\t\tbus_dat_sm_l <= {adapted_names[slave.name]}.dat_sm;')
                    impl.append(f'\t\tbus_ack_l <= {adapted_names[slave.name]}.ack;')
                    impl.append(f'\t\tbus_err_l <= {adapted_names[slave.name]}.err;')
                    impl.append(f'\t\tbus_rty_l <= {adapted_names[slave.name]}.rty;')
                impl.append(f'\tend')
                impl.append(f'\t')
                impl.append(f'end')
                for slave in self.bus.slaves:
                    impl.append(f'')
                    impl.append(f'')
                    impl.append(f'assign {adapted_names[slave.name]}.adr = bus_adr_l[{bus_adr_lo+slave.address_size-1}:{bus_adr_lo}];')
                    impl.append(f'assign {adapted_names[slave.name]}.dat_ms = bus_dat_ms_l;')
                    impl.append(f'assign {adapted_names[slave.name]}.sel = bus_sel_l;')
                    impl.append(f'assign {adapted_names[slave.name]}.we  = bus_we_l;')
                    impl.append(f'assign {adapted_names[slave.name]}.cyc = bus_cyc_l;')
        
        elif self.bus.topology == WbBusTopology.Crossbar:

            slave_adr_mask = 0
            for slave in self.bus.slaves:
                slave_adr_mask |= slave.get_base_address()
            slave_adr_hi = 64
            while slave_adr_mask & (1<<slave_adr_hi) == 0:
                slave_adr_hi -= 1
            slave_adr_lo = 1
            while slave_adr_mask & (1<<slave_adr_lo) == 0:
                slave_adr_lo += 1
            
            impl.append(f'// DEBUG: slave_adr_mask=0x{slave_adr_mask:X}')

            # TODO: address_slice_* and local_address_slice_* seem to be wrong 

            impl.append(f'/////////////////////////////////////////////////////////////')
            impl.append(f'// crossbar matrix')
            impl.append(f'')
            impl.append(f'localparam address_slice_high = {slave_adr_hi};')
            impl.append(f'localparam address_slice_low = {slave_adr_lo};')
            impl.append(f'localparam address_size = address_slice_high - address_slice_low + 1;')
            impl.append(f'')
            impl.append(f'localparam local_address_slice_high = {slave_adr_lo-1};')
            impl.append(f'localparam local_address_slice_low = {bus_adr_lo};')
            impl.append(f'')
            for slave in self.bus.slaves:
                impl.append(f'localparam address_{signal_name(slave.name)} = {slave_adr_hi-slave_adr_lo+1}\'h{(slave.get_base_address() & slave_adr_mask)>>slave_adr_lo};')
            impl.append(f'')
            impl.append(f'')
            impl.append(f'// arbiter')
            impl.append(f'')

            n_masters = len(self.bus.masters)
            n_slaves = len(self.bus.slaves)
            impl.append(f'logic master_cyc_w[{n_masters-1}:0];')
            impl.append(f'logic[address_size-1:0] master_adr_w[{n_masters-1}:0];')
            impl.append(f'logic[address_size-1:0] slave_addresses_w[{n_slaves-1}:0];')
            impl.append(f'logic master_grant_w[{n_masters-1}:0];')
            impl.append(f'logic[{n_slaves-1}:0] master_ssel_w[{n_masters-1}:0];')
            impl.append(f'')

            for i,master in enumerate(self.bus.masters):
                impl.append(f'assign master_cyc_w[{i}] = {adapted_names[master.name]}.cyc;')
            for i,master in enumerate(self.bus.masters):
                impl.append(f'assign master_adr_w[{i}] = {adapted_names[master.name]}.adr[address_slice_high:address_slice_low];')
            for i,slave in enumerate(self.bus.slaves):
                impl.append(f'assign slave_addresses_w[{i}] = address_{signal_name(slave.name)};')
            impl.append(f'')
            impl.append(f'wb_crossbar_arbiter #(')
            impl.append(f'\t.master_count({n_masters}),')
            impl.append(f'\t.slave_count({n_slaves}),')
            impl.append(f'\t.address_bits({slave_adr_hi-slave_adr_lo+1})')
            impl.append(f') wb_crossbar_arbiter_inst (')
            impl.append(f'\t.clk_i(clk_i),'),
            impl.append(f'\t.rst_i(rst_i),')
            impl.append(f'\t.master_cyc_i(master_cyc_w),')
            impl.append(f'\t.master_adr_i(master_adr_w),')
            impl.append(f'\t.slave_addresses_i(slave_addresses_w),')
            impl.append(f'\t.master_grant_o(master_grant_w),')
            impl.append(f'\t.master_ssel_o(master_ssel_w)')
            impl.append(f');')
            impl.append(f'')
            for i,master in enumerate(self.bus.masters):
                impl.append(f'logic {adapted_names[master.name]}_grant_w;')
            for i,master in enumerate(self.bus.masters):
                impl.append(f'logic[{n_slaves-1}:0] {adapted_names[master.name]}_ssel_w;')
            impl.append(f'')
            for i,master in enumerate(self.bus.masters):
                impl.append(f'assign {adapted_names[master.name]}_grant_w = master_grant_w[{i}];')
            for i,master in enumerate(self.bus.masters):
                impl.append(f'assign {adapted_names[master.name]}_ssel_w = master_ssel_w[{i}];')

            impl.append('')
            impl.append(f'// mux logic')
            impl.append(f'// need an explicit sensitivity list, all other approaches make ModelSim crash or throw errors...')

            senslist = []
            for master in self.bus.masters:
                senslist.append(f'{adapted_names[master.name]}.adr, {adapted_names[master.name]}.dat_ms')
                senslist.append(f'{adapted_names[master.name]}.sel, {adapted_names[master.name]}.stb')
                senslist.append(f'{adapted_names[master.name]}.cyc, {adapted_names[master.name]}.we')
            for slave in self.bus.slaves:
                senslist.append(f'{adapted_names[slave.name]}.dat_sm, {adapted_names[slave.name]}.ack')
                senslist.append(f'{adapted_names[slave.name]}.err, {adapted_names[slave.name]}.rty')
            for master in self.bus.masters:
                senslist.append(f'{adapted_names[master.name]}_grant_w, {adapted_names[master.name]}_ssel_w')
            sensitivity = ',\n\t'.join(senslist)
            impl.append(f'always @({sensitivity}) begin')
            
            impl.append(f'\t')
            impl.append(f'\t// default assignments for idle masters/slaves')
            for master in self.bus.masters:
                impl.append(f'\t{adapted_names[master.name]}.dat_sm <= \'x;')
                impl.append(f'\t{adapted_names[master.name]}.ack <= 0;')
                impl.append(f'\t{adapted_names[master.name]}.err <= 0;')
                impl.append(f'\t{adapted_names[master.name]}.rty <= 0;')
            for slave in self.bus.slaves:
                impl.append(f'\t{adapted_names[slave.name]}.adr <= \'0;')
                impl.append(f'\t{adapted_names[slave.name]}.dat_ms <= \'x;')
                impl.append(f'\t{adapted_names[slave.name]}.sel <= \'x;')
                impl.append(f'\t{adapted_names[slave.name]}.stb <= 0;')
                impl.append(f'\t{adapted_names[slave.name]}.cyc <= 0;')
                impl.append(f'\t{adapted_names[slave.name]}.we <= 1\'bx;')

            impl.append(f'')
            impl.append(f'\t// multiplexer')
            for master in self.bus.masters:
                impl.append(f'\tif ({adapted_names[master.name]}_grant_w) begin')
                for i,slave in enumerate(self.bus.slaves):
                    impl.append(f'\t\t{"end else " if i>0 else ""}if ({adapted_names[master.name]}_ssel_w[{i}]) begin')
                    impl.append(f'\t\t\t{adapted_names[slave.name]}.adr[local_address_slice_high:local_address_slice_low] <= {adapted_names[master.name]}.adr[local_address_slice_high:local_address_slice_low];')
                    impl.append(f'\t\t\t{adapted_names[slave.name]}.dat_ms <= {adapted_names[master.name]}.dat_ms;')
                    impl.append(f'\t\t\t{adapted_names[slave.name]}.sel <= {adapted_names[master.name]}.sel;')
                    impl.append(f'\t\t\t{adapted_names[slave.name]}.stb <= {adapted_names[master.name]}.stb;')
                    impl.append(f'\t\t\t{adapted_names[slave.name]}.cyc <= {adapted_names[master.name]}.cyc;')
                    impl.append(f'\t\t\t{adapted_names[slave.name]}.we <= {adapted_names[master.name]}.we;')
                    impl.append(f'\t\t\t{adapted_names[master.name]}.dat_sm <= {adapted_names[slave.name]}.dat_sm;')
                    impl.append(f'\t\t\t{adapted_names[master.name]}.ack <= {adapted_names[slave.name]}.ack;')
                    impl.append(f'\t\t\t{adapted_names[master.name]}.err <= {adapted_names[slave.name]}.err;')
                    impl.append(f'\t\t\t{adapted_names[master.name]}.rty <= {adapted_names[slave.name]}.rty;')
                impl.append(f'\t\tend')
                impl.append(f'\tend')

            impl.append(f'end')

        else:
            raise ValueError()
        
        impl.append(f'')
        impl.append(f'')
        impl.append(f'endmodule')
        impl.append(f'')

        self.implementation = '\n'.join(impl)
        self.instance = '\n'.join(inst)
