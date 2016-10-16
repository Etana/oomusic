# -*- coding: utf-8 -*-

import logging
import os

from lxml import etree

from odoo import http
from odoo.http import request
from sub_common import SubsonicREST, API_VERSION

_logger = logging.getLogger(__name__)

class MusicSubsonicSystem(http.Controller):
    @http.route(['/rest/getMusicFolders.view'], type='http', auth='public', methods=['GET', 'POST'])
    def getMusicFolders(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        musicFolders = etree.SubElement(root, 'musicFolders')

        for folder in request.env['oomusic.folder'].search([('root', '=', True)]):
            etree.SubElement(
                musicFolders, 'musicFolder', id=str(folder.id), name=folder.name or folder.path
            )
        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )

    @http.route(['/rest/getIndexes.view'], type='http', auth='public', methods=['GET', 'POST'])
    def getIndexes(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        ifModifiedSince = kwargs.get('ifModifiedSince')
        if ifModifiedSince:
            try:
                ifModifiedSince = int(ifModifiedSince) / 1000
            except:
                return rest.make_error('0', 'Invalid timestamp')

        musicFolderId = kwargs.get('musicFolderId')
        if musicFolderId is None:
            folder = request.env['oomusic.folder'].search([('root', '=', True)], limit=1)
        else:
            folder = request.env['oomusic.folder'].browse([int(musicFolderId)])
            if not folder.exists():
                return rest.make_error('70', 'Folder not found')

        if ifModifiedSince is not None and folder.last_modification < ifModifiedSince:
            root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
            etree.SubElement(root, 'indexes', lastModified=str(folder.last_modification*1000))
            return request.make_response(
                etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
            )

        # Build indexes
        indexes_dict = {}
        for child in folder.child_ids.sorted(lambda r: r.path):
            name = os.path.basename(child.path)
            if name[:4] in ['The ', 'Los ', 'Las ', 'Les ']:
                index = name[4:][0]
            elif name[:3] in ['El ', 'La ', 'Le ']:
                index = name[3:][0]
            else:
                index = name[0].upper()
            if index in map(str, xrange(10)):
                index = '#'
            elif not index.isalnum():
                index = '?'

            indexes_dict.setdefault(index, [])
            indexes_dict[index].append(child)

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        indexes = etree.SubElement(
            root, 'indexes',
            lastModified=str(folder.last_modification*1000),
            ignoredArticles='The El La Los Las Le Les',
        )

        # List of folders
        for k, v in sorted(indexes_dict.iteritems()):
            index = etree.SubElement(indexes, 'index', name=k)
            for child in v:
                etree.SubElement(
                    index, 'artist', id=str(child.id), name=os.path.basename(child.path)
                )

        # List of tracks
        for track in folder.track_ids:
            xml_data = rest.make_track(track)
            indexes.append(xml_data)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )

    @http.route(['/rest/getMusicDirectory.view'], type='http', auth='public', methods=['GET', 'POST'])
    def getMusicDirectory(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        folderId = kwargs.get('id')
        folder = request.env['oomusic.folder'].browse([int(folderId)])
        if not folder.exists():
            return rest.make_error('70', 'Folder not found')

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        directory = rest.make_directory(folder)
        root.append(directory)

        # List of folders
        for child in folder.child_ids:
            xml_data = rest.make_directory_child(child)
            directory.append(xml_data)

        # List of tracks
        for track in folder.track_ids:
            xml_data = rest.make_track(track)
            directory.append(xml_data)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )

    @http.route(['/rest/getGenres.view'], type='http', auth='public', methods=['GET', 'POST'])
    def getGenres(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        genres = etree.SubElement(root, 'genres')

        for genre in request.env['oomusic.genre'].search([]):
            xml_data = rest.make_genre(genre)
            genres.append(xml_data)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )
