FPGA I/O Generator
==================

This tool generates code for FPGA-I/O. It generates code for register-type bus-slaves, as well as for entire buses.


## Features

### Register Generation

- Define a flexible register structure in Python
- Generate HDL code for those registers (SystemVerilog)
- Generate SW code to control those registers (C, Python)
- Generate documentation of those registers (Markdown)

<img src="./doc/demo_01-03_sv.png" width="200" />
<img src="./doc/demo_01-03_h.png" width="200" />
<img src="./doc/demo_01-03_md.png" width="300" />


### Bus Generation

- Define a flexible bus structure in Python
- Generate HDL code for this bus (SystemVerilog)
- Generate documentation of this bus (Markdown, Graphviz)

<img src="./doc/demo_02-04.png" width="600" />


## Requirements

Tested with python 3.11.


## How to Get Started

Check out the examples in the `samples` folder.

You will need some HDL files from the `include` folder for synthesis.


## Missing Features

- bus code generator (arbiters, demultiplexers, adapters): not fully working yet
- more intensive testing of generated code
