#!/usr/bin/env/python
"""
Pyrate - Optical raytracing based on Python

Copyright (C) 2014 Moritz Esslinger moritz.esslinger@web.de
               and Johannes Hartung j.hartung@gmx.net
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
import math
from ray import RayBundle
import optimize

from globalconstants import standard_wavelength, eps0

class Material(optimize.ClassWithOptimizableVariables):
    """Abstract base class for materials."""
        
    def __init__(self, lc, name="", comment=""):
        super(Material, self).__init__()
        """
        virtual constructor
        """
        self.setName(name)
        self.comment = comment
        self.lc = lc

    def refract(self, raybundle, actualSurface):
        """
        Class describing the interaction of the ray at the surface based on the material.

        :param raybundle: Incoming raybundle ( RayBundle object )
        :param intersection: Intersection point with the surface ( 2d numpy 3xN array of float )
        :param normal: Normal vector at the intersection point ( 2d numpy 3xN array of float )
        :param validIndices: whether the rays did hit the shape correctly (1d numpy array of bool)

        :return newray: rays after surface interaction ( RayBundle object )
        """
        raise NotImplementedError()

    def reflect(self, raybundle, actualSurface):
        """
        Class describing the interaction of the ray at the surface based on the material.

        :param raybundle: Incoming raybundle ( RayBundle object )
        :param intersection: Intersection point with the surface ( 2d numpy 3xN array of float )
        :param normal: Normal vector at the intersection point ( 2d numpy 3xN array of float )
        :param validIndices: whether the rays did hit the shape correctly (1d numpy array of bool)

        :return newray: rays after surface interaction ( RayBundle object )
        """
        raise NotImplementedError()


    def getEpsilonTensor(self, x, n, k, wave=standard_wavelength):
        """
        Calculate epsilon tensor if needed. (isotropic e.g.) eps = diag(3)*n^2
        
        :return epsilon (3x3 numpy array of complex)
        """
        raise NotImplementedError()
        
    def calcXi(self, x, n, k_inplane, wave=standard_wavelength):
        """
        Calculate normal component of k after refraction.
        
        :param n (3xN numpy array of float) 
                normal of surface in local coordinates
        :param k_inplane (3xN numpy array of float) 
                incoming wave vector inplane component in local coordinates
        
        :return (xi, valid) tuple of (3x1 numpy array of complex, 
                3x1 numpy array of bool)
        """
        raise NotImplementedError()
        
    def calcXiNormalDerivative(self, x, n, k_inplane, wave=standard_wavelength):
        
        raise NotImplementedError()
        
    def calcXiKinplaneDerivative(self, x, n, k_inplane, wave=standard_wavelength):

        raise NotImplementedError()
        
    
    def setCoefficients(self, coefficients):
        """
        Sets the dispersion coefficients of a glass (if any)

        :param coefficients: float or list or numpy array of float
        """
        raise NotImplementedError()

    def getCoefficients(self):
        """
        Returns the dispersion coefficients of a glass
        """
        raise NotImplementedError()

        
    def propagate(self, raybundle, nextSurface):
        """
        Propagates raybundle to nextSurface. In the most simple case this
        just adds the end point at nextSurface intersection to the raybundle
        """
        raise NotImplementedError()


class IsotropicMaterial(Material):
    
    def __init__(self, lc, n=1.0, name="", comment=""):
        super(IsotropicMaterial, self).__init__(lc, name, comment)

    def getEpsilonTensor(self, x, n, k, wave=standard_wavelength):
        raise NotImplementedError()

    def calcXiNormalDerivative(self, x, n, k_inplane, wave=standard_wavelength):
        return np.zeros_like(n)        
        
    def calcXiKinplaneDerivative(self, x, n, k_inplane, wave=standard_wavelength):
        (xi, valid) = self.calcXi(n, k_inplane, wave=wave)
        return -k_inplane/xi

    def calcEfield(self, x, n, k, wave=standard_wavelength):
        # TODO: Efield calculation wrong! For polarization you have to calc it correctly!
        ey = np.zeros_like(k)
        ey[1,:] =  1.
        return np.cross(k, ey, axisa=0, axisb=0).T

        

    def calcXi(self, x, normal, k_inplane, wave=standard_wavelength):
        # Depends on x in general: to be compatible with grin materials
        # and to reduce reimplementation effort
        
        k2_squared = 4.*math.pi**2/wave**2/(3.*eps0)*np.trace(self.getEpsilonTensor(x, normal, None, wave))
        square = k2_squared - np.sum(k_inplane * k_inplane, axis=0)

        # make total internal reflection invalid
        valid = (square > 0)

        xi = np.sqrt(square)
        
        return (xi, valid)


    def refract(self, raybundle, actualSurface):

        k1 = self.lc.returnGlobalToLocalDirections(raybundle.k[-1])
                
        globalnormal = actualSurface.shape.getGlobalNormal(raybundle.x[-1])
        normal = self.lc.returnGlobalToLocalDirections(globalnormal)
        xlocal = self.lc.returnGlobalToLocalPoints(raybundle.x[-1])

        k_inplane = k1 - np.sum(k1 * normal, axis=0) * normal

        (xi, valid_refraction) = self.calcXi(xlocal, normal, k_inplane, wave=raybundle.wave)
        
        valid = raybundle.valid[-1] * valid_refraction

        k2 = k_inplane + xi * normal

        # return ray with new direction and properties of old ray
        # return only valid rays
        orig = raybundle.x[-1][:, valid]        
        newk = self.lc.returnLocalToGlobalDirections(k2[:, valid])

        Efield = self.calcEfield(xlocal, normal, newk, wave=raybundle.wave)

        return RayBundle(orig, newk, Efield, raybundle.rayID[valid], raybundle.wave)


    def reflect(self, raybundle, actualSurface):

        k1 = self.lc.returnGlobalToLocalDirections(raybundle.k[-1])
        
        globalnormal = actualSurface.shape.getGlobalNormal(raybundle.x[-1])
        normal = self.lc.returnGlobalToLocalDirections(globalnormal)
        xlocal = self.lc.returnGlobalToLocalPoints(raybundle.x[-1])

        k_inplane = k1 - np.sum(k1 * normal, axis=0) * normal

        (xi, valid_refraction) = self.calcXi(xlocal, normal, k_inplane, wave=raybundle.wave)
        
        valid = raybundle.valid[-1] * valid_refraction

        k2 = -k_inplane + xi * normal # changed for mirror, all other code is doubled

        # return ray with new direction and properties of old ray
        # return only valid rays
        orig = raybundle.x[-1][:, valid]        
        newk = self.lc.returnLocalToGlobalDirections(k2[:, valid])

        Efield = self.calcEfield(xlocal, normal, newk, wave=raybundle.wave)
        
        return RayBundle(orig, newk, Efield, raybundle.rayID[valid], raybundle.wave)


    def propagate(self, raybundle, nextSurface):

        """
        Propagates through material until nextSurface.
        Has to check for aperture (TODO). Changes raybundle!
        
        :param raybundle (RayBundle object), gets changed!
        :param nextSurface (Surface object)
        """

        nextSurface.intersect(raybundle)

class ConstantIndexGlass(IsotropicMaterial):
    """
    A simple glass defined by a single refractive index.
    """
    def __init__(self, lc, n=1.0, name="", comment=""):
        super(ConstantIndexGlass, self).__init__(lc, name, comment)

        self.n = optimize.OptimizableVariable(value=n)
        self.addVariable("refractive index", self.n)

            
    def getEpsilonTensor(self, x, n, k, wave=standard_wavelength):
        (num_dims, num_pts) = np.shape(x)
        mat = np.zeros((num_dims, num_dims, num_pts))
        mat[0, 0, :] = 1.
        mat[1, 1, :] = 1.
        mat[2, 2, :] = 1.
        
        return mat*eps0*self.n()**2


    def setCoefficients(self, n):
        """
        Sets the refractive index.

        :param n: refractive index (float)
        """
        self.n.val = n

    def getIndex(self, ray):
        return self.n.evaluate()



class ModelGlass(ConstantIndexGlass):
    def __init__(self, lc, n0_A_B=(1.49749699179, 0.0100998734374*1e-3, 0.000328623343942*(1e-3)**3.5), name="", comment=""):
        """
        Set glass properties from the Conrady dispersion model.
        The Conrady model is n = n0 + A / wave + B / (wave**3.5)
        n0 [1], A [mm], B[mm**3.5]        
        
        :param tuple (n0, A, B) of float
        """
        super(ModelGlass, self).__init__(lc=lc, n=n0_A_B[0], name=name, comment=comment)


        self.n0 = optimize.OptimizableVariable(value=n0_A_B[0])
        self.A = optimize.OptimizableVariable(value=n0_A_B[1])
        self.B = optimize.OptimizableVariable(value=n0_A_B[2])
        
        self.addVariable("Conrady n0", self.n0)
        self.addVariable("Conrady A", self.A)
        self.addVariable("Conrady B", self.B)


    def setCoefficients(self, n0_A_B):
        """
        Sets the coefficients of the Conrady model.

        :param n0_A_B: coefficients (list or 1d numpy array of 3 floats)
        """
        self.n0.setvalue(n0_A_B[0])
        self.A.setvalue(n0_A_B[1])
        self.B.setvalue(n0_A_B[2])

    def getIndex(self, raybundle):
        """
        Private routine for all isotropic materials obeying the Snell law of refraction.

        :param raybundle: RayBundle object containing the wavelength of the rays.

        :return index: refractive index at respective wavelength (float)
        """
        wave = raybundle.wave  # wavelength in um
        return self.n0.evaluate() + self.A.evaluate() / wave + self.B.evaluate() / (wave**3.5)

    def getEpsilonTensor(self, x, n, k, wave=standard_wavelength):
        n = self.n0() + self.A() / wave + self.B() / (wave**3.5)
        return np.eye(3)*n**2

    def calcCoefficientsFrom_nd_vd_PgF(self, nd=1.51680, vd=64.17, PgF=0.5349):
        """
        Calculates the dispersion formula coefficients from nd, vd, and PgF.

        :param nd: refractive index at the d-line ( 587.5618 nm ) (float)
        :param vd: Abbe number with respect to the d-line (float)
        :param PgF: partial dispersion with respect to g- and F-line (float)
        """

        nF_minus_nC = (nd - 1) / vd
        B = (0.454670392956 * nF_minus_nC * (PgF - 0.445154791693))*(1e-3)**3.5
        A = (1.87513751845 * nF_minus_nC - B * 15.2203074842)*1e-3
        n0 = nd - 1.70194862906e3 * A - 6.43150432188*(1e3**3.5) * B

        self.setCoefficients((n0, A, B))

    def calcCoefficientsFrom_nd_vd(self, nd=1.51680, vd=64.17):
        """
        Calculates the dispersion formula coefficients, assuming the glass on the normal line.

        :param nd: refractive index at the d-line ( 587.5618 nm ) (float)
        :param vd: Abbe number (float)
        """

        PgF = 0.6438 - 0.001682 * vd
        self.calcCoefficientsFrom_nd_vd_PgF(nd, vd, PgF)

    def calcCoefficientsFromSchottCode(self, schottCode=517642):
        """
        Calculates the dispersion formula coefficients from the Schott Code, assuming the glass to be on the normal line.
        Less accurate than calcCoefficientsFrom_nd_vd_PgF().

        :param schottCode: 6 digit Schott Code (first 3 digits are 1000*(nd-1), last 3 digits are 10*vd)
        """
        if type(schottCode) is int and schottCode >= 1E5 and schottCode < 1E6:
            first3digits = schottCode / 1000
            last3digits = schottCode % 1000
            nd = 1 + 0.001 * first3digits
            vd = 0.1 * last3digits
        else:
            print "Warning: Schott Code must be a 6 digit positive integer number. Substituting invalid number with N-BK7."
            nd = 1.51680
            vd = 64.17
        self.calcCoefficientsFrom_nd_vd(nd, vd)


