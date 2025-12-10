// Mini package with nested structs for testing
// Based on sys_pkg.sv and nif_pkg.sv patterns

package mini_pkg;

// Simple typedef aliases (like pkt_pkg.sv)
typedef logic [7:0] byte_t;
typedef logic [15:0] word_t;
typedef logic [31:0] dword_t;

// Level 3: Deepest nested struct
typedef struct packed {
    logic [63:0] data;
    logic [1:0] typ;
    logic sop;
    logic eop;
    logic err;
} inner_trans_s;

// Level 2: Contains inner_trans_s
typedef struct packed {
    logic valid;
    logic [1:0] chan;
} inner_cred_s;

// Level 1: Top-level struct with nested structs (like noc_stream_s)
typedef struct packed {
    inner_trans_s trans;  // nested struct
    inner_cred_s cred;    // nested struct
    logic ini;
    logic par;
    logic dbg;
} outer_stream_s;

// 3-level deep nesting (like mhe_dprsr_hdr_s containing mhe_dprsr_hdr_info_s)
typedef struct packed {
    logic [7:0] offset_hdr;
    logic [6:0] port_id;
    logic eop;
    logic err;
} deep_info_s;

typedef struct packed {
    deep_info_s info;        // nested struct (level 2)
    logic [7:0] padding;
    logic [63:0] data;
} deep_container_s;

// Mixed: struct with both basic types and nested structs
typedef struct packed {
    logic [31:0] basic_field;
    inner_cred_s nested_field;  // nested struct
    logic flag;
} mixed_struct_s;

endpackage : mini_pkg
