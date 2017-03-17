#!/bin/env python
# -*- coding: utf-8 -*-
from Tkinter import Tk
import tkFileDialog
# from pywin.dialogs.status import StatusProgressDialog
from ttk import Progressbar, Frame, Label, Button
from os import path
from os import walk
from shutil import copy2

__author__ = 'Savenko'


class Application(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.files_count = 0
        self.pack()
        self.in_dir = tkFileDialog.askdirectory(title=u'Выберите исходный каталог')
        if not self.in_dir:
            exit()
        self.out_dir = tkFileDialog.askdirectory(title=u'Выберите конечный каталог')
        if not self.out_dir:
            exit()
        self.label = Label(self)
        self.label.pack()
        self.progress = Progressbar(self, mode='indeterminate')
        self.do_count()
        self.progress.pack_forget()
        self.b_ok = Button(self, text=u'Да', command=self.do_copy)
        self.b_ok.pack(side='left')
        self.b_cancel = Button(self, text=u'Нет', command=self.quit)
        self.b_cancel.pack(side='right')

    def do_count(self):
        self.label['text'] = u'Сканирование исходной папки.\nЖдите...'
        self.progress.pack()
        self.update()
        self.progress.start()
        files_size = 0

        for root_dir, dirs, files in walk(self.in_dir):
            files_size += sum(path.getsize(path.join(root_dir, name)) for name in files)
            self.files_count += len(files)
            self.update()
        prefix = u''
        if files_size > 2 ** 30 - 2 ** 20:
            prefix = u'Г'
            files_size /= 2 ** 30
        elif files_size > 2 ** 20 - 2 ** 10:
            prefix = u'М'
            files_size /= 2 ** 20
        elif files_size > 2 ** 10:
            prefix = u'К'
            files_size /= 2 ** 10
        self.label[
            'text'] = u'Исходный каталог: %s\nКонечный каталог: %s\nКоличество файлов: %s.\nОбщий размер: %s %sбайт.\n\nКопировать?' % \
                      (self.in_dir, self.out_dir, self.files_count, files_size, prefix)
        self.progress.stop()

    def do_copy(self):
        self.b_cancel.pack_forget()
        self.b_ok.pack_forget()
        self.label['text'] = u''
        self.progress['mode'] = 'determinate'
        self.progress['maximum'] = self.files_count
        self.progress.pack()
        self.update()

        files_done = 0
        if self.files_count == 0:
            self.files_count = 1
        err_str = u''
        for root_dir, dirs, files in walk(self.in_dir):
            for name in files:
                file_name = path.join(root_dir, name)
                rel_path = path.relpath(root_dir, self.in_dir)
                out_dir = path.join(self.out_dir, rel_path)
                out_file = path.join(self.out_dir, rel_path, name)

                files_done += 1
                self.progress.step()
                self.label['text'] = u'Завершено %s%%' % (files_done * 100 / self.files_count)
                self.update()

                if path.exists(out_file):
                    continue
                if not path.exists(out_dir):
                    from os import makedirs

                    makedirs(out_dir)

                try:
                    copy2(file_name, out_file)
                except IOError:
                    print(file_name)
                    basename = path.basename(file_name)
                    nm, ext = path.splitext(basename)
                    idx = nm.rfind('(')
                    ver = nm[idx:]
                    is_err = True
                    while is_err:
                        idx -= 1
                        nm = nm[:idx]
                        out_file = path.join(self.out_dir, rel_path, nm + ' ' + ver + ext)
                        if path.exists(out_file):
                            break
                        is_err = False
                        try:
                            copy2(file_name, out_file)
                        except:
                            if len(nm) > 0:
                                is_err = True
                            else:
                                err_str += file_name + '\n'
                    print(out_file + '\n')

        self.label['text'] = u'Готово\nОшибки:\n%s' % (err_str if len(err_str) > 0 else u'Отсутствуют')
        self.progress.pack_forget()
        self.update()


if __name__ == "__main__":
    root = Tk()
    app = Application(master=root)

    app.mainloop()
