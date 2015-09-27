import os
import unittest

from config import basedir
from application import application, db
from views import *


class TestCase(unittest.TestCase):
    def setUp(self):
        application.config['TESTING'] = True
        application.config['WTF_CSRF_ENABLED'] = False
        application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'test.db')
        self.app = application.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_intro(self):
        resp = self.app.get("/intro")
        assert resp._status_code is 200, resp._status_code


if __name__ == '__main__':
    unittest.main()
