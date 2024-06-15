# alembic_tools

Tools for managing and visualizing the alembic graph.

## Pre-requisites

For visualizing the graph, graphviz must be installed in the PATH. You can get it from https://graphviz.org/download/

## Setup

Clone the repository and execute

```bash
pip install ./alembic_tools
```

## Running

All commands should be run in the root of the alembic project (wherever alembic.ini is).

### Visualize

```bash
alembic_tools visualize [--horiz] [--open]
```

This will produce a png file of the graph.

Pass the `--horiz` option to lay out the graph horizontally. Otherwise it will be vertical.

Pass the `--open` option to open the image after running.

### Squash

```bash
alembic_tools squash <revision_1> <revision_2> [-m "name of squashed revision"]
```

This will combine two revisions, setting the new combined revision to <revision_2> and the downgrade revision to the downgrade revision of <revision_1>. The resulting revision requires manually combining of the two revisions.

Use with caution. If any database is currently at <revision_1>, that rev will cease to exist, and a manual SQL statement will have to be issued to restore it to the graph.

Use the `-m` option to set a message. Otherwise it will be blank.

### Move

```bash
alembic_tools move [revision_to_move] [revision_to_place_after]
```

This will reorder the graph so that revision_to_move comes just after revision_to_place_after. This will not
work if revision_to_move has multiple down_revisions. You can use "base" as revision_to_place_after if you want
to move something to the very beginning.

### Search

```bash
alembic_tools search --table [table_name]
alembic_tools search --replaceable [dbo_name]
```

Caveats: your alembic import must be `from alembic import op` (which is the default)

Right now, only finds (for tables)

- create_table
- drop_table
- create_index
- create_foreign_key
- add_column
- drop_column
- alter_column

and for ReplaceableObjects

- create_view
- drop_view
- replace_view
- create_sproc
- drop_sproc
- replace_sproc
- create_func
- drop_func
- replace_func


## Development

Set up the environment:

```bash
pip install pytest pytest-cov black
```

To run code coverage:

```bash
pytest --cov=src test/ --cov-report term-missing
```