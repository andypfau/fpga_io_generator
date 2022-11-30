// generic Wishbone multi-master/multi-slave crosbar arbiter


module wb_crossbar_arbiter #(

	parameter master_count = 2,
	parameter slave_count  = 2,
	parameter address_bits = 8

	) (

	input wire clk_i,
	input wire rst_i,
	
	// signals from the masters
	input master_cyc_i[master_count-1:0],
	input[address_bits-1:0] master_adr_i[master_count-1:0],
	
	// slave addresses
	input[address_bits-1:0] slave_addresses_i[slave_count-1:0],

	// indicates whether a master is granted, and which slave it is granted
	output master_grant_o[master_count-1:0],
	output[slave_count-1:0] master_ssel_o[master_count-1:0]
	
);


// these signals tell us whether a master is connected to any slave or not
logic master_connected_prev_r[master_count-1:0];
logic master_connected_w[master_count-1:0];

// these signals tell us which slave is connected to a master, if any
logic[address_bits-1:0] master_connected_address_prev_r[master_count-1:0];
logic[address_bits-1:0] master_connected_address_w[master_count-1:0];

logic[slave_count-1:0] master_ssel_w[master_count-1:0];


// crossbar arbitration/routing engine
// for each master, there are 6 input bits (2x 2x adr, cyc, plus a flag)
always_comb begin

	logic master_locked_v[master_count-1:0];
	logic[address_bits-1:0] master_requested_address_v[master_count-1:0];
	logic master_requesting_v[master_count-1:0];
	logic master_granted_v[master_count-1:0];
	logic master_disconnect_v[master_count-1:0];
	logic master_connected_v[master_count-1:0];
	logic[address_bits-1:0] master_next_address_v[master_count-1:0];

	// check all requests
	for (int im = 0; im < master_count; im++) begin
		master_requested_address_v[im] = '0;
		master_requesting_v[im] = 0;
		if (master_cyc_i[im]) begin
			// master requests a connection
			for (int is = 0; is < slave_count; is++) begin
				if (master_adr_i[im] == slave_addresses_i[is]) begin
					// this is the slave the master requests to connect to
					master_requested_address_v[im] = slave_addresses_i[is];
					master_requesting_v[im] = 1;
					break;
				end
			end
		end
	end

	// arbitration; in the case of conflicts, 1st master has highest priority
	for (int im = 0; im < master_count; im++)
		master_granted_v[im] = 0;

	for (int im = 0; im < master_count; im++) begin
		
		master_granted_v[im] = 0;
		master_disconnect_v[im] = 0;

		master_locked_v[im] = master_connected_prev_r[im] && master_cyc_i[im];

		if (master_requesting_v[im] == 1) begin
			// master requested something

			// start by assuming the requested connection is doable
			master_granted_v[im] = 1;

			// ensure no other master is connected to that slave
			for (int im2 = 0; im2 < master_count; im2++) begin
				
				if (im == im2)
					continue; // only compare to other masters

				if (master_requested_address_v[im] == master_requested_address_v[im2]) begin
					// master requested a slave that another master requested to as well

					if (master_granted_v[im2]) begin
						
						// decline, because we just granted it to the other master
						master_granted_v[im] = 0;

					end else begin
						
						// OK, but we must disconnect the other master first
						master_disconnect_v[im2] = 1;

					end
				
				end else if (master_requested_address_v[im] == master_connected_address_prev_r[im2]) begin
					// master requested a slave that another master is already connected to

					if (master_locked_v[im2]) begin
						
						// decline, because the other master still needs the connection
						master_granted_v[im] = 0;

					end else begin
						
						// OK, but we must disconnect the other master first
						master_disconnect_v[im2] = 1;

					end

				end
			end
			
		end else begin
			
			// this collection can be dropped safely
			master_disconnect_v[im] = 1;

		end
	end

	// map slaves to masters, based on arbitration outcome
	for (int im = 0; im < master_count; im++) begin

		if (master_granted_v[im]) begin
			master_connected_v[im] = 1;
			master_next_address_v[im] = master_requested_address_v[im];
		end else if (master_disconnect_v[im]) begin
			master_connected_v[im] = 0;
			master_next_address_v[im] = '0;
		end else begin
			master_connected_v[im] = master_connected_prev_r[im];
			master_next_address_v[im] = master_connected_address_prev_r[im];
		end

	end

	// put variables to wire/regs
	for (int im = 0; im < master_count; im++) begin
		
		if (master_granted_v[im])
			master_connected_w[im] <= 1;
		else if (master_disconnect_v[im])
			master_connected_w[im] <= 0;
		else
			master_connected_w[im] <= master_connected_prev_r[im];
		
		master_connected_address_w[im] <= master_next_address_v[im];

		for (int is = 0; is < slave_count; is++) begin
			if (master_next_address_v[im] == slave_addresses_i[is])
				master_ssel_w[im][is] <= 1;
			else
				master_ssel_w[im][is] <= 0;
		end

	end

end


// register current state
always_ff @(posedge rst_i or posedge clk_i) begin
	if (rst_i) begin
		for (int im = 0; im < master_count; im++) begin
			master_connected_prev_r[im] <= 0;
			master_connected_address_prev_r[im] <= '0;
		end
	end else begin
		for (int im = 0; im < master_count; im++) begin
			master_connected_prev_r[im] <= master_connected_w[im];
			master_connected_address_prev_r[im] <= master_connected_address_w[im];
		end
	end
end


// output renaming
assign master_grant_o = master_connected_w;
assign master_ssel_o = master_ssel_w;


endmodule
