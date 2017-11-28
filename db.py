# -*- encoding: utf-8 -*-
import logging

from sqlalchemy import Column, Integer, String
from sqlalchemy.engine import create_engine
from sqlalchemy.ext.declarative.api import declarative_base
from sqlalchemy.orm.session import sessionmaker

Base = declarative_base()


class Requests(Base):
    __tablename__ = 'requests'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    uuid = Column(String, nullable=False, index=True)
    declar_num = Column(String, nullable=False, index=True)
    last_status = Column(String)


class Db:
    def __init__(self, dbstr='sqlite:///dmsis.db'):
        self.engine = create_engine(dbstr,
                                    echo=(logging.root.level == logging.DEBUG))
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

    def add(self, uuid, declar_num, status):
        r = Requests(uuid=uuid, declar_num=declar_num, status=status)
        self.session.add(r)
        self.session.commit()

    def all(self):
        return self.session.query(Requests).all()

    def change_status(self, status, uuid, declar_num):
        if not status:
            raise Exception('status необходимо указать')

        if uuid:
            r = self.session.query(Requests).filter_by(uuid=uuid).first()
            r.status = status
        elif declar_num:
            r = self.session.query(Requests).filter_by(
                declar_num=declar_num).first()
            r.status = status
        self.session.commit()

    def _clear(self):
        for req in self.all():
            self.session.delete(req)
        self.session.commit()
        self.session.execute('VACUUM FULL')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    db = Db()
    db.add('gdfgdsgdfg-fdgfsdf-dfgdfsg', '85473h59394')
    res = db.all()
    print('*' * 80)
    for r in res:
        print(r.id, '|', r.uuid, '|', r.declar_num)
    print('*' * 80)
    db._clear()
