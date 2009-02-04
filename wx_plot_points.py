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

from BitTorrent.platform import install_translation
install_translation()

import os
import sys
import math
from traceback import *
import time
app_name = "BitTorrent"
import wx
#from BitTorrent.GUI import Window
from correlation import SizedList
import matfunc
import random
import filter_points

def ratio_sum_lists(a, b):
    tx = float(sum(a))
    ty = float(sum(b))
    return tx / max(ty, 0.0001)


class PlotWindow(wx.Frame):

    def add_points(self, u, d, t, limit):
        print "rate", u, limit
        open("u_points.txt", 'a').write(("%f %f %f" % (t, u, time.time())) + '\n')
        return 
        #open("d_points.txt", 'a').write(("%f %f" % (t, d)) + '\n')
        self.area_expose_cb(self, None)
        #self.area_expose_cb(self.d_area, None)

        self.points[0].append(u)
        self.points[1].append(t)
        #self.points[0].append(d)
        #self.points[1].append(t)


    def scale_points(self, a, b, w, h, invert=True):
        ma = float(max(max(a), 1))
        mb = float(max(max(b), 1))
        def inv_scale(x, m1, m2):
            if m1 == 0:
                return 0
            return int((1.0 - float(x)/m1) * float(m2))
        def scale(x, m1, m2):
            if m1 == 0:
                return 0
            return int((float(x)/m1) * float(m2))
        ma_s = lambda x : scale(x, ma, w)
        a = map(ma_s, a)
        if invert:
            mb_s = lambda x : inv_scale(x, mb, h)
        else:
            mb_s = lambda x : scale(x, mb, h)
        b = map(mb_s, b)
        return a, b, ma, mb        

    def get_lines(self, w, a, b, c):
        points = []
        for x in xrange(0, int(w*1.1), int(w*0.1) + 1):
            y = (a*(x**2)) + b*x + c
            points.append((int(x), int(y)))
        return points
    def get_lines1(self, w, a, b):
        points = []
        for x in xrange(0, int(w*1.1), int(w*0.1) + 1):
            y = (a*(x)) + b
            points.append((int(x), int(y)))
        return points
    def get_lines2(self, w, a, b, c, d):
        points = []
        for x in xrange(0, int(w*1.1), int(w*0.1) + 1):
            y = (a*(x**3)) + (b*(x**2)) + (c*(x)) + d
            points.append((int(x), int(y)))
        return points

    def draw_points(self, area, a, b):
        if len(a) < 3:
            return
        x1 = a[-1]
        y1 = b[-1]
        w, h = area.GetSize()
        a, b, ma, mb = self.scale_points(a, b, w, h)
        c = zip(a, b)
        c = filter_points.remove_dupes(c)
        
        area.Clear()
        area.SetPen(wx.Pen((0,0,0)))
       
        area.DrawPoints(c)

##        try:
##            rc = c#random.sample(c, 1000)
##            ra = [ x for x, y in rc ]
##            rb = [ y for x, y in rc ]
##
##            #a, b, c = matfunc.polyfit((ra, rb))
##            #lines = self.get_lines(w, a, b, c)
##            #a, b, c, d = matfunc.polyfit((ra, rb), 3)
##            a, b = matfunc.polyfit((ra, rb), 1)
##            lines = self.get_lines1(w, a, b)
##            area.DrawLines(lines)
##            #area.draw_lines(area.gc, lines)
##        except Exception, e:# ZeroDivisionError:
##            print e
##            pass


        u = SizedList(10)
        t = SizedList(10)
        points = []
        for (x,y) in c:
            u.append(x)
            t.append(y)

            #x2 = float(sum(u)) / float(len(u))
            x2 = x
            y2 = h - filter_points.standard_deviation(t)
            #y2 = float(sum(t)) / float(len(t))
            points.append((x2,y2))
                    
        #area.draw_lines(area.gc, points)
        area.SetPen(wx.Pen((255,0,0)))
        area.DrawPoints(points)

        def avg_atan2_p(a, b):
            atan = 0
            x = 0
            y = 0
            as = 0
            t = float(len(a))
            for p1, p2 in zip(a, b):
                atan += math.atan2(p1, p2) / t
                try:
                    as += math.sqrt(p1**2 + p2**2) / t
                except ZeroDivisionError, e:
                    print e
            
            x = math.sin(atan) * as
            y = math.cos(atan) * as
            return x, y

        def median(a, b):
            a = list(a)
            a.sort()
            b = list(b)
            b.sort()
            ap = min(len(a)-1, 5)
            bp = min(len(b)-1, 5)
            return a[ap], b[bp]           
            

        u = SizedList(10)
        t = SizedList(10)
        points = []
        for (x,y) in c:
            u.append(x)
            t.append(y)

            x2, y2 = avg_atan2_p(u, t)
            #x2, y2 = median(u,t)
            #x2 = x
            #y2 = float(sum(t)) / float(len(t))
            points.append((x2,y2))
                    
        #area.draw_lines(area.gc, points)
        area.SetPen(wx.Pen((0,0,255)))
        #area.DrawPoints(points)        

##        ##############################
##        u = SizedList(10)
##        t = SizedList(10)
##
##        def get_sqrt_avg(a):
##            at = 0
##            for i in a:
##                at += i**2
##            at = math.sqrt(at)
##            return at
##        
##        points_x = []
##        points_y = []
##        for (x,y) in c:
##            u.append(x)
##            t.append(y)
##
##            x2 = get_sqrt_avg(u)
##            y2 = get_sqrt_avg(t)
##            #points.append((x2,y2))
##            points_x.append(x2)
##            points_y.append(y2)
##                    
##        #area.draw_lines(area.gc, points)
##        area.SetPen(wx.Pen((0,0,255)))
##        a, b, ma, mb = self.scale_points(points_x, points_y, w, h, False)
##        c = zip(a, b)
##        c = filter_points.remove_dupes(c)
##        area.DrawPoints(c)
##        #############################
        
       
        #area.pangolayout.set_text("%dbps %dms" % (int(x1), int(y1)))
        #area.draw_layout(area.gc, x, y, area.pangolayout)


        t = "%dbps" % (int(ma))        
        #area.pangolayout.set_text()
        tw, th = area.GetTextExtent(t)
        #area.draw_layout(area.gc, w-tw, h-th, area.pangolayout)
        area.DrawText(t, w-tw, h-th)

        #area.pangolayout.set_text("%dms" % (int(mb)))
        #area.draw_layout(area.gc, 0, 0, area.pangolayout)
        area.DrawText("%dms" % (int(mb)), 0, 0)
    
    def area_expose_cb(self, event):
        dc = wx.ClientDC(self)
        def DrawPoints(points):
            for point in points:
                dc.DrawPoint(*point)
        dc.DrawPoints = DrawPoints
        self.draw_points(dc, *self.points)
        return True

                
def create_plotwindow(x=None, y=None):
    if x == None:
        x = SizedList(2000)
    if y == None:
        y = SizedList(2000)
    u_plotwindow = PlotWindow(None)
    u_plotwindow.SetTitle("Upload")
    u_plotwindow.SetBackgroundColour((255,255,255))
    u_plotwindow.points = [x, y]

    u_plotwindow.Show()

    u_plotwindow.Bind(wx.EVT_SIZE, u_plotwindow.area_expose_cb)

    return u_plotwindow


class MyApp(wx.App):

    def OnInit(self):
        start = None
        clock = 0
        a_u = []
        a_t = []
        b = open(sys.argv[1], 'r').read()
        if b[0] == '(':
            a_t, a_u = eval(b)
        else:
            last_t = -1
            for l in b.split('\n'):
                try:
                    t, u, clock = l.split(' ')
                except:
                    try:
                        t, u = l.split(' ')
                    except:
                        break
                clock = float(clock)
                if start == None:
                    start = clock
                #elif clock < (start + (60 * 70)):
                #    continue
                #elif clock > (start + (60 * 90)):
                #    print clock
                #    break
                t = round(float(t))
                if t == last_t:
                    continue
                u = round(float(u))
                a_t.append(t)
                a_u.append(u)
                last_t = t
        a_t, a_u = filter_points.filter_points(a_t, a_u)
        print filter_points.standard_deviation(a_t)
        f = create_plotwindow(a_u, a_t)
        self.SetTopWindow(f)
        #u_plotwindow.area_expose_cb(u_plotwindow.u_area, None)
        
        return True

if __name__ == '__main__':

    try:
        import psyco
        psyco.profile()
    except ImportError:
        pass

    app = MyApp(0)
    app.MainLoop()
        
