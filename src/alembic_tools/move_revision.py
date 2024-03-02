from pathlib import Path
import re
import shutil
from alembic.script import Script
from alembic_tools.revision_collection import (
    get_revision_map,
    get_script_directory,
    get_unambiguous_revision,
)


def find_rev_with_down_revision(
    revision_map: dict[str, Script], rev_to_move_after: str | None
) -> tuple[bool, str]:
    for rev, scr in revision_map.items():
        if scr.down_revision == rev_to_move_after:
            return True, rev
    print(f"Error: Could not find a node that points back to {rev_to_move_after}")
    return False, ""


def change_down_revision(script: Script, down_revision: str | None) -> None:
    print(f"Change {script.revision} to have its down revision be {down_revision}")
    # stash the file
    current_path = Path(script.path)
    shutil.copy2(current_path, Path(".") / "moved_revisions" / current_path.name)
    current_text = current_path.read_text()
    target_text = down_revision if down_revision is not None else ""
    modified_text = re.sub(
        R"Revises:\s?[^\n]*", f"Revises: {target_text}", current_text
    )
    target_text = f"'{down_revision}'" if down_revision is not None else "None"
    modified_text = re.sub(
        R"down_revision: Union\[str, None\] = (?:['\"][a-z0-9]+['\"]|None)",
        f"down_revision: Union[str, None] = {target_text}",
        modified_text,
    )
    current_path.write_text(modified_text)


def move_revision(rev_to_move: str, rev_to_move_after: str) -> int:
    # TODO: Handle if rev_to_move_after is head
    script_folder = get_script_directory()
    revision_map = get_revision_map(script_folder)
    destination_is_base = rev_to_move_after == "base"
    success, rev_to_move = get_unambiguous_revision(rev_to_move, revision_map)
    if not success:
        return 1
    if not destination_is_base:
        success, rev_to_move_after = get_unambiguous_revision(
            rev_to_move_after, revision_map
        )
        if not success:
            print(f"Could not find revision {rev_to_move_after}.")
            return 1
    script_to_move = revision_map[rev_to_move]
    # TODO: print a warning if this the current head

    if not destination_is_base:
        success, currently_after_rev_to_move_after = find_rev_with_down_revision(
            revision_map, rev_to_move_after
        )
        if not success:
            print(f"Could not find revision pointing to the base.")
            return 1
    else:
        success, currently_after_rev_to_move_after = find_rev_with_down_revision(
            revision_map, None
        )
        if not success:
            print(f"Could not find revision after {rev_to_move_after}.")
            return 1
    success, currently_after_rev_to_move = find_rev_with_down_revision(
        revision_map, rev_to_move
    )
    currently_before_rev_to_move = script_to_move.down_revision
    # TODO: Handle branching
    if not isinstance(currently_before_rev_to_move, str):
        print(f"Error: there are multiple revisions pointed to be {rev_to_move}")
        return 1
    (Path(".") / "moved_revisions").mkdir(exist_ok=True)

    change_down_revision(revision_map[currently_after_rev_to_move_after], rev_to_move)
    if destination_is_base:
        change_down_revision(revision_map[rev_to_move], None)
    else:
        change_down_revision(revision_map[rev_to_move], rev_to_move_after)
    change_down_revision(
        revision_map[currently_after_rev_to_move], currently_before_rev_to_move
    )
    return 0
