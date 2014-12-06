#################################################################
##
##  Modification of soil_moisture_field.py to accomodate 
##  multiple Plant Functional Types (PFTs)
##
##  Sai Nudurupati and Erkan Istanbulluoglu - 31Oct2014
#################################################################

from landlab import Component

import numpy as np

_VALID_METHODS = set(['Grid', 'Multi'])

def assert_method_is_valid(method):
    if method not in _VALID_METHODS:
        raise ValueError('%s: Invalid method name' % method)
        
class SoilMoisture( Component ):
    
    _name = 'Soil Moisture'

    _input_var_names = set([
        'VegetationCover',
        'LiveLeafAreaIndex',
        'PotentialEvapotranspiraton',
    ])

    _output_var_names = set([
        'WaterStress',
        'SaturationFraction',
        'Drainage',
        'Runoff',
        'ActualEvapotranspiration',
    ])

    _var_units = {
        'VegetationCover' : 'None',
        'LiveLeafAreaIndex': 'None',
        'PotentialEvapotranspiraton' : 'mm',
        'WaterStress' : 'Pa',
        'SaturationFraction' : 'None',
        'Drainage' : 'mm',
        'Runoff' : 'mm',
        'ActualEvapotranspiration' : 'mm',
    }


    def __init__( self, grid, **kwds ):
                
        self._method = kwds.pop('method', 'Grid')

        assert_method_is_valid(self._method)
        
        super(SoilMoisture, self).__init__(grid)
        
        self.initialize( **kwds )       

        for name in self._input_var_names:
            if not name in self.grid.at_cell:
                self.grid.add_zeros('cell', name, units=self._var_units[name])

        for name in self._output_var_names:
            if not name in self.grid.at_cell:
                self.grid.add_zeros('cell', name, units=self._var_units[name])

        self._nodal_values = self.grid['node']

        if not 'InitialSaturationFraction' in self.grid.at_cell:
            self.grid.add_zeros('cell', 'InitialSaturationFraction',
                                    units='None' )

        self._cell_values = self.grid['cell']


    def initialize( self, **kwds ):
        
        self._vegtype = \
          kwds.pop('VEGTYPE', np.zeros(self.grid.number_of_cells,dtype = int))       
        self._runon = kwds.pop('RUNON', 0.)
        self._fbare = kwds.pop('F_BARE', 0.7)
        
        self._interception_cap = \
                np.choose(self._vegtype, kwds.pop('INTERCEPT_CAP', [1.]))
        self._zr = np.choose(self._vegtype, kwds.pop('ZR', [0.3]))
        self._soil_Ib = np.choose(self._vegtype, kwds.pop('I_B', [12]))
        self._soil_Iv = np.choose(self._vegtype, kwds.pop('I_V', [36]))
        self._soil_Ew = np.choose(self._vegtype, kwds.pop('EW', [0.1]))
        self._soil_pc = np.choose(self._vegtype, kwds.pop('PC', [0.43]))
        self._soil_fc = np.choose(self._vegtype, kwds.pop('FC', [0.56]))
        self._soil_sc = np.choose(self._vegtype, kwds.pop('SC', [0.31]))
        self._soil_wp = np.choose(self._vegtype, kwds.pop('WP', [0.17]))
        self._soil_hgw = np.choose(self._vegtype, kwds.pop('HGW', [0.1]))
        self._soil_beta = np.choose(self._vegtype, kwds.pop('BETA', [12.7])) 


    def update( self, current_time, **kwds ):
        #DEBUGG = 0

        P = kwds.pop('P', 5.)
        Tb = kwds.pop('Tb', 24.)
        Tr = kwds.pop('Tr', 0.0)
        self._PET = self._cell_values['PotentialEvapotranspiration']
        self._SO = self._cell_values['InitialSaturationFraction']
        self._vegcover = self._cell_values['VegetationCover']
        self._water_stress = self._cell_values['WaterStress']
        self._S = self._cell_values['SaturationFraction']
        self._D = self._cell_values['Drainage']
        self._ETA = self._cell_values['ActualEvapotranspiration']
        self._fr = self._cell_values['LiveLeafAreaIndex']/1.44
        
        for cell in range(0,self.grid.number_of_cells):
            
            #print cell
            s = self._SO[cell]
            
            fbare = self._fbare
            ZR = self._zr[cell]
            pc = self._soil_pc[cell]
            fc = self._soil_fc[cell]
            sc = self._soil_sc[cell]
            wp = self._soil_wp[cell]
            hgw = self._soil_hgw[cell]
            beta = self._soil_beta[cell]


            Inf_cap = self._soil_Ib[cell]*(1-self._vegcover[cell]) +         \
                                    self._soil_Iv[cell]*self._vegcover[cell] 
                                                        # Infiltration capacity
            Int_cap = min(self._vegcover[cell]*self._interception_cap[cell],
                                    P)  # Interception capacity
            Peff = max(P-Int_cap, 0.0)         # Effective precipitation depth
            mu = (Inf_cap/1000.0)/(pc*ZR*(np.exp(beta*(1-fc))-1))
            Ep = max((self._PET[cell]*self._fr[cell]
                                +fbare*self._PET[cell]*(1-self._fr[cell])) 
                                    - Int_cap, 0.001)  #
            nu = ((Ep/24.0)/1000.0)/(pc*ZR) # Loss function parameter
            nuw = ((Ep*0.1/24)/1000.0)/(pc*ZR) # Loss function parameter
            sini = self._SO[cell] + ((Peff+self._runon)/(pc*ZR*1000.0))

            if sini>1:
                self._runoff = (sini-1)*pc*ZR*1000
                #print 'Runoff =', self._runoff
                sini = 1

            else:
                self._runoff = 0


            #self._runon = runoff

            if sini>=fc:
                tfc = (1.0/(beta*(mu-nu)))*(beta*(fc-sini)+                   \
                        np.log((nu-mu+mu*np.exp(beta*(sini-fc)))/nu))
                tsc = ((fc-sc)/nu)+tfc
                twp = ((sc-wp)/(nu-nuw))*np.log(nu/nuw)+tsc

                if Tb<tfc:
                    s = abs(sini-(1/beta)*np.log(((nu-mu+mu*                  \
                            np.exp(beta*(sini-fc)))*np.exp(beta*(nu-mu)*Tb)   \
                            -mu*np.exp(beta*(sini-fc)))/(nu-mu)))

                    self._D[cell] = ((pc*ZR*1000)*(sini-s))-(Tb*(Ep/24))
                    self._ETA[cell] = (Tb*(Ep/24))

                elif Tb>=tfc and Tb<tsc:
                    s = fc-(nu*(Tb-tfc))
                    self._D[cell] = ((pc*ZR*1000)*(sini-fc))-((tfc)*(Ep/24))
                    self._ETA[cell] = (Tb*(Ep/24))

                elif Tb>=tsc and Tb<twp:
                    s = wp+(sc-wp)*((nu/(nu-nuw))*np.exp((-1)*((nu-nuw)
                                        /(sc-wp))*(Tb-tsc))-(nuw/(nu-nuw)))
                    self._D[cell] = ((pc*ZR*1000)*(sini-fc))-(tfc*Ep/24)
                    self._ETA[cell] = (1000*ZR*pc*(sini-s))-self._D[cell]

                else:
                    s = hgw+(wp-hgw)*np.exp((-1)*(nuw/(wp-hgw))*max(Tb-twp,0))
                    self._D[cell] = ((pc*ZR*1000)*(sini-fc))-(tfc*Ep/24)
                    self._ETA[cell] = (1000*ZR*pc*(sini-s))-self._D[cell]

            elif sini<fc and sini>=sc:
                tfc = 0
                tsc = (sini-sc)/nu
                twp = ((sc-wp)/(nu-nuw))*np.log(nu/nuw)+tsc

                if Tb<tsc:
                    s = sini - nu*Tb
                    self._D[cell] = 0
                    self._ETA[cell] = 1000*ZR*pc*(sini-s)

                elif Tb>=tsc and Tb<twp:
                    s = wp+(sc-wp)*((nu/(nu-nuw))*np.exp((-1)
                                *((nu-nuw)/(sc-wp))*(Tb-tsc))-(nuw/(nu-nuw)))
                    self._D[cell] = 0
                    self._ETA[cell] = (1000*ZR*pc*(sini-s))

                else:
                    s = hgw+(wp-hgw)*np.exp((-1)*(nuw/(wp-hgw))*(Tb-twp))
                    self._D[cell] = 0
                    self._ETA[cell] = (1000*ZR*pc*(sini-s))

            elif sini<sc and sini>=wp:
                tfc = 0
                tsc = 0
                twp = ((sc-wp)/(nu-nuw))*np.log(1+(nu-nuw)*(sini-wp)
                                        /(nuw*(sc-wp)))

                if Tb<twp:
                    s = wp+((sc-wp)/(nu-nuw))*((np.exp((-1)*((nu-nuw)
                                    /(sc-wp))*Tb))*(nuw+((nu-nuw)
                                        /(sc-wp))*(sini-wp))-nuw)
                    self._D[cell] = 0
                    self._ETA[cell] = (1000*ZR*pc*(sini-s))

                else:
                    s = hgw+(wp-hgw)*np.exp((-1)*(nuw/(wp-hgw))*(Tb-twp))
                    self._D[cell] = 0
                    self._ETA[cell] = (1000*ZR*pc*(sini-s))

            else:
                tfc = 0
                tsc = 0
                twp = 0

                s = hgw+(sini-hgw)*np.exp((-1)*(nuw/(wp-hgw))*Tb)
                self._D[cell] = 0                
                self._ETA[cell] = (1000*ZR*pc*(sini-s))

            self._water_stress[cell] = min(max((((sc - (s+sini)/2.) 
                                        / (sc - wp))**4.),0.001),1.0)
            self._S[cell] = s
            self._SO[cell] = s

        current_time += (Tb+Tr)/(24.*365.25)
        return( current_time )
