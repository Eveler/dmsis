# -*- coding: utf-8 -*-
import logging

# import requests
# import pyodata
from odata import ODataService
from requests.auth import HTTPBasicAuth


class DirectumRXException(Exception):
    def __init__(self, msg, *args, **kwargs):
        super().__init__(msg, args, kwargs)

    @property
    def message(self):
        return self.args[0]


class DirectumRX:
    REF = None

    def __init__(self, url, username='', password=''):
        my_auth = HTTPBasicAuth(username, password) if username else None
        self._service = ODataService(url, auth=my_auth, reflect_entities=True)

    def add_declar(self, declar, files):
        raise "Not released yet"

    def run_script(self, script_name, params=()):
        raise "Not released yet"

    def search(self, code, criteria, tp=REF, order_by='', ascending=True, raw=False):
        entity = self._service.entities[code]
        query = self._service.query(entity)
        query_params = {'$expand': '*'}
        if criteria:
            query_params['$filter'] = criteria
        if order_by:
            query_params['$orderby'] = order_by + (' asc' if ascending else ' desc')
        return query.raw(query_params)

    def get_result_docs(self, directum_id, crt_name='Администрация Уссурийского городского округа',
                    zip_signed_doc=False, days_old=-3):
        raise "Not released yet"

    def get_declar_status_data(self, declar_id=None, fsuids: list = (), permanent_status='6'):
        raise "Not released yet"

    def update_reference(self, ref_name, rec_id, data):
        raise "Not released yet"

    def update_elk_status(self, data):
        raise "Not released yet"


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

    url = "http://rxtest.adm-ussuriisk.ru/Integration/odata/"
    rx = DirectumRX(url, 'Service User', '[1AnAr1]')
    res = rx.search('IMunicipalServicesServiceCases', 'ServEndDateFact eq null', order_by='Created', ascending=False)
    for r in res:
        print(r)
    exit()
    # print(query.raw({'$expand': '*'}))
    query.options['$expand'] = ['Author', 'DeliveryMethod']
    # query.expand(declar.Author, declar.DeliveryMethod)
    for ent in query.all():
        print(ent.Name, ent.__dict__)
        print(ent.DeliveryMethod.Name, ent.Author.Name)
