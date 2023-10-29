# valai/charm/loader.py

import logging
import os
import pandas as pd
from sqlalchemy import text

from .database import DatabaseManager
from .models import Base, Character, CharacterTrait, CharacterSymbol, InjectionSymbol, CharacterQuest, WorldLocation

logger = logging.getLogger(__name__)

class CsvLoader(object):
    """
    CsvLoader class for loading data from CSV files into database tables.

    Attributes:
        FILE_LIST (list): List of files to be loaded.
        TABLE_LIST (list): List of tables to be loaded.
    """
    FILE_LIST = ['InjectionSymbols', 'Characters', 'CharacterTraits', 'CharacterSymbols', 'CharacterQuests', 'WorldLocations']
    TABLE_LIST = ['injection_symbols', 'characters', 'character_traits', 'character_symbols', 'character_quests', 'locations']

    @classmethod
    def from_db(cls, db : DatabaseManager, data_path : str, **kwargs):
        """
        Factory method to create a CsvLoader instance from a database URI.

        Args:
            database_uri (str): The database URI.
            data_path (str): The path to the directory containing the data files.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            CsvLoader: A CsvLoader instance.
        """
        loader = cls(db, data_path)
        Base.metadata.create_all(db.engine)
        return loader

    def __init__(self, db : DatabaseManager, data_path : str):
        """
        Initialize a CsvLoader instance.

        Args:
            engine (Engine): The SQLAlchemy engine.
            Session (sessionmaker): The SQLAlchemy session factory.
            data_path (str): The path to the directory containing the data files.
        """
        self.data_path = data_path
        self.db = db

    def load(self, tablename : str):
        """
        Load data from a CSV file into a database table.

        Args:
            tablename (str): The name of the table.
        """
        data_path = os.path.join(self.data_path, f"{tablename}.csv")

        # Read the CSV file
        df = pd.read_csv(data_path)

        # Create a new session
        with self.db.get_session() as session:

            # Upsert the records
            for _, row in df.iterrows():
                if tablename == 'InjectionSymbols':
                    record = InjectionSymbol(**row)
                elif tablename == 'Characters':
                    record = Character(**row)
                elif tablename == 'CharacterTraits':
                    record = CharacterTrait(**row)
                elif tablename == 'CharacterSymbols':
                    record = CharacterSymbol(**row)
                    symbol = session.query(CharacterSymbol).filter_by(character_id=record.character_id, keyword=record.keyword, symbol=record.symbol).one_or_none()
                    if symbol is not None:
                        continue
                elif tablename == 'CharacterQuests':
                    record = CharacterQuest(**row)
                    quest = session.query(CharacterQuest).filter_by(character_id=record.character_id, name=record.name).one_or_none()
                    if quest is not None:
                        continue
                elif tablename == 'WorldLocations':
                    record = WorldLocation(**row)
                else:
                    raise ValueError(f"Unknown table: {tablename}")

                session.merge(record)

            # Commit the changes and close the session
            session.commit()
            session.close()

    def load_all_tables(self):
        """
        Load data from CSV files into all tables in TABLE_LIST.
        """
        for tablename in self.FILE_LIST:
            self.load(tablename)

    @classmethod
    def print_tables(cls, db : DatabaseManager, **kwargs):
        """
        Print the contents of all tables.

        Args:
            database_uri (str): The database URI.
        """

        with db.get_session() as session:

            # Loop over each table
            for table_name in cls.TABLE_LIST:
                print(f"\n{table_name}")
                # Execute raw SQL query to fetch all data from the table
                result = session.execute(text(f"SELECT * FROM {table_name}"))
                # Fetch column names from the result
                column_names = result.keys()
                # Print column names
                print("\t".join(column_names))
                # Fetch and print all rows
                for row in result:
                    print("\t".join(str(item) for item in row))

            # Close the session
            session.close()

def load(print_tables : bool = True, **kwargs):
    config = { 'database_uri': 'sqlite:///local/char.db', 'data_path': 'scene/verana', **kwargs }
    db = DatabaseManager.from_config(**config)
    loader = CsvLoader.from_db(db=db, **config)
    loader.load_all_tables()
    if print_tables:
        CsvLoader.print_tables(db=db, **config)

if __name__ == "__main__":
    load()
