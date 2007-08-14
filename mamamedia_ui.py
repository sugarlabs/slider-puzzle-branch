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


### mamamedia_ui
### TODO: Describe
### $Id: $
###
### author: Carlos Neves (cn (at) sueste.net)
### (c) 2007 World Wide Workshop Foundation

import pygtk
pygtk.require('2.0')
import gtk, gobject, pango

import os
import locale
import gettext
from abiword import Canvas

#from gettext import gettext as _

BORDER_LEFT = 1
BORDER_RIGHT = 2
BORDER_TOP = 4
BORDER_BOTTOM = 8
BORDER_VERTICAL = BORDER_TOP | BORDER_BOTTOM
BORDER_HORIZONTAL = BORDER_LEFT | BORDER_RIGHT
BORDER_ALL = BORDER_VERTICAL | BORDER_HORIZONTAL
BORDER_ALL_BUT_BOTTOM = BORDER_HORIZONTAL | BORDER_TOP
BORDER_ALL_BUT_LEFT = BORDER_VERTICAL | BORDER_RIGHT

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
        align.show()
        self.inner.show()
        gtk.EventBox.add(self, align)
        self.stack = []

    def set_border_color (self, color):
        gtk.EventBox.modify_bg(self, gtk.STATE_NORMAL, color)

    def modify_bg (self, state, color):
        self.inner.modify_bg(state, color)

    def add (self, widget):
        self.stack.append(widget)
        self.inner.add(widget)
        self.inner.child.show_now()

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


class NotebookReaderWidget (gtk.Notebook):
    def __init__ (self, path, lang_details=None):
        super(NotebookReaderWidget, self).__init__()
        self.set_scrollable(True)
        self.lang_details = lang_details
        lessons = filter(lambda x: os.path.isdir(os.path.join(path, x)), os.listdir(path))
        lessons.sort()
        for lesson in lessons:
            if lesson[0].isdigit():
                name = _(lesson[1:])
            else:
                name = _(lesson)
            self._load_lesson(os.path.join(path, lesson), name)

    def _load_lesson (self, path, name):
        if self.lang_details:
            code = self.lang_details.code
        else:
            code, encoding = locale.getdefaultlocale()
        if code is None:
            code = 'en'
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
