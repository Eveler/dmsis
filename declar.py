# -*- coding: utf-8 -*-
# flake8:noqa
# isort:skip_file
# vim:et:ft=python:nowrap:sts=4:sw=4:ts=4
##############################################################################
# Note: Generated by soapfish.xsd2py at 2017-10-25 21:08:29.141773
#       Try to avoid editing it if you might need to regenerate it.
##############################################################################

from soapfish import xsd


# urn://augo/smev/uslugi/1.0.0


class AgentType(xsd.String):
    enumeration = ['0', '1']


class Sex(xsd.String):
    enumeration = ['Муж', 'Жен', '']


class S6(xsd.String):
    pass


class S10(xsd.String):
    pass


class S50(xsd.String):
    pass


class S120(xsd.String):
    pass


class S1024(xsd.String):
    pass


class Address(xsd.ComplexType):
    INHERITANCE = None
    INDICATOR = xsd.Sequence
    Postal_Code = xsd.Element(S6, minOccurs=0)
    Region = xsd.Element(xsd.String, minOccurs=0)
    District = xsd.Element(xsd.String, minOccurs=0)
    City = xsd.Element(xsd.String, minOccurs=0)
    Urban_District = xsd.Element(xsd.String, minOccurs=0)
    Soviet_Village = xsd.Element(xsd.String, minOccurs=0)
    Locality = xsd.Element(xsd.String)
    Housing = xsd.Element(xsd.String, minOccurs=0)
    Building = xsd.Element(xsd.String, minOccurs=0)
    Apartment = xsd.Element(xsd.String, minOccurs=0)

    @classmethod
    def create(cls, Locality):
        instance = cls()
        instance.Locality = Locality
        return instance


class AppliedDocument(xsd.ComplexType):
    INHERITANCE = None
    INDICATOR = xsd.Sequence
    title = xsd.Element(S1024)
    number = xsd.Element(S50)
    date = xsd.Element(xsd.Date)
    valid_until = xsd.Element(xsd.Date, minOccurs=0)
    file_name = xsd.Element(xsd.String, minOccurs=0)
    url = xsd.Element(xsd.String)
    url_valid_until = xsd.Element(xsd.DateTime, minOccurs=0)

    @classmethod
    def create(cls, title, number, date, url):
        instance = cls()
        instance.title = title
        instance.number = number
        instance.date = date
        instance.url = url
        return instance


class LegalEntity(xsd.ComplexType):
    INHERITANCE = None
    INDICATOR = xsd.Sequence
    name = xsd.Element(xsd.String)
    full_name = xsd.Element(xsd.String, minOccurs=0)
    inn = xsd.Element(xsd.String, minOccurs=0)
    kpp = xsd.Element(xsd.String, minOccurs=0)
    address = xsd.Element(Address)
    ogrn = xsd.Element(xsd.String, minOccurs=0)
    taxRegDoc = xsd.Element(xsd.String, minOccurs=0)
    govRegDoc = xsd.Element(xsd.String, minOccurs=0)
    govRegDate = xsd.Element(xsd.Date, minOccurs=0)
    phone = xsd.ListElement(xsd.String, tagname='phone', minOccurs=0, maxOccurs=xsd.UNBOUNDED)
    email = xsd.ListElement(xsd.String, tagname='email', minOccurs=0, maxOccurs=xsd.UNBOUNDED)
    bossFio = xsd.Element(xsd.String, minOccurs=0)
    buhFio = xsd.Element(xsd.String, minOccurs=0)
    bank = xsd.Element(xsd.String, minOccurs=0)
    bankAccount = xsd.Element(xsd.String, minOccurs=0)
    lastCtrlDate = xsd.Element(xsd.Date, minOccurs=0)
    opf = xsd.Element(xsd.String, minOccurs=0)
    govRegOgv = xsd.Element(xsd.String, minOccurs=0)
    person = xsd.Element(__name__ + '.Individual', minOccurs=0)

    @classmethod
    def create(cls, name, address):
        instance = cls()
        instance.name = name
        instance.address = address
        return instance


class Individual(xsd.ComplexType):
    INHERITANCE = None
    INDICATOR = xsd.Sequence
    surname = xsd.Element(xsd.String)
    first_name = xsd.Element(xsd.String)
    patronymic = xsd.Element(xsd.String, minOccurs=0)
    address = xsd.Element(Address)
    fact_address = xsd.Element(Address, minOccurs=0)
    email = xsd.ListElement(xsd.String, tagname='email', minOccurs=0, maxOccurs=xsd.UNBOUNDED)
    birthdate = xsd.Element(xsd.Date, minOccurs=0)
    passport_serial = xsd.Element(xsd.String, minOccurs=0)
    passport_number = xsd.Element(xsd.String, minOccurs=0)
    passport_agency = xsd.Element(xsd.String, minOccurs=0)
    passport_date = xsd.Element(xsd.Date, minOccurs=0)
    phone = xsd.ListElement(xsd.String, tagname='phone', minOccurs=0, maxOccurs=xsd.UNBOUNDED)
    inn = xsd.Element(xsd.String, minOccurs=0)
    sex = xsd.Element(Sex, minOccurs=0)
    snils = xsd.Element(xsd.String, minOccurs=0)

    @classmethod
    def create(cls, surname, first_name, address):
        instance = cls()
        instance.surname = surname
        instance.first_name = first_name
        instance.address = address
        return instance


class RequestResponse(xsd.ComplexType):
    INHERITANCE = None
    INDICATOR = xsd.Sequence
    declar_number = xsd.Element(xsd.String)
    register_date = xsd.Element(xsd.Date)
    result = xsd.Element(xsd.String(enumeration=['ACCEPTED', 'INTERMEDIATE', 'INFO', 'ERROR', 'FINAL']))
    text = xsd.Element(xsd.String, minOccurs=0)
    AppliedDocument = xsd.ListElement(AppliedDocument, tagname='AppliedDocument', minOccurs=0, maxOccurs=xsd.UNBOUNDED)

    @classmethod
    def create(cls, declar_number, register_date, result):
        instance = cls()
        instance.declar_number = declar_number
        instance.register_date = register_date
        instance.result = result
        return instance


class Declar(xsd.ComplexType):
    INHERITANCE = None
    INDICATOR = xsd.Sequence
    declar_number = xsd.Element(xsd.String)
    service = xsd.Element(xsd.String)
    register_date = xsd.Element(xsd.Date)
    end_date = xsd.Element(xsd.Date)
    object_address = xsd.Element(Address, minOccurs=0)
    AppliedDocument = xsd.ListElement(AppliedDocument, tagname='AppliedDocument', maxOccurs=xsd.UNBOUNDED)
    confidant = xsd.Element(Individual, minOccurs=0)

    @classmethod
    def create(cls, declar_number, service, register_date, end_date, AppliedDocument):
        instance = cls()
        instance.declar_number = declar_number
        instance.service = service
        instance.register_date = register_date
        instance.end_date = end_date
        instance.AppliedDocument = AppliedDocument
        return instance


Schema_ef09a = xsd.Schema(
    imports=[],
    includes=[],
    targetNamespace='urn://augo/smev/uslugi/1.0.0',
    elementFormDefault='qualified',
    simpleTypes=[AgentType, Sex, S6, S10, S50, S120, S1024],
    attributeGroups=[],
    groups=[],
    complexTypes=[Address, AppliedDocument, LegalEntity, Individual, RequestResponse],
    elements={'declar': xsd.Element(Declar())},
)
