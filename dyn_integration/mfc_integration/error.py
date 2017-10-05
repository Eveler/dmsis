# -*- coding: utf-8 -*-
import logging

__author__ = 'Савенко_МЮ'


class Mail:
    pass


mail = Mail()
mail.addr = "<ioib@adm-ussuriisk.ru>"
mail.subject = 'Directrum & "MAX" integration error'
mail.smtp = '192.168.2.2'
# mail.smtp = 'smtp.mail.ru'


def report_error(e, by_mail=True):
    isinstance(e, Exception)
    logging.critical(u"Ошибка при интеграции Directrum и АИС МФЦ \"МАКС\"!\n%s" % e.message)

    if by_mail:
        from email.mime.text import MIMEText

        msg = MIMEText(u"Ошибка при интеграции Directrum и АИС МФЦ \"МАКС\"!\n%s" % e.message,
                       _charset="utf-8")
        msg['Subject'] = mail.subject
        msg['From'] = "servdir1 <ioib@adm-ussuriisk.ru>"
        msg['To'] = mail.addr

        from smtplib import SMTP

        s = SMTP(mail.smtp)
        s.sendmail(msg['From'], mail.addr, msg.as_string())

    quit()
