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


def build_graph(script_folder: ScriptDirectory) -> dict[str, list[str]]:
    graph = {}
    for revision in script_folder.walk_revisions():
        revision_id = revision.revision
        down_revisions = revision.down_revision
        if down_revisions is None:
            down_revisions = []
        elif isinstance(down_revisions, tuple):
            down_revisions = list(down_revisions)
        elif isinstance(down_revisions, str):
            down_revisions = [down_revisions]
        graph[revision_id] = down_revisions
    return graph


def topological_sort(graph: dict[str, list[str]]) -> list[str]:
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str):
        if node not in visited:
            visited.add(node)
            for neighbor in graph.get(node, []):
                if isinstance(neighbor, list):
                    for sub_neighbor in neighbor:
                        if sub_neighbor not in visited:
                            dfs(sub_neighbor)
                elif neighbor not in visited:
                    dfs(neighbor)
            stack.append(node)

    for node in graph:
        if node not in visited:
            dfs(node)

    return stack[::-1]  # Reverse the stack to get the topological order


def assign_order(script_folder: ScriptDirectory) -> dict[str, int]:
    graph = build_graph(script_folder)
    topo_order = topological_sort(graph)
    order = {revision: idx for idx, revision in enumerate(topo_order)}
    return order
