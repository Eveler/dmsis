#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Реализует логику System.Security.Cryptography.Xml (GOST 2012 + SMEV Transform) с использованием pycades и lxml.
"""

import sys
import base64
import logging
import os
import re
import subprocess
import tempfile
from lxml import etree
from encodings.base64_codec import base64_encode


# Попытка импорта библиотеки для СМЭВ-трансформации
if "smev_transform" not in sys.modules:
    try:
        from smev_transform import Transform
        HAS_SMEV_TRANSFORM = True
    except ImportError:
        log = logging.getLogger('cryptopro')
        log.setLevel(logging.root.level)
        log.warning("'smev-transform' library not found. Install via 'pip install smev-transform' for full SMEV compliance.")


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
    DS = "http://www.w3.org/2000/09/xmldsig#"

    def __init__(self, cert_sn="", container=None, crt_name=None,
                 use_com=False):
        self.log = logging.getLogger('cryptopro')
        self.log.setLevel(logging.root.level)
        self.__container = container
        self.serial = cert_sn.replace(' ', '').replace("\n", "").replace("\r", "")
        self.__crt_name = crt_name
        self.use_com = use_com


    @property
    def use_com(self):
        return self.__use_com

    @use_com.setter
    def use_com(self, v):
        self.__use_com = v
        if v:
            import pythoncom
            from win32com.client import Dispatch
            pythoncom.CoInitialize()
            self.signed_xml = Dispatch('CAdESCOM.SignedXML')

            crt = None
            if self.serial:
                oStore = Dispatch("CAdESCOM.Store")
                oStore.Open(Crypto.CAPICOM_CURRENT_USER_STORE)
                for cert in oStore.Certificates:
                    if cert.SerialNumber == self.serial:
                        crt = cert

            if crt:
                self.signer = Dispatch("CAdESCOM.CPSigner")
                self.signer.Certificate = crt
            else:
                self.signer = None

    @property
    def container(self):
        return self.__container

    @container.setter
    def container(self, value):
        self.__container = value

    @property
    def crt_name(self):
        return self.__crt_name

    @crt_name.setter
    def crt_name(self, value):
        self.__crt_name = value

    def sign(self, xml):
        if self.__use_com:
            return self.sign_com(xml)
        else:
            return self.sign_csp(xml)

    def __get_tool_path(self, tool_name):
        """Поиск утилит КриптоПро в стандартных путях."""
        if "linux" in sys.platform:
            paths = ["/opt/cprocsp/bin/amd64", "/opt/cprocsp/bin/ia32", "/usr/bin"]
        else:
            paths = ['C:\\Program Files (x86)\\Crypto Pro\\CSP', 'C:\\Program Files\\Crypto Pro\\CSP']
        for p in paths:
            path = os.path.join(p, tool_name)
            if os.path.isfile(path):
                return path
        return tool_name

    def __run_cmd(self, cmd, check=True, binary=False):
        try:
            res = subprocess.run(cmd, shell=isinstance(cmd, str), check=check, capture_output=True, text=not binary)
            self.log.debug(f"cmd = {cmd}\nstdout = {res.stdout}")
            return res.stdout, res.returncode
        except subprocess.CalledProcessError as e:
            if not binary:
                self.log.error(f"Command failed: {cmd}\nError: {e.stderr}")
            raise

    def get_file_hash(self, file_path):
        csptest_path = self.__get_tool_path('csptest.exe' if "win32" in sys.platform else 'csptest')
        cpverify_path = self.__get_tool_path('cpverify.exe' if "win32" in sys.platform else 'cpverify')
        args = [cpverify_path, '-mk', '-alg', 'GR3411_2012_256', os.path.abspath(file_path), '-inverted_halfbytes', '0']
        try:
            out = subprocess.check_output(args, stderr=subprocess.STDOUT)
            self.log.debug(out.decode(encoding='cp866'))

            out = bytes.fromhex(out.decode())
            hsh_bytes = base64_encode(out)[0][:-1].decode().replace('\n', '')
            return hsh_bytes
        except:
            if 'out' in locals():
                self.log.error(out.decode(encoding='cp866'))
            raise

    def get_file_sign(self, file_path, crt_name=None, crt_file=None):
        """ Generates PKCS #7 signature"""
        csptest_path = self.__get_tool_path('csptest.exe' if "win32" in sys.platform else 'csptest')
        signtmp_f, signtmp_fn = tempfile.mkstemp()
        os.close(signtmp_f)
        if crt_file:
            args = [csptest_path, '-sfsign', '-sign', '-detached',
                    '-in', os.path.abspath(file_path), '-out', signtmp_fn,
                    '-add', '-base64', '-addsigtime', '-signature', crt_file]
        else:
            args = [csptest_path, '-sfsign', '-sign',
                    '-my', crt_name if crt_name else self.__crt_name,
                    '-detached', '-in', os.path.abspath(file_path), '-out',
                    signtmp_fn, '-add', '-base64', '-addsigtime']
        try:
            out = subprocess.check_output(args, stderr=subprocess.STDOUT)
            self.log.debug(out.decode(encoding='cp866'))

            with open(signtmp_fn, 'rb') as f:
                hsh = f.read()
            return hsh.replace(b'\n', b'').replace(b'\r', b'')
        except subprocess.CalledProcessError as e:
            self.log.error(e.output.decode(encoding='cp866'))
            raise
        finally:
            os.remove(signtmp_fn)

    def get_buf_sign(self, buf, crt_name=None):
        if isinstance(buf, str):
            buf = buf.encode(errors='replace')
        tmp_f, tmp_fn = tempfile.mkstemp()
        os.write(tmp_f, buf)
        os.close(tmp_f)
        try:
            return self.get_file_sign(tmp_fn, crt_name=crt_name)
        except:
            raise
        finally:
            os.remove(tmp_fn)

    def get_cert_info(self):
        """Получение отпечатка и имени контейнера через certmgr."""
        CERTMGR = self.__get_tool_path("certmgr" if "linux" in sys.platform else "certmgr.exe")
        out, _ = self.__run_cmd([CERTMGR, "-list", "-store", "uMy"], check=False)
        if "No items found" in out or not out:
            out, _ = self.__run_cmd([CERTMGR, "-list", "-store", "mMy"], check=False)
        blocks = re.split(r'\n\d+-+\n', out)

        for block in blocks:
            if not block.strip(): continue

            # Ищем сертификаты, у которых ЕСТЬ привязка к контейнеру (закрытый ключ)
            m_container = re.search(r'Container\s*:\s*(.+)', block)
            if not m_container: continue

            self.log.debug(f"block = {block}")
            m_serial = re.search(r'Serial\s*:\s*(?:0x)?([0-9A-Fa-f\s]+)', block)
            m_thumbprint = re.search(r'(?:SHA1\s+)?(?:Thumbprint|Fingerprint)\s*:\s*([0-9A-Fa-f\s]+)', block)

            if not m_serial or not m_thumbprint: continue
            curr_serial = m_serial.group(1).replace(" ", "").replace("\n", "").replace("\r", "").upper()
            self.log.debug(f"curr_serial = {curr_serial}")
            self.log.debug(f"self.serial = {self.serial}")

            if self.serial and curr_serial != self.serial.replace(" ", "").upper():
                continue

            return (
                m_thumbprint.group(1).replace(" ", "").replace("\n", "").replace("\r", "").lower(),
                m_container.group(1).replace("\n", "").replace("\r", "").strip()
            )

        raise Exception("Не найден сертификат с закрытым ключом в хранилище.")

    def compute_digest_csp(self, file_path):
        """Вычисление хэша ГОСТ Р 34.11-2012 через OpenSSL."""
        CSPTEST = self.__get_tool_path("csptest" if "linux" in sys.platform else "csptest.exe")
        hash_file = file_path + ".hash"
        cmd = [CSPTEST, "-keyset", "-hash", "GOST12_256", "-in", file_path, "-hashout", hash_file]

        try:
            self.__run_cmd(cmd)
            with open(hash_file, 'rb') as f:
                hash_bytes = f.read()

            # csptest пишет ровно 32 байта (256 бит) для GOST12_256
            # Если вдруг в файл попал мусор или заголовки, берем последние 32 байта
            if len(hash_bytes) != 32 and len(hash_bytes) >= 32:
                hash_bytes = hash_bytes[-32:]

            return base64.b64encode(hash_bytes).decode('utf-8')
        finally:
            if os.path.exists(hash_file):
                os.unlink(hash_file)
        raise Exception("Не удалось вычислить хэш через openssl dgst.")

    def compute_raw_signature(self, container_name, file_path):
        """Создание raw-подписи через csptest и инверсия байт для XMLDSig."""
        sig_file = file_path + ".sig"
        # Пробуем оба типа ключей, так как сертификат может быть любым
        key_types = ["signature", "exchange"]
        # Пробуем имя контейнера как есть и с префиксом \\.\ (если его нет)
        containers_to_try = [container_name]
        if not container_name.startswith("\\\\.\\"):
            containers_to_try.append(f"\\\\.\\{container_name}")
        CSPTEST = self.__get_tool_path("csptest" if "linux" in sys.platform else "csptest.exe")
        for cont in containers_to_try:
            for ktype in key_types:
                cmd = [
                    CSPTEST, "-keys", "-sign", "GOST12_256",
                    "-silent",  # Предотвращает зависание в ожидании ввода с клавиатуры
                    "-cont", cont,
                    "-keytype", ktype,
                    "-in", file_path,
                    "-out", sig_file
                ]

                # Если у контейнера есть пароль, его можно передать через переменную окружения
                pin = os.environ.get("CSP_PIN")
                if pin:
                    cmd.extend(["-pin", pin])

                try:
                    # Подавляем вывод ошибок для "тихого" перебора вариантов
                    subprocess.run(cmd, check=True, capture_output=True, text=True)

                    with open(sig_file, 'rb') as f:
                        raw_sig = f.read()

                    if os.path.exists(sig_file):
                        os.unlink(sig_file)

                    # КриптоПро возвращает r и s в little-endian. XMLDSig требует big-endian.
                    return base64.b64encode(raw_sig[::-1]).decode('utf-8')

                except subprocess.CalledProcessError:
                    # Если вариант не сработал, пробуем следующий
                    continue

        raise Exception(
            f"Не удалось создать подпись. Ключ не найден в контейнере '{container_name}'.\n"
            f"Проверьте, что сертификат имеет привязку к закрытому ключу, и что вы запускаете "
            f"скрипт от имени пользователя-владельца контейнера."
        )

    def get_cert_b64(self, thumbprint):
        """Выгрузка сертификата в Base64 через cryptcp."""
        cer_file = tempfile.NamedTemporaryFile(delete=False, suffix=".cer")
        cer_file.close()
        try:
            CRYPTCP = self.__get_tool_path("cryptcp" if "linux" in sys.platform else "cryptcp.exe")
            cmd = [CRYPTCP, "-copycert", "-thumbprint", thumbprint, "-df", cer_file.name, "-der"]
            self.__run_cmd(cmd)
            with open(cer_file.name, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        finally:
            if os.path.exists(cer_file.name): os.unlink(cer_file.name)

    def sign_csp(self, xml_str):
        if not xml_str:
            raise Exception("Error: Empty XML input")

        thumbprint, container = self.get_cert_info()
        try:
            #root = etree.fromstring(xml_str.encode('utf-8'))
            root = etree.fromstring(xml_str)
        except Exception as e:
            raise Exception(f"Error parsing XML: {e}")
        target = root.find('.//*[@Id="SIGNED_BY_CALLER"]')
        if target is None: target = root

        # 1. Каноникализация + SMEV Transform
        c14n_data = etree.tostring(target, method='c14n', exclusive=True, with_comments=False)
        if HAS_SMEV_TRANSFORM:
            smev = Transform()
            data_bytes = smev.process(c14n_data.decode('utf-8')).encode('utf-8')
        else:
            data_bytes = c14n_data

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tf:
            tf.write(data_bytes)
            data_file = tf.name
        try:
            digest_value = self.compute_digest_csp(data_file)
        finally:
            os.unlink(data_file)

        # 2. Формирование SignedInfo
        signature = etree.Element(f"{{{Crypto.DS}}}Signature")
        signed_info = etree.SubElement(signature, f"{{{Crypto.DS}}}SignedInfo")

        etree.SubElement(signed_info, f"{{{Crypto.DS}}}CanonicalizationMethod", Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#")
        etree.SubElement(signed_info, f"{{{Crypto.DS}}}SignatureMethod", Algorithm="urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34102012-gostr34112012-256")

        reference = etree.SubElement(signed_info, f"{{{Crypto.DS}}}Reference", URI="#SIGNED_BY_CALLER")
        transforms = etree.SubElement(reference, f"{{{Crypto.DS}}}Transforms")
        etree.SubElement(transforms, f"{{{Crypto.DS}}}Transform", Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature")
        etree.SubElement(transforms, f"{{{Crypto.DS}}}Transform", Algorithm="urn://smev-gov-ru/xmldsig/transform")
        etree.SubElement(transforms, f"{{{Crypto.DS}}}Transform", Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#")

        etree.SubElement(reference, f"{{{Crypto.DS}}}DigestMethod", Algorithm="urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34112012-256")
        etree.SubElement(reference, f"{{{Crypto.DS}}}DigestValue").text = digest_value

        signed_info_c14n = etree.tostring(signed_info, method='c14n', exclusive=True, with_comments=False)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tf:
            tf.write(signed_info_c14n)
            si_file = tf.name
        try:
            signature_value = self.compute_raw_signature(container, si_file)
        finally:
            os.unlink(si_file)

        etree.SubElement(signature, f"{{{Crypto.DS}}}SignatureValue").text = signature_value

        # 3. Вставка сертификата
        key_info = etree.SubElement(signature, f"{{{Crypto.DS}}}KeyInfo")
        x509_data = etree.SubElement(key_info, f"{{{Crypto.DS}}}X509Data")
        etree.SubElement(x509_data, f"{{{Crypto.DS}}}X509Certificate").text = self.get_cert_b64(thumbprint)

        return etree.tostring(signature, encoding='unicode', pretty_print=True)

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

    def sign_sharp(self, xml, xmlsigner_path=''):
        self.log.debug(xml)
        if not xmlsigner_path:
            xmlsigner_path = 'xmlsigner/xmlsigner/bin/Release/xmlsigner.exe' if sys.platform == "linux" else 'xmlsigner\\xmlsigner\\bin\\Release\\xmlsigner.exe'
        try:
            if isinstance(xml, str):
                xml = xml.encode()
            args = ['mono', os.path.abspath(xmlsigner_path), 'xmlsigner.exe'] if sys.platform == "linux" else [os.path.abspath(xmlsigner_path), 'xmlsigner.exe']
            if self.serial:
                args.append(self.serial)
            out = subprocess.check_output(args, input=xml,
                                          stderr=subprocess.STDOUT)
            self.log.debug(out.decode(encoding='cp866'))
            return out.decode(encoding='cp866')
        except subprocess.CalledProcessError as e:
            self.log.error(e.output.decode(encoding='cp866'))
            raise Exception(e.output.decode(encoding='cp866'))


    def get_certificate(self):
        if "pycades" not in sys.modules:
            pycades = sys.modules["pycades"]
        else:
            from pycades import pycades

        """Получение сертификата из хранилища КриптоПро по серийному номеру."""
        store = pycades.Store()
        # Открываем хранилище контейнеров (MY)
        ##store.Open(pycades.CADESCOM_CONTAINER_STORE, pycades.CAPICOM_MY_STORE, pycades.CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED)
        store.Open(pycades.CAPICOM_CURRENT_USER_STORE, pycades.CAPICOM_MY_STORE, pycades.CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED)
        certs = store.Certificates
        if certs.Count == 0:
            raise Exception("Сертификаты с приватным ключом не найдены в хранилище.")

        if self.serial:
            sn = self.serial.upper()
            for i in range(1, certs.Count + 1):
                cert = certs.Item(i)
                if cert.SerialNumber.replace(" ", "").upper() == sn:
                    return cert
            raise Exception(f"Сертификат с серийным номером {self.serial} не найден.")

        # Возвращаем первый сертификат, если номер не задан
        return certs.Item(1)

    def apply_transforms(self, target_element):
        """
        Применение трансформаций к целевому узлу:
        1. Эксклюзивная каноникализация (ExcC14N)
        2. СМЭВ-трансформация (если доступна библиотека)
        """
        # lxml c14n возвращает байты (utf-8)
        c14n_data = etree.tostring(target_element, method='c14n', exclusive=True, with_comments=False)

        if HAS_SMEV_TRANSFORM:
            smev = Transform()
            # smev_transform ожидает строку и возвращает строку
            transformed_str = smev.process(c14n_data.decode('utf-8'))
            return transformed_str.encode('utf-8')
        else:
            return c14n_data

    def compute_digest(self, data_bytes):
        if "pycades" not in sys.modules:
            pycades = sys.modules["pycades"]
        else:
            from pycades import pycades

        """Вычисление хэша ГОСТ Р 34.11-2012 (256 бит) и возврат в Base64."""
        hasher = pycades.HashedData()
        hasher.Algorithm = pycades.CADESCOM_HASH_ALGORITHM_CP_GOST_3411_2012_256
        try:
            hasher.DataEncoding = pycades.CADESCOM_ENCODE_BASE64
            hasher.Hash(base64.b64encode(data_bytes).decode('utf-8'))
        except AttributeError:
            # Fallback: если DataEncoding не поддерживается, хэшируем как есть
            hasher.Hash(data_bytes)

        hash_value = hasher.Value
        # 1. Если библиотека вернула сырые байты
        if isinstance(hash_value, (bytes, bytearray)):
            return base64.b64encode(hash_value).decode('utf-8')

        val_str = str(hash_value).strip().replace("\n", "").replace("\r", "").replace(" ", "")

        # 2. Пробуем декодировать как Hex (чаще всего pycades.Value возвращает именно Hex)
        try:
            hash_bytes = bytes.fromhex(val_str)
            # Для ГОСТ 2012 256 бит длина хэша должна быть 32 байта
            if len(hash_bytes) == 32:
                return base64.b64encode(hash_bytes).decode('utf-8')
        except ValueError:
            pass

        # 3. Пробуем декодировать как Base64 (если библиотека вернула его сразу)
        try:
            # Восстанавливаем паддинг, если его нет
            padding = '=' * (-len(val_str) % 4)
            decoded = base64.b64decode(val_str + padding)
            if len(decoded) == 32:
                return val_str + padding
        except Exception:
            pass

        # 4. Если ничего не подошло, возвращаем как есть
        return val_str

    def create_signature_value(self, hasher, cert):
        """
        Создает подпись через RawSignature, автоматически определяя формат
        возвращаемого значения (Hex, Base64 или bytes).
        """
        raw_sig = pycades.RawSignature()
        try:
            sig_res = raw_sig.SignHash(hasher, cert)
        except Exception:
            sig_res = self._unwrap(raw_sig).SignHash(hasher, cert)

        # 1. Если библиотека вернула сырые байты
        if isinstance(sig_res, (bytes, bytearray)):
            sig_bytes = sig_res
        else:
            val_str = str(sig_res).strip().replace(" ", "")

            # 2. Пробуем Hex (стандарт для большинства версий)
            try:
                sig_bytes = bytes.fromhex(val_str)
            except ValueError:
                # 3. Пробуем Base64 (на случай, если библиотека вернула его)
                try:
                    # Восстанавливаем паддинг, если его нет
                    padding = '=' * (-len(val_str) % 4)
                    sig_bytes = base64.b64decode(val_str + padding)
                except Exception:
                    # Fallback: кодируем как есть (маловероятно)
                    sig_bytes = val_str.encode('utf-8')

        # КриптоПро возвращает r и s в little-endian.
        # Для XMLDSig требуется big-endian, поэтому инвертируем байты.
        return base64.b64encode(sig_bytes[::-1]).decode('utf-8')

    @staticmethod
    def _unwrap(obj):
        """
        Извлекает нативный объект из обертки pycades.
        Обертка из пипа обычно хранит оригинал в _original_instance или _obj.
        """
        if obj is None:
            return None
        if hasattr(obj, '_original_instance'):
            return obj._original_instance
        if hasattr(obj, '_obj'):
            return obj._obj
        return obj

    def sign_pycades(self, xml_str):
        if not xml_str:
            raise Exception("Empty XML input")

        if "pycades" not in sys.modules:
            pycades = sys.modules["pycades"]
        else:
            from pycades import pycades

        cert = self.get_certificate()

        try:
            root = etree.fromstring(xml_str.encode('utf-8') if isinstance(xml_str, str) else xml)
        except Exception as e:
            raise Exception(f"Error parsing XML: {e}")

        # Ищем узел с Id="SIGNED_BY_CALLER"
        target = root.find('.//*[@Id="SIGNED_BY_CALLER"]')
        if target is None:
            target = root  # Fallback

        # 1. Применяем трансформации (C14N + SMEV)
        transformed_bytes = self.apply_transforms(target)

        # 2. Вычисляем DigestValue
        digest_value = self.compute_digest(transformed_bytes)

        # 3. Формируем скелет подписи <ds:Signature>
        signature = etree.Element(f"{{{Crypto.DS}}}Signature")
        signed_info = etree.SubElement(signature, f"{{{Crypto.DS}}}SignedInfo")

        etree.SubElement(signed_info, f"{{{Crypto.DS}}}CanonicalizationMethod",
                        Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#")
        etree.SubElement(signed_info, f"{{{Crypto.DS}}}SignatureMethod",
                        Algorithm="urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34102012-gostr34112012-256")

        reference = etree.SubElement(signed_info, f"{{{Crypto.DS}}}Reference", URI="#SIGNED_BY_CALLER")
        transforms = etree.SubElement(reference, f"{{{Crypto.DS}}}Transforms")

        # Порядок трансформаций согласно требованиям СМЭВ
        etree.SubElement(transforms, f"{{{Crypto.DS}}}Transform", Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature")
        etree.SubElement(transforms, f"{{{Crypto.DS}}}Transform", Algorithm="urn://smev-gov-ru/xmldsig/transform")
        etree.SubElement(transforms, f"{{{Crypto.DS}}}Transform", Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#")

        etree.SubElement(reference, f"{{{Crypto.DS}}}DigestMethod",
                        Algorithm="urn:ietf:params:xml:ns:cpxmlsec:algorithms:gostr34112012-256")
        etree.SubElement(reference, f"{{{Crypto.DS}}}DigestValue").text = digest_value

        # 4. Каноникализируем блок <ds:SignedInfo>
        signed_info_c14n = etree.tostring(signed_info, method='c14n', exclusive=True, with_comments=False)

        # 5. Хэшируем SignedInfo
        si_hasher = pycades.HashedData()
        si_hasher.Algorithm = pycades.CADESCOM_HASH_ALGORITHM_CP_GOST_3411_2012_256
        try:
            si_hasher.DataEncoding = pycades.CADESCOM_ENCODE_BASE64
            si_hasher.Hash(base64.b64encode(signed_info_c14n).decode('utf-8'))
        except AttributeError:
            si_hasher.Hash(signed_info_c14n)

        # 6. Подписываем хэш с помощью RawSignature
        # signer = pycades.Signer()
        # signer.Certificate = self._unwrap(cert)
        # pin = os.environ.get("CSP_PIN", "")
        # if pin:
            # signer.KeyPin = pin
        signature_value = self.create_signature_value(self._unwrap(si_hasher), self._unwrap(cert))

        etree.SubElement(signature, f"{{{Crypto.DS}}}SignatureValue").text = signature_value

        # 7. Добавляем KeyInfo с сертификатом
        key_info = etree.SubElement(signature, f"{{{Crypto.DS}}}KeyInfo")
        x509_data = etree.SubElement(key_info, f"{{{Crypto.DS}}}X509Data")

        cert_b64 = cert.Export(pycades.CADESCOM_ENCODE_BASE64)
        cert_b64 = cert_b64.replace("-----BEGIN CERTIFICATE-----", "").replace("-----END CERTIFICATE-----", "").replace("\n", "").replace("\r", "")
        etree.SubElement(x509_data, f"{{{Crypto.DS}}}X509Certificate").text = cert_b64

        # 8. Вывод результата (только узел <ds:Signature>, как в C#)
        return etree.tostring(signature, encoding='unicode', pretty_print=True)


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

    from pycades import pycades
    print(pycades.__file__)

    signer = Crypto('00F024FE0A9C8A879E9FFC2BBB3A63A5F7')

    res = signer.sign_csp(xml_str)
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
