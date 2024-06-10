from pathlib import Path
import alembic_tools.analyze_revision as ar
from alembic_tools.revision_collection import (
    get_revision_walk,
    get_script_directory,
)


def table_search(table_name, rev_analysis):
    out = []
    cols_added = []
    for stmt in rev_analysis.statements:
        match stmt:
            case ar.CreateTableStatement():
                if stmt.table_name == table_name:
                    out.append("created")
            case ar.AddColumnStatement():
                if stmt.table_name == table_name:
                    cols_added.append(stmt.column_name)
            case ar.ReplaceableStatement():
                pass
            case _:
                pass
    if cols_added:
        cols_added_text = f"column {'s' if len(cols_added) > 1 else ''}"
        cols_added_text += ", ".join(cols_added)
        out.append(f"{cols_added_text} added")
    return out


def replaceable_search(replaceable_name, rev_analysis):
    out = []
    for stmt in rev_analysis.statements:
        match stmt:
            case ar.CreateTableStatement():
                pass
            case ar.AddColumnStatement():
                pass
            case ar.ReplaceableStatement():
                if stmt.replaceable_name == replaceable_name:
                    match stmt.replaceable_op:
                        case ar.ReplaceableOperation.CREATE:
                            out.append("Created")
                        case ar.ReplaceableOperation.DROP:
                            out.append("Dropped")
                        case ar.ReplaceableOperation.REPLACE:
                            out.append("Replaced")
            case _:
                pass
    return out


def search_collection(table_name: str | None, replaceable_name: str | None):
    if table_name is not None:
        print(f"Table: {table_name}")
    if replaceable_name is not None:
        print(f"Replacable entity {replaceable_name}")
    script_folder = get_script_directory()
    # TODO: try to order the graph
    # Traverse the graph and assign numbers to each revision, letting there be ties
    # if there's a branch.
    for rev in list(get_revision_walk(script_folder)):
        p = Path(rev.path)
        rev_analysis = ar.analyze_revision(p)
        if table_name is not None:
            out = table_search(table_name, rev_analysis)
            if out:
                print(f"{rev.revision} {', '.join(out)}")
        if replaceable_name is not None:
            out = replaceable_search(replaceable_name, rev_analysis)
