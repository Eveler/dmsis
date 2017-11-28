# -*- encoding: utf-8 -*-
from datetime import datetime
import ftplib
import logging
import tempfile
from os import close, remove
from urllib.parse import urlparse

from lxml import etree, objectify

from declar import Declar
from plugins.cryptopro import Crypto
from zeep.client import Client
from zeep.plugins import HistoryPlugin


class Adapter:
    # xml_template = '<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">' \
    #                '<SignedInfo>' \
    #                '<CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>' \
    #                '<SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411"/>' \
    #                '<Reference URI="">' \
    #                '<Transforms>' \
    #                '<Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>' \
    #                '<Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>' \
    #                '</Transforms>' \
    #                '<DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr3411"/>' \
    #                '<DigestValue></DigestValue></Reference></SignedInfo>' \
    #                '<SignatureValue></SignatureValue><KeyInfo><X509Data>' \
    #                '<X509Certificate></X509Certificate></X509Data></KeyInfo>' \
    #                '</Signature>'
    xml_template = '<ds:Signature ' \
                   'xmlns:ds="http://www.w3.org/2000/09/xmldsig#">' \
                   '<ds:SignedInfo>' \
                   '<ds:CanonicalizationMethod ' \
                   'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>' \
                   '<ds:SignatureMethod ' \
                   'Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411"/>' \
                   '<ds:Reference URI="#SIGNED_BY_CALLER"><ds:Transforms>' \
                   '<ds:Transform ' \
                   'Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>' \
                   '<ds:Transform ' \
                   'Algorithm="urn://smev-gov-ru/xmldsig/transform"/>' \
                   '</ds:Transforms>' \
                   '<ds:DigestMethod ' \
                   'Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr3411"/>' \
                   '<ds:DigestValue></ds:DigestValue></ds:Reference>' \
                   '</ds:SignedInfo><ds:SignatureValue></ds:SignatureValue>' \
                   '<ds:KeyInfo><ds:X509Data><ds:X509Certificate>' \
                   '</ds:X509Certificate></ds:X509Data></ds:KeyInfo>' \
                   '</ds:Signature>'

    def __init__(self,
                 wsdl="http://smev3-d.test.gosuslugi.ru:7500/smev/v1.2/ws?wsdl",
                 ftp_addr="ftp://smev3-d.test.gosuslugi.ru/",
                 history=False):
        self.log = logging.getLogger('smev.adapter')
        self.log.setLevel(logging.root.level)
        self.ftp_addr = ftp_addr
        self.crypto = Crypto()

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

    # def get_request(self, uri='urn://augo/smev/uslugi/1.0.0',
    #                 local_name='directum'):
    def get_request(self, uri=None, local_name=None, node_id=None):
        if (uri and not local_name) or (not uri and local_name):
            raise Exception(
                'uri и local_name необходимо указывать одновременно')
        # timestamp = datetime.now()
        # node = self.proxy.create_message(
        #     self.proxy.service, 'GetRequest',
        #     {'NamespaceURI': uri, 'RootElementLocalName': local_name,
        #      'Timestamp': timestamp, 'NodeID': node_id},
        #     CallerInformationSystemSignature=etree.Element('Signature'))
        # node[0][0][0].set('Id', 'SIGNED_BY_CALLER')
        # node_str = etree.tostring(node)
        # self.log.debug(node_str)
        #
        # # COM variant
        # # res = self.crypto.sign_com(
        # #     self.__xml_part(node_str, b'ns1:MessageTypeSelector').decode(),
        # #     Crypto.CADESCOM_XML_SIGNATURE_TYPE_ENVELOPED)
        # # res = self.__xml_part(res, 'Signature')
        # # res = res.replace('URI=""', 'URI="#SIGNED_BY_CALLER"')
        #
        # # CSP variant
        # # self.crypto.container = "049fc71a-1ff0-4e06-8714-03303ae34afd"
        # # res = self.crypto.sign_csp(
        # #     self.__xml_part(node_str, b'ns1:MessageTypeSelector'))
        #
        # # Sharp variant
        # self.crypto.serial = '008E BDC8 291F 0003 81E7 11E1 AF7A 5ED3 27'
        # res = self.crypto.sign_sharp(
        #     self.__xml_part(node_str, b'ns1:MessageTypeSelector'))
        #
        # res = node_str.decode().replace('<Signature/>', res)
        #
        # res = self.__send('GetRequest', res)
        # # res = self.proxy.service.GetRequest(
        # #     {'NamespaceURI': uri, 'RootElementLocalName': local_name,
        # #      'Timestamp': timestamp, 'NodeID': node_id},
        # #     CallerInformationSystemSignature=etree.fromstring(res))

        # if 'MessagePrimaryContent' in res:
        res = open('tests/GetRequestResponseAttachFTP.xml', 'rb').read()
        xml = etree.fromstring(res)

        declar = Declar.parsexml(
            etree.tostring(xml.find('.//{urn://augo/smev/uslugi/1.0.0}declar')))

        if 'RefAttachmentHeaderList' in res:
            files = {}
            attach_head_list = objectify.fromstring(
                self.__xml_part(res, b'RefAttachmentHeaderList'))
            for head in attach_head_list.getchildren():
                files[head.uuid] = {'MimeType': head.MimeType}
            attach_list = objectify.fromstring(
                self.__xml_part(res, b'FSAttachmentsList'))
            for attach in attach_list.getchildren():
                files[attach.uuid]['UserName'] = attach.UserName
                files[attach.uuid]['Password'] = attach.Password
                files[attach.uuid]['FileName'] = attach.FileName
            for uuid, file in files.items():
                res = self.__load_file(uuid, file['UserName'], file['Password'],
                                       file['FileName'])
                # TODO: Rename file if extension is not reflect MIME type
                declar.files.append(res)

        # tm = etree.Element('AckTargetMessage', Id='SIGNED_BY_CALLER',
        #                    accepted='true')
        # tm.text = '0e8cfc01-5e81-11e4-a9ff-d4c9eff07b77'
        # node = self.proxy.create_message(self.proxy.service, 'Ack', tm,
        #                                  CallerInformationSystemSignature=etree.Element(
        #                                      'Signature'))
        # node[0][0][0].set('Id', 'SIGNED_BY_CALLER')
        # node[0][0][0].set('accepted', 'true')
        # node[0][0][0].text = '0e8cfc01-5e81-11e4-a9ff-d4c9eff07b77'
        # node_str = etree.tostring(node)
        # self.log.debug(node_str)
        # res = self.crypto.sign_sharp(
        #     self.__xml_part(node_str, b'ns1:AckTargetMessage'))
        # res = node_str.decode().replace('<Signature/>', res)
        # res = self.__send('Ack', res)

        return declar

    def __load_file(self, uuid, user, passwd, file_name):
        addr = urlparse(self.ftp_addr).netloc
        with ftplib.FTP(addr, user, passwd) as con:
            con.cwd(uuid)
            if file_name[0] == '/':
                file_name = file_name[1:]
            f, file_path = tempfile.mkstemp()
            close(f)
            try:
                with open(file_path, 'wb') as f:
                    con.retrbinary('RETR ' + file_name, f.write)
            except ftplib.all_errors as e:
                self.log.error(e)
                remove(file_path)
                return ""
        return file_path

    def __send(self, operation, msg):
        kw = {'_soapheaders': self.proxy.service._client._default_soapheaders}
        response = self.proxy.transport.post(
            self.proxy.service._binding_options['address'], msg, kw)
        res = self.proxy.service._binding.process_reply(
            self.proxy.service._client,
            self.proxy.service._binding.get(operation), response)
        return res

    def __xml_part(self, xml_as_str, tag_name):
        """
        Cuts the XML part from `xml_as_str` bounded by tag `tag_name`

        :param xml_as_str: String with source XML

        :param tag_name: XML tag name bounds target XML part
        """
        b_idx = xml_as_str.index(tag_name) - 1
        try:
            if isinstance(tag_name, str):
                tgn = tag_name + '>'
            else:
                tgn = tag_name + b'>'
            e_idx = xml_as_str.index(tgn, b_idx + len(tag_name)) + len(
                tag_name) + 1
        except ValueError:
            if isinstance(tag_name, str):
                tgn = tag_name + ' '
            else:
                tgn = tag_name + b' '
            e_idx = xml_as_str.index(tgn, b_idx + len(tag_name)) + len(
                tag_name) + 1
        return xml_as_str[b_idx:e_idx]


if __name__ == '__main__':
    a = Adapter()
    print(a.get_request('urn://augo/smev/uslugi/1.0.0', 'declar'))
