# -*- encoding: utf-8 -*-

# Twisted reactor sends GetRequest by timer
# Got requests stored in DB

# Then it queries Directum for changed status for stored requests and sends
# SendResponse if status changed
import logging

from db import Db
from plugins.directum import IntegrationServices
from smev import Adapter


class Integration:
    def __init__(self, use_config=True, config_path='./dmsis.ini'):
        logging.basicConfig(
            format='%(asctime)s %(name)s:%(module)s(%(lineno)d): '
                   '%(levelname)s: %(message)s')
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
            self.mail_server = None

        self.smev = Adapter(self.smev_wsdl, self.smev_ftp,
                            method=self.cert_method)
        self.directum = IntegrationServices(self.directum_wsdl)
        self.db = Db()

    def step(self):
        """
        Sends GetRequest. Then queries Directum for changed status for stored
        requests and sends SendResponse if status changed
        """
        try:
            declar, uuid, reply_to = self.smev.get_request(self.smev_uri,
                                                           self.local_name)
            if declar:
                res = self.directum.add_declar(declar)
                self.db.add_update(uuid, declar.declar_number, reply_to)
                logging.info('Добавлено/обновлено дело с ID = %s' % res)
                self.directum.run_script('СтартЗадачПоМУ')
        except Exception as e:
            self.report_error(e)

    def parse_config(self, config_path):
        """
        Read the configuration. If something is missing, write the default one.
        """
        from configparser import ConfigParser, NoSectionError, NoOptionError

        cfg = ConfigParser()
        # If an exception, report it end exit
        try:
            from os.path import expanduser
            lst = cfg.read(
                [config_path, "./dmsis.ini", expanduser("~/dmsis.ini"),
                 "c:/dmsis/dmsis.ini"])
            do_write = False
            if not cfg.has_section("main"):
                logging.info("config = %s" % lst)
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
                cfg.get("main", "logfile"), when='D',
                backupCount=backupcount, encoding='cp1251')
            handler.setFormatter(logging.Formatter(
                '%(asctime)s %(name)s:%(module)s(%(lineno)d): %(levelname)s: '
                '%(message)s'))
            logging.root.addHandler(handler)
            logging.info("config(s) = %s" % lst)
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
                cfg.set(
                    'smev', 'wsdl', "http://172.20.3.12:7500/smev/v1.2/ws?wsdl")
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
                cfg.set(
                    'smev', 'wsdl', "http://172.20.3.12:7500/smev/v1.2/ws?wsdl")
            self.smev_wsdl = cfg.get('smev', 'wsdl')
            if 'ftp' not in cfg.options('smev'):
                cfg.set('smev', 'ftp', "ftp://172.20.3.12/")
            self.smev_ftp = cfg.get('smev', 'ftp')
            if 'method' not in cfg.options('smev'):
                cfg.set('smev', 'method', "sharp")
            self.cert_method = cfg.get('smev', 'method').lower()
            if 'crt_serial' in cfg.options('smev'):
                self.crt_serial = cfg.get('smev', 'crt_serial')
            if self.cert_method in ('sharp', 'com') and not hasattr(
                    self, 'crt_serial'):
                raise Exception('Ошибка в настройках: если method = sharp или '
                                'com, необходимо указать crt_serial')
            if 'container' in cfg.options('smev'):
                self.container = cfg.get('smev', 'container')
            if self.cert_method == 'csp' and not hasattr(self, 'container'):
                raise Exception('Ошибка в настройках: если method = csp, '
                                'необходимо указать container')

            if not cfg.has_section("directum"):
                cfg.set(
                    'directum', 'wsdl',
                    "http://servdir1:8083/IntegrationService.svc?singleWsdl")
            self.directum_wsdl = cfg.get('directum', 'wsdl')

            if not cfg.has_section("service"):
                do_write = True
                cfg.set('service', 'repeat_every', 300)
            self.repeat_every = cfg.getint('service', 'repeat_every')

            if do_write:
                for fn in lst:
                    with open(fn, "w") as configfile:
                        cfg.write(configfile)
                        configfile.close()
        except NoSectionError as e:
            self.report_error(e)
            quit()
        except NoOptionError as e:
            self.report_error(e)
        except Exception as e:
            self.report_error(e)

    def report_error(self, e):
        from sys import exc_info
        from traceback import format_exception
        etype, value, tb = exc_info()
        trace = ''.join(format_exception(etype, value, tb))
        msg = ("%s" + "\n" + "*" * 70 + "\n%s\n" + "*" * 70) % (value, trace)
        logging.error(msg)

        if self.mail_server:
            import smtplib
            from email.mime.text import MIMEText
            from_addr = 'admin@adm-ussuriisk.ru'
            message = MIMEText(msg)
            message['Subject'] = 'SMEV service error'
            message['From'] = from_addr
            message['To'] = self.mail_addr

            s = smtplib.SMTP(self.mail_server)
            s.sendmail(from_addr, [self.mail_addr], message.as_string())
            s.quit()


if __name__ == '__main__':
    logging.root.setLevel(logging.DEBUG)
    logging.getLogger('zeep.xsd').setLevel(logging.INFO)
    logging.getLogger('zeep.wsdl').setLevel(logging.INFO)
    i = Integration(False)
    i.step()
