# -*- coding: utf-8 -*-
from datetime import date, datetime
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

    def add_declar(self, declar, doc_getter=None):
        """
        Saves `declar` to Directum reference 'ДПУ' and binds `docs` to it. Creates appropriate records for 'ПРС' and 'ОРГ' if needed. If record already exists simply add not existing documents

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
            for doc in declar.AppliedDocument:
                res = self.search(
                    'ТКД_ПРОЧИЕ',
                    "ISBEDocName like '%%%s%%' and NumberEDoc='%s' "
                    "and Дата4='%s'" %
                    (doc.title, doc.number, doc.date.strftime('%d.%m.%Y')))
                if not len(res):
                    doc_data = doc_getter(doc.url, doc.file_name) \
                        if doc_getter else ('txt', '')
                    res = self.add_doc(doc, doc[1], doc_data[0])
        return res

        # Add new
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
        text = xml_package.createTextNode(declar.register_date)
        requisite.appendChild(text)
        section.appendChild(requisite)

        #  "Оконч. оказания услуги (ПЛАН)"
        requisite = xml_package.createElement("Requisite")
        requisite.setAttribute("Name", u"Дата4")
        requisite.setAttribute("Type", "String")
        text = xml_package.createTextNode(declar.end_date)
        requisite.appendChild(text)
        section.appendChild(requisite)

        # Запись
        rec = xml_package.createElement("Record")
        rec.setAttribute("ID", '')  # ИД
        rec.setAttribute("Action", "Change")
        rec.appendChild(section)

        # Объект
        obj = xml_package.createElement("Object")
        obj.setAttribute("Type", "Reference")  # Задаем атрибут "Тип"
        obj.setAttribute("Name", u'ДПУ')  # Дела по предоставлению услуг
        obj.appendChild(rec)

        dataexchangepackage = xml_package.createElement("DataExchangePackage")
        dataexchangepackage.appendChild(obj)

        xml_package.appendChild(dataexchangepackage)

        # 						//Формируем xml пакет по делу
        # 						//Заносим данные по реквизиту "Способ доставки"
        # 						XmlElement recvizitElement7 = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 						recvizitElement7.SetAttribute("Name", "СпособДост");
        # 						recvizitElement7.SetAttribute("Type", "Reference");
        # 						recvizitElement7.SetAttribute("ReferenceName", "СДК");
        # 						recvizitElement7.InnerText = "826965";
        # 						//Заносим данные по реквизиту "Адресат"
        # 						XmlElement recvizitElement6 = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 						recvizitElement6.SetAttribute("Name", "Подразделение");
        # 						recvizitElement6.SetAttribute("Type", "Reference");
        # 						recvizitElement6.SetAttribute("ReferenceName", "ПОД");
        # 						recvizitElement6.InnerText = "106759";
        # 						//Заносим данные по реквизиту "Место регистрации"
        # 						XmlElement recvizitElement5 = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 						recvizitElement5.SetAttribute("Name", "МестоРег");
        # 						recvizitElement5.SetAttribute("Type", "Reference");
        # 						recvizitElement5.SetAttribute("ReferenceName", "МРГ");
        # 						recvizitElement5.InnerText = "108279";
        # 						//Заносим данные по реквизиту "Статус оказания устуги"
        # 						XmlElement recvizitElement8 = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 						recvizitElement8.SetAttribute("Name", "ServiceState");
        # 						recvizitElement8.SetAttribute("Type", "Признак");
        # 						DateTime datein = DateTime.Parse(declar_datein);
        # //						if(archived || datein.Year < 2014){
        # 						if(archived || datein < DateTime.Parse("30.06.2015")){
        # 							recvizitElement8.InnerText = "Предоставлена";
        # 							if(declar_enddate != string.Empty){
        # 								XmlElement enddate = xmlDoc.CreateElement("Requisite");
        # 								enddate.SetAttribute("Name", "Дата5");
        # 								enddate.SetAttribute("Type", "String");
        # 								enddate.InnerText = declar_enddate;
        # 								sectionElement.AppendChild(enddate);
        # 							}
        # 						}
        # 						else recvizitElement8.InnerText = "Инициализация";
        # 						//Заносим данные по реквизиту "Вид услуги"
        # 						XmlElement recvizitElement9 = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 						recvizitElement9.SetAttribute("Name", "ServiceCode");
        # 						recvizitElement9.SetAttribute("Type", "Reference");
        # 						recvizitElement9.SetAttribute("ReferenceName", "ВМУ");
        # 						recvizitElement9.InnerText = directum_srvID;
        # 						//Заносим данные по реквизиту "Наша организация"
        # 						XmlElement recvizitElement10 = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 						recvizitElement10.SetAttribute("Name", "НашаОрг");
        # 						recvizitElement10.SetAttribute("Type", "Reference");
        # 						recvizitElement10.SetAttribute("ReferenceName", "НОР");
        # 						recvizitElement10.InnerText = "38838";

        #
        # 						//Создаем секцию для адреса объекта
        # 						XmlElement sectionElementObj = xmlDoc.CreateElement("Section");//Создаем подэллемент "Секция"
        # 						sectionElementObj.SetAttribute("Index", "9");//Задаем атрибут "Индекс"
        # 						XmlElement recordElementObj = xmlDoc.CreateElement("Record");//Создаем подэллемент запись
        # 						recordElementObj.SetAttribute("ID", "1");//Задаем атрибут "ID"
        # 						recordElementObj.SetAttribute("Action", "Change");//Задаем атрибут "Действие"
        # 						XmlElement sectionElementObj0 = xmlDoc.CreateElement("Section");//Создаем подэллемент "Секция"
        # 						sectionElementObj0.SetAttribute("Index", "0");//Задаем атрибут "Индекс"
        # 						//Заносим данные по реквизиту "Местоположение объекта"
        # 						XmlElement recvizitElementObj = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 						recvizitElementObj.SetAttribute("Name", "LongStringT9");
        # 						recvizitElementObj.SetAttribute("Type", "String");
        # 						recvizitElementObj.InnerText = object_addr.Length > 1023 ? object_addr.Substring(0, 1023) : object_addr;
        # 						sectionElementObj0.AppendChild(recvizitElementObj);
        # 						recordElementObj.AppendChild(sectionElementObj0);
        # 						sectionElementObj.AppendChild(recordElementObj);
        #
        # 						sectionElement.AppendChild(recvizitElement1);
        # 						sectionElement.AppendChild(recvizitElement2);
        # 						sectionElement.AppendChild(recvizitElement3);
        # 						sectionElement.AppendChild(recvizitElement4);
        # 						sectionElement.AppendChild(recvizitElement5);
        # 						sectionElement.AppendChild(recvizitElement6);
        # 						sectionElement.AppendChild(recvizitElement7);
        # 						sectionElement.AppendChild(recvizitElement8);
        # 						sectionElement.AppendChild(recvizitElement9);
        # 						sectionElement.AppendChild(recvizitElement10);
        # 						recordElement.AppendChild(sectionElement);
        # 						recordElement.AppendChild(sectionElementObj);
        #
        # 						//Создаем секцию для заявителей-физ.лиц
        # 						XmlElement sectionElementFiz = xmlDoc.CreateElement("Section");//Создаем подэллемент "Секция"
        # 						sectionElementFiz.SetAttribute("Index", "7");//Задаем атрибут "Индекс"
        # 						bool haveFiz=false;//Признак начилия заявителей физ. лиц
        #
        # 						//Создаем секцию для заявителей - юр.лиц
        # 						XmlElement sectionElementUr = xmlDoc.CreateElement("Section");//Создаем подэллемент "Секция"
        # 						sectionElementUr.SetAttribute("Index", "6");//Задаем атрибут "Индекс"
        # 						bool haveUr=false;//Признак наличия заявителей юр. лиц
        # 						//Заносим в xml файл данные о заявителях
        # 						for(int zayavNum=0; zayavNum<zayavDirID.Length; zayavNum++)//Перебираем массив идентификаторов заявителей
        # 						{
        # 							if (zayavType[zayavNum]==0)//Если заявитель - физ. лицо
        # 							{
        # 								XmlElement recordElementFizZay = xmlDoc.CreateElement("Record");//Создаем подэллемент запись
        # 								recordElementFizZay.SetAttribute("ID", Convert.ToString(zayavNum+1));//Задаем атрибут "ID"
        # 								recordElementFizZay.SetAttribute("Action", "Change");//Задаем атрибут "Действие"
        # 								XmlElement sectionElementFizZay0 = xmlDoc.CreateElement("Section");//Создаем подэллемент "Секция"
        # 								sectionElementFizZay0.SetAttribute("Index", "0");//Задаем атрибут "Индекс"
        # 								//Заносим данные по реквизиту "Гражданин"
        # 								XmlElement recvizitElementFizZay = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 								recvizitElementFizZay.SetAttribute("Name", "CitizenT7");
        # 								recvizitElementFizZay.SetAttribute("Type", "Reference");
        # 								recvizitElementFizZay.SetAttribute("ReferenceName", "ПРС");
        # 								recvizitElementFizZay.InnerText = zayavDirID[zayavNum];
        # 								sectionElementFizZay0.AppendChild(recvizitElementFizZay);
        # 								recordElementFizZay.AppendChild(sectionElementFizZay0);
        # 								sectionElementFiz.AppendChild(recordElementFizZay);
        # 								haveFiz=true;//Фиксируем наличие заявителя физ. лица
        # 							}
        # 							else//Если заявитель - юридическое лицо
        # 							{
        # 								XmlElement recordElementURZay = xmlDoc.CreateElement("Record");//Создаем подэллемент запись
        # 								recordElementURZay.SetAttribute("ID", Convert.ToString(zayavNum+1));//Задаем атрибут "ID"
        # 								recordElementURZay.SetAttribute("Action", "Change");//Задаем атрибут "Действие"
        # 								XmlElement sectionElementURZay0 = xmlDoc.CreateElement("Section");//Создаем подэллемент "Секция"
        # 								sectionElementURZay0.SetAttribute("Index", "0");//Задаем атрибут "Индекс"
        # 								//Заносим данные по реквизиту "Гражданин"
        # 								XmlElement recvizitElementURZay = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 								recvizitElementURZay.SetAttribute("Name", "OrgT6");
        # 								recvizitElementURZay.SetAttribute("Type", "Reference");
        # 								recvizitElementURZay.SetAttribute("ReferenceName", "ОРГ");
        # 								recvizitElementURZay.InnerText = zayavDirID[zayavNum];
        # 								sectionElementURZay0.AppendChild(recvizitElementURZay);
        # 								recordElementURZay.AppendChild(sectionElementURZay0);
        # 								sectionElementUr.AppendChild(recordElementURZay);
        # 								haveUr=true;//Фиксируем наличие заявителя юр. лица
        # 							}
        # 						}
        #
        # 						if(haveFiz==true)//Если есть заявители - физические лица
        # 						{
        # 							recordElement.AppendChild(sectionElementFiz);//Добавялем секцию к xml файлу
        # 						}
        # 						if(haveUr==true)//Еслие есть заявители - юридические лица
        # 						{
        # 							recordElement.AppendChild(sectionElementUr);//Добавляем секцию к файлу
        # 						}
        # 						objectElement.AppendChild(recordElement);
        # 						dataExchangePackageElement.AppendChild(objectElement);
        # 						xmlDoc.AppendChild(dataExchangePackageElement);
        # 						//Заносим данные по реквизиту "Услуга платная"
        # 						XmlElement recvizitElement4 = xmlDoc.CreateElement("Requisite");//Создаем подэллемент "Реквизит"
        # 						recvizitElement4.SetAttribute("Name", "ДаНет");
        # 						recvizitElement4.SetAttribute("Type", "Признак");
        # 						recvizitElement4.InnerText = "Нет";

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
        for oper in opers.keys():
            if oper in criteria.lower():
                idx = criteria.lower().index(oper)
                elem = doc.createElement(opers.get(oper))
                elem.setAttribute('Requisite', criteria[:idx].strip())
                elem.setAttribute('Value',
                                  get_val(criteria, idx + len(oper)))
                doc.unlink()
                return elem


if __name__ == '__main__':
    from declar import Declar
    from soapfish import xsd

    d = Declar()
    d.declar_number = '111111'
    dt = xsd.Date()
    d.register_date = date(2014, 8, 8)
    wsdl = "http://servdir1:8083/IntegrationService.svc?singleWsdl"
    dis = IntegrationServices(wsdl)
    res = dis.add_declar(d)
    print(res[0]['ИДЗапГлавРазд'])
