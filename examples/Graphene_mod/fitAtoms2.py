#!/usr/bin/python


import matplotlib.pyplot as plt
import numpy as np

import ppafm.atomfit as AF
from ppafm import io

'''

TODO:
determine z-position from approach curve ( slightly below minimum )

'''

E,lvec,nDim,head = io.loadXSF("OutFz.xsf")

E = E[13,:,:]

#Fy = E[:-1,:  ] - E[1:, :]; Fy=Fy[:  ,:-1]+Fy[ :,1:]
#Fx = E[:  ,:-1] - E[ :,1:]; Fx=Fx[:-1,:  ]+Fx[1:, :]


Fy = E[:-2,:  ] - E[2:, :]; Fy=Fy[:  ,:-2]+Fy[ :,2:]
Fx = E[:  ,:-2] - E[ :,2:]; Fx=Fx[:-2,:  ]+Fx[2:, :]

F = np.empty(Fx.shape+(2,))

F[:,:,0] =  Fx
F[:,:,1] =  Fy

F[:,:,:]*=-1.0

#del Fx,Fy

'''
pos = np.array([
    [5.0,5.0],
    [5.0,6.0],
    [6.0,5.0],
    [6.0,6.0]
])
'''

Xs,Ys = np.meshgrid(np.linspace(0.0,16.0,32),np.linspace(0.0,16.0,32))
pos = np.empty(Xs.shape+(2,))
pos[:,:,0]=Xs + 2.0
pos[:,:,1]=Ys + 2.0
pos=pos.reshape(-1,2).copy()
#print pos
print(pos.shape)

dpix=[0.1,0.1]
npix=F.shape
AF.setParams (1.0, 1.0 )
AF.setGridFF (F, dpix )
nfound = AF.relaxParticlesUnique( pos, 10, 2.0, 0.9, 1e-4 )
#nfound = AF.relaxParticlesRepel( pos, 100, 1.0, 0.9, 1e-4 )

pos = pos[:nfound,:]
print(pos)
print(pos.shape)

#plt.imshow(Fx*Fx + Fy*Fy, extent=(0,npix[0]*dpix[0],0,npix[1]*dpix[1]))
extent=(0,npix[0]*dpix[0],0,npix[1]*dpix[1])
plt.imshow(E, extent=extent)

#plt.imshow(Fx, extent=(0,npix[0]*dpix[0],0,npix[1]*dpix[1]))
#plt.imshow(E, extent=(0,npix[0]*dpix[0],0,npix[1]*dpix[1]))
plt.plot( pos[:,0],pos[:,1], ".w" )

plt.xlim(extent[0],extent[1])
plt.ylim(extent[2],extent[3])

plt.show()
