# -*- coding: utf-8 -*-

import logging
from os import remove
from traceback import format_exception
from zipfile import ZIP_DEFLATED
from sys import exc_info

from img2pdf import convert
from twisted.internet import task

from mfc_integration.directum import IntegrationServices
from mfc_integration.mfc_db import Max
from mfc_integration.error import mail, report_error


__author__ = 'Savenko'

mail_errors = False
mail.addr = "<evelerwork@mail.ru>"


class Integration:
    def __init__(self):
        from tempfile import gettempdir

        self.tmppath = gettempdir()
        self.convert_to_pdf = False
        self.mfc_db = None
        self.parse_config()

        self.directum = None
        self.doc_ids = {}

    def run(self):
        lc = task.LoopingCall(self.integrate)
        lc.start(self.get_delay())

    # def _lookup_proc(self, procedure_name):
    # proc = getattr(self, "integration_%s" % procedure_name, '')
    # if proc == '':
    # raise Exception("Procedure %s not found" % procedure_name)
    # return proc

    def _exec_proc(self, proc_name, params):
        """
        Executes method of this class named integration_<proc_name> with parameters values from params,
         i.e. integration_<proc_name>(params[0], params[1],...)
        """
        try:
##            to_exec = "self.integration_%s(" % proc_name
##            to_exec += ",".join(params) + ")"
##            return eval(to_exec)
            method = getattr(self, "integration_" + proc_name)
            return method(*params)
        except Exception as e:
            logging.error("Cannot execute integration_%s:" % proc_name)
            logging.error("params:")
            logging.error(params)
            logging.error(e.message.encode(errors="replace"))
            try:
                etype, value, tb = exc_info()
                trace = ''.join(format_exception(etype, value, tb))
                msg = "\n" + "*" * 70 + "\n%s: %s\n%s\n" + "*" * 70
                logging.error(msg % (etype, value, trace))
            except:
                pass
            return False

    def get_delay(self):
        return self.delay

    def parse_config(self):
        """
        Read the configuration. If something is missing, write the default one.
        """
        from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError

        cfg = SafeConfigParser()
        # If an exception, report it end exit
        try:
            from os.path import expanduser

            lst = cfg.read(["./integration.ini", expanduser("~/integration.ini"), "c:/integration/integration.ini"])
            # if not lst:
            # raise Exception("Config file integration.ini not found.\n"
            # "You need to place it in the program directory "
            # "or in the program user directory or in C:\\\\")
            do_write = False

            from twisted.python import log

            observer = log.PythonLoggingObserver()
            observer.start()

            if cfg.has_section("main"):
                if cfg.has_option("main", "logfile"):
                    from logging.handlers import TimedRotatingFileHandler

                    backupcount = 7
                    if "log_count" in cfg.options("main"):
                        backupcount = cfg.get("main", "log_count")
                    else:
                        do_write = True
                        cfg.set("main", "log_count", "7")
                    handler = TimedRotatingFileHandler(cfg.get("main", "logfile"), when='D', backupCount=backupcount,
                                                       encoding='cp1251')
                    from logging import Formatter

                    handler.setFormatter(Formatter('%(asctime)s %(module)s(%(lineno)d): %(levelname)s: %(message)s'))
                    logging.root.addHandler(handler)
                    # abslist = [abspath(l) for l in lst]
                    # logging.info("config = %s" % abslist)
                    logging.info("config = %s" % lst)
                    logging.info('Temporary files stored in "%s"' % self.tmppath)
                else:
                    do_write = True
                    cfg.set("main", "logfile", "integration.log")
                if "loglevel" in cfg.options("main"):
                    logging.info("Set logging level to '%s'", cfg.get("main", "loglevel"))
                    logging.root.setLevel(cfg.get("main", "loglevel").upper())
                else:
                    do_write = True
                    cfg.set("main", "loglevel", "warning")
            else:
                logging.info("config = %s" % lst)
                do_write = True
                cfg.add_section("main")
                cfg.set("main", "logfile", "integration.log")
                cfg.set("main", "loglevel", "warning")
                cfg.set("main", "log_count", "7")

            if not cfg.has_section("db"):
                do_write = True
                cfg.add_section("db")
                cfg.set("db", "type", "postgresql")
                cfg.set("db", "host", "192.168.91.60")
                cfg.set("db", "user", "mike")
                cfg.set("db", "pass", "me2db4con")
                cfg.set("db", "db", "MFCs")
            if not cfg.has_section("integration"):
                do_write = True
                cfg.add_section("integration")
                cfg.set("integration", "repeat_every", "600")

            if do_write:
                with open("./integration.ini", "w") as configfile:
                    cfg.write(configfile)
                    configfile.close()
                cfg.read("./integration.ini")

            self.dbstr = cfg.get("db", "type") + "://"
            if self.dbstr == "://":
                raise Exception("Wrong or not set db.type in config file")
            if "user" in cfg.options("db"):
                self.dbstr += cfg.get("db", "user")
            if "pass" in cfg.options("db"):
                self.dbstr += ":" + cfg.get("db", "pass")
            if "host" in cfg.options("db"):
                if "user" in cfg.options("db"):
                    self.dbstr += "@"
                self.dbstr += cfg.get("db", "host")
            if "db" in cfg.options("db"):
                self.dbstr += "/" + cfg.get("db", "db")

            self.delay = cfg.getint("integration", "repeat_every")

            if cfg.has_option("integration", "convert_to_pdf"):
                self.convert_to_pdf = cfg.get("integration", "convert_to_pdf").upper() == "YES"

            self.config = cfg

        except NoSectionError as e:
            report_error(e, mail_errors)
            quit()
        except NoOptionError as e:
            report_error(e, mail_errors)
        except Exception as e:
            report_error(e, mail_errors)

    def integrate(self):
        """
        Realizes the integration process
        """
        logging.info("Integration started")
        try:
            self.directum = IntegrationServices(self.config)
            self.mfc_db = Max(self.dbstr)  # connect to MFC DB
            for operation in self.mfc_db.session.query(self.mfc_db.operations) \
                .filter(self.mfc_db.operations.c.is_done == False).order_by(self.mfc_db.operations.c.id).all():
                self.declar = self.mfc_db.session.query(self.mfc_db.declars) \
                    .filter(self.mfc_db.declars.c.id == operation.declars_id).first()
                params = ["declars_id=" + str(operation.declars_id)]
                for parameter in self.mfc_db.session.query(
                    self.mfc_db.parameters).filter(self.mfc_db.parameters.c.operations_id == operation.id).all():
##                    params.append(str(parameter.tablename) + '_id=' + str(parameter.obj_id))
                    params.append(str(parameter.obj_id))
                res = self._exec_proc(operation.operation, params)

                # If declar is archived set is_done = True
                if res or (self.declar.archived and not operation.operation == "set_delivery_result"):
                    stmt = self.mfc_db.operations.update().where(self.mfc_db.operations.c.id == operation.id).values(
                        is_done=True)
                    self.mfc_db.session.connection().execute(stmt)
                    self.mfc_db.session.commit()

            # Send notification about new docs
            if self.doc_ids:
                for dcl_id in self.doc_ids:
                    # params = [('Code', dcl_id), ('Doc_IDs', ';'.join(self.doc_ids[dcl_id]))]
                    params = [('ID', dcl_id), ('Doc_IDs', ';'.join(self.doc_ids[dcl_id]))]
                    self.directum.run_script('notification_add_docs', params)
                self.doc_ids = {}

            # self.mfc_db.session.rollback()
        except Exception as e:
            logging.error("Integration aborted: %s" % e.message)
            etype, value, tb = exc_info()
            trace = ''.join(format_exception(etype, value, tb))
            msg = "\n" + "*" * 70 + "\n%s: %s\n%s\n" + "*" * 70
            logging.error(msg % (etype, value, trace))
        else:
            logging.info("Integration done.")
            # For debug
            # reactor.callFromThread(reactor.stop)
        self.mfc_db = None
        self.directum = None

    def integration_add_doc(self, declars_id, documents_id):
        """
        Gets document requisites identified by documents_id from MFC DB, document body from ftp and
        stores it to reference record with code=declars_id of Directum
        """
        docs_qry = self.mfc_db.session.query(self.mfc_db.documents, self.mfc_db.doctypes) \
                .join(self.mfc_db.doctypes).filter(self.mfc_db.documents.c.id == documents_id)
        all = docs_qry.all()
        for doc in all:
            url = doc.url
            # Only documents with body on ftp
            if url:
                from mfc_integration.directum import DocumentRequisites

                requisites = DocumentRequisites()
                doc_name = doc.aname
                if doc.docname:
                    doc_name += u" '" + doc.docname + u"'"
                if doc.docseries:
                    doc_name += u" серия " + doc.docseries
                if doc.docnum:
                    doc_name += u" № " + doc.docnum
                    requisites.number = doc.docnum
                doc_name += u" от " + doc.docdate.strftime('%d.%m.%Y')
                doc_name = doc_name.replace('/', '_')
                doc_name = doc_name.replace('\\', '_')

                logging.info(u'Добавление документа "%s" для дела № = %s (documents.id = %s, directum_id = %s)' %
                             (doc_name, self.declar.declarnum, str(documents_id), self.declar.directum_id))

                requisites.name = doc_name
                requisites.date = doc.docdate
                if doc.aname.upper() == u"ЗАЯВЛЕНИЕ":
                    try:
                        # Для ФЛ и ЮЛ используются разные типы карточек и виды документов
                        if isinstance(declars_id, str) and '=' in declars_id:
                            declars_id = declars_id.split('=')[1]
                        client = self.mfc_db.session.query(self.mfc_db.declar_clients, self.mfc_db.clients) \
                            .join(self.mfc_db.clients).filter(self.mfc_db.declar_clients.c.declar_id == declars_id) \
                            .order_by(self.mfc_db.declar_clients.c.id).first()
                        if client.isorg == 0:  # human (ФЛ)
                            human = self.mfc_db.session.query(self.mfc_db.humans).filter(
                                self.mfc_db.humans.c.id == client.clid).first()
                            requisites.human_name = "%s %s %s" % (human.surname, human.firstname, human.lastname)
                        else:
                            org = self.mfc_db.session.query(self.mfc_db.orgs).filter(
                                self.mfc_db.orgs.c.id == client.clid).first()
                            params = [('Param', org.shortname if org.shortname else org.fullname),
                                      ('Param1', org.directum_id if org.directum_id else '')]
                            logging.info(u' >>  Поиск организации (Param = %s, Param1 = %s)' %
                                         (org.shortname if org.shortname else org.fullname,
                                          org.directum_id if org.directum_id else ''))
                            try:
                                res = self.directum.run_script('SearchORG', params)
                                if res and res != '0':
                                    requisites.org_directum_id = res
                                    # FIXME: else: Add org to Directum
                            except Exception as e:
                                logging.error(e.message)
                    except Exception as e:
                        logging.error(e.message)
                    if not requisites.number:
                        requisites.number = u'б/н'

                from ftplib import FTP

                ftp = FTP(host='192.168.91.60', user='mike', passwd='me2db4con')
                doc_in = self.tmppath + "/doc_in.zip"
                try:
                    ftp.retrbinary("RETR %s" % url, open(doc_in, "wb").write)
                except Exception as e:
                    logging.error("FTP transfer error: %s" % url)
                    msg = e.message.decode('utf-8', errors="replace")
                    logging.error(msg)
                    if u'Нет такого файла или каталога' in msg:
                        return True
                    else:
                        return False
                finally:
                    ftp.close()

                doc_files = []
                if self.convert_to_pdf:
                    # images from archive convert to one pdf file, other files, except 'requisites.ini'
                    # compress to new archive
                    from zipfile import ZipFile

                    arc = ZipFile(doc_in)
                    arc.extractall()
                    images = []
                    for file_name in arc.namelist():
                        if ".JPG" in file_name.upper():
                            images.append(open(file_name, "rb"))
                    if images:
                        pdf_file = self.tmppath + "/doc.pdf"
                        open(pdf_file, "wb").write(convert(images, 0, 0, 0))
                        doc_files.append(pdf_file)

                    to_zip = []
                    for file_name in arc.namelist():
                        if (not ".JPG" in file_name.upper()) and (not file_name == "requisites.ini"):
                            to_zip.append(file_name)
                    if to_zip:
                        doc_file = self.tmppath + "/doc.zip"
                        arc1 = ZipFile(doc_file, "w", ZIP_DEFLATED)
                        for f_n in to_zip:
                            arc1.write(f_n)
                        arc1.close()
                        doc_files.append(doc_file)

                    for file_name in arc.namelist():
                        try:
                            remove(file_name)
                        except:
                            pass
                    arc.close()
                    remove(doc_in)
                else:
                    doc_files.append(doc_in)

                doc_ids = []
                for doc_file in doc_files:
                    fp = open(doc_file, "rb")
                    from os import SEEK_END, SEEK_SET

                    fp.seek(0, SEEK_END)
                    size = fp.tell()
                    fp.seek(0, SEEK_SET)
                    data = fp.read(size)
                    fp.close()
                    logging.info(u' >>  Передача в Directum')
                    try:
                        directum_id = self.declar.directum_id
                        # Проверим, существует ли дело в директум
                        params = [('Param', self.declar.id)]
                        res = self.directum.run_script('GetCaseIdByCode', params)
                        if not res or res == 0 or res == "0":
                            logging.info(u'Дело № %s отсутствует в директум' % self.declar.declarnum)
                            remove(doc_file)
                            return False
                        elif res != directum_id:
                            directum_id = res
                        
                        res = self.directum.add_doc(requisites, 'PDF' if '.PDF' in doc_file.upper() else 'ZIP', data)
                        doc_ids.append(str(res))
                        # bind document with declar
                        # params = [('Code', declars_id),
                        #           ('DocID', res)]
                        params = [('ID', directum_id),
                                  ('DocID', res)]
                        logging.info(u' >>  Привязка к делу (ID = %s, DocID = %s)' %
                                     (directum_id, res))
                        try:
                            self.directum.run_script('BindEDocDPbyID', params)
                            logging.info(u'Добавлен документ "%s" для дела № = %s (directum ИД = %s)' %
                                         (doc_name, self.declar.declarnum, res))
                        except Exception as e:
                            logging.error(e.message)
                            if 'Declar not found' in e.message:
                                pass
                            else:
                                remove(doc_file)
                                return False

                    except Exception as e:
                        logging.error(e.message)
                    remove(doc_file)

                if declars_id in self.doc_ids:
                    for doc_id in doc_ids:
                        # self.doc_ids[declars_id].append(doc_id)
                        self.doc_ids[self.declar.directum_id].append(doc_id)
                else:
                    # self.doc_ids[declars_id] = []
                    self.doc_ids[self.declar.directum_id] = []
                    for doc_id in doc_ids:
                        # self.doc_ids[declars_id].append(doc_id)
                        self.doc_ids[self.declar.directum_id].append(doc_id)

                # params = [('Code', declars_id),
                #           ('Doc_IDs', ';'.join(doc_ids))]
                # self.directum.run_script('notification_add_docs', params)
                return True

    def integration_set_delivery_result(self, declars_id, assessment_types_id):
        # assessment_types:
        # 1;"оценка заявителя"
        # 2;"отказ от оценки"
        # 3;"не востребованный результат"
        # результат выполнения
        # 1; В; Документ выдан заявителю; Документ выдан заявителю
        # 2; Н; Заявитель не явился; Заявитель не явился в течении 30 дней
        result_code = u'Заявитель не явился' if assessment_types_id == 3 else u'Документ выдан заявителю'

        logging.info(u'Установка результата выдачи для дела № = %s (result_code = %s, declars_id = %s, '
                     u'directum_id = %s)' %
                     (self.declar.declarnum, result_code, declars_id, self.declar.directum_id))

        # params = [('Code', self.declar.directum_id),
        #           ('Result_code', result_code)]
        params = [('ID', self.declar.directum_id),
                  ('Result_code', result_code)]
        try:
            res = self.directum.run_script('set_delivery_result', params)
        except Exception as e:
            res = e.message.encode(errors='replace')
            if "not found" in str(res):
                logging.info(
                    u'Дело № = %s в архиве. Отмена установки результата (result_code = %s)' %
                    (self.declar.declarnum, result_code))
                return True
            if self.declar.archived:
                logging.info(u'Дело № = %s в архиве. Отмена установки результата (result_code = %s)' %
                             (self.declar.declarnum, result_code))
                return True
            else:
                raise

        if str(res) == "True":
            logging.info(u'Результат выдачи для дела № = %s установлен (result_code = %s)' %
                         (self.declar.declarnum, result_code))
        elif self.declar.archived:
            logging.info(u'Дело № = %s в архиве. Отмена установки результата (result_code = %s)' %
                            (self.declar.declarnum, result_code))
            return True
        else:
            logging.info(u'Установка результата выдачи отложена для дела № = %s (result_code = %s): причина: %s' %
                         (self.declar.declarnum, result_code, res))
        return res == "True"

    def integration_set_cancellation(self, declars_id):
        logging.info(u'Аннулирование дела № %s' % self.declar.declarnum)

        try:
            docpaths = self.mfc_db.session.query(self.mfc_db.docpaths).filter(self.mfc_db.docpaths.c.declarid == declars_id.split('=')[1]) \
                .filter(self.mfc_db.docpaths.c.procname == 2145121329).first()
        except Exception as e:
            logging.error(e.message.decode('utf-8', errors='replace'))
            docpaths = None

        if not docpaths:
            logging.info(u'Аннулирование дела № %s отменено' % self.declar.declarnum)
            return True

        # params = [('Code', declars_id),
        #           ('Doc_date', docpaths.startdate.strftime('%d.%m.%Y'))]
        params = [('ID', self.declar.directum_id),
                  ('Doc_date', docpaths.startdate.strftime('%d.%m.%Y'))]
        try:
            self.directum.run_script('set_cancellation', params)
            logging.info(u'Дело № %s аннулировано' % self.declar.declarnum)
        except Exception as e:
            logging.error(e.message.decode(errors='replace'))
        return True

    def integration_add_declar(self, declars_id):
        pass
