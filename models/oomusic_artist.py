# -*- coding: utf-8 -*-

import datetime
import json
import requests
from werkzeug.urls import url_fix

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.tools.safe_eval import safe_eval

from . import FM_API_KEY, FM_CACHE_DURATION

class MusicArtist(models.Model):
    _name = 'oomusic.artist'
    _description = 'Music Artist'
    _order = 'name'

    name = fields.Char('Artist', index=True)
    track_ids = fields.One2many('oomusic.track', 'artist_id', string='Tracks')
    album_ids = fields.One2many('oomusic.album', 'artist_id', string='Albums')
    user_id = fields.Many2one(
        'res.users', string='User', index=True, required=True, ondelete='cascade',
        default=lambda self: self.env.user
    )

    fm_last_update = fields.Datetime('Last Update', default='2000-01-01 00:00:00')
    fm_getinfo = fields.Char('Biography', compute='_compute_fm_getinfo')
    fm_getinfo_cache = fields.Char('Biography')
    fm_gettoptracks = fields.Many2many(
        'oomusic.track', string='Top Tracks', compute='_compute_fm_gettoptracks')
    fm_gettoptracks_cache = fields.Char('Top Tracks')

    _sql_constraints = [
        ('oomusic_artist_name_uniq', 'unique(name, user_id)', 'Artist name must be unique!'),
    ]

    def _compute_fm_getinfo(self):
        if not self.env.context.get('compute_fields', True):
            return
        for artist in self:
            fm_last_update = datetime.datetime.strptime(artist.fm_last_update, DATETIME_FORMAT)
            if artist.fm_getinfo_cache\
                    and (fm_last_update - datetime.datetime.utcnow()).days < FM_CACHE_DURATION:
                artist.fm_getinfo = artist.fm_getinfo_cache
                return

            getinfo_url = url_fix(
                'https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist='\
                + artist.name + '&api_key=' + FM_API_KEY + '&format=json'
            )
            try:
                r = requests.get(getinfo_url, timeout=3.0)
                if r.status_code == 200:
                    r_json = json.loads(r.content)
                    artist.fm_getinfo =\
                        r_json['artist']['bio']['content'].replace('\n', '<br/>')\
                        or _('Biography not found')

            except:
                artist.fm_getinfo = _('Biography not found')

            # Save in cache
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            new_self.env['oomusic.artist'].browse(artist.id).sudo().write({
                'fm_getinfo_cache': artist.fm_getinfo,
                'fm_last_update': fields.Datetime.now(),
            })
            new_self.env.cr.commit()
            new_self.env.cr.close()

    def _compute_fm_gettoptracks(self):
        if not self.env.context.get('compute_fields', True):
            return
        for artist in self:
            fm_last_update = datetime.datetime.strptime(artist.fm_last_update, DATETIME_FORMAT)
            if artist.fm_gettoptracks_cache\
                    and artist.fm_gettoptracks_cache != "[]"\
                    and (fm_last_update - datetime.datetime.utcnow()).days < FM_CACHE_DURATION:
                top_tracks = safe_eval(artist.fm_gettoptracks_cache or "[]")
                artist.fm_gettoptracks = self.env['oomusic.track'].browse(top_tracks).exists().ids
                return

            gettoptracks_url = url_fix(
                'http://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist='\
                + artist.name + '&api_key=' + FM_API_KEY + '&format=json'
            )
            try:
                r = requests.get(gettoptracks_url, timeout=3.0)
                if r.status_code == 200:
                    r_json = json.loads(r.content)
                    track_cache = {
                        ''.join(c.lower() for c in t.name if c.isalnum()): t.id
                        for t in artist.track_ids
                    }
                    fm_gettoptracks = []
                    for track in r_json['toptracks']['track']:
                        track_name = ''.join(c.lower() for c in track['name'] if c.isalnum())
                        if track_name in track_cache.keys():
                            fm_gettoptracks.append(track_cache[track_name])
                            if len(fm_gettoptracks) > 9:
                                break
                    artist.fm_gettoptracks = fm_gettoptracks

            except:
                artist.fm_gettoptracks = []

            # Save in cache
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            new_self.env['oomusic.artist'].browse(artist.id).sudo().write({
                'fm_gettoptracks_cache': str(artist.fm_gettoptracks.ids),
                'fm_last_update': fields.Datetime.now(),
            })
            new_self.env.cr.commit()
            new_self.env.cr.close()

    @api.multi
    def action_add_to_playlist(self):
        Playlist = self.env['oomusic.playlist'].search([('current', '=', True)], limit=1)
        if not Playlist:
            raise UserError(_('No current playlist found!'))
        for artist in self:
            Playlist._add_tracks(artist.track_ids)
