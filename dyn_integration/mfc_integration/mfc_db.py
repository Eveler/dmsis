# -*- coding: utf-8 -*-
import logging

from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm.session import sessionmaker


__author__ = 'Савенко_МЮ'

Base = declarative_base()


class Max:
    def __init__(self, dbstr):
        engine = create_engine(dbstr, echo=(logging.root.level == logging.DEBUG))
        self.metadata = Base.metadata
        self.metadata.quote_schema = True
        self.metadata.reflect(bind=engine, only=('declars', 'declar_documents', 'docpaths', 'docpaths_documents',
                                                 'documents', 'doctypes', 'declar_clients', 'clients', 'humans',
                                                 'orgs'))
        self.metadata.reflect(bind=engine, only=('operations', 'parameters'), schema='directum_integration')

        self.declars = self.metadata.tables['declars']
        self.declar_documents = self.metadata.tables['declar_documents']
        self.docpaths = self.metadata.tables['docpaths']
        self.docpaths_documents = self.metadata.tables['docpaths_documents']
        self.documents = self.metadata.tables['documents']
        self.doctypes = self.metadata.tables['doctypes']
        self.declar_clients = self.metadata.tables['declar_clients']
        self.clients = self.metadata.tables['clients']
        self.humans = self.metadata.tables['humans']
        self.orgs = self.metadata.tables['orgs']

        self.operations = self.metadata.tables['directum_integration.operations']
        self.parameters = self.metadata.tables['directum_integration.parameters']

        self.session = sessionmaker(bind=engine)()
