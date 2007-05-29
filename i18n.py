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

import os
import gettext

_ = lambda x: x

# Images were taken from http://www.sodipodi.com/ 
# except for korea taken from http://zh.wikipedia.org/wiki/Image:Unification_flag_of_Korea.svg

lang_name_mapping = {
    'zh_cn':(_('Chinese (simplified)'), 'china'),
    'zh_tw':(_('Chinese (traditional)'), 'china'),
    'cs':(_('Czech'),'czech_republic'),
    'da':(_('Danish'),'denmark'),
    'nl':(_('Dutch'), 'netherlands'),
    'en':(_('English'),'united_states'),
    'en_gb':(_('English - Great Britain'),'united_kingdom'),
    'en_us':(_('English - U.S.'),'united_states'),
    'fi':(_('Finnish'),'finland'),
    'fr':(_('French'),'france'),
    'de':(_('German'),'germany'),
    'hu':(_('Hungarian'),'hungary'),
    'it':(_('Italian'),'italy'),
    'ja':(_('Japanese'),'japan'),
    'ko':(_('Korean'),'korea'),
    'no':(_('Norwegian'),'norway'),
    'pl':(_('Polish'),'poland'),
    'pt':(_('Portuguese'),'portugal'),
    'pt_br':(_('Portuguese - Brazilian'),'brazil'),
    'ru':(_('Russian'),'russian_federation'),
    'sk':(_('Slovak'),'slovenia'),
    'es':(_('Spanish'),'spain'),
    'sv':(_('Swedish'),'sweden'),
    'tr':(_('Turkish'),'turkey'),
    }

class LangDetails (object):
    def __init__ (self, code, name, image):
        self.code = code
        self.country_code = self.code.split('_')[0]
        self.name = name
        self.image = image

    def guess_translation (self, fallback=False):
        self.gnutranslation = gettext.translation('org.worldwideworkshop.olpc.SliderPuzzle', 'locale', [self.code], fallback=fallback)

    def install (self):
        self.gnutranslation.install()

    def matches (self, code, exact=True):
        if exact:
            return code.lower() == self.code.lower()
        return code.split('_')[0].lower() == self.country_code.lower()

def get_lang_details (lang):
    mapping = lang_name_mapping.get(lang.lower(), None)
    if mapping is None:
        # Try just the country code
        lang = lang.split('_')[0]
        mapping = lang_name_mapping.get(lang.lower(), None)
        if mapping is None:
            return None
    return LangDetails(lang, mapping[0], mapping[1])

def list_available_translations ():
    rv = [get_lang_details('en')]
    rv[0].guess_translation(True)
    for i,x in enumerate([x for x in os.listdir('locale') if os.path.isdir('locale/' + x) and not x.startswith('.')]):
        try:
            details = get_lang_details(x)
            if details is not None:
                details.guess_translation()
                rv.append(details)
        except:
            raise
            pass
    return rv
