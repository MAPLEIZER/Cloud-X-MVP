from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import app, db

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# app.py fail-closes when DATABASE_URL/authentication settings are absent. By
# importing the application here, migrations always use the exact database URL
# and SQLAlchemy metadata used by the running service.
database_url = app.config["SQLALCHEMY_DATABASE_URI"]
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
target_metadata = db.metadata


def run_migrations_offline():
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
