# -*- encoding: utf-8 -*-
import logging
from datetime import date

from sqlalchemy import Column, Integer, String, Boolean, Date
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm.session import sessionmaker

Base = declarative_base()


class Requests(Base):
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    uuid = Column(String, nullable=False, index=True)
    declar_num = Column(String, nullable=False, index=True)
    declar_date = Column(Date)
    directum_id = Column(Integer)
    reply_to = Column(String)
    last_status = Column(String)
    done = Column(Boolean, index=True)


class Db:
    def __init__(self, dbstr='sqlite:///dmsis.db'):
        self.engine = create_engine(dbstr,
                                    echo=(logging.root.level == logging.DEBUG))
        Base.metadata.create_all(self.engine, checkfirst=True)
        self.session = sessionmaker(bind=self.engine)()

    def add_update(self, uuid, declar_num, reply_to, status=None,
                   declar_date=None, directum_id=None):
        r = self.session.query(Requests).filter(Requests.uuid == uuid).first()
        if r:
            r.declar_num = declar_num
            r.reply_to = reply_to
            if status:
                r.last_status = status
            if declar_date:
                r.declar_date = declar_date
            if directum_id:
                r.directum_id = directum_id
        else:
            r = Requests(uuid=uuid, declar_num=declar_num, reply_to=reply_to,
                         last_status=status,
                         declar_date=declar_date if declar_date else date.today(),
                         directum_id=directum_id)
            self.session.add(r)
        self.session.commit()

    def all(self):
        return self.session.query(Requests).all()

    def all_not_done(self):
        return self.session.query(Requests).filter(Requests.done != True).all()

    def change_status(self, status, uuid, declar_num):
        if not status:
            raise Exception('status необходимо указать')
        if not uuid:
            raise Exception('uuid необходимо указать')

        if uuid:
            r = self.session.query(Requests).filter_by(uuid=uuid).first()
            r.last_status = status
        elif declar_num:
            r = self.session.query(Requests).filter_by(
                declar_num=declar_num).first()
            r.last_status = status
        self.session.commit()

    def delete(self, uuid):
        if not uuid:
            raise Exception('Необходимо указать UUID запроса')

        r = self.session.query(Requests).filter_by(uuid=uuid).first()
        self.session.delete(r)
        self.session.commit()

    def commit(self):
        self.session.commit()

    def _clear(self):
        for req in self.all():
            self.session.delete(req)
        self.session.commit()
        self.session.execute('VACUUM FULL')

    def __del__(self):
        self.session.execute('VACUUM FULL')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    db = Db()
    db.add_update('gdfgdsgdfg-fdgfsdf-dfgdfsg', '85473h59394',
                  'gdfgdsgdfg-fdgfsdf-dfgdfsg')
    res = db.all()
    print('*' * 80)
    for r in res:
        print(r.id, '|', r.uuid, '|', r.declar_num)
    print('*' * 80)
    db._clear()
