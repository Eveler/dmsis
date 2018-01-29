# -*- encoding: utf-8 -*-
import logging
from datetime import date, datetime

from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, func
from sqlalchemy.exc import SQLAlchemyError
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
    object_address = relationship('Addresses', back_populate='adresses')
    documents = relationship('Documents', back_populates='declar')
    legal_entity = relationship('LegalEntity', back_populates='declar')
    person = relationship('Individuals', back_populates='declar')
    param = relationship('Params', back_populates='declar')
    uuid = Column(String, nullable=False, index=True)
    reply_to = Column(String)


class Addresses(Base):
    __tablename__ = 'adresses'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    Postal_Code = Column(String)
    Region = Column(String)
    District = Column(String)
    City = Column(String)
    Urban_District = Column(String)
    Soviet_Village = Column(String)
    Locality = Column(String)
    Street = Column(String)
    House = Column(String)
    Housing = Column(String)
    Building = Column(String)
    Apartment = Column(String)
    Reference_point = Column(String)


class Documents(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    title = Column(String(length=1024), nullable=False)
    number = Column(String(length=50), nullable=False)
    date = Column(Date, nullable=False)
    valid_until = Column(Date)
    file_name = Column(String, nullable=False)
    url = Column(String)
    url_valid_until = Column(Date)
    mime_type = Column(String)
    body = Column(String)
    file_path = Column(String)
    declar_id = Column(Integer, ForeignKey('declars.id'), index=True)
    declar = relationship('Declars', back_populates='documents')


class Params(Base):
    __tablename__ = 'params'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    type = Column(String, nullable=False)
    param_id = Column(String, nullable=False)
    label = Column(String)
    row_number = Column(String)
    col_number = Column(String)
    row_delimiter = Column(String)
    col_delimiter = Column(String)
    value = Column(String, nullable=False)
    declar_id = Column(Integer, ForeignKey('declars.id'), index=True)
    declar = relationship('Declars', back_populates='param')


class LegalEntity(Base):
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String)
    inn = Column(String)
    kpp = Column(String)
    address = relationship('Addresses', back_populate='adresses')
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
    declar_id = Column(Integer, ForeignKey('declars.id'), index=True)
    declar = relationship('Declars', back_populates='legal_entity')


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
    declar_id = Column(Integer, ForeignKey('declars.id'), index=True)
    declar = relationship('Declars', back_populates='person')
    entity = Column(Integer, ForeignKey('entities.id'))


class Phones(Base):
    __tablename__ = 'phones'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    phone = Column(String)


class EntityPhones(Base):
    __tablename__ = 'entityphones'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    entity = Column(Integer, ForeignKey('entities.id'), index=True)
    phone = Column(Integer, ForeignKey('phones.id'))


class IndividualPhones(Base):
    __tablename__ = 'individualphones'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    person = Column(Integer, ForeignKey('persons.id'), index=True)
    phone = Column(Integer, ForeignKey('phones.id'))


class Emails(Base):
    __tablename__ = 'emails'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    email = Column(String)


class EntityEmails(Base):
    __tablename__ = 'entityemails'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    entity = Column(Integer, ForeignKey('entities.id'), index=True)
    email = Column(Integer, ForeignKey('emails.id'))


class IndividualEmails(Base):
    __tablename__ = 'individualemails'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    person = Column(Integer, ForeignKey('persons.id'), index=True)
    email = Column(Integer, ForeignKey('emails.id'))


class Db:
    def __init__(self, dbstr='sqlite:///dmsis.db'):
        self.log = logging.getLogger('db')
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

    def save_declar(self, declar, uuid, reply_to, files):
        a = Addresses(
            Postal_Code=declar.object_address.Postal_Code,
            Region=declar.object_address.Region,
            District=declar.object_address.District,
            City=declar.object_address.City,
            Urban_District=declar.object_address.Urban_District,
            Soviet_Village=declar.object_address.Soviet_Village,
            Locality=declar.object_address.Locality,
            Street=declar.object_address.Street,
            House=declar.object_address.House,
            Housing=declar.object_address.Housing,
            Building=declar.object_address.Building,
            Apartment=declar.object_address.Apartment,
            Reference_point=declar.object_address.Reference_point)
        d = Declars(declar_number=declar.declar_number, service=declar.service,
                    register_date=datetime.strptime(
                        declar.register_date.strftime('%Y-%m-%d'), '%Y-%m-%d'),
                    end_date=datetime.strptime(
                        declar.end_date.strftime('%Y-%m-%d'), '%Y-%m-%d'),
                    object_address=a, uuid=uuid, reply_to=reply_to)
        self.session.add(d)
        docs = []
        for adoc in declar.AppliedDocument:
            from mimetypes import guess_type
            found = files[adoc.file_name]
            mime_type = guess_type(found)[0]
            with open(found, 'rb') as f:
                doc_data = f.read()
            # from encodings.base64_codec import base64_encode
            # doc_data = base64_encode(doc_data)
            doc = Documents(title=adoc.title, number=adoc.number,
                            date=datetime.strptime(
                                adoc.date.strftime('%Y-%m-%d'), '%Y-%m-%d'),
                            valid_until=datetime.strptime(
                                adoc.valid_until.strftime('%Y-%m-%d'),
                                '%Y-%m-%d')
                            if adoc.valid_until else None,
                            file_name=adoc.file_name, mime_type=mime_type,
                            body=doc_data, declar_id=d.id, declar=d)
            self.session.add(doc)
            docs.append(doc)
        for param in declar.Param:
            p = Params(type=param.attr('type'), param_id=param.attr('id'),
                       label=param.attr('label'),
                       row_number=param.attr('rowNumber'),
                       col_number=param.attr('colNumber'),
                       row_delimiter=param.attr('rowDelimiter'),
                       col_delimiter=param.attr('colDelimiter'),
                       value=param, declar_id=d.id, declar=d)
            self.session.add(p)
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.log.warning(
                'Cannot write file to DB. Fallback to file storage.',
                exc_info=True)
            for doc in docs:
                self.session.delete(doc)
            for adoc in declar.AppliedDocument:
                from mimetypes import guess_type
                found = files[adoc.file_name]
                mime_type = guess_type(found)[0]
                maxid = self.session.query(func.max(Documents.id)).first() + 1
                from os import makedirs, path
                if not path.exists('storage'):
                    makedirs('storage')
                from shutil import copy2
                if maxid > 10000:
                    if not path.exists(path.join('storage', str(maxid)[:-4])):
                        makedirs(path.join('storage', str(maxid)[:-4]))
                    file_path = path.join('storage', str(maxid)[:-4],
                                          adoc.file_name)
                    copy2(found, file_path)
                else:
                    file_path = path.join('storage', adoc.file_name)
                    copy2(found, file_path)
                doc = Documents(title=adoc.title, number=adoc.number,
                                date=datetime.strptime(
                                    adoc.date.strftime('%Y-%m-%d'), '%Y-%m-%d'),
                                valid_until=datetime.strptime(
                                    adoc.valid_until.strftime('%Y-%m-%d'),
                                    '%Y-%m-%d')
                                if adoc.valid_until else None,
                                file_name=adoc.file_name, mime_type=mime_type,
                                file_path=file_path, declar_id=d.id, declar=d)
                self.session.add(doc)
            self.session.commit()

    def load_declar(self, uuid):
        r = self.session.query(Declars).filter_by(uuid=uuid).first()
        return r

    def all_declars(self):
        return self.session.query(Declars).all()

    def delete_declar(self, uuid):
        for d in self.session.query(Declars).filter_by(uuid=uuid).all():
            self.session.delete(d.object_address)
            for doc in d.documents:
                if doc.file_path:
                    from os import remove
                    remove(doc.file_path)
                self.session.delete(doc)
            for entity in d.legal_entity:
                self.session.delete(entity)
            for person in d.person:
                self.session.delete(person)
            for param in d.param:
                self.session.delete(param)
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
    with open('logo-ussuriisk.png', 'rb') as f:
        data = f.read()
    from declar import Declar, AppliedDocument

    doc = AppliedDocument(title='dsgsfdgs', number='cvgfdg',
                          date=date(2008, 1, 12), url='dfgdsfgs',
                          file_name='logo-ussuriisk.png')
    # doc.file = 'logo-ussuriisk.png'
    declar = Declar(declar_number='dfgds', service='dfd',
                    register_date=date(2008, 1, 12), end_date=date(2009, 1, 1),
                    AppliedDocument=[doc])
    files = {'logo-ussuriisk.png': 'logo-ussuriisk.png'}
    db.save_declar(declar, 'sfsdf', 'sdfdsfdsf', files)

    r = db.load_declar('sfsdf')
    for doc in r.documents:
        with open('logo-ussuriisk1.png', 'wb') as f:
            f.write(doc.body)
