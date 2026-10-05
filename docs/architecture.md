# Architecture

| Module | Responsibility | Allowed imports |
| --- | --- | --- |
| `tribulnation.cli` | Discover command entry points; validate names; lazy-load Click/Typer commands; root help and version | Standard library, Click, Typer |
| `tribulnation.cli.__main__` | Module invocation | `tribulnation.cli` |

The `tribulnation` namespace is shared with separately installed packages.
There is deliberately no `tribulnation/__init__.py`.

Provider packages depend on this launcher. The launcher never depends on SDK,
engine, catalogue, or other application packages. Providers own configuration,
logging, credentials, command behavior, and their own CLI documentation.

The plugin contract is the `tribulnation.commands` entry-point group, with values
resolving to Click commands/groups or Typer applications. It is a public interface;
changes must preserve existing providers or introduce an explicit versioned migration.
