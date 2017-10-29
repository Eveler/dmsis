# -*- coding: utf-8 -*-
from datetime import datetime
from xml.dom.minidom import Document
from xml.etree.ElementTree import fromstring

from zeep import Client

__author__ = 'Eveler'


class DocumentRequisites:
    name = ''
    number = ''
    date = None
    isinstance(date, datetime)
    org_directum_id = ''
    human_name = ''

    def __init__(self):
        pass


class HumanRequisites:
    def __init__(self):
        pass


class IntegrationServices:
    def __init__(self, wsdl):
        # do_write = False
        # if not cfg.has_section("directum"):
        #     cfg.add_section("directum")
        #     do_write = True
        # if not cfg.has_option("directum", "wsdl"):
        #     cfg.set("directum", "wsdl", "http://192.168.1.5:8082/IntegrationService.svc?singleWsdl")
        #     do_write = True
        #
        # if do_write:
        #     with open("./integration.ini", "w") as configfile:
        #         cfg.write(configfile)
        #         configfile.close()
        # self.proxy = Client(cfg.get("directum", "wsdl"))
        self.proxy = Client(wsdl)

    def run_script(self, script_name, params):
        keys_values = self.proxy.factory.create(
            'ns2:ArrayOfKeyValueOfstringstring')
        for key, value in params:
            param = {'Key': key, 'Value': value}
            keys_values.KeyValueOfstringstring.append(param)
        res = self.proxy.service.RunScript(script_name, keys_values)
        return res

    def add_doc(self, requisites, data_format, data):
        isinstance(requisites, DocumentRequisites)
        editor = "EDOTXT"
        data_format = data_format.upper()
        if data_format == "PDF":
            editor = "ACROREAD"
        elif "XLS" in data_format:
            editor = "EXCEL"
        elif data_format == "ZIP":
            editor = "WINZIP"

        xml_package = Document()

        section = xml_package.createElement("Section")
        section.setAttribute("Index", "0")

        # "№ документа"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дополнение")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(requisites.number)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Дата документа"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дата4")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(requisites.date.strftime('%d.%m.%Y'))
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "№ ведущего документа"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", "NumberEDoc")
        requisite.setAttribute("Type", "Date")
        text = xml_package.createTextNode(requisites.number)
        requisite.appendChild(text)
        section.appendChild(requisite)

        obj = xml_package.createElement("Object")
        obj.setAttribute("Type", "EDocument")  # Задаем атрибут "Тип"
        obj.setAttribute("TKED",
                         u"ТКД_ПРОЧИЕ")  # Задаем атрибут "Тип карточки электронного документа"
        obj.setAttribute("VED",
                         u"ПРОЧЕЕ")  # Задаем атрибут "Вид электронного документа"
        obj.setAttribute("Name",
                         requisites.name)  # Задаем атрибут "Наименование документа"
        obj.setAttribute("Editor",
                         editor)  # Задаем атрибут "Код приложения-редактора"
        obj.appendChild(section)

        dataexchangepackage = xml_package.createElement("DataExchangePackage")
        dataexchangepackage.appendChild(obj)

        xml_package.appendChild(dataexchangepackage)

        package = xml_package.toxml(encoding='utf-8').decode('utf-8')

        from encodings.base64_codec import base64_encode

        document = self.proxy.factory.create('ns2:ArrayOfbase64Binary')
        document.base64Binary = base64_encode(data)[0]
        res = self.proxy.service.EDocumentsCreate(XMLPackage=package,
                                                  Documents=document)
        if res.string[0][0] == "1":
            raise Exception(res.string[0][2:])
        return res.string[0][2:]

    def add_human(self, human):
        isinstance(human, HumanRequisites)

        xml_package = Document()

        section = xml_package.createElement("Section")
        section.setAttribute("Index", "0")

        # "Код"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Код")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.id)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Фамилия"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дополнение")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.surname)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Имя"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дополнение2")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.firstname)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Отчество"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дополнение3")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.lastname)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Адрес проживания"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Примечание")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.addr)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Адрес регистрации"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Расписание")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.addr)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Телефон"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Строка")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.phone)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "e-mail"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Строка2")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.mail)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Дата рождения"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дата")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.birthday)
        requisite.appendChild(text)
        section.appendChild(requisite)

        rec = xml_package.createElement("Record")
        rec.setAttribute("ID", '')
        rec.setAttribute("Action", "Change")
        rec.appendChild(section)

        obj = xml_package.createElement("Object")
        obj.setAttribute("Type", "Reference")  # Задаем атрибут "Тип"
        obj.setAttribute("Name",
                         u'ПРС')  # Задаем атрибут "Наименование документа"
        obj.appendChild(rec)

        dataexchangepackage = xml_package.createElement("DataExchangePackage")
        dataexchangepackage.appendChild(obj)

        xml_package.appendChild(dataexchangepackage)

        package = xml_package.toxml(encoding='utf-8').decode('utf-8')

        res = self.proxy.service.ReferencesUpdate(XMLPackage=package, ISCode='',
                                                  FullSync=True)
        params = [('Param', human.id),
                  ('ReferName', u'ПРС')]
        res = self.run_script('CheckDuplicateByCode', params)
        if res:
            raise Exception(res)
        return res

    # FIXME: Math criteria
    def search_ref(self, ref_name, criteria={}):
        """
        Call search on reference :ref_name:
        :param ref_name: Name of directum reference
        :param criteria:
        :return:
        """
        search_pak = Document()
        search = search_pak.createElement('Search')
        search.setAttribute('Type', 'Reference')
        search.setAttribute('ReferenceName', ref_name)

        select = search_pak.createElement('Select')
        search.appendChild(select)

        where = search_pak.createElement('Where')

        e_and = search_pak.createElement('And')
        for req, val in criteria.items():
            if '%' in val:
                like = search_pak.createElement('Like')
                like.setAttribute('Requisite', req)
                like.setAttribute('Value', val)
                e_and.appendChild(like)
            else:
                eq = search_pak.createElement('Eq')
                eq.setAttribute('Requisite', req)
                eq.setAttribute('Value', val)
                e_and.appendChild(eq)
        where.appendChild(e_and)

        search.appendChild(where)

        order = search_pak.createElement('OrderBy')
        search.appendChild(order)

        search_pak.appendChild(search)

        xml_doc = search_pak.toxml(encoding='utf-8')
        xml_doc = fromstring(self.proxy.service.Search(xml_doc))
        return [{req.get('Name'): req.text for req in elem.iter('Requisite')}
                for elem in xml_doc.iter('Record')]


if __name__ == '__main__':
    wsdl = "http://servdir1:8083/IntegrationService.svc?singleWsdl"
    dis = IntegrationServices(wsdl)
    res = dis.search_ref('РАБ', {'Наименование': "%Сав%"})
    for i in res:
        print(i.get('ИД'))
