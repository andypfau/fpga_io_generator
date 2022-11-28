interface wishbone #(
  parameter ADR_BITS = 16,
  parameter PORT_SIZE = 32,
  parameter GRANULARITY = 8
);

  localparam ADR_LO = $clog2(PORT_SIZE/GRANULARITY);

  logic[ADR_BITS+ADR_LO:ADR_LO] adr;
  logic[PORT_SIZE-1:0] dat_sm;
  logic[PORT_SIZE-1:0] dat_ms;
  logic[GRANULARITY-1:0] sel;
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
