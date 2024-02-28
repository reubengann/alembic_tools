import subprocess
from alembic.config import Config
from alembic.script import ScriptDirectory
from graphviz import Digraph


def is_graphviz_installed():
    try:
        subprocess.run(
            ["dot", "-V"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def visualize_graph_graphviz():
    alembic_config = Config(file_="alembic.ini", ini_section="alembic")
    script = ScriptDirectory.from_config(alembic_config)
    dot = Digraph(format="png")
    for revision in script.walk_revisions():
        dot.node(
            revision.revision,
            label=f"{revision.revision}\n{revision.doc}",
            shape="Msquare",
        )
        if revision.down_revision is None:  # this is the origin
            dot.edge("base", revision.revision)
        elif isinstance(revision.down_revision, str):
            dot.edge(revision.down_revision, revision.revision)
        else:
            for down_revision in revision.down_revision:
                dot.edge(down_revision, revision.revision)
    dot.render("alembic_graph")
