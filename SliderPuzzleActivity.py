# Copyright 2007 World Wide Workshop Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# If you find this activity useful or end up using parts of it in one of your
# own creations we would love to hear from you at info@WorldWideWorkshop.org !
#

# init gthreads before using abiword
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject
GObject.threads_init()
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from sugar3.activity.activity import Activity, get_bundle_path
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from gettext import gettext as _
from SliderPuzzleUI import SliderPuzzleUI
from mamamedia_modules import TubeHelper
import logging, os, sys
import md5

logger = logging.getLogger('sliderpuzzle-activity')

from mamamedia_modules import json, utils


# game tube
import zlib
import time
from cStringIO import StringIO

from dbus import Interface, DBusException
from dbus.service import method, signal
from dbus.gobject_service import ExportedGObject

from mamamedia_modules import GAME_IDLE, GAME_STARTED, GAME_FINISHED, GAME_QUIT
import logging
_logger = logging.getLogger('slider-activity')


SERVICE = "org.worldwideworkshop.olpc.SliderPuzzle.Tube"
IFACE = SERVICE
PATH = "/org/worldwideworkshop/olpc/SliderPuzzle/Tube"

class GameTube (ExportedGObject):
    """ Manage the communication between cooperating activities """
    def __init__(self, tube, is_initiator, activity):
        super(GameTube, self).__init__(tube, PATH)
        self.tube = tube
        self.activity = activity
        self.add_status_update_handler()
        self.get_buddy = activity._get_buddy
        self.syncd_once = False
        if is_initiator:
            self.add_hello_handler()
            self.add_need_image_handler()
            self.activity.ui.connect('game-state-changed', self.game_state_cb)
        else:
            self.add_re_sync_handler()
            self.Hello()

        self.tube.watch_participants(self.participant_change_cb)

    def participant_change_cb(self, added, removed):
        logger.debug('Adding participants: %r', added)
        logger.debug('Removing participants: %r', removed)

    @signal(dbus_interface=IFACE, signature='')
    def Hello(self):
        """Request that this player's Welcome method is called to bring it
        up to date with the game state.
        """

    @signal(dbus_interface=IFACE, signature='')
    def NeedImage(self):
        """Player needs actual binary image.
        """

    @signal(dbus_interface=IFACE, signature='s')
    def ReSync (self, state):
        """ signal a reshufle, possibly with a new image """

    @signal(dbus_interface=IFACE, signature='sbu')
    def StatusUpdate (self, status, clock_running, ellapsed_time):
        """ signal a reshufle, possibly with a new image """
        logger.debug("Status Update to %s, %s, %i" % (status, str(clock_running), ellapsed_time))

    def add_hello_handler(self):
        self.tube.add_signal_receiver(self.hello_cb, 'Hello', IFACE,
            path=PATH, sender_keyword='sender')

    def add_need_image_handler(self):
        self.tube.add_signal_receiver(self.need_image_cb, 'NeedImage', IFACE,
            path=PATH, sender_keyword='sender')

    def add_re_sync_handler (self):
        self.tube.add_signal_receiver(self.re_sync_cb, 'ReSync', IFACE,
            path=PATH, sender_keyword='sender')

    def add_status_update_handler(self):
        self.tube.add_signal_receiver(self.status_update_cb, 'StatusUpdate', IFACE,
            path=PATH, sender_keyword='sender')

    def game_state_cb (self, obj, state):
        if state == GAME_STARTED[0]:
            self.ReSync(self.activity.frozen.freeze())

    def hello_cb(self, obj=None, sender=None):
        """Tell the newcomer what's going on."""
        logger.debug('Newcomer %s has joined', sender)
        game = self.activity.ui.game
        f = self.activity.frozen
        if sender != self.activity.get_bus_name():
            self.tube.get_object(sender, PATH).Welcome(f.freeze(), dbus_interface=IFACE)
        else:
            self.ReSync(f.freeze())
        self.activity.ui._set_control_area()

    def need_image_cb (self, sender=None):
        """Send current image to peer as binary data."""
        if self.activity.ui.get_game_state()[1] <= GAME_IDLE[1]:
            return
        logger.debug('Sending image to %s', sender)
        img = self.activity.ui.game.get_image_as_png()
        #img = file(imgfile, 'rb').read()
        #img = self.activity.ui.game.image.get_pixbuf()
        t = time.time()
        compressed = zlib.compress(img, 9)
        # We will be sending the image, 24K at a time (my tests put the high water at 48K)
        logger.debug("was %d, is %d. compressed to %d%% in %0.4f seconds" % (len(img), len(compressed), len(compressed)*100/len(img), time.time() - t))
        part_size = 24*1024
        parts = len(compressed) / part_size
        self.tube.get_object(sender, PATH).ImageSync([], 0, dbus_interface=IFACE)
        for i in range(parts+1):
            self.tube.get_object(sender, PATH).ImageSync(compressed[i*part_size:(i+1)*part_size], i+1,
                                                         dbus_interface=IFACE)
        self.tube.get_object(sender, PATH).ImageDetailsSync(self.activity.frozen.freeze(), dbus_interface=IFACE)

    def re_sync_cb (self, state, sender=None):
        # new grid and possibly image too
        if self.syncd_once:
            return
        logger.debug("resync state: '%s' (%s)" % (state, type(state)))
        self.syncd_once = self.activity.frozen.thaw(str(state), tube=self)

    def status_update_cb (self, status, clock_running, ellapsed_time, sender=None):
        to = self.tube.get_object(sender, PATH)
        
        logger.debug("Status Update from %s:  %s, %s, %i" % (sender, status, str(clock_running), ellapsed_time))

        buddy = self.get_buddy(self.tube.bus_name_to_handle[sender])
        nick, stat = self.activity.ui.buddy_panel.update_player(buddy, status, bool(clock_running), int(ellapsed_time))
        if buddy != self.activity.owner:
            self.activity.ui.set_message(
                    _("Buddy '%(buddy)s' changed status: %(status)s") % \
                        {'buddy': nick, 'status': stat},
                    frommesh=True)

    @method(dbus_interface=IFACE, in_signature='s', out_signature='')
    def Welcome(self, state):
        """ """
        logger.debug("Welcome...");
        logger.debug("state: '%s' (%s)" % (state, type(state)))
        self.activity.frozen.thaw(str(state), tube=self)

    @method(dbus_interface=IFACE, in_signature='ayn', out_signature='', byte_arrays=True)
    def ImageSync (self, image_part, part_nr):
        """ """
        logger.debug("Received image part #%d, length %d" % (part_nr, len(image_part)))
        self.activity.ui.set_message(_("Waiting for Puzzle image to be transferred..."))
        if part_nr == 1:
            self.image = StringIO()
            self.image.write(image_part)
        elif part_nr > 1:
            self.image.write(image_part)

    @method(dbus_interface=IFACE, in_signature='s', out_signature='', byte_arrays=True)
    def ImageDetailsSync (self, state):
        """ Signals end of image and shares the rest of the needed data to create the image remotely."""
        logger.debug("Receive end of image sync")
        self.syncd_once = self.activity.frozen.thaw(str(state), forced_image=zlib.decompress(self.image.getvalue()), tube=self)

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
		self.frozen = json.write(self.slider_ui._freeze(journal=False))
		#self.nr_pieces = self.slider_ui.game.get_nr_pieces()
		#self.category_path = self.slider_ui.thumb.get_image_dir()
		##self.image_path = self.slider_ui.game.filename
		##if self.slider_ui.thumb.is_myownpath():
		##	self.image_path = os.path.basename(self.image_path)
		#self.thumb_state = self.slider_ui.thumb._freeze()
		##self.image_digest = self.slider_ui.game.image_digest
		#self.game_state = self.slider_ui.game._freeze(journal=False)
		##logger.debug("sync game_state: %s" % str(self.game_state))
		##logger.debug("sync category: %s image: %s (md5: %s)" % (self.category_path, self.image_path, self.image_digest))

	def apply (self):
		""" Apply the saved state to the running game """
		self.slider_ui._thaw(json.read(self.frozen))
		#self.slider_ui.thumb._thaw(self.thumb_state)
		#self.slider_ui.set_nr_pieces(None, self.nr_pieces)
		#self.slider_ui.game._thaw(self.game_state)

	def freeze (self):
		"""return a json version of the kept data"""
		return self.frozen
		#return json.write({
		#	'nr_pieces': self.nr_pieces,
		#	#'image_path': self.image_path,
    #  'thumb_state': self.thumb_state,
		#	#'image_digest': self.image_digest,
		#	'game_state': self.game_state,
		#	})

	def thaw (self, state=None, tube=None, forced_image=None):
		""" store the previously saved state """
		try:
			self._lock = True
			#found = False
			if state is not None:
				self.frozen = state
				#state = self.freeze()
			#for k,v in json.read(state).items():
			#	if hasattr(self, k):
			#		#logger.debug("%s=%s" % (k,str(v)))
			#		setattr(self, k, v)
#			self.slider_ui.thumb._thaw(self.thumb_state)
#			self.slider_ui.set_nr_pieces(None, self.nr_pieces)
#			self.slider_ui.game._thaw(self.game_state)
			#logger.debug("thaw game_state: %s" % str(self.game_state))

			if forced_image is not None:
					self.slider_ui.game.set_image_from_str(forced_image)
					self.slider_ui.thumb.load_pb(self.slider_ui.game.image)
					self.apply()
			elif tube is not None:
					tube.NeedImage()
			else:
					self.apply()
      
			#if self.image_path:
			#	if self.image_path == os.path.basename(self.image_path):
			#		# MyOwnPath based image...
			#		#if forced_image is not None:
			#		#	name = 'image_' + self.image_path
			#		#	while os.path.exists(os.path.join(self.slider_ui.thumb.myownpath, name)):
			#		#		name = '_' + name
			#		#	f = file(os.path.join(self.slider_ui.thumb.myownpath, name), 'wb')
			#		#	f.write(forced_image)
			#		#	f.close()
			#		#	self.slider_ui.thumb.set_image_dir(os.path.join(self.slider_ui.thumb.myownpath, name))
			#		#	self.slider_ui.set_nr_pieces(None, self.nr_pieces)
			#		#	self.slider_ui.game._thaw(self.game_state)
			#		#	#logger.debug("thaw game_state: %s" % str(self.game_state))
			#		#	found = True
			#		#else:
			#		#	for link, name, digest in self.slider_ui.thumb.gather_myownpath_images():
			#		#		if digest == self.image_digest:
			#		#			logger.debug("Found the image in myownpath!")
			#		#			self.slider_ui.thumb.set_image_dir(os.path.join(self.slider_ui.thumb.myownpath, link))
			#		#			self.slider_ui.set_nr_pieces(None, self.nr_pieces)
			#		#			self.slider_ui.game._thaw(self.game_state)
			#		#			logger.debug("thaw game_state: %s" % str(self.game_state))
			#		#			found = True
			#		#			break
			#		#	if not found:
			#		logger.debug("Don't know the image, so request it")
			#		if tube is not None:
			#			tube.NeedImage()
			#	elif os.path.exists(self.image_path) and md5.new(file(self.image_path, 'rb').read()).hexdigest() == self.image_digest:
			#		logger.debug("We have the image!")
			#		self.slider_ui.thumb.set_image_dir(self.image_path)
			#		#self.slider_ui.game.load_image(self.image_path)
			#		self.slider_ui.set_nr_pieces(None, self.nr_pieces)
			#		self.slider_ui.game._thaw(self.game_state)
			#		logger.debug("thaw game_state: %s" % str(self.game_state))
			#	else:
			#		logger.debug("Don't know the image, so request it")
			#		if tube is not None:
			#			tube.NeedImage()
			#else:
			#	logger.debug("No image...")
			return True
		finally:
			self._lock = False

class SliderPuzzleActivity(Activity, TubeHelper):
    def __init__(self, handle):
        Activity.__init__(self, handle)
        logger.debug('Starting Slider Puzzle activity... %s' % str(get_bundle_path()))
        os.chdir(get_bundle_path())
        self.connect('destroy', self._destroy_cb)
        self._sample_window = None
        self.fixed = Gtk.Fixed()
        self.ui = SliderPuzzleUI(self)
        toolbar_box = ToolbarBox()
        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()
        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, -1)
        activity_button.show()

        self.btn_9 = ToolButton('play-9')
        self. btn_9.set_tooltip(_('9 blocks'))
        toolbar_box.toolbar.insert(self.btn_9, -1)
        #btn_9.set_active(True)
        self.btn_9.connect('clicked', self.ui.set_nr_pieces, 9)
        self.btn_9.show()

        self.btn_12 = ToolButton('play-12')
        self.btn_12.set_tooltip(_('12 blocks'))
        toolbar_box.toolbar.insert(self.btn_12, -1)
        #btn_9.set_active(True)
        self.btn_12.connect('clicked', self.ui.set_nr_pieces, 12)
        self.btn_12.show()

        self.btn_16 = ToolButton('play-16')
        self.btn_16.set_tooltip(_('16 blocks'))
        toolbar_box.toolbar.insert(self.btn_16, -1)
        #btn_9.set_active(True)
        self.btn_16.connect('clicked', self.ui.set_nr_pieces, 16)
        self.btn_16.show()

        self.btn_solve = ToolButton('media-playback-start')
        self.btn_solve.set_tooltip(_('Solve'))
        toolbar_box.toolbar.insert(self.btn_solve, -1)
        #btn_9.set_active(True)
        self.btn_solve.connect('clicked', self.ui.do_solve)
        self.btn_solve.show()

        self.btn_shuffle = ToolButton('edit-redo')
        self.btn_shuffle.set_tooltip(_('Shuffle'))
        toolbar_box.toolbar.insert(self.btn_shuffle, -1)
        #btn_9.set_active(True)
        self.btn_shuffle.connect('clicked', self.ui.do_shuffle)
        self.btn_shuffle.show()


        self.btn_add = ToolButton('imageviewer')
        self.btn_add.set_tooltip(_('Add Picture'))
        toolbar_box.toolbar.insert(self.btn_add, -1)
        #btn_9.set_active(True)
        self.btn_add.connect('clicked', self.ui.do_add_image)
        self.btn_add.show()

        self.btn_select = ToolButton('image-load')
        self.btn_select.set_tooltip(_('Add Picture'))
        toolbar_box.toolbar.insert(self.btn_select, -1)
        #btn_9.set_active(True)
        self.btn_select.connect('clicked', self.do_samples_cb)
        self.btn_select.show()
        
        #self.set_canvas(self.ui)
        self.set_canvas(self.fixed)
        self.fixed.show()
        
        self.show_all()

        self.frozen = FrozenState(self.ui)
        self.ui.game.connect('shuffled', self.frozen.sync)

        TubeHelper.__init__(self, tube_class=GameTube, service=SERVICE)  

    def _destroy_cb(self, data=None):
        return True

    # TubeHelper mixin stuff

    @utils.trace
    def shared_cb (self):
        self.ui.buddy_panel.add_player(self.owner)

    def joined_cb (self):
        self.ui.set_readonly()

    @utils.trace
    def new_tube_cb (self):
        self.ui.set_contest_mode(True)

    def buddy_joined_cb (self, buddy):
        nick = self.ui.buddy_panel.add_player(buddy)
        self.ui.set_message(_("Buddy '%s' joined the game!") % (nick), frommesh=True)

    def buddy_left_cb (self, buddy):
        nick = self.ui.buddy_panel.remove_player(buddy)
        self.ui.set_message(_("Buddy '%s' left the game!") % (nick), frommesh=True)

    # Journal integration
		
    def read_file(self, file_path):
        f = open(file_path, 'r')
        try:
            session_data = f.read()
        finally:
            f.close()
        #logging.debug('Trying to set session: %s.' % session_data)
        logging.debug("Setting session")
        self.ui._thaw(json.read(session_data))
        logging.debug("Done setting session")
		
    def write_file(self, file_path):
        session_data = json.write(self.ui._freeze())
        f = open(file_path, 'w')
        try:
            f.write(session_data)
        finally:
            f.close()
    def do_samples_cb(self, button):
        self._create_store()

    def _create_store(self, widget=None):
            #if self._sample_window is None:
            
            self.set_canvas(self.fixed)
            self.fixed.show()
            
            self._sample_box = Gtk.EventBox()
            self._sample_window = Gtk.ScrolledWindow()
            self._sample_window.set_policy(Gtk.PolicyType.NEVER,
                                           Gtk.PolicyType.AUTOMATIC)
            width = Gdk.Screen.width() / 2
            height = Gdk.Screen.height() / 2
            self._sample_window.set_size_request(width, height)
            self._sample_window.show()

            store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)

            icon_view = Gtk.IconView()
            icon_view.set_model(store)
            icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
            icon_view.connect('selection-changed', self._sample_selected,
                             store)
            icon_view.set_pixbuf_column(0)
            icon_view.grab_focus()
            self._sample_window.add_with_viewport(icon_view)
            icon_view.show()
            self._fill_samples_list(store)

            width = Gdk.Screen.width() / 4
            height = Gdk.Screen.height() / 4

            self._sample_box.add(self._sample_window)
            #_logger.debug('check fixed')
            self.fixed.put(self._sample_box, width, height)
            #self.ui.game_wrapper.add(self._sample_box)
            #self.fixed.show()
            #_logger.debug('fixed comp')
            self._sample_window.show()
            #_logger.debug('window comp')
            self._sample_box.show()
            #_logger.debug('box comp')
            #self.fixed.show_all()
    def _get_selected_path(self, widget, store):
        try:
            iter_ = store.get_iter(widget.get_selected_items()[0])
            image_path = store.get(iter_, 1)[0]

            return image_path, iter_
        except:
            return None

    def _sample_selected(self, widget, store):
        logger.debug('love')
        self.set_canvas(self.ui)
        self.show_all()
        logger.debug('you')
        selected = self._get_selected_path(widget, store)


        if selected is None:
            self._selected_sample = None
            self._sample_window.hide()
            return
        
        image_path, _iter = selected
        iter_ = store.get_iter(widget.get_selected_items()[0])
        image_path = store.get(iter_, 1)[0]

        self._selected_sample = image_path
        self._sample_window.hide()
        logger.debug(self._selected_sample + 'hello')
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        GObject.idle_add(self._sample_loader)

    def _sample_loader(self):
        # Convert from thumbnail path to sample path
        logger.debug('sample here')
        self.ui._set_nr_pieces_pre(self._selected_sample)
        logger.debug('sample there')
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)) 

    def _fill_samples_list(self, store):
        '''
        Append images from the artwork_paths to the store.
        '''
        for filepath in self._scan_for_samples():
            pixbuf = None
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                filepath, 100, 100)
            store.append([pixbuf, filepath])
            #_logger.debug('fill comp')
    def _scan_for_samples(self):
        path = os.path.join(get_bundle_path(), 'images')
        samples = []
        for name in os.listdir(path):
            if name.endswith(".gif"):
                samples.append(os.path.join(path, name))
        samples.sort()
        #_logger.debug('scan comp')
        return samples

    
