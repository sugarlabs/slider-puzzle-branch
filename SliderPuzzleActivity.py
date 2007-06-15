from sugar.activity.activity import Activity, ActivityToolbox, get_bundle_path
from gettext import gettext as _
from SliderPuzzleUI import SliderPuzzleUI
import logging, os

import telepathy.client
from telepathy import CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, CHANNEL_TYPE_TEXT
from sugar.presence import presenceservice


logger = logging.getLogger('sliderpuzzle-activity')

import json

class SliderPuzzleActivity(Activity):
	def __init__(self, handle):
		Activity.__init__(self, handle)
		logger.debug('Starting Slider Puzzle activity... %s' % str(get_bundle_path()))
		os.chdir(get_bundle_path())
		self.connect('destroy', self._destroy_cb)

		#self._jobject.metadata['title'] = _('Slider Puzzle')
		
		toolbox = ActivityToolbox(self)
		self.set_toolbox(toolbox)
		toolbox.show()

		title_widget = toolbox._activity_toolbar.title
		title_widget.set_size_request(title_widget.get_layout().get_pixel_size()[0] + 20, -1)
		
		if getattr(self, 'game', None) is None:
			self.game = SliderPuzzleUI(self)

		self.set_canvas(self.game)
		self.game.show_all()


#		self.connect('shared', self._shared_cb)

		#name, path = self._pservice.get_preferred_connection()
		#self.conn = telepathy.client.Connection(name, path)

		#self.tp_conn_name = name
		#self.tp_conn_path = path
#		self.initiating = None
#
#		owner = self._pservice.get_owner()
#		self.owner = owner
#
#		if self._shared_activity:
#			print self._shared_activity
#			print dir(self._shared_activity)
#			print "Joining activity with %s" % [x.get_property('nick') for x in self._shared_activity.get_joined_buddies()]
#			# we are joining the activity
#			#self.buddies_panel.add_watcher(owner)
#			self.connect('joined', self._joined_cb)
#			self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
#			self._shared_activity.connect('buddy-left', self._buddy_left_cb)
#			if self.get_shared():
#				# oh, OK, we've already joined
#				self._joined_cb()
#
#
#	def _shared_cb(self, activity):
#		print 'My Connect activity was shared'
#		
#		print [x.get_property('nick') for x in self._shared_activity.get_joined_buddies()]
#
#		self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
#		self._shared_activity.connect('buddy-left', self._buddy_left_cb)
#
#		self._handle_sharing()
#		
#
#	def _handle_sharing (self):
#		bus_name, conn_path, channel_paths = self._shared_activity.get_channels()
#		# Work out what our room is called and whether we have Tubes already
#		room = None
#		tubes_chan = None
#		text_chan = None
#		for channel_path in channel_paths:
#			channel = telepathy.client.Channel(bus_name, channel_path)
#			htype, handle = channel.GetHandle()
#			if htype == telepathy.HANDLE_TYPE_ROOM:
#				logger.debug('Found our room: it has handle#%d "%s"',
#										 handle, self.conn.InspectHandles(htype, [handle])[0])
#				room = handle
#				ctype = channel.GetChannelType()
#				if ctype == telepathy.CHANNEL_TYPE_TUBES:
#					logger.debug('Found our Tubes channel at %s', channel_path)
#					tubes_chan = channel
#				elif ctype == telepathy.CHANNEL_TYPE_TEXT:
#					logger.debug('Found our Text channel at %s', channel_path)
#					text_chan = channel
#		print room
#		print tubes_chan
#		print text_chan
#
#		self.text_chan = text_chan
#		self.text_chan[CHANNEL_TYPE_TEXT].connect_to_signal('Received', self._tc_received_cb)
#
#	def _tc_received_cb (self, id, timestamp, sender, type, flags, text):
#		print "received",id,timestamp,sender,type,flags,text
#		
#	def _joined_cb(self, activity):
#		print 'joined a remote activity'
#		self._handle_sharing()
#		self.text_chan[CHANNEL_TYPE_TEXT].Send(CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, "Ping")
#
#		
#	def _buddy_joined_cb (self, activity, buddy):
#		print "buddy '%s' joined" % buddy.get_property('nick')
#
#	def _buddy_left_cb (self,  activity, buddy):
#		print "buddy '%s' left" % buddy,get_property('nick')

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
			self.game = SliderPuzzleUI(self)
		self.game._thaw(json.read(session_data))
		
	def write_file(self, file_path):
		session_data = json.write(self.game._freeze())
		
		if self.game.thumb.get_filename:
			self.metadata['preview'] = self.game.thumb.get_category_name()
		else:
			self.metadata['preview'] = ''
		f = open(file_path, 'w')
		try:
			f.write(session_data)
		finally:
			f.close()


