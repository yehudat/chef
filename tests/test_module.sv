// Test fixture for parser unit tests

typedef struct packed {
  logic [7:0] data;
  logic valid;
} payload_t;

module my_mod #(
  parameter integer WIDTH = 8,
  parameter type data_t = payload_t
) (
  input logic clk,
  input logic rst_n,
  input data_t in_data,
  output logic [WIDTH-1:0] out_data
);
endmodule