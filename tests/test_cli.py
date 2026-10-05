"""Verify plugin discovery, lazy imports, command adaptation and error isolation."""

from importlib import metadata
from pathlib import Path
import subprocess
import sys

import click
from click.testing import CliRunner
import pytest
import typer

from tribulnation.cli import app


@pytest.fixture
def plugins(monkeypatch):
  """Provide deterministic installed metadata and track imported commands."""
  entries = []
  objects = {}
  loaded = []
  monkeypatch.setattr(metadata, 'entry_points', lambda **kwargs: entries)

  def load(entry):
    """Resolve one registered object, including simulated broken imports."""
    loaded.append(entry.name)
    value = objects[entry.value]
    if isinstance(value, Exception):
      raise value
    return value

  monkeypatch.setattr(metadata.EntryPoint, 'load', load)

  def register(name, value, target=None):
    """Register a plugin with an independently identifiable entry point."""
    target = target or f'example_{name}:app'
    entries.append(
      metadata.EntryPoint(name=name, value=target, group='tribulnation.commands')
    )
    objects[target] = value

  return register, loaded


def test_empty_help(plugins):
  """A bare installation explains how commands are discovered."""
  result = CliRunner().invoke(app, ['--help'])
  assert result.exit_code == 0
  assert 'No commands installed' in result.output


def test_help_is_lazy_and_sorted(plugins):
  """Broken application imports cannot prevent root help from rendering."""
  register, loaded = plugins
  register('zebra', ImportError('missing optional dependency'))
  register('alpha', object())
  result = CliRunner().invoke(app, ['--help'])
  assert result.exit_code == 0
  assert result.output.index('alpha') < result.output.index('zebra')
  assert loaded == []


def test_click_command_arguments_and_exit_code(plugins):
  """Only the selected plugin loads; arguments and exit codes reach it."""
  register, loaded = plugins

  @click.command()
  @click.argument('value')
  def command(value):
    """Echo a value and return a nonzero application exit status."""
    click.echo(value)
    raise click.exceptions.Exit(7)

  register('echo', command)
  register('broken', ImportError('broken'))
  result = CliRunner().invoke(app, ['echo', 'hello'])
  assert result.exit_code == 7
  assert result.output == 'hello\n'
  assert loaded == ['echo']


def test_typer_group(plugins):
  """Existing Typer groups retain nested commands and help."""
  register, _ = plugins
  commands = typer.Typer()

  @commands.callback()
  def main():
    """Catalogue commands."""

  @commands.command()
  def lookup(query: str):
    """Look up one symbol."""
    typer.echo(query)

  register('catalogue', commands)
  result = CliRunner().invoke(app, ['catalogue', 'lookup', 'BTC'])
  assert result.exit_code == 0, result.output
  assert result.output == 'BTC\n'
  help_result = CliRunner().invoke(app, ['catalogue', '--help'])
  assert help_result.exit_code == 0
  assert 'lookup' in help_result.output


def test_typer_single_command(plugins):
  """Typer's single-command mode is preserved for commands like gateway."""
  register, _ = plugins
  commands = typer.Typer()

  @commands.command()
  def gateway(socket: str = '/tmp/gateway.sock'):
    """Show the selected socket."""
    typer.echo(socket)

  register('gateway', commands)
  result = CliRunner().invoke(app, ['gateway', '--socket', '/tmp/custom.sock'])
  assert result.exit_code == 0, result.output
  assert '/tmp/custom.sock' in result.output


def test_duplicate_providers(plugins):
  """Duplicate names fail before either provider's code is imported."""
  register, loaded = plugins
  register('engine', object(), 'first:app')
  register('engine', object(), 'second:app')
  result = CliRunner().invoke(app, ['--help'])
  assert result.exit_code == 1
  assert 'Duplicate command' in result.output
  assert 'first:app' in result.output and 'second:app' in result.output
  assert loaded == []


@pytest.mark.parametrize('name', ['--help', 'BadName', 'two words', '1bad'])
def test_invalid_names(plugins, name):
  """Malformed registrations fail with an actionable metadata error."""
  register, loaded = plugins
  register(name, object(), 'example:app')
  result = CliRunner().invoke(app, ['--help'])
  assert result.exit_code == 1
  assert 'Invalid command name' in result.output
  assert loaded == []


def test_broken_plugin(plugins):
  """Missing optional dependencies produce a concise selected-command error."""
  register, _ = plugins
  register('gateway', ImportError('No module named aiohttp'))
  result = CliRunner().invoke(app, ['gateway'])
  assert result.exit_code == 1
  assert 'aiohttp' in result.output and 'required extras' in result.output
  assert 'Traceback' not in result.output


def test_invalid_plugin_type(plugins):
  """Entry points cannot accidentally invoke arbitrary factory functions."""
  register, _ = plugins
  register('engine', lambda: None)
  result = CliRunner().invoke(app, ['engine'])
  assert result.exit_code == 1
  assert 'expected a click.Command or typer.Typer' in result.output


def test_unknown_command(plugins):
  """Unknown commands use Click's usage error without loading plugins."""
  _, loaded = plugins
  result = CliRunner().invoke(app, ['missing'])
  assert result.exit_code == 2
  assert 'No such command' in result.output
  assert loaded == []


def test_version(plugins):
  """Version comes from installed distribution metadata."""
  result = CliRunner().invoke(app, ['--version'])
  assert result.exit_code == 0
  assert metadata.version('tribulnation-cli') in result.output


def test_real_entry_point_discovery(tmp_path, monkeypatch):
  """Discover a provider from real dist-info in a fresh Python invocation."""
  dist = tmp_path / 'example_provider-1.0.dist-info'
  dist.mkdir()
  (dist / 'METADATA').write_text('Name: example-provider\nVersion: 1.0\n')
  (dist / 'entry_points.txt').write_text(
    '[tribulnation.commands]\nexample = example_provider:app\n'
  )
  (tmp_path / 'example_provider.py').write_text(
    'import click\n@click.command()\ndef app():\n    click.echo("discovered")\n'
  )
  monkeypatch.setenv('PYTHONPATH', str(tmp_path))
  result = subprocess.run(
    [sys.executable, '-m', 'tribulnation.cli', 'example'],
    capture_output=True,
    text=True,
    check=False,
  )
  assert result.returncode == 0, result.stderr
  assert result.stdout == 'discovered\n'
