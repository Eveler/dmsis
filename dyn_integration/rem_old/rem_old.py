#!/bin/env python
# -*- coding: utf-8 -*-

import datetime
import os
import rem_old_config as config

if __name__ == '__main__':
    directory = config.directory
    print(directory)
    print(config.max_time, 'days')
    td = datetime.timedelta(days=config.max_time)
#    for root_dir, dirs, files in os.walk(config.directory):
#        print('root_dir =', root_dir)
#        print('dirs =', dirs)
#        for name in files:
#            print(name)
#            print(os.path.abspath(name))
#            print(os.stat(os.path.abspath(name)).st_atime)
    join = os.path.join
    fromtimestamp = datetime.date.fromtimestamp
    today = datetime.date.today()
    stat = os.stat
    
    for name in os.listdir(directory):
        path = join(directory, name)
        filedate = fromtimestamp(stat(path).st_atime)
        if filedate + td < today:
            print(path)
            print(stat(path).st_atime, '-', filedate)
            if os.path.isfile(path):
                print('to remove')