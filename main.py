# -*- encoding: utf-8 -*-


import logging

# import requests
from smev import Adapter

# from os import environ, putenv

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(module)s:%(name)s:%(lineno)d: %(message)s')
    logging.getLogger('zeep.xsd').setLevel(logging.INFO)
    logging.getLogger('zeep.wsdl').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.INFO)

    # from soapfish.xsd2py import generate_code_from_xsd
    # with open('smev_service_adapter.py', 'wb') as out, \
    #         open('smev-service-adapter.xsd', 'rb') as inf:
    #     out.write(generate_code_from_xsd(inf.read()))

    # from soapfish.wsdl2py import generate_code_from_wsdl
    #
    # with open("SMEVService.py", "wb") as out:
    #     out.write(generate_code_from_wsdl(requests.get(
    #         "http://smev3-d.test.gosuslugi.ru:7500/smev/v1.2/ws?wsdl").content,
    #                                       'SMEVMessageExchangeService'))

    # environ['OPENSSL_CONF'] = 'cryptography/hazmat/bindings/openssl.cfg'
    # putenv('OPENSSL_CONF', 'cryptography/hazmat/bindings/openssl.cfg')

    a = Adapter()
    # logging.debug(a.dump())
    print(a.get_request('urn://augo/smev/uslugi/1.0.0', 'declar'))

    # print(a.history.last_received)
    # print('*'*40)
    # print(a.history.last_sent)
