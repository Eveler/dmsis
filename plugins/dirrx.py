# -*- coding: utf-8 -*-
import base64
import datetime
import logging
from datetime import timedelta
import os
from tempfile import mkstemp

from holidays import country_holidays
from numpy import busday_offset
# import requests
# import pyodata
from odata import ODataService, ODataError
from odata.property import SortOrder
from requests.auth import HTTPBasicAuth

from soapfish import xsd
from soapfish.xsd_types import XSDDate


def add_weekdays(start_date, days: int):
    import operator
    op = operator.sub if days < 0 else operator.add
    days_moved, end_date = 0, start_date

    while days_moved < abs(days):
        end_date = op(end_date, datetime.timedelta(days=1))
        if end_date.isoweekday() < 6:
            days_moved += 1

    return end_date


class DirectumRXException(Exception):
    def __init__(self, msg, *args, **kwargs):
        super().__init__(msg, args, kwargs)

    @property
    def message(self):
        return self.args[0]


class DirectumRX:
    REF = None
    __d_rx_ref_translate = {"ДПУ": 'IMunicipalServicesServiceCases',
                            'ПРС': 'IPersons',
                            'ВМУ': 'IMunicipalServicesServiceKinds',
                            'ОРГ': 'ICompanies',
                            'ТКД_ПРОЧИЕ': 'IAddendums',  # 'SimpleDocument', 'OfficialDocument'
                            'ELK_STATUS': 'IMunicipalServicesUPAStatuses',
                            'СтартЗадачПоМУ': 'MunicipalServices/StartDeclar'
                            }
    __d_rx_crit_translate = {"ИД": "Id",
                             "СпособДост": "DeliveryMethod/Id",
                             "Дата3": "ServBegDateFact",
                             "Дата5": "ServEndDateFact",
                             "LongString56": "NumELK",
                             "ID": "Id"}

    def __init__(self, url, username='', password=''):
        # Increase logging level by one step to filter unneeded messages from odata module
        logging.getLogger('odata.connection').setLevel(logging.getLogger().level + logging.DEBUG)
        logging.getLogger('odata.metadata').setLevel(logging.getLogger().level + logging.DEBUG)
        logging.getLogger('odata.context').setLevel(logging.getLogger().level + logging.DEBUG)

        my_auth = HTTPBasicAuth(username, password) if username else None
        self._service = ODataService(url, auth=my_auth, reflect_entities=True)

    @staticmethod
    def adopt_str(in_str):
        if in_str and isinstance(in_str, str):
            return (in_str.replace('\0', '').replace('\a', '').replace('\b', '').
                    replace('\t', ' ' * 4).replace('\n', ' ').replace('\v', ' ').
                    replace('\f', ' ').replace('\r', ' ').replace('\\', r'\\').
                    replace('"', r''))
        else:
            return in_str

    def add_individual(self, person):
        pers = self._service.entities['IPersons']()
        pers.FirstName = self.adopt_str(person.first_name)
        pers.LastName = self.adopt_str(person.surname)
        pers.MiddleName = self.adopt_str(person.patronymic)
        pers.LegalAddress = self.adopt_str(str(person.address)[:498]) if person.address else None
        pers.PostalAddress = self.adopt_str(str(person.fact_address)[:498]) if person.fact_address else None
        pers.DateOfBirth = person.birthdate
        pers.TIN = self.adopt_str(person.inn)
        # pers.Note = 'Паспорт серия %s № %s выдан %s %s' % (
        #     person.passport_serial, person.passport_number, person.passport_date.strftime("%d.%m.%Y"),
        #     person.passport_agency)
        try:
            phones = ', '.join(phone.phone for phone in person.phone)
            pers.Phones = self.adopt_str(phones[:248])
        except:
            try:
                phones = ', '.join(person.phone)
                pers.Phones = self.adopt_str(phones[:248])
            except:
                try:
                    pers.Phones = self.adopt_str(str(person.phone)[:248])
                except:
                    pass
        try:
            email = ', '.join(email.email for email in person.email)
            pers.Email = self.adopt_str(email[:248])
        except:
            try:
                email = ', '.join(person.email)
                pers.Email = self.adopt_str(email[:248])
            except:
                try:
                    pers.Email = self.adopt_str(str(person.email)[:248])
                except:
                    pass
        pers.Sex = "Male" if person.sex == 'Муж' else 'Female'
        pers.INILA = self.adopt_str(person.snils)
        pers.Status = "Active"
        pers.Name = self.adopt_str('%s %s %s' % (person.surname, person.first_name, person.patronymic))
        pers.ShortName = self.adopt_str('%s %s.%s.' % (person.surname, person.first_name[0].upper(),
                                        person.patronymic[0].upper() if person.patronymic else ''))
        pers.CanExchange = False
        pers.Nonresident = False
        self._service.save(pers)

        pers_info = self._service.entities['IAUGOPartiesPersonAddInfos']()
        pers_info.Person = pers
        pers_info.Status = 'Active'
        pers_info.Series = person.passport_serial
        pers_info.Number = person.passport_number
        pers_info.IssueDate = datetime.datetime.strptime(person.passport_date.strftime("%Y-%m-%d"), "%Y-%m-%d")
        pers_info.Issued = person.passport_agency
        self._service.save(pers_info)

        logging.info('Добавлен заявитель ФЛ: %s, регистрация: %s, Id: %s' % (pers.Name, pers.LegalAddress, pers.Id))
        return pers

    def add_legal_entity(self, entity):
        corr = self._service.entities['ICompanies']()
        corr.Name = self.adopt_str(entity.name[:248] if entity.name else entity.full_name[:248])
        if not corr.Name:
            raise DirectumRXException("Company name must be filled")
        corr.LegalName = self.adopt_str(entity.full_name[:498])
        corr.TIN = self.adopt_str(entity.inn)
        corr.TRRC = self.adopt_str(entity.kpp)
        corr.LegalAddress = self.adopt_str(str(entity.address)[:499]) if entity.address else None
        corr.Note = 'By integration'
        corr.Status = 'Active'
        self._service.save(corr)
        logging.info('Добавлен заявитель ЮЛ: %s' % (entity.name if entity.name else entity.full_name))
        return corr

    def add_declar(self, declar, files):
        oper_name = "Добавлено"
        data = self.search(
            "IMunicipalServicesServiceCases",
            "(RegistrationNumber eq '%s' or SMEVNumber eq '%s') and MFCRegDate eq %s" %
            (declar.declar_number, declar.declar_number,
             declar.register_date.strftime("%Y-%m-%d")), raw=False)
        if data:
            oper_name = "Обновлено"
            data = data[0]
        else:
            data = self._service.entities['IMunicipalServicesServiceCases']()
            # Individual
            apps_p = []
            if len(declar.person) > 0:
                for person in declar.person:
                    search_str = "LastName eq '%s' and FirstName eq '%s'%s%s" % (
                        person.surname, person.first_name,
                        " and MiddleName eq '%s'" % person.patronymic if person.patronymic else '',
                        " and ((PostalAddress eq '%(addr)s' or PostalAddress eq null) or "
                        "(LegalAddress eq '%(addr)s' or LegalAddress eq null))" % {"addr": person.address})
                    persons = self.search('IPersons', search_str, raw=False)
                    if persons:
                        if persons[0].Status != "Active":
                            persons[0].Status = "Active"
                            self._service.save(persons[0])
                        apps_p.append(persons[0])
                    else:
                        apps_p.append(self.add_individual(person))
                res = self.search("ICounterparties", "Id eq %s" % apps_p[0].Id, raw=False)
                data.Correspondent = res[0]  # Required "Заявитель"
                data.AppCategory = "PhPerson"
            # LegalEntity
            apps_le = []
            if len(declar.legal_entity):
                for entity in declar.legal_entity:
                    res = self.search('ICompanies', "%s%s%s" %
                                      ("LegalName eq '%s'" % entity.full_name if entity.full_name else '',
                                       "%sName eq '%s'" % (" or " if entity.full_name else '',
                                                           entity.name if entity.name else ''),
                                       " or TIN eq '%s'" % entity.inn if entity.inn else ''), raw=False)
                    if res:
                        if res[0].Status != "Active":
                            res[0].Status = "Active"
                            self._service.save(res[0])
                        apps_le.append(res[0])
                    else:
                        apps_le.append(self.add_legal_entity(entity))
                res = self.search("ICounterparties", "Id eq %s" % apps_le[0].Id, raw=False)
                data.Correspondent = res[0]  # Required "Заявитель"
                data.AppCategory = "LegPers"
            service_kind = self.search('IMunicipalServicesServiceKinds',
                              "Code eq '%(cod)s'" % {"cod": declar.service}, raw=False)
            if not service_kind:
                service_kind = self.search('IMunicipalServicesServiceKinds',
                                  "contains(ShortName,'%(cod)s') or contains(FullName,'%(cod)s')" %
                                  {"cod": declar.service}, raw=False)
            if not service_kind:
                raise DirectumRXException("Услуга не найдена")
            data.ServiceKind = service_kind[0]  # Required "Услуга"
            now = datetime.datetime.now()
            holidays = [day[0] for day in country_holidays("RU", years=[now.year, now.year + 1]).items()]
            now = busday_offset(now.date(), service_kind[0].ProvisionTerm, roll='forward', holidays=holidays).astype(datetime.datetime) \
                if service_kind[0].TermType == 'WorkDays' \
                else (now + timedelta(days=service_kind[0].ProvisionTerm))
            if now in holidays or now.weekday() > 5:
                now = busday_offset(now.date(), 1, roll='forward', holidays=holidays).astype(datetime.datetime)
            now = datetime.datetime(now.year, now.month, now.day)

            # if res[0].RegistrationGroup:
            #     data.Department = self.search("IDepartments", "Id eq %s" % res[0].RegistrationGroup.Id, raw=False)[0]
            # res = self.search("IEmployees", "Id eq %s" % res[0].ServPerformer.Id, raw=False)[0]
            # data.Addressee = res
            # res = self.search("IDepartments", "Id eq %s" % res.Department.Id, raw=False)
            # if res:
            #     data.AddresseeDep = res[0]
            #     if res[0].BusinessUnit:
            #         res = self.search("IBusinessUnits", "Id eq %s" % res[0].BusinessUnit.Id, raw=False)
            #         if res:
            #             data.BusinessUnit = res[0]

            res = self.search('IMailDeliveryMethods', "Name eq 'СМЭВ'", raw=False)
            data.DeliveryMethod = res[0]  # Required "Способ доставки"
            res = self.search('IDocumentRegisters', "Name eq 'Дела по оказанию муниципальных услуг'", raw=False)
            data.DocumentRegister = res[0]  # Required "Журнал регистрации"
            data.RegistrationNumber = self.adopt_str(declar.declar_number[:49])
            data.Subject = self.adopt_str(
                str(declar.object_address)[:249] if declar.object_address else "Приморский край, г. Уссурийск")
            data.HasRelations = False
            data.HasVersions = False  # Required
            data.VersionsLocked = False  # Required
            data.HasPublicBody = False  # Required
            data.Name = self.adopt_str(
                "Дело по оказанию услуг №%s от %s" %
                (declar.declar_number, declar.register_date.strftime("%d.%m.%Y")))  # Required
            data.MFCRegDate = datetime.datetime(
                declar.register_date.year, declar.register_date.month, declar.register_date.day) \
                if isinstance(declar.register_date, (XSDDate, xsd.Date)) else declar.register_date  # Required
            data.RegistrationDate = datetime.datetime.now()  # Required "Дата регистрации в органе"
            data.Created = datetime.datetime.now()  # Required "Создано"
            data.ServiceEndPlanData = now  # Required
            data.SMEVNumber = data.RegistrationNumber
            # return self._service.save(data)
            url = data.__odata_url__()
            if url is None:
                msg = 'Cannot insert Entity that does not belong to EntitySet: {0}'.format(data)
                raise ODataError(msg)
            es = data.__odata__
            insert_data = es.data_for_insert()

            if len(apps_le) > 1:
                insert_data["ApplicantsLE"] = [{"Id": a.Id} for a in apps_le if a != data.Correspondent]
            if len(apps_p) > 1:
                insert_data["ApplicantsPP"] = [{"Id": a.Id} for a in apps_p if a != data.Correspondent]
            # # insert_data["Addressees"] = [{"Id": data.Addressee.Id, "Number": 1}]

            saved_data = self._service.default_context.connection.execute_post(url, insert_data)
            es.reset()
            es.connection = self._service.default_context.connection
            es.persisted = True
            if saved_data is not None:
                es.update(saved_data)
                logging.info('%s дело № %s от %s ID = %s ID услуги = %s' %
                             (oper_name, declar.declar_number, declar.register_date.strftime('%d.%m.%Y'), data.Id, service_kind[0].Id))
            else:
                return False
        doc_ids = []
        if hasattr(declar, "AppliedDocument") and declar.AppliedDocument:
            for doc in declar.AppliedDocument:
                s_str = "contains(Name,'%s') and LeadingDocument/Id eq %s" % (doc.title[:249], data.Id)
                res = self.search('IAddendums', s_str)
                if not res:
                    res = self.__upload_doc(None, doc, files, declar, lead_doc=data)
                    # doc_ids.append(str(res))
        elif files:
            class D:
                pass
            was_error = False
            for file_name, file_path in files.items():
                fn, ext = os.path.splitext(file_name)
                with open(file_path, 'rb') as f:
                    doc_data = (f.read(), ext[1:].lower() if ext else 'txt')
                os.remove(file_path)
                doc = D()
                doc.number = ''
                doc.date = datetime.date.today()
                doc.title = fn
                try:
                    res = self.add_doc(doc, doc_data[1], doc_data[0], data)
                except:
                    was_error = True
                # doc_ids.append(str(res))
            if was_error:
                raise DirectumRXException("Не все документы загружены")

        # TODO: Send notification about new docs
        if doc_ids:
            params = [('ID', data.Id),
                      ('Doc_IDs', ';'.join(doc_ids))]
            res = self.run_script('notification_add_docs', params)
            logging.info('Отправлено уведомление ID = %s' % res)
        elif files:
            for file_name, file_path in files.items():
                try:
                    os.remove(file_path)
                except:
                    pass
        return data.Id

    def __upload_doc(self, doc_getter, doc, files, declar, i=0, lead_doc=None):
        doc_data = ()
        if doc_getter:
            doc_data = doc_getter(doc.url, doc.file_name)
        elif hasattr(doc, 'file') and doc.file:
            fn, ext = os.path.splitext(doc.file_name)
            with open(doc.file, 'rb') as f:
                doc_data = (f.read(), ext[1:].lower() if ext else 'txt')
        elif hasattr(declar, 'files') and declar.files:
            found = False
            for file_path, file_name in declar.files:
                if file_name.lower() == doc.file_name.lower():
                    found = file_path
            if not found:
                found, file_name = declar.files[i]
            fn, ext = os.path.splitext(doc.file_name)
            with open(found, 'rb') as f:
                doc_data = (f.read(), ext[1:] if ext else 'txt')
        elif files:
            file_name = doc.file_name if doc.file_name else doc.url
            fn, ext = os.path.splitext(file_name)
            found = files.get(file_name)
            if not found:
                found = files.get(fn + '.zip')
                ext = '.zip'
            if not found:
                found = files.get(fn + '..zip')
                ext = '.zip'
            if not found:
                raise DirectumRXException("Cannot find file '%s' in %s" % (file_name, files))
            try:
                with open(found, 'rb') as f:
                    doc_data = (f.read(), ext[1:].lower() if ext else 'txt')
                os.remove(found)
            except FileNotFoundError:
                logging.warning("Cannot find file '%s'" % file_name, exc_info=True)
                if not doc_data:
                    doc_data = (b'No file', 'txt')
        else:
            doc_data = (b'No file', 'txt')
        res = self.add_doc(doc, doc_data[1], doc_data[0], lead_doc)
        return res

    def run_script(self, script_name, params=(), entity=None):
        script_name = self.__dir_ref_subst(script_name)
        if isinstance(params, dict):
            params = {self.__d_rx_crit_translate[key] if key in self.__d_rx_crit_translate else key: val
                      for key, val in params.items()}
        else:
            params = {self.__d_rx_crit_translate[key] if key in self.__d_rx_crit_translate else key: val
                      for key, val in params}
        res = None
        if entity:
            if isinstance(entity, str):
                entity = self._service.entities[entity]
            func = getattr(entity, script_name)
            try:
                res = func(**params)
            except:
                logging.warning("Error call %s(%s)" % (script_name, ', '.join(
                    ["%s=%s" % (key, val) for key, val in params.items()])), exc_info=True)
        else:
            if script_name in self._service.functions or script_name in self._service.actions:
                func = self._service.functions[script_name] if script_name in self._service.functions \
                    else self._service.actions[script_name]
                try:
                    res = func(**params)
                except:
                    logging.warning("Error call %s(%s)" % (script_name, ', '.join(
                        ["%s=%s" % (key, val) for key, val in params.items()])), exc_info=True)
            else:
                # https://rxtest.adm-ussuriisk.ru/Integration/odata/MunicipalServices/StartDeclar(Id=315)
                params = ["%s=%s" % (key, "'%s'" % val if isinstance(val, str) else val)
                          for key, val in params.items()]
                func = "%s%s(%s)" % (self._service.url, script_name, ', '.join(params))
                try:
                    res = self._service.default_context.connection.execute_get(func)
                except:
                    logging.warning("Error call %s(%s)" % (script_name, ', '.join(params)), exc_info=True)
        return res

    def __dir_ref_subst(self, name):
        if name in self.__d_rx_ref_translate:
            name = self.__d_rx_ref_translate[name]
        return name

    def search(self, code, criteria, tp=REF, order_by='', ascending=True, raw=True):
        if isinstance(criteria, str):
            for key, val in self.__d_rx_crit_translate.items():
                if key in criteria:
                    criteria = criteria.replace(key, val)
            for f, t in (('<>', ' ne '), ('<=', ' le '), ('>=', ' ge '), ('=', ' eq '), ('<', ' lt '),
                         ('>', ' gt '), (' is ', ' eq ')):
                if f in criteria:
                    criteria = criteria.replace(f, t)

        code = self.__dir_ref_subst(code)
        try:
            entity = self._service.entities[code]
        except KeyError:
            logging.debug(self._service.entities.keys())
            raise
        query = self._service.query(entity)
        if raw:
            query_params = {'$expand': '*'}
            if criteria:
                query_params['$filter'] = criteria
            if order_by:
                query_params['$orderby'] = order_by + (' asc' if ascending else ' desc')
            return query.raw(query_params)
        else:
            query.options['$expand'] = ['*']
            if criteria:
                query.options['$filter'] = [criteria]
            if order_by:
                query.options['$orderby'] = [order_by] if isinstance(order_by, SortOrder) \
                    else [order_by + (' asc' if ascending else ' desc')]
            return query.all()

    def get_result_docs(self, directum_id, crt_name='Администрация Уссурийского городского округа',
                        zip_signed_doc=False, days_old=-3):
        class DocumentInfo(object):
            date = None
            file_name = None
            number = None
            title = None
            file = None
            certs = None

        def make_doc(data):
            data = self.search("IOfficialDocuments", "Id eq %s" % data['Id'], raw=False)
            if data:
                data = data[0]
            else:
                raise DirectumRXException("Document ID=%s not found" % data['Id'])
            ad = DocumentInfo()
            ad.date = data.RegistrationDate if hasattr(data, "RegistrationDate") and data.RegistrationDate else data.Created
            ad.file_name = "%s.%s" % (data.Id, data.AssociatedApplication.Extension)
            ad.number = data.RegistrationNumber
            ad.title = data.Subject
            # Get only last version
            i = len(data.Versions) - 1
            v_num = 0
            while i >= 0:
                if not data.Versions[i].IsHidden and v_num < data.Versions[i].Number:
                    v_num = data.Versions[i].Number
                    file, file_n = mkstemp()
                    try:
                        version = self._service.default_context.connection.execute_get(
                            "%s/Versions(%s)?$expand=Body" % (data.__odata__.instance_url, data.Versions[i].Id))
                        logging.debug(version)
                        os.write(file, base64.b64decode(version.get('Body', {}).get('Value', '')))
                        os.close(file)
                        # TODO: certs = clean_pkcs7(self.run_script('GetEDocCertificates', [('DocID', doc_id)]), crt_name)
                        certs = None
                        if zip_signed_doc and certs:
                            from smev import Adapter
                            ad.file = Adapter.make_sig_zip(ad.file_name, file_n, certs)
                        else:
                            ad.file = file_n
                            ad.certs = certs
                    except:
                        logging.error("Error loading resulting document %s" % data.Name, exc_info=True)
                        os.close(file)
                        os.remove(file_n)
                i -= 1
            return ad

        declar = self.search("IMunicipalServicesServiceCases", "Id eq %s" % directum_id, raw=False)
        if not declar:
            return declar
        applied_docs = []
        for doc in declar[0].ResultDocument:
            doc = self._service.default_context.connection.execute_get(
                "%s/ResultDocument(%s)?$expand=*" % (declar[0].__odata__.instance_url, doc.Id))
            if doc['Document']:
                applied_docs.append(make_doc(doc['Document']))
        return applied_docs

    def get_declar_status_data(self, declar_id=None, fsuids: list = (), permanent_status='6'):
        declar = self.search("IMunicipalServicesServiceCases", "Id eq %s" % declar_id, raw=False)
        if declar:
            declar = declar[0]
        else:
            return []
        if not permanent_status:
            status = declar.UPAStatus.Id
        else:
            status = permanent_status

        attachments = []
        for fsuuid in fsuids:
            attachments.append({'attachment': {'FSuuid': ''.join(fsuuid.keys()) if isinstance(fsuuid, dict) else fsuuid,
                                               'docTypeId': 'ELK_RESULT'}})

        res = []
        if declar.NumELK:
            order = {'orderNumber': declar.RegistrationNumber[:36], 'senderKpp': '251101001',
                     'senderInn': '2511004094',
                     'statusHistoryList':
                         {'statusHistory': {'status': status,
                                            # 'statusDate': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+10:00')}}}
                                            'statusDate': (datetime.datetime.now() + timedelta(hours=-10)).strftime(
                                                '%Y-%m-%dT%H:%M:%S')}}}
            if attachments:
                order['attachments'] = attachments
            res.append({'order': order})
            return res

        service_kind = self.search("IMunicipalServicesServiceKinds",
                                   "Id eq %s" % declar.ServiceKind.Id, raw=False)[0]
        while (service_kind.LeadServiceKind and hasattr(service_kind.LeadServiceKind, "Id")
               and service_kind.LeadServiceKind.Id):
            srv = self.search('IMunicipalServicesServiceKinds',
                              "Id eq %s" % service_kind.LeadServiceKind.Id, raw=False)
            if srv:
                service_kind = srv[0]
        if len(service_kind.Code) < 12: # Skip non federal services
            return res

        # Get persons
        users = []
        for fl in declar.ApplicantsPP:
            applicant = self._service.default_context.connection.execute_get(
                "%s/ApplicantsPP(%s)?$expand=*" % (declar.__odata__.instance_url, fl.Id))
            if applicant['Applicant']:
                series = num = None
                add_info = self.search(
                    "IAUGOPartiesPersonAddInfos", "Person/Id eq %s" % applicant['Applicant']['Id'], raw=False)
                if add_info:
                    add_info = add_info[0]
                    series = add_info.Series
                    num = add_info.Number
                if applicant['Applicant']['TIN'] or (series and num) or applicant['Applicant']['INILA']:
                    if series and num:
                        user = {'userPersonalDoc': {
                            'PersonalDocType': '1', 'series': series, 'number': num,
                            'lastName': applicant['Applicant']['LastName'],
                            'firstName': applicant['Applicant']['FirstName'],
                            'middleName': applicant['Applicant']['MiddleName'], 'citizenship': '643'}}
                    elif applicant['Applicant']['INILA']: # SNILS
                        if applicant['Applicant']['DateOfBirth']:
                            user = {'userDocSnilsBirthDate': {
                                'citizenship': '643', 'snils': applicant['Applicant']['INILA'].strip(),
                                'birthDate': applicant['Applicant']['DateOfBirth'][:10]}}
                        else:
                            user = {'userDocSnils': {
                                'snils': applicant['Applicant']['INILA'].strip(),
                                'lastName': applicant['Applicant']['LastName'],
                                'firstName': applicant['Applicant']['FirstName'],
                                'middleName': applicant['Applicant']['MiddleName'], 'citizenship': '643'}}
                    elif applicant['Applicant']['TIN']: # INN
                        user = {'userDocInn': {
                            'INN': applicant['Applicant']['TIN'].strip(),
                            'lastName': applicant['Applicant']['LastName'],
                            'firstName': applicant['Applicant']['FirstName'],
                            'middleName': applicant['Applicant']['MiddleName'], 'citizenship': '643'}}
                    else:
                        raise DirectumRXException("User %s %s %s (%s) has no passport nor INN nor SNILS" % (
                            applicant['Applicant']['LastName'],
                            applicant['Applicant']['FirstName'],
                            applicant['Applicant']['MiddleName'],
                            applicant['Applicant']['Id']))
                    users.append(user)
        # Get organisations
        orgs = []
        for ul in declar.ApplicantsLE:
            applicant = self._service.default_context.connection.execute_get(
                "%s/ApplicantsLE(%s)?$expand=*" % (declar.__odata__.instance_url, ul.Id))
            if applicant['Applicant']:
                if applicant['Applicant']['TIN'] and len(applicant['Applicant']['TIN']) == 10:
                    orgs.append({'ogrn_inn_UL': {'inn_kpp': {'inn': applicant['Applicant']['TIN'].strip()}}})
                elif applicant['Applicant']['PSRN']:
                    orgs.append({'ogrn_inn_UL': {'ogrn': applicant['Applicant']['PSRN'].strip()}})

        if users or orgs:
            for user in users:
                number = declar.RegistrationNumber if declar.RegistrationNumber else declar.SMEVNumber
                number = number[len(number) - 36 if len(number) > 36 else 0:]
                order = {'user': user, 'senderKpp': '251101001', 'senderInn': '2511004094',
                         'serviceTargetCode': service_kind.Code, 'userSelectedRegion': '00000000',
                         'orderNumber': number,
                         'requestDate': declar.RegistrationDate.strftime('%Y-%m-%dT%H:%M:%S')
                         if declar.RegistrationDate else declar.MFCRegDate.strftime('%Y-%m-%dT%H:%M:%S')
                         if declar.MFCRegDate else declar.Created.strftime('%Y-%m-%dT%H:%M:%S'),
                         'OfficeInfo': {'ApplicationAcceptance': '4'
                                        # ЕЛК. Канал приема - Подразделение ведомства (https://esnsi.gosuslugi.ru/classifiers/7213/view/8)
                                        },
                         'statusHistoryList': {'statusHistory': {
                             'status': status,
                             # 'statusDate': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+10:00')}}}
                             'statusDate': (datetime.datetime.now() + timedelta(hours=-10)).strftime(
                                 '%Y-%m-%dT%H:%M:%S')}}}
                if attachments:
                    order['attachments'] = attachments
                res.append({'order': order})
            for org in orgs:
                order = {'organization': org, 'senderKpp': '251101001', 'senderInn': '2511004094',
                         'serviceTargetCode': service_kind.Code, 'userSelectedRegion': '00000000',
                         'orderNumber': declar.RegistrationNumber,
                         'requestDate': declar.RegistrationDate.strftime('%Y-%m-%dT%H:%M:%S'),
                         'OfficeInfo': {'ApplicationAcceptance': '4'
                                        # ЕЛК. Канал приема - Подразделение ведомства (https://esnsi.gosuslugi.ru/classifiers/7213/view/8)
                                        },
                         'statusHistoryList': {'statusHistory': {
                             'status': status,
                             # 'statusDate': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+10:00')}}}
                             'statusDate': (datetime.datetime.now() + timedelta(hours=-10)).strftime(
                                 '%Y-%m-%dT%H:%M:%S')}}}
                if attachments:
                    order['attachments'] = attachments
                res.append({'order': order})
        return res

    def update_reference(self, ref_name, rec_id=None, data: list = None):
        ref_name = self.__dir_ref_subst(ref_name)
        if rec_id:
            ref = self.search(ref_name, 'Id eq %s' % rec_id, raw=False)
            if ref:
                ref = ref[0]
            logging.debug("Found ref: %s" % ref)
        else:
            ref = self._service.entities[ref_name]()
        if data:
            for req in data:
                key = req["Name"]
                val = req.get("Value")
                if isinstance(val, str):
                    val = self.adopt_str(val)
                ref.__setattr__(key, val)
        res = self._service.save(ref)
        logging.debug("Save result: %s" % res)
        return res

    def update_elk_status(self, data):
        if not data and not isinstance(data, dict):
            return
        code_values = name_values = []
        for key, value in data.items():
            if value['name'] == 'Код':
                code_values = value['values']
            if value['name'] == 'Наименование':
                name_values = value['values']
        index = 0
        while index < len(code_values):
            res = self.search('IMunicipalServicesUPAStatuss', "StatusID eq '%s'" % code_values[index], raw=False)
            if not res:
                elk = self._service.entities['IMunicipalServicesUPAStatuss']()
                elk.Name = name_values[index]
                elk.StatusID = code_values[index]
                name = elk.Name.lower()
                elk.Type = "Final" if "оказан" in name or "отказ" in name else "AtWork"
                elk.Status = "Active"
                self._service.save(elk)
            else:
                for r in res:
                    if r.Name != name_values[index]:
                        r.Name = name_values[index]
                        self._service.save(r)
            index += 1

    def add_doc(self, requisites, data_format, data, lead_doc=None):
        doc = self._service.entities['IAddendums']()
        doc_date = datetime.datetime(requisites.date.year, requisites.date.month, requisites.date.day) \
            if isinstance(requisites.date, (XSDDate, xsd.Date)) else requisites.date
        doc.Name = self.adopt_str("%s%s%s" % (
            requisites.title if len(requisites.title) < 250 else
            "%s..." % requisites.title[:246 - (len(" № %s" % requisites.number) if requisites.number else 0) -
                                        (len(" от %s" % doc_date) if doc_date else 0)],
            " № %s" % requisites.number if requisites.number else '', " от %s" % doc_date if doc_date else ''))
        doc.HasRelations = False
        doc.HasVersions = True  # Required
        doc.VersionsLocked = False  # Required
        doc.HasPublicBody = False  # Required
        doc.Created = datetime.datetime.now()
        doc.Subject = requisites.title[:240]
        doc.LeadingDocument = lead_doc
        res = self.search("IDocumentKinds", "Id eq 3", raw=False)
        doc.DocumentKind = res[0]
        self._service.save(doc)
        try:
            res = self.search("IAssociatedApplications", "Extension eq '%s'" % data_format, raw=False)
            if not res:
                self.search("IAssociatedApplications", "Extension eq 'txt'", raw=False)
            ver_num = 0
            while ver_num < 5:
                ver_num += 1
                doc.Versions = [{"Number": 1, "AssociatedApplication": {"Id": res[0].Id}}]
                try:
                    self._service.save(doc)
                    ver_num = 5
                except ODataError:
                    if ver_num == 5:
                        raise
                    pass
            doc = self.search("IAddendums", "Id eq %s" % doc.Id, raw=False)[0]
            self._service.default_context.connection.execute_post(
                "%s/Versions(%s)/Body" % (doc.__odata__.instance_url, doc.Versions[0].Id),
                {"Value": base64.b64encode(data).decode()})
            logging.info('Добавлен документ: %s № %s от %s Id = %s' % (doc.Name, requisites.number,
                                                                    requisites.date.strftime('%d.%m.%Y'), doc.Id))
        except ODataError:
            logging.error("Ошибка сохранения документа %s № %s от %s" % (requisites.title, requisites.number,
                                                                           requisites.date.strftime('%d.%m.%Y')),
                            exc_info=True)
            self._service.delete(doc)
            raise
        return doc.Id


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)s:%(module)s(%(lineno)d): %(levelname)s: '
               '%(message)s')

    # session = requests.Session()
    # session.auth = ('Savenko', 'mY3pss2augo')
    # client = pyodata.Client("http://192.168.0.134/Integration/odata/", session)
    # client = pyodata.Client("http://rxtest.adm-ussuriisk.ru/Integration/odata/", session)

    # http://192.168.0.134/Integration/odata/IMunicipalServicesServiceCases?$expand=*&$count=true&$filter=ServEndDateFact%20eq%20null

    url = "https://rxtest.adm-ussuriisk.ru/Integration/odata/"
    rx = DirectumRX(url, 'Service User', '[1AnAr1]')
    # class Declar:
    #     person = []
    #     class LE:
    #         full_name = ''
    #         name = 'АйТиСи'
    #         inn = ''
    #     legal_entity = [LE()]
    #     declar_number = 'SMEV_TEST'
    #     register_date = datetime.datetime.now()
    #     object_address = "г.Уссурийск, ул. Космонавтов, д.15"
    # res = rx.add_declar(Declar(), '')
    # print(res)
    # exit()
    # res = rx.run_script('MunicipalServices/StartDeclar', {"Id": 340})
