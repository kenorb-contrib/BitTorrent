#!/usr/bin/env python

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Written by Matt Chisholm

# What is this?

# This is just a quick and dirty set of heuristics to guess the
# maximum optimal upload speed for a given download and upload rate. I
# used it to calculate the values in speed_classes in the GUI and it
# is committed so that it can be used again when the popular net
# connection speeds/types change.

from __future__ import division
last = 0
size_classes = {}
for title,dnrate,uprate in (('modem',    44,    44), # in Kbps
                            ('DSL'  ,   384,   128),
                            ('DSL'  ,   768,   128),
                            ('DSL'  ,   768,   256),
                            ('DSL'  ,  1500,   256),
                            ('DSL'  ,  1500,   768),
                            ('DSL'  ,  6000,   768),
                            ('T1'   ,  1500,  1500),
                            ('E1'   ,  2048,  2048),
                            ('T3'   , 44736, 44736),
                            ('OC3'  ,155000,155000),
                            ('local',   1e9,   1e9), # 1Gbit local network
                   ):
    # for calculating optimum upload rates:
    max_up = (uprate - (dnrate * 0.02666666667)) / 8
    # for calculating optimum download rates:
    max_down = (dnrate - (dnrate * 0.02666666667)) / 8
    label = title
    title += '\t%dKb/s\t%dKb/s\t%0.2fKB/s\t%0.2fKB/s'%(uprate,dnrate,max_up,max_down)
    size_classes[max_up] = title
    last = max_up

speeds = size_classes.keys()
speeds.sort()
print "type\tup\tdown\tup\tdown"
for s in speeds:
    print size_classes[s]
    
