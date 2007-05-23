#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# at your option) any later version.
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


### SliderPuzzleWidget
### All the SliderPuzzle game logic in a GTK widget ready for usage
### $Id: $
###
### author: Carlos Neves (cn (at) sueste.net)
### (c) 2007 World Wide Workshop Foundation



import pygtk
pygtk.require('2.0')
import gtk, gobject

from math import sqrt, pow, ceil
from types import TupleType, ListType
from random import random
from time import time
import sys

###
# General Information
###

up_key =    ['Up', 'KP_Up', 'KP_8']
down_key =  ['Down', 'KP_Down', 'KP_2']
left_key =  ['Left', 'KP_Left', 'KP_4']
right_key = ['Right', 'KP_Right', 'KP_6']

SLIDE_UP = 1
SLIDE_DOWN = 2
SLIDE_LEFT = 3
SLIDE_RIGHT = 4

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

###
# Game Logic
###

class MatrixPosition (object):
    """ Helper class to hold a x/y coordinate, and move it by passing a direction,
    taking care of enforcing boundaries as needed.
    The x and y coords are 0 based. """
    def __init__ (self, rowsize, colsize, x=0, y=0):
        self.rowsize = rowsize
        self.colsize = colsize
        self.x = min(x, colsize-1)
        self.y = min(y, rowsize-1)

    def __eq__ (self, other):
        if isinstance(other, (TupleType, ListType)) and len(other) == 2:
            return self.x == other[0] and self.y == other[1]
        return False

    def __ne__ (self, other):
        return not self.__eq__ (other)

    def bottom_right (self):
        """ Move to the lower right position of the matrix, having 0,0 as the top left corner """
        self.x = self.colsize - 1
        self.y = self.rowsize-1

    def move (self, direction, count=1):
        """ Moving direction is actually the opposite of what is passed.
        We are moving the hole position, so if you slice a piece down into the hole,
        that hole is actually moving up.
        Returns bool, false if we can't move in the requested direction."""
        if direction == SLIDE_UP and self.y < self.rowsize-1:
            self.y += 1
            return True
        if direction == SLIDE_DOWN and self.y > 0:
            self.y -= 1
            return True
        if direction == SLIDE_LEFT and self.x < self.colsize-1:
            self.x += 1
            return True
        if direction == SLIDE_RIGHT and self.x > 0:
            self.x -= 1
            return True
        return False

    def clone (self):
        return MatrixPosition(self.rowsize, self.colsize, self.x, self.y)
        

class SliderPuzzleMap (object):
    """ This class holds the game logic.
    The current pieces position is held in self.pieces_map[YROW][XROW].
    """
    def __init__ (self, pieces=9, move_cb=None):
        self.reset(pieces)
        self.move_cb = move_cb
        self.solved = True

    def reset (self, pieces=9):
        self.pieces, self.rowsize, self.colsize = calculate_matrix(pieces)
        debug("SliderPuzzleMap init: requested %i pieces" % (pieces))
        debug("   got %i pieces as %ix%i" % (self.pieces, self.colsize, self.rowsize))
        pieces_map = range(1,self.pieces+1)
        self.pieces_map = []
        for i in range(self.rowsize):
            self.pieces_map.append(pieces_map[i*self.colsize:(i+1)*self.colsize])
        self.hole_pos = MatrixPosition(self.rowsize, self.colsize)
        self.hole_pos.bottom_right()
        self.solved_map = [list(x) for x in self.pieces_map]
        self.solved_map[-1][-1] = None

    def randomize (self):
        """ To make sure the randomization is solvable, we don't simply shuffle the numbers.
        We move the hole in random directions through a finite number of iteractions. """
        # Remove the move callback temporarily
        cb = self.move_cb
        self.move_cb = None

        iteractions = self.rowsize * self.colsize * (int(100*random())+1)

        t = time()
        for i in range(iteractions):
            while not (self.do_move(int(4*random())+1)):
                pass

        t = time() - t
        debug("Done %i iteractions in %f seconds" % (iteractions, t))

        # Now move the hole to the bottom right
        for x in range(self.colsize-self.hole_pos.x-1):
            self.do_move(SLIDE_LEFT)
        for y in range(self.rowsize-self.hole_pos.y-1):
            self.do_move(SLIDE_UP)

        # Put the callback where it was
        self.move_cb = cb
        self.solved = False

    def do_move (self, slide_direction):
        """
        The moves are relative to the moving piece:
        
        >>> jm = SliderPuzzleMap()
        >>> jm.debug_map()
        1 2 3
        4 5 6
        7 8 *
        >>> jm.do_move(SLIDE_DOWN)
        True
        >>> jm.debug_map() # DOWN
        1 2 3
        4 5 *
        7 8 6
        >>> jm.do_move(SLIDE_RIGHT)
        True
        >>> jm.debug_map() # RIGHT
        1 2 3
        4 * 5
        7 8 6
        >>> jm.do_move(SLIDE_UP)
        True
        >>> jm.debug_map() # UP
        1 2 3
        4 8 5
        7 * 6
        >>> jm.do_move(SLIDE_LEFT)
        True
        >>> jm.debug_map() # LEFT
        1 2 3
        4 8 5
        7 6 *

        We can't move over the matrix edges:

        >>> jm.do_move(SLIDE_LEFT)
        False
        >>> jm.debug_map() # LEFT
        1 2 3
        4 8 5
        7 6 *
        >>> jm.do_move(SLIDE_UP)
        False
        >>> jm.debug_map() # UP
        1 2 3
        4 8 5
        7 6 *
        >>> jm.do_move(SLIDE_RIGHT)
        True
        >>> jm.do_move(SLIDE_RIGHT)
        True
        >>> jm.do_move(SLIDE_RIGHT)
        False
        >>> jm.debug_map() # RIGHT x 3
        1 2 3
        4 8 5
        * 7 6
        >>> jm.do_move(SLIDE_DOWN)
        True
        >>> jm.do_move(SLIDE_DOWN)
        True
        >>> jm.do_move(SLIDE_DOWN)
        False
        >>> jm.debug_map() # DOWN x 3
        * 2 3
        1 8 5
        4 7 6
       """
        # What piece are we going to move?
        old_hole_pos = self.hole_pos.clone()
        if self.hole_pos.move(slide_direction):
            # Move was a success, now update the map
            self.pieces_map[old_hole_pos.y][old_hole_pos.x] = self.pieces_map[self.hole_pos.y][self.hole_pos.x]
            self.is_solved()
            if self.move_cb is not None:
                self.move_cb(self.hole_pos.x, self.hole_pos.y, old_hole_pos.x, old_hole_pos.y)
            return True
        return False

    def do_move_piece (self, piece):
        """ Move the piece (1 based index) into the hole, if possible
        >>> jm = SliderPuzzleMap()
        >>> jm.debug_map()
        1 2 3
        4 5 6
        7 8 *
        >>> jm.do_move_piece(6)
        True
        >>> jm.debug_map() # Moved 6
        1 2 3
        4 5 *
        7 8 6
        >>> jm.do_move_piece(2)
        False
        >>> jm.debug_map() # No move
        1 2 3
        4 5 *
        7 8 6

        Return True if a move was done, False otherwise.
        """
        for y in range(self.rowsize):
            for x in range(self.colsize):
                if self.pieces_map[y][x] == piece:
                    if self.hole_pos.x == x:
                        if abs(self.hole_pos.y-y) == 1:
                            return self.do_move(self.hole_pos.y > y and SLIDE_DOWN or SLIDE_UP)
                    elif self.hole_pos.y == y:
                        if abs(self.hole_pos.x-x) == 1:
                            return self.do_move(self.hole_pos.x > x and SLIDE_RIGHT or SLIDE_LEFT)
                    else:
                        return False
        return False

    def is_hole_at (self, x, y):
        """
        >>> jm = SliderPuzzleMap()
        >>> jm.debug_map()
        1 2 3
        4 5 6
        7 8 *
        >>> jm.is_hole_at(2,2)
        True
        >>> jm.is_hole_at(0,0)
        False
        """
        return self.hole_pos == (x,y)

    def is_solved (self):
        """
        >>> jm = SliderPuzzleMap()
        >>> jm.do_move_piece(6)
        True
        >>> jm.is_solved()
        False
        >>> jm.do_move_piece(6)
        True
        >>> jm.is_solved()
        True
        """
        if self.hole_pos != (self.colsize-1, self.rowsize-1):
            return False
        self.pieces_map[self.hole_pos.y][self.hole_pos.x] = None
        self.solved = self.pieces_map == self.solved_map
        return self.solved
        
        

    def get_cell_at (self, x, y):
        if x < 0 or x >= self.colsize or y < 0 or y >= self.rowsize or self.is_hole_at(x,y):
            return None
        return self.pieces_map[y][x]

    def debug_map (self):
        for y in range(self.rowsize):
            for x in range(self.colsize):
                if self.hole_pos == (x,y):
                    print "*",
                else:
                    print self.pieces_map[y][x],
            print

    def __call__ (self):
        self.debug_map()


###
# Widget Definition
###

class SliderPuzzleWidget (gtk.Table):
    __gsignals__ = {'solved' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())}
    
    def __init__ (self, pieces=9):
        self.jumbler = SliderPuzzleMap(pieces, self.jumblermap_piece_move_cb)
        # We take this from the jumbler object because it may have altered our requested value
        self.nr_pieces = self.jumbler.pieces
        gtk.Table.__init__(self, self.jumbler.rowsize, self.jumbler.colsize)
        self.image = gtk.Image()
        self.randomize()

    def prepare_pieces (self):
        """ set up a list of UI objects that will serve as pieces, ordered correctly """
        self.pieces = []
        if self.image is not None:
            pb = self.image.get_pixbuf()
        if self.image is None or pb is None:
            for i in range(self.nr_pieces):
                self.pieces.append(gtk.Button(str(i+1)))
                self.pieces[-1].connect("button-release-event", self.process_mouse_click, i+1)
                self.pieces[-1].show()
        else:
            w = pb.get_width() / self.jumbler.colsize
            h = pb.get_height() / self.jumbler.rowsize
            for y in range(self.jumbler.rowsize):
                for x in range(self.jumbler.colsize):
                    img = gtk.Image()
                    img.set_from_pixbuf(pb.subpixbuf(x*w, y*h, w-1, h-1))
                    img.show()
                    self.pieces.append(gtk.EventBox())
                    self.pieces[-1].add(img)
                    self.pieces[-1].connect("button-press-event", self.process_mouse_click, (y*self.jumbler.colsize)+x+1)
                    self.pieces[-1].show()
            self.set_row_spacings(1)
            self.set_col_spacings(1)

    def full_refresh (self):
        # Delete everything
        self.foreach(self.remove)
        self.prepare_pieces()
        # Add the pieces in their respective places
        for y in range(self.jumbler.rowsize):
            for x in range(self.jumbler.colsize):
                pos = self.jumbler.get_cell_at(x, y)
                if pos is not None:
                    self.attach(self.pieces[pos-1], x, x+1, y, y+1)

    def process_mouse_click (self, b, e, i):
        # i is the 1 based index of the piece
        self.jumbler.do_move_piece(i)

    def process_key (self, w, e, o):
        k = gtk.gdk.keyval_name(e.keyval)
        if k in up_key:
            self.jumbler.do_move(SLIDE_UP)
            return True
        if k in down_key:
            self.jumbler.do_move(SLIDE_DOWN)
            return True
        if k in left_key:
            self.jumbler.do_move(SLIDE_LEFT)
            return True
        if k in right_key:
            self.jumbler.do_move(SLIDE_RIGHT)
            return True
        return False

    ### SliderPuzzleMap specific callbacks ###

    def jumblermap_piece_move_cb (self, hx, hy, px, py):
        if not hasattr(self, 'pieces'):
            return
        piece = self.pieces[self.jumbler.get_cell_at(px, py)-1]
        self.remove(piece)
        self.attach(piece, px, px+1, py, py+1)
        if self.jumbler.solved:
            self.emit("solved")

    ### Parent callable interface ###

    def set_nr_pieces (self, nr_pieces):
        self.jumbler.reset(nr_pieces)
        self.resize(self.jumbler.rowsize, self.jumbler.colsize)
        self.randomize()

    def randomize (self):
        """ Jumble the SliderPuzzle """
        self.jumbler.randomize()
        self.full_refresh()

    def load_image (self, filename, width=-1, height=-1):
        """ Loads an image from the file """
        if width == height == -1:
            self.image.set_from_file(filename)
        else:
            img = gtk.Image()
            img.set_from_file(filename)
            pb = img.get_pixbuf()
            w,h = calculate_relative_size(pb.get_width(), pb.get_height(), width, height)
            scaled_pb = pb.scale_simple(w,h, gtk.gdk.INTERP_BILINEAR)
            self.image.set_from_pixbuf(scaled_pb)
        self.full_refresh()

    def show_image (self):
        """ Shows the full image, used as visual clue for solved puzzle """
        # Delete everything
        self.foreach(self.remove)
        if hasattr(self, 'pieces'):
            del self.pieces
        # Resize to a single cell and use that for the image
        self.resize(1,1)
        self.attach(self.image, 0,1,0,1)
        self.image.show()

def _test():
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    _test()
