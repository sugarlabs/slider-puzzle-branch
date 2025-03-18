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
from gi.repository import Gtk, GObject, Pango, Gdk

from mamamedia_modules import utils
#from mamamedia_modules import NotebookReaderWidget
from mamamedia_modules import BorderFrame, BORDER_ALL_BUT_BOTTOM, BORDER_ALL_BUT_LEFT
from mamamedia_modules import LanguageComboBox
from mamamedia_modules import ImageSelectorWidget
from mamamedia_modules import TimerWidget
from mamamedia_modules import BuddyPanel

from mamamedia_modules import GAME_IDLE, GAME_STARTED, GAME_FINISHED, GAME_QUIT


import locale

import logging
logger = logging.getLogger('sliderpuzzle-activity')
from glob import glob
from SliderPuzzleWidget import SliderPuzzleWidget
from time import time
import os
import hashlib
from sugar3.activity.activity import get_bundle_path
from sugar3 import mime
from sugar3.graphics.objectchooser import ObjectChooser
try:
    from sugar3.activity import activity
    from sugar3.graphics import units
    _inside_sugar = True
except:
    _inside_sugar = False


SLICE_BTN_WIDTH = 50

THUMB_SIZE = 48
IMAGE_SIZE = 200
#GAME_SIZE = 294
GAME_SIZE = 574

#MYOWNPIC_FOLDER = os.path.expanduser("~/.sugar/default/org.worldwideworkshop.olpc.SliderPuzzle.MyOwnPictures")
# Colors from Rich's UI design

COLOR_FRAME_OUTER = "#B7B7B7"
COLOR_FRAME_GAME = "#FF0099"
COLOR_FRAME_THUMB = COLOR_FRAME_GAME
COLOR_FRAME_CONTROLS = "#FFFF00"
COLOR_BG_CONTROLS = "#66CC00"
COLOR_FG_BUTTONS = (
    (Gtk.StateType.NORMAL, "#CCFF99"),
    (Gtk.StateType.ACTIVE, "#CCFF99"),
    (Gtk.StateType.PRELIGHT, "#CCFF99"),
    (Gtk.StateType.SELECTED, "#CCFF99"),
    (Gtk.StateType.INSENSITIVE, "#CCFF99"),
)
COLOR_BG_BUTTONS = (
    (Gtk.StateType.NORMAL, "#027F01"),
    (Gtk.StateType.ACTIVE, "#014D01"),
    (Gtk.StateType.PRELIGHT, "#016D01"),
    (Gtk.StateType.SELECTED, "#027F01"),
    (Gtk.StateType.INSENSITIVE, "#CCCCCC"),
)


def prepare_btn(btn, w=-1, h=-1):
    for state, color in COLOR_BG_BUTTONS:
        btn.modify_bg(state, Gdk.color_parse(color))
    c = btn.get_child()
    if c is not None:
        for state, color in COLOR_FG_BUTTONS:
            c.modify_fg(state, Gdk.color_parse(color))
    else:
        for state, color in COLOR_FG_BUTTONS:
            btn.modify_fg(state, Gdk.color_parse(color))
    if w > 0 or h > 0:
        btn.set_size_request(w, h)
    return btn


class SliderPuzzleUI (Gtk.Table):
    __gsignals__ = {
        'game-state-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (int,))}

    def __init__(self, parent):
        super(SliderPuzzleUI, self).__init__(3, 3, False)
        self._parent = parent

        # We want the translatables to be detected but not yet translated
        global _

        def _(x): return x
        self.labels_to_translate = []

        self._state = GAME_IDLE

        inner_table = Gtk.Table(2, 2, False)
        self.add(inner_table)
        self.from_journal = False
        self.game = SliderPuzzleWidget(9, GAME_SIZE, GAME_SIZE)
        self.game.connect("solved", self.do_solve)
        self.game.connect("moved", self.slider_move_cb)
        self._parent.connect("key_press_event", self.game.process_key)
        self._parent.connect("key_press_event", self.process_key)
        self.game.show()
        desktop = BorderFrame(border_color=COLOR_FRAME_CONTROLS)
        desktop.show()
        desktop.add(self.game)
        self.game_wrapper = Gtk.VBox()
        self.game_wrapper.show()
        inner = Gtk.HBox()
        inner.show()

        inner.pack_start(desktop, True, False, 0)
        self.game_wrapper.pack_start(inner, True, False, 0)

        # panel is a holder for everything on the left side down to (not inclusive) the language dropdown
        panel = Gtk.VBox()

        # Logo image
        img_logo = Gtk.Image()
        img_logo.set_from_file("icons/logo.png")
        img_logo.show()
        panel.pack_start(img_logo, False, False, 0)

        # Control panel has the image controls
        control_panel = BorderFrame(border=BORDER_ALL_BUT_BOTTOM,
                                    border_color=COLOR_FRAME_CONTROLS,
                                    bg_color=COLOR_BG_CONTROLS)
        control_panel_box = Gtk.VBox()
        control_panel.add(control_panel_box)

        spacer = Gtk.Label()
        spacer.set_size_request(-1, 5)
        control_panel_box.pack_start(spacer, False, False, 0)

        self.thumb = ImageSelectorWidget(
            self._parent, frame_color=COLOR_FRAME_THUMB, prepare_btn_cb=prepare_btn, image_dir='images')
        control_panel_box.pack_start(self.thumb, False, True, 0)

        spacer = Gtk.Label()
        spacer.set_size_request(-1, 5)
        control_panel_box.pack_start(spacer, False, False, 0)

        # Control panel end
        panel.pack_start(control_panel, True, True, 0)

        inner_table.attach(panel, 0, 1, 0, 1, 0)

        self.game_box = BorderFrame(border_color=COLOR_FRAME_GAME)
        self.game_box.add(self.game_wrapper)

        lang_combo = prepare_btn(LanguageComboBox(
            'org.worldwideworkshop.olpc.SliderPuzzle'))

        del _
        lang_combo.install()
        lang_box = BorderFrame(bg_color=COLOR_BG_CONTROLS,
                               border_color=COLOR_FRAME_CONTROLS)
        hbox = Gtk.HBox(False)
        vbox = Gtk.VBox(False)
        vbox.pack_start(lang_combo, True, True, 8)
        hbox.pack_start(vbox, True, True, 8)
        lang_box.add(hbox)

        timer_box = BorderFrame(border=BORDER_ALL_BUT_LEFT,
                                bg_color=COLOR_BG_CONTROLS,
                                border_color=COLOR_FRAME_CONTROLS)
        timer_hbox = Gtk.HBox(False)
        self.timer = TimerWidget(bg_color=COLOR_BG_BUTTONS[0][1],
                                 fg_color=COLOR_FG_BUTTONS[0][1],
                                 lbl_color=COLOR_BG_BUTTONS[1][1])
        self.timer.set_sensitive(False)
        self.timer.set_border_width(3)

        self.labels_to_translate.append((self.timer, _("Time: ")))
        timer_hbox.pack_start(self.timer, False, True, 8)
        self.timer.connect('timer_toggle', self.timer_toggle_cb)

        self.msg_label = Gtk.Label()
        self.msg_label.show()
        timer_hbox.pack_start(self.msg_label, True, True, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.show()
        self.notebook.props.show_border = False
        self.notebook.props.show_tabs = False
        self.notebook.append_page(self.game_box, None)
        inner_table.attach(self.notebook, 1, 2, 0, 1,
                           Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
        vbox = Gtk.VBox(False)
        vbox.pack_start(timer_hbox, True, True, 8)
        timer_box.add(vbox)
        inner_table.attach(timer_box, 1, 2, 1, 2, Gtk.AttachOptions.FILL |
                           Gtk.AttachOptions.EXPAND, Gtk.AttachOptions.FILL)

        self.buddy_panel = BuddyPanel()
        self.buddy_panel.show()

        # Contest mode flags
        self.set_contest_mode(False)
        self.initial_path = os.path.join(
            get_bundle_path(), 'images', 'image_aisc_h250_w313_lg.gif')
        self.set_nr_pieces(nr_pieces=9, path=self.initial_path)
        self.pre_path = self.initial_path

        self._on_lesson_plan = False

    def set_message(self, msg, frommesh=False):
        if frommesh and self.get_game_state() < GAME_STARTED:
            return
        self.msg_label.set_label(msg)

    def is_initiator(self):
        return self._parent.initiating

    @utils.trace
    def timer_toggle_cb(self, evt, running):
        logging.debug("Timer running: %s" % str(running))
        if self._contest_mode and running:
            self.set_game_state(GAME_STARTED)
        self._send_status_update()

    def _set_control_area(self, *args):
        """ The controls area below the logo needs different actions when in contest mode,
        and also if we are the contest initiators or not. """
        if self._contest_mode:
            if self.get_game_state() > GAME_IDLE:
                self.set_readonly()
            else:
                if self.is_initiator():
                    if self.timer.is_reset():
                        self.set_message(
                            _("Select image and press Start Game..."))
                    else:
                        self.set_game_state(GAME_STARTED)
                else:
                    self.set_message(
                        _("Waiting for Puzzle image to be chosen..."))
                    self.set_button_translation(self.btn_add, "Buddies")
                    self.btn_add.get_child().set_label(_("Buddies"))

    def set_game_state(self, state, force=False):
        if state[0] > self._state[0] or force:
            self._state = state
            self.emit('game-state-changed', state[0])
            self._set_control_area()
            if state == GAME_STARTED:
                self.set_button_translation(self.btn_add, "Buddies")
                self.btn_add.get_child().set_label(_("Buddies"))
            self._send_status_update()

    def get_game_state(self):
        return self._state

    def set_button_translation(self, btn, translation):
        for i in range(len(self.labels_to_translate)):
            if self.labels_to_translate[i][0] == btn:
                self.labels_to_translate[i][1] = translation
                break

    def set_contest_mode(self, mode):
        if getattr(self, '_contest_mode', None) != mode:
            self._contest_mode = bool(mode)
            self._set_control_area()
            if self._contest_mode:
                self.set_button_translation(self.btn_solve, "Give Up")
                self.btn_solve.get_child().set_label(_("Give Up"))
                self.set_button_translation(self.btn_shuffle, "Start Game")
                self.btn_shuffle.get_child().set_label(_("Start Game"))

    def is_contest_mode(self):
        return self._contest_mode  # and self.game.filename

    def do_select_language(self, combo, *args):
        self.selected_lang_details = combo.translations[combo.get_active()]
        self.refresh_labels()

    def refresh_labels(self, first_time=False):
        self._parent.set_title(_("Slider Puzzle Activity"))
        for lbl in self.labels_to_translate:
            if isinstance(lbl[0], Gtk.Button):
                lbl[0].get_child().set_label(_(lbl[1]))
            else:
                lbl[0].set_label(_(lbl[1]))
        if not self.game_wrapper.get_parent() and not first_time:
            self.game_box.pop()
            if self.notebook.get_current_page() == 1:
                m = self.do_lesson_plan
            else:
                m = self.do_select_category
            m(self)

    @utils.trace
    def set_nr_pieces(self, btn=None, nr_pieces=None, path=None, path_from_journal=None):
        # if isinstance(btn, Gtk.ToggleButton) and not btn.get_active():
        #    return
        logger.debug('final path')
        if self.is_contest_mode() and nr_pieces == self.game.get_nr_pieces():
            return

        if nr_pieces is None:
            nr_pieces = self.game.get_nr_pieces()
        if btn is None:
            if self._contest_mode:
                self.set_game_state(GAME_STARTED)
                return

        if not self.game_wrapper.get_parent():
            self.game_box.pop()

        if not path:
            self.yy = self.pre_path
        else:
            self.yy = path
        if self.from_journal:
            self.yy = path_from_journal
        if self.from_journal and not path_from_journal:
            self.yy = self.pth_frm_jrnl

        self.px = utils.load_image(self.yy)
        self.game.load_image(self.px)
        self.game.set_nr_pieces(nr_pieces)
        self.timer.reset(False)
        # set the current thumbnail
        self.pbb = utils.load_image(self.yy)
        self.fnpbb = utils.resize_image(self.pbb, 200, 200, method=2)
        self.thumb.image.set_from_pixbuf(self.fnpbb)

    def _set_nr_pieces_pre(self, img_path):
        self.from_journal = False
        self.pre_path = img_path
        self.set_nr_pieces(nr_pieces=9, path=img_path)

    def do_shuffle(self, *args, **kwargs):
        if self._contest_mode:
            if self.get_game_state() > GAME_IDLE:
                # Restart
                self.set_game_state(GAME_STARTED, True)
                self._parent.frozen.thaw()
                self.timer.reset(True)
            elif self.game.filename is not None and self.timer.is_reset():
                # Start
                self.timer.start()
        if not self.game_wrapper.get_parent():
            self.game_box.pop()
        self.game.load_image(self.px)
        self.game.randomize()
        self.timer.reset(False)

    def slider_move_cb(self, *args):
        if not self.timer.is_running():
            self.timer.start()

    def do_solve(self, btn):
        if self.game.filename is not None:
            if not self.game_wrapper.get_parent():
                self.game_box.pop()
            self.game.show_image()
            self.timer.stop(True)
            if self._contest_mode and self.get_game_state() == GAME_STARTED:
                if btn != self.btn_solve:
                    self.set_game_state(GAME_FINISHED)
                    self.set_message(_("Puzzle Solved!"))
                else:
                    self.set_game_state(GAME_QUIT)
                    self.set_message(_("Gave Up"))
        self._set_control_area()

    @utils.trace
    def do_add_image(self, widget, *args):
        """ Use to trigger and process the My Own Image selector.
        Also used for showing the buddies panel on contest mode"""
        self.from_journal = True
        if self._contest_mode and self.get_game_state() >= GAME_STARTED:
            # Buddy Panel
            if not self.buddy_panel.get_parent():
                self.timer.stop()
                self.game_box.push(self.buddy_panel)
            else:
                self.game_box.pop()
        elif self._contest_mode and not self.is_initiator():
            # do nothing
            pass
        else:
            self.add_image()
            self.do_shuffle()

    def add_image(self, *args):  # widget=None, response=None, *args):
        """ Use to trigger and process the My Own Image selector. """

        if hasattr(mime, 'GENERIC_TYPE_IMAGE'):
            filter = {'what_filter': mime.GENERIC_TYPE_IMAGE}
        else:
            filter = {}

        chooser = ObjectChooser(self._parent, **filter)
        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    self.pth_frm_jrnl = str(jobject.file_path)
                    self.set_nr_pieces(
                        nr_pieces=9, path_from_journal=str(jobject.file_path))
                    pass
        finally:
            chooser.destroy()
            del chooser

    def do_lesson_plan(self, btn):
        if self._on_lesson_plan:
            return
        try:
            self._on_lesson_plan = True
            if self._contest_mode and self.get_game_state() < GAME_STARTED:
                return
            page = self.notebook.get_current_page()
            if page == 0:
                self.timer.stop()
                self.timer.props.sensitive = False
                if self.notebook.get_n_pages() == 1:
                    lessons = NotebookReaderWidget('lessons',
                                                   self.selected_lang_details)
                    lessons.connect('parent-set', self.do_lesson_plan_reparent)
                    lessons.show_all()
                    self.notebook.append_page(lessons, None)
            else:
                self.timer.props.sensitive = True
            self.notebook.set_current_page(int(not page))
        finally:
            self._on_lesson_plan = False

    def do_lesson_plan_reparent(self, widget, oldparent):
        if widget.parent is None:
            self.set_button_translation(self.btn_lesson, "Lesson Plans")
            self.btn_lesson.get_child().set_label(_("Lesson Plans"))
        else:
            self.set_button_translation(self.btn_lesson, "Close Lesson")
            self.btn_lesson.get_child().set_label(_("Close Lesson"))

    def process_key(self, w, e):
        """ The callback for key processing. The button shortcuts are all defined here. """
        k = Gdk.keyval_name(e.keyval)
        if not isinstance(self._parent.get_focus(), Gtk.Editable):
            if k == '1':
                self.set_nr_pieces(nr_pieces=9)
                return True
            if k == '2':
                self.set_nr_pieces(nr_pieces=12)
                return True
            if k == '3':
                self.set_nr_pieces(nr_pieces=16)
                return True
            if k == 'Return':
                self.set_nr_pieces(None)
                return True

            if k in ('Escape', 'q'):
                Gtk.main_quit()
                return True
            return False

    @utils.trace
    def _freeze(self, journal=True):
        """ returns a json writable object representation capable of being used to restore our current status """
        return ({'image_dir': os.path.join(get_bundle_path(), 'images'), 'filename': self.yy}, self.game._freeze(journal=journal), self.game.get_nr_pieces(), self.timer._freeze())

    def _thaw(self, obj):
        """ retrieves a frozen status from a python object, as per _freeze """
        logging.debug('_thaw: %s' % obj)

        if not obj[1]['image']:
            return

        if 'image' not in obj[1]:
            self.game.load_image(self.pbb)
        self.set_nr_pieces(None, obj[2])
        logging.debug(list(obj[1].keys()))
        wimg = 'image' in obj[1]
        self.game._thaw(obj[1])
        if wimg:
            logging.debug("Forcing thumb image from the one in game")
            self.thumb.image.set_from_pixbuf(self.game.image)

        self.timer.reset()
        self.timer._thaw(obj[3])
        self.game_box.pop()

    @utils.trace
    def _send_status_update(self):
        """ Send a status update signal """
        if self._parent.shared_activity:
            if self.get_game_state() == GAME_STARTED:
                self.set_message(_("Game Started!"))
            self._parent.game_tube.StatusUpdate(
                self._state[1], self.timer.is_running(), self.timer.ellapsed())


def main():
    win = Gtk.Window(Gtk.WindowType.TOPLEVEL)
    t = SliderPuzzleUI(win)
    Gtk.main()
    return 0


if __name__ == "__main__":
    main()
