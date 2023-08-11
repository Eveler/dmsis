# -*- encoding: utf-8 -*-
import logging
import tempfile
from datetime import datetime
from os import write, close, remove
from zipfile import ZipFile

from lxml import etree

from plugins import DirectumRX
from smev import Adapter


class Cnsi:
    def __init__(self, a: Adapter):
        self.smev = a
        self.urn = 'urn://x-artefacts-smev-gov-ru/esnsi/smev-integration/read/2.0.1'

    def get_revision_list(self, code):
        self.smev._send_request('CnsiRequest', self.urn,
                                {'GetClassifierRevisionList': {'code': code,'pageSize': '500'}})
        #  TODO: Remove time.sleep
        import time
        time.sleep(10)
        res = self.smev.get_response('CnsiRequest', self.urn, None)
        count = 10
        while not res and count:
            time.sleep(10)
            res = self.smev.get_response('CnsiRequest', self.urn, None)
            count -= 1
        if isinstance(res, bytes):
            res = res.decode(errors='replace')
        if res and 'MessagePrimaryContent' in res:
            res = etree.fromstring(res)
        if hasattr(res, 'Response') and hasattr(res.Response, 'SenderProvidedResponseData'):
            if hasattr(res, 'Response') and hasattr(res.Response, 'SenderProvidedResponseData') \
                    and hasattr(res.Response.SenderProvidedResponseData, "MessageID"):
                self.smev.send_ack(res.Response.SenderProvidedResponseData.MessageID)
            if hasattr(res.Response.SenderProvidedResponseData, 'RequestRejected') \
                    and res.Response.SenderProvidedResponseData.RequestRejected:
                logging.warning("Список версий '%s' не получен: %s" % (code,
                                res.Response.SenderProvidedResponseData.RequestRejected))
                # RejectionReasonDescription
                return False
            if hasattr(res.Response.SenderProvidedResponseData, 'MessagePrimaryContent') \
                    and hasattr(res.Response.SenderProvidedResponseData.MessagePrimaryContent, '_value_1'):
                res = res.Response.SenderProvidedResponseData.MessagePrimaryContent._value_1
                max_revision = 0
                timestamp = datetime.strptime('', '')
                revisions = []
                for elem in res.iterfind('.//{*}RevisionDescriptor'):
                    if timestamp < datetime.strptime(elem.findtext('.//{*}timestamp')[:-6], '%Y-%m-%d'):
                        timestamp = datetime.strptime(elem.findtext('.//{*}timestamp')[:-6], '%Y-%m-%d')
                        max_revision = elem.findtext('.//{*}revision')
                    revisions.append(elem.findtext('.//{*}revision'))
                return revisions, max_revision
        print(res)
        return None

    def get_increment(self, code, revision):
        #  TODO: Incomplete
        self.smev._send_request('CnsiRequest', self.urn,
                                {'GetAvailableIncrement': {'code': code, 'revision': revision}})
        #  TODO: Remove time.sleep
        import time
        time.sleep(10)
        res = self.smev.get_response('CnsiRequest', self.urn, None)
        count = 10
        while not res and count:
            time.sleep(10)
            res = self.smev.get_response('CnsiRequest', self.urn, None)
            count -= 1
        if isinstance(res, bytes):
            res = res.decode(errors='replace')
        if res and 'MessagePrimaryContent' in res:
            res = etree.fromstring(res)
        if hasattr(res, 'Response') and hasattr(res.Response, 'SenderProvidedResponseData'):
            if hasattr(res, 'Response') and hasattr(res.Response, 'SenderProvidedResponseData') \
                    and hasattr(res.Response.SenderProvidedResponseData, "MessageID"):
                self.smev.send_ack(res.Response.SenderProvidedResponseData.MessageID)
            if hasattr(res.Response.SenderProvidedResponseData, 'MessagePrimaryContent') \
                    and hasattr(res.Response.SenderProvidedResponseData.MessagePrimaryContent, '_value_1'):
                res = res.Response.SenderProvidedResponseData.MessagePrimaryContent._value_1
                res = etree.tostring(res)
            if hasattr(res.Response.SenderProvidedResponseData, 'RequestRejected') \
                    and res.Response.SenderProvidedResponseData.RequestRejected:
                logging.warning("Инкрементное обновление '%s' не получено: %s" % (code,
                                res.Response.SenderProvidedResponseData.RequestRejected))
                # RejectionReasonDescription
                return False
        print(res)
        return None

    def get_data(self, code, revision):
        '''
        Query CNSI reference data
        :param code: Reference code
        :param revision: Data revision. Revisions list cold quered by get_revision_list()
        :return: Data in form {'fieldID': {'name': '', 'values: []}}
        '''

        self.smev._send_request('CnsiRequest', self.urn,
                           {'GetClassifierData': {'code': code, 'revision': revision, 'pageSize': '50000'}})

        #  TODO: Remove time.sleep
        import time
        time.sleep(10)
        res = self.smev.get_response('CnsiRequest', self.urn, None)
        count = 10
        while not res and count:
            time.sleep(10)
            res = self.smev.get_response('CnsiRequest', self.urn, None)
            count -= 1
        if isinstance(res, bytes):
            res = res.decode(errors='replace')
        if res and 'MessagePrimaryContent' in res:
            res = etree.fromstring(res)
        if hasattr(res, 'Response') and hasattr(res.Response, 'SenderProvidedResponseData'):
            if hasattr(res, 'Response') and hasattr(res.Response, 'SenderProvidedResponseData') \
                    and hasattr(res.Response.SenderProvidedResponseData, "MessageID"):
                self.smev.send_ack(res.Response.SenderProvidedResponseData.MessageID)
            if hasattr(res.Response.SenderProvidedResponseData, 'RequestRejected') \
                    and res.Response.SenderProvidedResponseData.RequestRejected:
                logging.warning("Данные справочника '%s' не получены: %s" % (code,
                                res.Response.SenderProvidedResponseData.RequestRejected))
                return False
            if hasattr(res.Response.SenderProvidedResponseData, 'MessagePrimaryContent') \
                    and hasattr(res.Response.SenderProvidedResponseData.MessagePrimaryContent, '_value_1'):
                if hasattr(res, 'AttachmentContentList') and res.AttachmentContentList:
                    # attach_files = {}
                    # attach_head_list = res.Response.SenderProvidedResponseData.AttachmentHeaderList.AttachmentHeader
                    # for head in attach_head_list:
                    #     attach_files[head.contentId] = {'MimeType': head.MimeType}
                    attach_list = res.AttachmentContentList.AttachmentContent
                    # i = 1
                    files = []
                    #  Save attachments to disk
                    for attach in attach_list:
                        # file_name = str('file' + str(i))
                        # i += 1
                        # ext = guess_extension(attach_files[attach.Id]['MimeType'])
                        # file_name = file_name + ext if ext else '.zip'
                        f, fn = tempfile.mkstemp()
                        write(f, attach.Content)
                        close(f)
                        files.append(fn)
                    if len(files) > 1:
                        #  Merge attachments
                        f, fn = tempfile.mkstemp()
                        for flname in files:
                            with open(flname, 'rb') as fl:
                                write(f, fl.read())
                            remove(flname)
                        close(f)
                    if files:
                        with ZipFile(fn) as myzip:
                            for file_name in myzip.namelist():
                                with myzip.open(file_name) as myfile:
                                    # doc = xmltodict.parse(myfile)
                                    doc = etree.fromstring(myfile.read())
                                    classifier = doc.find('.//{*}simple-classifier')
                                    data = doc.find('.//{*}data')
                                    doc = {}
                                    for elem in classifier.getchildren():
                                        if 'attribute' in elem.tag:
                                            doc[elem.get('uid')] = {'name': elem.get('name'), 'values': []}
                                    for elem in data.iterfind('.//{*}record'):
                                        for val in elem.iterfind('.//{*}attribute-value'):
                                            doc[val.get('attribute-ref')]['values'].append(
                                                ''.join(v.text for v in val.getchildren()))
                        remove(fn)
                    return doc
                res = res.Response.SenderProvidedResponseData.MessagePrimaryContent._value_1
                res = etree.tostring(res)
        print(res)
        return None

    def list_classifiers(self):
        self.smev._send_request('CnsiRequest', self.urn, {'ListClassifiers': {'ClassifierDescriptorList': 'true'}})
        #  TODO: Remove time.sleep
        import time
        time.sleep(10)
        res = self.smev.get_response('CnsiRequest', self.urn, None)
        count = 10
        while not res and count:
            time.sleep(10)
            res = self.smev.get_response('CnsiRequest', self.urn, None)
            count -= 1
        if isinstance(res, bytes):
            res = res.decode(errors='replace')
        if res and 'MessagePrimaryContent' in res:
            res = etree.fromstring(res)
        if hasattr(res, 'Response') and hasattr(res.Response, 'SenderProvidedResponseData'):
            if hasattr(res, 'Response') and hasattr(res.Response, 'SenderProvidedResponseData') \
                    and hasattr(res.Response.SenderProvidedResponseData, "MessageID"):
                self.smev.send_ack(res.Response.SenderProvidedResponseData.MessageID)
            if hasattr(res.Response.SenderProvidedResponseData, 'MessagePrimaryContent') \
                    and hasattr(res.Response.SenderProvidedResponseData.MessagePrimaryContent, '_value_1'):
                res = res.Response.SenderProvidedResponseData.MessagePrimaryContent._value_1
                cls_list = []
                for elem in res.iterfind('.//{*}ClassifierDescriptor'):
                    cls_list.append({
                        'code': elem.findtext('.//{*}code'),
                        'name': elem.findtext('.//{*}name'),
                        'revision': elem.findtext('.//{*}revision')
                    })
                if cls_list:
                    return cls_list
                else:
                    res = etree.tostring(res)
            if hasattr(res.Response.SenderProvidedResponseData, 'RequestRejected') \
                    and res.Response.SenderProvidedResponseData.RequestRejected:
                logging.warning("Список справочников не получен: %s" %
                                res.Response.SenderProvidedResponseData.RequestRejected)
                return False
        print(res)
        return None


if __name__ == '__main__':
    loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel,
                        format='%(asctime)s %(levelname)s:%(module)s:%(name)s:%(lineno)d: %(message)s')

    a = Adapter(serial='00AB 63BB BD9B 3728 C624 1DC9 C482 6264 F4',
                container='ep_ov-2023',
                wsdl="http://172.20.3.12:7500/smev/v1.2/ws?wsdl",
                ftp_addr="ftp://172.20.3.12/",
                crt_name='АДМИНИСТРАЦИЯ УССУРИЙСКОГО ГОРОДСКОГО ОКРУГА')
    cnsi = Cnsi(a)
    res = cnsi.smev.get_response('CnsiRequest',
                                 'urn://x-artefacts-smev-gov-ru/esnsi/smev-integration/read/2.0.1', None)
    while res:
        res = cnsi.smev.get_response('CnsiRequest',
                                     'urn://x-artefacts-smev-gov-ru/esnsi/smev-integration/read/2.0.1', None)

    # cls_data = cnsi.list_classifiers()
    # print(cls_data)

    revisions = cnsi.get_revision_list('ELK_STATUS')
    if revisions:
        revisions, max_revision = revisions
        print(revisions, max(revisions), max_revision)
        res = cnsi.get_data('ELK_STATUS', max_revision)
        print(etree.tostring(res) if isinstance(res, etree._Element) else res)
        dis = DirectumRX("http://127.0.0.1:8082/IntegrationService.svc?singleWsdl")
        res = dis.update_elk_status(res)
        print(res)


    # if res and isinstance(res, (str, bytes)):
    #     with open('C:\\Users\\Администратор\\Downloads\\1111111111.xml', 'w') as out:
    #         out.write(res if isinstance(res, str) else res.decode(errors='replace'))
