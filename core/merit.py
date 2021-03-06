#!/usr/bin/env/python
"""
Pyrate - Optical raytracing based on Python

Copyright (C) 2014 Moritz Esslinger moritz.esslinger@web.de
               and    Johannes Hartung j.hartung@gmx.net
               and    Uwe Lippmann  uwe.lippmann@web.de

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import numpy as np
import aim
import field
import raster
import pupil
from ray import RayPath

def mySimpleDumbRMSSpotSizeMeritFunction(s):
    """
    This is a test Merit function for RMS spot size on axis with modifications implemented suggested by Mo

    :param s: OpticalSystem object

    :return merit: merit function value (float)
    """

    nray = 1e3  # number of rays
    rasterType= raster.RectGrid

    pupilType= pupil.StopDiameter # EntrancePupilDiameter
    pupilSizeParameter = 3.0 # 5.5
    wavelength = 0.55
    stopPosition = 5

    fieldType= field.ObjectHeight
    fieldpoints = [0., 0.1, -0.1]

    aimy = aim.aimFiniteByMakingASurfaceTheStop(s, pupilType, pupilSizeParameter, fieldType, rasterType, nray, wavelength, stopPosition)


    # RMS at all field points
    merit_squared = 0

    for y in fieldpoints:
        initialBundle = aimy.getInitialRayBundle(s, array([0.,y]), wavelength)
        raypath_on_axis = RayPath(initialBundle, s)

        merit_squared += ( raypath_on_axis.raybundles[-1].getRMSspotSizeCentroid() )**2

    return merit_squared



def myPersonalMeritFunctionForTestingPurposes(s):
    """
    This is a test Merit function for RMS of a finite corrected 20x microscope objective.
    The microscope sample is on the object side.
    Parfocal or tube length are not enforced.

    :param s: OpticalSystem object

    :return merit: merit function value (float)
    """
    nray = 1E3  # number of rays
    rasterType= raster.RectGrid

    pupilType= pupil.ObjectSpaceNA
    pupilSizeParameter = 0.25
    wavelengths = [0.48, 0.55, 0.65]
    stopPosition = 5
    mag = 20

    fieldType= field.ObjectHeight
    fieldpoints = 1./mag * 0.5*array([0., 17.5,25.])

    aimy = aim.aimFiniteByMakingASurfaceTheStop(s, pupilType, pupilSizeParameter, fieldType, rasterType, nray, wavelengths[1], stopPosition)


    # RMS at all field points
    merit_squared = 0
    for wavelength in wavelengths:
        for y in fieldpoints:

            initialBundle = aimy.getInitialRayBundle(s, array([0.,y]), wavelength)
            raypath_on_axis = RayPath(initialBundle, s)

            merit_squared += ( raypath_on_axis.raybundles[-1].getRMSspotSizeCentroid() )**2


    initialBundle = aimy.getInitialRayBundle(s, array([0.,0.]), wavelengths[1])

    # magnification
    merit_squared += ( s.getParaxialMagnification(initialBundle) - mag ) **2

    # positive thicknesses
    for i in arange(s.getNumberOfSurfaces()):
        merit_squared += ( int(s.getThickness(i) < 0) )


    return merit_squared
