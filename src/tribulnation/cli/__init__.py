"""Discover independently installed Tribulnation commands without eager imports."""

from importlib import metadata
import re

import click

GROUP = 'tribulnation.commands'


def provider(entry: metadata.EntryPoint) -> str:
  """Identify the distribution responsible for a registered command."""
  if entry.dist is not None:
    return entry.dist.metadata['Name'] or entry.value
  return entry.value


class PluginGroup(click.Group):
  """Load only the requested installed Click command or Typer application."""

  def plugins(self, ctx: click.Context) -> dict[str, metadata.EntryPoint]:
    """Discover command metadata once per invocation and reject collisions."""
    key = 'tribulnation.cli.plugins'
    if key not in ctx.meta:
      found: dict[str, metadata.EntryPoint] = {}
      for entry in metadata.entry_points(group=GROUP):
        if not re.fullmatch(r'[a-z][a-z0-9-]*', entry.name):
          raise click.ClickException(
            f'Invalid command name {entry.name!r} from {provider(entry)}. '
            'Use lowercase letters, digits and hyphens, starting with a letter.'
          )
        if entry.name in found:
          raise click.ClickException(
            f'Duplicate command {entry.name!r}: '
            f'{provider(found[entry.name])} and {provider(entry)}. '
            'Uninstall one provider or give its command a different name.'
          )
        found[entry.name] = entry
      ctx.meta[key] = found
    return ctx.meta[key]

  def list_commands(self, ctx: click.Context) -> list[str]:
    """List installed command names in deterministic order."""
    return sorted(self.plugins(ctx))

  def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter):
    """Render root help from metadata without importing plugin modules."""
    entries = self.plugins(ctx)
    if not entries:
      formatter.write_paragraph()
      formatter.write_text(
        'No commands installed. Install a package that registers '
        'tribulnation.commands in this Python environment.'
      )
      return
    with formatter.section('Commands'):
      formatter.write_dl(
        [(name, f'Provided by {provider(entries[name])}') for name in sorted(entries)]
      )

  def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
    """Resolve one plugin, adapting a Typer application to a Click command."""
    entry = self.plugins(ctx).get(cmd_name)
    if entry is None:
      return None
    try:
      command = entry.load()
      if isinstance(command, click.Command):
        return command
      import typer
      from typer.main import get_command

      if isinstance(command, typer.Typer):
        typer_command = get_command(command)

        @click.pass_context
        def invoke_typer(plugin_ctx: click.Context):
          """Let Typer parse its own arguments and handle its own exceptions."""
          return typer_command.main(
            args=plugin_ctx.args,
            prog_name=plugin_ctx.command_path,
            standalone_mode=True,
          )

        return click.Command(
          cmd_name,
          callback=invoke_typer,
          add_help_option=False,
          context_settings={'ignore_unknown_options': True, 'allow_extra_args': True},
        )
    except Exception as exc:
      raise click.ClickException(
        f'Cannot load {cmd_name!r} from {provider(entry)}: {exc}. '
        'Check that the provider and its required extras are installed.'
      ) from exc
    raise click.ClickException(
      f'Invalid plugin {cmd_name!r} from {provider(entry)}: '
      'expected a click.Command or typer.Typer instance.'
    )


@click.command(
  cls=PluginGroup, context_settings={'help_option_names': ['-h', '--help']}
)
@click.version_option(package_name='tribulnation-cli', prog_name='tn')
def app():
  """Run installed Tribulnation tools. Use tn COMMAND --help for command help."""
