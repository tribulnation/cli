# Tribulnation CLI

`tn` is a small launcher for independently installed Tribulnation tools.
It owns command discovery; each tool owns its implementation and release cycle.

## Install

Until the first PyPI release:

```sh
python -m pip install 'git+https://github.com/tribulnation/cli.git'
tn --help
```

The launcher alone has no application commands. SDK gateway, engine, and catalogue
integration are separate migrations; this repository does not install those tools.
Install providers in the **same Python environment** as `tn`. Separate pipx or uv
tool environments do not discover one another's plugins; use a shared environment
(or inject providers into the launcher's environment).

## Register a command

Add the launcher to your package's dependencies once it is released, and register
an existing Typer application or Click command/group:

```toml
[project]
dependencies = ["tribulnation-cli>=0.1.0,<1"]

[project.entry-points."tribulnation.commands"]
catalogue = "your_package.cli:app"
```

Until publication, install this repository explicitly alongside your provider;
`0.1.0` in this source tree does not imply an available PyPI release.

For a Typer application:

```python
import typer

app = typer.Typer()


@app.command()
def lookup(query: str):
  """Look up a catalogue entry."""
  print(query)


# Add a callback to retain the group when it has only one subcommand.
@app.callback()
def main():
  """Catalogue commands."""
```

After installing that package:

```sh
tn catalogue lookup BTC
tn catalogue --help
```

1. Entry points must resolve to a `typer.Typer` instance or `click.Command`
   (including `click.Group`), not a function that invokes a CLI.
2. Names start with a lowercase letter and contain lowercase letters, digits
   and hyphens. Duplicate names fail with both providers identified.
3. Root help lists names and providers without importing application modules.
   Only the selected command loads; `tn catalogue --help` shows its own help.
4. Private packages work the same way. Discovery reads installed package
   metadata locally; there is no central command registry or network lookup.
5. Existing console scripts can remain aliases. Only this package should install
   the `tn` executable. Optional extras cannot conditionally register an entry
   point: register it normally and make its missing-dependency error useful.
6. Commands execute installed Python code with the current user's permissions.
   There is no plugin isolation or package installation performed by the launcher.

This uses [Python package entry points](https://packaging.python.org/en/latest/specifications/entry-points/)
and [Click's custom group extension](https://click.palletsprojects.com/en/stable/extending-click/).

## Develop

```sh
python -m pip install -e '.[test]'
pytest
ruff check .
ruff format --check .
python -m build
```

See [the module map](docs/architecture.md). Publishing a PyPI release is a separate
maintainer action; CI only checks and builds the package.
