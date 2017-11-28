# -*- encoding: utf-8 -*-

# Twisted reactor sends GetRequest by timer
# Got requests stored in DB

# Then it queries Directum for changed status for stored requests and sends
# SendResponse if status changed
import logging
from sys import exc_info
from traceback import format_exception

from smev import Adapter


class Integration:
    def __init__(self, use_config=True, config_path='./dmsis.ini'):
        if use_config:
            self.parse_config(config_path)
        self.smev = Adapter()

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
                '%(asctime)s %(module)s(%(lineno)d): %(levelname)s: '
                '%(message)s'))
            logging.root.addHandler(handler)
            logging.info("config(s) = %s" % lst)

            if "loglevel" not in cfg.options("main"):
                do_write = True
                cfg.set("main", "loglevel", "warning")

            loglevel = cfg.get("main", "loglevel").upper()
            logging.info("Set logging level to '%s'", loglevel)
            logging.root.setLevel(loglevel)

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
        logging.error(e.message)
        etype, value, tb = exc_info()
        trace = ''.join(format_exception(etype, value, tb))
        msg = "\n" + "*" * 70 + "\n%s: %s\n%s\n" + "*" * 70
        logging.error(msg % (etype, value, trace))
