# -*- encoding: utf-8 -*-
import ftplib
import logging
import tempfile
from datetime import datetime, date
from os import close, write
from urllib.parse import urlparse
from uuid import uuid1

from declar import Declar, AppliedDocument
from lxml import etree, objectify
from plugins.cryptopro import Crypto
from zeep import Client, xsd
from zeep.plugins import HistoryPlugin


class Adapter:
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
                 history=False, method='sharp', serial=None, container=None):
        self.log = logging.getLogger('smev.adapter')
        self.log.setLevel(logging.root.level)
        self.ftp_addr = ftp_addr
        self.crypto = Crypto()
        self.crypto.serial = serial
        self.crypto.container = container
        self.method = method

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
    def get_request(self, uri=None, local_name=None, node_id=None,
                    gen_xml_only=False):
        # if (uri and not local_name) or (not uri and local_name):
        #     raise Exception(
        #         'uri и local_name необходимо указывать одновременно')

        operation = 'GetRequest'
        timestamp = datetime.now()
        node = self.proxy.create_message(
            self.proxy.service, operation,
            {'NamespaceURI': uri, 'RootElementLocalName': local_name,
             'Timestamp': timestamp, 'NodeID': node_id},
            CallerInformationSystemSignature=etree.Element('Signature'))
        node[0][0][0].set('Id', 'SIGNED_BY_CALLER')
        node_str = etree.tostring(node)
        self.log.debug(node_str)

        res = self.__call_sign(
            self.__xml_part(node_str, b'ns1:MessageTypeSelector'))
        # COM variant
        # res = self.crypto.sign_com(
        #     self.__xml_part(node_str, b'ns1:MessageTypeSelector').decode())
        # res = self.__xml_part(res, 'Signature')
        # res = res.replace('URI=""', 'URI="#SIGNED_BY_CALLER"')

        # CSP variant
        # self.crypto.container = "049fc71a-1ff0-4e06-8714-03303ae34afd"
        # res = self.crypto.sign_csp(
        #     self.__xml_part(node_str, b'ns1:MessageTypeSelector'))

        # Sharp variant
        # self.crypto.serial = '008E BDC8 291F 0003 81E7 11E1 AF7A 5ED3 27'
        # res = self.crypto.sign_sharp(
        #     self.__xml_part(node_str, b'ns1:MessageTypeSelector'))

        res = node_str.decode().replace('<Signature/>', res)
        if gen_xml_only:
            return res

        res = self.__send(operation, res)
        self.log.debug(type(res))
        self.log.debug(res)

        declar, uuid, reply_to, files = None, None, None, {}

        if 'MessagePrimaryContent' in res:
            xml = etree.fromstring(res)

            declar = Declar.parsexml(
                etree.tostring(
                    xml.find('.//{urn://augo/smev/uslugi/1.0.0}declar')))

            if 'RefAttachmentHeaderList' in res:
                files = {}
                attach_head_list = objectify.fromstring(
                    self.__xml_part(res, b'RefAttachmentHeaderList'))
                for head in attach_head_list.getchildren():
                    files[head.uuid] = {'MimeType': head.MimeType}
                attach_list = objectify.fromstring(
                    self.__xml_part(res, b'FSAttachmentsList'))
                for attach in attach_list.getchildren():
                    files[attach.uuid]['UserName'] = str(attach.UserName)
                    files[attach.uuid]['Password'] = str(attach.Password)
                    files[attach.uuid]['FileName'] = str(attach.FileName)
                for uuid, file in files.items():
                    file_name = file['FileName']
                    from os import path
                    fn, ext = path.splitext(file_name)
                    res = self.__load_file(uuid, file['UserName'],
                                           file['Password'],
                                           file['FileName'])
                    if isinstance(res, (str, bytes)):
                        from mimetypes import guess_extension
                        new_ext = guess_extension(file_name).lower()
                        ext = ext.lower()
                        if ext != new_ext:
                            file_name = fn + new_ext
                    else:
                        res, e = res
                        file_name = fn + '.txt'
                    declar.files.append({res: file_name})

            uuid = xml.find('.//{*}MessageID').text
            reply_to = xml.find('.//{*}ReplyTo')
            if reply_to:
                reply_to = reply_to.text

        if hasattr(res, 'Request') \
                and hasattr(res.Request, 'SenderProvidedRequestData') \
                and hasattr(res.Request.SenderProvidedRequestData,
                            'MessagePrimaryContent') \
                and res.Request.SenderProvidedRequestData.MessagePrimaryContent:
            # declar = Declar.parsexml(
            #     etree.tostring(
            #         res.Request.SenderProvidedRequestData.MessagePrimaryContent.find(
            #             './/{urn://augo/smev/uslugi/1.0.0}declar')))
            declar = Declar.parsexml(
                etree.tostring(
                    res.Request.SenderProvidedRequestData.MessagePrimaryContent._value_1))
            if hasattr(res.Request, 'FSAttachmentsList') \
                    and res.Request.FSAttachmentsList:
                attach_head_list = res.Request.SenderProvidedRequestData.RefAttachmentHeaderList
                for head in attach_head_list:
                    files[head.uuid] = {'MimeType': head.MimeType}
                attach_list = res.Request.FSAttachmentsList
                for attach in attach_list:
                    files[attach.uuid]['UserName'] = str(attach.UserName)
                    files[attach.uuid]['Password'] = str(attach.Password)
                    files[attach.uuid]['FileName'] = str(attach.FileName)
                for uuid, file in files.items():
                    file_name = file['FileName']
                    from os import path
                    fn, ext = path.splitext(file_name)
                    res = self.__load_file(uuid, file['UserName'],
                                           file['Password'],
                                           file['FileName'])
                    if isinstance(res, (str, bytes)):
                        from mimetypes import guess_extension
                        new_ext = guess_extension(file_name).lower()
                        ext = ext.lower()
                        if ext != new_ext:
                            file_name = fn + new_ext
                    else:
                        res, e = res
                        file_name = fn + '.txt'
                    # declar.files.append({res: file_name})
                    files[file_name] = res

            uuid = res.Request.SenderProvidedRequestData.MessageID
            reply_to = res.Request.ReplyTo

        if uuid:
            operation = 'Ack'
            tm = etree.Element('AckTargetMessage', Id='SIGNED_BY_CALLER',
                               accepted='true')
            tm.text = uuid
            node = self.proxy.create_message(
                self.proxy.service, operation, tm,
                CallerInformationSystemSignature=etree.Element('Signature'))
            res = node.find('.//{*}AckTargetMessage')
            res.set('Id', 'SIGNED_BY_CALLER')
            res.set('accepted', 'true')
            res.text = uuid
            node_str = etree.tostring(node)
            self.log.debug(node_str)
            res = self.__xml_part(node_str, b'ns1:AckTargetMessage')
            res = self.__call_sign(res)
            res = node_str.decode().replace('<Signature/>', res)
            res = self.__send(operation, res)
            self.log.debug(res)

        return declar, uuid, reply_to, files

    def send_respose(self, reply_to, declar_number, register_date,
                     result='FINAL', text='', applied_documents=list(),
                     ftp_user='', ftp_pass=''):
        files = []
        for doc in applied_documents:
            from mimetypes import guess_type
            if isinstance(doc, (bytes, str)):
                file_name = os.path.split(doc)[1]
                uuid = self.__upload_file(doc, file_name, ftp_user, ftp_pass)
                files.append({uuid: {'name': file_name,
                                     'type': guess_type(doc),
                                     'full_name': doc}})
            if doc.file:
                uuid = self.__upload_file(doc.file, doc.file_name, ftp_user,
                                          ftp_pass)
                files.append({uuid: {'name': doc.file_name,
                                     'type': guess_type(doc.file),
                                     'full_name': doc.file}})

        operation = 'SendResponse'
        element = self.proxy.get_element('ns1:MessagePrimaryContent')
        rr = etree.Element(
            '{urn://augo/smev/uslugi/1.0.0}requestResponse',
            nsmap={'rr': 'urn://augo/smev/uslugi/1.0.0'})
        etree.SubElement(
            rr,
            '{urn://augo/smev/uslugi/1.0.0}declar_number').text = declar_number
        etree.SubElement(
            rr,
            '{urn://augo/smev/uslugi/1.0.0}register_date').text = \
            register_date.strftime('%Y-%m-%d') if isinstance(
                register_date, (date, datetime)) else register_date
        etree.SubElement(rr,
                         '{urn://augo/smev/uslugi/1.0.0}result').text = result
        if text:
            etree.SubElement(rr,
                             '{urn://augo/smev/uslugi/1.0.0}text').text = text
        if files:
            for doc in applied_documents:
                ad = etree.SubElement(
                    rr, '{urn://augo/smev/uslugi/1.0.0}AppliedDocument')
                etree.SubElement(
                    ad,
                    '{urn://augo/smev/uslugi/1.0.0}title').text = \
                    doc.title
                etree.SubElement(
                    ad,
                    '{urn://augo/smev/uslugi/1.0.0}number').text = \
                    doc.number
                etree.SubElement(
                    ad,
                    '{urn://augo/smev/uslugi/1.0.0}date').text = \
                    doc.date
                etree.SubElement(
                    ad,
                    '{urn://augo/smev/uslugi/1.0.0}valid_until').text = \
                    doc.valid_until
                etree.SubElement(
                    ad,
                    '{urn://augo/smev/uslugi/1.0.0}file_name').text = \
                    doc.file_name
                etree.SubElement(
                    ad,
                    '{urn://augo/smev/uslugi/1.0.0}url').text = doc.url
                etree.SubElement(
                    ad,
                    '{urn://augo/smev/uslugi/1.0.0}url_valid_until').text = \
                    doc.url_valid_until

        mpc = element(rr)
        node = self.proxy.create_message(
            self.proxy.service, operation,
            {'MessageID': uuid1(), 'To': reply_to,
             'MessagePrimaryContent': mpc},
            CallerInformationSystemSignature=etree.Element('Signature'))
        res = node.find('.//{*}SenderProvidedResponseData')
        res.set('Id', 'SIGNED_BY_CALLER')

        if files:
            rahl = etree.SubElement(res, 'RefAttachmentHeaderList')
            for uuid, file in files:
                rah = etree.SubElement(rahl, 'RefAttachmentHeader')
                etree.SubElement(rah, 'uuid').text = uuid
                etree.SubElement(
                    rah, 'Hash').text = self.crypto.get_file_hash(
                    file['full_name'])
                etree.SubElement(rah, 'MimeType').text = file['type']

        node_str = etree.tostring(node)
        res = etree.QName(res)
        node_str = node_str.replace(
            b'<ns0:SenderProvidedResponseData',
            b'<ns0:SenderProvidedResponseData xmlns:ns0="' +
            res.namespace.encode() + b'"')
        self.log.debug(node_str)
        res = self.__xml_part(node_str,
                              b'ns0:SenderProvidedResponseData')
        res = self.__call_sign(res)
        res = node_str.decode().replace('<Signature/>', res)
        res = self.__send(operation, res.encode('utf-8'))
        self.log.debug(res)
        return res

    def __call_sign(self, xml):
        method_name = 'sign_' + self.method
        self.log.debug('Calling Crypto.%s' % method_name)
        method = getattr(self.crypto, method_name)
        return method(xml)

    def __upload_file(self, file, file_name, ftp_user='anonymous', ftp_pass='anonymous'):
        addr = urlparse(self.ftp_addr).netloc
        with ftplib.FTP(addr, ftp_user, ftp_pass) as con:
            uuid = str(uuid1())
            con.mkd(uuid)
            con.cwd(uuid)
            with open(file, 'rb') as f:
                res = con.storbinary('STOR ' + file_name, f)
            self.log.debug(res)
        return uuid

    def __load_file(self, uuid, user, passwd, file_name):
        addr = urlparse(self.ftp_addr).netloc
        f, file_path = tempfile.mkstemp()
        try:
            with ftplib.FTP(addr, user, passwd) as con:
                con.cwd(uuid)
                if file_name[0] == '/':
                    file_name = file_name[1:]
                close(f)
                with open(file_path, 'wb') as f:
                    con.retrbinary('RETR ' + file_name, f.write)
        except ftplib.all_errors as e:
            self.log.error(str(e))
            write(f, str(e).encode('cp1251'))
            close(f)
            return file_path, e
        return file_path

    def __send(self, operation, msg):
        kw = {'_soapheaders': self.proxy.service._client._default_soapheaders}
        response = self.proxy.transport.post(
            self.proxy.service._binding_options['address'], msg, kw)
        res = self.proxy.service._binding.process_reply(
            self.proxy.service._client,
            self.proxy.service._binding.get(operation), response)
        # if not res and b'--uuid:' in response.content:
        #     res = response.content[
        #               response.content.index(b'Content-Type:'):]
        #     res = res[:res.index(b'--uuid:')]
        #     self.log.debug(res)
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
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s:%(module)s:%(name)s:%(lineno)d: %(message)s')
    logging.root.handlers[0].setLevel(logging.INFO)
    logging.getLogger('zeep.xsd').setLevel(logging.INFO)
    logging.getLogger('zeep.wsdl').setLevel(logging.INFO)
    logging.getLogger('urllib3').setLevel(logging.INFO)

    import sys

    if len(sys.argv) < 2:
        import os
        from logging.handlers import TimedRotatingFileHandler

        handler = TimedRotatingFileHandler(
            os.path.abspath("dmsis.log"), when='D', backupCount=0,
            encoding='cp1251')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(name)s:%(module)s(%(lineno)d): %(levelname)s: '
            '%(message)s'))
        logging.root.addHandler(handler)
        handler.setLevel(logging.DEBUG)

    a = Adapter(serial='008E BDC8 291F 0003 81E7 11E1 AF7A 5ED3 27',
                container='smev_ep-ov',
                wsdl="http://smev3-n0.test.gosuslugi.ru:7500/smev/v1.2/ws?wsdl",
                ftp_addr="ftp://smev3-n0.test.gosuslugi.ru/")

    if len(sys.argv) > 1 and sys.argv[1].lower() == 'test2':
        with open('tests/test2.xml', 'w') as f:
            f.write(a.get_request('urn://augo/smev/uslugi/1.0.0', 'directum',
                                  gen_xml_only=True))
    else:
        try:
            res = a.send_respose(reply_to='eyJzaWQiOjMyNzg1LCJtaWQiOiIwOTlmNjlkMy1lYmE2LTExZTctYTIyZS1hNDVkMzZjNzcwNmYiLCJ0Y2QiOiJmMDIxM2E4My1lYmE1LTExZTctOTc4NC1mYTE2M2UxMDA3Yjl8MTExMTExMTExMTExMTExMTExMTF8VjhoUXFvLzlYMVBDckJkV010RHQ2UlUyNGdQdEdZQzlPTjlEM2d4TWQzZGdWK1ErUFo3L2o3SUJKMG5WY1BBNnZ5T1ZrczRuNHl5ZWhEQytFclYydkRSYXBVKzJMcWJtNmNHQlVGR0lRbyt2Kzl3TnpnMVlFOFI5Tnh6MmNxWmlFTzN3TUNYQlplbXNJaUVUajlNNm5JKzVaOHU4VXNnTFpyb1NoMkN1WlR3L244MS9wYU00cFMxcXlXaWE3TWRYUUJLN1gwcUpwcG80VGl0cnJOcFFqR3phUXNPUFFDSThIT3Vnc2o1QmRSNUUveTdIM1ZwZUlhQ1ZjTG5LeEtQbm5hQllyandGYzRrQUZVcW1zM3JTWjdaWitXeWNCQlpZOTZOS0hpbE10eVNYQW9PeE1Qa1dsQXA1b1hScDhhQXNoRzNIQitOV0lsVm9CRFpiaW1MTnZBPT0iLCJyaWQiOiJkMGFjYmY2Yy0xNDMzLTExZTUtOWFkZi00YWIyM2QwN2NlMzkiLCJlb2wiOjAsInNsYyI6ImF1Z29fc21ldl91c2x1Z2lfMS4wLjBfZGVjbGFyIiwibW5tIjoibXRfdGVzdCJ9',
                                 declar_number='23156/564/5611Д',
                                 register_date='2008-09-29',
                                 text='В услуге отказано по причине отсутствия документов удостоверяющих личность и заявления')
            logging.debug(res)
            res = a.get_request(
                # node_id='099f69d3-eba6-11e7-a22e-a45d36c7706f',
                uri='urn://augo/smev/uslugi/1.0.0',
                local_name='declar')
            logging.debug(res)
            if res:
                import json

                try:
                    with open('declar.json', 'w') as j:
                        json.dump(res, j)
                except (ValueError, IOError, TypeError) as e:
                    logging.error(str(e))
                    with open('declar.bin', 'wb') as b:
                        b.write(res)
        except Exception as e:
            logging.error(str(e), exc_info=True)
            # with open('tests/dmsis.log', 'a') as f:
            #     f.write(str(e))
    # from datetime import date

    # doc = AppliedDocument
    # doc.file_name = 'fgfdgfd'
    # doc.file = 'dfdscxvcx'
    # print(a.send_respose('fbklfblkfdgndndf', '454/5624365', date(2008, 8, 25),
    #                      applied_documents=[doc]))
