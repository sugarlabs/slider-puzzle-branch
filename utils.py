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

from math import sqrt, pow, ceil
import sys

DEBUG = True

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

def load_image (filename, width=-1, height=-1):
    img = gtk.Image()
    img.set_from_file(filename)
    pb = img.get_pixbuf()
    if pb is None:
        return None
    w,h = calculate_relative_size(pb.get_width(), pb.get_height(), width, height)
    scaled_pb = pb.scale_simple(w,h, gtk.gdk.INTERP_BILINEAR)
    return scaled_pb
