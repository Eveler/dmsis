# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.platypus.doctemplate import SimpleDocTemplate, Image

__author__ = 'Savenko'


def to_pdf(pdf_name, img_file_names):
    doc = SimpleDocTemplate(pdf_name, pagesize=A4)
    parts = []
    for file_name in img_file_names:
        parts.append(Image(file_name))
    doc.build(parts)
