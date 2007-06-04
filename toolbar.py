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


### toolbar.py
### TODO: Describe
### $Id: $
###
### author: Carlos Neves (cn (at) sueste.net)
### (c) 2007 World Wide Workshop Foundation

import gtk
import gettext
import locale
import os
import logging

from i18n import list_available_translations


from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.combobox import ComboBox
from abiword import Canvas

class LanguageComboBox (ComboBox):
    def __init__ (self):
        ComboBox.__init__(self)
        self.translations = list_available_translations()
        for i,x in enumerate(self.translations):
            self.append_item(i+1,gettext.gettext(x.name))
        self.connect('changed', self.install)

    def install (self, *args):
        if self.get_active() > -1:
            self.translations[self.get_active()].install()
        else:
            code, encoding = locale.getdefaultlocale()
            # Try to find the exact translation
            for i,t in enumerate(self.translations):
                if t.matches(code):
                    self.set_active(i)
                    break
            if self.get_active() < 0:
                # Failed, try to get the translation based only in the country
                for i,t in enumerate(self.translations):
                    if t.matches(code, False):
                        self.set_active(i)
                        break
            if self.get_active() < 0:
                # nothing found, select first translation
                self.set_active(0)
        # Allow for other callbacks
        return False

try:
    from sugar.graphics.palette import Palette
    class LessonPlan (Palette):
        def __init__ (self):
            Palette.__init__(self)
            _ = gettext.gettext
            #self.set_size_request(600,400)
            self.set_primary_state(_('Lesson Plan'))
            self._frame = gtk.Frame()
            self._frame.show()
            self.set_content(self._frame)

            button_dismiss = gtk.Button(_('Dismiss'))
            self.append_button(button_dismiss)
            self._menu_bar.hide()

        def popup (self):
            logging.debug("POPUP")
            canvas = Canvas()
            canvas.set_size_request(600,400)
            canvas.show()
            self._frame.add(canvas)
            Palette.popup(self)
            # What file should we load?
            code, encoding = locale.getdefaultlocale()
            files = map(lambda x: os.path.join('texts', 'lesson_plan%s.abw' % x), ('_'+code.lower(), '_'+code.split('_')[0].lower(), ''))
            files = filter(lambda x: os.path.exists(x), files)
            canvas.load_file('file://%s/%s' % (os.getcwd(), files[0]))
            canvas.view_online_layout()
            canvas.zoom_width()
            canvas.set_show_margin(False)

        def hide (self):
            logging.debug("HIDE")
            self._frame.forall(lambda x: self._frame.remove(x))
            Palette.hide(self)
except:
    LessonPlan = None

class SliderToolbar(gtk.Toolbar):
    def __init__(self):
        gtk.Toolbar.__init__(self)
        self.tb_lang_select = LanguageComboBox()
        tool_item = gtk.ToolItem()
        tool_item.set_expand(False)
        tool_item.add(self.tb_lang_select)
        self.tb_lang_select.show()
        tool_item.show()

        lesson_plan = ToolButton('format-justify-center')
        lesson_plan.show()

        if LessonPlan is not None:
            lesson_plan.set_palette(LessonPlan())

        self.insert(tool_item, -1)
        self.insert(lesson_plan, -1)

    def set_language_callback (self, cb, call_now=True):
        self.tb_lang_select.connect('changed', cb)
        if call_now:
            self.tb_lang_select.install()
            cb(self.tb_lang_select)

        

