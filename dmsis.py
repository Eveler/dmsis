# -*- encoding: utf-8 -*-

# Twisted reactor sends GetRequest by timer
# Got requests stored in DB

# Then it queries Directum for changed status for stored requests and sends
# SendResponse if status changed
import logging
import os
from tempfile import mkstemp

from win32._service import SERVICE_STOP_PENDING
from win32serviceutil import ServiceFramework, HandleCommandLine

from db import Db
from plugins.directum import IntegrationServices
from smev import Adapter
from twisted.internet import task, reactor
from twisted.python import log


class Integration:
    def __init__(self, use_config=True, config_path='./dmsis.ini'):
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
            self.mail_server, self.ftp_user, self.ftp_pass = None, None, None

        try:
            self.__smev = Adapter(self.smev_wsdl, self.smev_ftp,
                                  method=self.cert_method)
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
            try:
                self.__smev = Adapter(self.smev_wsdl, self.smev_ftp,
                                      method=self.cert_method)
            except Exception:
                self.report_error()

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
        try:
            for declar, files, reply_to, uuid in self.db.all_declars_as_xsd():
                res = self.directum.add_declar(declar, files=files)
                self.db.add_update(uuid, declar.declar_number,
                                   reply_to, directum_id=res)
                logging.info('Добавлено/обновлено дело с ID = %s' % res)
                self.directum.run_script('СтартЗадачПоМУ')
                self.db.delete_declar(uuid)
        except Exception:
            self.report_error()

        try:
            declar, uuid, reply_to, files = self.smev.get_request(
                self.smev_uri,
                self.local_name)
            if declar:
                try:
                    res = self.directum.add_declar(declar, files=files)
                    self.db.add_update(uuid, declar.declar_number, reply_to,
                                       directum_id=res)
                    logging.info('Добавлено/обновлено дело с ID = %s' % res)
                    self.directum.run_script('СтартЗадачПоМУ')
                except Exception:
                    logging.warning(
                        'Failed to send data to DIRECTUM. Saving locally.',
                        exc_info=True)
                    self.db.save_declar(declar, uuid, reply_to, files)
        except Exception as e:
            self.report_error()

        # Send final response
        try:
            for request in self.db.all_not_done():
                declar = self.directum.search('ДПУ',
                                              'ИД=%s' % request.directum_id)

                # For all requests check if declar`s end date is set
                if declar[0].get('Дата5'):
                    # Stub class for document info
                    class Ad(object):
                        pass

                    applied_docs = []
                    found = False

                    # Search newest procedure with document bound
                    # for that declar
                    procs = self.directum.search(
                        'ПРОУ', 'Kod2=%s' % request.declar_number,
                        order_by='Дата4', ascending=False)
                    for proc in procs:
                        if proc.get(
                                'Ведущая аналитика') == request.directum_id:
                            docs = self.directum.get_bind_docs(
                                'ПРОУ', proc.get('ИДЗапГлавРазд'))
                            for doc in docs:
                                doc_id = doc.get('ID')
                                ad = Ad()
                                # Get only last version
                                versions = self.directum.get_doc_versions(
                                    doc_id)
                                data = self.directum.get_doc(
                                    doc_id, versions[0])
                                file, file_n = mkstemp()
                                os.write(file, data)
                                os.close(file)
                                ad.file = file_n
                                ad.date = doc.get('ISBEDocCreateDate')
                                ad.file_name = doc.get(
                                    'ID') + '.' + doc.get(
                                    'Extension').lower()
                                ad.number = doc.get(
                                    'Дополнение') if doc.get(
                                    'Дополнение') else doc.get('NumberEDoc')
                                ad.title = doc.get('ISBEDocName')
                                applied_docs.append(ad)
                            if docs:
                                found = True
                                break

                    # Get bound docs from declar if there is no procedures
                    # with docs bound
                    if not found:
                        docs = self.directum.get_bind_docs(
                            'ДПУ', request.directum_id)
                        ad = Ad()
                        for doc in docs:
                            if doc.get('TKED') in (
                                    'КИК', 'ИК1', 'ИК2', 'ПСИ'):
                                if ad.date > doc.get('ISBEDocCreateDate'):
                                    doc_id = doc.get('ID')
                                    if ad.file:
                                        os.remove(ad.file)
                                    file, file_n = mkstemp()
                                    ad.file = file_n
                                    ad.date = doc.get('ISBEDocCreateDate')
                                    ad.file_name = doc.get(
                                        'ID') + '.' + doc.get(
                                        'Extension').lower()
                                    ad.number = doc.get(
                                        'Дополнение') if doc.get(
                                        'Дополнение') else doc.get(
                                        'NumberEDoc')
                                    ad.title = doc.get('ISBEDocName')
                        # Get only last version
                        versions = self.directum.get_doc_versions(
                            doc_id)
                        data = self.directum.get_doc(
                            doc_id, versions[0])
                        os.write(ad.file, data)
                        os.close(ad.file)
                        applied_docs.append(ad)

                    text = 'Услуга предоставлена'
                    if declar[0].get('СтатусУслуги'):
                        state = self.directum.search(
                            'СОУ', 'Kod=%s' % declar[0].get('СтатусУслуги'))
                        if state[0].get('Наименование'):
                            text += '. Статус: %s' % \
                                    state[0].get('Наименование')

                    self.smev.send_respose(
                        request.reply_to, request.declar_num,
                        request.declar_date, text=text,
                        applied_documents=applied_docs,
                        ftp_user=self.ftp_user,
                        ftp_pass=self.ftp_pass)
                    # self.db.delete(request.uuid)
                    request.done = True
                    self.db.commit()
        except Exception as e:
            self.report_error()

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
                backupcount = cfg.get("main", "log_count")
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
            if 'mail_addr' not in cfg.options('main'):
                do_write = True
                cfg.set('main', 'mail_addr', 'ioib@adm-ussuriisk.ru')
            self.mail_addr = cfg.get('main', 'mail_addr')
            if 'mail_server' not in cfg.options('main'):
                do_write = True
                cfg.set('main', 'mail_server', '192.168.1.6')
            self.mail_server = cfg.get('main', 'mail_server')

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
                self.local_name = 'directum'
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
            if 'container' in cfg.options('smev'):
                self.container = cfg.get('smev', 'container')
            else:
                raise Exception('Ошибка в настройках: необходимо указать '
                                'container в секции smev')
            if 'ftp_user' in cfg.options('smev'):
                self.ftp_user = cfg.get('smev', 'ftp_user')
            else:
                self.ftp_user = None
            if 'ftp_pass' in cfg.options('smev'):
                self.ftp_pass = cfg.get('smev', 'ftp_pass')
            else:
                self.ftp_pass = None

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


class Service(ServiceFramework):
    _svc_name_ = 'dmsis'
    _svc_display_name_ = 'Directum SMEV integration system'

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

    from optparse import OptionParser

    parser = OptionParser(version="%prog ver. 1.0",
                          conflict_handler="resolve")
    parser.print_version()
    parser.add_option("-r", "--run", action="store_true", dest="run",
                      help="Just run program. Don`t work as win32service")
    # parser.add_option("--startup")
    (options, args) = parser.parse_args()
    if options.run:
        run()
    else:
        HandleCommandLine(Service)


if __name__ == '__main__':
    main()
