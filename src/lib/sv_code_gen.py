from .code_gen import CodeFormatter


class SvCommaList(CodeFormatter):

    @staticmethod
    def Functor(code: str, suffix: str):
        def wrapper(props: "CodeFormatter.LineProperties"):
            result = code
            if props.tags[-1] == 'comma_list':
                # add a comma at the end, except for the last item in the list
                if props.tags_next == props.tags:
                    result += ','
            if suffix:
                result += suffix
            return result
        return wrapper

    def add(self, text, **kwargs):
        # mark this block as a "comma_list"
        super().add(text, **kwargs, tag='comma_list')

    def add_comma(self, code: str, suffix: str = None, **kwargs):
        # mark this block as a "comma_list", and use a wrapper than adds a "," to the end of the line of blocks tagged this way
        super().add(SvCommaList.Functor(code, suffix), **kwargs, tag='comma_list')


class SvCodeFormatter(CodeFormatter):

    def __init__(self, rst: str = 'rst', clk: str = 'clk', rst_active_high: bool = True, clk_rising: bool = True, parent: "SvCodeFormatter" = None):
        super().__init__()
        if parent is not None:
            rst, clk, rst_active_high, clk_rising = parent.rst, parent.clk, parent.rst_active_high, parent.clk_rising
        self.rst, self.clk, self.rst_active_high, self.clk_rising = rst, clk, rst_active_high, clk_rising
        self._module = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ff_reset = None
        super().__exit__(exc_type, exc_val, exc_tb)

    def _finish(self):
        if self._module is not None:
            super().add('endmodule')

    def sub(self, blank_after: bool = True) -> "SvCodeFormatter":
        """ Inserts and returns another formatter object """
        new = SvCodeFormatter(parent=self)
        super().add(new)
        if blank_after:
            super().blank()
        return new

    def module(self, name: str, clk_port: bool = True, rst_port: bool = True, blank_after: bool = True) -> "SvModule":
        if self._module is not None:
            raise RuntimeError('Only one module allowed')
        self._module = SvModule(self, name, clk_port, rst_port)
        super().add(self._module)
        if blank_after:
            super().blank()
        return self._module

    def instance(self, module_name: str, instance_name, clk_port: str = None, rst_port: str = None, blank_after: bool = True) -> "SvInstance":
        inst = SvInstance(self, module_name, instance_name, clk_port, rst_port)
        super().add(inst)
        if blank_after:
            super().blank()
        return inst

    def block(self, header_code: str, suffix: str = '', begin: bool = True, end: bool = True, blank_at_end: bool = True):

        footer = CodeFormatter()
        if begin:
            super().add(f'{header_code} begin' + suffix, indent_after=True)
        else:
            super().add(header_code + suffix, indent_after=True)
        if end:
            footer.add('end', detent_before=True)
        else:
            footer.add(detent_before=True)
        if blank_at_end:
            footer.blank()

        return CodeFormatter.ContextManager(self, footer)

    def ifblock(self) -> "SvIfBlock":
        blk = SvIfBlock(self)
        super().add(blk)
        return blk

    def always_ff(self, blanks: bool = True):
        return SvAlwaysFf(self, self.rst, self.clk, self.rst_active_high, self.clk_rising, blanks)

    def always_comb(self):
        raise NotImplementedError()

    def always_latch_block(self):
        raise NotImplementedError()

    def case(self, header_code: str):

        frame = CodeFormatter()

        super().add(f'case ({header_code})', indent_after=True)
        super().add(frame)
        super().add('endcase', detent_before=True)
        super().blank()

        super()._push(frame)
        return self


class SvAlwaysFf(SvCodeFormatter):

    def __init__(self, parent: "SvCodeFormatter", rst: str, clk: str, rst_active_high: bool, clk_rising: bool, blanks: bool):
        super().__init__()

        if clk is None:
            raise RuntimeError('Cannot create FF with no clock defined')
        rst_edge = "posedge" if rst_active_high else "negedge"
        clk_edge = "posedge" if clk_rising else "negedge"
        if rst:
            alwaysff = f'always_ff @({rst_edge} {rst} or {clk_edge} {clk})'
            resetif = f'if ({"" if rst_active_high else "~"}{rst}) begin'
        else:
            alwaysff = f'always_ff @({clk_edge} {clk}) begin'

        with parent.block(alwaysff):
            if parent.rst is not None:
                parent.begin(resetif)
                self.reset = parent.sub(blank_after=False)
                parent.end_begin('end else begin')
                if blanks:
                    parent.blank()
                parent.add(self)
                if blanks:
                    parent.blank()
                parent.end('end')
            else:
                parent.add(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class SvIfBlock(SvCodeFormatter):

    def __init__(self, parent: "SvCodeFormatter"):
        super().__init__()
        self._parent = parent
        self._first = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _finish(self):
        super().add('end', detent_before=True)

    def ifthen(self, condition: str, suffix: str = '') -> "SvCodeFormatter":
        if self._first:
            super().add(f'if ({condition}) begin{suffix}', indent_after=True)
        else:
            super().add(f'end else if ({condition}) begin{suffix}', detent_before=True, indent_after=True)
        self._first = False
        return self

    def elsethen(self, suffix: str = '') -> "SvCodeFormatter":
        if self._first:
            raise RuntimeError('Else without if')
        super().add(f'end else begin{suffix}', detent_before=True, indent_after=True)
        return self


class SvModule(SvCodeFormatter):

    def __init__(self, parent: "SvCodeFormatter", name: str, clk_port: bool, rst_port: bool):
        super().__init__()
        self._name = name
        self.parameters = SvCommaList()
        self.ports = SvCommaList()
        if parent.clk is not None and clk_port:
            self.ports.add_comma(f'input {parent.clk}')
        if parent.rst is not None and rst_port:
            self.ports.add_comma(f'input {parent.rst}')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _finish(self):
        if self.parameters.get_numbert_of_content_lines() > 0:
            with super().block(f'module {self._name} #(', begin=False, end=False, blank_at_end=False):
                super().add(self.parameters)
            with super().block(') (', begin=False, end=False, blank_at_end=False):
                super().add(self.ports)
            super().add(');')
        else:
            with super().block(f'module {self._name} (', begin=False, end=False, blank_at_end=False):
                super().add(self.ports)
            super().add(');')


class SvInstance(SvCodeFormatter):

    def __init__(self, parent: "SvCodeFormatter", module_name: str, instance_name: bool, rst_port: str = None, clk_port: str = None):
        super().__init__()
        self._module_name, self._instance_name = module_name, instance_name
        self.parameters = SvCommaList()
        self.signals = SvCommaList()
        if parent.clk is not None and clk_port is not None:
            self.map_signal(clk_port, parent.clk)
        if parent.rst is not None and rst_port:
            self.map_signal(rst_port, parent.rst)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def map_parameter(self, parameter_name: str, value: str, comment: str = None):
        self.parameters.add_comma(f'.{parameter_name}({value})', comment)

    def map_signal(self, port_name: str, signal: str = Ellipsis, comment: str = None):
        self.signals.add_comma(f'.{port_name}({port_name if signal is Ellipsis else signal})', comment)

    def _finish(self):
        if self.parameters.get_numbert_of_content_lines() > 0:
            with super().block(f'{self._module_name} #(', begin=False, end=False, blank_at_end=False):
                super().add(self.parameters)
            with super().block(f') {self._instance_name} (', begin=False, end=False, blank_at_end=False):
                super().add(self.signals)
            super().add(');')
        else:
            with super().block(f'{self._module_name} {self._instance_name} (', begin=False, end=False, blank_at_end=False):
                super().add(self.signals)
            super().add(');')
