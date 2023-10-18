#!/usr/bin/python 
# This is a sead of simple plotting script which should get AFM frequency delta 'df.xsf' and generate 2D plots for different 'z'

import os
import sys

import numpy as np
import matplotlib.pyplot as plt   
import pyProbeParticle.GridUtils      as GU
from   optparse import OptionParser

parser = OptionParser()
parser.add_option( "-p",   action="store", type="string", help="pixels (ix,iy) to take curve", default='curve_points.ini' )
parser.add_option( "-i",   action="store", type="string", help="input file",                   default='OutFz'        )
parser.add_option( "--iz", action="store", type="int",    help="z-slice index to plot legend", default=15                 )
#parser.add_option( "--npy" , action="store_true" ,  help="load and save fields in npy instead of xsf"     , default=False)
parser.add_option("-f","--data_format" , action="store" , type="string", help="Specify the output format of the vector and scalar field. Supported formats are: xsf,npy", default="xsf")
(options, args) = parser.parse_args()

try:
	points = np.genfromtxt( options.p )
	print("plotting in points", points)
except:
	print(options.p+" not found => exiting ...")
	sys.exit()

fzs,lvec,nDim=GU.load_scal_field(options.i,data_format=options.data_format)
#xs = lvec[3,2]/*np.array( range(nDim[0]) )
xs = np.linspace( 0, lvec[3,2], nDim[0] )

#print nDim
print(xs)

plt.imshow( fzs[options.iz], origin='imgage', cmap='gray' )
for point in points:
    print("point", point)
    plt.plot([point[0]],[point[1]],'o')
plt.xlim(0,nDim[2])
plt.ylim(0,nDim[1])
plt.savefig( options.i+'_zcurves_legend.png', bbox_inches='tight')

plt.figure()
curves = np.zeros((len(points)+1,len(xs)))
curves[0] = xs

vmin = 0
for i,point in enumerate(points):
	ys = fzs[:,int(point[1]),int(point[0])]
	vmin=min(ys.min(),vmin)
	print(point, vmin)
	print(ys)
	curves[i+1] = ys
	plt.plot( xs, ys )
plt.grid()
plt.savefig( options.i+'_zcurves.png', bbox_inches='tight')

#plt.ylim( 1.1*vmin, -2*vmin )
np.savetxt( options.i+'_zcurves.dat', np.transpose(curves) )

#dfs = PPU.Fz2df( fzs, dz = dz, k0 = PPU.params['kCantilever'], f0=PPU.params['f0Cantilever'], n=Amp/dz )
                    
plt.show()
