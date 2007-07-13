from sugar.activity.activity import Activity, ActivityToolbox, get_bundle_path
from gettext import gettext as _
from SliderPuzzleUI import SliderPuzzleUI
from tube_helper import TubeHelper
import logging, os
import md5

logger = logging.getLogger('sliderpuzzle-activity')

import json

class FrozenState (object):
	""" Keep everything about a game state here so we can easily store our state in the Journal or
	send it to mesh peers """
	def __init__ (self, slider_ui):
		self.slider_ui = slider_ui
		self._lock = False
		self.sync()

	def sync (self, *args):
		""" reads the current state for the slider_ui and keeps it """
		if self._lock:
			return
		logger.debug("sync'ing game state")
		self.nr_pieces = self.slider_ui.game.get_nr_pieces()
		self.category_path = self.slider_ui.thumb.get_image_dir()
		self.image_path = self.slider_ui.game.filename
		if self.slider_ui.thumb.is_myownpath():
			self.image_path = os.path.basename(self.image_path)
		self.image_digest = self.slider_ui.game.image_digest
		self.game_state = self.slider_ui.game._freeze()
		logger.debug("sync game_state: %s" % str(self.game_state))
		logger.debug("sync category: %s image: %s (md5: %s)" % (self.category_path, self.image_path, self.image_digest))

	def freeze (self):
		"""return a json version of the kept data"""
		return json.write({
			'nr_pieces': self.nr_pieces,
			'image_path': self.image_path,
			'image_digest': self.image_digest,
			'game_state': self.game_state,
			})

	def thaw (self, state=None, tube=None, forced_image=None):
		""" apply the previously saved state to the running game """
		try:
			self._lock = True
			if state is None:
				state = self.freeze()
			for k,v in json.read(state).items():
				if hasattr(self, k):
					logger.debug("%s=%s" % (k,str(v)))
					setattr(self, k, v)
			if self.image_path:
				if self.image_path == os.path.basename(self.image_path):
					# MyOwnPath based image...
					found = False
					if forced_image is not None:
						name = 'image_' + self.image_path
						while os.path.exists(os.path.join(self.slider_ui.thumb.myownpath, name)):
							name = '_' + name
						f = file(os.path.join(self.slider_ui.thumb.myownpath, name), 'wb')
						f.write(forced_image)
						f.close()
						self.slider_ui.thumb.set_image_dir(os.path.join(self.slider_ui.thumb.myownpath, name))
						self.slider_ui.set_nr_pieces(None, self.nr_pieces)
						self.slider_ui.game._thaw(self.game_state)
						logger.debug("thaw game_state: %s" % str(self.game_state))
						found = True
					else:
						for link, name, digest in self.slider_ui.thumb.gather_myownpath_images():
							if digest == self.image_digest:
								logger.debug("Found the image in myownpath!")
								self.slider_ui.thumb.set_image_dir(os.path.join(self.slider_ui.thumb.myownpath, link))
								self.slider_ui.set_nr_pieces(None, self.nr_pieces)
								self.slider_ui.game._thaw(self.game_state)
								logger.debug("thaw game_state: %s" % str(self.game_state))
								found = True
								break
						if not found:
							logger.debug("Don't know the image, so request it")
							if tube is not None:
								tube.NeedImage()
				elif os.path.exists(self.image_path) and md5.new(file(self.image_path, 'rb').read()).hexdigest() == self.image_digest:
					logger.debug("We have the image!")
					self.slider_ui.thumb.set_image_dir(self.image_path)
					#self.slider_ui.game.load_image(self.image_path)
					self.slider_ui.set_nr_pieces(None, self.nr_pieces)
					self.slider_ui.game._thaw(self.game_state)
					logger.debug("thaw game_state: %s" % str(self.game_state))
				else:
					logger.debug("Don't know the image, so request it")
					if tube is not None:
						tube.NeedImage()
			else:
				logger.debug("No image...")
		finally:
			self._lock = False

class SliderPuzzleActivity(Activity, TubeHelper):
	def __init__(self, handle):
		Activity.__init__(self, handle)
		logger.debug('Starting Slider Puzzle activity... %s' % str(get_bundle_path()))
		os.chdir(get_bundle_path())
		self.connect('destroy', self._destroy_cb)

		#self._jobject.metadata['title'] = _('Slider Puzzle')
		
		toolbox = ActivityToolbox(self)
		self.set_toolbox(toolbox)
		toolbox.show()
    #if hasattr(self, '_jobject'):
		title_widget = toolbox._activity_toolbar.title
		title_widget.set_size_request(title_widget.get_layout().get_pixel_size()[0] + 20, -1)
		
		if getattr(self, 'game', None) is None:
			self.ui = SliderPuzzleUI(self)

		self.set_canvas(self.ui)
		self.show_all()

		self.frozen = FrozenState(self.ui)
		self.ui.game.connect('shuffled', self.frozen.sync)

		TubeHelper.__init__(self)

	def _destroy_cb(self, data=None):
		return True

	def read_file(self, file_path):
		f = open(file_path, 'r')
		try:
			session_data = f.read()
		finally:
			f.close()
		logging.debug('Trying to set session: %s.' % session_data)
		if getattr(self, 'game', None) is None:
			self.ui = SliderPuzzleUI(self)
		self.ui._thaw(json.read(session_data))
		
	def write_file(self, file_path):
		session_data = json.write(self.ui._freeze())
		f = open(file_path, 'w')
		try:
			f.write(session_data)
		finally:
			f.close()


