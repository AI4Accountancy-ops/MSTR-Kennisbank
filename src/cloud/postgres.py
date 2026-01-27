from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import urlparse, urlunparse

from logger.logger import Logger

logger = Logger.get_logger(__name__)


class PostgresClient:
    def __init__(self, db_uri: str):
        self.engine = create_engine(db_uri)
        self.admin_engine = create_engine(db_uri, isolation_level='AUTOCOMMIT')
        self.db_uri = db_uri

    def create_database(self, db_name: str) -> None:
        try:
            with self.admin_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {db_name};"))
            logger.info(f"Database '{db_name}' created successfully.")
        except SQLAlchemyError as e:
            logger.error(f"Error creating database '{db_name}': {e}")

    def drop_database(self, db_name: str) -> None:
        try:
            with self.admin_engine.connect() as conn:
                conn.execute(text(f"DROP DATABASE IF EXISTS {db_name};"))
            logger.info(f"Database '{db_name}' dropped successfully.")
        except SQLAlchemyError as e:
            logger.error(f"Error dropping database '{db_name}': {e}")

    def _get_db_uri(self, db_name: str) -> str:
        parsed_uri = urlparse(self.db_uri)
        new_path = f"/{db_name}"
        return urlunparse(parsed_uri._replace(path=new_path))

    def add_pgvector_extension(self, db_name: str) -> None:
        try:
            db_uri = self._get_db_uri(db_name)
            engine = create_engine(db_uri, isolation_level='AUTOCOMMIT')
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION vector;"))
            logger.info(f"pgvector extension added to database '{db_name}'.")
        except SQLAlchemyError as e:
            logger.error(f"Error adding pgvector to database '{db_name}': {e}")


