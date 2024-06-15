from pathlib import Path
import alembic_tools.analyze_revision as ar
from alembic_tools.revision_collection import (
    assign_order,
    get_revision_walk,
    get_script_directory,
)


def table_search(table_name: str, rev_analysis: ar.Revision):
    out = []
    cols_added = []
    cols_dropped = []
    indexes_added = 0
    fk_tables = []
    cols_altered = []
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
            case ar.DropColumnStatement():
                if stmt.table_name == table_name:
                    cols_dropped.append(stmt.column_name)
            case ar.CreateIndexStatement():
                if stmt.table_name == table_name:
                    indexes_added += 1
            case ar.CreateForeignKeyStatement():
                if stmt.table_name == table_name:
                    fk_tables.append(stmt.referent_table_name)
                elif stmt.referent_table_name == table_name:
                    fk_tables.append(stmt.table_name)
            case ar.DropTableStatement():
                if stmt.table_name == table_name:
                    out.append("dropped")
            case ar.AlterColumnStatement():
                if stmt.table_name == table_name:
                    cols_altered.append(stmt.column_name)
            case _:
                pass
    if cols_added:
        cols_added_text = f"column{'s' if len(cols_added) > 1 else ''} "
        cols_added_text += ", ".join(cols_added)
        out.append(f"{cols_added_text} added")
    if cols_dropped:
        cols_dropped_text = f"column{'s' if len(cols_dropped) > 1 else ''} "
        cols_dropped_text += ", ".join(cols_dropped)
        out.append(f"{cols_dropped_text} dropped")
    if indexes_added > 0:
        idx_text = "indexes" if indexes_added > 1 else "index"
        out.append(f"{indexes_added} {idx_text} created")
    if fk_tables:
        plural = "s" if len(fk_tables) > 1 else ""
        fk_text = f"Created FK{plural} to {', '.join(fk_tables)}"
        out.append(fk_text)
    if cols_altered:
        plural = "s" if len(cols_altered) > 1 else ""
        col_altered_text = f"Column{plural} {', '.join(cols_altered)} altered"
        out.append(col_altered_text)
    return out


def replaceable_search(replaceable_name, rev_analysis) -> list[str]:
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
                            if stmt.replaces is not None:
                                out.append(f"Replaced {stmt.replaces}")
                            else:
                                out.append("Replaced (unknown)")
            case _:
                pass
    return out


def search_collection(table_name: str | None, replaceable_name: str | None):
    if table_name is not None:
        print(f"Table: {table_name}")
    if replaceable_name is not None:
        print(f"Replacable entity {replaceable_name}")
    script_folder = get_script_directory()
    script_order_map = assign_order(script_folder)
    output_lines: list[tuple[str, str, int]] = []
    for rev in list(get_revision_walk(script_folder)):
        p = Path(rev.path)
        rev_analysis = ar.analyze_revision(p)
        if table_name is not None:
            out = table_search(table_name, rev_analysis)
            if out:
                order_num = script_order_map[rev.revision]
                output_lines.append((rev.revision, ", ".join(out), order_num))
        if replaceable_name is not None:
            out = replaceable_search(replaceable_name, rev_analysis)
            if out:
                order_num = script_order_map[rev.revision]
                output_lines.append((rev.revision, ", ".join(out), order_num))
    output_lines.sort(key=lambda x: x[2])
    latest_order_num = max([v[2] for v in output_lines])
    for rev_num, ol, order_num in output_lines:
        latest_maybe = "" if order_num != latest_order_num else " (latest)"
        print(f"{rev_num} {ol}{latest_maybe}")
