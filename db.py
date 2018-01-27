# -*- encoding: utf-8 -*-
import logging
from datetime import date

from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm.session import sessionmaker

Base = declarative_base()


class Requests(Base):
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    uuid = Column(String, nullable=False, index=True)
    declar_num = Column(String, nullable=False, index=True)
    declar_date = Column(Date)
    directum_id = Column(Integer)
    reply_to = Column(String)
    last_status = Column(String)
    done = Column(Boolean, index=True)


class Declars(Base):
    __tablename__ = 'declars'
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    declar_number = Column(String, nullable=False)
    service = Column(String, nullable=False)
    register_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    object_address = Column(String)
    param = Column(String)
    documents = relationship('Documents', back_populates='declar')
    
    
class Documents(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    title = Column(String(length=1024), nullable=False)
    number = Column(String(length=50), nullable=False)
    date = Column(Date, nullable=False)
    valid_until = Column(Date)
    file_name = Column(String, nullable=False)
    mime_type = Column(String)
    body = Column(String)
    declar_id = Column(Integer, ForeignKey('declars.id'), index=True)
    declar = relationship('Declars', back_populates='documents')
    
    
class LegalEntity(Base):
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String)
    inn = Column(String)
    kpp = Column(String)
    address = Column(String, nullable=False)
    ogrn = Column(String)
    taxRegDoc = Column(String)
    govRegDoc = Column(String)
    govRegDate = Column(Date)
    # phone = xsd.ListElement(String, tagname='phone', minOccurs=0,
    #                         maxOccurs=xsd.UNBOUNDED)
    # email = xsd.ListElement(String, tagname='email', minOccurs=0,
    #                         maxOccurs=xsd.UNBOUNDED)
    bossFio = Column(String)
    buhFio = Column(String)
    bank = Column(String)
    bankAccount = Column(String)
    lastCtrlDate = Column(Date)
    opf = Column(String)
    govRegOgv = Column(String)
    person = Column(Integer)
    declar = Column(Integer, ForeignKey('declars.id'), index=True)
    

class Individuals(Base):
    __tablename__ = 'persons'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    surname = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    patronymic = Column(String)
    address = Column(String, nullable=False)
    fact_address = Column(String)
    # email = xsd.ListElement(String, tagname='email', minOccurs=0,
    #                         maxOccurs=xsd.UNBOUNDED)
    birthdate = Column(Date)
    passport_serial = Column(String)
    passport_number = Column(String)
    passport_agency = Column(String)
    passport_date = Column(Date)
    # phone = xsd.ListElement(String, tagname='phone', minOccurs=0,
    #                         maxOccurs=xsd.UNBOUNDED)
    inn = Column(String)
    sex = Column(String)
    snils = Column(String)
    declar = Column(Integer, ForeignKey('declars.id'), index=True)
    entity = Column(Integer, ForeignKey('entities.id'))
    
    
class Phones(Base):
    __tablename__ = 'phones'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    phone = Column(String)


class EntityPhones(Base):
    __tablename__ = 'entityphones'

    entity = Column(Integer, ForeignKey('entities.id'), index=True)
    phone = Column(Integer, ForeignKey('phones.id'))

class IndividualPhones(Base):
    __tablename__ = 'individualphones'

    person = Column(Integer, ForeignKey('persons.id'), index=True)
    phone = Column(Integer, ForeignKey('phones.id'))


class Emails(Base):
    __tablename__ = 'emails'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    email = Column(String)


class EntityEmails(Base):
    __tablename__ = 'entityemails'

    entity = Column(Integer, ForeignKey('entities.id'), index=True)
    email = Column(Integer, ForeignKey('emails.id'))


class IndividualEmails(Base):
    __tablename__ = 'individualemails'

    person = Column(Integer, ForeignKey('persons.id'), index=True)
    email = Column(Integer, ForeignKey('emails.id'))


class Db:
    def __init__(self, dbstr='sqlite:///dmsis.db'):
        self.engine = create_engine(dbstr,
                                    echo=(logging.root.level == logging.DEBUG))
        Base.metadata.create_all(self.engine, checkfirst=True)
        self.session = sessionmaker(bind=self.engine)()

    def add_update(self, uuid, declar_num, reply_to, status=None,
                   declar_date=None, directum_id=None):
        r = self.session.query(Requests).filter(Requests.uuid == uuid).first()
        if r:
            r.declar_num = declar_num
            r.reply_to = reply_to
            if status:
                r.last_status = status
            if declar_date:
                r.declar_date = declar_date
            if directum_id:
                r.directum_id = directum_id
        else:
            r = Requests(uuid=uuid, declar_num=declar_num, reply_to=reply_to,
                         last_status=status,
                         declar_date=declar_date if declar_date else date.today(),
                         directum_id=directum_id)
            self.session.add(r)
        self.session.commit()

    def all(self):
        return self.session.query(Requests).all()

    def all_not_done(self):
        return self.session.query(Requests).filter(Requests.done != True).all()

    def change_status(self, status, uuid, declar_num):
        if not status:
            raise Exception('status необходимо указать')
        if not uuid:
            raise Exception('uuid необходимо указать')

        if uuid:
            r = self.session.query(Requests).filter_by(uuid=uuid).first()
            r.last_status = status
        elif declar_num:
            r = self.session.query(Requests).filter_by(
                declar_num=declar_num).first()
            r.last_status = status
        self.session.commit()

    def delete(self, uuid):
        if not uuid:
            raise Exception('Необходимо указать UUID запроса')

        r = self.session.query(Requests).filter_by(uuid=uuid).first()
        self.session.delete(r)
        self.session.commit()

    def commit(self):
        self.session.commit()

    def _clear(self):
        for req in self.all():
            self.session.delete(req)
        self.session.commit()
        self.session.execute('VACUUM FULL')

    def __del__(self):
        self.session.execute('VACUUM FULL')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    db = Db()
    db.add_update('gdfgdsgdfg-fdgfsdf-dfgdfsg', '85473h59394',
                  'gdfgdsgdfg-fdgfsdf-dfgdfsg')
    res = db.all()
    print('*' * 80)
    for r in res:
        print(r.id, '|', r.uuid, '|', r.declar_num)
    print('*' * 80)
    db._clear()
