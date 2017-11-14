# -*- encoding: utf-8 -*-

import logging
from datetime import datetime

from zeep.client import Client
from zeep.plugins import HistoryPlugin
from zeep.wsse.signature import Signature


class Adapter:
    def __init__(self,
                 wsdl="http://smev3-d.test.gosuslugi.ru:7500/smev/v1.2/ws?wsdl",
                 history=False):
        self.log = logging.getLogger('smev_adapter')
        if history:
            self.history = HistoryPlugin()
            self.proxy = Client(wsdl, plugins=[self.history])
        else:
            self.proxy = Client(wsdl)

    def dump(self):
        res = "Prefixes:\n"
        for prefix, namespace in self.proxy.wsdl.types.prefix_map.items():
            res += ' ' * 4 + '%s: %s\n' % (prefix, namespace)

        res += "\nGlobal elements:\n"
        for elm_obj in sorted(self.proxy.wsdl.types.elements,
                              key=lambda k: k.qname):
            value = elm_obj.signature(schema=self.proxy.wsdl.types)
            res += ' ' * 4 + value + '\n'

        res += "\nGlobal types:\n"
        for type_obj in sorted(self.proxy.wsdl.types.types,
                               key=lambda k: k.qname or ''):
            value = type_obj.signature(schema=self.proxy.wsdl.types)
            res += ' ' * 4 + value + '\n'

        res += "\nBindings:\n"
        import six
        for binding_obj in sorted(self.proxy.wsdl.bindings.values(),
                                  key=lambda k: six.text_type(k)):
            res += ' ' * 4 + six.text_type(binding_obj) + '\n'

        res += '\n'
        import operator
        for service in self.proxy.wsdl.services.values():
            res += six.text_type(service) + '\n'
            for port in service.ports.values():
                res += ' ' * 4 + six.text_type(port) + '\n'
                res += ' ' * 8 + 'Operations:\n'

                operations = sorted(
                    port.binding._operations.values(),
                    key=operator.attrgetter('name'))

                for operation in operations:
                    res += '%s%s\n' % (' ' * 12, six.text_type(operation))
                res += '\n'
        return res

    def get_request(self, uri='urn://augo/smev/uslugi/1.0.0'):
        # mts = self.proxy.get_type('ns1:GetRequestRequest')()
        # mts.NamespaceURI = 'urn://augo/smev/uslugi/1.0.0'
        # mts.RootElementLocalName = 'declar'
        sign = Signature('C:\\Users\\Администратор\\Desktop\\Подписи\\Малышева ЭП-ОВ\\le-33b9d.000\\primary.key', 'C:\\Users\\Администратор\\Desktop\\Подписи\\Малышева ЭП-ОВ\\Малышева О.В. (ЭП-ОВ).cer')
        res = self.proxy.service.GetRequest(
            {'NamespaceURI': uri,
             'Timestamp': datetime.now()}, sign)
        return res
