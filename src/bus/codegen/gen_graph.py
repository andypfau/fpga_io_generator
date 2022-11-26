from ..tools import *

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..structure.types import WbBus, WbMaster, WbSlave

from sys import maxsize
from graphviz import Graph, Digraph


class BusGraphGenerator:

    def __init__(self, bus: 'WbBus', filename: str = 'wb_bus.gv'):
        self.bus = bus
        self.filename = filename
        self.update()
    
    def update(self):

        from ..structure.types import WbBusTopology

        # TODO: draw box (subgraph) around the bus

        if len(self.bus.masters)<1 or len(self.bus.slaves)<1:
            raise ValueError('Bus is empty')

        g = Digraph('G', filename=self.filename)
        
        bus_port_size = max([c.port_size for c in self.bus.masters+self.bus.slaves])
        bus_granularity = min([c.granularity for c in self.bus.masters+self.bus.slaves])

        def m_id(m:'WbMaster'):
            return m.name
        def m_name(m:'WbMaster'):
            return f'Master\n"{m.name}"\n{m.port_size}/{m.granularity}'
        def m_label(m:'WbMaster'):
            return f''
        def s_id(s:'WbSlave'):
            return s.name
        def s_name(s:'WbSlave'):
            return f'Slave\n"{s.name}"\n{s.port_size}/{s.granularity}'
        def s_label(s:'WbSlave'):
            return f'0x{s.base_address:X}'

        g.attr('node', shape='rect')
        for master in self.bus.masters:
            g.attr('node', label=m_name(master))
            g.node(m_id(master))

        g.attr('node', shape='rect', style='rounded')
        for slave in self.bus.slaves:
            g.attr('node', label=s_name(slave))
            g.node(m_id(slave))
        
        g.attr('node', shape='circle')
        if (self.bus.topology == WbBusTopology.SharedBus):
            if len(self.bus.masters)==1 and len(self.bus.slaves)==1:
                mb_name = 'Bus'
                sb_name = 'Bus'
                g.attr('node', label='Bus')
                g.node(mb_name)
            elif len(self.bus.masters)==1 and len(self.bus.slaves)>1:
                mb_name = 'Demux'
                g.attr('node', label=f'Demux\n{bus_port_size}/{bus_granularity}')
                g.node(mb_name)
            elif len(self.bus.masters)>1 and len(self.bus.slaves)==1:
                mb_name = 'Arbiter'
                g.attr('node', label=f'Arbiter\n{bus_port_size}/{bus_granularity}')
                g.node(mb_name)
            else:
                mb_name = 'Arbiter'
                sb_name = 'Demux'
                g.attr('node', label=f'Arbiter\n{bus_port_size}/{bus_granularity}')
                g.node(mb_name)
                g.attr('node', label=f'Demux\n{bus_port_size}/{bus_granularity}')
                g.node(sb_name)
                g.edge(mb_name, sb_name)
        elif (self.bus.topology == WbBusTopology.Crossbar):
                mb_name = 'Crossbar'
                sb_name = 'Crossbar'
                g.attr('node', label=f'Crossbar Matrix\n{bus_port_size}/{bus_granularity}')
                g.node(mb_name)
        else:
            raise ValueError()

        for master in self.bus.masters:
            if master.port_size==bus_port_size and master.granularity==bus_granularity:
                g.edge(m_id(master), mb_name, taillabel=m_label(master))
            else:
                g.attr('node', shape='trapezium' if master.port_size<bus_port_size else 'invtrapezium', style='')
                g.attr('node', label=f'{master.port_size}/{master.granularity}\nto\n{bus_port_size}/{bus_granularity}')
                g.attr('node', fontsize='12')
                id_adapter = m_id(master) + '_adapter'
                g.edge(m_id(master), id_adapter)
                g.edge(id_adapter, mb_name, taillabel=m_label(master))
        for slave in self.bus.slaves:
            if slave.port_size==bus_port_size and slave.granularity==bus_granularity:
                g.edge(sb_name, m_id(slave), headlabel=s_label(slave))
            else:
                g.attr('node', shape='invtrapezium' if slave.port_size<bus_port_size else 'trapezium', style='')
                g.attr('node', label=f'{bus_port_size}/{bus_granularity}\nto\n{slave.port_size}/{slave.granularity}')
                g.attr('node', fontsize='12')
                id_adapter = m_id(slave) + '_adapter'
                g.edge(sb_name, id_adapter)
                g.edge(id_adapter, m_id(slave), headlabel=s_label(slave))

        self.graph = g
