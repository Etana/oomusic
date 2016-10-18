# -*- coding: utf-8 -*-

from lxml import etree

from odoo import http
from odoo.http import request
from sub_common import SubsonicREST, API_VERSION

class MusicSubsonicList(http.Controller):
    @http.route(['/rest/getAlbumList2.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getAlbumList2(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        list_type_accepted = [
            'random', 'newest', 'frequent', 'recent', 'starred', 'alphabeticalByName',
            'alphabeticalByArtist', 'byYear', 'byGenre'
        ]

        list_type = kwargs.get('type')
        if not list_type:
            return rest.make_error(
                code='10', message='Required string parameter "type" is not present'
            )
        if list_type not in list_type_accepted:
            return rest.make_error(code='0', message='Invalid list type: %s' % list_type)

        fromYear = kwargs.get('fromYear')
        toYear = kwargs.get('toYear')
        if list_type == 'byYear' and (not fromYear or not toYear):
            return rest.make_error(
                code='10', message='Required string parameter "fromYear" or "toYear" is not present'
            )

        genre = kwargs.get('genre')
        if list_type == 'byGenre' and not genre:
            return rest.make_error(
                code='10', message='Required string parameter "genre" is not present'
            )

        folderId = kwargs.get('musicFolderId')
        if folderId:
            folder = request.env['oomusic.folder'].browse([int(folderId)])
            if not folder.exists():
                return rest.make_error(code='70', message='Folder not found')

        size = int(kwargs.get('size', 10))
        offset = int(kwargs.get('offset', 0))

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        xml_album_list = rest.make_AlbumList2()
        root.append(xml_album_list)

        albums = request.env['oomusic.album'].search([('year', 'like', '20')])
        if albums:
            min_val = min(offset, len(albums))
            max_val = min_val + size
            for album in albums[min_val:max_val]:
                xml_album = rest.make_AlbumID3(album)
                xml_album_list.append(xml_album)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )
