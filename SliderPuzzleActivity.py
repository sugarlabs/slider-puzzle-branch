from sugar.activity.activity import Activity, ActivityToolbox, get_bundle_path
from gettext import gettext as _
from SliderPuzzleUI import SliderPuzzleUI
import logging, os

logger = logging.getLogger('sliderpuzzle-activity')

class SliderPuzzleActivity(Activity):
	def __init__(self, handle):
		Activity.__init__(self, handle)
		logger.debug('Starting Slider Puzzle activity... %s' % str(get_bundle_path()))
		os.chdir(get_bundle_path())
		self.connect('destroy', self.destroy_cb)

		self.set_title(_('SliderPuzzle'))
		toolbox = ActivityToolbox(self)
		self.set_toolbox(toolbox)
		toolbox.show()

		game = SliderPuzzleUI(self)

	def destroy_cb(self, data=None):
		return True
