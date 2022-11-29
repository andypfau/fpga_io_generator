from ..tools import *
from ..structure.types import WbBus, WbMaster, WbSlave

from sys import maxsize
from graphviz import Graph, Digraph
import os



class BusGraphGenerator:

    def __init__(self, bus: 'WbBus', filename: str = 'wb_bus.gv'):
        self.bus = bus
        self.filename = filename
        
        gen = BusGraphGeneratorHelper(bus, filename)
        self.graph = gen.graph
    

    def get_graph(self) -> Graph:
        """Returns the Graphc as a graphviz object"""

        return self.graph
    

    def save(self, filename: str = None, render: bool = True):
        """
        Saves the graph to a file.
        filename:  Target file
        render:    If True, a graphic is created. The format depends on the file extension of
            filename, e.g. ".pdf" or ".png". If False, the raw dot-file (graphviz format)
            is saved instead.
        """

        if render:
            path_only, ext = os.path.splitext(filename)
            format = ext[1:] # remove the dot
            self.graph.render(path_only, cleanup=True, format=format)
        else:
            self.graph.save(filename)



class BusGraphGeneratorHelper:


    def __init__(self, bus: 'WbBus', filename: str):
        self.bus = bus
        self.filename = filename

        self.bus.check()
        self.update()

    
    def update(self):

        from ..structure.types import WbBusTopology

        # TODO: draw box (subgraph) around the bus

        g = Digraph('G', filename=self.filename)
        g.attr('graph', rankdir='LR', splines='ortho')

        def bus_type_str(n: "WbNode") -> str:
            return f'{n.port_size}/{n.granularity}'
        def m_id(m:'WbMaster'):
            return m.name
        def m_name(m:'WbMaster'):
            return f'{m.name}\n{bus_type_str(m)}'
        def m_label(m:'WbMaster'):
            return f''
        def s_id(s:'WbSlave'):
            return s.name
        def s_name(s:'WbSlave'):
            return f'{s.name}\n{bus_type_str(s)}'
        def s_label(s:'WbSlave'):
            return f'0x{s.get_base_address():X}'
        
        def master_style(g: Graph):
            g.attr('node', shape='rect', style='rounded,filled,bold', fillcolor='HotPink', margin='0.4,0.2')
        def slave_style(g: Graph):
            g.attr('node', shape='rect', style='rounded,filled,bold', fillcolor='Chartreuse', margin='0.4,0.2')
        def bus_style(g: Graph):
            g.attr('node', shape='rect', style='filled', fillcolor='OldLace', margin='0.1')
        def adapter_style(g: Graph):
            g.attr('node', shape='rect', style='filled', fillcolor='LightGrey', margin='0.1')

        
        master_style(g)
        with g.subgraph(name='__all_masters__') as sg:
            g.attr('graph', rank='same')
            for master in self.bus.masters:
                sg.attr('node', label=m_name(master))
                sg.node(m_id(master))

        slave_style(g)
        with g.subgraph(name='__all_slaves__') as sg:
            g.attr('graph', rank='same')
            for slave in self.bus.slaves:
                sg.attr('node', label=s_name(slave))
                sg.node(m_id(slave))
        
        bus_fmt = self.bus.bus_format
        bus_style(g)
        if (self.bus.topology == WbBusTopology.SharedBus):
            if len(self.bus.masters)==1 and len(self.bus.slaves)==1:
                mb_name = sb_name = 'Bus'
                g.attr('node', label='Bus')
                g.node(mb_name)
            elif len(self.bus.masters)==1 and len(self.bus.slaves)>1:
                mb_name = sb_name = 'Demux'
                g.attr('node', label=f'Demux\n{bus_type_str(bus_fmt)}')
                g.node(mb_name)
            elif len(self.bus.masters)>1 and len(self.bus.slaves)==1:
                mb_name = sb_name = 'Arbiter'
                g.attr('node', label=f'Arbiter\n{bus_type_str(bus_fmt)}')
                g.node(mb_name)
            else:
                mb_name = 'Arbiter'
                sb_name = 'Demux'
                g.attr('node', label=f'Arbiter\n{bus_type_str(bus_fmt)}')
                g.node(mb_name)
                g.attr('node', label=f'Demux\n{bus_type_str(bus_fmt)}')
                g.node(sb_name)
                g.edge(mb_name, sb_name)
        elif (self.bus.topology == WbBusTopology.Crossbar):
                mb_name = 'Crossbar'
                sb_name = 'Crossbar'
                g.attr('node', label=f'Crossbar Matrix\n{bus_type_str(bus_fmt)}')
                g.node(mb_name)
        else:
            raise ValueError()

        for master in self.bus.masters:
            adapter = self.bus.get_adapter(master)
            if adapter is None:
                g.attr('edge', minlen='2', labeldistance='3')
                g.edge(m_id(master), mb_name, taillabel=m_label(master))
                g.attr('edge', minlen='1', labeldistance='1')
            
            else:
                adapter_style(g)
                g.attr('node', label=f'{bus_type_str(adapter[0])}\nto\n{bus_type_str(adapter[1])}')
                id_adapter = m_id(master) + '_adapter'
                g.edge(m_id(master), id_adapter)
                
                g.attr('edge', minlen='2', labeldistance='3')
                g.edge(id_adapter, mb_name, taillabel=m_label(master))
                g.attr('edge', minlen='1', labeldistance='1')
        
        for slave in self.bus.slaves:
            adapter = self.bus.get_adapter(slave)
            if self.bus.get_adapter(slave) is None:
                g.attr('edge', minlen='2', labeldistance='3')
                g.edge(sb_name, m_id(slave), headlabel=s_label(slave))
                g.attr('edge', minlen='1', labeldistance='1')
            else:
                adapter_style(g)
                g.attr('node', label=f'{bus_type_str(adapter[1])}\nto\n{bus_type_str(adapter[0])}')
                id_adapter = m_id(slave) + '_adapter'
                g.edge(sb_name, id_adapter)
                
                g.attr('edge', minlen='2', labeldistance='3')
                g.edge(id_adapter, m_id(slave), headlabel=s_label(slave))
                g.attr('edge', minlen='1', labeldistance='1')

        self.graph = g
