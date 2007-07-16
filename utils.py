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


### utils
### TODO: Describe
### $Id: $
###
### author: Carlos Neves (cn (at) sueste.net)
### (c) 2007 World Wide Workshop Foundation

import pygtk
pygtk.require('2.0')
import gtk
import pango

from math import sqrt, pow, ceil
import sys

DEBUG = True

RESIZE_STRETCH = 1
RESIZE_CUT = 2

GAME_IDLE = (10, 'idle')
GAME_SELECTED = (20, 'selected')
GAME_STARTED = (30, 'started')
GAME_FINISHED = (40, 'finished')
GAME_QUIT = (50, 'quit')

def debug (what):
    if DEBUG:
        print >> sys.stderr, what

def calculate_matrix (pieces):
    """ Given a number of pieces, calculate the best fit 2 dimensional matrix """
    rows = int(sqrt(pieces))
    cols = int(float(pieces) / rows)
    return rows*cols, rows, cols

def calculate_relative_size (orig_width, orig_height, width, height):
    """ If any of width or height is -1, the returned width or height will be in the same relative scale as the
    given part.
    >>> calculate_relative_size(100, 100, 50, -1)
    (50, 50)
    >>> calculate_relative_size(200, 100, -1, 50)
    (100, 50)

    If both width and height are given, the same values will be returned. If none is given, the orig_* will be returned.
    >>> calculate_relative_size(200,200,100,150)
    (100, 150)
    >>> calculate_relative_size(200,200,-1,-1)
    (200, 200)
    """
    if width < 0:
        if height >= 0:
            out_w = int(orig_width * (float(height)/orig_height))
            out_h = height
        else:
            out_w = orig_width
            out_h = orig_height
    else:
        out_w = width
        if height < 0:
            out_h = int(orig_height * (float(width)/orig_width))
        else:
            out_h = height
    return out_w, out_h

def load_image (filename, width=-1, height=-1, method=RESIZE_CUT):
    """ load an image from filename, returning it's gtk.gdk.PixBuf().
    If any or all of width and height are given, scale the loaded image to fit the given size(s).
    If both width and height and requested scaling can be achieved in two flavours, as defined by
    the method argument:
      RESIZE_CUT : resize so one of width or height fits the requirement and the other fits or overflows,
                   cut the center of the image to fit the request.
      RESIZE_STRETCH : fit the requested sizes exactly, by scaling with stretching sides if needed.

    Example: Image with 500x500, requested 200x100
      - RESIZE_CUT: scale to 200x200, cut 50 off each top and bottom to fit 200x100
      - RESIZE STRETCH : scale to 200x100, by changing the image WxH ratio from 1:1 to 2:1, thus distorting it.
    """
    if filename.lower().endswith('.sequence'):
        slider = None
        cmds = file(filename).readlines()
        if len(cmds) > 1:
            _x_ = eval(cmds[0])
            items = []
            for i in range(16):
                items.append(_x_)
                _x_ = eval(cmds[1])
            slider = SliderCreator(width, height, items)
            slider.prepare_stringed(2,2)
        return slider

    img = gtk.Image()
    try:
        img.set_from_file(filename)
        pb = img.get_pixbuf()
    except:
        return None
    if pb is None:
        return None
    if method == RESIZE_STRETCH or width == -1 or height == -1:
        w,h = calculate_relative_size(pb.get_width(), pb.get_height(), width, height)
        scaled_pb = pb.scale_simple(w,h, gtk.gdk.INTERP_BILINEAR)
    else: # RESIZE_CUT / default
        w,h = pb.get_width(), pb.get_height()
        if width > w:
            if height > h:
                #calc which side needs more scaling up as both are smaller
                hr = float(height)/h
                wr = float(width)/w
                if hr < wr:
                    w = width
                    h = -1
                else:
                    h = height
                    w = -1
            else:
                # requested height smaller than image, scale width up and cut on height
                h = -1
                w = width
        else:
            if height > h:
                #requested width smaller than image, scale height up and cut on width
                h = height
                w = -1
            else:
                # calc which side needs less scaling down as both are bigger
                hr = float(height)/h
                wr = float(width)/w
                if hr < wr:
                    w = width
                    h = -1
                else:
                    h = height
                    w = -1
        # w, h now have -1 for the side that should be relatively scaled, to keep the aspect ratio and
        # assuring that the image is at least as big as the request.
        w,h = calculate_relative_size(pb.get_width(), pb.get_height(), w,h)
        scaled_pb = pb.scale_simple(w,h, gtk.gdk.INTERP_BILINEAR)
        # now we cut whatever is left to make the requested size
        scaled_pb = scaled_pb.subpixbuf(abs((width-w)/2),abs((height-h)/2), width, height)
    return scaled_pb

class SliderCreator (gtk.gdk.Pixbuf):
    def __init__ (self, width, height, tlist):
        super(SliderCreator, self).__init__(gtk.gdk.COLORSPACE_RGB, False, 8, width, height)
        self.width = width
        self.height = height
        self.tlist = tlist

    def prepare_stringed (self, rows, cols):
        # We use a Pixmap as offscreen drawing canvas
        cm = gtk.gdk.colormap_get_system()
        pm = gtk.gdk.Pixmap(None, self.width, self.height, cm.get_visual().depth)
        #pangolayout = pm.create_pango_layout("")
        font_size = int(self.width / cols / 4)
        l = gtk.Label()
        pangolayout = pango.Layout(l.create_pango_context())
        pangolayout.set_font_description(pango.FontDescription("sans bold %i" % font_size))
        gc = pm.new_gc()
        gc.set_colormap(gtk.gdk.colormap_get_system())
        color = cm.alloc_color('white')
        gc.set_foreground(color)
        pm.draw_rectangle(gc, True, 0, 0, self.width, self.height)
        color = cm.alloc_color('black')
        gc.set_foreground(color)

        sw, sh = (self.width / cols), (self.height / rows)
        item = iter(self.tlist)
        for r in range(rows):
            for c in range(cols):
                px = sw * c
                py = sh * r
                #if c > 0 and r > 0:
                #    pm.draw_line(gc, px, 0, px, self.height-1)
                #    pm.draw_line(gc, 0, py, self.width-1, py)
                pangolayout.set_text(str(item.next()))
                pe = pangolayout.get_pixel_extents()
                print pe
                pe = pe[1][2]/2, pe[1][3]/2
                print pe
                print "**%s**" % pangolayout.get_text(), px + (sw / 2) - pe[0],  py + (sh / 2) - pe[1]
                pm.draw_layout(gc, px + (sw / 2) - pe[0],  py + (sh / 2) - pe[1], pangolayout)
        self.get_from_drawable(pm, cm, 0, 0, 0, 0, -1, -1)


def scale_images(img_dir, outdir):
    import os
    images = os.listdir(img_dir)
    for img_name in [x for x in images if x.startswith('image_')]:
        try:
            img = load_image(os.path.join(img_dir, img_name), 480, 480)
            h_p = img_name.rfind('_h')
            if h_p == -1:
                h_p = img_name.rfind('_w')
            if h_p == -1:
                h_p = img_name.rfind('_lg')
            name = img_name[:h_p]
            img.save(os.path.join(outdir, name+'.png'), 'png', {'compression':'9'})
            img.save(os.path.join(outdir, name+'.jpg'), 'jpeg', {'quality':'75'})
        except:
            raise
