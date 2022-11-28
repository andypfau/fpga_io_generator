// Generic adapter to connect unequal-size/-granularity Wishbone entitites
// NOT TESTED


module wb_adapter #(

  parameter MASTER_ADR_BITS = 16,
  parameter MASTER_PORT_SIZE = 32, // port size of master, in bits
  parameter MASTER_GRANULARITY = 8, // granularity of master, in bits

  parameter SLAVE_ADR_BITS = 16,
  parameter SLAVE_PORT_SIZE = 8, // port size of slave, in bits
  parameter SLAVE_GRANULARITY = 8 // granularity of master, in bits

) (

  wishbone.slave master_m,
  wishbone.master slave_s

);


  initial begin
    // check if this is a valid configuration for a Wishbone bus
    assert (MASTER_PORT_SIZE==8 || MASTER_PORT_SIZE==16 || MASTER_PORT_SIZE==32 || MASTER_PORT_SIZE==64) else $error("MASTER_PORT_SIZE must be 8, 16, 32 or 64");
    assert (MASTER_GRANULARITY==8 || MASTER_GRANULARITY==16 || MASTER_GRANULARITY==32 || MASTER_GRANULARITY==64) else $error("MASTER_GRANULARITY must be 8, 16, 32 or 64");
    assert (SLAVE_PORT_SIZE==8 || SLAVE_PORT_SIZE==16 || SLAVE_PORT_SIZE==32 || SLAVE_PORT_SIZE==64) else $error("SLAVE_PORT_SIZE must be 8, 16, 32 or 64");
    assert (SLAVE_GRANULARITY==8 || SLAVE_GRANULARITY==16 || SLAVE_GRANULARITY==32 || SLAVE_GRANULARITY==64) else $error("SLAVE_GRANULARITY must be 8, 16, 32 or 64");
    assert (MASTER_PORT_SIZE>=MASTER_GRANULARITY) else $error("MASTER_PORT_SIZE must be >= MASTER_GRANULARITY");
    assert (SLAVE_PORT_SIZE>=SLAVE_GRANULARITY) else $error("SLAVE_PORT_SIZE must be >= SLAVE_GRANULARITY");
  end


  localparam N_SLAVE_SEL_BITS = SLAVE_PORT_SIZE / SLAVE_GRANULARITY;
  localparam N_MASTER_SEL_BITS = MASTER_PORT_SIZE / MASTER_GRANULARITY;

  localparam MASTER_ADR_HI = MASTER_ADR_BITS-1;
  localparam MASTER_ADR_LO = $clog2(MASTER_PORT_SIZE/MASTER_GRANULARITY);
  localparam SLAVE_ADR_HI = SLAVE_ADR_BITS-1;
  localparam SLAVE_ADR_LO = $clog2(SLAVE_PORT_SIZE/SLAVE_GRANULARITY);

  localparam SHRINKER_SEL_BUNDLE = (SLAVE_GRANULARITY > MASTER_GRANULARITY) ? 1 : MASTER_GRANULARITY / SLAVE_GRANULARITY;
  localparam SHRINKER_SEL_STRIDE = (SLAVE_GRANULARITY > MASTER_GRANULARITY) ? SLAVE_GRANULARITY / MASTER_GRANULARITY : 1;

  initial begin
    //$info("SEL: stride=%p, bundle=%p", SHRINKER_SEL_STRIDE, SHRINKER_SEL_BUNDLE);
    assert (SHRINKER_SEL_STRIDE==1) else $warning("SEL: since SLAVE_GRANULARITY > MASTER_GRANULARITY, some master SEL bits will be ignored!");
  end

  
  generate

    if (MASTER_PORT_SIZE >= SLAVE_PORT_SIZE) begin

      //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
      // Master port size is greater than or equal to slave port size
      // Master DAT port can be connected directly to slave, excess data bits are dropped; SEL bits are adapted

      initial begin
        if (MASTER_PORT_SIZE >= SLAVE_PORT_SIZE) 
          $info("Generating a Wishbone bus shrinker");
        else
          $info("Generating a Wishbone bus granularity adapter");
      end

      always_comb begin
        
        // connect address directly; Verilog matches the LSBs automatically
        slave_s.adr <= master_m.adr;

        // connect data directly; Verilog does the zero-padding or truncation for us
        slave_s.dat_ms <= master_m.dat_ms;
        master_m.dat_sm <= slave_s.dat_sm;

        // match up select signals
        for (int i = 0; i < N_SLAVE_SEL_BITS; i++) begin
          slave_s.sel[i*SHRINKER_SEL_STRIDE] <= master_m.sel[i/SHRINKER_SEL_BUNDLE];
          //$info("############ connect S_SEL[%p] <= M_SEL[%p]", i*SHRINKER_SEL_STRIDE, i/SHRINKER_SEL_BUNDLE);
        end

      end

    end else begin

      //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
      // Master port size is less than slave port size
      // A multiplexer is needed to to connect DAT; SEL bits are adapted

      localparam MUX_DAT_WIDTH = MASTER_PORT_SIZE;
      localparam MUX_STATE_COUNT = SLAVE_PORT_SIZE / MASTER_PORT_SIZE;
      localparam MUX_CONTROL_BITS = $clog2(MUX_STATE_COUNT);
      localparam MUX_SEL_WIDTH = N_SLAVE_SEL_BITS / MUX_STATE_COUNT;
      
      logic[63:0] tmp_adr, mux_sel;

      initial begin
        $info("Generating a Wishbone bus expander");
        assert (MASTER_PORT_SIZE>=SLAVE_GRANULARITY) else $error("For an expander, MASTER_PORT_SIZE must be >= SLAVE_GRANULARITY");
        //$info("MUX: MUX_DAT_WIDTH=%p, MUX_SEL_WIDTH=%p, MUX_STATE_COUNT=%p, MUX_CONTROL_BITS=%p", MUX_DAT_WIDTH, MUX_SEL_WIDTH, MUX_STATE_COUNT, MUX_CONTROL_BITS);
      end

      always_comb begin

        // grab off the mux selector bits
        mux_sel = '0;
        mux_sel = master_m.adr[MASTER_ADR_LO+:MUX_CONTROL_BITS];
        
        // adjust address bus width
        tmp_adr = '0;
        tmp_adr = master_m.adr[MASTER_ADR_HI:MASTER_ADR_LO+MUX_CONTROL_BITS];
        slave_s.adr <= '0;
        slave_s.adr <= tmp_adr;

        // route master data out to all slave data in words
        slave_s.dat_ms <= '0;
        for(int i = 0; i < MUX_STATE_COUNT; i++) begin
          slave_s.dat_ms[i*MASTER_PORT_SIZE+:MASTER_PORT_SIZE] <= master_m.dat_ms;
        end

        // use address to mux slave data to slave data
        master_m.dat_sm <= '0;
        for(int i = 0; i < MUX_STATE_COUNT; i++) begin
          if (mux_sel == i)
            master_m.dat_sm <= slave_s.dat_sm[i*MASTER_PORT_SIZE+:MASTER_PORT_SIZE];
        end

        // match up select signals
        slave_s.sel <= '0;
        for(int i = 0; i < MUX_STATE_COUNT; i++) begin
          if (mux_sel == i) begin
            for (int j = 0; j < MUX_SEL_WIDTH; j++) begin
              slave_s.sel[i*MUX_SEL_WIDTH+j*SHRINKER_SEL_STRIDE] <= master_m.sel[j/SHRINKER_SEL_BUNDLE];
            end
          end
        end

      end

    end

  endgenerate


  // route all other signals directly
  assign slave_s.stb = master_m.stb;
  assign slave_s.cyc = master_m.cyc;
  assign slave_s.we = master_m.we;
  assign master_m.ack = slave_s.ack;
  assign master_m.err = slave_s.err;
  assign master_m.rty = slave_s.rty;

endmodule
