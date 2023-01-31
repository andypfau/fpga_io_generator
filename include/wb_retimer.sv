// Wishbone retimer


module wb_retimer (

	input wire clk_i,
	input wire rst_i,
	
	wishbone.slave wb_i,
	wishbone.master wb_o,
	
);


// TODO: implement
// how do I do that...? I believe just registering every signal won't work, right?

logic ack_r;


// Single Write:
//
//    clk    \./'\./'\./'\./'\./'\.
// MASTER      |   |   |   |   |   
//    cyc_i  ../'''''''''''''......
//    we_i   ../'''''''''\.........
//    stb_i  ../'''''''''\.........
//    adr_i  --<:::::::::>-----....
//    ack_o  .........../''\.......
// REG         |   |   |   |   |   
//    ack_r  ........../'''''''\...
// SLAVE       |   |   |   |   |   
//    cyc_i  ....../'''''''\.......
//    we_i   ....../'''''''\.......
//    stb_i  ....../'''''''\.......
//    adr_i  ------<:::::::>-------
//    ack_o  ......./'''''''\......


// Back-to-Back Write:
//
//    clk    \./'\./'\./'\./'\./'\./'\./'\./'\./'\./'\./'\./'\./'\.
// MASTER      |   |   |   |   |   |   |   |   |   |   |   |   |   
//    cyc_i  ../'''''''''''''''
//    we_i   ../'''''''''''''''
//    stb_i  ../'''''''''''''''
//    adr_i  --<:::::::::::X:::
//    ack_o  .........../''
// REG         |   |   |   |   |   |   |   |   |   |   |   |   |   
//    ack_r  ........../'''''''\...
// SLAVE       |   |   |   |   |   |   |   |   |   |   |   |   |   
//    cyc_i  ....../'''''''''''''''
//    we_i   ....../'''''''''''''''
//    stb_i  ....../'''''''''''''''
//    adr_i  ------<:::::::::::X:::
//    ack_o  ......./''''''''''''''

// Single Read:
//
//    clk    \./'\./'\./'\./'\./'\./'\./'\./'\./'\./'\.
// MASTER      |   |   |   |   |   |   |   |   |   |   |   |
//    cyc_i  ../'''''''''''''../'''''''''''''
//    we_i   ../'''''''''\...................
//    stb_i  ../'''''''''\...../'''''''''''''
//    adr_i  --<:::::::::>-----<::::::::::::::::::
//    ack_o  .........../''\............/''
// REG         |   |   |   |   |   |   |   |   |   |   |   |
//    ack_r  ........../'''''''\......./''''
// SLAVE       |   |   |   |   |   |   |   |   |   |   |   |
//    cyc_i  ....../'''''''\......./'''''''''''\..
//    we_i   ....../'''''''\......................
//    stb_i  ....../'''''''\......./'''''''''''\..
//    adr_i  ------<:::::::>-------<:::::::::::>--
//    ack_o  ......./'''''''\....../'''''''''''\.


always_ff @(posedge rst_i or posedge clk_i) begin
    if (rst_i) begin
		wb_i.err <= 0;
		wb_i.rty <= 0;
		wb_i.dat_sm <= '0;
		wb_o.cyc <= 0;
		wb_o.stb <= 0;
		wb_o.we <= 0;
		wb_o.adr <= '0;
		wb_o.dat_ms <= '0;
		wb_o.sel <= '0;
		ack_r <= 0;
    end else begin
		wb_i.err <= wb_o.err;
		wb_i.rty <= wb_o.rty;
		wb_i.dat_sm <= wb_o.dat_sm;
		wb_o.cyc <= wb_i.cyc;
		wb_o.stb <= wb_i.stb;
		wb_o.we <= wb_i.we;
		wb_o.adr <= wb_i.adr;
		wb_o.dat_ms <= wb_i.dat_ms;
		wb_o.sel <= wb_i.sel;
    end
end


assign wb_i.ack = wb_s.stb & ack_r;


endmodule
