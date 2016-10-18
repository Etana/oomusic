# -*- coding: utf-8 -*-

import binascii
import mimetypes
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
IGNORED_ARTICLES = ['The', 'El', 'La', 'Los', 'Las', 'Le', 'Les']

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

    def build_dict_indexes_folder(self, folder):
        indexes_dict = {}
        for child in folder.child_ids:
            name = os.path.basename(child.path)
            if name[:4] in [e + ' ' for e in IGNORED_ARTICLES if len(e) == 3]:
                index = name[4:][0]
            elif name[:3] in [e + ' ' for e in IGNORED_ARTICLES if len(e) == 2]:
                index = name[3:][0]
            else:
                index = name[0].upper()
            if index in map(str, xrange(10)):
                index = '#'
            elif not index.isalnum():
                index = '?'

            indexes_dict.setdefault(index, [])
            indexes_dict[index].append(child)

        return indexes_dict

    def build_dict_indexes_artists(self, artists):
        indexes_dict = {}
        for artist in artists:
            name = artist.name
            if name[:4] in [e + ' ' for e in IGNORED_ARTICLES if len(e) == 3]:
                index = name[4:][0]
            elif name[:3] in [e + ' ' for e in IGNORED_ARTICLES if len(e) == 2]:
                index = name[3:][0]
            else:
                index = name[0].upper()
            if index in map(str, xrange(10)):
                index = '#'
            elif not index.isalnum():
                index = '?'

            indexes_dict.setdefault(index, [])
            indexes_dict[index].append(artist)

        return indexes_dict

    def make_MusicFolders(self):
        return etree.Element('musicFolders')

    def make_MusicFolder(self, folder):
        return etree.Element(
            'musicFolder',
            id=str(folder.id),
            name=folder.name or os.path.basename(folder.path),
        )

    def make_Indexes(self, folder):
        return etree.Element(
            'indexes',
            lastModified=str(folder.last_modification*1000),
            ignoredArticles=' '.join(IGNORED_ARTICLES),
        )

    def make_Index(self, index):
        return etree.Element('index', name=index)

    def make_Artist(self, folder):
        elem_artist = etree.Element(
            'artist',
            id=str(folder.id),
            name=os.path.basename(folder.path),
        )

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.10.2']:
            if folder.star == '1':
                elem_artist.set('starred', folder.write_date.replace(' ', 'T') + 'Z')

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.13.0']:
            if folder.rating and folder.rating != '0':
                elem_artist.set('userRating', folder.rating)
                elem_artist.set('averageRating', folder.rating)

        return elem_artist

    def make_Child_track(self, track, tag_name='child'):
        elem_track = etree.Element(
            tag_name,
            id=str(track.id),
            parent=str(track.folder_id.id),
            isDir='false',
            size=str(os.path.getsize(track.path)),
            contentType=mimetypes.guess_type(track.path)[0],
            suffix=os.path.splitext(track.path)[1].lstrip('.'),
            transcodedContentType='audio/mpeg',
            transcodedSuffix='mp3',
            duration=str(track.duration),
            bitRate=str(track.bitrate),
            path=os.path.basename(track.path),
        )

        if track.name:
            elem_track.set('title', track.name)
        if track.album_id:
            elem_track.set('album', track.album_id.name)
        if track.artist_id:
            elem_track.set('artist', track.artist_id.name)
        if track.track_number:
            elem_track.set('track', track.track_number)
        if track.year:
            elem_track.set('year', track.year)
        if track.genre_id:
            elem_track.set('genre', track.genre_id.name)


        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.4.0']:
            elem_track.set('isVideo', 'false')
        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.6.0']:
            if track.rating and track.rating != '0':
                elem_track.set('userRating', track.rating)
                elem_track.set('averageRating', track.rating)
        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.14.0']:
            elem_track.set('playCount', str(track.play_count))
        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.8.0']:
            if track.disc:
                elem_track.set('discNumber', track.disc)
            elem_track.set('created', track.create_date.replace(' ', 'T') + 'Z')
            if track.star == '1':
                elem_track.set('starred', track.write_date.replace(' ', 'T') + 'Z')
            elem_track.set('albumId', str(track.album_id.id))
            elem_track.set('artistId', str(track.artist_id.id))
            elem_track.set('type', 'music')
        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.10.2']:
            elem_track.set('bookmarkPosition', '0.0')

        return elem_track

    def make_Child_folder(self, folder):
        elem_directory = etree.Element(
            'child',
            id=str(folder.id),
            isDir='true',
            title=os.path.basename(folder.path),
            path=folder.path,
        )

        if folder.track_ids:
            track = folder.track_ids[0]
            elem_directory.set('album', track.album_id.name or '')
            elem_directory.set('artist', track.artist_id.name or '')
            elem_directory.set('year', track.year or '')
            elem_directory.set('genre', track.genre_id.name or '')
            if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.8.0']:
                elem_directory.set('discNumber', track.disc or '')
                elem_directory.set('albumId', str(track.album_id.id))
                elem_directory.set('artistId', str(track.artist_id.id))

        if folder.parent_id:
            elem_directory.set('parent', str(folder.parent_id.id))

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.6.0']:
            if folder.rating and folder.rating != '0':
                elem_directory.set('userRating', folder.rating)
                elem_directory.set('averageRating', folder.rating)

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.14.0']:
            elem_directory.set('playCount', str(sum(folder.track_ids.mapped('play_count'))))

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.8.0']:
            elem_directory.set('created', folder.create_date.replace(' ', 'T') + 'Z')

        return elem_directory

    def make_Directory(self, folder):
        elem_directory = etree.Element(
            'directory',
            id=str(folder.id),
            name=os.path.basename(folder.path),
        )
        if folder.parent_id:
            elem_directory.set('parent', str(folder.parent_id.id))

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.10.2']:
            if folder.star == '1':
                elem_directory.set('starred', folder.write_date.replace(' ', 'T') + 'Z')

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.13.0']:
            if folder.rating and folder.rating != '0':
                elem_directory.set('userRating', folder.rating)
                elem_directory.set('averageRating', folder.rating)

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.14.0']:
            elem_directory.set('playCount', str(sum(folder.track_ids.mapped('play_count'))))

        return elem_directory

    def make_Genres(self):
        return etree.Element('genres')

    def make_Genre(self, genre):
        elem_genre = etree.Element('genre')
        elem_genre.text = genre.name

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.10.2']:
            elem_genre.set('songCount', str(len(genre.track_ids)))
            elem_genre.set('albumCount', str(len(genre.album_ids)))

        return elem_genre

    def make_ArtistsID3(self):
        elem_artists = etree.Element('artists')

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.10.2']:
            elem_artists.set('ignoredArticles', ' '.join(IGNORED_ARTICLES))

        return elem_artists

    def make_IndexID3(self, index):
        return etree.Element('index', name=index)

    def make_ArtistID3(self, artist):
        elem_artist = etree.Element(
            'artist',
            id=str(artist.id),
            name=artist.name,
            albumCount=str(len(artist.album_ids)),
        )

        if artist.star == '1':
            elem_artist.set('starred', artist.write_date.replace(' ', 'T') + 'Z')

        return elem_artist

    def make_AlbumID3(self, album):
        elem_album = etree.Element(
            'album',
            id=str(album.id),
            name=album.name,
            songCount=str(len(album.track_ids)),
            duration=str(sum(album.track_ids.mapped('duration'))),
            created=album.create_date.replace(' ', 'T') + 'Z',
        )

        if album.artist_id:
            elem_album.set('artist', album.artist_id.name)
            elem_album.set('artistId', str(album.artist_id.id))
        if album.image_folder:
            elem_album.set('coverArt', str(album.folder_id.id))
        if album.star == '1':
            elem_album.set('starred', album.write_date.replace(' ', 'T') + 'Z')

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.10.2']:
            if album.year:
                elem_album.set('year', album.year)
            if album.genre_id:
                elem_album.set('genre', album.genre_id.name)

        if API_VERSION_LIST[self.version] >= API_VERSION_LIST['1.14.0']:
            elem_album.set('playCount', str(sum(album.track_ids.mapped('play_count'))))

        return elem_album
