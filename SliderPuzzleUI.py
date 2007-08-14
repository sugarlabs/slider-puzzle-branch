#!/usr/bin/env python

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


### SliderPuzzeUI
### TODO: Describe
### $Id: $
###
### author: Carlos Neves (cn (at) sueste.net)
### (c) 2007 World Wide Workshop Foundation

import pygtk
pygtk.require('2.0')
import gtk, gobject, pango

from utils import load_image, SliderCreator, GAME_IDLE, GAME_STARTED, GAME_FINISHED, GAME_QUIT
#from buddy_handler import BuddyPanel
from mamamedia_ui import NotebookReaderWidget, BorderFrame, BORDER_ALL_BUT_BOTTOM, BORDER_ALL_BUT_LEFT
#from toolbar import SliderToolbar
from i18n import LanguageComboBox
import locale

import logging
from glob import glob
from SliderPuzzleWidget import SliderPuzzleWidget
from time import time
import os
import md5

try:
    from sugar.activity import activity
    from sugar.graphics import units
    _inside_sugar = True
except:
    _inside_sugar = False


SLICE_BTN_WIDTH = 50

THUMB_SIZE = 48
IMAGE_SIZE = 200
#GAME_SIZE = 294
GAME_SIZE = 564

MYOWNPIC_FOLDER = os.path.expanduser("~/.sugar/default/org.worldwideworkshop.olpc.SliderPuzzle.MyOwnPictures")
# Colors from Rich's UI design

COLOR_FRAME_OUTER = "#B7B7B7"
COLOR_FRAME_GAME = "#FF0099"
COLOR_FRAME_THUMB = COLOR_FRAME_GAME
COLOR_FRAME_CONTROLS = "#FFFF00"
COLOR_BG_CONTROLS = "#66CC00"
COLOR_FG_BUTTONS = (
    (gtk.STATE_NORMAL,"#CCFF99"),
    (gtk.STATE_ACTIVE,"#CCFF99"),
    (gtk.STATE_PRELIGHT,"#CCFF99"),
    (gtk.STATE_SELECTED,"#CCFF99"),
    (gtk.STATE_INSENSITIVE,"#CCFF99"),
    )
COLOR_BG_BUTTONS = (
    (gtk.STATE_NORMAL,"#027F01"),
    (gtk.STATE_ACTIVE,"#014D01"),
    (gtk.STATE_PRELIGHT,"#016D01"),
    (gtk.STATE_SELECTED,"#027F01"),
    (gtk.STATE_INSENSITIVE,"#027F01"),
    )

def prepare_btn(btn, w=-1, h=-1):
    for state, color in COLOR_BG_BUTTONS:
        btn.modify_bg(state, gtk.gdk.color_parse(color))
    c = btn.get_child()
    if c is not None:
        for state, color in COLOR_FG_BUTTONS:
            c.modify_fg(state, gtk.gdk.color_parse(color))
    else:
        for state, color in COLOR_FG_BUTTONS:
            btn.modify_fg(state, gtk.gdk.color_parse(color))
    if w>0 or h>0:
        btn.set_size_request(w, h)
    return btn


class TimerWidget (gtk.HBox):
    __gsignals__ = {'timer_toggle' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (bool,)),}
    def __init__ (self, bg_color="#DD4040", fg_color="#4444FF", lbl_color="#DD4040"):
        gtk.HBox.__init__(self)
        self.counter = gtk.EventBox()
        self.counter.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(bg_color))
        self.counter.set_size_request(90, -1)
        hb = gtk.HBox()
        self.counter.add(hb)
        self.lbl_time = gtk.Label()
        self.lbl_time.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(lbl_color))
        self.pack_start(self.lbl_time, False)
        self.time_label = gtk.Label("--:--")
        self.time_label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(fg_color))
        hb.pack_start(self.time_label, False, False, 5)
        self.prepare_icons()
        self.icon = gtk.Image()
        self.icon.set_from_pixbuf(self.icons[1])
        hb.pack_end(self.icon, False, False, 5)
        self.pack_start(self.counter, False)
        self.connect("button-press-event", self.process_click)
        self.start_time = 0
        self.timer_id = None
        self.finished = False

    def set_label (self, label):
        self.lbl_time.set_label(label)

    def prepare_icons (self):
        self.icons = []
        self.icons.append(load_image("icons/circle-x.svg"))
        self.icons.append(load_image("icons/circle-check.svg"))

    def modify_bg(self, state, color):
        self.foreach(lambda x: x is not self.counter and x.modify_bg(state, color))

    def reset (self, auto_start=True):
        self.set_sensitive(True)
        self.finished = False
        self.stop()
        self.start_time = 0
        if auto_start:
            self.start()

    def start (self):
        if self.finished:
            return
        self.icon.set_from_pixbuf(self.icons[0])
        if self.start_time is None:
            self.start_time = time()
        else:
            self.start_time = time() - self.start_time
        self.do_tick()
        if self.timer_id is None:
            self.timer_id = gobject.timeout_add(1000, self.do_tick)
        self.emit('timer_toggle', True)

    def stop (self, finished=False):
        self.icon.set_from_pixbuf(self.icons[1])
        if self.timer_id is not None:
            gobject.source_remove(self.timer_id)
            self.timer_id = None
            self.start_time = time() - self.start_time
        if not finished:
            self.time_label.set_text("--:--")
        else:
            self.finished = True
        self.emit('timer_toggle', False)
        
    def process_click (self, btn, event):
        if self.timer_id is None:
            self.start()
        else:
            self.stop()

    def is_running (self):
        return self.timer_id is not None

    def ellapsed (self):
        if self.is_running():
            return time() - self.start_time
        else:
            return self.start_time

    def is_reset (self):
        return not self.is_running() and self.start_time == 0

    def do_tick (self):
        t = time() - self.start_time
        if t > 5999:
            # wrap timer
            t = 0
            self.start_time = time()
        self.time_label.set_text("%0.2i:%0.2i" % (t/60, t%60))
        return True

    def _freeze (self):
        return (self.start_time, time(), self.finished, self.timer_id is None)

    def _thaw (self, obj):
        self.start_time, t, finished, stopped = obj
        if self.start_time is not None:
            if not stopped:
                self.start_time = t - self.start_time
                self.start()
                return
            self.start_time = time() - self.start_time
            self.do_tick()
        self.stop(finished)
                
class CategoryDirectory (object):
    def __init__ (self, path, width=-1, height=-1):
        self.path = path
        if os.path.isdir(path):
            self.gather_images()
        else:
            self.images = [path]
        self.set_thumb_size(THUMB_SIZE, THUMB_SIZE)
        self.set_image_size(width, height)
        self.filename = None
        self.name = os.path.basename(path)

    def gather_images (self):
        """ Lists all images in the selected path as per the wildcard expansion of 'image_*'.
        Adds all linked images from files (*.lnk) """
        self.images = []
        links = glob(os.path.join(self.path, "*.lnk"))
        for link in links:
            fpath = file(link).readlines()[0].strip()
            if os.path.isfile(fpath) and not (fpath in self.images):
                self.images.append(fpath)
            else:
                os.remove(link)
        self.images.extend(glob(os.path.join(self.path, "image_*")))
        self.images.sort()

    def set_image_size (self, w, h):
        self.width = w
        self.height = h

    def set_thumb_size (self, w, h):
        self.twidth = w
        self.theight = h
        self.thumb = self._get_category_thumb()

    def get_image (self, name):
        if not len(self.images) or name is None or name not in self.images:
            return None
        self.filename = name
        return load_image(self.filename, self.width, self.height)

    def get_next_image (self):
        if not len(self.images):
            return None
        if self.filename is None or self.filename not in self.images:
            pos = -1
        else:
            pos = self.images.index(self.filename)
        pos += 1
        if pos >= len(self.images):
            pos = 0
        return self.get_image(self.images[pos])

    def get_previous_image (self):
        if not len(self.images):
            return None
        if self.filename is None or self.filename not in self.images:
            pos = len(self.images)
        else:
            pos = self.images.index(self.filename)
        pos -= 1
        if pos < 0:
            pos = len(self.images) - 1
        return self.get_image(self.images[pos])

    def has_images (self):
        return len(self.images) > 0

    def count_images (self):
        return len(self.images)

    def has_image (self):
        return self.filename is not None

    def _get_category_thumb (self):
        if os.path.isdir(self.path):
            thumbs = glob(os.path.join(self.path, "thumb.*"))
            thumbs.extend(glob("images/default_thumb.*"))
            thumbs = filter(lambda x: os.path.exists(x), thumbs)
            thumbs.append(None)
        else:
            thumbs = [self.path]
        return load_image(thumbs[0], self.twidth, self.theight)
    

class ImageSelectorWidget (gtk.Table):
    __gsignals__ = {'category_press' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
                    'image_press' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),}

    def __init__ (self, width=-1, height=-1, frame_color=None):
        gtk.Table.__init__(self, 2,5,False)
        self._signals = []
        self.width = width
        self.height = height
        self.image = gtk.Image()
        self.myownpath = None
        img_box = BorderFrame(border_color=frame_color)
        img_box.add(self.image)
        img_box.set_border_width(5)
        self._signals.append((img_box, img_box.connect('button_press_event', self.emit_image_pressed)))
        self.attach(img_box, 0,5,0,1,0,0)
        self.attach(gtk.Label(), 0,1,1,2)
        self.bl = gtk.Button()

        il = gtk.Image()
        il.set_from_pixbuf(load_image('icons/arrow_left.png'))
        self.bl.set_image(il)

        self.bl.connect('clicked', self.previous)
        self.attach(prepare_btn(self.bl), 1,2,1,2,0,0)

        cteb = gtk.EventBox()
        self.cat_thumb = gtk.Image()
        self.cat_thumb.set_size_request(THUMB_SIZE, THUMB_SIZE)
        cteb.add(self.cat_thumb)
        self._signals.append((cteb, cteb.connect('button_press_event', self.emit_cat_pressed)))
        self.attach(cteb, 2,3,1,2,0,0,xpadding=10)
        
        self.br = gtk.Button()
        ir = gtk.Image()
        ir.set_from_pixbuf(load_image('icons/arrow_right.png'))
        self.br.set_image(ir)
        self.br.connect('clicked', self.next)
        self.attach(prepare_btn(self.br), 3,4,1,2,0,0)
        self.attach(gtk.Label(),4,5,1,2)
        self.filename = None
        self.show_all()
        self.image.set_size_request(width, height)

    def set_readonly (self, ro=True):
        if ro:
            self.bl.hide()
            self.br.hide()
            for w, s in self._signals:
                w.handler_block(s)

    def set_myownpath (self, path):
        """ Sets the path to My Own Pictures storage, so we know where to add links to new pictures """
        if not os.path.exists(path):
            os.mkdir(path)
        self.myownpath = path

    def is_myownpath (self):
        """ Checks current path against the set custom image path """
        return self.myownpath == self.category.path

    def gather_myownpath_images(self):
        """ """
        rv = []
        self.images = []
        links = glob(os.path.join(self.myownpath, "*.lnk"))
        for link in links:
            linfo = filter(None, map(lambda x: x.strip(), file(link).readlines()))
            fpath = linfo[0]
            if os.path.isfile(fpath) and not (fpath in self.images):
                self.images.append(fpath)
                if len(linfo) > 1:
                    digest = linfo[1]
                else:
                    digest = md5.new(file(fpath, 'rb').read()).hexdigest()
                rv.append((link, fpath, digest))
        for fpath in glob(os.path.join(self.myownpath, "image_*")):
            digest = md5.new(file(fpath, 'rb').read()).hexdigest()
            rv.append((fpath, fpath, digest))
        return rv

    def emit_cat_pressed (self, *args):
        self.emit('category_press')
        return True

    def emit_image_pressed (self, *args):
        self.emit('image_press')
        return True

    def has_image (self):
        return self.category.has_image()

    def get_category_name (self):
        return self.category.name

    def get_filename (self):
        return self.category.filename

    def next (self, *args, **kwargs):
        self.image.set_from_pixbuf(self.category.get_next_image())

    def previous (self, *args, **kwargs):
        self.image.set_from_pixbuf(self.category.get_previous_image())

    def get_image_dir (self):
        return self.category.path

    def set_image_dir (self, directory):
        if os.path.exists(directory) and not os.path.isdir(directory):
            filename = directory
            directory = os.path.dirname(directory)
            logging.debug("dir=%s, filename=%s" % (directory, filename))
        else:
            logging.debug("dir=%s" % (directory))
            filename = None
        self.category = CategoryDirectory(directory, self.width, self.height)
        self.cat_thumb.set_from_pixbuf(self.category.thumb)
        if filename:
            self.image.set_from_pixbuf(self.category.get_image(filename))
        else:
            if self.category.has_images():
                self.next()

    def load_image(self, filename):
        """ Loads an image from the file """
        if self.myownpath is not None and os.path.isdir(self.myownpath):
            name = os.path.splitext(os.path.basename(filename))[0]
            while os.path.exists(os.path.join(self.myownpath, '%s.lnk' % name)):
                name = name + '_'
            f = file(os.path.join(self.myownpath, '%s.lnk' % name), 'w')
            f.write(filename)
            image_digest = md5.new(file(filename, 'rb').read()).hexdigest()
            f.write('\n%s' % image_digest)
            f.close()
            self.category = CategoryDirectory(self.myownpath, self.width, self.height)
            self.image.set_from_pixbuf(self.category.get_image(filename))
        else:
            self.category = CategoryDirectory(filename, self.width, self.height)
            self.next()
        self.cat_thumb.set_from_pixbuf(self.category.thumb)
        return self.image.get_pixbuf() is not None

    def set_game_widget(self, game_widget):
        if self.has_image():
            game_widget.load_image(self.get_filename())

    def _freeze (self):
        """ returns a json writable object representation capable of being used to restore our current status """
        return {'image_dir': self.get_image_dir(),
                'filename': self.get_filename()}

    def _thaw (self, obj):
        """ retrieves a frozen status from a python object, as per _freeze """
        self.set_image_dir(obj.get('image_dir', None))
        self.image.set_from_pixbuf(self.category.get_image(obj.get('filename', None)))

class CategorySelector (gtk.ScrolledWindow):
    __gsignals__ = {'selected' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,))}
    
    def __init__ (self, path, title=None, selected_category_path=None):
        gtk.ScrolledWindow.__init__ (self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.path = path
        self.thumbs = []
        model, selected = self.get_model(path, selected_category_path)
        self.ignore_first = selected is not None
        
        self.treeview = gtk.TreeView()
        col = gtk.TreeViewColumn(title)
        r1 = gtk.CellRendererPixbuf()
        r2 = gtk.CellRendererText()
        col.pack_start(r1, False)
        col.pack_start(r2, True)
        col.set_cell_data_func(r1, self.cell_pb)
        col.set_attributes(r2, text=1)
        self.treeview.append_column(col)
        self.treeview.set_model(model)

        self.add(self.treeview)
        self.show_all()
        if selected is not None:
            self.treeview.get_selection().select_path(selected)
        self.treeview.connect("cursor-changed", self.do_select)

    def grab_focus (self):
        self.treeview.grab_focus()

    def cell_pb (self, tvcolumn, cell, model, it):
        # Renders a pixbuf stored in the thumbs cache
        cell.set_property('pixbuf', self.thumbs[model.get_value(it, 2)])

    def get_pb (self, path):
        thumbs = glob(os.path.join(path, "thumb.*"))
        thumbs.extend(glob(os.path.join(self.path, "default_thumb.*")))
        thumbs = filter(lambda x: os.path.exists(x), thumbs)
        thumbs.append(None)
        return load_image(thumbs[0], THUMB_SIZE, THUMB_SIZE)

    def get_model (self, path, selected_path):
        # Each row is (path/dirname, pretty name, 0 based index)
        selected = None
        store = gtk.ListStore(str, str, int)
        store.set_sort_column_id(1, gtk.SORT_ASCENDING)
        files = [os.path.join(path, x) for x in os.listdir(path) if not x.startswith('.')]
        for fullpath, prettyname in [(x, _(os.path.basename(x))) for x in files if os.path.isdir(x)]:
            count = CategoryDirectory(fullpath).count_images()
            store.append([fullpath, prettyname + (" (%i)" % count), len(self.thumbs)])
            self.thumbs.append(self.get_pb(fullpath))
        if os.path.isdir(MYOWNPIC_FOLDER):
            count = CategoryDirectory(MYOWNPIC_FOLDER).count_images()
            store.append([MYOWNPIC_FOLDER, _("My Pictures") + (" (%i)" % count), len(self.thumbs)])
            self.thumbs.append(self.get_pb(MYOWNPIC_FOLDER))

        i = store.get_iter_first()
        while i:
            if selected_path == store.get_value(i, 0):
                selected = store.get_path(i)
                break
            i = store.iter_next(i)
        return store, selected

    def do_select (self, tree, *args, **kwargs):
        if self.ignore_first:
            self.ignore_first = False
        else:
            tv, it = tree.get_selection().get_selected()
            self.emit("selected", tv.get_value(it,0))

class BuddyPanel (gtk.ScrolledWindow):
    def __init__ (self):
        super(BuddyPanel, self).__init__()
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.model = gtk.ListStore(str, str, str)
        self.model.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.treeview = gtk.TreeView()

        col = gtk.TreeViewColumn(_("Buddy"))
        r = gtk.CellRendererText()
        col.pack_start(r, True)
        col.set_attributes(r, text=0)
        self.treeview.append_column(col)

        col = gtk.TreeViewColumn(_("Status"))
        r = gtk.CellRendererText()
        col.pack_start(r, True)
        col.set_attributes(r, text=1)
        self.treeview.append_column(col)

        col = gtk.TreeViewColumn(_("Play Time"))
        r = gtk.CellRendererText()
        col.pack_start(r, True)
        col.set_attributes(r, text=2)
        self.treeview.append_column(col)
        
        self.treeview.set_model(self.model)

        self.add(self.treeview)
        self.show_all()

        self.players = {}

    def add_player (self, buddy):
        """Since the current target build (432) does not fully support the contest mode, we are removing this for now. """
        return
        #op = buddy.object_path()
        #if self.players.get(op) is not None:
        #    return
        #
        #nick = buddy.props.nick
        #if not nick:
        #    nick = ""
        #self.players[op] = (buddy, self.model.append([nick, _('synchronizing'), '']))
        
    def update_player (self, buddy, status, clock_running, time_ellapsed):
        """Since the current target build (432) does not fully support the contest mode, we are removing this for now. """
        return
        #op = buddy.object_path()
        #if self.players.get(op, None) is None:
        #    return
        #print self.players[op]
        #if status == GAME_STARTED[1]:
        #    stat = clock_running and _("Playing") or _("Paused")
        #elif status == GAME_FINISHED[1]:
        #    stat = _("Finished")
        #elif status == GAME_QUIT[1]:
        #    stat = _("Gave up")
        #else:
        #    stat = _("Unknown")
        #self.model.set_value(self.players[op][1], 1, stat)
        #self.model.set_value(self.players[op][1], 2, _("%i minutes") % (time_ellapsed/60))
        
    def get_buddy_from_path (self, object_path):
        logging.debug("op = " + object_path)
        logging.debug(self.players)
        return self.players.get(object_path, None)
        
    def remove_player (self, buddy):
        pass
    
class SliderPuzzleUI (gtk.Table):
    __gsignals__ = {'game-state-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (int,))}
    
    def __init__(self, parent):
        super(SliderPuzzleUI, self).__init__(3,3,False)
        self.set_name('ui')
        self._state = GAME_IDLE
        # Add our own icons here, needed for the translation flags
        theme = gtk.icon_theme_get_default()
        theme.append_search_path(os.path.join(os.getcwd(), 'icons'))
        logging.debug("GTK Theme path: %s" % (str(gtk.icon_theme_get_default().get_search_path())))

        # We want the translatables to be detected but not yet translated
        global _
        _ = lambda x: x
        self.labels_to_translate = []

        # Basic window settings
        self._parent = parent
        bgcolor = gtk.gdk.color_parse("#DDDD40")

        # The containers we will use
        outer_box = BorderFrame(border_color=COLOR_FRAME_OUTER)
        inner_table = gtk.Table(2,2,False)
        controls_vbox = gtk.VBox(False)
        self.game_box = BorderFrame(border_color=COLOR_FRAME_GAME)
        
        outer_box.add(inner_table)
        inner_table.attach(controls_vbox, 0,1,0,1)
        inner_table.attach(self.game_box, 1,2,0,1,1,1)

        # Logo image
        img_logo = gtk.Image()
        img_logo.set_from_file("icons/logo.png")
        img_logo.show()
        controls_vbox.pack_start(img_logo, False)

        # Left side containers
        controls_area_1 = BorderFrame(border=BORDER_ALL_BUT_BOTTOM,
                                      bg_color=COLOR_BG_CONTROLS,
                                      border_color=COLOR_FRAME_CONTROLS)

        controls_area_box = gtk.VBox(False)
        #controls_area_1_box = gtk.VBox(False)
        controls_area = gtk.VBox()
        controls_vbox.pack_start(controls_area_1)
        controls_area_1.add(controls_area)
        controls_area.pack_start(controls_area_box, padding=5)
        
        # Slice buttons
        spacer = gtk.Label()
        spacer.set_size_request(-1, 15)
        controls_area_box.pack_start(spacer, expand=False, fill=False)
        cutter = gtk.HBox(False, 8)
        cutter.pack_start(gtk.Label(), True)
        self.btn_9 = prepare_btn(gtk.ToggleButton("9"),SLICE_BTN_WIDTH)
        self.btn_9.set_active(True)
        self.btn_9.connect("clicked", self.set_nr_pieces, 9)
        cutter.pack_start(self.btn_9, False, False)
        self.btn_12 = prepare_btn(gtk.ToggleButton("12"), SLICE_BTN_WIDTH)
        self.btn_12.connect("clicked", self.set_nr_pieces, 12)
        cutter.pack_start(self.btn_12, False, False)
        self.btn_16 = prepare_btn(gtk.ToggleButton("16"), SLICE_BTN_WIDTH)
        self.btn_16.connect("clicked", self.set_nr_pieces, 16)
        cutter.pack_start(self.btn_16, False, False)
        cutter.pack_start(gtk.Label(), True)
        controls_area_box.pack_start(cutter, True)
        spacer = gtk.Label()
        spacer.set_size_request(-1, 10)
        controls_area_box.pack_start(spacer, expand=False, fill=False)

        # The image selector with thumbnail
        self.thumb = ImageSelectorWidget(IMAGE_SIZE, IMAGE_SIZE, frame_color=COLOR_FRAME_THUMB)
        self.thumb.set_image_dir("images")
        self.thumb.set_myownpath(MYOWNPIC_FOLDER)
        self.thumb.connect("category_press", self.do_select_category)
        self.thumb.connect("image_press", self.set_nr_pieces)
        controls_area_box.pack_start(self.thumb, False)

        spacer = gtk.Label()
        spacer.set_size_request(-1, 5)
        controls_area_box.pack_start(spacer, expand=False, fill=False)

        # The game control buttons
        btn_box = gtk.Table(3,3,False)
        btn_box.set_row_spacings(2)
        btn_box.attach(gtk.Label(), 0,1,0,3)
        btn_box.attach(gtk.Label(), 2,3,0,3)
        self.btn_solve = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append([self.btn_solve, _("Solve")])
        self.btn_solve.connect("clicked", self.do_solve)
        btn_box.attach(self.btn_solve, 1,2,0,1,0,0)
        self.btn_shuffle = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append([self.btn_shuffle, _("Shuffle")])
        self.btn_shuffle.connect("clicked", self.do_shuffle)
        btn_box.attach(self.btn_shuffle, 1,2,1,2,0,0)
        self.btn_add = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append([self.btn_add, _("My Picture")])
        self.btn_add.connect("clicked", self.do_add_image)
        btn_box.attach(self.btn_add, 1,2,2,3,0,0)
        controls_area_box.pack_start(btn_box, False)

        spacer = gtk.Label()
        spacer.set_size_request(-1, 1)
        controls_area_box.pack_start(spacer, expand=True, fill=True)

        # Language Selection dropdown
        controls_area_2 = BorderFrame(bg_color=COLOR_BG_CONTROLS, border_color=COLOR_FRAME_CONTROLS)
        vbox = gtk.VBox(False)
        btn_box = gtk.HBox(False)
        btn_box.pack_start(gtk.Label(), True)
        lang_combo = prepare_btn(LanguageComboBox())

        btn_box.pack_start(lang_combo, False)
        btn_box.pack_start(gtk.Label(), True)
        vbox.pack_start(btn_box, padding=8)
        controls_area_2.add(vbox)
        inner_table.attach(controls_area_2, 0,1,1,2)

        # The actual game widget
        self.game = SliderPuzzleWidget(9, GAME_SIZE, GAME_SIZE)
        self.game.show()
        self.game.connect("solved", self.do_solve)
        self.game.connect("moved", self.slider_move_cb)
        self._parent.connect("key_press_event",self.game.process_key)
        self._parent.connect("key_press_event",self.process_key)
        self.game_box.add(self.game)

        # The timer widget and lesson plans
        controls_area_3 = BorderFrame(border=BORDER_ALL_BUT_LEFT,
                                      bg_color=COLOR_BG_CONTROLS,
                                      border_color=COLOR_FRAME_CONTROLS)
        vbox = gtk.VBox(False)
        btn_box = gtk.HBox(False)
        self.timer = TimerWidget(bg_color=COLOR_BG_BUTTONS[0][1],
                                 fg_color=COLOR_FG_BUTTONS[0][1],
                                 lbl_color=COLOR_BG_BUTTONS[1][1])
        self.timer.set_sensitive(False)
        #self.timer.modify_bg(gtk.STATE_NORMAL, bgcolor)
        self.timer.set_border_width(3)
        self.labels_to_translate.append((self.timer, _("Time: ")))
        btn_box.pack_start(self.timer, False, padding=8)
        
        btn_box.pack_start(gtk.Label(), True)
        self.btn_lesson = prepare_btn(gtk.Button(" "))
        self.labels_to_translate.append([self.btn_lesson, _("Lesson Plans")])
        self.btn_lesson.connect("clicked", self.do_lesson_plan)
        btn_box.pack_start(self.btn_lesson, False, padding=8)
        vbox.pack_start(btn_box, padding=8)
        controls_area_3.add(vbox)
        inner_table.attach(controls_area_3, 1,2,1,2)
        
#        buddybox = BuddyPanel(parent)
#        buddybox.show()
        # This has the sole purpose of centering the widget on screen
#        self.attach(buddybox, 0,3,0,1)
        self.attach(gtk.Label(), 0,3,0,1)
        self.attach(outer_box, 1,2,1,2,0,0)
        self.msg_label = gtk.Label()
        self.msg_label.show()
        self.attach(self.msg_label, 0,3,2,3)

        if not parent._shared_activity:
            self.do_select_category(self)
        else:
            self.set_message(_("Waiting for remote game..."))

        # Push the gettext translator into the global namespace
        del _
        lang_combo.connect('changed', self.do_select_language)
        lang_combo.install()
        self.do_select_language(lang_combo)

        self.buddy_panel = BuddyPanel()
        self.buddy_panel.show()
        self.timer.connect('timer_toggle', self.timer_toggle_cb)

        
        #self.controls_area.pack_start(self.contest_controls_area_box, padding=5)
        # Contest mode flags
        self.set_contest_mode(False)

    def set_message (self, msg):
        self.msg_label.set_label(msg)

    def is_initiator (self):
        return self._parent.initiating

    def set_readonly (self, ro=True):
        """ Since the current target build (432) does not fully support the contest mode, we are removing this for now."""
        return
        #self.thumb.set_readonly(ro)
        #for b in (self.btn_9, self.btn_12, self.btn_16):
        #    if not b.get_active():
        #        b.set_sensitive(False)

    def timer_toggle_cb (self, evt, running):
        logging.debug("Timer running: %s" % str(running))
        if self._contest_mode and running:
            self.set_game_state(GAME_STARTED)
        self._send_status_update()
#        if self._contest_mode:
#            if running:
#                if self.game.filename and not self.game.get_parent():
#                    self.game_box.pop()
#            else:
#                if not self.buddy_panel.get_parent():
#                    self.game_box.push(self.buddy_panel)

    def _set_control_area (self, *args):
        """ The controls area below the logo needs different actions when in contest mode,
        and also if we are the contest initiators or not. """
        if self._contest_mode:
            if self.get_game_state() > GAME_IDLE:
                self.set_readonly()
            else:
                if self.is_initiator():
                    if self.timer.is_reset():
                        self.set_message(_("Select image to share..."))
                    else:
                        self.set_game_state(GAME_STARTED)
                else:
                    self.set_message(_("Waiting for game image..."))
                    #self.set_button_translation(self.btn_add, "Buddies")
                    #self.btn_add.get_child().set_label(_("Buddies"))

    def set_game_state (self, state, force=False):
        if state[0] > self._state[0] or force:
            self._state = state
            self.emit('game-state-changed', state[0])
            self._set_control_area()
            if state == GAME_STARTED:
                self.set_message("")#_("Game Started!"))
                #self.set_button_translation(self.btn_add, "Buddies")
                #self.btn_add.get_child().set_label(_("Buddies"))
            self._send_status_update()

    def get_game_state (self):
        return self._state

    def set_button_translation (self, btn, translation):
        for i in range(len(self.labels_to_translate)):
            if self.labels_to_translate[i][0] == btn:
                self.labels_to_translate[i][1] = translation
                break

    def set_contest_mode (self, mode):
        if getattr(self, '_contest_mode', None) != mode:
            self._contest_mode = bool(mode)
            self._set_control_area()
            #if self._contest_mode:
            #    self.set_button_translation(self.btn_solve, "Give Up")
            #    self.btn_solve.get_child().set_label(_("Give Up"))
            #    self.set_button_translation(self.btn_shuffle, "Start Game")
            #    self.btn_shuffle.get_child().set_label(_("Start Game"))
        
    def is_contest_mode (self):
        return self._contest_mode and self.game.filename

    def do_select_language (self, combo, *args):
        self.selected_lang_details = combo.translations[combo.get_active()]
        self.refresh_labels()

    def refresh_labels (self, first_time=False):
        self._parent.set_title(_("Slider Puzzle Activity"))
        for lbl in self.labels_to_translate:
            if isinstance(lbl[0], gtk.Button):
                lbl[0].get_child().set_label(_(lbl[1]))
            else:
                lbl[0].set_label(_(lbl[1]))
        if not self.game.get_parent() and not first_time:
            self.game_box.pop()
            if isinstance(self.game_box.get_child(), NotebookReaderWidget):
                m = self.do_lesson_plan
            else:
                m = self.do_select_category
            m(self)

    def set_nr_pieces (self, btn, nr_pieces=None):
        if isinstance(btn, gtk.ToggleButton) and not btn.get_active():
            return
        if self.is_contest_mode() and isinstance(btn, gtk.ToggleButton) and nr_pieces == self.game.get_nr_pieces():
            return
        if isinstance(btn, gtk.ToggleButton):
            if not btn.get_active():
                if nr_pieces == self.game.get_nr_pieces():
                    btn.set_active(True)
                return
        if nr_pieces is None:
            nr_pieces = self.game.get_nr_pieces()
        if btn is None: #not isinstance(btn, gtk.ToggleButton):
            self.set_game_state(GAME_STARTED)
            for n, b in ((9, self.btn_9),(12, self.btn_12),(16, self.btn_16)):
                if n == nr_pieces and not b.get_active():
                    b.set_sensitive(True)
                    b.set_active(True)
                    return
        if self.thumb.has_image():
            if not self.game.get_parent():
                self.game_box.pop()
            self.thumb.set_game_widget(self.game)
            self.game.set_nr_pieces(nr_pieces)
            self.timer.reset(False)
        if isinstance(btn, gtk.ToggleButton):
            for n, b in ((9, self.btn_9),(12, self.btn_12),(16, self.btn_16)):
                if b is not btn:
                    b.set_active(False)
                    #b.set_sensitive(not self._contest_mode)

    def do_shuffle (self, *args, **kwargs):
        if 0 and self._contest_mode:
            if self.get_game_state() > GAME_IDLE:
                # Restart
                self.set_game_state(GAME_STARTED, True)
                self._parent.frozen.thaw()
                self.timer.reset(True)
            elif self.game.filename is not None and self.timer.is_reset():
                # Start
                self.timer.start()
        elif self.thumb.has_image():
            if not self.game.get_parent():
                self.game_box.pop()
            self.thumb.set_game_widget(self.game)
            self.game.randomize()
            self.timer.reset(False)

    def slider_move_cb (self, *args):
        if not self.timer.is_running():
            self.timer.start()
        
    def do_solve (self, btn):
        if self.game.filename is not None:
            if not self.game.get_parent():
                self.game_box.pop()
            self.game.show_image()
            self.timer.stop(True)
            if self._contest_mode and self.get_game_state() == GAME_STARTED:
                self.set_game_state(btn != self.btn_solve and GAME_FINISHED or GAME_QUIT)
        self._set_control_area()

    def do_select_category(self, owner, *args, **kwargs):
        if isinstance(owner, CategorySelector):
            self.thumb.set_image_dir(args[0])
            #self.game_box.pop()
            if not self.thumb.category.has_images():
                self.do_add_image(None)
        else:
            if self.game.get_parent():
                s = CategorySelector("images", _("Choose a Subject"), self.thumb.get_image_dir())
                s.connect("selected", self.do_select_category)
                s.show()
                self.game_box.push(s)
                s.grab_focus()
            else:
                self.game_box.pop()

    def do_add_image (self, widget, response=None, *args):
        """ Use to trigger and process the My Own Image selector.
        Also used for showing the buddies panel on contest mode"""
        if response is None:
            #if self._contest_mode and self.get_game_state() >= GAME_STARTED:
            #    # Buddy Panel
            #    if not self.buddy_panel.get_parent():
            #        self.timer.stop()
            #        self.game_box.push(self.buddy_panel)
            #    else:
            #        self.game_box.pop()
            #elif self._contest_mode and not self.is_initiator():
            #    # do nothing
            #    pass
            #else:
                # My Own Image selector
                imgfilter = gtk.FileFilter()
                imgfilter.set_name(_("Image Files"))
                imgfilter.add_mime_type('image/*')
                fd = gtk.FileChooserDialog(title=_("Select Image File"), parent=self._parent,
                                           action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                           buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

                fd.set_current_folder(os.path.expanduser("~/"))
                fd.set_modal(True)
                fd.add_filter(imgfilter)
                fd.connect("response", self.do_add_image)
                fd.resize(800,600)
                fd.show()
        else:
            if response == gtk.RESPONSE_ACCEPT:
                if self.thumb.load_image(widget.get_filename()):
                    self.do_shuffle()
                else:
                    err = gtk.MessageDialog(self._parent, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                            _("Not a valid image file"))
                    err.run()
                    err.destroy()
                    return
            widget.destroy()

    def do_lesson_plan (self, btn):
        if isinstance(self.game_box.get_child(), NotebookReaderWidget):
            self.game_box.pop()
        else:
            s = NotebookReaderWidget('lessons', self.selected_lang_details)
            s.connect('parent-set', self.do_lesson_plan_reparent)
            s.show_all()
            self.game_box.push(s)
            self.timer.stop()

    def do_lesson_plan_reparent (self, widget, oldparent):
        if widget.parent is None:
            self.set_button_translation(self.btn_lesson, "Lesson Plans")
            self.btn_lesson.get_child().set_label(_("Lesson Plans"))
        else:
            self.set_button_translation(self.btn_lesson, "Close Lesson")
            self.btn_lesson.get_child().set_label(_("Close Lesson"))

    def process_key (self, w, e):
        """ The callback for key processing. The button shortcuts are all defined here. """
        k = gtk.gdk.keyval_name(e.keyval)
        if not isinstance(self._parent.get_focus(), gtk.Editable):
            if k == '1':
                self.btn_9.clicked()
                return True
            if k == '2':
                self.btn_12.clicked()
                return True
            if k == '3':
                self.btn_16.clicked()
                return True
            if k == 'period':
                self.thumb.next()
                return True
            if k == 'comma':
                self.thumb.previous()
                return True
            if k == 'Return':
                self.set_nr_pieces(None)
                return True
            if k == 'slash':
                self.do_select_category(None)
                return True
            if k == 'question':
                self.btn_add.clicked()
                return True
            if k == 'equal':
                self.btn_solve.clicked()
                return True
            if k in ('Escape', 'q'):
                gtk.main_quit()
                return True
        return False

    def _freeze (self):
        """ returns a json writable object representation capable of being used to restore our current status """
        return (self.thumb._freeze(), self.game._freeze(), self.game.get_nr_pieces(), self.timer._freeze())

    def _thaw (self, obj):
        """ retrieves a frozen status from a python object, as per _freeze """
        self.thumb._thaw(obj[0])
        self.thumb.set_game_widget(self.game)
        self.set_nr_pieces(None, obj[2])
        self.game._thaw(obj[1])
        self.timer._thaw(obj[3])

    def _send_status_update (self):
        """ current build (432) will not fully support this method, so we are removing it for now. """
        pass
        #if self._parent._shared_activity:
        #    self._parent.game_tube.StatusUpdate(self._state[1], self.timer.is_running(), self.timer.ellapsed())

def main():
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    t = SliderPuzzleUI(win)
    gtk.main()
    return 0

if __name__ == "__main__":
	main()
