# -*- coding: utf-8 -*-
import logging
from datetime import date, datetime
from xml.dom.minidom import Document
from xml.etree.ElementTree import fromstring

from zeep import Client



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
        self.log = logging.getLogger('directum')
        self.proxy = Client(wsdl)

    def run_script(self, script_name, params):
        """
        Executes Directum script `script_name` with parameters `params`
        :param str script_name: Name of the script
        :param list params: Script parameters in form: [(par1, val1), (par2, val2)]
        :return: Script execution result
        """
        keys_values = self.proxy.get_type('ns2:ArrayOfKeyValueOfstringstring')()
        for key, value in params:
            param = {'Key': key, 'Value': value}
            keys_values.KeyValueOfstringstring.append(param)
        res = self.proxy.service.RunScript(script_name, keys_values)
        return res

    # TODO: Refactor
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

        document = self.proxy.get_type('ns2:ArrayOfbase64Binary')()
        document.base64Binary = base64_encode(data)[0]
        res = self.proxy.service.EDocumentsCreate(XMLPackage=package,
                                                  Documents=document)
        if res.string[0][0] == "1":
            raise Exception(res.string[0][2:])
        return res.string[0][2:]

    # TODO: Refactor
    def add_individual(self, human):
        isinstance(human, HumanRequisites)

        xml_package = Document()

        section = xml_package.createElement("Section")
        section.setAttribute("Index", "0")

        # # "Код"
        # requisite = xml_package.createElement("Requisite")
        # requisite.setAttribute("Name", u"Код")
        # requisite.setAttribute("Type", "String")
        # text = xml_package.createTextNode(human.id)
        # requisite.appendChild(text)
        # section.appendChild(requisite)

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
        text = xml_package.createTextNode(human.first_name)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Отчество"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дополнение3")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.patronymic)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Адрес проживания"
        if human.fact_address:
            requisite = xml_package.createElement("Requisite")
            requisite.setAttribute("Name", u"Примечание")
            requisite.setAttribute("Type", "String")
            text = xml_package.createTextNode(human.fact_address)
            requisite.appendChild(text)
            section.appendChild(requisite)

        # "Адрес регистрации"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Расписание")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(self.__address_2_str(human.address))
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
        text = xml_package.createTextNode(human.email)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Дата рождения"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дата")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(human.birthdate)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # Запись
        rec = xml_package.createElement("Record")
        rec.setAttribute("ID", '')
        rec.setAttribute("Action", "Change")
        rec.appendChild(section)

        # Запись справочника
        obj = xml_package.createElement("Object")
        obj.setAttribute("Type", "Reference")  # Задаем атрибут "Тип"
        obj.setAttribute("Name", u'ПРС')  # Персоны
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

    def add_legal_entity(self, entity):
        """

        :param entity: declar.LegalEntity instanse
        :return: None or error message
        """
        xml_package = Document()

        section = xml_package.createElement("Section")
        section.setAttribute("Index", "0")

        # # "Код"
        # requisite = xml_package.createElement("Requisite")
        # requisite.setAttribute("Name", u"Код")
        # requisite.setAttribute("Type", "String")
        # text = xml_package.createTextNode(declar.id)
        # requisite.appendChild(text)
        # section.appendChild(requisite)

        #  "Наименование"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Наименование")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(
            entity.name if len(entity.name) < 50 else entity.name[:49])
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Юрид. наименование"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"LongString")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(
            entity.full_name
            if len(entity.full_name) < 1024 else entity.full_name[:1023])
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "ИНН"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"ИНН")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(
            entity.inn if len(entity.inn) < 15 else entity.inn[:14])
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "КПП"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Ед_Изм")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(
            entity.kpp if len(entity.kpp) < 10 else entity.kpp[:9])
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Юридический адрес"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Содержание2")
        requisite.setAttribute("Type", "String")
        addr = self.__address_2_str(entity.address)
        text = xml_package.createTextNode(
            addr if len(addr) < 255 else addr[:254])
        requisite.appendChild(text)
        section.appendChild(requisite)

        # Запись
        rec = xml_package.createElement("Record")
        rec.setAttribute("ID", '')
        rec.setAttribute("Action", "Change")
        rec.appendChild(section)

        # Запись справочника
        obj = xml_package.createElement("Object")
        obj.setAttribute("Type", "Reference")  # Задаем атрибут "Тип"
        obj.setAttribute("Name", u'ОРГ')  # Организации
        obj.appendChild(rec)

        dataexchangepackage = xml_package.createElement("DataExchangePackage")
        dataexchangepackage.appendChild(obj)

        xml_package.appendChild(dataexchangepackage)

        package = xml_package.toxml(encoding='utf-8').decode('utf-8')
        xml_package.unlink()

        res = self.proxy.service.ReferencesUpdate(XMLPackage=package, ISCode='',
                                                  FullSync=True)
        return res

    def add_declar(self, declar, doc_getter=None, subdivision="106759",
                   reg_place="108279"):
        """
        Saves `declar` to Directum reference 'ДПУ' and binds `docs` to it. Creates appropriate records for 'ПРС' and 'ОРГ' if needed. If record already exists simply add not existing documents

        :param reg_place:
        :param subdivision:
        :param doc_getter:
        :param declar:

        :param docs:

        :return: None or error message
        """
        # Search for such declar
        res = self.search('ДПУ', "Дополнение3='%s' and Дата='%s'" %
                          (declar.declar_number,
                           declar.register_date.strftime('%d.%m.%Y')))
        if len(res):
            # Добавляем отсутствующие документы
            declar_id = res[0]['ИДЗапГлавРазд']
            doc_ids = []
            for doc in declar.AppliedDocument:
                if doc.number:
                    s_str = "ISBEDocName like '%%%s%%' and NumberEDoc='%s' " \
                            "and Дата4='%s'" % \
                            (doc.title, doc.number,
                             doc.date.strftime('%d.%m.%Y'))
                else:
                    s_str = "ISBEDocName like '%%%s%%' and " \
                            "(NumberEDoc='' or NumberEDoc is null) " \
                            "and Дата4='%s'" % \
                            (doc.title, doc.date.strftime('%d.%m.%Y'))
                res = self.search('ТКД_ПРОЧИЕ', s_str, tp=self.DOC)
                if not len(res):
                    doc_data = doc_getter(doc.url, doc.file_name) \
                        if doc_getter else ('txt', '')
                    res = self.add_doc(doc, doc_data[1], doc_data[0])
                    # bind document with declar
                    params = [('ID', declar_id), ('DocID', res)]
                    self.run_script('BindEDocDPbyID', params)
                    doc_ids.append(str(res))
            # Send notification about new docs
            if doc_ids:
                params = [('ID', declar_id),
                          ('Doc_IDs', ';'.join(doc_ids))]
                self.run_script('notification_add_docs', params)
            return res

        # Add new
        xml_package = Document()

        section = xml_package.createElement("Section")
        section.setAttribute("Index", "0")

        # Search for applicant in Directum
        # If not exists add new
        # Individual
        if len(declar.person) > 0:
            section7 = xml_package.createElement('Section')
            section7.setAttribute('Index', '7')
            number = 1
            for person in declar.person:
                res = self.search('ПРС', "Дополнение='%s' and Дополнение2='%s' "
                                         "and Дополнение3='%s' "
                                         "and Расписание='%s'"
                                         " and Состояние='Действующая'" %
                                  (person.surname, person.first_name,
                                   person.patronymic,
                                   person.address.Locality + ', ' +
                                   person.address.Housing))
                if res:
                    person_id = res[0].get('ИД')
                else:
                    res = self.add_individual(person)
                    person_id = res
                # "Заявитель ФЛ"
                rec = xml_package.createElement('Record')
                rec.setAttribute("ID", str(number))
                number += 1
                rec.setAttribute("Action", "Change")
                sec = xml_package.createElement("Section")
                sec.setAttribute("Index", "0")
                requisite = xml_package.createElement("Requisite")
                requisite.setAttribute("Name", "CitizenT7")
                requisite.setAttribute("Type", "Reference")
                requisite.setAttribute("ReferenceName", u"ПРС")
                text = xml_package.createTextNode(person_id)
                requisite.appendChild(text)
                sec.appendChild(requisite)
                rec.appendChild(sec)
                section7.appendChild(rec)

        # LegalEntity
        if len(declar.legal_entity):
            section6 = xml_package.createElement('Section')
            section6.setAttribute('Index', '6')
            number = 1
            for ent in declar.legal_entity:
                res = self.search('ОРГ', "Наименование='%s'"
                                         " and Состояние='Действующая'" %
                                  ent.name)
                if res:
                    ent_id = res[0].get('ИД')
                else:
                    res = self.add_legal_entity(ent)
                    ent_id = res
                # "Заявитель ЮЛ"
                rec = xml_package.createElement('Record')
                rec.setAttribute("ID", str(number))
                number += 1
                rec.setAttribute("Action", "Change")
                sec = xml_package.createElement("Section")
                sec.SetAttribute("Index", "0")
                requisite = xml_package.createElement("Requisite")
                requisite.setAttribute("Name", "OrgT6")
                requisite.setAttribute("Type", "Reference")
                requisite.setAttribute("ReferenceName", u"ОРГ")
                text = xml_package.createTextNode(ent_id)
                requisite.appendChild(text)
                sec.appendChild(requisite)
                rec.appendChild(sec)
                section6.appendChild(rec)

        # # "Код"
        # requisite = xml_package.createElement("Requisite")
        # requisite.setAttribute("Name", u"Код")
        # requisite.setAttribute("Type", "String")
        # text = xml_package.createTextNode(declar.id)
        # requisite.appendChild(text)
        # section.appendChild(requisite)

        # "№ дела"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дополнение3")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(declar.declar_number)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Дата регистрации"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дата")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(
            declar.register_date.strftime('%d.%m.%Y'))
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Оконч. оказания услуги (ПЛАН)"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дата4")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(declar.end_date.strftime('%d.%m.%Y'))
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Способ доставки"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"СпособДост")
        requisite.setAttribute("Type", "Reference")
        requisite.setAttribute("ReferenceName", u"СДК")
        text = xml_package.createTextNode("826965")
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Адресат"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Подразделение")
        requisite.setAttribute("Type", "Reference")
        requisite.setAttribute("ReferenceName", u"ПОД")
        text = xml_package.createTextNode(subdivision)
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Место регистрации"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"МестоРег")
        requisite.setAttribute("Type", "Reference")
        requisite.setAttribute("ReferenceName", u"МРГ")
        text = xml_package.createTextNode(reg_place)
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Статус оказания устуги"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"ServiceState")
        requisite.setAttribute("Type", u"Признак")
        text = xml_package.createTextNode("Инициализация")
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Наша организация"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"НашаОрг")
        requisite.setAttribute("Type", "Reference")
        requisite.setAttribute("ReferenceName", u"НОР")
        text = xml_package.createTextNode("38838")
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Вид услуги"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"ServiceCode")
        requisite.setAttribute("Type", "Reference")
        requisite.setAttribute("ReferenceName", u"ВМУ")
        res = self.search('ВМУ', "Наименование like '%%%s%%'"
                                 " or LongString like '%%%s%%'" %
                          (declar.service, declar.service))
        if not len(res):
            raise Exception("Услуга не найдена")
        text = xml_package.createTextNode(res[0]['ИДЗапГлавРазд'])
        requisite.appendChild(text)
        section.appendChild(requisite)

        if declar.object_address:
            #  "Местонахождение объекта"
            section9 = xml_package.createElement("Section")
            section9.setAttribute("Index", "9")
            rec = xml_package.createElement("Record")
            rec.setAttribute("ID", "1")
            rec.setAttribute("Action", "Change")
            sec = xml_package.createElement("Section")
            sec.setAttribute("Index", "0")
            requisite = xml_package.createElement("Requisite")
            requisite.setAttribute("Name", "LongStringT9")
            requisite.setAttribute("Type", "String")
            text = xml_package.createTextNode(
                declar.object_address
                if len(declar.object_address) < 1024
                else declar.object_address[:1023])
            requisite.appendChild(text)
            sec.appendChild(requisite)
            rec.appendChild(sec)
            section9.appendChild(rec)

        # Запись
        rec = xml_package.createElement("Record")
        rec.setAttribute("ID", '')  # ИД
        rec.setAttribute("Action", "Change")
        rec.appendChild(section)
        if len(declar.person):
            rec.appendChild(section7)
        if len(declar.legal_entity):
            rec.appendChild(section6)
        if declar.object_address:
            rec.appendChild(section9)

        # Объект
        obj = xml_package.createElement("Object")
        obj.setAttribute("Type", "Reference")  # Задаем атрибут "Тип"
        obj.setAttribute("Name", u'ДПУ')  # Дела по предоставлению услуг
        obj.appendChild(rec)

        dataexchangepackage = xml_package.createElement("DataExchangePackage")
        dataexchangepackage.appendChild(obj)

        xml_package.appendChild(dataexchangepackage)

        package = xml_package.toxml(encoding='utf-8').decode('utf-8')
        xml_package.unlink()

        res = self.proxy.service.ReferencesUpdate(XMLPackage=package, ISCode='',
                                                  FullSync=True)

        for doc in declar.AppliedDocument:
            doc_data = doc_getter(doc.url, doc.file_name) \
                if doc_getter else ('txt', '')
            res = self.add_doc(doc, doc_data[1], doc_data[0])
            # bind document with declar
            params = [('ID', declar_id), ('DocID', res)]
            self.run_script('BindEDocDPbyID', params)
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
        self.log.debug("Search request: %s" % xml_doc.decode())
        search_pak.unlink()
        res = self.proxy.service.Search(xml_doc)
        self.log.debug("Search result: %s" % res)
        xml_doc = fromstring(res)
        if tp:
            return [{req: elem.get(req)
                     for req in ('Editor', 'Extension', 'Type', 'Name', 'ID',
                                 'VED', 'TKED')}
                    for elem in xml_doc.iter('Object')]
        else:
            return [
                {req.get('Name'): req.text for req in elem.iter('Requisite')}
                for elem in xml_doc.iter('Record')]

    def __search_crit_parser(self, criteria):
        """
        Recursively parses `criteria` to XML Element

        :param str criteria: Criteria like SQL WHERE clause

        :return: xml.dom.minidom.Element
        """

        def get_val(crt, idx):
            v = crt[idx:-1].strip() \
                if crt.endswith(')') else criteria[idx:].strip()
            # Remove string quotes
            if v[0] == "'" and v.endswith("'"):
                v = v[1:-1]
            return v

        opers = {'like': 'Like', '>=': 'GEq', '<=': 'LEq', '=': 'Eq',
                 '<>': 'NEq', '>': 'Gt', '<': 'Lt', 'is null': 'IsNull',
                 'is not null': 'IsNotNull', 'contains': 'Contains'}
        doc = Document()
        # if criteria[0] == '(' and criteria.endswith(')'):
        #     criteria = criteria[1:-1]
        # Cut strings from criteria
        c_no_str = criteria
        while "'" in c_no_str:
            idx = c_no_str.index("'")
            first = c_no_str[:idx]
            second = c_no_str[c_no_str.index("'", idx + 1) + 1:]
            c_no_str = first + second
        if '(' in c_no_str:
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
            elif 'And' in criteria:
                first, second = criteria.split('And', 1)
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
            elif 'Or' in criteria:
                first, second = criteria.split('Or', 1)
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
        if 'is null' in criteria.lower():
            if 'IS NULL' in criteria:
                first, second = criteria.split('IS NULL', 1)
            elif 'Is null' in criteria:
                first, second = criteria.split('Is null', 1)
            elif 'is Null' in criteria:
                first, second = criteria.split('is Null', 1)
            elif 'Is Null' in criteria:
                first, second = criteria.split('Is Null', 1)
            else:
                first, second = criteria.split('is null', 1)
            first, second = first.strip(), second.strip()
            elem = doc.createElement('IsNull')
            elem.setAttribute('Requisite', first)
            doc.unlink()
            return elem
        if 'is not null' in criteria.lower():
            if 'IS NOT NULL' in criteria:
                first, second = criteria.split('IS NOT NULL', 1)
            elif 'Is not null' in criteria:
                first, second = criteria.split('Is not null', 1)
            elif 'is not Null' in criteria:
                first, second = criteria.split('is not Null', 1)
            elif 'Is not Null' in criteria:
                first, second = criteria.split('Is not Null', 1)
            elif 'Is Not Null' in criteria:
                first, second = criteria.split('Is Not Null', 1)
            else:
                first, second = criteria.split('is not null', 1)
            first, second = first.strip(), second.strip()
            elem = doc.createElement('IsNotNull')
            elem.setAttribute('Requisite', first)
            doc.unlink()
            return elem
        for oper in opers.keys():
            if oper in criteria.lower():
                idx = criteria.lower().index(oper)
                elem = doc.createElement(opers.get(oper))
                elem.setAttribute('Requisite', criteria[:idx].strip())
                elem.setAttribute('Value',
                                  get_val(criteria, idx + len(oper)))
                doc.unlink()
                return elem

    def __address_2_str(self, addr):
        """
        Converts `declar.Address` to str

        :param addr: `declar.Address`

        :return: str
        """
        res = ''
        if addr.Postal_Code:
            res = addr.Postal_Code
        if addr.Region:
            res += ', ' + addr.Region if res else addr.Region
        if addr.District:
            res += ', ' + addr.District if res else addr.District
        if addr.City:
            res += ', ' + addr.City if res else addr.City
        if addr.Urban_District:
            res += ', ' + addr.Urban_District if res else addr.Urban_District
        if addr.Soviet_Village:
            res += ', ' + addr.Soviet_Village if res else addr.Soviet_Village
        res += ', ' + addr.Locality if res else addr.Locality
        if addr.Street:
            res += ', ' + addr.Street
        if addr.House:
            res += ', ' + addr.House
        if addr.Housing:
            res += ', ' + addr.Housing
        if addr.Building:
            res += ', ' + addr.Building
        if addr.Apartment:
            res += ', ' + addr.Apartment
        if addr.Reference_point:
            res += ', ' + addr.Reference_point
        return res


if __name__ == '__main__':
    from declar import Declar, Individual, Address

    # logging.basicConfig(level=logging.DEBUG)

    d = Declar()
    d.declar_number = '111111'
    i = Individual()
    i.surname = 'Бендер'
    i.first_name = 'Остап'
    i.patronymic = 'Ибрагимович'
    a = Address()
    a.Locality = 'ул. Бонивура'
    a.Housing = '7а рег'
    i.address = a
    d.person.append(i)
    d.register_date = date(2014, 8, 8)
    d.end_date = date(2014, 10, 8)
    d.service = "Предоставление земельных участков, на которых расположены " \
                "здания, строения, сооружения на праве аренды, постоянного " \
                "(бессрочного) пользования, безвозмездного срочного " \
                "пользования, в собственность"
    wsdl = "http://servdir1:8083/IntegrationService.svc?singleWsdl"

    logger = logging.getLogger('directum')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    dis = IntegrationServices(wsdl)
    res = dis.add_declar(d)
    print(res)
