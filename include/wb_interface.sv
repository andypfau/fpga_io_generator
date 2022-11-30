interface wishbone #(
  
  // The number of available address bits
  // E.g. if ADR_BITS=4, PORT_SIZE=32 and GRANULARITY=8, then
  //   the adr-signal will have size [5:2] (the lower bound, 2, is
  //   determined by port size and granularity, and the upper bound
  //   is ADR_BITS-1 higher.
  parameter ADR_BITS = 16,
  
  // Port size, in bits
  parameter PORT_SIZE = 32,
  
  // Port granularity, in bits
  parameter GRANULARITY = 8
);

  localparam ADR_LO = $clog2(PORT_SIZE/GRANULARITY);
  localparam ADR_HI = ADR_LO+ADR_BITS-1;
  localparam SEL_HI = PORT_SIZE/GRANULARITY-1;

  logic[ADR_HI:ADR_LO] adr;
  logic[PORT_SIZE-1:0] dat_sm;
  logic[PORT_SIZE-1:0] dat_ms;
  logic[SEL_HI:0] sel;
  logic stb;
  logic cyc;
  logic we;
  logic ack;
  logic err;
  logic rty;

  modport master (
    output adr, dat_ms, sel, stb, cyc, we,
    input dat_sm, ack, err, rty
  );

  modport slave (
    input adr, dat_ms, sel, stb, cyc, we,
    output dat_sm, ack, err, rty
  );

endinterface
