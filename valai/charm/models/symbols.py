# valai/charm/models/symbols.py

from sqlalchemy import Column, String

from .base import Base

class InjectionSymbol(Base):
    __tablename__ = 'injection_symbols'

    symbol = Column(String, primary_key=True)
    keyword = Column(String)
    value = Column(String)