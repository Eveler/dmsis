# -*- encoding: utf-8 -*-

# Author: Savenko Mike

import pyximport
pyximport.install()
import hello
pyximport.uninstall(__import__, pyximport)
import hellop

if __name__ == '__main__':
    hello.say_hello("Cython")
    hellop.say_hello("Python")
