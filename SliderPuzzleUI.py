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

from gettext import gettext as _
from glob import glob
from SliderPuzzleWidget import SliderPuzzleWidget
from time import time
import os

BORDER_LEFT = 1
BORDER_RIGHT = 2
BORDER_TOP = 4
BORDER_BOTTOM = 8
BORDER_VERTICAL = BORDER_TOP | BORDER_BOTTOM
BORDER_HORIZONTAL = BORDER_LEFT | BORDER_RIGHT
BORDER_ALL = BORDER_VERTICAL | BORDER_HORIZONTAL

class BorderFrame (gtk.EventBox):
    def __init__ (self, border=BORDER_ALL, size=5, color="#0000FF"):
        gtk.EventBox.__init__(self)
        self.set_border_color(gtk.gdk.color_parse(color))
        self.inner = gtk.EventBox()
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

    def get_allocation (self):
        return self.inner.get_allocation()


class TimerWidget (gtk.HBox):
    def __init__ (self):
        gtk.HBox.__init__(self)
        spacer = gtk.Label()
        spacer.set_size_request(20, -1)
        self.counter = BorderFrame(size=1, color="#4444FF")
        self.counter.set_size_request(100, -1)
        self.counter.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#DD4040"))
        hb = gtk.HBox()
        self.counter.add(hb)
        self.pack_start(spacer, False)
        self.pack_start(gtk.Label(_("Time: ")), False)
        
        #eb = gtk.EventBox()
        self.prepare_icons()
        self.icon = gtk.Image()
        self.icon.set_from_pixbuf(self.icons[1])
        hb.pack_start(self.icon, False, False, 5)
        self.time_label = gtk.Label("--:--")
        hb.pack_end(self.time_label, False, False, 5)
        self.pack_start(self.counter, False)
        self.connect("button-press-event", self.process_click)
        self.start_time = None
        self.timer_id = None
        self.finished = False

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

class ImageSelectorWidget (gtk.Table):
    def __init__ (self, width=-1, height=-1):
        gtk.Table.__init__(self, 2,4,False)
        self.width = width
        self.height = height
        self.image = gtk.Image()
        img_box = BorderFrame()
        img_box.add(self.image)
        img_box.set_border_width(5)
        self.attach(img_box, 0,4,0,1,0,0)
        self.attach(gtk.Label(), 0,1,1,2)
        bl = gtk.Button()
        bl.add(gtk.Arrow(gtk.ARROW_LEFT, gtk.SHADOW_IN))
        bl.connect('clicked', self.previous)
        self.attach(bl, 1,2,1,2)
        br = gtk.Button()
        br.add(gtk.Arrow(gtk.ARROW_RIGHT, gtk.SHADOW_IN))
        br.connect('clicked', self.next)
        self.attach(br, 2,3,1,2)
        self.attach(gtk.Label(),3,4,1,2)
        self.filename = None
        self.show_all()
        self.image.set_size_request(width, height)

    def next (self, *args, **kwargs):
        if not len(self.images):
            return
        if self.filename is None or self.filename not in self.images:
            pos = -1
        else:
            pos = self.images.index(self.filename)
        pos += 1
        if pos >= len(self.images):
            pos = 0
        self.load_image(self.images[pos])

    def previous (self, *args, **kwargs):
        if not len(self.images):
            return
        if self.filename is None or self.filename not in self.images:
            pos = len(self.images)
        else:
            pos = self.images.index(self.filename)
        pos -= 1
        if pos < 0:
            pos = len(self.images) - 1
        self.load_image(self.images[pos])

    def set_image_dir (self, directory):
        self.images = glob(os.path.join(directory, "image_*"))
        if len(self.images):
            self.load_image(self.images[0])
#        else:
#            self.load_image("activity/activity-sliderpuzzle.svg")

    def load_image(self, filename, force_filename=False):
        """ Loads an image from the file """
        pb = self.image.get_pixbuf()
        self.image.set_from_pixbuf(load_image(filename, self.width, self.height))
        if self.image.get_pixbuf() is not None:
            if (len(self.images) or force_filename):
                self.filename = filename
                if force_filename:
                    self.images = []
                return True
        else:
            self.image.set_from_pixbuf(pb)
        return False

class CategorySelector (gtk.ScrolledWindow):
    __gsignals__ = {'selected' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,))}
    
    def __init__ (self, path, title=None):
        gtk.ScrolledWindow.__init__ (self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.path = path
        self.thumbs = []
        model = self.get_model(path)
        
        treeview = gtk.TreeView()
        col = gtk.TreeViewColumn(title)
        r1 = gtk.CellRendererPixbuf()
        r2 = gtk.CellRendererText()
        col.pack_start(r1, False)
        col.pack_start(r2, True)
        col.set_cell_data_func(r1, self.cell_pb)
        col.set_attributes(r2, text=1)
        treeview.append_column(col)
        treeview.set_model(model)

        treeview.connect("cursor-changed", self.do_select)
        self.add(treeview)
        self.show_all()

    def cell_pb (self, tvcolumn, cell, model, it):
        cell.set_property('pixbuf', self.thumbs[model.get_value(it, 2)])

    def get_pb (self, path):
        thumbs = glob(os.path.join(path, "thumb.*"))
        thumbs.extend(glob(os.path.join(self.path, "default_thumb.*")))
        thumbs = filter(lambda x: os.path.exists(x), thumbs)
        thumbs.append(None)
        return load_image(thumbs[0], 32,32)

    def get_model (self, path):
        # Each row is (path/dirname, pretty name, 0 based index)
        store = gtk.ListStore(str, str, int)
        files = [os.path.join(path, x) for x in os.listdir(path) if not x.startswith('.')]
        i = 0
        for fullpath, prettyname in [(x, _(os.path.basename(x))) for x in files if os.path.isdir(x)]:
            store.append([fullpath, prettyname, len(self.thumbs)])
            self.thumbs.append(self.get_pb(fullpath))
        return store

    def do_select (self, tree, *args, **kwargs):
        tv, it = tree.get_selection().get_selected()
        self.emit("selected", tv.get_value(it,0))

class SliderPuzzleUI:
    def __init__(self, parent):
        # Basic window settings
        self.window = parent
        #settings = self.window.get_settings()
        #settings.set_string_property("gtk-font-name", "sans bold 10", "SliderPuzzleUI")
        self.window.set_title(_("Slider Puzzle Activity"))

        bgcolor = gtk.gdk.color_parse("#DDDD40")

        # The actual game widget
        self.game = SliderPuzzleWidget(9, 480, 480)
        self.game.connect("solved", self.do_solve)
        self.window.connect("key_press_event",self.game.process_key)

        # The image selector with thumbnail
        self.thumb = ImageSelectorWidget(200, 200)
        self.thumb.set_image_dir("images")
        self.thumb.connect("button_press_event", self.do_select_category)
        #self.thumb.load_image("images/image_XO.svg")

        # Buttons for selecting the number of pieces
        cutter = gtk.VBox()
        btn_9 = gtk.Button("9")
        btn_9.set_size_request(50,-1)
        btn_9.connect("clicked", self.set_nr_pieces, 9)
        cutter.add(btn_9)
        btn_12 = gtk.Button("12")
        btn_12.connect("clicked", self.set_nr_pieces, 12)
        cutter.add(btn_12)
        btn_16 = gtk.Button("16")
        btn_16.connect("clicked", self.set_nr_pieces, 16)
        cutter.add(btn_16)

        # Thumb box has both the image selector and the number of pieces buttons
        thumb_box = gtk.Table(1,2)
        thumb_box.attach(self.thumb, 0,1,0,1)
        thumb_box.attach(cutter,1,2,0,1,0,0)

        # The bottom left buttons
        buttons_box = BorderFrame(BORDER_TOP)
        buttons_box.modify_bg(gtk.STATE_NORMAL, bgcolor)
        inner_buttons_box = gtk.VBox(False, 5)
        inner_buttons_box.set_border_width(10)
        btn_add = gtk.Button(_("My Own Picture"))
        btn_add.connect("clicked", self.do_add_image)
        inner_buttons_box.add(btn_add)
        btn_solve = gtk.Button(_("Solve"))
        btn_solve.connect("clicked", self.do_solve)
        inner_buttons_box.add(btn_solve)
        btn_jumble = gtk.Button(_("Jumble"))
        btn_jumble.connect("clicked", self.do_jumble)
        inner_buttons_box.add(btn_jumble)
        buttons_box.add(inner_buttons_box)

        # The timer widget
        self.timer = TimerWidget()
        self.timer.modify_bg(gtk.STATE_NORMAL, bgcolor)
        self.timer.set_border_width(3)

        # Everything on the left side of the game widget goes here
        event_controls_box = gtk.EventBox()
        event_controls_box.modify_bg(gtk.STATE_NORMAL, bgcolor)
        controls_box = gtk.VBox(False, 5)
        controls_box.pack_start(self.timer, False, False)
        controls_box.add(thumb_box)
        controls_box.add(buttons_box)
        event_controls_box.add(controls_box)
        # This is the horizontal container that holds everything
        wrapping_box = gtk.HBox()
        wrapping_box.add(event_controls_box)
        self.game_box = BorderFrame(BORDER_LEFT)
        self.game_box.add(self.game)
        wrapping_box.add(self.game_box)
        # Put a border around the whole thing
        inner = BorderFrame()
        inner.add(wrapping_box)

        # This has the sole purpose of centering the widget on screen
        outter = gtk.Table(3,3,False)
        outter.attach(gtk.Label(), 0,3,0,1)
        outter.attach(inner, 1,2,1,2,0,0)
        outter.attach(gtk.Label(), 0,3,2,3)

        try:
            # This fails if testing outside Sugar
            self.window.set_canvas(outter)
        except:
            self.window.add(outter)

        self.window.show_all()
        self.do_select_category(self)
        #self.timer.start()

    def set_nr_pieces (self, btn, nr_pieces):
        if self.thumb.filename:
            if not self.game.get_parent():
                self.game_box.pop()
            self.game.load_image(self.thumb.filename)
            self.game.set_nr_pieces(nr_pieces)
            self.timer.reset()

    def do_jumble (self, *args, **kwargs):
        if self.thumb.filename:
            if not self.game.get_parent():
                self.game_box.pop()
            self.game.load_image(self.thumb.filename)
            self.game.randomize()
            self.timer.reset()

    def do_solve (self, btn):
        if self.thumb.filename:
            if not self.game.get_parent():
                self.game_box.pop()
            self.game.show_image()
            self.timer.stop(True)

    def do_select_category(self, owner, *args, **kwargs):
        if isinstance(owner, CategorySelector):
            self.thumb.set_image_dir(args[0])
            #self.game_box.pop()
        else:
            if self.game.get_parent():
                s = CategorySelector("images", _("Select Image Category"))
                s.connect("selected", self.do_select_category)
                s.show()
                self.game_box.push(s)
            else:
                self.game_box.pop()

    def do_add_image (self, widget, response=None, *args):
        if response is None:
            imgfilter = gtk.FileFilter()
            imgfilter.set_name(_("Image Files"))
            imgfilter.add_mime_type('image/*')
            fd = gtk.FileChooserDialog(title=("Select Image File"), parent=self.window, action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                       buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
            fd.set_current_folder(os.path.expanduser("~/"))
            fd.set_modal(True)
            fd.add_filter(imgfilter)
            fd.connect("response", self.do_add_image)
            fd.show()
        else:
            if response == gtk.RESPONSE_ACCEPT:
                if self.thumb.load_image(widget.get_filename(), True):
                    self.do_jumble()
                else:
                    err = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                            _("Not a valid image file"))
                    err.run()
                    err.destroy()
                    return
            widget.destroy()

def main():
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    t = SliderPuzzleUI(win)
    gtk.main()
    return 0

if __name__ == "__main__":
	main()
