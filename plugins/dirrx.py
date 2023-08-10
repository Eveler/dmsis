# -*- coding: utf-8 -*-
import logging

# import requests
# import pyodata
from odata import ODataService
from requests.auth import HTTPBasicAuth


class DirectumRX:
    def __init__(self, url, username='', password=''):
        my_auth = HTTPBasicAuth(username, password) if username else None
        self._service = ODataService(url, auth=my_auth, reflect_entities=True)


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
    rx = DirectumRX(url, 'Savenko', 'mY3pss2augo')
    declar = rx._service.entities['IMunicipalServicesServiceCases']
    query = rx._service.query(declar)
    # print(query.raw({'$expand': '*'}))
    query.options['$expand'] = ['Author', 'DeliveryMethod']
    # query.expand(declar.Author, declar.DeliveryMethod)
    # query.filter(declar.ServEndDateFact == None)
    query.options['$filter'] = ['ServEndDateFact eq null']
    for ent in query.all():
        print(ent.Name, ent.__dict__)
        print(ent.DeliveryMethod.Name, ent.Author.Name)
