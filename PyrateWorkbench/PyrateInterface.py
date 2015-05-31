# standard include

import time
from numpy import *


import material
import surfShape
import aim
import field
import pupil
import raster
from ray import RayPath
from optical_system import OpticalSystem, Surface

# freecad modules

import FreeCAD
import Part
import Points

# to gain variables with their own supervision
from traits.api import HasTraits, String, Int, Float
import traitsui




class OpticalSystemInterface(HasTraits):

    trolo = Float
    blub = Int
    bla = String

    def __init__(self):
        self.trolo = 0.0
        self.blub = 1
        self.bla = "Hallo"

        self.surfaceviews = []

        self.os = OpticalSystem()

    def dummycreate(self): # should only create the demo system, will be removed later
        self.os.surfaces[0].thickness.val = 2.0 # it is not good give the object itself a thickness if the user is not aware of that
        self.os.surfaces[1].shape.sdia.val = 1e10 # radius of image plane may not be zero to be sure to catch all rays
        self.os.insertSurface(1, Surface(surfShape.Conic(curv=1/-5.922, semidiam=0.55), thickness=3.0, material=material.ConstantIndexGlass(1.7))) # 0.55
        self.os.insertSurface(2, Surface(surfShape.Conic(curv=1/-3.160, semidiam=1.0), thickness=5.0)) # 1.0
        self.os.insertSurface(3, Surface(surfShape.Conic(curv=1/15.884, semidiam=1.3), thickness=3.0, material=material.ConstantIndexGlass(1.7))) # 1.3
        self.os.insertSurface(4, Surface(surfShape.Conic(curv=1/-12.756, semidiam=1.3), thickness=3.0)) # 1.3
        self.os.insertSurface(5, Surface(surfShape.Conic(semidiam=1.01), thickness=2.0)) # semidiam=1.01 # STOP
        self.os.insertSurface(6, Surface(surfShape.Conic(curv=1/3.125, semidiam=1.0), thickness=3.0, material=material.ConstantIndexGlass(1.5))) # semidiam=1.0
        self.os.insertSurface(7, Surface(surfShape.Conic(curv=1/1.479, semidiam=1.0), thickness=19.0)) # semidiam=1.0

    def makeSurfaceFromSag(self, surface, startpoint = [0,0,0], R=50.0, rpoints=10, phipoints=12):
        surPoints = []
        pts = Points.Points()
        pclpoints = []
        for r in linspace(0,R,rpoints):
            points = []
            for a in linspace(0.0, 360.0-360/float(phipoints), phipoints):
                x = r * math.cos(a*math.pi/180.0)# + startpoint[0]
                y = r * math.sin(a*math.pi/180.0)# + startpoint[1]
                z = surface.shape.getSag(x, y)# + startpoint[2]
                p = FreeCAD.Base.Vector(x,y,z)
                p2 = FreeCAD.Base.Vector(x+startpoint[0], y+startpoint[1], z+startpoint[2])
                points.append(p)
                pclpoints.append(p2)
            surPoints.append(points)
        pts.addPoints(pclpoints)
        sur = Part.BSplineSurface()
        sur.interpolate(surPoints)
        sur.setVPeriodic()
        surshape  = sur.toShape()
        surshape.translate(tuple(startpoint))
        return (surshape, pts)


    def createSurfaceViews(self):
        offset = [0, 0, 0]
        doc = FreeCAD.ActiveDocument

        for (index, surf) in enumerate(self.os.surfaces):
            # all accesses to the surface internal variables should be performed by appropriate supervised functions
            # to not violate the privacy of the class

            FCsurfaceobj = doc.addObject("Part::Feature", "Surf_"+str(index))
            FCsurfaceview = FCsurfaceobj.ViewObject

            if surf.shape.sdia.val > 0.5 and surf.shape.sdia.val < 100.0: # boundaries for drawing the surfaces, should be substituted by appropriate drawing conditions
                (FCsurface, FCptcloud) = self.makeSurfaceFromSag(surf, offset, surf.shape.sdia.val, 100, 360)
                #Points.show(ptcloud)
                #Part.show(surface)

                #pointcloudview = ptcloud.ViewObject
                FCsurfaceobj.Shape = FCsurface

                FCsurfaceview.ShapeColor = (0.0, 0.0, 1.0)
                #surfaceview.show()
            else:
                FCplaneshape = Part.makePlane(2,2)
                newoffset = [offset[0] - 1, offset[1] - 1, offset[2]]
                FCplaneshape.translate(tuple(newoffset))
                FCsurfaceobj.Shape = FCplaneshape

                FCsurfaceview.ShapeColor = (1.0, 0.0, 0.0)

            offset[2] += surf.getThickness() # may be substituted later by a real coordinate transformation (coordinate break)

            time.sleep(0.1)

        doc.recompute()


    def makeRayBundle(self, raybundle, offset):
        raysorigin = raybundle.o
        nrays = shape(raysorigin)[1]

        pp = Points.Points()
        sectionpoints = []

        res = []

        for i in range(nrays):
            if raybundle.t[i] > 1e-6:
                x1 = raysorigin[0, i] + offset[0]
                y1 = raysorigin[1, i] + offset[1]
                z1 = raysorigin[2, i] + offset[2]

                x2 = x1 + raybundle.t[i] * raybundle.rayDir[0, i]
                y2 = y1 + raybundle.t[i] * raybundle.rayDir[1, i]
                z2 = z1 + raybundle.t[i] * raybundle.rayDir[2, i]

                res.append(Part.makeLine((x1,y1,z1),(x2,y2,z2))) # draw ray
                sectionpoints.append((x2,y2,z2))
        pp.addPoints(sectionpoints)
        Points.show(pp) # draw intersection points per raybundle per field point

        return res


    def makeRaysFromRayPath(self, raypath, offset):
        Nsurf = len(raypath.raybundles)
        offx = offset[0]
        offy = offset[1]
        offz = offset[2]
        for i in arange(Nsurf):
            offz += self.os.surfaces[i].getThickness()
            [Part.show(j) for j in self.makeRayBundle(raypath.raybundles[i], offset=(offx, offy, offz))]



    def createRayViews(self):

        numrays = 5
        pupilsize = 5.5
        stopposition = 5
        wavelengthparam = 0.55

        fieldvariable = [0., 0.]
        fieldvariable2 = [0., 0.1]


        aimy = aim.aimFiniteByMakingASurfaceTheStop(self.os, pupilType= pupil.EntrancePupilDiameter, \
                                                    pupilSizeParameter=pupilsize, \
                                                    fieldType= field.ObjectHeight, \
                                                    rasterType= raster.RectGrid, \
                                                    nray=numrays, wavelength=wavelengthparam, \
                                                    stopPosition=stopposition)
        aimy.setPupilRaster(rasterType= raster.ChiefAndComa, nray=numrays)
        initialBundle2 = aimy.getInitialRayBundle(self.os, fieldXY=array(fieldvariable), wavelength=wavelengthparam)

        r2 = RayPath(initialBundle2, self.os)

        initialBundle3 = aimy.getInitialRayBundle(self.os, fieldXY=array(fieldvariable2), wavelength=wavelengthparam)
        r3 = RayPath(initialBundle3, self.os)


        self.makeRaysFromRayPath(r2,offset=(0,0,0))
        self.makeRaysFromRayPath(r3,offset=(0,0,0))

    def returnPrescriptionData(self):

        # get effective focal length and so on from self.os and put it into some string which could be shown by
        # some dialog


OSinterface = OpticalSystemInterface()






