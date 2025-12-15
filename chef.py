import argparse
import os
import sys

from svlang.strategy import strategy_registry
from svlang.renderers import renderer_registry


def cmd_fetch_if(args: argparse.Namespace) -> int:
    """Fetch interface (ports + params) and print in specified format.

    The parser strategy can be selected via the ``--strategy`` option
    on the ``fetchif`` command. The output format can be selected via
    the ``--format`` option. Both use registries for extensibility.
    """
    if not getattr(args, "file", None):
        sys.exit("Error: No file provided. Usage: chef.py fetchif FILE")

    if not os.path.isfile(args.file):
        sys.exit(f"Error: File not found: {args.file}")

    strategy = strategy_registry.create(args.strategy)
    strategy.load_design([args.file])
    modules = strategy.get_modules()

    renderer = renderer_registry.create(args.format)

    for mod in modules:
        signals_output = renderer.render_signal_table(mod.ports)
        params_output = renderer.render_parameter_table(mod.parameters)

        # HTML renderer outputs a full page
        if hasattr(renderer, "render_full_page"):
            print(renderer.render_full_page(mod.name, signals_output, params_output))
        else:
            print(f"# Module {mod.name}\n")
            print(signals_output)
            print()
            print(params_output)
            print()

    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chef.py",
        description="Facade for SystemVerilog utilities.",
    )

    # Global options
    parser.add_argument(
        "--format",
        choices=renderer_registry.keys(),
        default="markdown",
        help="Output format (default: markdown).",
    )

    subparsers = parser.add_subparsers(dest="command")

    # fetchif subcommand
    fetch_if = subparsers.add_parser(
        "fetchif",
        help="Fetch interface description (ports and parameters).",
    )
    fetch_if.add_argument(
        "file",
        metavar="FILE",
        help="SystemVerilog file to parse.",
    )
    fetch_if.add_argument(
        "--strategy",
        choices=strategy_registry.keys(),
        default="genesis2",
        help="Parser strategy (default: genesis2).",
    )
    fetch_if.set_defaults(func=cmd_fetch_if)

    return parser


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
