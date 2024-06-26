import argparse
import os
from pathlib import Path
import sys
from alembic_tools.move_revision import move_revision

from alembic_tools.revision_collection import assign_order, get_script_directory
from alembic_tools.search_collection import search_collection
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
    viz_p.add_argument(
        "--horiz",
        action="store_true",
        help="Lay out graph horizontally (usually vertical)",
    )
    viz_p.add_argument(
        "--open", action="store_true", help="Open image after generating"
    )
    squash_p = subp.add_parser(
        "squash", help="Squash/combine two revisions into a single revision"
    )
    squash_p.add_argument("revision_1", help="First revision to combine")
    squash_p.add_argument("revision_2", help="Second revision to combine")
    squash_p.add_argument("-m", "--message", help="Name of commit")
    move_p = subp.add_parser(
        "move", help="Move a revision to another part of the graph"
    )
    move_p.add_argument("rev_to_move", help="Revision to move")
    move_p.add_argument(
        "rev_to_put_after",
        help="Revision to put the moved revision after. Use base if you want to put it at the beginning.",
    )
    search_p = subp.add_parser("search", help="Search for an entity to see its changes")
    search_p.add_argument("-t", "--table")
    search_p.add_argument("-r", "--replaceable")
    # temp
    subp.add_parser("order")

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
        case "move":
            rev_to_move = args.rev_to_move
            rev_to_put_after = args.rev_to_put_after
            return move_revision(rev_to_move, rev_to_put_after)
        case "search":
            if args.table is None and args.replaceable is None:
                print("Must specify either a table or a replaceable entity")
                return 1
            search_collection(args.table, args.replaceable)
            return 0
        # temp
        case "order":
            folder = get_script_directory()
            print(assign_order(folder))
            return 0
        case _:
            parser.print_help()
            return 1


if __name__ == "__main__":
    sys.exit(main())
