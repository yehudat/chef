# Chef - SystemVerilog Design Exploration Tool

## Project Overview
Chef is a SystemVerilog design exploration tool. Currently implements ICD (Interface Configuration Document) fetching - extracting port/parameter information as markdown tables. More exploration features planned.

Uses pyslang for parsing (requires Docker as pyslang needs compiled extensions).

## Development Workflow

### Running the Tool
```bash
./chef.sh fetchif path/to/file.sv          # parse SV file, output markdown
./chef.sh --format markdown fetchif file.sv # explicit format
```

### Testing
```bash
./test.sh                    # full regression (33 tests)
./test.sh sanity             # quick sanity (7 tests, ~0.003s)
./test.sh sanity --coverage  # with coverage report
./test.sh regression --coverage
```
Always run `./test.sh sanity` before commits.

### Git Commits
Format: `[chef] [context] max-6-words-comment`
Examples:
- `[chef] [renderer] fix table header column names`
- `[chef] [slang] add nested struct lookup`
- `[chef] [ci] replace codecov with artifacts`

## Architecture

### Key Files
- `chef.py` - CLI entry point, argparse setup
- `svlang/slang_backend.py` - pyslang parsing, type lookup, struct extraction
- `svlang/renderer.py` - markdown table generation
- `svlang/strategy.py` - Genesis2Strategy (default), handles imports
- `svlang/model.py` - data models (StructType, BasicType, StructField, etc.)

### Parsing Strategy
- Default: `genesis2` (handles Genesis2-generated RTL patterns)
- Alternative: `lrm` (standard LRM parsing)

### Features Implemented
- Nested struct recursive parsing and rendering (4-space indentation)
- Genesis2 comment cleaning in Direction column (preserves interface.modport)
- Type column shows actual types (not just width)

## CI/CD
- PR pushes: sanity tests + coverage summary
- Merge to main: full regression + coverage
- Coverage reports saved as GitHub Actions artifacts

## Test Organization
- `tests/test_*.py` - unit tests
- `tests/test_*_integration.py` - integration tests (skipped in sanity)
- `tests/fixtures/` - mini SV files for testing (mini_pkg.sv, mini_module.sv)
