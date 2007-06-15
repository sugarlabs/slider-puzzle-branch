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

from utils import load_image
#from toolbar import SliderToolbar
from i18n import LanguageComboBox
from abiword import Canvas
import locale

import logging
from glob import glob
from SliderPuzzleWidget import SliderPuzzleWidget
from time import time
import os


try:
    from sugar.activity import activity
    from sugar.graphics import units
    _inside_sugar = True
except:
    _inside_sugar = False


BORDER_LEFT = 1
BORDER_RIGHT = 2
BORDER_TOP = 4
BORDER_BOTTOM = 8
BORDER_VERTICAL = BORDER_TOP | BORDER_BOTTOM
BORDER_HORIZONTAL = BORDER_LEFT | BORDER_RIGHT
BORDER_ALL = BORDER_VERTICAL | BORDER_HORIZONTAL
BORDER_ALL_BUT_BOTTOM = BORDER_HORIZONTAL | BORDER_TOP
BORDER_ALL_BUT_LEFT = BORDER_VERTICAL | BORDER_RIGHT

SLICE_BTN_WIDTH = 50

THUMB_SIZE = 48
GAME_SIZE = 520

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

# This is me trying to get to the translation message bundles:

class BorderFrame (gtk.EventBox):
    def __init__ (self, border=BORDER_ALL, size=5, bg_color=None, border_color=None):
        gtk.EventBox.__init__(self)
        if border_color is not None:
            self.set_border_color(gtk.gdk.color_parse(border_color))
        self.inner = gtk.EventBox()
        if bg_color is not None:
            self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(bg_color))
        align = gtk.Alignment(1.0,1.0,1.0,1.0)
        padding = [0,0,0,0]
        if (border & BORDER_TOP) != 0:
            padding[0] = size
        if (border & BORDER_BOTTOM) != 0:
            padding[1] = size
        if (border & BORDER_LEFT) != 0:
            padding[2] = size
        if (border & BORDER_RIGHT) != 0:
            padding[3] = size
        align.set_padding(*padding)
        align.add(self.inner)
        gtk.EventBox.add(self, align)
        self.stack = []

    def set_border_color (self, color):
        gtk.EventBox.modify_bg(self, gtk.STATE_NORMAL, color)

    def modify_bg (self, state, color):
        self.inner.modify_bg(state, color)

    def add (self, widget):
        self.stack.append(widget)
        self.inner.add(widget)

    def push (self, widget):
        widget.set_size_request(*self.inner.child.get_size_request())
        self.inner.remove(self.inner.child)
        self.add(widget)

    def pop (self):
        if len(self.stack) > 1:
            self.inner.remove(self.inner.child)
            del self.stack[-1]
            self.inner.add(self.stack[-1])

    def get_child (self):
        return self.inner.child

    def get_allocation (self):
        return self.inner.get_allocation()


class TimerWidget (gtk.HBox):
    def __init__ (self, bg_color="#DD4040", fg_color="#4444FF", lbl_color="#DD4040"):
        gtk.HBox.__init__(self)
        #spacer = gtk.Label()
        #spacer.set_size_request(20, -1)
        #self.counter = BorderFrame(size=1, bg_color=bg_color, border_color=border_color)
        self.counter = gtk.EventBox()
        self.counter.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(bg_color))
        self.counter.set_size_request(120, -1)
        hb = gtk.HBox()
        self.counter.add(hb)
        #self.pack_start(spacer, False)
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
        self.start_time = None
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

    def reset (self):
        self.finished = False
        if self.timer_id is not None:
            self.start_time = time()
            self.do_tick()
        else:
            self.start_time = None
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
        
    def process_click (self, btn, event):
        if self.timer_id is None:
            self.start()
        else:
            self.stop()

    def do_tick (self):
        t = time() - self.start_time
        self.time_label.set_text("%i:%0.2i" % (t/60, t%60))
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
        self.width = width
        self.height = height
        self.image = gtk.Image()
        self.myownpath = None
        img_box = BorderFrame(border_color=frame_color)
        img_box.add(self.image)
        img_box.set_border_width(5)
        img_box.connect('button_press_event', self.emit_image_pressed)
        self.attach(img_box, 0,5,0,1,0,0)
        self.attach(gtk.Label(), 0,1,1,2)
        bl = gtk.Button()

        il = gtk.Image()
        il.set_from_pixbuf(load_image('icons/arrow_left.png'))
        bl.set_image(il)

        bl.connect('clicked', self.previous)
        self.attach(prepare_btn(bl), 1,2,1,2,0,0)

        cteb = gtk.EventBox()
        self.cat_thumb = gtk.Image()
        self.cat_thumb.set_size_request(THUMB_SIZE, THUMB_SIZE)
        cteb.add(self.cat_thumb)
        cteb.connect('button_press_event', self.emit_cat_pressed)
        self.attach(cteb, 2,3,1,2,0,0,xpadding=10)
        
        br = gtk.Button()
        ir = gtk.Image()
        ir.set_from_pixbuf(load_image('icons/arrow_right.png'))
        br.set_image(ir)
        br.connect('clicked', self.next)
        self.attach(prepare_btn(br), 3,4,1,2,0,0)
        self.attach(gtk.Label(),4,5,1,2)
        self.filename = None
        self.show_all()
        self.image.set_size_request(width, height)

    def set_myownpath (self, path):
        """ Sets the path to My Own Pictures storage, so we know where to add links to new pictures """
        if not os.path.exists(path):
            os.mkdir(path)
        self.myownpath = path

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
        self.category = CategoryDirectory(directory, self.width, self.height)
        self.cat_thumb.set_from_pixbuf(self.category.thumb)
        if self.category.has_images():
            self.next()

    def load_image(self, filename, force_filename=False):
        """ Loads an image from the file """
        if self.myownpath is not None and os.path.isdir(self.myownpath):
            name = os.path.splitext(os.path.basename(filename))[0]
            while os.path.exists(os.path.join(self.myownpath, '%s.lnk' % name)):
                name = name + '_'
            f = file(os.path.join(self.myownpath, '%s.lnk' % name), 'w')
            f.write(filename)
            f.close()
            self.category = CategoryDirectory(self.myownpath, self.width, self.height)
            self.image.set_from_pixbuf(self.category.get_image(filename))
        else:
            self.category = CategoryDirectory(filename, self.width, self.height)
            self.next()
        self.cat_thumb.set_from_pixbuf(self.category.thumb)
        return self.image.get_pixbuf() is not None

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
            store.append([MYOWNPIC_FOLDER, _("My Own Pictures") + (" (%i)" % count), len(self.thumbs)])
            self.thumbs.append(self.get_pb(MYOWNPIC_FOLDER))

        i = store.get_iter_first()
        while i:
            if selected_path == store.get_value(i, 0):
                selected = store.get_path(i)
                break
            i = store.iter_next(i)
        #if selected_path == fullpath:
        #    selected = (len(self.thumbs)-1,)
        return store, selected

    def do_select (self, tree, *args, **kwargs):
        if self.ignore_first:
            self.ignore_first = False
        else:
            tv, it = tree.get_selection().get_selected()
            self.emit("selected", tv.get_value(it,0))

class LessonPlanWidget (gtk.Notebook):
    def __init__ (self):
        super(LessonPlanWidget, self).__init__()
        lessons = filter(lambda x: os.path.isdir(os.path.join('lessons', x)), os.listdir('lessons'))
        lessons.sort()
        for lesson in lessons:
            self._load_lesson(os.path.join('lessons', lesson), _(lesson))

    def _load_lesson (self, path, name):
        code, encoding = locale.getdefaultlocale()
        canvas = Canvas()
        canvas.show()
        files = map(lambda x: os.path.join(path, '%s.abw' % x),
                    ('_'+code.lower(), '_'+code.split('_')[0].lower(), 'default'))
        files = filter(lambda x: os.path.exists(x), files)
        try:
            canvas.load_file('file://%s/%s' % (os.getcwd(), files[0]), 'text/plain')
        except:
            canvas.load_file('file://%s/%s' % (os.getcwd(), files[0]))
        canvas.view_online_layout()
        canvas.zoom_width()
        canvas.set_show_margin(False)
        self.append_page(canvas, gtk.Label(name))
        

class SliderPuzzleUI (gtk.Table):
    def __init__(self, parent):
        super(SliderPuzzleUI, self).__init__(3,3,False)
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
        controls_area_1_box = gtk.VBox(False)
        vbox = gtk.VBox()
        controls_vbox.pack_start(controls_area_1)
        vbox.pack_start(controls_area_1_box, padding=5)
        controls_area_1.add(vbox)

        # Slice buttons
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
        controls_area_1_box.pack_start(cutter, True)

        # The image selector with thumbnail
        self.thumb = ImageSelectorWidget(180, 180, frame_color=COLOR_FRAME_THUMB)
        self.thumb.set_image_dir("images")
        self.thumb.set_myownpath(MYOWNPIC_FOLDER)
        self.thumb.connect("category_press", self.do_select_category)
        self.thumb.connect("image_press", self.set_nr_pieces, None)
        controls_area_1_box.pack_start(self.thumb, False)

        sep = gtk.Label()
        sep.set_size_request(3,3)
        controls_area_1_box.pack_start(sep, False)

        # The game control buttons
        btn_box = gtk.Table(3,3,False)
        btn_box.set_row_spacings(3)
        btn_box.attach(gtk.Label(), 0,1,0,3)
        btn_box.attach(gtk.Label(), 2,3,0,3)
        self.btn_solve = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append((self.btn_solve, _("Solve")))
        self.btn_solve.connect("clicked", self.do_solve)
        btn_box.attach(self.btn_solve, 1,2,0,1,0,0)
        self.btn_shuffle = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append((self.btn_shuffle, _("Shuffle")))
        self.btn_shuffle.connect("clicked", self.do_shuffle)
        btn_box.attach(self.btn_shuffle, 1,2,1,2,0,0)
        self.btn_add = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append((self.btn_add, _("My Own Picture")))
        self.btn_add.connect("clicked", self.do_add_image)
        btn_box.attach(self.btn_add, 1,2,2,3,0,0)
        controls_area_1_box.pack_start(btn_box, False)

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
        #self.timer.modify_bg(gtk.STATE_NORMAL, bgcolor)
        self.timer.set_border_width(3)
        self.labels_to_translate.append((self.timer, _("Time: ")))
        btn_box.pack_start(self.timer, False, padding=8)
        
        btn_box.pack_start(gtk.Label(), True)
        self.btn_lesson = prepare_btn(gtk.Button(" "))
        self.labels_to_translate.append([self.btn_lesson, _("Lesson Plan")])
        self.btn_lesson.connect("clicked", self.do_lesson_plan)
        btn_box.pack_start(self.btn_lesson, False, padding=8)
        vbox.pack_start(btn_box, padding=8)
        controls_area_3.add(vbox)
        inner_table.attach(controls_area_3, 1,2,1,2)
        
        # This has the sole purpose of centering the widget on screen
        self.attach(gtk.Label(), 0,3,0,1)
        self.attach(outer_box, 1,2,1,2,0,0)
        self.attach(gtk.Label(), 0,3,2,3)

        self.do_select_category(self)

        # Push the gettext translator into the global namespace
        del _
        lang_combo.connect('changed', self.do_select_language)
        lang_combo.install()
        self.do_select_language(lang_combo)

    def do_select_language (self, combo, *args):
        self.refresh_labels()

    def refresh_labels (self, first_time=False):
        logging.debug(str(_))
        self._parent.set_title(_("Slider Puzzle Activity"))
        for lbl in self.labels_to_translate:
            if isinstance(lbl[0], gtk.Button):
                lbl[0].get_child().set_label(_(lbl[1]))
            else:
                lbl[0].set_label(_(lbl[1]))
        if not self.game.get_parent() and not first_time:
            self.game_box.pop()
            if isinstance(self.game_box.get_child(), LessonPlanWidget):
                m = self.do_lesson_plan
            else:
                m = self.do_select_category
            m(self)

    def set_nr_pieces (self, btn, nr_pieces=None):
        if isinstance(btn, gtk.ToggleButton):
            if not btn.get_active():
                if nr_pieces == self.game.get_nr_pieces():
                    btn.set_active(True)
                return
        if nr_pieces is None:
            nr_pieces = self.game.get_nr_pieces()
        if self.thumb.has_image():
            if not self.game.get_parent():
                self.game_box.pop()
            self.game.load_image(self.thumb.get_filename())
            self.game.set_nr_pieces(nr_pieces)
            self.timer.reset()
        if isinstance(btn, gtk.ToggleButton):
            for b in (self.btn_9, self.btn_12, self.btn_16):
                if b is not btn:
                    b.set_active(False)

    def do_shuffle (self, *args, **kwargs):
        if self.thumb.has_image():
            if not self.game.get_parent():
                self.game_box.pop()
            self.game.load_image(self.thumb.get_filename())
            self.game.randomize()
            self.timer.reset()

    def do_solve (self, btn):
        if self.thumb.has_image():
            if not self.game.get_parent():
                self.game_box.pop()
            self.game.show_image()
            self.timer.stop(True)

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
        if response is None:
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
        if isinstance(self.game_box.get_child(), LessonPlanWidget):
            self.game_box.pop()
        else:
            s = LessonPlanWidget()
            s.connect('parent-set', self.do_lesson_plan_reparent)
            s.show_all()
            self.game_box.push(s)

    def do_lesson_plan_reparent (self, widget, oldparent):
        if widget.parent is None:
            for i in range(len(self.labels_to_translate)):
                if self.labels_to_translate[i][0] == self.btn_lesson:
                    self.labels_to_translate[i][1] = "Lesson Plan"
                    break
            self.btn_lesson.get_child().set_label(_("Lesson Plan"))
        else:
            for i in range(len(self.labels_to_translate)):
                if self.labels_to_translate[i][0] == self.btn_lesson:
                    self.labels_to_translate[i][1] = "Close Lesson"
                    break
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
        #logging.debug("%s %s %s" % (str(self._parent.get_focus()), str(isinstance(self.window.get_focus(), gtk.Editable)), str(k)))
        return False

    def _freeze (self):
        """ returns a json writable object representation capable of being used to restore our current status """
        return (self.thumb._freeze(), self.game._freeze(), self.game.get_nr_pieces(), self.timer._freeze())

    def _thaw (self, obj):
        """ retrieves a frozen status from a python object, as per _freeze """
        self.thumb._thaw(obj[0])
        self.game.load_image(self.thumb.get_filename())
        self.set_nr_pieces(None, obj[2])
        self.game._thaw(obj[1])
        self.timer._thaw(obj[3])

def main():
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    t = SliderPuzzleUI(win)
    gtk.main()
    return 0

if __name__ == "__main__":
	main()
