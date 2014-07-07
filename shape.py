#!/usr/bin/env/python

from numpy import *

class Shape(object):
    """
    Virtual Class for all surface shapes.
    The shape of a surface provides a function to calculate
    the intersection point with a ray.
    """

    def __init__(self):
        self.curvature = 0 # spherical curvature
        self.sdia = 0 # semi-diameter
        raise NotImplementedError()

    def intersect(self, raybundle):
        """
        Intersection routine returning intersection point
        with ray and normal vector of the surface.
        :param raybundle: RayBundle that shall intersect the surface. (RayBundle Object)
        :return t: geometrical path length to the next surface (1d numpy array of float)
        :return normal: surface normal vectors (2d numpy 3xN array of float) 
        """
        raise NotImplementedError()

    def getSag(self, x, y):
        """
        Returns the sag of the surface for given coordinates - mostly used
        for plotting purposes.
        :param x: x coordinate perpendicular to the optical axis (list or numpy 1d array of float)
        :param y: y coordinate perpendicular to the optical axis (list or numpy 1d array of float)
        :return z: sag (list or numpy 1d array of float)
        """
        raise NotImplementedError()

    def getCentralCurvature(self):
        """
        Returns the curvature ( inverse local radius ) on the optical axis.
        :return curv: (float)
        """
        raise NotImplementedError()

    def draw2d(self, ax, offset = [0,0], vertices=100, color="grey"):
        """
        Plots the surface in a matplotlib figure.
        :param ax: matplotlib axes handle 
        :param offset: y and z offset (list or 1d numpy array of 2 floats)
        :param vertices: number of points the polygon representation of the surface contains (int)
        :param color: surface draw color (str)
        """
        raise NotImplementedError()
        
    def draw3d(self, offset = [0,0,0], tilt=[0,0,0], color="grey"):
        """
        To do: find proper rendering package
        """
        raise NotImplementedError()
        

class Conic(Shape):
    """
    Defines a rotationally symmetric conic section (sphere, paraboloid,
    ellipsoid, hyperboloid).
    """
    def __init__(self, curv=0.0, cc=0.0, semidiam=0.0):
        """
        Create conic surface.
        :param curv: Curvature of the surface.
        :param cc: Conic constant.
        :param semidiam: Semi-diameter of the surface.
        """
        self.curvature = curv
        self.conic = cc
        self.sdia = semidiam

    def getSag(self, x, y):
        rs = x**2 + y**2
        return self.curvature * rs / ( 1 + sqrt ( 1 - (1+self.conic) * self.curvature**2 * rs) )

    def getCentralCurvature(self):
        # Conic curvature on axis is only influenced by spherical curvature term
        return self.curvature

    def intersect(self, raybundle):
        rayDir = raybundle.rayDir
        
        r0 = raybundle.o
        
        F = rayDir[2] - self.curvature * ( rayDir[0] * r0[0] + rayDir[1] * r0[1] + rayDir[2] * r0[2] * (1+self.conic) )
        G = self.curvature * ( r0[0]**2 + r0[1]**2 + r0[2]**2 * (1+self.conic) ) - 2 * r0[2]
        H = - self.curvature - self.conic * self.curvature * rayDir[2]**2
    
        square = F**2 + H*G     
    
        # indices of rays that don't intercest with the sphere
        
        # indicesOfNan = find( square < 0 ) 
        
        # to do: add rays outside the clear aperture to the indicesOfNan list    

        t = G / ( F + sqrt( square ) )
        
        intersection = r0 + raybundle.rayDir * t
        
        # Normal
        normal    = zeros(shape(r0), dtype=float)
        normal[0] =   - self.curvature * intersection[0]
        normal[1] =   - self.curvature * intersection[1]
        normal[2] = 1 - self.curvature * intersection[2] * (1+self.conic)
        
        absn = sqrt( sum(normal**2, axis=0) )
        
        normal[0] = normal[0] / absn
        normal[1] = normal[1] / absn
        normal[2] = normal[2] / absn
        
        return intersection, t, normal

    def draw2d(self, ax, offset = [0,0], vertices=100, color="grey"):
        y = self.sdia * linspace(-1,1,vertices)
        z = self.getSag(0,y)
        
        ax.plot(z+offset[1],y+offset[0], color)
             

class Asphere(Shape):
    """

    """
    pass


class Aperture(object):
    """
    Base class representing the aperture of a surface.
    Subclasses may define the actual shapes (circular,
    elliptic, rectangular, etc.)
    """
    pass
