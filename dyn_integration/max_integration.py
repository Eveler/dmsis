#!/bin/env python
# -*- coding: utf-8 -*-
"""
Зависимости:
    SQLAlchemy
    twisted
    img2pdf
    suds
Вспомогательный код:
    Триггерная функция directum_integration.directum_integrate() в БД МФЦ
    Сценарии Directum:
        SearchORG
        BindEDocDP
        notification_add_docs
        set_delivery_result
        set_cancellation
        CheckDuplicateByCode
"""
__author__ = 'Савенко_МЮ'

import win32service

import win32serviceutil
from twisted.internet import reactor
from twisted.python import log

# Ensure basic thread support is enabled for twisted
from twisted.python import threadable

threadable.init(1)


def run():
    from mfc_integration import process

    process.setup()
    reactor.run(installSignalHandlers=0)


class Service(win32serviceutil.ServiceFramework):
    _svc_name_ = 'max_integration'
    _svc_display_name_ = 'Integration Directum and AIS MFC MAX'

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        log.msg('Stopping max_integration...')
        reactor.callFromThread(reactor.stop)

    def SvcDoRun(self):
        #
        # ... Initialize application here
        #

        log.msg('max_integration running...')
        run()


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser(version="%prog ver. 0.1", conflict_handler="resolve")
    parser.print_version()
    parser.add_option("-r", "--run", action="store_true", dest="run",
                      help="Just run program. Don`t work with win32service")
    parser.add_option("--startup")
    (options, args) = parser.parse_args()
    if options.run:
        run()
    else:
        win32serviceutil.HandleCommandLine(Service)
