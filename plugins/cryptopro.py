# -*- encoding: utf-8 -*-

# Author: Savenko Mike
from sys import platform

from comtypes.client import CreateObject

if 'win32' not in platform:
    raise Exception('This is for Windows only')


class Crypto:
    CAPICOM_CURRENT_USER_STORE = 2
    CAPICOM_CERTIFICATE_INCLUDE_WHOLE_CHAIN = 1


if __name__ == '__main__':
    oSigner = CreateObject('CAdESCOM.About')
