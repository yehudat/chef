# Chef

A SystemVerilog design exploration tool for extracting documentation from RTL files.

## Overview

Chef parses SystemVerilog files and extracts information, rendering it
in multiple formats. It uses [pyslang](https://github.com/MikePopoloski/pyslang) for accurate SystemVerilog parsing.

### Features

- Extract module ports and parameters from SystemVerilog files
- Support for nested structs and unions with recursive field expansion
- Multiple output formats: Markdown, CSV, HTML
- Interactive HTML output with regex filter and hide/show toggle
- CLI regex filter to exclude signals/parameters
- Genesis2-generated RTL pattern support

## Requirements

- Docker

## Quick Start

```bash
# Show help
./chef.sh --help

# Parse a SystemVerilog file
./chef.sh fetchif path/to/module.sv
```

## Usage

```bash
./chef.sh [OPTIONS] COMMAND [ARGS]

Commands:
  fetchif FILE    Extract interface (ports and parameters) from a SystemVerilog file

Options:
  --format FORMAT    Output format: markdown (default), csv, html
  --help             Show help message

fetchif Options:
  --strategy NAME    Parser strategy: genesis2 (default), lrm
  --exclude REGEX    Exclude signals/parameters matching regex pattern
```

### Examples

```bash
# Output as Markdown (default)
./chef.sh fetchif design.sv

# Output as CSV
./chef.sh --format csv fetchif design.sv

# Output as HTML (with interactive filter panel)
./chef.sh --format html fetchif design.sv

# Use LRM parsing strategy (instead of default Genesis2)
./chef.sh fetchif --strategy lrm design.sv

# Exclude clock and reset signals
./chef.sh fetchif --exclude "clk|rst" design.sv

# Exclude debug signals
./chef.sh fetchif --exclude "debug_.*" design.sv
```

## Testing

```bash
./test.sh                       # full regression
./test.sh sanity                # quick sanity tests
./test.sh sanity --coverage     # with coverage report
./test.sh regression --coverage # full regression with coverage
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

Interactive HTML page with:
- Collapsible nested struct views
- Regex filter panel (filters as you type)
- "Hide matching" toggle for inverse filtering

## Parser Strategies

| Strategy | Description |
|----------|-------------|
| `genesis2` (default) | Handles Genesis2-generated RTL patterns |
| `lrm` | Standard SystemVerilog LRM parsing |
