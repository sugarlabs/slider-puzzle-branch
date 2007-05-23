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

from gettext import gettext as _
from glob import glob
from SliderPuzzleWidget import SliderPuzzleWidget, calculate_relative_size
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
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(color))
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
        #self.inner = align
        gtk.EventBox.add(self, align)

    def add (self, widget):
        self.inner.add(widget)

    def do_size_request (self, requisition):
        print requisition.width, requisition.height, self.inner.child
        gtk.EventBox.do_size_request(self, requisition)
        self.inner.child.request_resize()


class TimerWidget (gtk.HBox):
    def __init__ (self):
        gtk.HBox.__init__(self)
        self.pack_start(gtk.Label(), True, True, 0)
        eb = gtk.EventBox()
        eb.add(gtk.Label(_("Time: ")))
        self.pack_start(eb, False)
        eb = gtk.EventBox()
        self.time_label = gtk.Label("--:--")
        eb.add(self.time_label)
        self.pack_start(eb, False)
        self.pack_end(gtk.Label(), True, True, 0)
        self.connect("button-press-event", self.process_click)
        self.start_time = None
        self.timer_id = None
        self.finished = False

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
        if self.start_time is None:
            self.start_time = time()
        else:
            self.start_time = time() - self.start_time
        self.do_tick()
        if self.timer_id is None:
            self.timer_id = gobject.timeout_add(1000, self.do_tick)

    def stop (self, finished=False):
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
        self.time_label.set_text("%0.2i:%0.2i" % (t/60, t%60))
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

    def next (self, *args, **kwargs):
        if self.filename is None or self.filename not in self.images:
            pos = -1
        else:
            pos = self.images.index(self.filename)
        pos += 1
        if pos >= len(self.images):
            pos = 0
        self.load_image(self.images[pos])

    def previous (self, *args, **kwargs):
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
        self.load_image(self.images[0])

    def load_image(self, filename):
        """ Loads an image from the file """
        img = gtk.Image()
        img.set_from_file(filename)
        pb = img.get_pixbuf()
        w,h = calculate_relative_size(pb.get_width(), pb.get_height(), self.width, self.height)
        scaled_pb = pb.scale_simple(w,h, gtk.gdk.INTERP_BILINEAR)
        self.image.set_from_pixbuf(scaled_pb)
        self.filename = filename

class SliderPuzzleUI:
    def __init__(self, parent):
        # Basic window settings
        self.window = parent
        settings = self.window.get_settings()
        settings.set_string_property("gtk-font-name", "sans bold 10", "SliderPuzzleUI")
        self.window.set_title("Slider Puzzle Activity")

        # The actual game widget
        self.game = SliderPuzzleWidget()
        self.game.connect("solved", self.do_solve)
	self.game.load_image("images/image_XO.svg", 480, 480)

        # The image selector with thumbnail
        self.thumb = ImageSelectorWidget(200)
        self.thumb.set_image_dir("images")
        #self.thumb.load_image("images/image_XO.svg")
        self.window.connect("key_press_event",self.game.process_key, None)

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
        inner_buttons_box = gtk.VBox(False, 5)
        btn_add = gtk.Button(_("Add My Own Picture"))
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

        # Everything on the left side of the game widget goes here
        controls_box = gtk.VBox(False, 5)
        controls_box.add(self.timer)
        controls_box.add(thumb_box)
        controls_box.add(buttons_box)

        # This is the horizontal container that holds everything
        wrapping_box = gtk.HBox()
        wrapping_box.add(controls_box)
        game_box = BorderFrame(BORDER_LEFT)
        game_box.add(self.game)
        wrapping_box.add(game_box)
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
            self.dcntr = 0
            self.window.connect("activated", do_check_resize)
            self.window.connect("deactivated", do_check_resize)
        except:
            self.window.add(outter)
            
        self.window.show_all()
        self.timer.start()

    def set_nr_pieces (self, btn, nr_pieces):
        self.game.load_image(self.thumb.filename)
        self.game.set_nr_pieces(nr_pieces)
        self.timer.reset()

    def do_jumble (self, btn):
        self.game.randomize()
        self.timer.reset()

    def do_solve (self, btn):
        self.game.show_image()
        self.timer.stop(True)

    def do_check_resize (self, *args, **kwargs):
        self.dbg_label.set_text("%i" % self.dcntr)
        self.dcntr += 1

def main():
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    t = SliderPuzzleUI(win)
    gtk.main()
    return 0

if __name__ == "__main__":
	main()
