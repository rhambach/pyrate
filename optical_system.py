#!/usr/bin/env/python

import inspect
import shape as surfShape # the name 'shape' already denotes the dimensions of a numpy array
import material

from numpy import *



class Surface():
    """
    Represents a surface of an optical system.
    
    :param shap: Shape of the surface. Claculates the intersection with rays. ( Shape object or child )
    :param mater: Material of the volume behind the surface. Claculates the refraction. ( Material object or child )
    :param thickness: distance to next surface on the optical axis
    """
    def __init__(self, thickness = 0.0):
        self.shap  = surfShape.Conic()
        self.mater = material.ConstantIndexGlass()
        self.thickness = thickness
        
        self.availableShapeNames, self.availableShapeClasses = self.getAvailableShapes()
        self.availableMaterialTypeNames, self.availableMaterialTypeClasses = self.getAvailableMaterialTypes()


    def getAvailableShapes(self):
        """
        Parses shape.py for class definitions. Returns all but shape.Shape
        
        :return listOfShapeNames: List of strings
        :return listOfShapeClasses: List of Class references
        """
        listOfShapeNames = []
        listOfShapeClasses = []
        for name, cla in inspect.getmembers(surfShape):
            fullname = str(cla).strip()
            if fullname.startswith('<class \'shape.') and fullname != '<class \'shape.Shape\'>':
                listOfShapeNames.append( name )
                listOfShapeClasses.append( cla )
        return listOfShapeNames, listOfShapeClasses

    def getAvailableMaterialTypes(self):
        """
        Parses material.py for class defintions. Returns all but material.Material
        
        :return listOfMaterialTypeNames: List of strings
        :return listOfMaterialTypeClasses: List of Class references
        """
        listOfMaterialTypeNames = []
        listOfMaterialTypeClasses = []
        for name, cla in inspect.getmembers(material):
            fullname = str(cla).strip()
            if fullname.startswith('<class \'material.') and fullname != '<class \'material.Material\'>':
                listOfMaterialTypeNames.append( name )
                listOfMaterialTypeClasses.append( cla )
        return listOfMaterialTypeNames, listOfMaterialTypeClasses


    def setMaterial(self, materialType):
        """
        Sets the material object self.mater
        
        :param materialType: name of the material dispersion formula (str)
        """
        
        if materialType in self.availableMaterialTypeNames:
            i = self.availableMaterialTypeNames.index(materialType)
            self.mater = self.availableMaterialTypeClasses[i]()
        else:
            print 'Warning: material type \'', materialType, '\' not found. setMaterial() aborted.'

    def setMaterialCoefficients(self, coeff):
        """
        Sets the coefficients that determine the material behavior. 

        :param coeff: coefficients. Type and format depend on Material child class.
        """
        self.mater.setCoefficients(coeff)

    def setShape(self, shapeName):
        """
        Sets the shape object self.shap
        
        :param shapeName: name of the shape type (str)
        """
        if shapeName in self.availableShapeNames:
            i = self.availableShapeNames.index(shapeName)

            # conserve the most basic parameters of the shape
            curv = self.shap.curvature 
            semidiam = self.shap.sdia
         
            self.shap = self.availableShapeClasses[i](curv=curv, semidiam=semidiam)
        else:
            print 'Warning: shape \'', materialType, '\' not found. setShape() aborted.'

    def draw2d(self, ax, offset = [0,0], vertices=100, color="grey"):
        self.shap.draw2d(ax, offset, vertices, color)      

    def getABCDMatrix(self, nextSurface, ray):
        """
        Returns an ABCD matrix of the current surface.
        The matrix is set up in geometric convention for (y, dy/dz) vectors.

        The matrix contains:
        - paraxial refraction from vacuum through the front surface
        - paraxial translation through the material
        - paraxial refraction at the rear surface into vacuum

        :param nextSurface: next surface for rear surface curvature (Surface object)
        :param ray: ray bundle to obtain wavelength (RayBundle object)
        :return abcd: ABCD matrix (2d numpy 2x2 matrix of float)
        """
        curvature = self.shap.getCentralCurvature()
        nextCurvature = nextSurface.shap.getCentralCurvature()
        return self.mater.getABCDMatrix(curvature, self.thickness, nextCurvature, ray)

class OpticalSystem():
    """
    Represents an optical system, consisting of several surfaces and materials inbetween.
    """
    def __init__(self):
        self.surfaces = []
        self.insertSurface(0) # object
        self.insertSurface(1) # image
        self.stopPosition = None        

    def insertSurface(self,position):
        """
        Inserts a new surface into the optical system.

        :param position: number of the new surface (int). 
           Surface that is currently at this position 
           and all following surface indices are incremented.
        """
        self.surfaces.insert(position, Surface() )
        
    def removeSurface(self,position):
        """
        Removes a surface from the optical system.

        :param position: number of the surface to remove (int) 
        """
        self.surfaces.pop(position)
        
    def getNumberOfSurfaces(self):
        """
        Returns the number of surfaces, including object and image (int)
        """
        return len(self.surfaces)
        
    def setThickness(self, position, thickness):
        """
        Sets the on-axis thickness of a surface.

        :param position: number of the surface (int) 
        """
        self.surfaces[position].thickness = thickness

    def getAvailableShapeNames(self):
        """
        Returns a list of valid Shape child class names (list of str)
        """
        return self.surfaces[0].availableShapeNames

    def getAvailableMaterialTypeNames(self):
        """
        Returns a list of valid Material child class names (list of str)
        """
        return self.surfaces[0].availableMaterialTypeNames

    def setMaterial(self, position, materialType):
        """
        Sets the material of a surface.

        :param position: number of the surface (int)
        :param materialType: name of the Material child class (str)
          See OpticalSystem.getAvailableMaterialTypeNames() for details.
        """
        self.surfaces[position].setMaterial(materialType)

    def setMaterialCoefficients(self, position, coeff):
        """
        Sets the coefficients that determine the material behavior. 

        :param position: number of the surface (int)
        :param coeff: coefficients. Type and format depend on Material child class.
        """
        self.surfaces[position].setMaterialCoefficients(coeff)

    def setShape(self, position, shapeName):
        """
        Sets the shape of a surface.

        :param position: number of the surface (int)
        :param shapeName: name of the Shape child class (str)
          See OpticalSystem.getAvailableShapeNames() for details.
        """
        self.surfaces[position].setShape(shapeName)

    def setStopPosition(self, position):
        """
        Sets one surface as the stop. Don't forget to set its semi-diameter.

        :param position: number of the surface (int) 
        """
        self.stopPosition = position

    def getABCDMatrix(self, ray, firstSurfacePosition = 0, lastSurfacePosition = -1):
        """
        Returns an ABCD matrix of the optical system.
        The matrix is set up in geometric convention for (y, dy/dz) vectors.

        The matrix contains:
        - paraxial refraction from vacuum through the first surface
        - paraxial propagation through the system
        - paraxial refraction after the last surface into vacuum

        :param firstSurfacePosition: Position of the first surface to consider (int).
          Preset is 0 (object position).
        :param lastSurfacePosition: Position of the last surface to consider (int).
          Preset is -1 (image position)
        :param ray: Ray bundle object.
        :return abcd: ABCD matrix (2d numpy 2x2 matrix of float)
        """
        print "first", firstSurfacePosition, lastSurfacePosition

        if lastSurfacePosition < 0:
            lastSurfacePosition = self.getNumberOfSurfaces() - lastSurfacePosition - 3

        print "first", firstSurfacePosition, lastSurfacePosition

        abcd = [[1,0],[0,1]]

        for i in arange( lastSurfacePosition - firstSurfacePosition + 1) + firstSurfacePosition:
            print "i=",i
            abcd = dot( self.surfaces[i].getABCDMatrix(self.surfaces[i+1], ray)  ,  abcd )

        return abcd

    def getParaxialPupil(self, ray):
        """
        Returns the paraxially calculated pupil positions.

        :param ray: Raybundle object
        :return zen: entrance pupil position from object (float)
        :return magen: entrance pupil magnificaction; entrance pupil diameter per stop diameter (float)
        :return zex: exit pupil position from image (float)
        :return magex: exit pupil magnificaction; exit pupil diameter per stop diameter (float)
        """ 
        abcd = self.getABCDMatrix(ray, 0 , self.stopPosition - 1) # object to stop

        zen  = abcd[0,1] / abcd[0,0] # entrance pupil position from object
        magen = 1.0 / abcd[0,0]     

        abcd = self.getABCDMatrix(ray, self.stopPosition, -1) # stop to image

        zex = - abcd[0,1] / abcd[1,1] # exit pupil position from image
        magex = abcd[0,0] - abcd[0,1] * abcd[1,0] / abcd[1,1]

        return zen, magen, zex, magex

    def draw2d(self, ax, offset = [0,0], vertices=100, color="grey"):
        N = self.getNumberOfSurfaces()
        offy = offset[0]
        offz = offset[1]
        for i in arange(N):
            self.surfaces[i].draw2d(ax, offset = [offy, offz])
            offz += self.surfaces[i].thickness
 

