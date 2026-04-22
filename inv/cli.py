"""CLI entrypoints for inventory management."""

import sys

import typer

from inv import __version__
from inv.settings import AppDirs, get_settings
from inv.storage.db import init_engine
from inv.storage.migrations import upgrade_to_head

app = typer.Typer(help="open-inventory — lightweight barcode inventory system")


@app.command()
def init() -> None:
    """Initialize the database and configuration directories."""
    settings = get_settings()
    AppDirs.ensure_dirs()
    db_path = settings.db_path

    typer.echo("Initializing open-inventory...")
    typer.echo(f"  Config: {AppDirs.config_dir()}")
    typer.echo(f"  Data: {AppDirs.data_dir()}")
    typer.echo(f"  Cache: {AppDirs.cache_dir()}")
    typer.echo(f"  Logs: {AppDirs.log_dir()}")
    typer.echo(f"  Database: {db_path}")

    # Schema is managed exclusively through Alembic so every environment
    # (dev, test, prod) has a matching `alembic_version` row. Idempotent:
    # running `inventory init` twice no-ops on the second call.
    upgrade_to_head(settings)
    typer.echo("  Schema migrated to head")

    # Engine is needed for the post-migration seed insert below.
    engine = init_engine(settings)

    # Insert default location if it doesn't exist
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        from inv.storage.orm import Location

        existing = session.query(Location).filter_by(name="Main").first()
        if not existing:
            default_location = Location(name="Main", notes="Default storage location")
            session.add(default_location)
            session.commit()
            typer.echo("  Created default location: 'Main'")
        else:
            typer.echo("  Default location 'Main' already exists")

    typer.echo("Initialization complete.")


@app.command()
def run(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind address"),
    port: int = typer.Option(8765, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload on code changes"),
) -> None:
    """Run the development server."""
    import uvicorn

    typer.echo(f"Starting open-inventory v{__version__}...")
    typer.echo(f"Listen: http://{host}:{port}")
    typer.echo(f"Scan page: http://{host}:{port}/scan")

    # When reload is enabled, uvicorn needs an import string (not an app object).
    # Otherwise, pass the app directly for faster startup.
    if reload:
        uvicorn.run(
            "inv.asgi:app",
            host=host,
            port=port,
            reload=True,
            log_level=get_settings().log_level.lower(),
        )
    else:
        from inv.main import create_app

        settings = get_settings()
        app_instance = create_app(settings)
        uvicorn.run(
            app_instance,
            host=host,
            port=port,
            reload=False,
            log_level=settings.log_level.lower(),
        )


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo(f"open-inventory v{__version__}")


def main() -> None:
    """Main CLI entry point."""
    try:
        app()
    except KeyboardInterrupt:
        typer.echo("\nShutdown.", err=True)
        sys.exit(0)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
