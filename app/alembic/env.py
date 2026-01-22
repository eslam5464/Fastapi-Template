import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, Inspector, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql.ddl import CreateSchema

from app.core.config import settings
from app.core.db import meta
from app.models import *  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = meta


def get_schema_name():
    """Get schema name from environment variable"""
    return settings.postgres_db_schema


def include_name(name, type_, parent_names):
    """
    Determine whether a given database object should be included during migrations.
    :param name: The name of the database object (e.g., table, schema).
    :param type_: The type of the database object (e.g., "table", "schema").
    :param parent_names: A list of parent names, usually empty or None for schemas.
    :return: True if the object should be included, False otherwise.
    """
    if type_ == "schema":
        return name == settings.postgres_db_schema
    else:
        return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=settings.db_url.human_repr(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=get_schema_name(),
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run actual sync migrations.

    :param connection: connection to the database.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=include_name,
        version_table_schema=get_schema_name(),
    )
    inspector: Inspector = inspect(connection)

    if not inspector.has_schema(schema_name=get_schema_name()):
        connection.execute(CreateSchema(get_schema_name()))
        connection.commit()

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_async_engine(settings.db_url.human_repr())

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_migrations_online())
