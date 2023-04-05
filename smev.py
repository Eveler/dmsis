# -*- encoding: utf-8 -*-

import ftplib
import logging
import operator
import os
import sys
import tempfile
from datetime import datetime, date
# from logging.handlers import TimedRotatingFileHandler
from mimetypes import guess_type, guess_extension
from os import close, write, path, remove
from os.path import basename
from urllib.parse import urlparse
from uuid import uuid1

# from datetime import date
from zipfile import ZipFile, ZIP_DEFLATED

from zeep.exceptions import XMLParseError

import six
from declar import Declar
from lxml import etree, objectify
from plugins.cryptopro import Crypto
from translit import translate
from zeep import Client
from zeep.plugins import HistoryPlugin


class Adapter:
    def __init__(self,
                 wsdl="http://smev3-d.test.gosuslugi.ru:7500/smev/v1.2/ws?wsdl",
                 ftp_addr="ftp://smev3-d.test.gosuslugi.ru/",
                 history=False, method='sharp', serial=None, container=None,
                 crt_name=None):
        self.log = logging.getLogger('smev.adapter')
        self.log.setLevel(logging.root.level)
        self.ftp_addr = ftp_addr
        self.crypto = Crypto()
        self.crypto.serial = serial
        self.crypto.crt_name = crt_name
        self.crypto.container = container
        self.method = method

        if history:
            self.history = HistoryPlugin()
            self.proxy = Client(wsdl, plugins=[self.history], strict=False)
        else:
            self.proxy = Client(wsdl)
        self.__calls = 0

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
        for binding_obj in sorted(self.proxy.wsdl.bindings.values(),
                                  key=lambda k: six.text_type(k)):
            res += ' ' * 4 + six.text_type(binding_obj) + '\n'

        res += '\n'
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
    def get_request(self, uri='', local_name='', node_id=None,
                    gen_xml_only=False):
        operation = 'GetRequest'
        if sys.version_info.major == 3 and sys.version_info.minor <= 5:
            import timezone
            timestamp = timezone.utcnow()
        else:
            import pytz
            timestamp = datetime.now(pytz.utc)
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
        self.log.debug(res)

        declar, uuid, reply_to, files = None, None, None, {}
        if isinstance(res, bytes):
            res = res.decode(errors='replace')

        if res and 'MessagePrimaryContent' in res:
            xml = etree.fromstring(res)

            declar = Declar.parsexml(
                etree.tostring(
                    xml.find('.//{urn://augo/smev/uslugi/1.0.0}declar')))

            if 'RefAttachmentHeaderList' in res:
                attach_files = {}
                attach_head_list = objectify.fromstring(
                    self.__xml_part(res, b'RefAttachmentHeaderList'))
                for head in attach_head_list.getchildren():
                    attach_files[head.uuid] = {'MimeType': head.MimeType}
                    attach_files[head.uuid]['SignaturePKCS7'] = head.SignaturePKCS7
                attach_list = objectify.fromstring(
                    self.__xml_part(res, b'FSAttachmentsList'))
                for attach in attach_list.getchildren():
                    attach_files[attach.uuid]['UserName'] = str(attach.UserName)
                    attach_files[attach.uuid]['Password'] = str(attach.Password)
                    attach_files[attach.uuid]['FileName'] = str(attach.FileName)
                self.__load_files(attach_files, res, files)
                for key, item in files:
                    declar.files.append({item: key})

            uuid = xml.find('.//{*}MessageID').text
            reply_to = xml.find('.//{*}ReplyTo')
            if reply_to:
                reply_to = reply_to.text

        if hasattr(res, 'Request') \
                and hasattr(res.Request, 'SenderProvidedRequestData') \
                and hasattr(res.Request.SenderProvidedRequestData,
                            'MessagePrimaryContent') \
                and res.Request.SenderProvidedRequestData.MessagePrimaryContent:
            declar = Declar.parsexml(
                etree.tostring(
                    res.Request.SenderProvidedRequestData.\
                        MessagePrimaryContent._value_1))
            try:
                if hasattr(res.Request, 'FSAttachmentsList') \
                        and res.Request.FSAttachmentsList:
                    attach_files = {}
                    attach_head_list = res.Request.SenderProvidedRequestData.\
                        RefAttachmentHeaderList.RefAttachmentHeader
                    for head in attach_head_list:
                        attach_files[head.uuid] = {'MimeType': head.MimeType}
                        if hasattr(head, 'SignaturePKCS7') and head.SignaturePKCS7:
                            attach_files[head.uuid]['SignaturePKCS7'] = \
                                head.SignaturePKCS7
                    attach_list = res.Request.FSAttachmentsList.FSAttachment
                    for attach in attach_list:
                        attach_files[attach.uuid]['UserName'] = str(attach.UserName)
                        attach_files[attach.uuid]['Password'] = str(attach.Password)
                        attach_files[attach.uuid]['FileName'] = str(attach.FileName)
                    self.__load_files(attach_files, res, files)
                if hasattr(res, 'AttachmentContentList') \
                        and res.AttachmentContentList:
                    attach_files = {}
                    attach_head_list = res.Request.SenderProvidedRequestData. \
                        AttachmentHeaderList.AttachmentHeader
                    for head in attach_head_list:
                        attach_files[head.contentId] = {'MimeType': head.MimeType}
                        if hasattr(head, 'SignaturePKCS7') and head.SignaturePKCS7:
                            attach_files[head.contentId]['SignaturePKCS7'] = \
                                head.SignaturePKCS7
                    attach_list = res.AttachmentContentList.AttachmentContent
                    i = 1
                    for attach in attach_list:
                        mime_type = attach_files[attach.Id]['MimeType']
                        file_name = str('file' + str(i))
                        i += 1
                        ext = guess_extension(mime_type)
                        file_name = file_name + ext if ext else '.txt'
                        f, fn = tempfile.mkstemp()
                        write(f, attach.Content)
                        close(f)
                        sig = attach_files[attach.Id].get('SignaturePKCS7')
                        if sig:
                            fn = self.make_sig_zip(file_name, fn, sig)
                            file_name = file_name.replace(ext, '.zip')
                        files[file_name] = fn
            except:
                for file_name, file_path in files.items():
                    try:
                        remove(file_path)
                    except:
                        pass
                raise

            uuid = res.Request.SenderProvidedRequestData.MessageID
            reply_to = res.Request.ReplyTo

        if not uuid:
            uuid = res

        return declar, uuid, reply_to, files

    def send_ack(self, uuid, accepted='true'):
        operation = 'Ack'
        tm = etree.Element('AckTargetMessage', Id='SIGNED_BY_CALLER',
                           accepted='true')
        tm.text = uuid
        node = self.proxy.create_message(
            self.proxy.service, operation, tm,
            CallerInformationSystemSignature=etree.Element('Signature'))
        res = node.find('.//{*}AckTargetMessage')
        res.set('Id', 'SIGNED_BY_CALLER')
        res.set('accepted', accepted)
        res.text = uuid
        node_str = etree.tostring(node)
        self.log.debug(node_str)
        res = self.__xml_part(node_str, b'ns1:AckTargetMessage')
        res = self.__call_sign(res)
        res = node_str.decode().replace('<Signature/>', res)
        res = self.__send(operation, res)
        self.log.debug(res)

    def get_status(self, timestamp):
        operation = 'GetStatus'
        node = self.proxy.create_message(
            self.proxy.service, operation, Timestamp=timestamp,
            CallerInformationSystemSignature=etree.Element('Signature'))
        res = node.find('.//{*}Timestamp')
        res.set('Id', 'SIGNED_BY_CALLER')
        node_str = etree.tostring(node)
        self.log.debug(node_str)
        res = self.__xml_part(node_str, b'ns1:Timestamp')
        res = self.__call_sign(res)
        res = node_str.decode().replace('<Signature/>', res)
        res = self.__send(operation, res)
        self.log.debug(res)

    def __add_element(self, parent, ns, elem, data, file_names=()):
        if not data:
            return
        se = etree.SubElement(parent, '{%s}%s' % (ns, elem))
        if elem == 'AppliedDocument':
            if isinstance(data, list):
                for itm in data:
                    for item in (
                            'title', 'number', 'date', 'valid_until',
                            'file_name', 'url', 'url_valid_until'):
                        if item in itm and itm[item]:
                            if item == 'file_name':
                                fn = itm[item]
                                file_names.append(fn)
                                self.__add_element(
                                    se, ns, item, path.basename(fn), file_names)
                            else:
                                self.__add_element(
                                    se, ns, item, itm[item], file_names)
                    if data.index(itm) < len(data) - 1:
                        se = etree.SubElement(parent, '{%s}%s' % (ns, elem))
            else:
                for item in (
                        'title', 'number', 'date', 'valid_until', 'file_name',
                        'url', 'url_valid_until'):
                    if item in data and data[item]:
                        if item == 'file_name':
                            file_names.append(item)
                        self.__add_element(se, ns, item, data[item], file_names)
        elif elem == 'legal_entity':
            if isinstance(data, list):
                for itm in data:
                    for item in (
                            'name', 'full_name', 'inn', 'kpp', 'address',
                            'ogrn', 'taxRegDoc', 'govRegDoc', 'govRegDate',
                            'phone', 'email', 'bossFio', 'buhFio', 'bank',
                            'bankAccount', 'lastCtrlDate', 'opf', 'govRegOgv',
                            'person'):
                        if item in itm and itm[item]:
                            self.__add_element(
                                se, ns, item, itm[item], file_names)
                    if data.index(itm) < len(data) - 1:
                        se = etree.SubElement(parent, '{%s}%s' % (ns, elem))
            else:
                for item in (
                        'name', 'full_name', 'inn', 'kpp', 'address', 'ogrn',
                        'taxRegDoc', 'govRegDoc', 'govRegDate', 'phone',
                        'email', 'bossFio', 'buhFio', 'bank', 'bankAccount',
                        'lastCtrlDate', 'opf', 'govRegOgv', 'person'):
                    if item in data and data[item]:
                        self.__add_element(se, ns, item, data[item], file_names)
        elif 'address' in elem:
            for item in (
                    'Postal_Code', 'Region', 'District', 'City',
                    'Urban_District', 'Soviet_Village', 'Locality', 'Street',
                    'House', 'Housing', 'Building', 'Apartment',
                    'Reference_point'):
                if item in data and data[item]:
                    self.__add_element(se, ns, item, data[item], file_names)
        elif elem in ('person', 'confidant'):
            if isinstance(data, list):
                for itm in data:
                    for item in (
                            'surname', 'first_name', 'patronymic', 'address',
                            'fact_address', 'email', 'birthdate',
                            'passport_serial', 'passport_number',
                            'passport_agency', 'passport_date',
                            'phone', 'inn', 'sex', 'snils'):
                        if item in itm and itm[item]:
                            self.__add_element(
                                se, ns, item, itm[item], file_names)
                    if data.index(itm) < len(data) - 1:
                        se = etree.SubElement(parent, '{%s}%s' % (ns, elem))
            else:
                for item in (
                        'surname', 'first_name', 'patronymic', 'address',
                        'fact_address', 'email', 'birthdate', 'passport_serial',
                        'passport_number', 'passport_agency', 'passport_date',
                        'phone', 'inn', 'sex', 'snils'):
                    if item in data and data[item]:
                        self.__add_element(se, ns, item, data[item], file_names)
        else:
            if isinstance(data, (date, datetime)):
                se.text = data.strftime('%Y-%m-%d')
            else:
                se.text = data

    def send_request(self, declar):
        operation = 'SendRequest'
        file_names = []

        element = self.proxy.get_element('ns1:MessagePrimaryContent')
        rr = etree.Element(
            '{urn://augo/smev/uslugi/1.0.0}declar',
            nsmap={'ns1': 'urn://augo/smev/uslugi/1.0.0'})
        self.log.debug(declar)
        for item in (
                'declar_number', 'service', 'register_date', 'end_date',
                'object_address', 'AppliedDocument', 'legal_entity', 'person',
                'confidant', 'Param'):
            if item in declar and declar[item]:
                self.__add_element(
                    rr, 'urn://augo/smev/uslugi/1.0.0', item, declar[item],
                    file_names)
        mpc = element(rr)

        node = self.proxy.create_message(
            self.proxy.service, operation,
            {'MessageID': uuid1(), 'MessagePrimaryContent': mpc},
            CallerInformationSystemSignature=etree.Element('Signature'))
        res = node.find('.//{*}SenderProvidedRequestData')
        res.set('Id', 'SIGNED_BY_CALLER')

        if file_names:
            ns = etree.QName(node.find('.//{*}MessagePrimaryContent')).namespace
            rahl = etree.SubElement(res, '{%s}RefAttachmentHeaderList' % ns)
            for file_name in file_names:
                rah = etree.SubElement(rahl, '{%s}RefAttachmentHeader' % ns)
                etree.SubElement(
                    rah, '{%s}uuid' % ns).text = self.__upload_file(
                    file_name, translate(basename(file_name)))
                f_hash = self.crypto.get_file_hash(file_name)
                etree.SubElement(rah, '{%s}Hash' % ns).text = f_hash
                etree.SubElement(
                    rah, '{%s}MimeType' % ns).text = guess_type(file_name)[0]
                # etree.SubElement(
                #     rah,
                #     '{%s}SignaturePKCS7' % ns).text = self.crypto.get_file_sign(
                #     file_name)

        node_str = etree.tostring(node)
        res = etree.QName(res)
        node_str = node_str.replace(
            b'<ns0:SenderProvidedRequestData',
            b'<ns0:SenderProvidedRequestData xmlns:ns0="' +
            res.namespace.encode() + b'"')
        self.log.debug(node_str)
        res = self.__xml_part(node_str,
                              b'ns0:SenderProvidedRequestData')
        res = self.__call_sign(res)
        res = node_str.decode().replace('<Signature/>', res)
        self.log.debug(res)
        res = self.__send(operation, res.encode('utf-8'))
        self.log.debug(res)
        return res

    def send_response(self, reply_to, declar_number, register_date,
                      result='FINAL', text='', applied_documents=(),
                      ftp_user='anonymous', ftp_pass='anonymous'):
        files = []
        for doc in applied_documents:
            if isinstance(doc, (bytes, str)):
                file_name = os.path.split(doc)[1]
                # file_name = translate(file_name)
                uuid = self.__upload_file(doc, file_name, ftp_user, ftp_pass)
                files.append({uuid: {'name': file_name,
                                     'type': guess_type(doc)[0],
                                     'full_name': doc}})
            if doc.file:
                uuid = self.__upload_file(doc.file, doc.file_name, ftp_user,
                                          ftp_pass)
                # uuid = self.__upload_file(doc.file, translate(doc.file_name),
                #                           ftp_user, ftp_pass)
                files.append({uuid: {'name': doc.file_name,
                                     'type': guess_type(doc.file)[0],
                                     'full_name': doc.file,
                                     'certs': doc.certs
                                     if hasattr(doc, 'certs') and doc.certs
                                     else None}})

        operation = 'SendResponse'
        element = self.proxy.get_element('ns1:MessagePrimaryContent')
        rr = etree.Element(
            '{urn://augo/smev/uslugi/1.0.0}requestResponse',
            nsmap={'ns1': 'urn://augo/smev/uslugi/1.0.0'})
        etree.SubElement(
            rr,
            '{urn://augo/smev/uslugi/1.0.0}declar_number').text = declar_number
        from dateutil.parser import parse
        etree.SubElement(
            rr, '{urn://augo/smev/uslugi/1.0.0}register_date'
        ).text = register_date.strftime('%Y-%m-%d') if isinstance(
            register_date, (date, datetime)) else parse(
            register_date).strftime('%Y-%m-%d')
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
                    ad, '{urn://augo/smev/uslugi/1.0.0}title').text = \
                    doc.title if doc.title else ' '
                etree.SubElement(
                    ad, '{urn://augo/smev/uslugi/1.0.0}number'
                ).text = doc.number if doc.number else 'б/н'
                etree.SubElement(
                    ad, '{urn://augo/smev/uslugi/1.0.0}date'
                ).text = doc.date.strftime('%Y-%m-%d') if isinstance(
                    doc.date, (date, datetime)) else parse(
                    doc.date).strftime('%Y-%m-%d')
                if hasattr(doc, 'valid_until') and doc.valid_until:
                    etree.SubElement(
                        ad, '{urn://augo/smev/uslugi/1.0.0}valid_until'
                    ).text = doc.valid_until
                if hasattr(doc, 'file_name') and doc.file_name:
                    etree.SubElement(
                        ad, '{urn://augo/smev/uslugi/1.0.0}file_name'
                    ).text = doc.file_name
                if hasattr(doc, 'url') and doc.url:
                    etree.SubElement(
                        ad, '{urn://augo/smev/uslugi/1.0.0}url').text = doc.url
                if hasattr(doc, 'url_valid_until') and doc.url_valid_until:
                    etree.SubElement(
                        ad, '{urn://augo/smev/uslugi/1.0.0}url_valid_until'
                    ).text = doc.url_valid_until

        mpc = element(rr)
        node = self.proxy.create_message(
            self.proxy.service, operation,
            {'MessageID': uuid1(), 'To': reply_to,
             'MessagePrimaryContent': mpc},
            CallerInformationSystemSignature=etree.Element('Signature'))
        res = node.find('.//{*}SenderProvidedResponseData')
        res.set('Id', 'SIGNED_BY_CALLER')

        uuids = []
        if files:
            ns = etree.QName(node.find('.//{*}MessagePrimaryContent')).namespace
            rahl = etree.SubElement(res, '{%s}RefAttachmentHeaderList' % ns)
            for item in files:
                uuid, file = item.popitem()
                uuids.append(uuid)
                rah = etree.SubElement(rahl, '{%s}RefAttachmentHeader' % ns)
                etree.SubElement(rah, '{%s}uuid' % ns).text = uuid
                etree.SubElement(
                    rah, '{%s}Hash' % ns).text = self.crypto.get_file_hash(
                    file['full_name'])
                etree.SubElement(rah, '{%s}MimeType' % ns).text = \
                    file['type'] if file['type'] else guess_type(file['name'])[0]
                if file['certs']:
                    etree.SubElement(
                        rah,
                        '{%s}SignaturePKCS7' % ns).text = file['certs']

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
        return res, uuids

    def __call_sign(self, xml):
        method_name = 'sign_' + self.method
        self.log.debug('Calling Crypto.%s' % method_name)
        method = getattr(self.crypto, method_name)
        return method(xml)

    def __upload_file(self, file, file_name, ftp_user='anonymous',
                      ftp_pass='anonymous'):
        self.log.debug(file_name)
        addr = urlparse(self.ftp_addr).netloc
        max_try = 12
        do_loop = True
        while do_loop:
            try:
                with ftplib.FTP(addr, ftp_user, ftp_pass) as con:
                    con.encoding = 'utf-8'
                    uuid = str(uuid1())
                    res = con.mkd(uuid)
                    self.log.debug(res)
                    con.cwd(uuid)
                    with open(file, 'rb') as f:
                        res = con.storbinary('STOR ' + file_name, f)
                    self.log.debug(res)
                    do_loop = False
            except ConnectionResetError:
                max_try -= 1
                if max_try < 0:
                    raise
                do_loop = max_try > 0
        return uuid

    @staticmethod
    def make_sig_zip(file_name, file_path, sig):
        f, f_p = tempfile.mkstemp()
        close(f)
        zip = ZipFile(f_p, mode='w', compression=ZIP_DEFLATED)
        if file_name[0] == '/':
            file_name = file_name[1:]
        # fn = file_name.encode('utf8').decode('cp866')
        zip.write(file_path, file_name)
        zip.writestr(file_name + '.sig', sig)
        zip.close()
        remove(file_path)
        return f_p

    def __load_files(self, attach_files, res, files):
        for uuid, file in attach_files.items():
            file_name = file['FileName']
            rs = self.__load_file(uuid, file_name, file['UserName'],
                                  file['Password'])
            fn, ext = path.splitext(file_name)
            if fn[0] == '/':
                fn = fn[1:]
            if isinstance(rs, (str, bytes)):
                new_ext = guess_extension(file['MimeType'])
                ext = ext.lower()
                if new_ext and not ext:
                    file_name = fn + new_ext.lower()
                else:
                    file_name = fn + ext
            else:
                rs, e = rs
                logging.error(
                    'Error loading file %s: %s\n%s\n\n%s\n\n' %
                    (file_name, str(e),
                     etree.tostring(res.Request.SenderProvidedRequestData.
                                    MessagePrimaryContent._value_1),
                     str(res)))
                raise Exception(
                    'Error loading file %s: %s\n%s\n\n%s\n\n' %
                    (file_name, str(e),
                     etree.tostring(res.Request.SenderProvidedRequestData.
                                    MessagePrimaryContent._value_1),
                     str(res))) from e
                file_name = fn + '.txt'
                with open(rs, 'a') as f:
                    f.write('\n\r\n\r')
                    try:
                        f.write(str(e, errors='ignore'))
                        f.write('\n\r\n\r')
                        f.write(str(res))
                        f.write('\n\r\n\r')
                        f.write(etree.tostring(
                            res.Request.SenderProvidedRequestData.
                                MessagePrimaryContent._value_1))
                    except:
                        from sys import exc_info
                        from traceback import format_exception
                        etype, value, tb = exc_info()
                        trace = ''.join(
                            format_exception(etype, value, tb))
                        msg = ("%s\n" + "*" * 70 + "\n%s\n" +
                               "*" * 70) % (value, trace)
                        f.write(msg)
                        f.write('\n\r\n\r')
                        try:
                            f.write(str(res.Request))
                            f.write('\n\r\n\r')
                            f.write(etree.tostring(
                                res.Request.SenderProvidedRequestData.
                                    MessagePrimaryContent._value_1))
                        except:
                            etype, value, tb = exc_info()
                            trace = ''.join(
                                format_exception(etype, value, tb))
                            msg = ("%s\n" + "*" * 70 + "\n%s\n" +
                                   "*" * 70) % (value, trace)
                            f.write(msg)
                            f.write('\n\r\n\r')
                            f.write(str(res))
            sig = file.get('SignaturePKCS7')
            if sig:
                rs = self.make_sig_zip(file_name, rs, sig)
                file_name = file_name[:-4] + '.zip'
            files[file_name] = rs

    # def __load_files(self, attach_files, res, files):
    #     if reactor.running:
    #         reactor.stop()
    #     defereds = {}
    #     for uuid, file in attach_files.items():
    #         file_name = file['FileName']
    #         rs = self.__load_file_ic(uuid, file_name, file['UserName'],
    #                                  file['Password'])
    #         defereds[file_name] = rs
    #     reactor.run()
    #     for uuid, file in attach_files.items():
    #         file_name = file['FileName']
    #         fn, ext = path.splitext(file_name)
    #         if fn[0] == '/':
    #             fn = fn[1:]
    #         rs = defereds[file_name].result
    #         if isinstance(rs, (str, bytes)):
    #             new_ext = guess_extension(file['MimeType'])
    #             ext = ext.lower()
    #             if new_ext and not ext:
    #                 file_name = fn + new_ext.lower()
    #             else:
    #                 file_name = fn + ext
    #         else:
    #             rs, e = rs
    #             self.log.error(
    #                 'Error loading file %s: %s\n%s\n\n%s\n\n' %
    #                 (file_name, str(e),
    #                  etree.tostring(res.Request.SenderProvidedRequestData.
    #                                 MessagePrimaryContent._value_1),
    #                  str(res)))
    #             raise Exception(
    #                 'Error loading file %s\n\n%s\n%s\n\n' %
    #                 (file_name,
    #                  etree.tostring(res.Request.SenderProvidedRequestData.
    #                                 MessagePrimaryContent._value_1),
    #                  str(res))) from e
    #             file_name = fn + '.txt'
    #             with open(rs, 'a') as f:
    #                 f.write('\n\r\n\r')
    #                 try:
    #                     f.write(str(e, errors='ignore'))
    #                     f.write('\n\r\n\r')
    #                     f.write(str(res))
    #                     f.write('\n\r\n\r')
    #                     f.write(etree.tostring(
    #                         res.Request.SenderProvidedRequestData.
    #                             MessagePrimaryContent._value_1))
    #                 except:
    #                     from sys import exc_info
    #                     from traceback import format_exception
    #                     etype, value, tb = exc_info()
    #                     trace = ''.join(
    #                         format_exception(etype, value, tb))
    #                     msg = ("%s\n" + "*" * 70 + "\n%s\n" +
    #                            "*" * 70) % (value, trace)
    #                     f.write(msg)
    #                     f.write('\n\r\n\r')
    #                     try:
    #                         f.write(str(res.Request))
    #                         f.write('\n\r\n\r')
    #                         f.write(etree.tostring(
    #                             res.Request.SenderProvidedRequestData.
    #                                 MessagePrimaryContent._value_1))
    #                     except:
    #                         etype, value, tb = exc_info()
    #                         trace = ''.join(
    #                             format_exception(etype, value, tb))
    #                         msg = ("%s\n" + "*" * 70 + "\n%s\n" +
    #                                "*" * 70) % (value, trace)
    #                         f.write(msg)
    #                         f.write('\n\r\n\r')
    #                         f.write(str(res))
    #         sig = file.get('SignaturePKCS7')
    #         if sig:
    #             rs = self.__make_zip(file_name, rs, sig)
    #             file_name = file_name[:-4] + '.zip'
    #         files[file_name] = rs
    #
    # @inlineCallbacks
    # def __load_file_ic(self, uuid, file_name, user='anonymous',
    #                   passwd='anonymous'):
    #     self.__calls += 1
    #     try:
    #         r = yield threads.deferToThread(
    #             self.__load_file, uuid, file_name, user, passwd)
    #     finally:
    #         self.__calls -= 1
    #         if not self.__calls:
    #             reactor.stop()
    #     returnValue(r)

    def __load_file(self, uuid, file_name, user='anonymous',
                    passwd='anonymous'):
        addr = urlparse(self.ftp_addr).netloc
        f, file_path = tempfile.mkstemp()
        do_loop = True
        max_try = 12
        closed = False
        encoding = 'utf-8'
        # encodings = ['utf-8', 'cp1251', 'cp866']
        while do_loop:
            do_loop = False
            try:
                with ftplib.FTP(addr, user, passwd) as con:
                    con.encoding = encoding
                    con.cwd(uuid)
                    # lst = con.mlsd()
                    # lst = con.nlst(uuid)
                    if file_name[0] == '/':
                        file_name = file_name[1:]
                    if not closed:
                        close(f)
                        closed = True
                    with open(file_path, 'wb') as fo:
                        con.retrbinary('RETR ' + file_name, fo.write)
            except ftplib.all_errors as e:
                str_e = str(e)
                if user != 'anonymous' and passwd != 'anonymous' \
                        and 'Login incorrect' in str_e:
                    user, passwd = 'anonymous', 'anonymous'
                    do_loop = True
                elif 'No such' in str_e and uuid in str_e \
                        and uuid != uuid.upper():
                    uuid = uuid.upper()
                    do_loop = True
                elif len(uuid) > 2:
                    uuid = '/'
                    do_loop = True
                # elif 'No such' in str_e:
                #     if encodings:
                #         encoding = encodings.pop()
                #         do_loop = True
                else:
                    if max_try:
                        max_try -= 1
                        do_loop = True
                    else:
                        try:
                            self.log.error(str_e, exc_info=True)
                        except UnicodeEncodeError:
                            self.log.error(str_e)
                        from sys import exc_info
                        from traceback import format_exception
                        etype, value, tb = exc_info()
                        trace = ''.join(format_exception(etype, value, tb))
                        msg = ("%s\n" + "*" * 70 + "\n%s\n" + "*" * 70) % (
                            value, trace)
                        if not closed:
                            close(f)
                        with open(file_path, 'wb') as fo:
                            fo.write(
                                str(msg).encode('cp1251', errors='replace') +
                                b'\nFile: ' +
                                file_name.encode('cp1251', errors='replace'))
                        return file_path, e
        return file_path

    def __send(self, operation, msg):
        host = self.proxy.service._binding_options['address']
        host = host[host.index('//') + 2:]
        host = host[:host.index('/')]
        kw = {'_soapheaders': self.proxy.service._client._default_soapheaders,
              'Content-Type': 'text/xml;charset=UTF-8', 'SOAPAction': 'urn:' + operation,
              'Host': 's' + host}
        response = self.proxy.transport.post(
            self.proxy.service._binding_options['address'], msg, kw)
        try:
            import pickle
            with open('response.pkl', 'w') as f:
                pickle.dump(response, f)
        except:
            with open('response.pkl', 'wb') as f:
                f.write(response.content)
        try:
            res = self.proxy.service._binding.process_reply(
                self.proxy.service._client,
                self.proxy.service._binding.get(operation), response)
        except XMLParseError as e:
            with open('response.txt', 'wb') as f:
                f.write(response.content)
            logging.warning(response.content)
            raise e
        if not res and b'--uuid:' in response.content:
            res = response.content[
                  response.content.index(b'Content-Type:'):]
            res = res[res.index(b'--uuid:') + 7:-2]
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

    def _dict_to_xml(self, tag, d: dict, pre=None, nsmap=None):
        elem = etree.Element("{%s}%s" % (pre, tag) if pre else tag, nsmap=nsmap)
        for key, val in d.items():
            if isinstance(val, dict):
                child = self._dict_to_xml(key, val, pre, nsmap)
            else:
                child = etree.Element("{%s}%s" % (pre, key) if pre else key, nsmap=nsmap)
                child.text = str(val)
            elem.append(child)
        return elem

    def create_orders_request(self, orders: dict = (), files: list = None,
                              uri='http://epgu.gosuslugi.ru/elk/status/1.0.2'):
        operation = 'SendRequest'
        element = self.proxy.get_element('ns1:MessagePrimaryContent')
        eor = etree.Element('{%s}ElkOrderRequest' % uri, nsmap={'ns1': uri})
        eor.set("env", "EPGU")  # Код маршрутизации
        cor = etree.SubElement(eor, '{%s}CreateOrdersRequest' % uri, nsmap={'ns1': uri})
        cor.append(self._dict_to_xml("orders", orders, pre=uri, nsmap={'ns1': uri}))
        mpc = element(eor)
        node = self.proxy.create_message(
            self.proxy.service, operation,
            {'MessageID': uuid1(), 'MessagePrimaryContent': mpc},
            CallerInformationSystemSignature=etree.Element('Signature'))
        if files:
            uploaded = self.__upload_files(node, files, 'SenderProvidedRequestData')
            if uploaded:
                sh = node.find('.//{*}statusHistory')
                atts = etree.SubElement(sh, '{%s}attachments' % uri)
                for file_data in uploaded:
                    att = etree.SubElement(atts, '{%s}attachment' % uri)
                    etree.SubElement(att, '{%s}FSuuid' % uri).text = file_data.get('uuid')
                    etree.SubElement(att, '{%s}docTypeId' % uri).text = 'ELK_RESULT'
        self.log.debug(etree.tostring(node))
        res = self.__sign_node(node, 'SenderProvidedRequestData')
        res = self.__send(operation, res.encode('utf-8'))
        self.log.debug(res)

    def update_orders_request(self, orders: dict = (), files: list = None,
                              uri='http://epgu.gosuslugi.ru/elk/status/1.0.2', test=False):
        operation = 'SendRequest'
        element = self.proxy.get_element('ns1:MessagePrimaryContent')
        eor = etree.Element('{%s}ElkOrderRequest' % uri, nsmap={'ns1': uri})
        eor.set("env", "EPGU")  # Код маршрутизации
        cor = etree.SubElement(eor, '{%s}UpdateOrdersRequest' % uri, nsmap={'ns1': uri})
        cor.append(self._dict_to_xml("orders", orders, pre=uri, nsmap={'ns1': uri}))
        mpc = element(eor)
        node = self.proxy.create_message(
            self.proxy.service, operation,
            {'TestMessage': '', 'MessageID': uuid1(), 'MessagePrimaryContent': mpc} if test else
            {'MessageID': uuid1(), 'MessagePrimaryContent': mpc},
            CallerInformationSystemSignature=etree.Element('Signature'))
        if files:
            uploaded = self.__upload_files(node, files, 'SenderProvidedRequestData')
            if uploaded:
                sh = node.find('.//{*}statusHistory')
                atts = etree.SubElement(sh, '{%s}attachments' % uri)
                for file_data in uploaded:
                    att = etree.SubElement(atts, '{%s}attachment' % uri)
                    etree.SubElement(att, '{%s}FSuuid' % uri).text = file_data.get('uuid')
                    etree.SubElement(att, '{%s}docTypeId' % uri).text = 'ELK_RESULT'
        self.log.debug(etree.tostring(node))
        res = self.__sign_node(node, 'SenderProvidedRequestData')
        res = self.__send(operation, res.encode('utf-8'))
        self.log.debug(res)
        return res

    def __upload_files(self, node, file_names, signed_tag='SenderProvidedRequestData'):
        ns = etree.QName(node.find('.//{*}MessagePrimaryContent')).namespace
        res = node.find('.//{*}%s' % signed_tag)
        rahl = etree.SubElement(res, '{%s}RefAttachmentHeaderList' % ns)
        uploaded = []
        for file_name in file_names:
            rah = etree.SubElement(rahl, '{%s}RefAttachmentHeader' % ns)
            uuid = self.__upload_file(file_name, translate(basename(file_name)))
            etree.SubElement(rah, '{%s}uuid' % ns).text = uuid
            f_hash = self.crypto.get_file_hash(file_name)
            etree.SubElement(rah, '{%s}Hash' % ns).text = f_hash
            mime_type = guess_type(file_name)[0]
            if not mime_type:
                mime_type = 'application/octet-stream'
            etree.SubElement(
                rah, '{%s}MimeType' % ns).text = mime_type
            uploaded.append({'uuid': uuid, 'Hash': f_hash, 'MimeType': mime_type})
        return uploaded

    def get_response(self, resp_name: str, uri: str, node_id=None):
        operation = 'GetResponse'
        if sys.version_info.major == 3 and sys.version_info.minor <= 5:
            import timezone
            timestamp = timezone.utcnow()
        else:
            import pytz
            timestamp = datetime.now(pytz.utc)
        node = self.proxy.create_message(
            self.proxy.service, operation,
            {'NamespaceURI': uri, 'RootElementLocalName': resp_name,
             'Timestamp': timestamp, 'NodeID': node_id},
            CallerInformationSystemSignature=etree.Element('Signature'))
        node[0][0][0].set('Id', 'SIGNED_BY_CALLER')
        node_str = etree.tostring(node)
        self.log.debug(node_str)
        res = self.__call_sign(
            self.__xml_part(node_str, b'ns1:MessageTypeSelector'))
        res = node_str.decode().replace('<Signature/>', res)
        res = self.__send(operation, res)
        self.log.debug(res)
        return res

    def __sign_node(self, node, signed_tag: str):
        res = node.find('.//{*}%s' % signed_tag)
        res.set('Id', 'SIGNED_BY_CALLER')
        node_str = etree.tostring(node)
        res = etree.QName(res)
        node_str = node_str.replace(b'<ns0:%s' % signed_tag.encode(),
                                    (b'<ns0:%s xmlns:ns0="' % signed_tag.encode()) + res.namespace.encode() + b'"')
        self.log.debug(node_str)
        res = self.__xml_part(node_str, b'ns0:%s' % signed_tag.encode())
        res = self.__call_sign(res)
        res = node_str.decode().replace('<Signature/>', res)
        return res

    def _send_request(self, req_name: str, uri: str, data, test=False):
        operation = 'SendRequest'
        element = self.proxy.get_element('ns1:MessagePrimaryContent')
        if isinstance(data, dict):
            rr = self._dict_to_xml(req_name, data, pre=uri, nsmap={'ns1': uri})
            mpc = element(rr)
        elif isinstance(data, (str, bytes)):
            rr = etree.Element('{%s}%s' % (uri, req_name), nsmap={'ns1': uri})
            rr.text = data
            mpc = element(rr)
        elif data:
            mpc = element(data)
        else:
            mpc = element(etree.Element('{%s}%s' % (uri, req_name), nsmap={'ns1': uri}))
        node = self.proxy.create_message(
            self.proxy.service, operation,
            {'TestMessage': '', 'MessageID': uuid1(), 'MessagePrimaryContent': mpc} if test else
            {'MessageID': uuid1(), 'MessagePrimaryContent': mpc},
            CallerInformationSystemSignature=etree.Element('Signature'))
        res = self.__sign_node(node, 'SenderProvidedRequestData')
        res = self.__send(operation, res)
        self.log.debug(res)
        return res


if __name__ == '__main__':
    loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel,
                        format='%(asctime)s %(levelname)s:%(module)s:%(name)s:%(lineno)d: %(message)s')
    # logging.root.handlers[0].setLevel(logging.DEBUG)
    # logging.getLogger('zeep.xsd').setLevel(logging.INFO)
    # logging.getLogger('zeep.wsdl').setLevel(logging.INFO)
    # logging.getLogger('urllib3').setLevel(logging.INFO)
    # from logging.handlers import TimedRotatingFileHandler
    # backupcount = 7
    # handler = TimedRotatingFileHandler(
    #     os.path.abspath("dmsis.log"), when='D',
    #     backupCount=backupcount, encoding='cp1251')
    # handler.setFormatter(logging.Formatter(
    #     '%(asctime)s %(name)s:%(module)s(%(lineno)d): %(levelname)s: '
    #     '%(message)s'))
    # logging.root.addHandler(handler)
    # logging.info("Set logging level to '%s'", loglevel)
    # logging.root.setLevel(loglevel)
    #
    # if len(sys.argv) < 2:
    #     handler = TimedRotatingFileHandler(
    #         os.path.abspath("dmsic.log"), when='D', backupCount=0,
    #         encoding='cp1251')
    #     handler.setFormatter(logging.Formatter(
    #         '%(asctime)s %(name)s:%(module)s(%(lineno)d): %(levelname)s: '
    #         '%(message)s'))
    #     logging.root.addHandler(handler)
    #     handler.setLevel(logging.DEBUG)

    # a = Adapter(serial='2F5D 25DB 6C79 E302 1D08 4786 DEFC C15A 0EAC B515',
    #             container='ep_ov-2022',
    #             wsdl="http://smev3-n0.test.gosuslugi.ru:7500/smev/v1.2/ws?wsdl",
    #             ftp_addr="ftp://smev3-n0.test.gosuslugi.ru/",
    #             crt_name='АДМИНИСТРАЦИЯ УССУРИЙСКОГО ГОРОДСКОГО ОКРУГА')
    a = Adapter(serial='2F5D 25DB 6C79 E302 1D08 4786 DEFC C15A 0EAC B515',
                container='ep_ov-2022',
                wsdl="http://172.20.3.12:7500/smev/v1.2/ws?wsdl",
                ftp_addr="ftp://172.20.3.12/",
                crt_name='АДМИНИСТРАЦИЯ УССУРИЙСКОГО ГОРОДСКОГО ОКРУГА')

    orders = {
        'order': {
            # 'user': {
            #     # 'userPersonalDoc': {
            #     #     'PersonalDocType': '1',  # ЕЛК. Тип документа удостоверяющего личность - Паспорт гражданина РФ (https://esnsi.gosuslugi.ru/classifiers/7211/view/10)
            #     #     'series': '0502',
            #     #     'number': '918150',
            #     #     'lastName': 'Савенко',
            #     #     'firstName': 'Михаил',
            #     #     'middleName': 'Юрьевич',
            #     #     'citizenship': '643'  # ЕЛК. Гражданство - РОССИЯ (https://esnsi.gosuslugi.ru/classifiers/7210/view/27)
            #     # }
            #     'userPersonalDoc': {
            #         'PersonalDocType': '1',
            #         # ЕЛК. Тип документа удостоверяющего личность - Паспорт гражданина РФ (https://esnsi.gosuslugi.ru/classifiers/7211/view/10)
            #         'series': '0507',
            #         'number': '380602',
            #         'lastName': 'Эйснер',
            #         'firstName': 'Ольга',
            #         'middleName': 'Владимировна',
            #         'citizenship': '643'
            #         # ЕЛК. Гражданство - РОССИЯ (https://esnsi.gosuslugi.ru/classifiers/7210/view/27)
            #     }
            #
            #     # 'userDocSnils': {
            #     #     'snils': '060-908-001-34',
            #     #     'lastName': 'Савенко',
            #     #     'firstName': 'Михаил',
            #     #     'middleName': 'Юрьевич',
            #     #     'citizenship': '643'
            #     # }
            #
            #     # 'userDocSnilsBirthDate': {
            #     #     'citizenship': '643',
            #     #     'snils': '060-908-001-34',
            #     #     'birthDate': '1980-09-21'
            #     # }
            #
            #     # 'userDocInn': {
            #     #     'INN': '253602023181',
            #     #     'lastName': 'Савенко',
            #     #     'firstName': 'Михаил',
            #     #     'middleName': 'Юрьевич',
            #     #     'citizenship': '643'
            #     # }
            # },
            'organization': {
                'ogrn_inn_UL': {
                    'inn_kpp': {
                        'inn': '2511004094'
                    }#,
                    #'UlTitle': 'Администрация Уссурийского городского округа'
                }
            },
            'senderKpp': '251101001',
            'senderInn': '2511004094',
            # 'serviceTargetCode': '2540100010000664823',
            'serviceTargetCode': '2540100010000664885',
            'userSelectedRegion': '00000000',
            'orderNumber': 'test_num02',
            'requestDate': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+10:00'),
            'OfficeInfo': {
                'ApplicationAcceptance': '4'  # ЕЛК. Канал приема - Подразделение ведомства (https://esnsi.gosuslugi.ru/classifiers/7213/view/8)
            },
            'statusHistoryList': {
                'statusHistory': {
                    'status': '6',  # ЕЛК. Статусы - Заявление принято (https://esnsi.gosuslugi.ru/classifiers/7212/view/86)
                    'IsInformed': 'true',
                    'statusDate': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+10:00')
                }
            }
        }
    }
    a.create_orders_request(orders)

    orders = {
        'order': {
            'orderNumber': 'test_num',
            'senderKpp': '251101001',
            'senderInn': '2511004094',
            'statusHistoryList': {
                'statusHistory': {
                    'status': '223',
                    # 'IsInformed': 'true',
                    'statusDate': datetime.now().strftime('%Y-%m-%dT%H:%M:%S+10:00')
                }
            }
        }
    }
    # a.update_orders_request(orders, ['D:\\dmsis\\smev.py'])

    import time
    time.sleep(10)
    res = a.get_response('ElkOrderResponse', 'http://epgu.gosuslugi.ru/elk/status/1.0.2', None)
    while not res:
        time.sleep(10)
        res = a.get_response('ElkOrderResponse', 'http://epgu.gosuslugi.ru/elk/status/1.0.2', None)
    if isinstance(res, bytes):
        res = res.decode(errors='replace')
    if res and 'MessagePrimaryContent' in res:
        res = etree.fromstring(res)
    if hasattr(res, 'Response') \
            and hasattr(res.Response, 'SenderProvidedResponseData'):
        if hasattr(res.Response.SenderProvidedResponseData, "MessageID"):
            a.send_ack(res.Response.SenderProvidedResponseData.MessageID)
        if hasattr(res.Response.SenderProvidedResponseData, 'MessagePrimaryContent') \
                and res.Response.SenderProvidedResponseData.MessagePrimaryContent:
            val: etree._Element = res.Response.SenderProvidedResponseData.MessagePrimaryContent._value_1
            try:
                print(val, type(val))
                print(val.findtext('.//{*}message'),
                      ', '.join([elem.findtext('.//{*}message') for elem in val.findall('.//{*}order')]))
                print('elkOrderNumber', val.findtext('.//{*}elkOrderNumber'))
                print(len(val[0]), val[0][1], [elem for elem in val[0][2]])
            except Exception as e:
                print("ERROR:", e)
            res = etree.tostring(res.Response.SenderProvidedResponseData.MessagePrimaryContent._value_1)
    print(res)

    orders = {
        'order': {
            'user': {
                'userDocPassport': {
                    'passportRF': {
                        'series': '0502',
                        'number': '918150',
                        'issueDate': '2002-07-03'
                    },
                    'lastName': 'Савенко',
                    'firstName': 'Михаил',
                    'middleName': 'Юрьевич'
                }

                # 'userDocSnils': {
                #     'snils': '060-908-001-34',
                #     'lastName': 'Савенко',
                #     'firstName': 'Михаил',
                #     'middleName': 'Юрьевич',
                # }
            },
            # 'serviceTargetCode': '2540100010000664823',
            'serviceTargetCode': '2540100010000664885',
            'userSelectedRegion': '00000000',
            'orderNumber': 'a',
            'requestDate': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'statusHistoryList': {
                'statusHistory': {
                    'status': '6',
                    # ЕЛК. Статусы - Заявление принято (https://esnsi.gosuslugi.ru/classifiers/7212/view/86)
                    'statusDate': '2022-12-17T09:30:47Z'
                }
            }
        }
    }
    # a.create_orders_request(orders, 'http://epgu.gosuslugi.ru/elk/order/3.3.0')
    # time.sleep(10)
    # res = a.get_response('ElkOrderRequest', 'http://epgu.gosuslugi.ru/elk/order/3.3.0', None)
    # while not res:
    #     time.sleep(10)
    #     res = a.get_response('ElkOrderRequest', 'http://epgu.gosuslugi.ru/elk/order/3.3.0', None)
    # if isinstance(res, bytes):
    #     res = res.decode(errors='replace')
    # if res and 'MessagePrimaryContent' in res:
    #     res = etree.fromstring(res)
    # if hasattr(res, 'Response') \
    #         and hasattr(res.Response, 'SenderProvidedResponseData'):
    #     if hasattr(res.Response.SenderProvidedResponseData, "MessageID"):
    #         a.send_ack(res.Response.SenderProvidedResponseData.MessageID)
    #     if hasattr(res.Response.SenderProvidedResponseData, 'MessagePrimaryContent') \
    #             and res.Response.SenderProvidedResponseData.MessagePrimaryContent:
    #         res = etree.tostring(res.Response.SenderProvidedResponseData.MessagePrimaryContent._value_1)
    # print(res)
