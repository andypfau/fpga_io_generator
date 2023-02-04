import warnings
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class LineProperties:
    line_idx: int = field(default=0)
    first_line: bool = field(default=False)
    last_line: bool = field(default=False)
    first_in_indentation: bool = field(default=False)
    last_in_indentation: bool = field(default=False)
    tags: list[any] = field(default_factory=list)
    tags_prev: list[any] = field(default_factory=list)
    tags_next: list[any] = field(default_factory=list)


@dataclass
class LineElement:
    content: "CodeFormatter|Callable[CodeFormatter.LineProperties,str]|str|list[str]" = field(default=None)
    indent: int = field(default=0)
    blank: int = field(default=0)
    props: LineProperties = field(default_factory=LineProperties)
    tag: any = field(default=None)


class CodeFormatter:

    def __init__(self):
        self._lines: list[LineElement]
        self._lines = []
        self._context_needed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    class ContextManager:

        def __init__(self, parent: "CodeFormatter", content: "CodeFormatter"):
            self.parent, self.content = parent, content

        def __enter__(self):
            self.parent._context_needed = False
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.parent.add(self.content)

    def _check_context(self):
        if self._context_needed:
            raise RuntimeError('Context manager expected')

    def _finish(self):
        """ Called before code is generated; may be overridden in derived class,
            e.g. to add additional lines at the end, or to post-process lines """
        pass

    def sub(self) -> "CodeFormatter":
        """ Inserts and returns another formatter object """
        self._check_context()
        new = CodeFormatter()
        self.add(new)
        return new

    def add(self, content: "CodeFormatter|callable|str|list[str]" = None, indented: bool = False, indent_before: bool = False, detent_before: bool = False, indent_after: bool = False, detent_after: bool = False, tag: any = None):
        """
        Add one or more lines

        content:   a line, or an array of lines, or another CodeFormatter object, or a callable *
        indented:  indent these lines
        end_sep:   add this string at the end of each lines, except if if the next line is detented (i.e. end-of-block); useful e.g. for comma-separated lists
        block_tag: any object you want to add to the content, in order to later identify it (see LineProperties.block_tags)

        * if it is a callable, it will be called with a <LineProperties> object as argument; must return a string
        """
        self._check_context()
        def add_str(content):
            if content == '':
                self._lines.append(LineElement(blank=1))
            else:
                self._lines.append(LineElement(content, tag=tag))
        if indented:
            indent_before , detent_after = True, True
        if indent_before:
            self._lines.append(LineElement(indent=+1))
        if detent_before:
            self._lines.append(LineElement(indent=-1))
        if content is None:
            pass
        elif isinstance(content, str):
            add_str(content)
        elif callable(content):
            self._lines.append(LineElement(content, tag=tag))
        elif isinstance(content, list):
            for i, line in enumerate(content):
                add_str(line)
        elif isinstance(content, CodeFormatter):
            self._lines.append(content)
        else:
            raise ValueError(f'Unknown line type: <{type(content)}> ({content})')
        if indent_after:
            self._lines.append(LineElement(indent=+1))
        if detent_after:
            self._lines.append(LineElement(indent=-1))

    def block(self, header_content: "CodeFormatter|str|list[str]" = None, footer_content: "CodeFormatter|str|list[str]" = None, **kwargs) -> "CodeFormatter.ContextManager":
        """ Same as add(), but can be used in a <with>-statement; all lines added within the <with> will be indented """

        self._check_context()

        if header_content is not None:
            self.add(header_content, **kwargs)
        self.add(indent_before=True)

        footer = CodeFormatter()
        footer.add(detent_before=True)
        if footer_content is not None:
            footer.add(footer_content, **kwargs)
    
        self._context_needed = True
        return CodeFormatter.ContextManager(self, footer)

    def begin(self, header_content: "CodeFormatter|str|list[str]" = None, **kwargs):
        """ Same as add(), but indents the following lines """
        if header_content is not None:
            self.add(header_content, **kwargs)
        self.add(indent_before=True)

    def end(self, footer_content: "CodeFormatter|str|list[str]" = None, **kwargs):
        """ Same as add(), but detents before this line """
        self.add(detent_before=True)
        if footer_content is not None:
            self.add(footer_content, **kwargs)

    def end_begin(self, header_content: "CodeFormatter|str|list[str]" = None, **kwargs):
        """ Same as add(), but detents before this line, and re-indents the following lines """
        self.end()
        self.begin(header_content)

    def blank(self, n = 1):
        """ Insert a number of blank lines (multiple blanks are combined into the longest of them) """
        self._check_context()
        self._lines.append(LineElement(blank=n))

    def _finish_and_unroll_lines(self):
        self._finish()
        all_lines = []
        def recurse(line):
            nonlocal all_lines
            if isinstance(line, CodeFormatter):
                line._finish()
                for line in line._lines:
                    recurse(line)
            else:
                all_lines.append(line)
        for line in self._lines:
            recurse(line)
        return all_lines

    def _update_line_props(self, lines: "list[LineElement]"):

        block_tags = []
        for line in lines:
            if line.indent > 0:
                block_tags.append(line.tag)
            elif line.indent < 0:
                if len(block_tags) < 1:
                    raise RuntimeError('Too many detents')
                del block_tags[-1]
            elif line.content is not None:
                line.props.tags = block_tags + [line.tag]

        first_found = False
        block_opened = False
        block_tags_prev = []
        for i, line in enumerate(lines):
            if (not first_found) and (line.content):
                line.props.first_line = True
                first_found = True
            if block_opened and line.content:
                line.props.first_in_indentation = True
                block_opened = False
            if line.indent > 0:
                block_opened = True
            if line.content:
                line.props.tags_prev = block_tags_prev
                block_tags_prev = line.props.tags

        last_found = False
        block_closed = False
        block_tags_next = []
        for i, line in reversed(list(enumerate(lines))):
            if (not last_found) and (line.content):
                line.props.last_line = True
                last_found = True
            if block_closed and line.content:
                line.props.last_in_indentation = True
                block_closed = False
            if line.indent < 0:
                block_closed = True
            if line.content:
                line.props.tags_next = block_tags_next
                block_tags_next = line.props.tags

        line_idx = 0
        for line in lines:
            line.props.line_idx = line_idx
            if line.content:
                line_idx += 1
            line_idx += line.blank

        return lines

    def _resolve_callables(self, lines: "list[LineElement]"):
        for line in lines:
            if callable(line.content):
                line.content = line.content(line.props)
        return lines

    def _assemble_code(self, lines: "list[LineElement]", indent, line_end, indent_blank_lines, initial_indent, break_last_line):
        text = ''
        blanks_already_inserted = 0
        indent_level = initial_indent
        first_done = False
        last_done = False
        for line in lines:

            if line.indent != 0:
                indent_level += line.indent
                continue

            if indent_level < 0:
                warnings.warn(f'Negative indent level')

            if line.blank > 0 and not line.props.first_line:
                if (not first_done) or (last_done):
                    continue
                # if multiple blanks touch, only use the longest of them
                n = max(0, line.blank - blanks_already_inserted)
                for _ in range(n):
                    if indent_blank_lines:
                        text += indent*indent_level
                    text += line_end
                blanks_already_inserted += n
                continue

            if line.content:
                text += indent*indent_level + line.content
                if (not line.props.last_line) or break_last_line:
                    text += line_end
                blanks_already_inserted = 0
                first_done = True
                last_done |= line.props.last_line
                continue

        final_level = indent_level - initial_indent
        if final_level != 0:
            warnings.warn(f'Indentation ends at level {final_level:+d}')
        return text

    def get_numbert_of_content_lines(self):
        """ Gets the number of lines that contain actual content (i.e. without blanks); note that this also counts content lines that are zero-length strings """
        return len(self._finish_and_unroll_lines())

    def generate(self, indent = '\t', line_end = '\n', indent_blank_lines = False, initial_indent = 0, break_last_line = True):
        """ Generate formatted code """
        lines = self._finish_and_unroll_lines()
        lines = self._update_line_props(lines)
        lines = self._resolve_callables(lines)
        return self._assemble_code(lines, indent, line_end, indent_blank_lines, initial_indent, break_last_line)
