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
        root.append(xml_indexes)

        if ifModifiedSince is not None and folder.last_modification < ifModifiedSince:
            return request.make_response(
                etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
            )

        # Build indexes
        indexes_dict = rest.build_dict_indexes_folder(folder)

        # List of folders
        for k, v in sorted(indexes_dict.iteritems()):
            xml_index = rest.make_Index(k)
            xml_indexes.append(xml_index)
            for child in v:
                xml_data = rest.make_Artist(child)
                xml_index.append(xml_data)

        # List of tracks
        for track in folder.track_ids:
            xml_data = rest.make_Child_track(track)
            xml_indexes.append(xml_data)

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
        xml_directory = rest.make_Directory(folder)
        root.append(xml_directory)

        # List of folders
        for child in folder.child_ids:
            xml_data = rest.make_Child_folder(child)
            xml_directory.append(xml_data)

        # List of tracks
        for track in folder.track_ids:
            xml_data = rest.make_Child_track(track)
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
        xml_genres = rest.make_Genres()
        root.append(xml_genres)

        for genre in request.env['oomusic.genre'].search([]):
            xml_data = rest.make_Genre(genre)
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
        xml_artists = rest.make_ArtistsID3()
        root.append(xml_artists)

        musicFolderId = kwargs.get('musicFolderId')
        if musicFolderId:
            artists = request.env['oomusic.track'].search([
                ('folder_id', 'child_of', int(musicFolderId))
            ]).mapped('artist_id')
        else:
            artists = request.env['oomusic.artist'].search([])

        # Build indexes
        indexes_dict = rest.build_dict_indexes_artists(artists)

        # List of artists
        for k, v in sorted(indexes_dict.iteritems()):
            xml_index = rest.make_IndexID3(k)
            xml_artists.append(xml_index)
            for artist in v:
                xml_artist = rest.make_ArtistID3(artist)
                xml_index.append(xml_artist)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )

    @http.route(['/rest/getArtist.view'], type='http', auth='public', methods=['GET', 'POST'])
    def getArtist(self, **kwargs):
        rest = SubsonicREST(kwargs)
        success, response = rest.check_login()
        if not success:
            return response

        artistId = kwargs.get('id')
        if artistId:
            artist = request.env['oomusic.artist'].browse([int(artistId)])
            if not artist.exists():
                return rest.make_error('70', 'Artist not found')
        else:
            return rest.make_error('10', 'Required artist ID missing.')

        root = etree.Element('subsonic-response', status='ok', version=API_VERSION)
        xml_artist = rest.make_ArtistID3(artist)
        root.append(xml_artist)

        for album in artist.album_ids:
            xml_album = rest.make_AlbumID3(album)
            xml_artist.append(xml_album)

        return request.make_response(
            etree.tostring(root, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        )
