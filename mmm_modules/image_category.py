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

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import os
from glob import glob
import logging
import md5
from sugar3.activity.activity import Activity, get_bundle_path
from sugar3 import mime
from sugar3.graphics.objectchooser import ObjectChooser

from borderframe import BorderFrame
from utils import load_image, resize_image, RESIZE_CUT
import logging
logger = logging.getLogger('sliderpuzzle-activity')
cwd = os.path.normpath(os.path.join(os.path.split(__file__)[0], '..'))

if os.path.exists(os.path.join(cwd, 'mamamedia_icons')):
    # Local, no shared code, version
    mmmpath = cwd
    iconpath = os.path.join(mmmpath, 'mamamedia_icons')
else:
    propfile = os.path.expanduser("~/.sugar/default/org.worldwideworkshop.olpc.MMMPath")

    if os.path.exists(propfile):
        mmmpath = file(propfile, 'rb').read()
    else:
        mmmpath = cwd
    iconpath = os.path.join(mmmpath, 'icons')


from gettext import gettext as _

THUMB_SIZE = 48
IMAGE_SIZE = 200
#MYOWNPIC_FOLDER = os.path.expanduser("~/.sugar/default/org.worldwideworkshop.olpc.MyOwnPictures")

def prepare_btn (btn):
    return btn

def register_category (pixbuf_class, path):
    pass

class CategoryDirectory (object):
    def __init__ (self, path, width=-1, height=-1, method=RESIZE_CUT):
        self.path = path
        self.method = method
        self.pb = None
        
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
        self.pb = load_image(name)
        if self.pb is not None:
            rv = resize_image(self.pb, self.width, self.height, method=self.method)
            self.filename = name
            return rv
        return None
            
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
        logging.debug("IMG %s" % self.images)
        return len(self.images) > 0

    def count_images (self):
        return len(self.images)

    def has_image (self):
        return self.pb is not None

    def _get_category_thumb (self):
        if os.path.isdir(self.path):
            thumbs = glob(os.path.join(self.path, "thumb.*"))
            thumbs.extend(glob(os.path.join(self.path, "default_thumb.*")))
            thumbs.extend(glob(os.path.join(mmmpath, "mmm_images","default_thumb.*")))
            logging.debug(thumbs)
            thumbs = filter(lambda x: os.path.exists(x), thumbs)
            thumbs.append(None)
        else:
            thumbs = [self.path]
        logging.debug("%s %s" % (self.path, thumbs))
        return load_image(thumbs[0], self.twidth, self.theight)
    

class ImageSelectorWidget (Gtk.Table):
    __gsignals__ = {'category_press' : (GObject.SignalFlags.RUN_LAST, None, ()),
                    'image_press' : (GObject.SignalFlags.RUN_LAST, None, ()),}

    def __init__ (self,parentp,
                  width=IMAGE_SIZE,
                  height=IMAGE_SIZE,
                  frame_color=None,
                  prepare_btn_cb=prepare_btn,
                  method=RESIZE_CUT,
                  image_dir=None):
        Gtk.Table.__init__(self, 2,5,False)
        self._signals = []
        self.parentp = parentp
        self.width = width
        self.height = height
        self.image = Gtk.Image()
        self.method = method
        #self.set_myownpath(MYOWNPIC_FOLDER)
        img_box = BorderFrame()
        img_box.add(self.image)
        img_box.set_border_width(5)
        self._signals.append((img_box, img_box.connect('button_press_event', self.emit_image_pressed)))
        self.attach(img_box, 0,5,0,1,0,0)
        self.attach(Gtk.Label(), 0,1,1,2)
        self.filename = None
        self.show_all()
        self.image.set_size_request(width, height)            
        self.set_image_dir(image_dir)
        
    def add_image (self, *args):#widget=None, response=None, *args):
        """ Use to trigger and process the My Own Image selector. """

        if hasattr(mime, 'GENERIC_TYPE_IMAGE'):
            filter = { 'what_filter': mime.GENERIC_TYPE_IMAGE }
        else:
            filter = { }

        chooser = ObjectChooser(_('Choose image'), self.parentp, #self._parent,
                                Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                **filter)
        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    if self.load_image(str(jobject.file_path), True):
                        pass
                    else:
                        err = Gtk.MessageDialog(self._parent, Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                                _("Not a valid image file"))
                        err.run()
                        err.destroy()
                        return
        finally:
            chooser.destroy()
            del chooser


        

    def set_readonly (self, ro=True):
        if ro:
            self.bl.hide()
            self.br.hide()
            for w, s in self._signals:
                w.handler_block(s)

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

    def get_image (self):
        return self.category.pb
        
        
    def next (self, *args, **kwargs):
        pb = self.category.get_next_image()
        if pb is not None:
            self.image.set_from_pixbuf(pb)

    def previous (self, *args, **kwargs):
        pb = self.category.get_previous_image()
        if pb is not None:
            self.image.set_from_pixbuf(pb)

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
        self.category = CategoryDirectory(directory, self.width, self.height, self.method)
        #self.cat_thumb.set_from_pixbuf(self.category.thumb)
        logger.debug('checkit')
        if filename:
            self.image.set_from_pixbuf(self.category.get_image(filename))
            logger.debug('mid')
        else:
            if self.category.has_images():
                logger.debug('final')
                self.next()

    def load_image(self, filename, fromJournal=False):
        logger.debug('heyao')
        self.category = CategoryDirectory(filename, self.width, self.height, method=self.method)
        self.next()
        return self.image.get_pixbuf() is not None

    def load_pb (self, pb):
        self.category.pb = pb
        self.image.set_from_pixbuf(resize_image(pb, self.width, self.height, method=self.method))

    def _freeze (self):
        """ returns a json writable object representation capable of being used to restore our current status """
        return {'image_dir': self.get_image_dir(),
                'filename': self.get_filename()}

    def _thaw (self, obj):
        """ retrieves a frozen status from a python object, as per _freeze """
        self.set_image_dir(obj.get('image_dir', None))
        self.image.set_from_pixbuf(self.category.get_image(obj.get('filename', None)))

class CategorySelector (Gtk.ScrolledWindow):
    __gsignals__ = {'selected' : (GObject.SignalFlags.RUN_LAST, None, (str,))}
    
    def __init__ (self, title=None, selected_category_path=None, path=None, extra=()):
        GObject.GObject.__init__ (self)
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        if path is None:
            path = os.path.join(mmmpath, 'mmm_images')
        self.path = path
        self.thumbs = {}
        model, selected = self.get_model(path, selected_category_path, extra)
        self.ignore_first = selected is not None
        
        self.treeview = Gtk.TreeView()
        col = Gtk.TreeViewColumn(title)
        r1 = Gtk.CellRendererPixbuf()
        r2 = Gtk.CellRendererText()
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

    def cell_pb (self, tvcolumn, cell, model, it, w):
        # Renders a pixbuf stored in the thumbs cache
        cell.set_property('pixbuf', self.thumbs[it.stamp])

    def get_pb (self, path):
        thumbs = glob(os.path.join(path, "thumb.*"))
        thumbs.extend(glob(os.path.join(self.path, "default_thumb.*")))
        thumbs = filter(lambda x: os.path.exists(x), thumbs)
        thumbs.append(None)
        return load_image(thumbs[0], THUMB_SIZE, THUMB_SIZE)

    def get_model (self, path, selected_path, extra):
        # Each row is (path/dirname, pretty name, 0 based index)
        selected = None
        store = Gtk.ListStore(str, str, int)
        store.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        files = [os.path.join(path, x) for x in os.listdir(path) if not x.startswith('.')]
        files.extend(extra)
        for fullpath, prettyname in [(x, _(os.path.basename(x))) for x in files if os.path.isdir(x)]:
            count = CategoryDirectory(fullpath).count_images()
            logging.debug("%s %s %s" % (fullpath, prettyname, count))
            store.append([fullpath, prettyname + (" (%i)" % count), len(self.thumbs)])
            self.thumbs.append(self.get_pb(fullpath))
            
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

