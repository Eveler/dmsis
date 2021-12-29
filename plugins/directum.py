# -*- coding: utf-8 -*-
import logging
from xml.dom.minidom import Document
from xml.etree.ElementTree import fromstring
from os import path, remove

from zeep import Client


class IntegrationServicesException(Exception):
    def __init__(self, msg, *args, **kwargs):
        super().__init__(msg, args, kwargs)

    @property
    def message(self):
        return self.args[0]


class IntegrationServices:
    REF = 0
    DOC = 1

    def __init__(self, wsdl):
        self.log = logging.getLogger('directum')
        self.proxy = Client(wsdl)

    def run_script(self, script_name, params={}):
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
        editor = "EDOTXT"
        data_format = data_format.upper()
        if data_format == "PDF":
            editor = "ACROREAD"
        elif "XLS" in data_format:
            editor = "EXCEL"
        elif "DOC" in data_format:
            editor = "WORD2007"
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
                         requisites.title)  # Задаем атрибут "Наименование документа"
        obj.setAttribute("Editor",
                         editor)  # Задаем атрибут "Код приложения-редактора"
        obj.appendChild(section)

        dataexchangepackage = xml_package.createElement("DataExchangePackage")
        dataexchangepackage.appendChild(obj)

        xml_package.appendChild(dataexchangepackage)

        package = xml_package.toxml(encoding='utf-8').decode('utf-8')
        xml_package.unlink()

        document = self.proxy.get_type('ns2:ArrayOfbase64Binary')()
        # from encodings.base64_codec import base64_encode
        # document.base64Binary = base64_encode(data)[0]
        document.base64Binary = data
        res = self.proxy.service.EDocumentsCreate(XMLPackage=package,
                                                  Documents=document)
        self.log.info('Добавлен документ: %s № %s от %s = %s' % (
            requisites.title, requisites.number,
            requisites.date.strftime('%d.%m.%Y'), res))
        if res[0][:1] == "1":
            raise Exception(res[0][2:])
        return res[0][2:]

    def add_individual(self, human):
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

        #  "Наименование"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Наименование")
        requisite.setAttribute("Type", "String")
        name = human.surname + ' ' + human.first_name + \
               (' ' + human.patronymic if human.patronymic else '')
        text = xml_package.createTextNode(name if len(name) < 50 else name[:49])
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
        text = xml_package.createTextNode(human.first_name)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # "Отчество"
        if human.patronymic:
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
            text = xml_package.createTextNode(str(human.fact_address))
            requisite.appendChild(text)
            section.appendChild(requisite)

        # "Адрес регистрации"
        if human.address:
            requisite = xml_package.createElement("Requisite")
            requisite.setAttribute("Name", u"Расписание")
            requisite.setAttribute("Type", "String")
            text = xml_package.createTextNode(str(human.address))
            requisite.appendChild(text)
            section.appendChild(requisite)

        # "Телефон"
        try:
            text = ', '.join(human.phone)
            requisite = xml_package.createElement("Requisite")
            requisite.setAttribute("Name", u"Строка")
            requisite.setAttribute("Type", "String")
            text = xml_package.createTextNode(text)
            requisite.appendChild(text)
            section.appendChild(requisite)
        except TypeError:
            pass

        # "e-mail"
        try:
            text = ', '.join(human.email)
            if text:
                requisite = xml_package.createElement("Requisite")
                requisite.setAttribute("Name", u"Строка2")
                requisite.setAttribute("Type", "String")
                text = xml_package.createTextNode(text)
                requisite.appendChild(text)
                section.appendChild(requisite)
        except TypeError:
            pass

        # "Дата рождения"
        if human.birthdate:
            requisite = xml_package.createElement("Requisite")
            requisite.setAttribute("Name", u"Дата")
            requisite.setAttribute("Type", "String")
            text = xml_package.createTextNode(
                human.birthdate.strftime('%d.%m.%Y'))
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
        # params = [('Param', human_id), ('ReferName', u'ПРС')]
        # res = self.run_script('CheckDuplicateByCode', params)
        if res[0]:
            raise Exception(str(res))
        self.log.info('Добавлен заявитель ФЛ: %s, регистрация: %s' %
                      (name, str(human.address)))
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
        name = entity.name if entity.name else entity.full_name
        text = xml_package.createTextNode(
            name if len(name) < 50 else name[:50])
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Юрид. наименование"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"LongString")
        requisite.setAttribute("Type", "String")
        name = entity.full_name if entity.full_name else entity.name
        text = xml_package.createTextNode(
            name if len(name) < 1024 else name[:1023])
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "ИНН"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"ИНН")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(
            '' if not entity.inn else
            entity.inn if len(entity.inn) < 15 else entity.inn[:14])
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "КПП"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Ед_Изм")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(
            '' if not entity.kpp else
            entity.kpp if len(entity.kpp) < 10 else entity.kpp[:9])
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Юридический адрес"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Содержание2")
        requisite.setAttribute("Type", "String")
        addr = str(entity.address)
        text = xml_package.createTextNode(
            '' if not addr else addr if len(addr) < 255 else addr[:254])
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
        if res[0]:
            raise Exception(str(res))
        self.log.info('Добавлен заявитель ЮЛ: %s' %
                      (entity.name if entity.name else entity.full_name))
        return res

    def __upload_doc(self, doc_getter, doc, files, declar_id, declar, i=0):
        if doc_getter:
            doc_data = doc_getter(doc.url, doc.file_name)
        elif hasattr(doc, 'file') and doc.file:
            fn, ext = path.splitext(doc.file_name)
            with open(doc.file, 'rb') as f:
                doc_data = (
                    f.read(), ext[1:].lower() if ext else 'txt')
        elif hasattr(declar, 'files') and declar.files:
            found = False
            for file_path, file_name in declar.files:
                if file_name.lower() == doc.file_name.lower():
                    found = file_path
            if not found:
                found, file_name = declar.files[i]
            fn, ext = path.splitext(doc.file_name)
            with open(found, 'rb') as f:
                doc_data = (f.read(), ext[1:] if ext else 'txt')
        elif files:
            file_name = doc.file_name if doc.file_name else doc.url
            fn, ext = path.splitext(file_name)
            found = files.get(file_name)
            if not found:
                found = files.get(fn + '.zip')
                ext = '.zip'
            if not found:
                found = files.get(fn + '..zip')
                ext = '.zip'
            if not found:
                raise Exception("Cannot find file '%s' in %s" % (file_name, files))
            with open(found, 'rb') as f:
                doc_data = (
                    f.read(), ext[1:].lower() if ext else 'txt')
            remove(found)
        else:
            doc_data = (b'No file', 'txt')
        res = self.add_doc(doc, doc_data[1], doc_data[0])
        # bind document with declar
        params = [('ID', declar_id), ('DocID', res)]
        self.run_script('BindEDocDPbyID', params)
        return res

    def add_declar(self, declar, files={}, doc_getter=None,
                   subdivision="106759", reg_place="108279"):
        """
        Saves `declar` to Directum reference 'ДПУ' and binds `docs` to it.
        Creates appropriate records for 'ПРС' and 'ОРГ' if needed. If record
        already exists simply add not existing documents

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
            declar_id = res[0].get('Аналитика-оригинал') \
                if res[0].get('Аналитика-оригинал') \
                else res[0].get('ИДЗапГлавРазд') \
                if res[0].get('ИДЗапГлавРазд') else res[0].get('ИД')

            # На всякий случай нормализуем наименование записи
            # params = [('Param', None), ('Param2', declar_id)]
            # res = self.run_script('NameDPU', params)
            # self.log.debug('Создание имени дела: %s' % res)

            doc_ids = []
            if declar.AppliedDocument:
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
                    s_str = s_str.replace('"', '\\"')
                    res = self.search('ТКД_ПРОЧИЕ', s_str, tp=self.DOC)
                    if not len(res):
                        doc_ids.append(str(self.__upload_doc(
                            doc_getter, doc, files, declar_id, declar)))
            else:
                for file_name, file_path in files.items():
                    fn, ext = path.splitext(file_name)
                    with open(file_path, 'rb') as f:
                        doc_data = (
                            f.read(), ext[1:].lower() if ext else 'txt')
                    remove(file_path)

                    class D:
                        pass

                    doc = D()
                    doc.number = ''
                    from datetime import date
                    doc.date = date.today()
                    doc.title = fn
                    res = self.add_doc(doc, doc_data[1], doc_data[0])
                    # bind document with declar
                    params = [('ID', declar_id), ('DocID', res)]
                    self.run_script('BindEDocDPbyID', params)
                    doc_ids.append(str(res))

            # Send notification about new docs
            if doc_ids:
                params = [('ID', declar_id),
                          ('Doc_IDs', ';'.join(doc_ids))]
                res = self.run_script('notification_add_docs', params)
                self.log.info('Отправлено уведомление ID = %s' % res)
            else:
                for file_name, file_path in files.items():
                    try:
                        remove(file_path)
                    except:
                        pass
            return declar_id

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
                query_str = \
                    "Дополнение='%s' and Дополнение2='%s'" \
                    " and Состояние='Действующая' and" \
                    " (Расписание='%s' or Расписание=''" \
                    " or Расписание is null)" % \
                    (person.surname, person.first_name, str(person.address))
                if person.patronymic:
                    query_str = "Дополнение3='%s' and " % person.patronymic +\
                                query_str
                query_str = query_str.replace('"', '\\"')
                res = self.search('ПРС', query_str)
                if not res:
                    query_str = \
                        "Дополнение='%s' and Дополнение2='%s'" \
                        " and Состояние='Действующая'" % \
                        (person.surname, person.first_name)
                    if person.patronymic:
                        query_str = "Дополнение3='%s' and " \
                                    % person.patronymic + query_str
                    query_str = query_str.replace('"', '\\"')
                    res = self.search('ПРС', query_str)
                self.log.debug('res = %s' % res)
                if res:
                    person_id = res[0].get('ИД')
                else:
                    self.add_individual(person)
                    query_str = \
                        "Дополнение='%s' and Дополнение2='%s'" \
                        " and Состояние='Действующая' and" \
                        " (Расписание='%s' or Расписание=''" \
                        " or Расписание is null)" % \
                        (person.surname, person.first_name, str(person.address))
                    if person.patronymic:
                        query_str = "Дополнение3='%s' and " % person.patronymic + \
                                    query_str
                    query_str = query_str.replace('"', '\\"')
                    res = self.search('ПРС', query_str)
                    if not res:
                        query_str = \
                            "Дополнение='%s' and Дополнение2='%s'" \
                            " and Состояние='Действующая'" % \
                            (person.surname, person.first_name)
                        if person.patronymic:
                            query_str = "Дополнение3='%s' and " \
                                        % person.patronymic + query_str
                        query_str = query_str.replace('"', '\\"')
                        res = self.search('ПРС', query_str)
                    person_id = res[0].get('ИД')
                    self.log.info('ИД персоны = %s' % person_id)
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
                query_str = ''
                if ent.full_name:
                    query_str = "LongString='%s'" % ent.full_name
                if ent.name:
                    query_str = (query_str + ' or ' if query_str else '') + \
                                "Наименование like '%%%s%%'" % \
                                (ent.name if len(ent.name) < 50
                                 else ent.name[:50])
                if ent.inn:
                    query_str = "ИНН like '%%%s%%'" % ent.inn + (
                        ' or ' + query_str if query_str else '')
                query_str = query_str.replace('"', '\\"')
                res = self.search(
                    'ОРГ', "(" + query_str + ") and Состояние='Действующая'")
                if res:
                    ent_id = res[0].get('ИД')
                else:
                    self.add_legal_entity(ent)
                    res = self.search(
                        'ОРГ', "(" + query_str + ") and Состояние='Действующая'")
                    ent_id = res[0].get('ИД')
                    logging.info('ИД организации = %s' % ent_id)
                # "Заявитель ЮЛ"
                rec = xml_package.createElement('Record')
                rec.setAttribute("ID", str(number))
                number += 1
                rec.setAttribute("Action", "Change")
                sec = xml_package.createElement("Section")
                sec.setAttribute("Index", "0")
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
        # text = xml_package.createTextNode("826965") # Автоматическая доставка из МФЦ
        text = xml_package.createTextNode("4673938") # СМЭВ
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
                                 " or LongString like '%%%s%%'"
                                 " or КСтрока like '%%%s'" %
                          (declar.service, declar.service, declar.service))
        if not len(res):
            raise IntegrationServicesException("Услуга не найдена")
        text = xml_package.createTextNode(
            res[0].get('Аналитика-оригинал')
            if res[0].get('Аналитика-оригинал') else res[0].get('ИДЗапГлавРазд')
            if res[0].get('ИДЗапГлавРазд') else res[0].get('ИД'))
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
            addr = str(declar.object_address)
            text = xml_package.createTextNode(
                addr if len(addr) < 1024 else addr[:1023])
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

        self.proxy.service.ReferencesUpdate(XMLPackage=package, ISCode='',
                                            FullSync=True)
        res = self.search('ДПУ', "Дополнение3='%s' and Дата='%s'" %
                          (declar.declar_number,
                           declar.register_date.strftime('%d.%m.%Y')))
        declar_id = res[0].get('Аналитика-оригинал') \
            if res[0].get('Аналитика-оригинал') else res[0].get('ИДЗапГлавРазд') \
            if res[0].get('ИДЗапГлавРазд') else res[0].get('ИД')

        params = [('Param', None), ('Param2', declar_id)]
        res = self.run_script('NameDPU', params)
        self.log.debug('Создание имени дела: %s' % res)
        # try:
        #     params = [('Param', None), ('Param2', declar_id)]
        #     res = self.run_script('NameDPU', params)
        #     self.log.debug('Создание имени дела: %s' % res)
        # except:
        #     self.log.error('NameDPU', exc_info=True)
        #     self.proxy.service.ReferencesUpdate(XMLPackage=package, ISCode='',
        #                                         FullSync=True)
        #     res = self.search('ДПУ', "Дополнение3='%s' and Дата='%s'" %
        #                       (declar.declar_number,
        #                        declar.register_date.strftime('%d.%m.%Y')))
        #     declar_id = res[0]['ИДЗапГлавРазд']

        self.log.info('Добавлено дело № %s от %s ID = %s' %
                      (declar.declar_number,
                       declar.register_date.strftime('%d.%m.%Y'),
                       declar_id))

        if declar.AppliedDocument:
            for doc in declar.AppliedDocument:
                self.__upload_doc(doc_getter, doc, files, declar_id, declar)
        else:
            for file_name, file_path in files:
                fn, ext = path.splitext(file_name)
                with open(file_path, 'rb') as f:
                    doc_data = (
                        f.read(), ext[1:].lower() if ext else 'txt')
                remove(file_path)

                class D:
                    pass

                doc = D()
                doc.number = ''
                from datetime import date
                doc.date = date.today()
                doc.title = fn
                res = self.add_doc(doc, doc_data[1], doc_data[0])
                # bind document with declar
                params = [('ID', declar_id), ('DocID', res)]
                self.run_script('BindEDocDPbyID', params)

        return declar_id

    def get_entity(self, name, eid):
        res = self.proxy.service.GetEntity(name, eid)
        # return res
        xml_doc = fromstring(res)
        return [{req: elem.text if req == 'value' else elem.get(req) for req in
                 ('Type', 'Name', 'value')} for elem in
                xml_doc.iter('Requisite')]

    def get_bind_docs(self, otype, oid):
        res = self.proxy.service.GetBindEDocumentsList(otype, oid)
        xml_doc = fromstring(res)
        docs = []
        for elem in xml_doc.iter('Object'):
            res = {req: elem.get(req)
                   for req in ('Editor', 'Extension', 'Type', 'Name', 'ID',
                               'VED', 'TKED')}
            res.update(
                {req.get('Name'): req.text for req in elem.iter('Requisite')})
            docs.append(res)
        return docs

    def get_doc_versions(self, doc_id):
        res = self.proxy.service.GetEDocumentVersionList(doc_id)
        xml_doc = fromstring(res)
        res = [elem.get('ID') for elem in xml_doc.iter('Version')]
        res = sorted(res, reverse=True)
        return res

    def get_doc(self, doc_id, version=-1):
        res = self.proxy.service.GetEDocument(doc_id, version)
        return res

    def get_doc_card(self, doc_id):
        res = self.proxy.service.GetEDocumentCard(doc_id)
        xml_doc = fromstring(res)
        for elem in xml_doc.iter('Object'):
            res = {req: elem.get(req)
                   for req in ('Editor', 'Extension', 'Type', 'Name', 'ID',
                               'VED', 'TKED')}
            res.update(
                {req.get('Name'): req.text for req in elem.iter('Requisite')})
        return res

    def search(self, code, criteria, tp=REF, order_by='', ascending=True):
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
        where.appendChild(elem)
        # if elem.tagName != 'And' and not tp:
        #     e_and = search_pak.createElement('And')
        #     e_and.appendChild(elem)
        #     where.appendChild(e_and)
        # else:
        #     where.appendChild(elem)

        search.appendChild(where)

        order = search_pak.createElement('OrderBy')
        if order_by:
            order.setAttribute('Name', order_by)
            order.setAttribute('Ascending', ascending)
        search.appendChild(order)

        search_pak.appendChild(search)

        xml_doc = search_pak.toxml(encoding='utf-8')
        self.log.debug("Search request: %s" % xml_doc.decode())
        search_pak.unlink()
        res = self.proxy.service.Search(xml_doc)
        self.log.debug("Search result: %s" % res)
        xml_doc = fromstring(res)
        if tp:
            docs = []
            for elem in xml_doc.iter('Object'):
                res = {req: elem.get(req)
                       for req in ('Editor', 'Extension', 'Type', 'Name', 'ID',
                                   'VED', 'TKED')}
                res.update(
                    {req.get('Name'): req.text for req in
                     elem.iter('Requisite')})
                docs.append(res)
            return docs
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

        opers = ({'like': 'Like'}, {'>=': 'GEq'}, {'<=': 'LEq'}, {'=': 'Eq'},
                 {'<>': 'NEq'}, {'>': 'Gt'}, {'<': 'Lt'},
                 {'contains': 'Contains'})
        doc = Document()
        criteria = criteria.replace('\n', ' ').replace('\r', ' ')
        # Cut strings from criteria
        c_no_str = criteria
        while "'" in c_no_str:
            idx = c_no_str.index("'")
            first = c_no_str[:idx]
            second = c_no_str[c_no_str.index("'", idx + 1) + 1:]
            c_no_str = first + second
        if '(' in c_no_str:
            idx = criteria.index('(')
            idx2 = criteria.rfind(')')
            cnt, cnt2 = 1, 0
            while cnt or cnt2:
                q_idx = criteria.find("'", idx + 1)
                q_idx2 = criteria.rfind("'", idx + 1, idx2 - 1)
                oldidx = idx
                idx = criteria.find('(', idx + 1, idx2 - 1)
                if idx < 0:
                    idx = oldidx
                if q_idx < 0:
                    q_idx = idx
                oldidx2 = idx2
                idx2 = criteria.rfind(')', idx + 1, idx2 - 1)
                if idx2 < 0:
                    idx2 = oldidx2
                if q_idx2 < 0:
                    q_idx2 = idx2
                if q_idx < idx:
                    cnt = 0
                    idx = oldidx
                else:
                    cnt = criteria.count('(', idx + 1, idx2 - 1)
                if q_idx2 > idx2:
                    cnt2 = 0
                    idx2 = oldidx2
                else:
                    cnt2 = criteria.count(')', idx + 1, idx2 - 1)
            if idx2 < 0:
                quoted = criteria[idx:]
            else:
                quoted = criteria[idx:idx2 + 1]
            criteria = criteria.replace(quoted, '')
            elem = self.__search_crit_parser(criteria)
            elem.appendChild(self.__search_crit_parser(quoted[1:].strip()))
            doc.unlink()
            return elem
        logics = {'and': 'And', 'or': 'Or'}
        for logic, txt in logics.items():
            logic = ' %s ' % logic
            if logic in criteria.lower():
                idx = criteria.lower().index(logic)
                first = criteria[:idx]
                second = criteria[idx + len(logic):]
                first, second = first.strip(), second.strip()
                elem = doc.createElement(txt)
                if first:
                    first = self.__search_crit_parser(first)
                    if first:
                        elem.appendChild(first)
                if second:
                    second = self.__search_crit_parser(second)
                    if second:
                        elem.appendChild(second)
                doc.unlink()
                return elem
        logics = {'is null': 'IsNull', 'is not null': 'IsNotNull'}
        for logic, txt in logics.items():
            logic = ' %s' % logic
            if logic in criteria.lower():
                idx = criteria.lower().index(logic)
                first = criteria[:idx]
                first = first.strip()
                elem = doc.createElement('IsNotNull')
                elem.setAttribute('Requisite', first)
                doc.unlink()
                return elem
        for oper in opers:
            key = list(oper)[0]
            val = oper[key]
            if key in criteria.lower():
                idx = criteria.lower().index(key)
                elem = doc.createElement(val)
                elem.setAttribute('Requisite', criteria[:idx].strip())
                elem.setAttribute('Value',
                                  get_val(criteria, idx + len(key)))
                doc.unlink()
                return elem


if __name__ == '__main__':
    # from declar import Declar
    # from lxml import etree

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s:%(module)s(%(lineno)d): %(levelname)s: '
               '%(message)s')
    logging.getLogger('zeep.xsd').setLevel(logging.INFO)
    logging.getLogger('zeep.wsdl').setLevel(logging.INFO)

    # with open('tests/GetRequestResponseAttachFTP.xml', 'rb') as f:
    #     res = f.read()
    # xml = etree.fromstring(res)
    # declar = Declar.parsexml(
    #     etree.tostring(xml.find('.//{urn://augo/smev/uslugi/1.0.0}declar')))

    # wsdl = "http://snadb:8082/IntegrationService.svc?singleWsdl"
    wsdl = "http://127.0.0.1:8082/IntegrationService.svc?singleWsdl"
    dis = IntegrationServices(wsdl)
    res = dis.run_script('GetEDocCertificates', [('DocID', 5277587)])
    if res:
        import crypto
        # res = res.replace('\r', '').replace('\n', '')
        # doc = dis.get_doc(5277587, 0)
        # import tempfile, os, subprocess
        # p7stmp_f, p7stmp_fn = tempfile.mkstemp()
        # os.close(p7stmp_f)
        # with open(p7stmp_fn, 'w') as f:
        #     f.write(res)
        # doctmp_f, doctmp_fn = tempfile.mkstemp()
        # os.write(doctmp_f, doc)
        # os.close(doctmp_f)
        # csptest_path = 'C:\\Program Files (x86)\\Crypto Pro\\CSP\\csptest.exe'
        # if not os.path.exists(csptest_path):
        #     csptest_path = 'C:\\Program Files\\Crypto Pro\\CSP\\csptest.exe'
        # signtmp_f, signtmp_fn = tempfile.mkstemp()
        # os.close(signtmp_f)
        # args = [csptest_path, '-lowsign', '-sign', '-detached',
        #         '-in', os.path.abspath(doctmp_fn), '-out', signtmp_fn,
        #         '-add', '-base64', '-signature', p7stmp_fn,
        #         '-my', 'Администрация Уссурийского городского округа']
        # print(' '.join(args))
        # try:
        #     out = subprocess.check_output(args, stderr=subprocess.STDOUT)
        #     print(out)
        # except subprocess.CalledProcessError as e:
        #     print(e.output.decode(encoding='cp866'))
        # os.rename(signtmp_fn, path.join(path.dirname(signtmp_fn), 'doc.pdf.p7s'))
        # os.rename(p7stmp_fn, path.join(path.dirname(p7stmp_fn), 'doc.pdf.sig'))
        # os.rename(doctmp_fn, path.join(path.dirname(doctmp_fn), 'doc.pdf'))

    # procs = dis.search('ПРОУ', 'Kod2=%s' % 178609, order_by='Дата4',
    #                    ascending=False)
    # for proc in procs:
    #     if proc.get('Ведущая аналитика') == '3863571':
    #         res = dis.get_bind_docs('ПРОУ', proc.get('ИДЗапГлавРазд'))
    #         if res:
    #             # doc_id = res[0].get('ID')
    #             # res = dis.get_doc_versions(doc_id)
    #             # res = dis.get_doc(doc_id, res[0])
    #             print(proc.get('ИДЗапГлавРазд'), res)
    #             # print(res)
