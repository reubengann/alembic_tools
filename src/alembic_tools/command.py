import argparse
import os
from pathlib import Path
import sys

from alembic_tools.visualize_graph import (
    is_graphviz_installed,
    visualize_graph_graphviz,
)
from alembic_tools.squash import squash_commits


def main() -> int:
    parser = argparse.ArgumentParser()
    subp = parser.add_subparsers(
        dest="subparser_name",
        help="Your help message",
    )

    viz_p = subp.add_parser("visualize", help="Visualize the alembic graph")
    viz_p.add_argument("--horiz", action="store_true")
    viz_p.add_argument("--open", action="store_true")
    squash_p = subp.add_parser("squash", help="Squash two commits")
    squash_p.add_argument("revision_1", help="First revision to combine")
    squash_p.add_argument("revision_2", help="Second revision to combine")
    squash_p.add_argument("-m", "--message", help="Name of commit")

    args = parser.parse_args()
    if not Path("./alembic.ini").exists():
        print("Cannot find alembic.ini in the current folder.")
        return 1
    match args.subparser_name:
        case "visualize":
            if not is_graphviz_installed():
                print(
                    "Graphviz is not found in the path. Please install it from https://graphviz.org/download/ and make sure to select the option to add it to your path."
                )
                return 1
            print("Vizualizing")
            visualize_graph_graphviz(horiz=args.horiz)
            if args.open:
                os.startfile("alembic_graph.png")
            return 0
        case "squash":
            rev1 = args.revision_1
            rev2 = args.revision_2
            commit_name = args.message
            return squash_commits(rev1, rev2, commit_name)
        case _:
            parser.print_help()
            return 1


if __name__ == "__main__":
    sys.exit(main())
