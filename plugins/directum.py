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
    REF = 0
    DOC = 1

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
        xml_package.unlink()

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
        xml_package.unlink()

        res = self.proxy.service.ReferencesUpdate(XMLPackage=package, ISCode='',
                                                  FullSync=True)
        params = [('Param', human.id),
                  ('ReferName', u'ПРС')]
        res = self.run_script('CheckDuplicateByCode', params)
        if res:
            raise Exception(res)
        return res

    def search(self, code, criteria, tp=REF):
        """
        Call search

        :param str code: Name of directum object

        :param str criteria: Criteria like SQL WHERE clause: 'par1=val1 and (par2=val2 or par3 like val3)'

        :param int tp: If equal to `IntegrationServices.REF` search on directum reference else on document

        :return: list of dict
        """
        search_pak = Document()
        search = search_pak.createElement('Search')
        if tp:
            search.setAttribute('Type', 'EDocument')
            search.setAttribute('CardType', code)
        else:
            search.setAttribute('Type', 'Reference')
            search.setAttribute('ReferenceName', code)

        select = search_pak.createElement('Select')
        search.appendChild(select)

        where = search_pak.createElement('Where')

        elem = self.__search_crit_parser(criteria)
        if elem.tagName != 'And' and not tp:
            e_and = search_pak.createElement('And')
            e_and.appendChild(elem)
            where.appendChild(e_and)
        else:
            where.appendChild(elem)

        search.appendChild(where)

        order = search_pak.createElement('OrderBy')
        search.appendChild(order)

        search_pak.appendChild(search)

        xml_doc = search_pak.toxml(encoding='utf-8')
        search_pak.unlink()
        res = self.proxy.service.Search(xml_doc)
        xml_doc = fromstring(res)
        if tp:
            return [{req: elem.get(req)
                     for req in ('Editor', 'Extension', 'Type', 'Name', 'ID',
                                 'VED', 'TKED')}
                    for elem in xml_doc.iter('Object')]
        else:
            return [{req.get('Name'): req.text for req in elem.iter('Requisite')}
                    for elem in xml_doc.iter('Record')]

    def __search_crit_parser(self, criteria):
        """
        Recursively parses `criteria` to XML Element

        :param str criteria: Criteria like SQL WHERE clause

        :return: xml.dom.minidom.Element
        """

        def get_val(crt, idx):
            v = crt[idx:-1] if crt.endswith(')') else criteria[idx:]
            # Remove string quotes
            if v[0] == "'" and v.endswith("'"):
                v = v[1:-1]
            return v

        doc = Document()
        # if criteria[0] == '(' and criteria.endswith(')'):
        #     criteria = criteria[1:-1]
        if '(' in criteria:
            idx = criteria.index('(')
            idx2 = criteria.index(')')
            cnt = criteria.count('(', idx + 1, idx2)
            while cnt:
                idx2 = criteria.index(')', __end=idx2 - 1)
                cnt = criteria.count('(', idx + 1, idx2)
            quoted = criteria[idx:criteria.index(')') + 1]
            criteria = criteria.replace(quoted, '').strip()
            elem = self.__search_crit_parser(criteria)
            elem.appendChild(self.__search_crit_parser(quoted[1:-1].strip()))
            doc.unlink()
            return elem
        if 'and' in criteria.lower():
            if 'AND' in criteria:
                first, second = criteria.split('AND', 1)
            else:
                first, second = criteria.split('and', 1)
            first, second = first.strip(), second.strip()
            elem = doc.createElement('And')
            if first:
                elem.appendChild(self.__search_crit_parser(first))
            if second:
                elem.appendChild(self.__search_crit_parser(second))
            doc.unlink()
            return elem
        if 'or' in criteria.lower():
            if 'OR' in criteria:
                first, second = criteria.split('OR', 1)
            else:
                first, second = criteria.split('or', 1)
            first, second = first.strip(), second.strip()
            elem = doc.createElement('Or')
            if first:
                elem.appendChild(self.__search_crit_parser(first))
            if second:
                elem.appendChild(self.__search_crit_parser(second))
            doc.unlink()
            return elem
        if 'like' in criteria.lower():
            if 'LIKE' in criteria.lower():
                idx = criteria.index('LIKE')
            else:
                idx = criteria.index('like')
            elem = doc.createElement('Like')
            elem.setAttribute('Requisite', criteria[:idx - 1].strip())
            elem.setAttribute('Value', get_val(criteria, idx + 5))
            doc.unlink()
            return elem
        if '=' in criteria:
            idx = criteria.index('=')
            elem = doc.createElement('Eq')
            elem.setAttribute('Requisite', criteria[:idx].strip())
            elem.setAttribute('Value', get_val(criteria, idx + 1))
            doc.unlink()
            return elem
        if '<>' in criteria:
            idx = criteria.index('<>')
            elem = doc.createElement('NEq')
            elem.setAttribute('Requisite', criteria[:idx].strip())
            elem.setAttribute('Value', get_val(criteria, idx + 2))
            doc.unlink()
            return elem


if __name__ == '__main__':
    wsdl = "http://servdir1:8083/IntegrationService.svc?singleWsdl"
    dis = IntegrationServices(wsdl)
    res = dis.search(
        'РАБ', "Наименование like '%Сав%' and Состояние='Действующая'")
    print('count:', len(res))
    for i in res:
        print(i.get('ИД'))

    # res = dis.search('ТКД_ПРОЧИЕ', "ИД=1508559", tp=IntegrationServices.DOC)
    res = dis.search('ТКД_ПРОЧИЕ', "Дата4='13.07.2014'",
                     tp=IntegrationServices.DOC)
    print('count:', len(res))
    for i in res:
        print(i.get('ID'))
