"""Mostly stolen from HelloMesh, which was in turn based on the Connect activity """

import logging
import telepathy
import telepathy.client
import zlib
import time
#import md5
import os
import json
from cStringIO import StringIO
# will eventually be imported from telepathy.tubes or something
from tubeconn import TubeConnection
from sugar.presence import presenceservice
import dbus

from dbus import Interface, DBusException
from dbus.service import method, signal
from dbus.gobject_service import ExportedGObject

from utils import GAME_STARTED

SERVICE = "org.worldwideworkshop.olpc.SliderPuzzle.Tube"
IFACE = SERVICE
PATH = "/org/worldwideworkshop/olpc/SliderPuzzle/Tube"

logger = logging.getLogger('SliderPuzzle-buddy_handler')

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
        logger.debug('Adding participants: %r' % added)
        logger.debug('Removing participants: %r' % type(removed))

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
        logger.debug("Resync %s" % state)

    @signal(dbus_interface=IFACE, signature='sbn')
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
        if sender:
            self.tube.get_object(sender, PATH).Welcome(f.freeze(), dbus_interface=IFACE)
        else:
            self.ReSync(f.freeze())
        self.activity.ui._set_control_area()

    def need_image_cb (self, sender=None):
        """Send current image to peer as binary data."""
        logger.debug('Sending image to %s', sender)
        imgfile = self.activity.ui.game.filename
        img = file(imgfile, 'rb').read()
        #img = self.activity.ui.game.image.get_pixbuf()
        t = time.time()
        compressed = zlib.compress(img, 9)
        # We will be sending the image, 24K at a time (my tests put the high water at 48K)
        logger.debug("was %d, is %d. compressed to %d%% in %0.4f seconds" % (len(img), len(compressed), len(compressed)*100/len(img), time.time() - t))
        part_size = 24*1024
        parts = len(compressed) / part_size
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
        logger.debug(dir(to))
        logger.debug(to.__dbus_object_path__)
#        if to.bus_name == self.tube.get_unique_name():
#            # message from myself, ignore
#            return
        
        logger.debug("Status Update from %s:  %s, %s, %i" % (sender, status, str(clock_running), ellapsed_time))
       # try:
        buddy = self.get_buddy(self.tube.bus_name_to_handle[sender])
       # except DBusException:
       #     buddy = self.activity.ui.buddy_panel.get_buddy_from_path(to.object_path)
        self.activity.ui.buddy_panel.update_player(buddy, status, bool(clock_running), int(ellapsed_time))

    @method(dbus_interface=IFACE, in_signature='s', out_signature='')
    def Welcome(self, state):
        """ """
        logger.debug("state: '%s' (%s)" % (state, type(state)))
        self.activity.frozen.thaw(str(state), tube=self)

    @method(dbus_interface=IFACE, in_signature='ayb', out_signature='', byte_arrays=True)
    def ImageSync (self, image_part, part_nr):
        """ """
        logger.debug("Received image part #%d, length %d" % (part_nr, len(image_part)))
        if part_nr == 1:
            self.image = StringIO(image_part)
        else:
            self.image.write(image_part)

    @method(dbus_interface=IFACE, in_signature='s', out_signature='', byte_arrays=True)
    def ImageDetailsSync (self, state):
        """ Signals end of image and shares the rest of the needed data to create the image remotely."""
        self.syncd_once = self.activity.frozen.thaw(str(state), forced_image=zlib.decompress(self.image.getvalue()), tube=self)
    

class TubeHelper (object):
    """HelloMesh Activity as specified in activity.info"""
    def __init__(self):
        """Set up the tubes for this activity."""

        self.pservice = presenceservice.get_instance()

        bus = dbus.Bus()
        name, path = self.pservice.get_preferred_connection()
        self.tp_conn_name = name
        self.tp_conn_path = path
        self.conn = telepathy.client.Connection(name, path)
        self.game_tube = False
        self.initiating = None
        
        self.connect('shared', self._shared_cb)

        # Buddy object for you
        owner = self.pservice.get_owner()
        self.owner = owner

        if self._shared_activity:
            # we are joining the activity
            self.connect('joined', self._joined_cb)
            self._shared_activity.connect('buddy-joined',
                                          self._buddy_joined_cb)
            self._shared_activity.connect('buddy-left',
                                          self._buddy_left_cb)
            if self.get_shared():
                # we've already joined
                self._joined_cb()

    def _shared_cb(self, activity):
        logger.debug('My activity was shared')
        self.initiating = True
        self.ui.buddy_panel.add_player(self.owner)
        self._setup()

        for buddy in self._shared_activity.get_joined_buddies():
            pass  # Can do stuff with newly acquired buddies here

        self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self._shared_activity.connect('buddy-left', self._buddy_left_cb)

        logger.debug('This is my activity: making a tube...')
        id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferTube(
            telepathy.TUBE_TYPE_DBUS, SERVICE, {})

    # FIXME: presence service should be tubes-aware and give us more help
    # with this
    def _setup(self):
        if self._shared_activity is None:
            logger.error('Failed to share or join activity')
            return

        bus_name, conn_path, channel_paths =\
            self._shared_activity.get_channels()

        # Work out what our room is called and whether we have Tubes already
        room = None
        tubes_chan = None
        text_chan = None
        for channel_path in channel_paths:
            channel = telepathy.client.Channel(bus_name, channel_path)
            htype, handle = channel.GetHandle()
            if htype == telepathy.HANDLE_TYPE_ROOM:
                logger.debug('Found our room: it has handle#%d "%s"',
                    handle, self.conn.InspectHandles(htype, [handle])[0])
                room = handle
                ctype = channel.GetChannelType()
                if ctype == telepathy.CHANNEL_TYPE_TUBES:
                    logger.debug('Found our Tubes channel at %s', channel_path)
                    tubes_chan = channel
                elif ctype == telepathy.CHANNEL_TYPE_TEXT:
                    logger.debug('Found our Text channel at %s', channel_path)
                    text_chan = channel

        if room is None:
            logger.error("Presence service didn't create a room")
            return
        if text_chan is None:
            logger.error("Presence service didn't create a text channel")
            return

        # Make sure we have a Tubes channel - PS doesn't yet provide one
        if tubes_chan is None:
            logger.debug("Didn't find our Tubes channel, requesting one...")
            tubes_chan = self.conn.request_channel(telepathy.CHANNEL_TYPE_TUBES,
                telepathy.HANDLE_TYPE_ROOM, room, True)

        self.tubes_chan = tubes_chan
        self.text_chan = text_chan

        tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal('NewTube',
            self._new_tube_cb)

    def _list_tubes_reply_cb(self, tubes):
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        if not self._shared_activity:
            return

        for buddy in self._shared_activity.get_joined_buddies():
            self._buddy_joined_cb(self, buddy)

        logger.debug('Joined an existing shared activity')
        self.ui.set_readonly()
        self.initiating = False
        self._setup()

        logger.debug('This is not my activity: waiting for a tube...')
        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
            reply_handler=self._list_tubes_reply_cb,
            error_handler=self._list_tubes_error_cb)

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        logger.debug('New tube: ID=%d initator=%d type=%d service=%s '
                     'params=%r state=%d', id, initiator, type, service,
                     params, state)

        if (type == telepathy.TUBE_TYPE_DBUS and
            service == SERVICE):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptTube(id)

            tube_conn = TubeConnection(self.conn,
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES],
                id, group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])

            logger.debug("creating game tube")
            self.game_tube = GameTube(tube_conn, self.initiating, self)
            self.ui.set_contest_mode(True)

    def _get_buddy(self, cs_handle):
        """Get a Buddy from a channel specific handle."""
        logger.debug('Trying to find owner of handle %u...', cs_handle)
        group = self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP]
        my_csh = group.GetSelfHandle()
        logger.debug('My handle in that group is %u', my_csh)
        if my_csh == cs_handle:
            handle = self.conn.GetSelfHandle()
            logger.debug('CS handle %u belongs to me, %u', cs_handle, handle)
        else:
            handle = group.GetHandleOwners([cs_handle])[0]
            logger.debug('CS handle %u belongs to %u', cs_handle, handle)

            # XXX: deal with failure to get the handle owner
            assert handle != 0

        # XXX: we're assuming that we have Buddy objects for all contacts -
        # this might break when the server becomes scalable.
        return self.pservice.get_buddy_by_telepathy_handle(self.tp_conn_name,
                self.tp_conn_path, handle)

    def _buddy_joined_cb (self, activity, buddy):
        logger.debug('Buddy %s joined' % buddy.props.nick)
        self.ui.buddy_panel.add_player(buddy)

    def _buddy_left_cb (self, activity, buddy):
        logger.debug('Buddy %s left' % buddy.props.nick)
        self.ui.buddy_panel.remove_player(buddy)
