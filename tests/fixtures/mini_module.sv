// Mini module for testing nested struct parsing
// Based on ppc_d2d.sv Genesis2 patterns

module mini_module
import mini_pkg::*;(
    // ports for interface 'stream_if.src_mp'
    output outer_stream_s   out_stream,
    output logic            out_valid,

    // ports for interface 'stream_if.snk_mp'
    input var outer_stream_s  in_stream,
    input var logic           in_valid,

    // Port with 3-level nested struct
    input var deep_container_s deep_data,

    // Port with mixed struct (basic + nested)
    output mixed_struct_s   mixed_out,

    // Simple ports
    input var logic         clk,
    input var logic         rst_n
);

// Module body placeholder
assign out_stream = in_stream;
assign out_valid = in_valid;
assign mixed_out.basic_field = 32'h0;
assign mixed_out.nested_field = in_stream.cred;
assign mixed_out.flag = 1'b0;

endmodule : mini_module
