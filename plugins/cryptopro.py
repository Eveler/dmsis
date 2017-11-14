# -*- encoding: utf-8 -*-

from sys import platform
import pythoncom
from win32com.client import Dispatch

if 'win32' not in platform:
    raise Exception('This is for Windows only')


class Crypto:
    CAPICOM_CURRENT_USER_STORE = 2
    CAPICOM_CERTIFICATE_INCLUDE_WHOLE_CHAIN = 1


if __name__ == '__main__':
    pythoncom.CoInitialize()
    # oSigner = CreateObject('CAdESCOM.About')
    # o = Dispatch('CAPICOM.Algorithm')
    o = Dispatch('CAdESCOM.About')
    # o = Dispatch('Excel.Application')
    print(o)
