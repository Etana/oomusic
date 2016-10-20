# -*- coding: utf-8 -*-

import random

from lxml import etree

from odoo import http
from odoo.http import request
from sub_common import SubsonicREST, API_VERSION


def _uniquify_list(seq):
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]

class MusicSubsonicList(http.Controller):
    @http.route(['/rest/getAlbumList2.view'], type='http', auth='public', csrf=False, methods=['GET', 'POST'])
    def getAlbumList2(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        AlbumObj = request.env['oomusic.album']

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

        size = min(int(kwargs.get('size', 10)), 500)
        offset = int(kwargs.get('offset', 0))

        # Build domain
        domain = []
        if list_type == 'byYear':
            domain += [('year', '>=', fromYear), ('year', '<=', toYear)]
        elif list_type == 'byGenre':
            domain += [('genre_id.name', 'ilike', genre)]
        elif list_type == 'byGenre':
            domain += [('star', '=', '1')]

        # Search for albums
        albums = False
        if list_type == 'random':
            params = (request.env.user.id, )
            query = "SELECT id FROM oomusic_album WHERE user_id = %s;"
            request.env.cr.execute(query, params)
            res = request.env.cr.fetchall()
            if not res:
                album_ids = []
            else:
                album_ids = random.sample([r[0] for r in res], size)
            albums = AlbumObj.browse(album_ids)

        elif list_type == 'newest':
            albums = AlbumObj.search(domain, order='create_date desc')

        elif list_type == 'recent':
            params = (request.env.user.id, )
            query = """
                SELECT album_id FROM oomusic_track
                WHERE user_id = %s and last_play is not NULL
                ORDER BY last_play desc;
            """
            request.env.cr.execute(query, params)
            res = request.env.cr.fetchall()

            album_ids = _uniquify_list([r[0] for r in res if r[0] is not None])
            albums = AlbumObj.browse(album_ids)

        elif list_type == 'frequent':
            params = (request.env.user.id, )
            query = """
                SELECT album_id FROM oomusic_track
                WHERE user_id = %s
                ORDER BY play_count desc;
            """
            request.env.cr.execute(query, params)
            res = request.env.cr.fetchall()

            album_ids = _uniquify_list([r[0] for r in res if r[0] is not None])
            albums = AlbumObj.browse(album_ids)

        elif list_type == 'alphabeticalByName':
            albums = AlbumObj.search(domain, order='name')

        elif list_type == 'alphabeticalByArtist':
            albums = AlbumObj.search(domain, order='artist_id')

        else:
            albums = AlbumObj.search(domain)

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        xml_album_list = rest.make_AlbumList2()
        root.append(xml_album_list)

        if albums:
            min_val = min(offset, len(albums))
            max_val = min_val + size
            for album in albums[min_val:max_val]:
                xml_album = rest.make_AlbumID3(album)
                xml_album_list.append(xml_album)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )
