# -*- encoding: utf-8 -*-

# Twisted reactor sends GetRequest by timer
# Got requests stored in DB

# Then it queries Directum for changed status for stored requests and sends
# SendResponse if status changed

import logging
import os
from datetime import date, timedelta
from sys import version_info, platform

from dateutil.utils import today

from smev_cnsi import Cnsi

if 'win32' in platform:
    if version_info.major == 3 and version_info.minor <= 5:
        from win32._service import SERVICE_STOP_PENDING
    else:
        from win32.win32service import SERVICE_STOP_PENDING
#from win32serviceutil import ServiceFramework, HandleCommandLine

import requests
from db import Db
from plugins.directum import IntegrationServices, IntegrationServicesException
from smev import Adapter
from twisted.internet import task, reactor
from twisted.python import log


class Integration:
    def __init__(self, use_config=True, config_path='./dmsis.ini'):
        self.__smev = None
        self.__directum = None
        logging.basicConfig(
            format='%(asctime)s %(name)s:%(module)s(%(lineno)d): '
                   '%(levelname)s: %(message)s', level=logging.INFO)
        if use_config:
            self.parse_config(config_path)
        else:
            self.mail_addr = ''
            self.smev_wsdl = "http://smev3-d.test.gosuslugi.ru:7500/smev/v1.2/ws?wsdl"
            self.smev_ftp = "ftp://smev3-d.test.gosuslugi.ru/"
            self.directum_wsdl = "http://snadb:8082/IntegrationService.svc?singleWsdl"
            self.smev_uri = 'urn://augo/smev/uslugi/1.0.0'
            self.local_name = 'directum'
            self.cert_method = 'sharp'
            self.crt_serial = None
            self.crt_name = 'Администрация Уссурийского городского округа'
            self.mail_server = None
            self.ftp_user, self.ftp_pass = 'anonymous', 'anonymous'
            self.zip_signed_doc = False
            self.check_workdays = False

        try:
            self.__smev = Adapter(self.smev_wsdl, self.smev_ftp,
                                  method=self.cert_method,
                                  crt_name=self.crt_name,
                                  container=self.container,
                                  serial=self.crt_serial)
        except Exception:
            self.report_error()

        try:
            self.__directum = IntegrationServices(self.directum_wsdl)
        except Exception:
            self.report_error()

        self.db = Db()

    @property
    def directum(self):
        if not self.__directum:
            try:
                self.__directum = IntegrationServices(self.directum_wsdl)
            except Exception:
                self.report_error()

        return self.__directum

    @directum.setter
    def directum(self, value):
        self.__directum = value

    @property
    def smev(self):
        if not self.__smev:
            self.__smev = Adapter(self.smev_wsdl, self.smev_ftp,
                                  method=self.cert_method,
                                  crt_name=self.crt_name,
                                  container=self.container,
                                  serial=self.crt_serial)
        return self.__smev

    @smev.setter
    def smev(self, value):
        self.__smev = value

    def run(self):
        lc = task.LoopingCall(self.step)
        lc.start(self.repeat_every)

    def step(self):
        """
        Sends GetRequest. Then queries Directum for changed status for stored
        requests and sends SendResponse if status changed
        """
        # Send to DIRECTUM previously saved declars
        sent = False
        try:
            for declar, files, reply_to, uuid in self.db.all_declars_as_xsd():
                try:
                    res = self.directum.add_declar(declar, files=files)
                    self.db.add_update(uuid, declar.declar_number,
                                       reply_to, directum_id=res)
                    logging.info('Добавлено/обновлено дело с ID = %s' % res)
                    self.db.delete_declar(uuid)
                    sent = True
                    try:
                        self.smev.send_ack(uuid)
                    except:
                        logging.warning(
                            'Failed to send AckRequest.', exc_info=True)
                    try:
                        params = [('ID', res)]
                        self.directum.run_script('СтартЗадачПоМУ', params)
                    except:
                        logging.warning('Error while run directum`s script '
                                        '"СтартЗадачПоМУ"', exc_info=True)
                    # try:
                    #     params = ['ID', res]
                    #     self.directum.run_script('СтартЗадачПоМУ', params)
                    # except:
                    #     logging.warning('Error while run directum`s script '
                    #                     '"СтартЗадачПоМУ"', exc_info=True)
                except IntegrationServicesException as e:
                    if "Услуга не найдена" in e.message:
                        logging.warning(
                            "Услуга '%s' не найдена. Дело № %s от %s" %
                            (declar.service, declar.declar_number,
                             declar.register_date.strftime('%d.%m.%Y')))
                        self.smev.send_ack(uuid, 'false')
                        self.smev.send_response(reply_to, declar.declar_number,
                                                declar.register_date.strftime(
                                                    '%d.%m.%Y'), 'ERROR',
                                                "Услуга '%s' не найдена" % declar.service)
                        self.db.delete_declar(uuid)
                    else:
                        logging.warning(
                            'Failed to send saved data to DIRECTUM.',
                            exc_info=True)
                # except FileNotFoundError:
                #     self.db.delete_declar(uuid)
                except:
                    logging.warning(
                        'Failed to send saved data to DIRECTUM.',
                        exc_info=True)
            if sent:
                try:
                    self.directum.run_script('СтартЗадачПоМУ')
                except:
                    logging.warning(
                        'Error while run directum`s script "СтартЗадачПоМУ"',
                        exc_info=True)
        except Exception:
            self.report_error()
            self.db.rollback()

        check_requests = requests.get('https://isdayoff.ru/' + today().strftime('%Y%m%d')).text == '0' \
            if self.check_workdays else True
        if check_requests:
            declar = 1
            received = False
            try:
                declar, uuid, reply_to, files = self.smev.get_request(
                    uri='urn://augo/smev/uslugi/1.0.0', local_name='declar')
                if declar:
                    received = True
                    try:
                        res = self.directum.add_declar(declar, files=files)
                        self.db.add_update(uuid, declar.declar_number, reply_to,
                                           directum_id=res)
                        logging.info('Добавлено/обновлено дело с ID = %s' % res)
                        try:
                            self.smev.send_ack(uuid)
                        except:
                            logging.warning(
                                'Failed to send AckRequest.', exc_info=True)
                        try:
                            params = [('ID', res)]
                            self.directum.run_script('СтартЗадачПоМУ', params)
                        except:
                            logging.warning('Error while run directum`s script '
                                            '"СтартЗадачПоМУ"', exc_info=True)
                        # try:
                        #     params = ['ID', res]
                        #     self.directum.run_script('СтартЗадачПоМУ', params)
                        # except:
                        #     logging.warning('Error while run directum`s script '
                        #                     '"СтартЗадачПоМУ"', exc_info=True)
                    except IntegrationServicesException as e:
                        if "Услуга не найдена" in e.message:
                            logging.warning(
                                "Услуга '%s' не найдена. Дело № %s от %s" %
                                (declar.service, declar.declar_number,
                                 declar.register_date.strftime('%d.%m.%Y')))
                            self.smev.send_ack(uuid)
                            self.smev.send_response(reply_to,
                                                    declar.declar_number,
                                                    declar.register_date.strftime(
                                                        '%d.%m.%Y'), 'ERROR',
                                                    "Услуга '%s' не найдена" % declar.service)
                        else:
                            logging.warning(
                                'Failed to send saved data to DIRECTUM.',
                                exc_info=True)
                    except Exception:
                        logging.warning(
                            'Failed to send data to DIRECTUM. Saving locally.',
                            exc_info=True)
                        self.db.save_declar(declar, uuid, reply_to, files)
                        self.smev.send_ack(uuid)
                else:
                    # logging.warning("Получен пустой ответ")
                    # self.smev.send_ack(uuid, 'false')
                    pass
            except Exception:
                self.report_error()
                self.db.rollback()
            if received:
                try:
                    self.directum.run_script('СтартЗадачПоМУ')
                except:
                    logging.warning(
                        'Error while run directum`s script "СтартЗадачПоМУ"',
                        exc_info=True)

        # Send final response
        try:
            for request in self.db.all_not_done():
                declar = self.directum.search('ДПУ', 'ИД=%s' % request.directum_id)

                # For all requests check if declar`s end date is set
                if declar and declar[0].get('Дата5'):
                    applied_docs = self.directum.get_result_docs(request.directum_id, self.crt_name,
                                                                 self.zip_signed_doc)

                    text = 'Услуга предоставлена'
                    # if declar[0].get('СтатусУслуги'):
                    #     state = self.directum.search('СОУ', 'ИД=%s' % declar[0].get('СтатусУслуги'))
                    #     if state[0].get('Наименование'):
                    #         text += '. Статус: %s' % state[0].get('Наименование')

                    try:
                        res, uuids = self.smev.send_response(request.reply_to, request.declar_num, request.declar_date,
                                                        text=text, applied_documents=applied_docs,
                                                        ftp_user=self.ftp_user, ftp_pass=self.ftp_pass)
                        logging.info(
                            'Результат услуги отправлен. Дело № %s от %s' %
                            (request.declar_num, request.declar_date))
                        if applied_docs:
                            logging.info('Прикреплены документы:')
                        for doc in applied_docs:
                            logging.info(
                                '%s от %s № %s' %
                                (doc.title, doc.date[:19],
                                 doc.number if doc.number else 'б/н'))
                        request.done = True
                        self.db.commit()

                        # Send final status to ELK
                        st_list = self.directum.get_declar_status_data(request.directum_id, permanent_status='3')
                        for status in st_list:
                            files = []
                            for item in uuids:
                                uuid, ad = item.popitem()
                                # files.append({'path': ad.get('full_name'), "name": ad.get('name'), 'uuid': uuid})
                                files.append({'path': ad.get('full_name'), "name": ad.get('name')})
                            if 'user' in status['order'] or 'organization' in status['order']:
                                self.smev.create_orders_request(status, files)
                            else:
                                self.smev.update_orders_request(status, files)
                            elk_num = self.smev.get_orders_response()
                            if elk_num and elk_num != '0':
                                res = self.directum.update_reference(
                                    "ДПУ", request.directum_id, [{'Name': 'LongString56', 'Type': 'String',
                                                                  'Value': "%s (3)" % elk_num}])
                                if res[0]:
                                    logging.warning(str(res) + " when " + str(status))
                                else:
                                    logging.info(
                                        "Отправлен конечный статус для дела Id=%s, num=%s %s. ELK = %s" %
                                        (request.directum_id, request.declar_num,
                                         declar[0].get('Наименование'), elk_num))
                    except:
                        self.report_error()
                    finally:
                        for ad in applied_docs:
                            try:
                                os.remove(ad.file)
                            except:
                                pass
        except:
            self.report_error()
            self.db.rollback()

        # Обновление ЕЛК.Статусы
        try:
            last_update = self.db.get_config_value('last_ELK_STATUS_update')
        except:
            last_update = None
        try:
            # Once a day
            if not last_update or date.fromisoformat(last_update) < date.today():
                cnsi = Cnsi(self.smev)
                res = cnsi.smev.get_response('CnsiRequest',
                                             'urn://x-artefacts-smev-gov-ru/esnsi/smev-integration/read/2.0.1', None)
                while res:
                    res = cnsi.smev.get_response('CnsiRequest',
                                                 'urn://x-artefacts-smev-gov-ru/esnsi/smev-integration/read/2.0.1',
                                                 None)
                revisions = cnsi.get_revision_list('ELK_STATUS')
                if revisions:
                    revisions, max_revision = revisions
                    res = cnsi.get_data('ELK_STATUS', max_revision)
                    try:
                        res = self.directum.update_elk_status(res)
                        logging.debug(res)
                        logging.info("Обновлён справочник ЕЛК.Статусы")
                    except:
                        pass
                    self.db.set_config_value('last_ELK_STATUS_update', date.today())
        except:
            logging.error('Error update ELK_STATUS', exc_info=True)

        # Send initial status to ELK
        try:
            if not last_update or date.fromisoformat(last_update) < date.today():
                days = 3 if date.today().weekday() == 0 else 1  # On monday take sunday and saturday into account
                xml = self.directum.search(
                    'ДПУ',
                    'СпособДост<>5652824 and СпособДост<>6953048 and СпособДост<>5652821 and Дата3>=%s and Дата3<%s'
                    ' and Дата5 is null and LongString56 is null' %
                    (date.today() - timedelta(days=days), date.today() + timedelta(days=1)), raw=True)
                recs = xml.findall('.//Object/Record')
                logging.info("************* Проверка начальных статусов для %s дел" % len(recs))
                for rec in recs:
                    declar_id = rec.findtext('.//Section[@Index="0"]/Requisite[@Name="ИД"]')
                    st_list = self.directum.get_declar_status_data(declar_id)
                    for status in st_list:
                        if 'user' in status['order'] or 'organization' in status['order']:
                            self.smev.create_orders_request(status)
                        else:
                            self.smev.update_orders_request(status)
                        elk_num = self.smev.get_orders_response()
                        if elk_num and elk_num != '0':
                            res = self.directum.update_reference(
                                "ДПУ", declar_id, [{'Name': 'LongString56', 'Type': 'String', 'Value': elk_num}])
                            if res[0]:
                                logging.warning(str(res) + " when " + str(status))
                            else:
                                logging.info(
                                    "Отправлен начальный статус для дела Id=%s, num=%s %s. ELK = %s" %
                                    (declar_id, rec.findtext('.//Section[@Index="0"]/Requisite[@Name="Дополнение3"]'),
                                     rec.findtext('.//Section[@Index="0"]/Requisite[@Name="Наименование"]'), elk_num))
        except:
            logging.error('Error send initial status to ELK', exc_info=True)

        # Send final status to ELK
        try:
            if not last_update or date.fromisoformat(last_update) < date.today():
                days = 3 if date.today().weekday() == 0 else 1
                xml = self.directum.search(
                    'ДПУ',
                    "СпособДост<>5652824 and СпособДост<>6953048 and СпособДост<>5652821 and Дата5>=%s and Дата5<%s" %
                    (date.today() - timedelta(days=days), date.today() + timedelta(days=1)), raw=True)
                recs = xml.findall('.//Object/Record')
                logging.info("************** Проверка конечных статусов для %s дел" % len(recs))
                for rec in recs:
                    elk_num = rec.findtext('.//Section[@Index="0"]/Requisite[@Name="LongString56"]')
                    if '(3)' in elk_num:
                        continue
                    declar_id = rec.findtext('.//Section[@Index="0"]/Requisite[@Name="ИД"]')
                    st_list = self.directum.get_declar_status_data(declar_id, permanent_status='3')
                    for status in st_list:
                        applied_docs = self.directum.get_result_docs(declar_id, self.crt_name, self.zip_signed_doc)
                        files = []
                        for ad in applied_docs:
                            files.append({'path': ad.file, 'name': ad.file_name})
                        if 'user' in status['order'] or 'organization' in status['order']:
                            self.smev.create_orders_request(status, files)
                        else:
                            self.smev.update_orders_request(status, files)
                        for item in files:
                            try:
                                os.remove(item.get('path'))
                            except:
                                pass
                        elk_num = self.smev.get_orders_response()
                        if elk_num and elk_num != '0':
                            res = self.directum.update_reference(
                                "ДПУ", declar_id,
                                [{'Name': 'LongString56', 'Type': 'String', 'Value': "%s (3)" % elk_num}])
                            if res[0]:
                                logging.warning(str(res) + " when " + str(status))
                            else:
                                logging.info(
                                    "Отправлен конечный статус для дела Id=%s, num=%s %s. ELK = %s" %
                                    (declar_id, rec.findtext('.//Section[@Index="0"]/Requisite[@Name="Дополнение3"]'),
                                     rec.findtext('.//Section[@Index="0"]/Requisite[@Name="Наименование"]'), elk_num))
        except:
            logging.error('Error send final status to ELK', exc_info=True)

        self.db.vacuum()

    def parse_config(self, config_path):
        """
        Read the configuration. If something is missing, write the default one.
        """
        from configparser import ConfigParser, NoSectionError, NoOptionError

        cfg = ConfigParser()
        do_write = False
        # If an exception, report it end exit
        try:
            from os.path import expanduser
            lst = cfg.read(
                ["c:/dmsis/dmsis.ini", expanduser("~/dmsis.ini"), "./dmsis.ini",
                 config_path])
            if lst:
                logging.info('Configuration loaded from: %s' % lst)
            else:
                logging.warning('No config files found. Using default')
                lst = [os.path.abspath("./dmsis.ini")]
                logging.info('Configuration stored in: %s' % lst)

            if not cfg.has_section("main"):
                do_write = True
                cfg.add_section("main")
                cfg.set("main", "logfile", "dmsis.log")
                cfg.set("main", "loglevel", "warning")
                cfg.set("main", "log_count", "7")
            if not cfg.has_option("main", "logfile"):
                do_write = True
                cfg.set("main", "logfile", "dmsis.log")
            from logging.handlers import TimedRotatingFileHandler
            backupcount = 7
            if "log_count" in cfg.options("main"):
                backupcount = int(cfg.get("main", "log_count"))
            else:
                do_write = True
                cfg.set("main", "log_count", "7")
            handler = TimedRotatingFileHandler(
                os.path.abspath(cfg.get("main", "logfile")), when='D',
                backupCount=backupcount, encoding='cp1251')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s %(name)s:%(module)s(%(lineno)d): %(levelname)s: '
                '%(message)s'))
            logging.root.addHandler(handler)
            if "loglevel" not in cfg.options("main"):
                do_write = True
                cfg.set("main", "loglevel", "warning")
            loglevel = cfg.get("main", "loglevel").upper()
            logging.info("Set logging level to '%s'", loglevel)
            logging.root.setLevel(loglevel)
            logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)
            if 'mail_addr' not in cfg.options('main'):
                do_write = True
                cfg.set('main', 'mail_addr', 'ioib@adm-ussuriisk.ru')
            self.mail_addr = cfg.get('main', 'mail_addr')
            # if 'mail_server' not in cfg.options('main'):
            #     do_write = True
            #     cfg.set('main', 'mail_server', '192.168.1.6')
            if 'mail_server' in cfg.options('main'):
                self.mail_server = cfg.get('main', 'mail_server')
            else:
                self.mail_server = None

            if not cfg.has_section("smev"):
                do_write = True
                cfg.add_section('smev')
                cfg.set(
                    'smev', 'wsdl',
                    "http://172.20.3.12:7500/smev/v1.2/ws?wsdl")
                cfg.set('smev', 'ftp', "ftp://172.20.3.12/")
            if 'uri' in cfg.options('smev'):
                self.smev_uri = cfg.get('smev', 'uri')
            else:
                self.smev_uri = 'urn://augo/smev/uslugi/1.0.0'
            if 'local_name' in cfg.options('smev'):
                self.local_name = cfg.get('smev', 'local_name')
            else:
                # self.local_name = 'directum'
                self.local_name = 'declar'
                # self.local_name = ''
            if 'wsdl' not in cfg.options('smev'):
                do_write = True
                cfg.set(
                    'smev', 'wsdl',
                    "http://172.20.3.12:7500/smev/v1.2/ws?wsdl")
            self.smev_wsdl = cfg.get('smev', 'wsdl')
            if 'ftp' not in cfg.options('smev'):
                do_write = True
                cfg.set('smev', 'ftp', "ftp://172.20.3.12/")
            self.smev_ftp = cfg.get('smev', 'ftp')
            if 'method' not in cfg.options('smev'):
                do_write = True
                cfg.set('smev', 'method', "sharp")
            self.cert_method = cfg.get('smev', 'method').lower()
            if 'crt_serial' in cfg.options('smev'):
                self.crt_serial = cfg.get('smev', 'crt_serial')
            else:
                raise Exception('Ошибка в настройках: необходимо указать '
                                'crt_serial в секции smev')
            if 'crt_name' in cfg.options('smev'):
                self.crt_name = cfg.get('smev', 'crt_name')
            else:
                raise Exception('Ошибка в настройках: необходимо указать '
                                'crt_name в секции smev')
            if 'container' in cfg.options('smev'):
                self.container = cfg.get('smev', 'container')
            else:
                raise Exception('Ошибка в настройках: необходимо указать '
                                'container в секции smev')
            if 'ftp_user' in cfg.options('smev'):
                self.ftp_user = cfg.get('smev', 'ftp_user')
            else:
                self.ftp_user = 'anonymous'
            if 'ftp_pass' in cfg.options('smev'):
                self.ftp_pass = cfg.get('smev', 'ftp_pass')
            else:
                self.ftp_pass = 'anonymous'
            if 'zip_signed_doc' not in cfg.options('smev'):
                do_write = True
                cfg.set('smev', 'zip_signed_doc', "False")
            self.zip_signed_doc = cfg.getboolean('smev', 'zip_signed_doc')

            if not cfg.has_section("directum"):
                do_write = True
                cfg.add_section('directum')
            if 'wsdl' not in cfg.options('directum'):
                do_write = True
                cfg.set(
                    'directum', 'wsdl',
                    "http://servdir1:8083/IntegrationService.svc?singleWsdl")
            self.directum_wsdl = cfg.get('directum', 'wsdl')

            if not cfg.has_section("integration"):
                do_write = True
                cfg.add_section('integration')
            if 'repeat_every' not in cfg.options('integration'):
                do_write = True
                cfg.set('integration', 'repeat_every', '10')
            self.repeat_every = cfg.getint('integration', 'repeat_every')
            if 'check_workdays' not in cfg.options('integration'):
                do_write = True
                cfg.set('integration', 'check_workdays', 'True')
            self.check_workdays = cfg.getboolean('integration', 'check_workdays')

            if do_write:
                for fn in lst:
                    with open(fn, "w") as configfile:
                        cfg.write(configfile)
                        configfile.close()
        except NoSectionError:
            self.report_error()
            quit()
        except NoOptionError:
            self.report_error()
        except Exception:
            if do_write:
                for fn in lst:
                    with open(fn, "w") as configfile:
                        cfg.write(configfile)
                        configfile.close()
            raise

    def report_error(self):
        from sys import exc_info
        from traceback import format_exception
        etype, value, tb = exc_info()
        trace = ''.join(format_exception(etype, value, tb))
        msg = ("%s" + "\n" + "*" * 70 + "\n%s\n" + "*" * 70) % (
            value, trace)
        logging.error(msg)

        if self.mail_server:
            import smtplib
            from email.mime.text import MIMEText
            from_addr = 'admin@adm-ussuriisk.ru'
            message = MIMEText(msg)
            message['Subject'] = 'SMEV integration error'
            message['From'] = from_addr
            message['To'] = self.mail_addr

            try:
                s = smtplib.SMTP(self.mail_server)
                s.sendmail(from_addr, [self.mail_addr], message.as_string())
                s.quit()
            except smtplib.SMTPException:
                etype, value, tb = exc_info()
                trace = ''.join(format_exception(etype, value, tb))
                msg = ("%s" + "\n" + "*" * 70 + "\n%s\n" + "*" * 70) % (
                    value, trace)
                logging.error(msg)


# class Service(ServiceFramework):
#     _svc_name_ = 'dmsis'
#     _svc_display_name_ = 'Directum SMEV integration system'

    def SvcStop(self):
        self.ReportServiceStatus(SERVICE_STOP_PENDING)
        log.msg('Stopping dmsis...')
        reactor.callFromThread(reactor.stop)

    def SvcDoRun(self):
        #
        # ... Initialize application here
        #
        log.msg('dmsis running...')
        run()


def run():
    a = Integration()
    a.run()
    reactor.run(installSignalHandlers=0)


def main():
    # Ensure basic thread support is enabled for twisted
    from twisted.python import threadable

    threadable.init(1)
    reactor.suggestThreadPoolSize(30)

    from optparse import OptionParser

    parser = OptionParser(version="%prog ver. 1.15",
                          conflict_handler="resolve")
    parser.print_version()
    parser.add_option("-r", "--run", action="store_true", dest="run",
                      help="Just run program. Don`t work as win32service.")
    parser.add_option("-o", "--once", action="store_true", dest="once",
                      help="Do the job and exit. Don`t use Twisted manager and "
                           "don`t run continuously.")
    # parser.add_option("--startup")
    (options, args) = parser.parse_args()
    if options.once and options.run:
        a = Integration()
        a.step()
    elif options.run:
        run()
    else:
        HandleCommandLine(Service)


if __name__ == '__main__':
    main()
