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


def search_collection(table_name: str):
    print(f"Table: {table_name}")
    script_folder = get_script_directory()
    # TODO: try to order the graph
    for rev in list(get_revision_walk(script_folder)):
        p = Path(rev.path)
        rev_analysis = ar.analyze_revision(p)
        out = table_search(table_name, rev_analysis)
        if out:
            print(f"{rev.revision} {', '.join(out)}")
