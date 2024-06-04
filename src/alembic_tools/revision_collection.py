from alembic.script import ScriptDirectory, Script
from alembic.config import Config


def find_revs_that_start_with(
    prefix: str, revision_map: dict[str, Script]
) -> list[str]:
    ret = []
    for rev in revision_map:
        if rev.startswith(prefix):
            ret.append(rev)
    return ret


def get_script_directory() -> ScriptDirectory:
    alembic_config = Config(file_="alembic.ini", ini_section="alembic")
    return ScriptDirectory.from_config(alembic_config)


def get_revision_walk(script_folder: ScriptDirectory):
    return script_folder.walk_revisions()


def get_revision_map(script_folder: ScriptDirectory):
    return {a.revision: a for a in script_folder.walk_revisions()}


def get_unambiguous_revision(rev_to_move, revision_map) -> tuple[bool, str]:
    revs1 = find_revs_that_start_with(rev_to_move, revision_map)
    if len(revs1) == 0:
        print(f"Could not find revision beginning with {rev_to_move}")
        return False, ""
    if len(revs1) > 1:
        print(
            f"Revision {rev_to_move} is ambiguous. Could be any of {', '.join(revs1)}"
        )
        return False, ""
    return True, revs1[0]
