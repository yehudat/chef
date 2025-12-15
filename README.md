# Chef

A SystemVerilog design exploration tool for extracting documentation from RTL files.

## Overview

Chef parses SystemVerilog files and extracts information, rendering it
in multiple formats. It uses [pyslang](https://github.com/MikePopoloski/pyslang) for accurate SystemVerilog parsing.

### Features

- Extract module ports and parameters from SystemVerilog files
- Support for nested structs and unions with recursive field expansion
- Multiple output formats: Markdown, CSV, HTML
- Genesis2-generated RTL pattern support

## Requirements

- Docker

## Quick Start

```bash
# Show help
docker run yehudats/chef:latest --help

# Parse a SystemVerilog file (mount your files into /app)
docker run -v $(pwd):/app yehudats/chef:latest fetchif /app/path/to/module.sv
```

## Usage

```bash
docker run -v $(pwd):/app yehudats/chef:latest [OPTIONS] COMMAND [ARGS]

Commands:
  fetchif FILE    Extract interface (ports and parameters) from a SystemVerilog file

Options:
  --format FORMAT   Output format: markdown (default), csv, html
  --help            Show help message
```

### Examples

```bash
# Output as Markdown (default)
docker run -v $(pwd):/app yehudats/chef:latest fetchif /app/design.sv

# Output as CSV
docker run -v $(pwd):/app yehudats/chef:latest --format csv fetchif /app/design.sv

# Output as HTML
docker run -v $(pwd):/app yehudats/chef:latest --format html fetchif /app/design.sv

# Use LRM parsing strategy (instead of default Genesis2)
docker run -v $(pwd):/app yehudats/chef:latest fetchif --strategy lrm /app/design.sv
```

## Output Formats

### Markdown (default)

GitHub Flavored Markdown tables:

```markdown
# Module my_module

| Signal Name | Type | Direction | Reset Value | Default Value | clk Domain | Description |
|:------------|:-----|:----------|:------------|:--------------|:-----------|:------------|
| clk | logic | input | | | | |
| data_in | logic [31:0] | input | | | | |
| data_out | logic [31:0] | output | | | | |
```

### CSV

Comma-separated values for spreadsheet import.

### HTML

Interactive HTML page with collapsible nested struct views.

## Parser Strategies

| Strategy | Description |
|----------|-------------|
| `genesis2` (default) | Handles Genesis2-generated RTL patterns |
| `lrm` | Standard SystemVerilog LRM parsing |
