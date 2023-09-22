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
                            'СтартЗадачПоМУ': 'StartDeclar'
                            }
    __d_rx_crit_translate = {"ИД": "Id",
                             "СпособДост": "DeliveryMethod",
                             "Дата3": "ServBegDateFact",
                             "Дата5": "ServEndDateFact",
                             "LongString56": "NumELK",
                             "ID": "Id"}

    def __init__(self, url, username='', password=''):
        my_auth = HTTPBasicAuth(username, password) if username else None
        self._service = ODataService(url, auth=my_auth, reflect_entities=True)

    def add_declar(self, declar, files):
        data = self.search("IMunicipalServicesServiceCases", "RegistrationNumber eq '%s' and MFCRegDate eq %s" %
                          (declar.declar_number, declar.register_date.strftime("%Y-%m-%dT00:00:00Z")), raw=False)
        if not data:
            data = self._service.entities['IMunicipalServicesServiceCases']()
            # data = [{"Name": 'Note', "Value": 'By integration'}]
            # Individual
            apps_p = []
            if len(declar.person) > 0:
                for person in declar.person:
                    res = self.search(
                        'IPersons',
                        "Status eq 'Active' and LastName eq '%s' and FirstName eq '%s'%s%s" %
                        (person.surname, person.first_name,
                         " and MiddleName eq '%s'" % person.patronymic if person.patronymic else '',
                         " and (LegalAddress eq '%s' or LegalAddress eq null)" % person.address), raw=False)
                data.ApplicantsPP = res
                # data.append({"Name": 'Correspondent', "Value": res[0]})
                raise "Not released yet"
            # LegalEntity
            apps_le = []
            if len(declar.legal_entity):
                for entity in declar.legal_entity:
                    res = self.search('ICompanies', "Status eq 'Active'%s%s%s" %
                                      (" and LegalName eq '%s'" % entity.full_name if entity.full_name else '',
                                       " and Name eq '%s'" % entity.name if entity.name else '',
                                       " and TIN eq '%s'" % entity.inn if entity.inn else ''), raw=False)
                    if res:
                        apps_le.append(res[0])
                    else:
                        # Create new company
                        corr = self._service.entities['ICompanies']()
                        corr.Name = entity.name if entity.name else entity.full_name
                        if not corr.Name:
                            raise DirectumRXException("Company name must be filled")
                        corr.LegalName = entity.full_name
                        corr.TIN = entity.inn
                        corr.TRRC = entity.kpp
                        corr.LegalAddress = entity.address
                        corr.Note = 'By integration'
                        corr.Status = 'Active'
                        self._service.save(corr)
                        apps_le.append(corr)
                res = self.search("ICounterparties", "Id eq %s" % apps_le[0].Id, raw=False)
                data.Correspondent = res[0]  # Required "Заявитель"
            res = self.search('IMunicipalServicesServiceKinds',
                              "Code eq '119' or contains(ShortName,'119') or contains(FullName,'119')", raw=False)
            data.ServiceKind = res[0]  # Required "Услуга"
            now = datetime.datetime.now()
            holidays = country_holidays("RU")
            now = busday_offset(now, res[0].ProvisionTerm, roll='forward', holidays=holidays) \
                if res[0].TermType == 'WorkDays' \
                else (now + timedelta(days=res[0].ProvisionTerm))
            if now in holidays or now.weekday() > 5:
                now = busday_offset(now, 1, roll='forward', holidays=holidays)
            res = self.search('IMailDeliveryMethods', "Name eq 'СМЭВ'", raw=False)
            data.DeliveryMethod = res[0]  # Required "Способ доставки"
            res = self.search('IDocumentRegisters', "Name eq 'Дела по оказанию муниципальных услуг'", raw=False)
            data.DocumentRegister = res[0]  # Required "Журнал регистрации"
            data.RegistrationNumber = declar.declar_number
            data.Subject = declar.object_address
            data.HasRelations = False
            data.HasVersions = False  # Required
            data.VersionsLocked = False  # Required
            data.HasPublicBody = False  # Required
            data.Name = ("Дело по оказанию услуг №%s от %s" %
                         (declar.declar_number, declar.register_date.strftime("%d.%m.%Y")))  # Required
            data.MFCRegDate = declar.register_date  # Required
            data.RegistrationDate = datetime.datetime.now()  # Required "Дата регистрации в органе"
            data.Created = datetime.datetime.now()  # Required "Создано"
            data.ServiceEndPlanData = now  # Required

            # rx.update_reference('IMunicipalServicesServiceCases', data=data)
            # return self._service.save(data)
            url = data.__odata_url__()
            if url is None:
                msg = 'Cannot insert Entity that does not belong to EntitySet: {0}'.format(data)
                raise ODataError(msg)
            es = data.__odata__
            insert_data = es.data_for_insert()

            insert_data["ApplicantsLE"] = [{"Id": a.Id} for a in apps_le if apps_le != data.Correspondent]
            # insert_data["ServiceEndPlanData"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")  # Required
            # # insert_data["Addressees"] = [{"Id": data.Addressee.Id, "Number": 1}]

            saved_data = self._service.default_context.connection.execute_post(url, insert_data)
            es.reset()
            es.connection = self._service.default_context.connection
            es.persisted = True
            if saved_data is not None:
                es.update(saved_data)
                logging.info('Добавлено дело № %s от %s ID = %s' %
                             (declar.declar_number, declar.register_date.strftime('%d.%m.%Y'), data.Id))
            else:
                return False
        doc_ids = []
        if hasattr(declar, "AppliedDocument") and declar.AppliedDocument:
            for doc in declar.AppliedDocument:
                if doc.number:
                    s_str = "contains(Name,'%s') and RegistrationNumber eq '%s' and RegistrationDate eq '%s'" % \
                            (doc.title, doc.number, doc.date.strftime('%d.%m.%Y'))
                else:
                    s_str = ("contains(Name,'%s') and (RegistrationNumber eq '' or RegistrationNumber eq null)"
                             " and RegistrationDate eq '%s'") % (doc.title, doc.date.strftime('%d.%m.%Y'))
                res = self.search('IAddendums', s_str)
                if not len(res):
                    doc_ids.append(str(self.__upload_doc(
                        doc_getter, doc, files, data.Id, declar)))
        elif files:
            class D:
                pass
            for file_name, file_path in files.items():
                fn, ext = os.path.splitext(file_name)
                with open(file_path, 'rb') as f:
                    doc_data = (f.read(), ext[1:].lower() if ext else 'txt')
                os.remove(file_path)
                doc = D()
                doc.number = ''
                doc.date = datetime.date.today()
                doc.title = fn
                res = self.add_doc(doc, doc_data[1], doc_data[0], data)
                # doc_ids.append(str(res))

        # Send notification about new docs
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

    def run_script(self, script_name, params=()):
        script_name = self.__dir_ref_subst(script_name)
        if isinstance(params, dict):
            params = {self.__d_rx_crit_translate[key] if key in self.__d_rx_crit_translate else key: val
                      for key, val in params.items()}
        else:
            params = {self.__d_rx_crit_translate[key] if key in self.__d_rx_crit_translate else key: val
                      for key, value in params}
        return self._service.functions[script_name](**params)

    def __dir_ref_subst(self, name):
        if name in self.__d_rx_ref_translate:
            name = self.__d_rx_ref_translate[name]
        return name

    def search(self, code, criteria, tp=REF, order_by='', ascending=True, raw=True):
        if isinstance(criteria, str):
            for key, val in self.__d_rx_crit_translate.items():
                if key in criteria:
                    criteria = criteria.replace(key, val)
            for f, t in (('<>', ' ne '), ('<=', ' le '), ('>=', ' ge '), ('=', ' eq '), ('<', ' lt '), ('>', ' gt ')):
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
            data = self.search("IOfficialDocuments", "Id eq %s" % data.Id, raw=False)[0]
            ad = DocumentInfo()
            ad.date = data.RegistrationDate if hasattr(data, "RegistrationDate") and data.RegistrationDate else data.Created
            ad.file_name = "%s.%s" % (data.Id, data.AssociatedApplication.Extension)
            ad.number = data.RegistrationNumber
            ad.title = data.Subject
            # Get only last version
            i = len(data.Versions) - 1
            while i >= 0:
                if not data.Versions[i].IsHidden:
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
        if isinstance(declar[0].ResultingDocument, list):
            for doc in declar[0].ResultingDocument:
                applied_docs.append(make_doc(doc))
        else:
            applied_docs.append(make_doc(declar[0].ResultingDocument))
        return applied_docs

    def get_declar_status_data(self, declar_id=None, fsuids: list = (), permanent_status='6'):
        declar = self.search("IMunicipalServicesServiceCases", "Id eq %s" % declar_id, raw=False)[0]
        if not permanent_status:
            status = declar.UPAStatus.Id
        else:
            status = permanent_status

        attachments = []
        for fsuuid in fsuids:
            attachments.append({'attachment': {'FSuuid': ''.join(fsuuid.keys()) if isinstance(fsuuid, dict) else fsuuid,
                                               'docTypeId': 'ELK_RESULT'}})

        res = []
        elk_num = declar.NumELK
        if elk_num:
            order = {'orderNumber': declar.RegistrationNumber, 'senderKpp': '251101001',
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

        # Get persons
        users = []
        for fl in declar.ApplicantsPP:
            applicant = self._service.default_context.connection.execute_get(
                "%s/ApplicantsPP(%s)?$expand=Body" % (declar.__odata__.instance_url, fl.Id))
            series = num = ''
            if applicant.TIN or (series and num) or applicant.INILA:
                if applicant.INILA:
                    if applicant.DateOfBirth:
                        user = {'userDocSnilsBirthDate': {
                            'citizenship': '643', 'snils': applicant.INILA.strip(), 'birthDate': applicant.DateOfBirth}}
                    else:
                        user = {'userDocSnils': {
                            'snils': applicant.INILA.strip(), 'lastName': applicant.LastName,
                            'firstName': applicant.FirstName, 'middleName': applicant.MiddleName, 'citizenship': '643'}}
                elif applicant.TIN:
                    user = {'userDocInn': {
                        'INN': applicant.TIN.strip(),
                        'lastName': applicant.LastName, 'firstName': applicant.FirstName,
                        'middleName': applicant.MiddleName, 'citizenship': '643'}}
                else:
                    user = {'userPersonalDoc': {
                        'PersonalDocType': '1', 'series': series, 'number': num, 'lastName': applicant.LastName,
                        'firstName': applicant.FirstName, 'middleName': applicant.MiddleName, 'citizenship': '643'}}
                users.append(user)
        # Get organisations
        orgs = []
        for ul in declar.ApplicantsLE:
            applicant = self._service.default_context.connection.execute_get(
                "%s/ApplicantsLE(%s)?$expand=Body" % (declar.__odata__.instance_url, ul.Id))
            if applicant.TIN:
                orgs.append({'ogrn_inn_UL': {'inn_kpp': {'inn': applicant.TIN.strip()}}})
            elif applicant.PSRN:
                orgs.append({'ogrn_inn_UL': {'ogrn': applicant.PSRN.strip()}})

        if users or orgs:
            for user in users:
                order = {'user': user, 'senderKpp': '251101001', 'senderInn': '2511004094',
                         'serviceTargetCode': declar.ServiceKind.Code, 'userSelectedRegion': '00000000',
                         'orderNumber': declar.RegistrationNumber,
                         'requestDate': declar.RegistrationDate,
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
                         'serviceTargetCode': declar.ServiceKind.Code, 'userSelectedRegion': '00000000',
                         'orderNumber': declar.RegistrationNumber,
                         'requestDate': declar.RegistrationDate,
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
        if rec_id:
            ref = self.search(ref_name, 'Id eq %s' % rec_id, raw=False)
            logging.debug("Found ref: %s" % ref)
        else:
            ref = self._service.entities[ref_name]()
        if data:
            for req in data:
                key = req["Name"]
                val = req.get("Value")
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
            res = self.search('IMunicipalServicesUPAStatuss', "StatusID eq '%s'" % code_values[index], raw=True)
            for r in res:
                if r.Name != name_values[index]:
                    r.Name = name_values[index]
                    self._service.save(r)
            if not res:
                elk = self._service.entities['IMunicipalServicesUPAStatuss']()
                elk.Name = name_values[index]
                elk.StatusID = code_values[index]
                elk.Type = "AtWork"
                self._service.save(elk)
            index += 1

    def add_doc(self, requisites, data_format, data, lead_doc=None):
        doc = self._service.entities['IAddendums']()
        # doc.Name = requisites.title
        doc.RegistrationNumber = requisites.number
        doc.RegistrationDate = requisites.date
        doc.LeadingDocument = lead_doc
        doc.Subject = requisites.title
        doc.HasRelations = False
        doc.VersionsLocked = False  # Required
        doc.HasPublicBody = False  # Required
        res = self.search('IDocumentRegisters', "Name eq 'Дела по оказанию муниципальных услуг'", raw=False)
        doc.DocumentRegister = res[0]  # Required "Журнал регистрации"
        doc.Created = datetime.datetime.now()
        doc.HasVersions = True  # Required
        self._service.save(doc)
        try:
            res = self.search("IAssociatedApplications", "Extension eq '%s'" % data_format, raw=False)
            doc.Versions = [{"Number": 1, "AssociatedApplication": {"Id": res[0].Id}}]
            self._service.save(doc)
            doc = self.search("IAddendums", "Id eq %s" % doc.Id, raw=False)[0]
            saved_data = self._service.default_context.connection.execute_post(
                "%s/Versions(%s)/Body" % (doc.__odata__.instance_url, doc.Versions[0].Id),
                {"Value": base64.b64encode(data).decode()})
            # doc.__odata__.reset()
            # doc.__odata__.connection = self._service.default_context.connection
            # doc.__odata__.persisted = True
            # if saved_data is not None:
            #     doc.__odata__.update(saved_data)
            logging.info('Добавлен документ: %s № %s от %s = %s' % (requisites.title, requisites.number,
                                                                    requisites.date.strftime('%d.%m.%Y'), doc.Id))
        except ODataError:
            logging.warning("Ошибка сохранения документа %s № %s от %s" % (requisites.title, requisites.number,
                                                                           requisites.date.strftime('%d.%m.%Y')),
                            exc_info=True)
            self._service.delete(doc)
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
    res = rx.get_result_docs(116)
    print(res)
