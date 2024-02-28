import argparse
import sys

from alembic_tools.visualize_graph import (
    is_graphviz_installed,
    visualize_graph_graphviz,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    subp = parser.add_subparsers(
        dest="subparser_name",
        help="Your help message",
    )

    subp.add_parser("visualize", help="Visualize the alembic graph")

    args = parser.parse_args()
    match args.subparser_name:
        case "visualize":
            if not is_graphviz_installed():
                print(
                    "Graphviz is not found in the path. Please install it from https://graphviz.org/download/ and make sure to select the option to add it to your path."
                )
                return 1
            print("Vizualizing")
            visualize_graph_graphviz()
            return 0
        case _:
            parser.print_help()
            return 1


if __name__ == "__main__":
    sys.exit(main())
