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
        musicFolders = rest.make_MusicFolders()
        root.append(musicFolders)

        for folder in request.env['oomusic.folder'].search([('root', '=', True)]):
            musicFolder = rest.make_MusicFolder(folder)
            musicFolders.append(musicFolder)

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

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        xml_indexes = rest.make_Indexes(folder)

        if ifModifiedSince is not None and folder.last_modification < ifModifiedSince:
            root.append(xml_indexes)
            return request.make_response(
                etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
            )

        # Build indexes
        indexes_dict = rest.build_dict_indexes_folder(folder)

        # List of folders
        for k, v in sorted(indexes_dict.iteritems()):
            xml_index = rest.make_Index(k)
            for child in v:
                xml_data = rest.make_Artist(child)
                xml_index.append(xml_data)
            xml_indexes.append(xml_index)

        # List of tracks
        for track in folder.track_ids:
            xml_data = rest.make_Child_track(track)
            xml_indexes.append(xml_data)

        root.append(xml_indexes)

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
        xml_directory = rest.make_directory(folder)
        root.append(xml_directory)

        # List of folders
        for child in folder.child_ids:
            xml_data = rest.make_directory_child(child)
            xml_directory.append(xml_data)

        # List of tracks
        for track in folder.track_ids:
            xml_data = rest.make_track(track)
            xml_directory.append(xml_data)

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
        xml_genres = etree.SubElement(root, 'genres')

        for genre in request.env['oomusic.genre'].search([]):
            xml_data = rest.make_genre(genre)
            xml_genres.append(xml_data)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )

    @http.route(['/rest/getArtists.view'], type='http', auth='public', methods=['GET', 'POST'])
    def getArtists(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        xml_artists = etree.SubElement(root, 'artists', ignoredArticles='The El La Los Las Le Les')

        # Build indexes
        musicFolderId = kwargs.get('musicFolderId')
        if musicFolderId:
            artists = request.env['oomusic.track'].search([
                ('folder_id', 'child_of', musicFolderId)
            ]).mapped('artist_id')
        else:
            artists = request.env['oomusic.artist'].search([])

        indexes_dict = {}
        for artist in artists:
            name = artist.name
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
            indexes_dict[index].append(artist)

        for k, v in sorted(indexes_dict.iteritems()):
            xml_index = etree.SubElement(xml_artists, 'index', name=k)
            for artist in v:
                xml_artist = rest.make_artist(artist)
                xml_index.append(xml_artist)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )
