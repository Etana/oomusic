# -*- coding: utf-8 -*-

import binascii
import os

from lxml import etree

from odoo.http import request

API_VERSION = '1.12.0'
API_VERSION_LIST = {
    '1.14.0': 15,
    '1.13.0': 14,
    '1.12.0': 13,
    '1.11.0': 12,
    '1.10.2': 11,
    '1.9.0': 10,
    '1.8.0': 9,
    '1.7.0': 8,
    '1.6.0': 7,
    '1.5.0': 6,
    '1.4.0': 5,
    '1.3.0': 4,
    '1.2.0': 3,
    '1.1.1': 2,
    '1.1.0': 1,
}
API_ERROR_LIST = {
    '0': 'A generic error.',
    '10': 'Required parameter is missing.',
    '20': 'Incompatible Subsonic REST protocol version. Client must upgrade.',
    '30': 'Incompatible Subsonic REST protocol version. Server must upgrade.',
    '40': 'Wrong username or password.',
    '41': 'Token authentication not supported for LDAP users.',
    '50': 'User is not authorized for the given operation.',
    '60': 'The trial period for the Subsonic server is over. Please upgrade to Subsonic Premium.',
    '70': 'The requested data was not found.',
}

class SubsonicREST():
    def __init__(self, args):
        self.login = args['u']
        self.password = args.get('p', '')
        self.token = args.get('t', '')
        self.salt = args.get('s', '')
        self.version = args['v']
        self.client = args['c']
        self.format = args.get('f', 'xml')

        self.xsd_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '../api/subsonic/subsonic-rest-api-' + args['v'] + '.wsdl',
        )

    def make_error(self, code='0', message=''):
        root = etree.Element('subsonic-response', status='failed', version=API_VERSION)
        etree.SubElement(
            root, 'error', code=code, message=message or API_ERROR_LIST[code]
        )
        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )

    def check_login(self):
        uid = False
        if self.password:
            if self.password.startswith('enc:'):
                password = binascii.unhexlify(self.password[4:])
            else:
                password = self.password
            uid = request.session.authenticate(request.session.db, self.login, password)

        elif self.token and self.salt:
            return False, self.make_error('30')

        if uid:
            root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
            return True, request.make_response(
                etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
            )
        else:
            return False, self.make_error('40')
