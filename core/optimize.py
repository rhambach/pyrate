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
import uuid

class OptimizableVariable(object):
    """
    Class that contains an optimizable variable. Used to get a pointer on a variable.
    The value is not constrained to float. Also other dependent variables are possible to define.
    """
    def __init__(self, variable_type="fixed", **kwargs):
        """
        Name is gone since it's only needed for reference. Therefore the former listOfOptimizableVariables
        will be a dictionary. type may contain a string e.g.
        "Fixed", "Variable", "Pickup", "External", "...",
        status=True means updating during optimization run
        status=False means no updating during optimization run
        kwargs depend on type
        "Variable" is value=value
        "Pickup" gets function=f, args=tuple of optimizablevariables
        "External" gets function=f, args=tuple of external standard variables (or values)

        :param variable_type (string): which kind of variable do we have? valid choices are: 'fixed', 'variable', 'pickup', 'external'

        :param kwargs (keyword arguments): used to fill up parameters dictionary for variable.

        kwargs:

        type:        kwargs:
        'fixed'         value=1.0 or value='hello'
        'variable'    value=1.0, or value='hello'
        'pickup'        function=f, args=(other_optvar1, other_optvar2, ...)
        'external'        function=f, args=(other_externalvar/value, ...)

        Notice: f must take exactly as many arguments as args=... long is. The only constraint on f is
        that it has to convert the variables into some final float variable. If this is not the case some
        low-level optimizer might break down.


        """

        self.evaldict = {
                    "fixed"    : self.eval_fixed,
                    "variable" : self.eval_variable,
                    "pickup"   : self.eval_pickup,
                    "external" : self.eval_external
                    }


        self.changetype(variable_type)
        self.parameters = kwargs

        self.initial_value = self.evaluate()
        self.set_interval(None, None)


    def __str__(self, *args, **kwargs):
        return "OptVar('" + self.var_type + "') = " + str(self.parameters)

    def getVarType(self):
        return self.__var_type.lower()

    var_type = property(fget=getVarType)

    def set_interval(self, left=None, right=None):
        """
        Interval transform from finite to infinite and back.
        The reason for this is that the optimizer backend has
        only to deal with infinite range variables and the user
        can transparently change the interval. The idea and
        verification is (up to a slight change in the 
        transformation) taken from:
        M. Roeber, "Multikriterielle Optimierungsverfahren fuer
        rechenzeitintensive technische Aufgabenstellungen",
        Diploma Thesis, Technische Universitaet Chemnitz, 
        2010-03-31
        """
        # TODO: fine-tune for one-sided intervals
        if left is None and right is None:
            self.transform = lambda x: x
            self.inv_transform = lambda x: x
        else:
            self.inv_transform = lambda x: left + (right - left)/(1. + math.exp(-x/math.fabs(right - left)))
            self.transform = lambda x: math.log((-x + left)/(x - right))*math.fabs(left - right)

    def changetype(self, vtype, **kwargs):
        self.__var_type = vtype.lower()
        self.evalfunc = self.evaldict[self.var_type]
        try:        
            parameter_backup = self.parameters
        except:
            parameter_backup = {"value":None}
        self.parameters = kwargs
        if vtype.lower() in ["variable", "fixed"] \
            and self.__var_type in ["variable", "fixed"] \
            and parameter_backup["value"] != None:
            self.parameters["value"] = parameter_backup["value"]

    def setvalue(self, value):
        # TODO: overload assign operator
        if self.var_type == "variable" or self.var_type == "fixed":
            self.parameters["value"] = value

    def eval_fixed(self):
        # if type = variable then give only access to value
        return self.parameters["value"]

    def eval_variable(self):
        # if type = variable then give only access to value
        return self.parameters["value"]

    def eval_pickup(self):
        # if type = pickup then pack all arguments into one tuple
        # and put it into the userdefined function
        # evaluate the result
        arguments_for_function_eval = (argfunc.evaluate() for argfunc in self.parameters["args"])
        return self.parameters["function"](*arguments_for_function_eval)

    def eval_external(self):
        # same as for solve except that there are no further OptimizableVariables to be considered
        return self.parameters["function"](*self.parameters["args"])

    def evaluate(self):
        # notice: evaluation code is not limited to floats
        # do not use if-else construct because for many cases dict lookup is faster

        return self.evalfunc()
        
    def __call__(self):
        return self.evaluate()
        
    def evaluate_transformed(self):
        '''
        Transform variable value from finite interval to infinite IR before evaluation
        '''
        return self.transform(self.evaluate())
        
    def setvalue_transformed(self, value_transformed):
        '''
        Transform value back from infinite IR before setting value
        '''
        value = self.inv_transform(value_transformed)
        self.setvalue(value)
        
class ClassWithOptimizableVariables(object):
    """
    Implementation of some class with optimizable variables with the help of a dictionary.
    This class is also able to collect the variables and their values from its subclasses per recursion.
    """
    def __init__(self, name = ""):
        """
        Initialize with empty dict.
        """
        self.setName(name)
        self.dict_variables = {}
        self.list_observers = [] 
        # for the optimizable variable class it is useful to have some observer links
        # they get informed if variables change their values

    def __call__(self, key):
        return self.dict_variables.get(key, None)

    def setName(self, name):
        if name == "":
            name = str(uuid.uuid4())
        self.__name = name
        
    def getName(self):
        return self.__name
        
    name = property(getName, setName)


    def appendObservers(self, obslist):
        self.list_observers += obslist

    def informObservers(self):
        for obs in self.list_observers:
            obs.informAboutUpdate()

    def addVariable(self, name, var):
        """
        Add some variable into dict.
        """
        self.dict_variables[name] = var


                
    def getAllVariables(self):

        def addOptimizableVariablesToList(var, listOfOptVars = [], idlist=[]):
            """
            Accumulates optimizable variables in var and its linked objects.
            Ignores ring-links and double links.       
            
            @param var: object to evaluate (object)
            @param listOfOptVars: optimizable variables found so far (list of objects)
            @param idlist: ids of objects already evaluated (list of int)
            """ 
            
            if id(var) not in idlist:
                idlist.append(id(var))
    
                if isinstance(var, ClassWithOptimizableVariables):
                    for v in var.__dict__.values():
                        listOfOptVars, idlist = addOptimizableVariablesToList(v, listOfOptVars, idlist) 
                elif isinstance(var, dict):
                    for v in var.values():
                        listOfOptVars, idlist = addOptimizableVariablesToList(v, listOfOptVars, idlist)                        
    
                elif isinstance(var, list) or isinstance(var, tuple):
                    for v in var:
                        listOfOptVars, idlist = addOptimizableVariablesToList(v, listOfOptVars, idlist)
    
                elif isinstance(var, OptimizableVariable):
                    listOfOptVars.append(var)
    
            return listOfOptVars, idlist



        (lst, idlist) = addOptimizableVariablesToList(self)
        return lst


    def getAllValues(self):
        """
        For fast evaluation of value vector
        """
        return np.array([a.evaluate() for a in self.getAllVariables()])

    def getActiveVariables(self):
        """
        Returns a list of active variables the names are lost
        but it does not matter since the variable references are still in the
        original dictionary in the class
        """
        return [x for x in self.getAllVariables() if x.var_type == "variable"]


    def getActiveValues(self):
        """
        Function to get all values into one large np.array.
        """
        return np.array([a() for a in self.getActiveVariables()])

    def setActiveValues(self, x):
        """
        Function to set all values of active variables to the values in the large np.array x.
        """
        for i, var in enumerate(self.getActiveVariables()):
            var.setvalue(x[i])

    def getActiveTransformedValues(self):
        return np.array([a.evaluate_transformed() for a in self.getActiveVariables()])

    def setActiveTransformedValues(self, x):
        """
        Function to set all values of active variables to the values in the large np.array x.
        """
        for i, var in enumerate(self.getActiveVariables()):
            var.setvalue_transformed(x[i])


class Optimizer(object):
    '''
    Easy optimization interface. All variables are public such that a quick
    attachment of other meritfunctions or other update functions with other
    parameters is possible.
    '''
    def __init__(self, classwithoptvariables, meritfunction, backend, updatefunction=None):

        def noupdate(cl):
            pass
        
        super(Optimizer, self).__init__()
        self.classwithoptvariables = classwithoptvariables
        self.meritfunction = meritfunction # function to minimize
        if updatefunction is None:
            updatefunction = noupdate
        self.updatefunction = updatefunction # function to be called to update classwithoptvariables
        self.setBackend(backend) # eats vector performs optimization, returns vector
        # scipy Nelder-Mead, scipy ..., evolutionary, genetic, ...        
       
        self.meritparameters = {}
        self.updateparameters = {}
        self.log = "" # for logging

    def setBackend(self, backend):
        self.__backend = backend
        self.__backend.init(self.MeritFunctionWrapper)

    backend = property(fget=None, fset=setBackend)

    def MeritFunctionWrapper(self, x):
        """
        Merit function wrapper for backend. 
        Notice that x and length of active values must have the same size
    
        :param x (np.array): active variable values
        :param meritfunction (function): meritfunction depending on s
    
        :return value of the merit function
        """
        self.classwithoptvariables.setActiveTransformedValues(x)
        self.updatefunction(self.classwithoptvariables, **self.updateparameters)    
        return self.meritfunction(self.classwithoptvariables, **self.meritparameters)

    def run(self):
        '''
        Funtion to perform a certain number of optimization steps.
        '''
        x0 = self.classwithoptvariables.getActiveTransformedValues()
        self.log += "initial x: " + str(x0) + '\n'
        self.log += "initial merit: " + str(self.MeritFunctionWrapper(x0)) + "\n"
        xfinal = self.__backend.run(x0)
        self.log += "final x: " + str(xfinal) + '\n'
        self.log += "final merit: " + str(self.MeritFunctionWrapper(xfinal)) + "\n"
        self.classwithoptvariables.setActiveTransformedValues(xfinal)
        # TODO: do not change original classwithoptvariables
        return self.classwithoptvariables

