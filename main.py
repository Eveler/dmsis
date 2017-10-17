# -*- encoding: utf-8 -*-

# Author: Savenko Mike

# from ladon.compat import PORTABLE_STRING
# from ladon.ladonizer import ladonize
# from ladon.types.ladontype import LadonType

# import pyximport
# pyximport.install()
# import hello
# pyximport.uninstall(__import__, pyximport)
# import hellop


# class Declar(LadonType):
#     number = PORTABLE_STRING
#
#
# class SoapService:
#     @ladonize(Declar, rtype=PORTABLE_STRING)
#     def SendDeclar(self, declar):
#         pass


# class Calculator(object):
#     """
#     This service does the math, and serves as example for new potential Ladon
#     users.
#     """
#
#     @ladonize(int, int, rtype=int)
#     def add(self, a, b):
#         """
#         Add two integers together and return the result
#
#         @param a: 1st integer
#         @param b: 2nd integer
#         @rtype: The result of the addition
#         """
#         return a + b


if __name__ == '__main__':
    #     # hello.say_hello("Cython")
    #     hellop.say_hello("Python")
    from soapfish import xsd


    class Airport(xsd.ComplexType):
        type = xsd.Element(xsd.String)
        code = xsd.Element(xsd.String)


    airport = Airport()
    airport.type = 'IATA'
    airport.code = 'WAW'

    print(airport.xml('takeoff_airport', pretty_print=True))

    from soapfish.xsd2py import generate_code_from_xsd
    open('declar.py', 'wb').write(generate_code_from_xsd(open('declar-1.0.0.xsd', 'rb').read()))
    pass
