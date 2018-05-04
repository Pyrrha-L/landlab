#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create a LithoLayers object with different properties."""
"""
Create a block of rock with different properties.

@author: barnhark
"""
import numpy as np
from landlab.components.lithology.lithology import Lithology


class LithoLayers(Lithology):
    """Create LithoLayers object

    A LithoLayers is a three dimentional representation of material operated on
    by landlab components. Material can be removed through erosion or added to
    through deposition. Rock types can have multiple attributes (e.g. age,
    erodability or other parameter values, etc).

    If the tracked properties are model grid fields, they will be updated to
    the surface values of the Lithology. If the properties are not grid fields
    then at-node grid fields will be created with their names.

    It is constructed by specifying a series of depths below the surface, an
    anchor point, a series of rock type ids, and the functional form of a
    surface. Depths and IDs are both specified in order of closest
    to the surface to furthest from the surface.

    Additionally, an attribute dictionary specifies the properties of each
    rock type. This dictionary is expected to have the form of:

    .. code-block:: python

        attrs = {'K_sp': {1: 0.001,
                          2: 0.0001},
                 'D': {1: 0.01,
                       2: 0.001}}

    Where ``'K_sp'`` and ``'D'`` are properties to track, and ``1`` and ``2``
    are rock type IDs. The rock type IDs can be any type that is valid as a
    python dictionary key.

    The following attributes and methods are the same as in the Lithology.

    Attributes
    ----------
    z_top
    z_bottom
    thickness
    dz
    tracked_properties
    properties

    Methods
    -------
    add_rock_type
    add_rock_attribute
    update_rock_attribute
    add_layer
    run_one_step

    """
    _name = 'LithoLayers'

    _cite_as = """ """



    def __init__(self, grid, z0s, ids, attrs, x0=0, y0=0,
                 function=lambda x, y: 0*x + 0*y,
                 layer_type='EventLayers'):
        """Create a new instance of a LithoLayers.

        Parameters
        ----------
        grid : Landlab ModelGrid
        z0s : ndarray of shape `(n_layers, )`
            Values of layer depth from surface at horizontal location (x0, y0).
        ids : ndarray of shape `(n_layers, )`
            Values of rock type IDs cooresponding to each layer specified in
            **z0s**.
        attrs : dict
            Rock type property dictionary. See class docstring for example of
            required format.
        x0 : float, optional
            x value of anchor point for all layers.
        y0 : float, optional
            y value of anchor point for all layers.
        function : function, optional
            Functional form of layers as a function of two variables, x and y.
            Default value is lambda x, y: 0*x + 0*y for flatlying layers.
        layer_type : str, optional
            Type of Landlab layers object used to store the layers. If
            MaterialLayers (default) is specified, then erosion removes material
            and does not create a layer of thickness zero. If EventLayers is
            used, then erosion removes material and creates layers of thickness
            zero. Thus, EventLayers may be appropriate if the user is interested
            in chronostratigraphy.

        Examples
        --------
        >>> from landlab import RasterModelGrid
        >>> from landlab.components import LithoLayers
        >>> mg = RasterModelGrid(3, 3)
        >>> z = mg.add_zeros('node', 'topographic__elevation')

        Create a LithoLayers with flatlying layers that altrnate between
        layers of type 1 and type 2 rock.

        >>> z0s = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
        >>> ids = [1, 2, 1, 2, 1, 2, 1, 2, 1]
        >>> attrs = {'K_sp': {1: 0.001,
        ...                   2: 0.0001}}
        >>> rb = LithoLayers(mg, z0s, ids, attrs)
        >>> rb.dz
        array([[ 1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.],
               [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.],
               [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.],
               [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.],
               [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]])

        Now create a set of layers that dip. Our anchor point will be the
        default value of (x0, y0) = (0, 0)

        >>> rb = LithoLayers(mg, z0s, ids, attrs, function=lambda x, y: x+y)
        >>> rb.dz
        array([[ 1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 0.,  1.,  1.,  1.,  1.,  1.,  1.,  1.,  1.],
               [ 0.,  0.,  1.,  0.,  1.,  1.,  1.,  1.,  1.],
               [ 0.,  0.,  0.,  0.,  0.,  1.,  0.,  1.,  1.],
               [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  1.],
               [ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]])

        We can get the surface values, and as we'd expect, they alternate as
        the dipping layers are exposed at the surface.

        >>> rb['K_sp']
        array([ 0.0001,  0.001 ,  0.0001,  0.001 ,  0.0001,  0.001 ,  0.0001,
            0.001 ,  0.0001])
        """
        self._grid = grid

        if np.asarray(z0s).size != np.asarray(ids).size:
            msg = 'size of zs and ids must be the same'
            raise ValueError(msg)

        if np.any(np.diff(z0s) < 0):
            msg = 'bad order'
            raise ValueError(msg)

        z_surf = function(self._grid.x_of_node - y0, self._grid.y_of_node - y0)

        layer_thicknesses = []
        layer_ids = []

        num_layers = np.asarray(z0s).size

        last_layer_elev = np.zeros(self._grid.number_of_nodes)

        # create layers (here listed from the top to the bottom.)
        for i in range(num_layers):

            layer_depth = z_surf + z0s[i]
            layer_depth[layer_depth<0] = 0

            layer_thickness = layer_depth.copy() - last_layer_elev.copy()

            last_layer_elev = layer_depth.copy()

            layer_thicknesses.append(layer_thickness)
            layer_ids.append(ids[i] * np.ones(z_surf.size))

        super(LithoLayers, self).__init__(grid, layer_thicknesses, layer_ids, attrs, layer_type=layer_type)
