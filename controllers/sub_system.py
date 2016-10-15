# -*- coding: utf-8 -*-

import logging

from lxml import etree

from odoo import http
from odoo.http import request
from sub_common import SubsonicREST, API_VERSION

_logger = logging.getLogger(__name__)

class MusicSubsonicSystem(http.Controller):
    @http.route(['/rest/ping.view'], type='http', auth='public', methods=['GET', 'POST'])
    def ping(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        return response

    @http.route(['/rest/getLicense.view'], type='http', auth='public', methods=['GET', 'POST'])
    def getLicense(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        etree.SubElement(
            root, 'license', valid='true', email='foo@bar.com', licenseExpires='2099-12-31T23:59:59'
        )
        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )
