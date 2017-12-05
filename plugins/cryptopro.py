# -*- encoding: utf-8 -*-
import logging
import os
import subprocess
import tempfile
from encodings.base64_codec import base64_encode
from sys import platform

if 'win32' not in platform:
    raise Exception('This is for Windows only')


class Crypto:
    CAPICOM_CURRENT_USER_STORE = 2
    CAPICOM_ENCODE_ANY = 0xffffffff
    CAPICOM_ENCODE_BASE64 = 0
    CAPICOM_ENCODE_BINARY = 1
    CAPICOM_CERTIFICATE_SAVE_AS_PFX = 0
    CAPICOM_CERTIFICATE_SAVE_AS_CER = 1
    CAPICOM_CERTIFICATE_INCLUDE_CHAIN_EXCEPT_ROOT = 0
    CAPICOM_CERTIFICATE_INCLUDE_WHOLE_CHAIN = 1
    CAPICOM_CERTIFICATE_INCLUDE_END_ENTITY_ONLY = 2
    CADESCOM_XML_SIGNATURE_TYPE_ENVELOPED = 0
    CADESCOM_XML_SIGNATURE_TYPE_ENVELOPING = 1
    CADESCOM_XML_SIGNATURE_TYPE_TEMPLATE = 2

    def __init__(self, cert_sn="", container=None, use_com=False):
        self.log = logging.getLogger('cryptopro')
        self.log.setLevel(logging.root.level)
        self.__use_com = use_com
        self.__container = container
        self.serial = cert_sn.replace(' ', '')

        if use_com:
            import pythoncom
            from win32com.client import Dispatch
            pythoncom.CoInitialize()
            self.signed_xml = Dispatch('CAdESCOM.SignedXML')

            crt = None
            if cert_sn:
                cert_sn = cert_sn.replace(' ', '')
                oStore = Dispatch("CAdESCOM.Store")
                oStore.Open(Crypto.CAPICOM_CURRENT_USER_STORE)
                for cert in oStore.Certificates:
                    if cert.SerialNumber == cert_sn:
                        crt = cert

            if crt:
                self.signer = Dispatch("CAdESCOM.CPSigner")
                self.signer.Certificate = crt
            else:
                self.signer = None

    @property
    def use_com(self):
        return self.__use_com

    @use_com.setter
    def use_com(self, v):
        self.__use_com = v

    @property
    def container(self):
        return self.__container

    @container.setter
    def container(self, value):
        self.__container = value

    def sign(self, xml):
        if self.__use_com:
            return self.sign_com(xml)
        else:
            return self.sign_csp(xml)

    def get_file_hash(self, file_path):
        csptest_path = 'C:\\Program Files (x86)\\Crypto Pro\\CSP\\csptest.exe'
        hashtmp_f, hashtmp_fn = tempfile.mkstemp()
        os.close(hashtmp_f)
        args = [csptest_path, 'csptest.exe', '-silent', '-keyset', '-hash',
                'GOST', '-container', self.__container, '-keytype', 'exchange',
                '-in', os.path.abspath(file_path), '-hashout', hashtmp_fn]
        out = subprocess.check_output(args, stderr=subprocess.STDOUT)
        self.log.debug(out.decode(encoding='cp866'))

        with open(hashtmp_fn, 'rb') as f:
            hsh = f.read()
        hsh_bytes = base64_encode(hsh)[0][:-1].decode().replace('\n', '')
        return hsh_bytes

    # TODO: Enveloped signature
    def sign_csp(self, xml):
        csptest_path = 'C:\\Program Files (x86)\\Crypto Pro\\CSP\\csptest.exe'
        intmp_f, intmp_fn = tempfile.mkstemp()
        outtmp_f, outtmp_fn = tempfile.mkstemp()
        hashtmp_f, hashtmp_fn = tempfile.mkstemp()
        try:
            if isinstance(xml, str):
                xml = xml.encode()
            os.write(intmp_f, xml)
            os.close(intmp_f)
            os.close(outtmp_f)
            os.close(hashtmp_f)
            args = [csptest_path, 'csptest.exe', '-silent', '-keyset', '-sign',
                    'GOST', '-hash', 'GOST', '-container', self.__container,
                    '-keytype', 'exchange', '-in', intmp_fn, '-out', outtmp_fn,
                    '-hashout', hashtmp_fn]
            out = subprocess.check_output(args, stderr=subprocess.STDOUT)
            self.log.debug(out.decode(encoding='cp866'))

            with open(outtmp_fn, 'rb') as f:
                sgn = f.read()
            sgn = sgn[::-1]
            sign = base64_encode(sgn)[0][:-1].decode().replace('\n', '')
            with open(hashtmp_fn, 'rb') as f:
                hsh = f.read()
            hsh_bytes = base64_encode(hsh)[0][:-1].decode().replace('\n', '')
        except subprocess.CalledProcessError as e:
            self.log.error(e.output.decode(encoding='cp866'))
            return e.output.decode(encoding='cp866')
        finally:
            os.remove(intmp_fn)
            os.remove(outtmp_fn)
            os.remove(hashtmp_fn)

        outtmp_f, outtmp_fn = tempfile.mkstemp()
        try:
            os.close(outtmp_f)
            args = [csptest_path, 'csptest.exe', '-keyset', '-container',
                    self.__container, '-keytype', 'exchange', '-expcert',
                    outtmp_fn]
            out = subprocess.check_output(args, stderr=subprocess.STDOUT)
            self.log.debug(out.decode(encoding='cp866'))

            with open(outtmp_fn, 'rb') as f:
                crt = f.read()
            cert = base64_encode(crt)[0][:-1]
        except subprocess.CalledProcessError as e:
            self.log.error(e.output.decode(encoding='cp866'))
            return e.output.decode(encoding='cp866')
        finally:
            os.remove(outtmp_fn)

        if b'Signature xmlns' in xml:
            # TODO: Template signature
            pass
        return '<ds:Signature ' \
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
               '<ds:DigestValue>' + hsh_bytes + \
               '</ds:DigestValue></ds:Reference></ds:SignedInfo>' \
               '<ds:SignatureValue>' + sign + \
               '</ds:SignatureValue><ds:KeyInfo><ds:X509Data>' \
               '<ds:X509Certificate>' + cert.decode() + \
               '</ds:X509Certificate></ds:X509Data></ds:KeyInfo></ds:Signature>'

    def sign_com(self, xml, sign_type=CADESCOM_XML_SIGNATURE_TYPE_ENVELOPED):
        self.log.debug(xml)
        self.signed_xml.Content = xml
        self.signed_xml.SignatureType = sign_type
        self.signed_xml.SignatureMethod = 'http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411'
        self.signed_xml.DigestMethod = 'http://www.w3.org/2001/04/xmldsig-more#gostr3411'
        if self.signer:
            return self.signed_xml.Sign(self.signer)
        else:
            return self.signed_xml.Sign()

    def sign_sharp(self, xml):
        self.log.debug(xml)
        xmlsigner_path = 'xmlsigner\\xmlsigner\\bin\\Release\\xmlsigner.exe'
        try:
            if isinstance(xml, str):
                xml = xml.encode()
            args = [os.path.abspath(xmlsigner_path), 'xmlsigner.exe']
            if self.serial:
                args.append(self.serial)
            out = subprocess.check_output(args, input=xml,
                                          stderr=subprocess.STDOUT)
            self.log.debug(out.decode(encoding='cp866'))
            return out.decode(encoding='cp866')
        except subprocess.CalledProcessError as e:
            self.log.error(e.output.decode(encoding='cp866'))
            raise Exception(e.output.decode(encoding='cp866'))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    # signed_xml = Dispatch('CAdESCOM.SignedXML')
    xml_str = '<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"><soap-env:Body><ns0:GetRequestRequest xmlns:ns0="urn://x-artefacts-smev-gov-ru/services/message-exchange/types/1.2"><ns1:MessageTypeSelector xmlns:ns1="urn://x-artefacts-smev-gov-ru/services/message-exchange/types/basic/1.2" Id="SIGNED_BY_CALLER"><ns1:Timestamp>2017-11-22T00:54:55.936780</ns1:Timestamp></ns1:MessageTypeSelector><ns0:CallerInformationSystemSignature><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411"/><ds:Reference URI="#SIGNED_BY_CALLER"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/><ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#gostr3411"/><ds:DigestValue/></ds:Reference></ds:SignedInfo><ds:SignatureValue/><ds:KeyInfo><ds:X509Data><ds:X509Certificate/></ds:X509Data></ds:KeyInfo></ds:Signature></ns0:CallerInformationSystemSignature></ns0:GetRequestRequest></soap-env:Body></soap-env:Envelope>'
    xml_str = '<ns1:MessageTypeSelector xmlns:ns1="urn://x-artefacts-smev-gov-ru/services/message-exchange/types/basic/1.2" Id="SIGNED_BY_CALLER"><ns1:Timestamp>2017-11-22T00:54:55.936780</ns1:Timestamp></ns1:MessageTypeSelector>'
    # signed_xml.Content = xml_str
    # signed_xml.SignatureType = Crypto.CADESCOM_XML_SIGNATURE_TYPE_ENVELOPED
    # XmlDsigGost3410Url = "urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34102001-gostr3411"
    # signed_xml.SignatureMethod = 'http://www.w3.org/2001/04/xmldsig-more#gostr34102001-gostr3411'
    # XmlDsigGost3411Url = "urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr3411"
    # signed_xml.DigestMethod = 'http://www.w3.org/2001/04/xmldsig-more#gostr3411'
    # res = signed_xml.Sign(oSigner)
    signer = Crypto('008E BDC8 291F 0003 81E7 11E1 AF7A 5ED3 27', use_com=True)

    res = signer.sign_sharp(xml_str)
    print(res)
    quit()

    res = signer.sign(xml_str)
    print(res)
    signer.signed_xml.Verify(res)
    print(signer.signed_xml.Signers[0].SignatureStatus.IsValid)

    signer.use_com = False
    signer.container = "049fc71a-1ff0-4e06-8714-03303ae34afd"
    res = signer.sign(xml_str)
    print(res)
