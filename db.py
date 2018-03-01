# -*- encoding: utf-8 -*-
import logging
from datetime import date, datetime

from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, func
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm import relationship
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
    object_address = relationship('Addresses')
    object_address_id = Column(ForeignKey('adresses.id'))
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
    declar = relationship('Declars', back_populates='documents')
    declar_id = Column(ForeignKey('declars.id'), index=True)


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
    declar = relationship('Declars', back_populates='param')
    declar_id = Column(ForeignKey('declars.id'), index=True)


class LegalEntity(Base):
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String)
    inn = Column(String)
    kpp = Column(String)
    address = relationship('Addresses')
    address_id = Column(ForeignKey('adresses.id'))
    ogrn = Column(String)
    taxRegDoc = Column(String)
    govRegDoc = Column(String)
    govRegDate = Column(Date)
    phone = relationship('Phones', back_populates='entity')
    email = relationship('Emails', back_populates='entity')
    bossFio = Column(String)
    buhFio = Column(String)
    bank = Column(String)
    bankAccount = Column(String)
    lastCtrlDate = Column(Date)
    opf = Column(String)
    govRegOgv = Column(String)
    person = relationship('Individuals', back_populates='entity')
    person_id = Column(ForeignKey('persons.id'))
    declar = relationship('Declars', back_populates='legal_entity')
    declar_id = Column(ForeignKey('declars.id'))


class Individuals(Base):
    __tablename__ = 'persons'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    surname = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    patronymic = Column(String)
    address_id = Column(ForeignKey('adresses.id'))
    address = relationship('Addresses', foreign_keys=address_id)
    fact_address_id = Column(ForeignKey('adresses.id'))
    fact_address = relationship('Addresses', foreign_keys=fact_address_id)
    email = relationship('Emails', back_populates='person')
    birthdate = Column(Date)
    passport_serial = Column(String)
    passport_number = Column(String)
    passport_agency = Column(String)
    passport_date = Column(Date)
    phone = relationship('Phones', back_populates='person')
    inn = Column(String)
    sex = Column(String)
    snils = Column(String)
    declar = relationship('Declars', back_populates='person')
    declar_id = Column(ForeignKey('declars.id'))
    entity = relationship('LegalEntity', back_populates='person')


class Phones(Base):
    __tablename__ = 'phones'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    phone = Column(String)
    entity = relationship('LegalEntity', back_populates='phone')
    entity_id = Column(ForeignKey('entities.id'))
    person = relationship('Individuals', back_populates='phone')
    person_id = Column(ForeignKey('persons.id'))


class Emails(Base):
    __tablename__ = 'emails'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    email = Column(String)
    entity = relationship('LegalEntity', back_populates='email')
    entity_id = Column(ForeignKey('entities.id'))
    person = relationship('Individuals', back_populates='email')
    person_id = Column(ForeignKey('persons.id'))


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
            r = Requests(
                uuid=uuid, declar_num=declar_num, reply_to=reply_to,
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
        self.session.add(a)
        d = Declars(declar_number=declar.declar_number, service=declar.service,
                    register_date=datetime.strptime(
                        declar.register_date.strftime('%Y-%m-%d'), '%Y-%m-%d'),
                    end_date=datetime.strptime(
                        declar.end_date.strftime('%Y-%m-%d'), '%Y-%m-%d'),
                    object_address=a, uuid=uuid, reply_to=reply_to)
        self.session.add(d)
        for legal_entity in declar.legal_entity:
            a = Addresses(
                Postal_Code=legal_entity.Postal_Code,
                Region=legal_entity.Region,
                District=legal_entity.District, City=legal_entity.City,
                Urban_District=legal_entity.Urban_District,
                Soviet_Village=legal_entity.Soviet_Village,
                Locality=legal_entity.Locality, Street=legal_entity.Street,
                House=legal_entity.House, Housing=legal_entity.Housing,
                Building=legal_entity.Building,
                Apartment=legal_entity.Apartment,
                Reference_point=legal_entity.Reference_point)
            self.session.add(a)
            p = None
            if legal_entity.person:
                person = legal_entity.person
                pa = Addresses(
                    Postal_Code=person.address.Postal_Code,
                    Region=person.address.Region,
                    District=person.address.District, City=person.address.City,
                    Urban_District=person.address.Urban_District,
                    Soviet_Village=person.address.Soviet_Village,
                    Locality=person.address.Locality,
                    Street=person.address.Street,
                    House=person.address.House, Housing=person.address.Housing,
                    Building=person.address.Building,
                    Apartment=person.address.Apartment,
                    Reference_point=person.address.Reference_point)
                self.session.add(pa)
                pfa = None
                if person.fact_address:
                    pfa = Addresses(
                        Postal_Code=person.fact_address.Postal_Code,
                        Region=person.fact_address.Region,
                        District=person.fact_address.District,
                        City=person.fact_address.City,
                        Urban_District=person.fact_address.Urban_District,
                        Soviet_Village=person.fact_address.Soviet_Village,
                        Locality=person.fact_address.Locality,
                        Street=person.fact_address.Street,
                        House=person.fact_address.House,
                        Housing=person.fact_address.Housing,
                        Building=person.fact_address.Building,
                        Apartment=person.fact_address.Apartment,
                        Reference_point=person.fact_address.Reference_point)
                    self.session.add(pfa)
                p = Individuals(
                    surname=person.surname, first_name=person.first_name,
                    patronymic=person.patronymic, address=pa, fact_address=pfa,
                    birthdate=datetime.strptime(
                        person.birthdate.strftime('%Y-%m-%d'), '%Y-%m-%d'),
                    passport_serial=person.passport_serial,
                    passport_number=person.passport_number,
                    passport_agency=person.passport_agency,
                    passport_date=datetime.strptime(
                        person.passport_date.strftime('%Y-%m-%d'),
                        '%Y-%m-%d'), inn=person.inn, sex=person.sex,
                    snils=person.snils)
                for phone in person.phone:
                    pp = Phones(phone=phone, person=p)
                    self.session.add(pp)
                for email in person.email:
                    pe = Emails(email=email, person=p)
                    self.session.add(pe)
            l = LegalEntity(
                name=legal_entity.name, full_name=legal_entity.full_name,
                inn=legal_entity.inn, kpp=legal_entity.kpp,
                address=a, ogrn=legal_entity.ogrn,
                taxRegDoc=legal_entity.taxRegDoc,
                govRegDoc=legal_entity.govRegDoc,
                govRegDate=datetime.strptime(
                    legal_entity.govRegDate.strftime('%Y-%m-%d'),
                    '%Y-%m-%d'), bossFio=legal_entity.bossFio,
                buhFio=legal_entity.buhFio, bank=legal_entity.bank,
                bankAccount=legal_entity.bankAccount,
                lastCtrlDate=datetime.strptime(
                    legal_entity.lastCtrlDate.strftime('%Y-%m-%d'),
                    '%Y-%m-%d'), opf=legal_entity.opf,
                govRegOgv=legal_entity.govRegOgv, person=p, declar=d)
            self.session.add(l)
            for phone in legal_entity.phone:
                ep = Phones(phone=phone, entity=l)
                self.session.add(ep)
            for email in legal_entity.email:
                ee = Emails(email=email, entity=l)
                self.session.add(ee)
        docs = []
        for adoc in declar.AppliedDocument:
            from mimetypes import guess_type
            found = files[adoc.file_name]
            mime_type = guess_type(found)[0]
            doc_data = None
            file_path = None
            from os import path
            if path.getsize(found) > 1000000 - 2048:
                maxid = self.session.query(func.max(Documents.id)).first() + 1
                from os import makedirs
                if not path.exists('storage'):
                    makedirs('storage')
                from shutil import copy2
                if maxid > 10000:
                    file_path = path.join('storage', str(maxid)[:-4])
                    if not path.exists(file_path):
                        makedirs(file_path)
                    file_path = path.join(file_path, adoc.file_name)
                else:
                    file_path = path.join('storage', adoc.file_name)
                copy2(found, file_path)
            else:
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
                            body=doc_data, file_path=file_path, declar_id=d.id,
                            declar=d)
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
        self.session.commit()

    def load_declar(self, uuid):
        r = self.session.query(Declars).filter_by(uuid=uuid).first()
        return r

    def all_declars(self):
        return self.session.query(Declars).all()

    def all_declars_as_xsd(self):
        from declar import AppliedDocument, Declar, Address, LegalEntity, \
            Individual
        declars_info = []
        for declar in self.session.query(Declars).all():
            files = {}
            for doc in declar.documents:
                if doc.body:
                    from tempfile import mkstemp
                    import os
                    fp, file_path = mkstemp()
                    os.close(fp)
                    with open(file_path, 'wb') as f:
                        f.write(doc.body)
                    files[doc.file_name] = file_path
                else:
                    files[doc.file_name] = doc.file_path
            object_address = declar.object_address
            a = Address(
                Postal_Code=object_address.Postal_Code,
                Region=object_address.Region, District=object_address.District,
                City=object_address.City,
                Urban_District=object_address.Urban_District,
                Soviet_Village=object_address.Soviet_Village,
                Locality=object_address.Locality, Street=object_address.Street,
                House=object_address.House, Housing=object_address.Housing,
                Building=object_address.Building,
                Apartment=object_address.Apartment,
                Reference_point=object_address.Reference_point)
            docs = [AppliedDocument(
                title=doc.title, number=doc.number, date=doc.date,
                valid_until=doc.valid_until, file_name=doc.file_name,
                url=doc.url, url_valid_until=doc.url_valid_until)
                for doc in declar.documents]
            legal_entities = [LegalEntity(
                name=legal_entity.name, full_name=legal_entity.full_name,
                inn=legal_entity.inn, kpp=legal_entity.kpp,
                address=Address(
                    Postal_Code=legal_entity.address.Postal_Code,
                    Region=legal_entity.address.Region,
                    District=legal_entity.address.District,
                    City=legal_entity.address.City,
                    Urban_District=legal_entity.address.Urban_District,
                    Soviet_Village=legal_entity.address.Soviet_Village,
                    Locality=legal_entity.address.Locality,
                    Street=legal_entity.address.Street,
                    House=legal_entity.address.House,
                    Housing=legal_entity.address.Housing,
                    Building=legal_entity.address.Building,
                    Apartment=legal_entity.address.Apartment,
                    Reference_point=legal_entity.address.Reference_point),
                ogrn=legal_entity.ogrn, taxRegDoc=legal_entity.taxRegDoc,
                govRegDoc=legal_entity.govRegDoc,
                govRegDate=legal_entity.govRegDate,
                phone=[phone for phone in legal_entity.phone],
                email=[email for email in legal_entity.email],
                bossFio=legal_entity.bossFio, buhFio=legal_entity.buhFio,
                bank=legal_entity.bank, bankAccount=legal_entity.bankAccount,
                lastCtrlDate=legal_entity.lastCtrlDate, opf=legal_entity.opf,
                govRegOgv=legal_entity.govRegOgv,
                person=Individual(
                    surname=legal_entity.person.surname,
                    first_name=legal_entity.person.first_name,
                    patronymic=legal_entity.person.patronymic,
                    address=Address(
                        Postal_Code=legal_entity.person.address.Postal_Code,
                        Region=legal_entity.person.address.Region,
                        District=legal_entity.person.address.District,
                        City=legal_entity.person.address.City,
                        Urban_District=legal_entity.person.address.Urban_District,
                        Soviet_Village=legal_entity.person.address.Soviet_Village,
                        Locality=legal_entity.person.address.Locality,
                        Street=legal_entity.person.address.Street,
                        House=legal_entity.person.address.House,
                        Housing=legal_entity.person.address.Housing,
                        Building=legal_entity.person.address.Building,
                        Apartment=legal_entity.person.address.Apartment,
                        Reference_point=legal_entity.person.address.Reference_point),
                    fact_address=Address(
                        Postal_Code=legal_entity.person.fact_address.Postal_Code,
                        Region=legal_entity.person.fact_address.Region,
                        District=legal_entity.person.fact_address.District,
                        City=legal_entity.person.fact_address.City,
                        Urban_District=legal_entity.person.fact_address.Urban_District,
                        Soviet_Village=legal_entity.person.fact_address.Soviet_Village,
                        Locality=legal_entity.person.fact_address.Locality,
                        Street=legal_entity.person.fact_address.Street,
                        House=legal_entity.person.fact_address.House,
                        Housing=legal_entity.person.fact_address.Housing,
                        Building=legal_entity.person.fact_address.address.Building,
                        Apartment=legal_entity.person.fact_address.Apartment,
                        Reference_point=legal_entity.person.fact_address.Reference_point) if legal_entity.person.fact_address else None,
                    email=[email for email in legal_entity.person.email],
                    birthdate=legal_entity.person.birthdate,
                    passport_serial=legal_entity.person.passport_serial,
                    passport_number=legal_entity.person.passport_number,
                    passport_agency=legal_entity.person.passport_agency,
                    passport_date=legal_entity.person.passport_date,
                    phone=[phone for phone in legal_entity.person.phone],
                    inn=legal_entity.person.inn, sex=legal_entity.person.sex,
                    snils=legal_entity.person.snils) if legal_entity.person else None)
                for legal_entity in declar.legal_entity]
            persons = [
                Individual(
                    surname=person.surname, first_name=person.first_name,
                    patronymic=person.patronymic, address=Address(
                        Postal_Code=person.address.Postal_Code,
                        Region=person.address.Region,
                        District=person.address.District,
                        City=person.address.City,
                        Urban_District=person.address.Urban_District,
                        Soviet_Village=person.address.Soviet_Village,
                        Locality=person.address.Locality,
                        Street=person.address.Street,
                        House=person.address.House,
                        Housing=person.address.Housing,
                        Building=person.address.Building,
                        Apartment=person.address.Apartment,
                        Reference_point=person.address.Reference_point),
                    fact_address=Address(
                        Postal_Code=person.fact_address.Postal_Code,
                        Region=person.fact_address.Region,
                        District=person.fact_address.District,
                        City=person.fact_address.City,
                        Urban_District=person.fact_address.Urban_District,
                        Soviet_Village=person.fact_address.Soviet_Village,
                        Locality=person.fact_address.Locality,
                        Street=person.fact_address.Street,
                        House=person.fact_address.House,
                        Housing=person.fact_address.Housing,
                        Building=person.fact_address.address.Building,
                        Apartment=person.fact_address.Apartment,
                        Reference_point=person.fact_address.Reference_point) if person.fact_address else None,
                    email=[email for email in person.email],
                    birthdate=person.birthdate,
                    passport_serial=person.passport_serial,
                    passport_number=person.passport_number,
                    passport_agency=person.passport_agency,
                    passport_date=person.passport_date,
                    phone=[phone for phone in person.phone], inn=person.inn,
                    sex=person.sex, snils=person.snils) for person in
                declar.person]
            params = [param for param in declar.param]
            d = Declar(
                declar_number=declar.declar_number, service=declar.service,
                register_date=declar.register_date, end_date=declar.end_date,
                object_address=a, AppliedDocument=docs,
                legal_entity=legal_entities, person=persons,
                confidant=Individual(
                    surname=declar.confidant.surname,
                    first_name=declar.confidant.first_name,
                    patronymic=declar.confidant.patronymic, address=Address(
                        Postal_Code=declar.confidant.address.Postal_Code,
                        Region=declar.confidant.address.Region,
                        District=declar.confidant.address.District,
                        City=declar.confidant.address.City,
                        Urban_District=declar.confidant.address.Urban_District,
                        Soviet_Village=declar.confidant.address.Soviet_Village,
                        Locality=declar.confidant.address.Locality,
                        Street=declar.confidant.address.Street,
                        House=declar.confidant.address.House,
                        Housing=declar.confidant.address.Housing,
                        Building=declar.confidant.address.Building,
                        Apartment=declar.confidant.address.Apartment,
                        Reference_point=declar.confidant.address.Reference_point),
                    fact_address=Address(
                        Postal_Code=declar.confidant.fact_address.Postal_Code,
                        Region=declar.confidant.fact_address.Region,
                        District=declar.confidant.fact_address.District,
                        City=declar.confidant.fact_address.City,
                        Urban_District=declar.confidant.fact_address.Urban_District,
                        Soviet_Village=declar.confidant.fact_address.Soviet_Village,
                        Locality=declar.confidant.fact_address.Locality,
                        Street=declar.confidant.fact_address.Street,
                        House=declar.confidant.fact_address.House,
                        Housing=declar.confidant.fact_address.Housing,
                        Building=declar.confidant.fact_address.address.Building,
                        Apartment=declar.confidant.fact_address.Apartment,
                        Reference_point=declar.confidant.fact_address.Reference_point) if declar.confidant.fact_address else None,
                    email=[email for email in declar.confidant.email],
                    birthdate=declar.confidant.birthdate,
                    passport_serial=declar.confidant.passport_serial,
                    passport_number=declar.confidant.passport_number,
                    passport_agency=declar.confidant.passport_agency,
                    passport_date=declar.confidant.passport_date,
                    phone=[phone for phone in declar.confidant.phone],
                    inn=declar.confidant.inn, sex=declar.confidant.sex,
                    snils=declar.confidant.snils) if declar.confidant else None,
                Param=params)
            declars_info.append((d, files, declar.reply_to, declar.uuid))
        return declars_info

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
        self.session.execute('VACUUM FULL')

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
