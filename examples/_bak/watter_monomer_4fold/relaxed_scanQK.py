#!/usr/bin/python

import os
import numpy as np
import matplotlib.pyplot as plt
import sys

print(" # ========== make & load  ProbeParticle C++ library ")

LWD = "/home/prokop/git/ProbeParticleModel/code"
sys.path = [LWD]

import basUtils
import elements
import GridUtils as GU
import ProbeParticle as PP
import PPPlot

print(" ============= RUN  ")

print(" >> WARNING!!! OVEWRITING SETTINGS by params.ini  ")

PP.loadParams("params.ini")

PPPlot.params = PP.params

print(" load Electrostatic Force-field ")
FFel, lvec, nDim, head = GU.loadVecFieldXsf("FFel")
print(" load Lenard-Jones Force-field ")
FFLJ, lvec, nDim, head = GU.loadVecFieldXsf("FFLJ")
PP.lvec2params(lvec)
PP.setFF(FFel)

xTips, yTips, zTips, lvecScan = PP.prepareScanGrids()

# Ks   = [ 0.25, 0.5, 1.0 ]
# Qs   = [ -0.2, 0.0, +0.2 ]
# Amps = [ 2.0 ]

Ks = [0.5]
Qs = [0.0]
Amps = [1.0]

for iq, Q in enumerate(Qs):
    FF = FFLJ + FFel * Q
    PP.setFF_Pointer(FF)
    for ik, K in enumerate(Ks):
        dirname = "Q%1.2fK%1.2f" % (Q, K)
        os.makedirs(dirname)
        PP.setTip(kSpring=np.array((K, K, 0.0)) / -PP.eVA_Nm)
        # GU.saveVecFieldXsf( 'FFtot', FF, lvec, head )
        fzs = PP.relaxedScan3D(xTips, yTips, zTips)
        GU.saveXSF(dirname + "/OutFz.xsf", fzs, lvecScan, GU.XSF_HEAD_DEFAULT)
        for iA, Amp in enumerate(Amps):
            AmpStr = "/Amp%2.2f" % Amp
            print("Amp= ", AmpStr)
            os.makedirs(dirname + AmpStr)
            dz = PP.params["scanStep"][2]
            dfs = PP.Fz2df(
                fzs,
                dz=dz,
                k0=PP.params["kCantilever"],
                f0=PP.params["f0Cantilever"],
                n=Amp / dz,
            )
            extent = (xTips[0], xTips[-1], yTips[0], yTips[-1])
            PPPlot.plotImages(
                dirname + AmpStr + "/df",
                dfs,
                slices=list(range(0, len(dfs))),
                extent=extent,
            )

print(" ***** ALL DONE ***** ")

# plt.show()
