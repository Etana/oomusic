# -*- coding: utf-8 -*-

import datetime
import os
import subprocess

from odoo import fields, models

class MusicTranscoder(models.Model):
    _name = 'oomusic.transcoder'
    _description = 'Music Transcoder'
    _order = 'sequence'

    name = fields.Char('Transcoder Name', required=True)
    sequence = fields.Integer(default=10,
        help='Sequence used to order the transcoders. The lower the value, the higher the priority')
    command = fields.Char(
        'Command line', required=True,
        help='''Command to execute for transcoding. Specific keywords are automatically replaced:
        - "INPUT": input file
        - "SEEK": start from this seek time
        - "BITRATE": birate for output file
        '''
    )
    bitrate = fields.Integer(
        'Bitrate', required=True,
        help='Default bitrate. Can be changed if necessary when the transcoding function is called'
    )
    input_formats = fields.Many2many(
        'oomusic.format', string='Input Formats', required=True, index=True,
    )
    output_format = fields.Many2one('oomusic.format', string='Output Format', required=True)
    buffer_size = fields.Integer(
        'Buffer Size (KB)', required=True, default=200,
        help='''Size of the buffer used while streaming. A larger value can reduce the potential
        file download errors when playing, but will increase the waiting delay when switching
        songs.
        The default value (200 KB) should be a good compromise between waiting delay and download
        stability. A large value (e.g. 20000 KB) will ensure the complete download of the file
        before playing.'''
    )

    def transcode(self, track_id, bitrate=0, seek=0):
        '''
        Method used to transcode a track. It takes in charge the replacement of the specific
        keywords of the command, and returns the subprocess executed. The subprocess output is
        redirected to stdout, so it is possible to stream the transcoding result while it is still
        ongoing.
        :param track_id: ID of the track to transcode
        :param bitrate: value of the bitrate for the output file. Optional field aimed to override
            the default value
        :param seek: start time for the encoding
        :returns: subprocess redirected to stdout.
        :rtype: subprocess.Popen
        '''
        self.ensure_one()

        Track = self.env['oomusic.track'].browse([track_id])
        cmd = self.command\
            .replace('SEEK', '%s' % (str(datetime.timedelta(seconds=seek))))\
            .replace('BITRATE', '%d' % (bitrate or self.bitrate))
        cmd = cmd.split(' ')
        cmd[cmd.index('INPUT')] = Track.path

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=open(os.devnull, 'w'))
        return proc
