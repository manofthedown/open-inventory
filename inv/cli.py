"""CLI entrypoints for inventory management."""

import sys

import typer

from inv import __version__
from inv.settings import AppDirs, get_settings
from inv.storage.db import init_engine
from inv.storage.orm import Base

app = typer.Typer(help="open-inventory — lightweight barcode inventory system")


@app.command()
def init() -> None:
    """Initialize the database and configuration directories."""
    settings = get_settings()
    db_path = settings.db_path

    typer.echo("Initializing open-inventory...")
    typer.echo(f"  Config: {AppDirs.config_dir()}")
    typer.echo(f"  Data: {AppDirs.data_dir()}")
    typer.echo(f"  Cache: {AppDirs.cache_dir()}")
    typer.echo(f"  Logs: {AppDirs.log_dir()}")
    typer.echo(f"  Database: {db_path}")

    # Create engine and initialize schema
    engine = init_engine(settings)
    Base.metadata.create_all(engine)

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

    typer.echo("✓ Initialization complete!")


@app.command()
def run(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind address"),
    port: int = typer.Option(8765, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload on code changes"),
) -> None:
    """Run the development server."""
    import uvicorn

    from inv.main import create_app

    settings = get_settings()
    app = create_app(settings)

    typer.echo(f"Starting open-inventory v{__version__}...")
    typer.echo(f"Listen: http://{host}:{port}")
    typer.echo(f"Scan page: http://{host}:{port}/scan")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
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
