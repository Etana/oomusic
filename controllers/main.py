# -*- coding: utf-8 -*-

import logging
import os

from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class MusicController(http.Controller):

    @http.route(['/oomusic/down/<int:track_id>'], type='http', auth='user')
    def down(self, track_id, **kwargs):
        Track = request.env['oomusic.track'].browse([track_id])
        return http.send_file(Track.path, as_attachment=True)

    @http.route([
        '/oomusic/trans/<int:track_id>.<string:output_format>',
        '/oomusic/trans/<int:track_id>_<int:seek>.<string:output_format>',
        ], type='http', auth='user')
    def trans(self, track_id, output_format, seek=0, **kwargs):
        Track = request.env['oomusic.track'].browse([track_id])
        fn_ext = os.path.splitext(Track.path)[1]

        Transcoder = request.env['oomusic.transcoder'].search(
            [('input_formats.name', '=', fn_ext[1:]), ('output_format.name', '=', output_format)],
            limit=1,
        )
        if Transcoder:
            generator = Transcoder.transcode(track_id, seek=seek).stdout
            mimetype = Transcoder.output_format.mimetype
        if not Transcoder:
            _logger.warning('Could not find converter from "%s" to "%s"', fn_ext[1:], output_format)
            return http.send_file(Track.path)

        # FIXME: see http://librelist.com/browser/flask/2011/10/5/response-to-a-range-request/#1e95dd715f412161d3db2fc8aaf8666f

        # Set a buffer size of 200 KB. The default value (8 KB) seems too small and leads to chunk
        # download errors. Since the player is not fault-tolerant, a single download error leads to
        # a complete stop of the music. Maybe consider this value as a user option for people with
        # bad network.
        data = wrap_file(
            request.httprequest.environ, generator, buffer_size=Transcoder.buffer_size * 1024)
        return Response(data, mimetype=mimetype, direct_passthrough=True)

    @http.route([
        '/oomusic/playlist/<int:playlist_id>.m3u'
        ], type='http', auth='public')
    def playlist(self, playlist_id, **kwargs):
        playlist = request.env['oomusic.playlist'].sudo().browse(playlist_id)
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        tracks_urls = []
        for playlist_line in playlist.playlist_line_ids:
            track_pathname = playlist_line.track_id._oomusic_info()['mp3'].replace('/trans/', '/sudotrans/')
            tracks_urls.append('{}{}'.format(base_url, track_pathname))
        return Response('\n'.join(tracks_urls), content_type='text/plain')

    @http.route([
        '/oomusic/sudotrans/<int:track_id>.<string:output_format>',
        ], type='http', auth='public')
    def sudotrans(self, *argv, **kwargs):
        request.uid = 1
        return self.trans(*argv, **kwargs)
