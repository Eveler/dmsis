# -*- coding: utf-8 -*-
import datetime
import logging

# import requests
# import pyodata
from odata import ODataService
from odata.property import SortOrder
from requests.auth import HTTPBasicAuth


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
                            'ELK_STATUS': 'IMunicipalServicesUPAStatuses'
                            }

    def __init__(self, url, username='', password=''):
        my_auth = HTTPBasicAuth(username, password) if username else None
        self._service = ODataService(url, auth=my_auth, reflect_entities=True)

    def add_declar(self, declar, files):
        data = [{"Name": 'Note', "Value": 'By integration'}]
        # Individual
        if len(declar.person) > 0:
            for person in declar.person:
                res = self.search(
                        'IPersons',
                        "Status eq 'Active' and LastName eq '%s' and FirstName eq '%s'%s%s" %
                        (person.surname, person.first_name,
                         " and MiddleName eq '%s'" % person.patronymic if person.patronymic else '',
                         " and (LegalAddress eq '%s' or LegalAddress eq null)" % person.address), raw=False)
            data.append({"Name": 'ApplicantsPP', "Value": res})
            # data.append({"Name": 'Correspondent', "Value": res[0]})
            raise "Not released yet"
        # LegalEntity
        if len(declar.legal_entity):
            apps_le = []
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
            data.append({"Name": 'ApplicantsLE', "Value": apps_le})
            res = self.search('IContacts', self._service.entities['IContacts'].Company == apps_le[0], raw=False)
            data.append({"Name": 'Contact', "Value": res[0]})
            data.append({"Name": 'Correspondent', "Value": apps_le[0]})
        res = self.search('IMunicipalServicesServiceKinds',
                          "Code eq '119' or contains(ShortName,'119') or contains(FullName,'119')", raw=False)
        data.append({"Name": 'ServiceKind', "Value": res[0]})
        res = self.search('IEmployees', "Id eq %s" % res[0].ServPerformer.Id, raw=False)
        data.append({"Name": 'Addressee', "Value": res[0]})
        data.append({"Name": 'ManyAddresseesLabel', "Value": res[0].Name})
        res = self.search('IDepartments', "Id eq %s" % res[0].Department.Id, raw=False)
        data.append({"Name": 'AddresseeDep', "Value": res[0]})
        res = self.search('IMailDeliveryMethods', "Name eq 'СМЭВ'", raw=False)
        data.append({"Name": 'DeliveryMethod', "Value": res[0]})
        res = self.search('IDocumentKinds', "Name eq 'Дело по оказанию услуг'", raw=False)
        data.append({"Name": 'DocumentKind', "Value": res[0]})
        res = self.search('IBusinessUnits', "Name eq 'Администрация Уссурийского городского округа'", raw=False)
        data.append({"Name": 'BusinessUnit', "Value": res[0]})
        res = self.search('IDepartments', "Name eq 'Отдел информатизации'", raw=False)
        data.append({"Name": 'Department', "Value": res[0]})
        data.append({"Name": 'Created', "Value": datetime.datetime.now()})
        data.append({"Name": 'IsManyAddressees', "Value": False})
        res = self.search('IEmployees', "Id eq 13", raw=False)
        data.append({"Name": 'Author', "Value": res[0]})

        # data.append({"Name": 'Status', "Value": 'Active'})

        rx.update_reference('IMunicipalServicesServiceCases', data=data)

    def run_script(self, script_name, params=()):
        raise DirectumRXException("Not released yet")

    def search(self, code, criteria, tp=REF, order_by='', ascending=True, raw=True):
        if code in self.__d_rx_ref_translate:
            code = self.__d_rx_ref_translate[code]
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
        raise DirectumRXException("Not released yet")

    def get_declar_status_data(self, declar_id=None, fsuids: list = (), permanent_status='6'):
        raise "Not released yet"

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
        raise DirectumRXException("Not released yet")


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
    # res = rx.search('IMunicipalServicesServiceCases', 'ServEndDateFact eq null', order_by='Created', ascending=False)
    # for r in res:
    #     print(r)
    # print(rx._service.entities.keys())
    # exit()
    # pers = rx._service.entities['IPersons']
    # res = rx.search(
    #     'IPersons', Query.and_(pers.FirstName == 'Илья',
    #                            Query.and_(pers.MiddleName == 'Владимирович', pers.LastName == 'Елисеев')),
    #     order_by=pers.FirstName.asc(), raw=False)
    # res = rx.search(
    #     'IPersons',
    #     "FirstName eq 'Илья' and MiddleName eq 'Владимирович' and LastName eq 'Елисеев'",
    #     order_by="FirstName", raw=False)
    # for r in res:
    #     print(r)

    # corr = rx._service.entities['ICompanies']()
    # corr.Name = 'АйТиСи2'
    # corr.LegalName = entity.full_name
    # corr.TIN = entity.inn
    # corr.TRRC = entity.kpp
    # corr.LegalAddress = entity.address
    # corr.Note = 'By integration'
    # corr.Status = 'Active'
    # res = rx._service.save(corr)
    # print(res)
    # exit()
    class Declar:
        person = []
        class LE:
            full_name = ''
            name = 'АйТиСи'
            inn = ''
        legal_entity = [LE()]
    res = rx.add_declar(Declar(), '')
    print(res)
    exit()
    # print(query.raw({'$expand': '*'}))
    query.options['$expand'] = ['Author', 'DeliveryMethod']
    # query.expand(declar.Author, declar.DeliveryMethod)
    for ent in query.all():
        print(ent.Name, ent.__dict__)
        print(ent.DeliveryMethod.Name, ent.Author.Name)
