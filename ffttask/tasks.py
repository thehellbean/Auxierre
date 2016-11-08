from __future__ import absolute_import

from ffttask.CPPFFT import FastFourierTransform
from pydub import AudioSegment
from flaskapp import db, models
from ffttask.celery import celeryApp
import struct
from struct import unpack

@celeryApp.task
def fftMP3(songid):
	# The step size with which to move through the audio 
	length = 2048
	offset = 2048

	# log2(offset)
	exponent = 11
	transformer = FastFourierTransform(length, exponent)
	song = models.Song.query.get(songid)
	if song:
		path = song.path
	else:
		return False
	# Load audio
	audio = AudioSegment.from_mp3(path)

	# Each frequency bin has a bandwidth of the sample rate divided by the FFT length
	bandwidth = audio.frame_rate / float(length)

	# A segment of length offset corresponds to time_per_segment milliseconds of audio
	time_per_segment = length * 1000.0 / float(audio.frame_rate)

	raw_length = len(audio._data)
	data_length = 20 * int(raw_length / (offset * 2 * audio.channels))

	song.time_per_segment = time_per_segment
	song.data_length = data_length
	song.duration = int(audio.duration_seconds)
	db.session.commit()

	step = 0
	rotation = 0
	result = []
	while 2 * audio.channels * offset * (step + 1) < raw_length - 1:
		# Grab an audio segment of length offset
		try:
			if audio.channels == 2:
				data = unpack("{}h".format(offset * 2), audio._data[4 * offset * step:4 * offset * (step + 1)])
				data = [x + y for x, y in zip(data[::2], data[1::2])]
			else:
				data = unpack("{}h".format(offset), audio._data[2 * offset * step:2 * offset * (step + 1)])
		except struct.error:
			if audio.channels == 2:
				section = audio._data[4 * offset * step:]
				data = unpack("{}h".format(len(section) / 2), section)
				data = [x + y for x, y in zip(data[::2], data[1::2])]
			else:
				section = audio._data[2 * offset * step:]
				data = unpack("{}h".format(len(section) / 2), section)
		result.extend(transformer.center_on_octaves(transformer.float_transform(data), bandwidth))
		rotation += 1
		if rotation == 400:
			song.last_index += 20 * rotation
			song.data = song.data + result
			result = []
			rotation = 0
			try:
				db.session.commit()
			except:
				db.session.rollback()
				raise
		step += 1
	try:		
		song.last_index += 20 * rotation
		song.data = song.data + result
		song.full = True
		db.session.commit()
	except:
		db.session.rollback()
		raise