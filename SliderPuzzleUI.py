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
from i18n import list_available_translations

import logging
import gettext
import locale
from glob import glob
from SliderPuzzleWidget import SliderPuzzleWidget
from time import time
import os

try:
    from sugar.graphics.combobox import ComboBox
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

# This is me trying to get to the translation message bundles:

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
        self.lbl_time = gtk.Label()
        self.pack_start(self.lbl_time, False)
        
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

class CategoryDirectory (object):
    def __init__ (self, path, width=-1, height=-1):
        self.path = path
        if os.path.isdir(path):
            self.images = glob(os.path.join(path, "image_*"))
        else:
            self.images = [path]
        self.set_thumb_size(32, 32)
        self.set_image_size(width, height)
        self.filename = None

    def set_image_size (self, w, h):
        self.width = w
        self.height = h

    def set_thumb_size (self, w, h):
        self.twidth = w
        self.theight = h
        self.thumb = self._get_category_thumb()

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
        self.filename = self.images[pos]
        return load_image(self.images[pos], self.width, self.height)

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
        self.filename = self.images[pos]
        return load_image(self.images[pos], self.width, self.height)

    def has_images (self):
        return len(self.images) > 0

    def has_image (self):
        return self.filename is not None

    def _get_category_thumb (self):
        if os.path.isdir(self.path):
            thumbs = glob(os.path.join(self.path, "thumb.*"))
            thumbs.extend(glob(os.path.join("..", os.path.join(self.path, "default_thumb.*"))))
            thumbs = filter(lambda x: os.path.exists(x), thumbs)
            thumbs.append(None)
        else:
            thumbs = [self.path]
        return load_image(thumbs[0], self.twidth, self.theight)
    

class ImageSelectorWidget (gtk.Table):
    __gsignals__ = {'category_press' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
                    'image_press' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),}

    def __init__ (self, width=-1, height=-1):
        gtk.Table.__init__(self, 2,4,False)
        self.width = width
        self.height = height
        self.image = gtk.Image()
        img_box = BorderFrame()
        img_box.add(self.image)
        img_box.set_border_width(5)
        img_box.connect('button_press_event', self.emit_image_pressed)
        self.attach(img_box, 0,5,0,1,0,0)
        self.attach(gtk.Label(), 0,1,1,2)
        bl = gtk.Button()
        bl.add(gtk.Arrow(gtk.ARROW_LEFT, gtk.SHADOW_IN))
        bl.connect('clicked', self.previous)
        self.attach(bl, 1,2,1,2,0,0)

        cteb = gtk.EventBox()
        self.cat_thumb = gtk.Image()
        self.cat_thumb.set_size_request(32,32)
        cteb.add(self.cat_thumb)
        cteb.connect('button_press_event', self.emit_cat_pressed)
        self.attach(cteb, 2,3,1,2,0,0)
        
        br = gtk.Button()
        br.add(gtk.Arrow(gtk.ARROW_RIGHT, gtk.SHADOW_IN))
        br.connect('clicked', self.next)
        self.attach(br, 3,4,1,2,0,0)
        self.attach(gtk.Label(),4,5,1,2)
        self.filename = None
        self.show_all()
        self.image.set_size_request(width, height)

    def emit_cat_pressed (self, *args):
        self.emit('category_press')
        return True

    def emit_image_pressed (self, *args):
        self.emit('image_press')
        return True

    def has_image (self):
        return self.category.has_image()

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
        self.category = CategoryDirectory(filename, self.width, self.height)
        self.next()
        self.cat_thumb.set_from_pixbuf(self.category.thumb)
        return self.image.get_pixbuf() is not None

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
        return load_image(thumbs[0], 32,32)

    def get_model (self, path, selected_path):
        # Each row is (path/dirname, pretty name, 0 based index)
        selected = None
        store = gtk.ListStore(str, str, int)
        files = [os.path.join(path, x) for x in os.listdir(path) if not x.startswith('.')]
        for fullpath, prettyname in [(x, _(os.path.basename(x))) for x in files if os.path.isdir(x)]:
            store.append([fullpath, prettyname, len(self.thumbs)])
            self.thumbs.append(self.get_pb(fullpath))
            if selected_path == fullpath:
                selected = (len(self.thumbs)-1,)
        return store, selected

    def do_select (self, tree, *args, **kwargs):
        if self.ignore_first:
            self.ignore_first = False
        else:
            tv, it = tree.get_selection().get_selected()
            self.emit("selected", tv.get_value(it,0))

class SliderPuzzleUI:
    def __init__(self, parent):
        # Add our own icons here, needed for the translation flags
        theme = gtk.icon_theme_get_default()
        theme.append_search_path(os.path.join(os.getcwd(), 'icons'))
        logging.debug("GTK Theme path: %s" % (str(gtk.icon_theme_get_default().get_search_path())))
        # We want the translatables to be detected but not yet translated
        global _
        _ = lambda x: x
        self.labels_to_translate = []

        # Basic window settings
        self.window = parent

        if _inside_sugar:
            self.update_toolbar()
        else:
            gettext.bindtextdomain('org.worldwideworkshop.olpc.SliderPuzzle', 'locale')
            gettext.textdomain('org.worldwideworkshop.olpc.SliderPuzzle')
        bgcolor = gtk.gdk.color_parse("#DDDD40")

        # The actual game widget
        self.game = SliderPuzzleWidget(9, 480, 480)
        self.game.connect("solved", self.do_solve)
        self.window.connect("key_press_event",self.game.process_key)
        self.window.connect("key_press_event",self.process_key)

        # The image selector with thumbnail
        self.thumb = ImageSelectorWidget(200, 200)
        self.thumb.set_image_dir("images")
        self.thumb.connect("category_press", self.do_select_category)
        self.thumb.connect("image_press", self.set_nr_pieces, None)
        #self.thumb.load_image("images/image_XO.svg")

        # Buttons for selecting the number of pieces
        cutter = gtk.VBox()
        self.btn_9 = gtk.ToggleButton("9")
        self.btn_9.set_size_request(50,-1)
        self.btn_9.set_active(True)
        self.btn_9.connect("clicked", self.set_nr_pieces, 9)
        cutter.add(self.btn_9)
        self.btn_12 = gtk.ToggleButton("12")
        self.btn_12.connect("clicked", self.set_nr_pieces, 12)
        cutter.add(self.btn_12)
        self.btn_16 = gtk.ToggleButton("16")
        self.btn_16.connect("clicked", self.set_nr_pieces, 16)
        cutter.add(self.btn_16)

        # Thumb box has both the image selector and the number of pieces buttons
        thumb_box = gtk.Table(1,2)
        thumb_box.attach(self.thumb, 0,1,0,1)
        thumb_box.attach(cutter,1,2,0,1,0,0)

        # The bottom left buttons
        buttons_box = BorderFrame(BORDER_TOP)
        buttons_box.modify_bg(gtk.STATE_NORMAL, bgcolor)
        inner_buttons_box = gtk.VBox(False, 5)
        inner_buttons_box.set_border_width(10)
        self.btn_add = gtk.Button()
        self.labels_to_translate.append((self.btn_add, _("My Own Picture")))
        self.btn_add.connect("clicked", self.do_add_image)
        inner_buttons_box.add(self.btn_add)
        self.btn_solve = gtk.Button()
        self.labels_to_translate.append((self.btn_solve, _("Solve")))
        self.btn_solve.connect("clicked", self.do_solve)
        inner_buttons_box.add(self.btn_solve)
        self.btn_jumble = gtk.Button()
        self.labels_to_translate.append((self.btn_jumble, _("Jumble")))
        self.btn_jumble.connect("clicked", self.do_jumble)
        inner_buttons_box.add(self.btn_jumble)
        buttons_box.add(inner_buttons_box)

        # The timer widget
        self.timer = TimerWidget()
        self.timer.modify_bg(gtk.STATE_NORMAL, bgcolor)
        self.timer.set_border_width(3)
        self.labels_to_translate.append((self.timer, _("Time: ")))

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

        if _inside_sugar:
            self.window.set_canvas(outter)
        else:
            self.window.add(outter)

        self.window.show_all()
        self.do_select_category(self)

        # Push the gettext translator into the global namespace
        del _
        if _inside_sugar:
            self.do_select_language(self.tb_lang_select)
        else:
            _ = gettext.gettext
            self.refresh_labels(True)
        #self.timer.start()


    def update_toolbar (self):
        """ This method lists all available translations in a ComboBox widget.
        The first translation is English, for that is the 'no translation' language in the code."""
        self.translations = list_available_translations()
        logging.debug(self.translations)
        self.tb_lang_select = ComboBox()
        for i,x in enumerate(self.translations):
            self.tb_lang_select.append_item(i+1,gettext.gettext(x.name), x.image)
        self.tb_lang_select.connect('changed', self.do_select_language)
        # Attach the ComboBox to Sugar activity default toolbar
        toolbox = self.window.toolbox
        toolbar = toolbox.get_activity_toolbar()
        tool_item = gtk.ToolItem()
        tool_item.set_expand(False)
        tool_item.add(self.tb_lang_select)
        self.tb_lang_select.show()
        toolbar.insert(tool_item, 2)
        tool_item.show()
        self.tb_lang_select._icon_renderer.props.stock_size = 3

    def do_select_language (self, combo, *args):
        if combo.get_active() > -1:
            self.translations[combo.get_active()].install()
        else:
            code, encoding = locale.getdefaultlocale()
            # Try to find the exact translation
            for i,t in enumerate(self.translations):
                if t.matches(code):
                    combo.set_active(i)
                    break
            if combo.get_active() < 0:
                # Failed, try to get the translation based only in the country
                for i,t in enumerate(self.translations):
                    if t.matches(code, False):
                        combo.set_active(i)
                        break
            if combo.get_active() < 0:
                # nothing found, select first translation
                combo.set_active(0)
        self.refresh_labels()

    def refresh_labels (self, first_time=False):
        logging.debug(str(_))
        self.window.set_title(_("Slider Puzzle Activity"))
        for lbl in self.labels_to_translate:
            lbl[0].set_label(_(lbl[1]))
        if not self.game.get_parent() and not first_time:
            self.game_box.pop()
            self.do_select_category(self)

    def set_nr_pieces (self, btn, nr_pieces=None):
        if isinstance(btn, gtk.ToggleButton):
            print nr_pieces, btn.get_active()
            if not btn.get_active():
                print nr_pieces, self.game.get_nr_pieces()
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

    def do_jumble (self, *args, **kwargs):
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
        else:
            if self.game.get_parent():
                s = CategorySelector("images", _("Select Image Category"), self.thumb.get_image_dir())
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
            fd = gtk.FileChooserDialog(title=_("Select Image File"), parent=self.window, action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                       buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
            fd.set_current_folder(os.path.expanduser("~/"))
            fd.set_modal(True)
            fd.add_filter(imgfilter)
            fd.connect("response", self.do_add_image)
            fd.show()
        else:
            if response == gtk.RESPONSE_ACCEPT:
                if self.thumb.load_image(widget.get_filename()):
                    self.do_jumble()
                else:
                    err = gtk.MessageDialog(self.window, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK,
                                            _("Not a valid image file"))
                    err.run()
                    err.destroy()
                    return
            widget.destroy()

    def process_key (self, w, e):
        """ The callback for key processing. The button shortcuts are all defined here. """
        k = gtk.gdk.keyval_name(e.keyval)
        if not isinstance(self.window.get_focus(), gtk.Editable):
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
        #logging.debug("%s %s %s" % (str(self.window.get_focus()), str(isinstance(self.window.get_focus(), gtk.Editable)), str(k)))
        return False

def main():
    win = gtk.Window(gtk.WINDOW_TOPLEVEL)
    t = SliderPuzzleUI(win)
    gtk.main()
    return 0

if __name__ == "__main__":
	main()
