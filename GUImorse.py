#!/usr/bin/python

# https://matplotlib.org/examples/user_interfaces/index.html
# https://matplotlib.org/examples/user_interfaces/embedding_in_qt5.html
# embedding_in_qt5.py --- Simple Qt5 application embedding matplotlib canvases


import sys
import os
import time
import random
import matplotlib; matplotlib.use('Qt5Agg')
from PyQt5 import QtCore, QtWidgets, QtGui
#from numpy import arange, sin, pi
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.figure import Figure
#import matplotlib.pyplot as plt
import numpy as np
from enum import Enum

#sys.path.append("/home/prokop/git/ProbeParticleModel_OCL") 
#import pyProbeParticle.GridUtils as GU

from   pyProbeParticle import basUtils
from   pyProbeParticle import PPPlot 
import pyProbeParticle.GridUtils as GU
import pyProbeParticle.common    as PPU
import pyProbeParticle.cpp_utils as cpp_utils

import pyopencl as cl
import pyProbeParticle.oclUtils    as oclu 
import pyProbeParticle.fieldOCL    as FFcl 
import pyProbeParticle.RelaxOpenCL as oclr

import pyProbeParticle.GuiWigets   as guiw

Modes     = Enum( 'Modes',    'MorseFFel MorseFFel_pbc' )
DataViews = Enum( 'DataViews','FFin FFout df FFel FFpl' )

# Pre-autosetting:
zmin = 1.0; zmax = 20.0; ymax = 20.0; xmax =20.0;
atoms0, nDim0, lvec0 = basUtils.loadXSFGeom( "FFel_z.xsf" )
zmin = round(max(atoms0[3]),1); zmax=round(lvec0[3][2],1); ymax=round(lvec0[1][1]+lvec0[2][1],1); xmax=round(lvec0[1][0]+lvec0[2][0],1)

print("zmin, zmax, ymax, xmax")
print(zmin, zmax, ymax, xmax)

class ApplicationWindow(QtWidgets.QMainWindow):

    df   = None
    FFel = None
    FF   = None
    FEin = None
    ff_args = None
    str_Atoms = None
    mode = Modes.MorseFFel.name
    #Q          = -0.25;
    Q           = 0.0;
    relax_dim   = (120,120,60)

    def __init__(self):

        print("oclu.ctx    ", oclu.ctx)
        print("oclu.queue  ", oclu.queue)
    
        FFcl.init()
        oclr.init()
    
        #self.resize(600, 800)

        # --- init QtMain
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("application main window")
        self.main_widget = QtWidgets.QWidget(self)
        #l0 = QtWidgets.QVBoxLayout(self.main_widget)
        l00 = QtWidgets.QHBoxLayout(self.main_widget)
        self.figCan = guiw.FigImshow( parentWiget=self.main_widget, parentApp=self, width=5, height=4, dpi=100)
        l00.addWidget(self.figCan)
        l0 = QtWidgets.QVBoxLayout(self.main_widget); l00.addLayout(l0);

        # -------------- Potential
        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb);

        sl = QtWidgets.QComboBox(); self.slMode = sl; vb.addWidget(sl)
        sl.addItem( Modes.MorseFFel.name )
        sl.addItem( Modes.MorseFFel_pbc.name )
        sl.setCurrentIndex( sl.findText( Modes.MorseFFel.name ) )
        sl.currentIndexChanged.connect(self.selectMode)

        sl = QtWidgets.QComboBox(); self.slDataView = sl; vb.addWidget(sl)
        sl.addItem( DataViews.FFpl.name ); sl.addItem( DataViews.FFel.name ); sl.addItem( DataViews.FFin.name ); sl.addItem( DataViews.FFout.name ); sl.addItem(DataViews.df.name );
        sl.setCurrentIndex( sl.findText( DataViews.FFpl.name ) )
        sl.currentIndexChanged.connect(self.updateDataView)
        
        
        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("{iZPP, fMorse[1]}") )
        bx = QtWidgets.QSpinBox();       bx.setRange(0, 200);    bx.setValue(8);                             bx.valueChanged.connect(self.updateFromFF); vb.addWidget(bx); self.bxZPP=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.25, 4.0); bx.setValue(1.00);  bx.setSingleStep(0.05); bx.valueChanged.connect(self.updateFromFF); vb.addWidget(bx); self.bxMorse=bx
        
        # -------------- Relaxation 
        ln = QtWidgets.QFrame(); l0.addWidget(ln); ln.setFrameShape(QtWidgets.QFrame.HLine); ln.setFrameShadow(QtWidgets.QFrame.Sunken)

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("Q [e]") )
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(-2.0, 2.0); bx.setValue(self.Q); bx.setSingleStep(0.05); bx.valueChanged.connect(self.upload_and_relax); vb.addWidget(bx); self.bxQ=bx

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("K {x,y,R} [N/m]") )
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.0,   2.0); bx.setValue(0.24);  bx.setSingleStep(0.05); bx.valueChanged.connect(self.relax); vb.addWidget(bx); self.bxKx=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.0,   2.0); bx.setValue(0.24);  bx.setSingleStep(0.05); bx.valueChanged.connect(self.relax); vb.addWidget(bx); self.bxKy=bx
        #bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.0,  2.0); bx.setValue(0.5);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.relax); vb.addWidget(bx); self.bxKz=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.0, 100.0); bx.setValue(30.0); bx.setSingleStep(5.0); bx.valueChanged.connect(self.relax); vb.addWidget(bx); self.bxKr=bx

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("eq.pos {x,y,R} [A]") )
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(-2.0, 2.0); bx.setValue(0.0);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.relax); vb.addWidget(bx); self.bxP0x=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(-2.0, 2.0); bx.setValue(0.0);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.relax); vb.addWidget(bx); self.bxP0y=bx
        #bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.0, 2.0); bx.setValue(0.5);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.relax); vb.addWidget(bx); self.bxP0z=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange( 0.0, 10.0); bx.setValue(4.0); bx.setSingleStep(0.1); bx.valueChanged.connect(self.relax); vb.addWidget(bx); self.bxP0r=bx

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("relax_min {x,y,z}[A]") )
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(-100.0,100.0); bx.setValue(0.0);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxSpanMinX=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(-100.0,100.0); bx.setValue(0.0);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxSpanMinY=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(-100.0,100.0); bx.setValue(zmin);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxSpanMinZ=bx

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("relax_max {x,y,z}[A]") )
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.0,100.0); bx.setValue(xmax);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxSpanMaxX=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.0,100.0); bx.setValue(ymax);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxSpanMaxY=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.0,100.0); bx.setValue(zmax);  bx.setSingleStep(0.1); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxSpanMaxZ=bx

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("relax_step {x,y,z}[A]") )
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.02,0.5); bx.setValue(0.1);  bx.setSingleStep(0.02); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxStepX=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.02,0.5); bx.setValue(0.1);  bx.setSingleStep(0.02); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxStepY=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0.02,0.5); bx.setValue(0.1);  bx.setSingleStep(0.02); bx.valueChanged.connect(self.shapeRelax); vb.addWidget(bx); self.bxStepZ=bx 

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("In the beginning & after chaging anything rather push relax") )

        # -------------- df Conversion & plotting
        ln = QtWidgets.QFrame(); l0.addWidget(ln); ln.setFrameShape(QtWidgets.QFrame.HLine); ln.setFrameShadow(QtWidgets.QFrame.Sunken)

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("{ iz (down from top), nAmp }") )
        bx = QtWidgets.QSpinBox();bx.setRange(-300,500); bx.setSingleStep(1); bx.setValue(0); bx.valueChanged.connect(self.updateDataView); vb.addWidget(bx); self.bxZ=bx
        bx = QtWidgets.QSpinBox();bx.setRange(0,50 ); bx.setSingleStep(1); bx.setValue(10); bx.valueChanged.connect(self.F2df); vb.addWidget(bx); self.bxA=bx

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("{ k[kN/m], f0 [kHz] }") )
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0,1000.0); bx.setSingleStep(0.1); bx.setValue(1.8);  bx.valueChanged.connect(self.F2df); vb.addWidget(bx); self.bxCant_K=bx
        bx = QtWidgets.QDoubleSpinBox(); bx.setRange(0,2000.0); bx.setSingleStep(1.0); bx.setValue(30.3); bx.valueChanged.connect(self.F2df); vb.addWidget(bx); self.bxCant_f0=bx

        # === buttons
        ln = QtWidgets.QFrame(); l0.addWidget(ln); ln.setFrameShape(QtWidgets.QFrame.HLine); ln.setFrameShadow(QtWidgets.QFrame.Sunken)

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb) 
        
        # --- EditAtoms
        bt = QtWidgets.QPushButton('Edit Geom', self)
        bt.setToolTip('Edit atomic structure')
        bt.clicked.connect(self.editAtoms)
        self.btEditAtoms = bt; vb.addWidget( bt )
        
        # --- EditFFparams
        bt = QtWidgets.QPushButton('Edit Params', self)
        bt.setToolTip('Edit atomic structure')
        bt.clicked.connect(self.editSpecies)
        self.btEditParams = bt; vb.addWidget( bt )
        
        # --- btFF
        self.btFF = QtWidgets.QPushButton('getFF', self)
        self.btFF.setToolTip('Get ForceField')
        self.btFF.clicked.connect(self.getFF)
        vb.addWidget( self.btFF )
        
        # --- btRelax
        self.btRelax = QtWidgets.QPushButton('relax', self)
        self.btRelax.setToolTip('relaxed scan')
        self.btRelax.clicked.connect(self.relax)
        vb.addWidget( self.btRelax )

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)
        

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb) 
        
        # --- btLoad
        self.btLoad = QtWidgets.QPushButton('Load', self)
        self.btLoad.setToolTip('Load inputs')
        self.btLoad.clicked.connect(self.loadInputs_New)
        vb.addWidget( self.btLoad )
        
        # --- btSave
        self.btSave = QtWidgets.QPushButton('save fig', self)
        self.btSave.setToolTip('save current figure')
        self.btSave.clicked.connect(self.saveFig)
        vb.addWidget( self.btSave )

        # --- btSaveW (W- wsxm)
        self.btSaveW = QtWidgets.QPushButton('save data', self)
        self.btSaveW.setToolTip('save current figure data')
        self.btSaveW.clicked.connect(self.saveDataW)
        vb.addWidget( self.btSaveW )

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)
        self.geomEditor    = guiw.EditorWindow(self,title="Geometry Editor")
        self.speciesEditor = guiw.EditorWindow(self,title="Species Editor")
        self.figCurv       = guiw.PlotWindow( parent=self, width=5, height=4, dpi=100)

        self.selectMode()

    def shapeRelax(self):
        step = np.array( [ float(self.bxStepX   .value()), float(self.bxStepY   .value()), float(self.bxStepZ   .value()) ] )
        rmin = np.array( [ float(self.bxSpanMinX.value()), float(self.bxSpanMinY.value()), float(self.bxSpanMinZ.value()) ] )
        rmax = np.array( [ float(self.bxSpanMaxX.value()), float(self.bxSpanMaxY.value()), float(self.bxSpanMaxZ.value()) ] )
        self.relax_dim   = tuple( ((rmax-rmin)/step).astype(np.int32) ) 
        print("shapeRelax", step, rmin, rmax, self.relax_dim)
        self.FEin = np.zeros( self.ff_nDim+(4,), dtype=np.float32)
        print("self.FEin.shape", self.FEin.shape)
        if self.FF is not None:
            self.composeTotalFF()
        self.relax_poss  = oclr.preparePoss   ( self.relax_dim, z0=rmax[2], start=rmin, end=rmax )
        self.relax_args  = oclr.prepareBuffers( self.FEin, self.relax_dim )

    def editAtoms(self):        
        self.geomEditor.show()    # TODO : we use now QDialog instead
    
    def editSpecies(self):        
        self.speciesEditor.show() # TODO : we use now QDialog instead
    
    def updateFF(self):
        #print self.str_Atoms;
        self.str_Atoms   = self.geomEditor   .textEdit.toPlainText()
        self.str_Species = self.speciesEditor.textEdit.toPlainText()
        #print self.str_Species
        #print self.str_Atoms;
        xyzs,Zs,enames,qs = basUtils.loadAtomsLines( self.str_Atoms.split('\n') )
        pbcnx = (1 if self.mode == Modes.MorseFFel_pbc.name else 0)
        Zs, xyzs, qs      = PPU.PBCAtoms( Zs, xyzs, qs, avec=self.lvec[1], bvec=self.lvec[2], na=pbcnx, nb=pbcnx )
        self.atoms        = FFcl.xyzq2float4(xyzs,qs);

        #print Zs
        #print xyzs
        #print qs
        #print self.atoms

        iZPP = self.bxZPP.value()

        self.TypeParams = PPU. loadSpeciesLines( self.str_Species.split('\n') )

        self.perAtom = False
        if self.perAtom:
            atomREAs  = np.genfromtxt( "atom_REAs.xyz", skip_header=2 )
            #print atomREAs
            PP_R = self.TypeParams[iZPP][0]
            PP_E = self.TypeParams[iZPP][1]
            #print " PP: ", iZPP, PP_R, PP_E
            REAs = PPU.combineREA( PP_R, PP_E, atomREAs[:,4:7], alphaFac=self.bxMorse.value() )
            #REAs = np.repeat( REAs, (PPU.params['nPBC'][0]*2+1)*(PPU.params['nPBC'][1]*2+1 ) , axis=0 )
            #self.REAs = REAs[4:7].astype(np.float32)
            #REAs[:,0] = 1.8 + 1.8
            #REAs[:,1] = -0.01
            #REAs[:,2] = -1.8
            #REAs[:,3] = 0.0
        else:
            REAs     = PPU.getAtomsREA( iZPP, Zs, self.TypeParams, alphaFac=-self.bxMorse.value() )
        self.REAs    = REAs.astype(np.float32)
        print("self.REAs.shape", self.REAs.shape)
        print("self.atoms.shape", self.atoms.shape)
        #print "self.perAtom REAs", self.REAs

        self.ff_args = FFcl.updateArgsMorse( self.ff_args, self.atoms, self.REAs, self.poss )  

    def updateFromFF(self):
        self.updateFF()
        self.getFF()
        self.upload_and_relax()

    def loadInputs_New(self):
        print("self.mode  ", self.mode) 
        try:
            with open('atomtypes.ini', 'r') as f:  self.str_Species = f.read(); 
        except:
            print("defaul atomtypes.ini")
            with open(cpp_utils.PACKAGE_PATH+'/defaults/atomtypes.ini', 'r') as f:  self.str_Species = f.read();

        self.str_Species = "\n".join( "\t".join( l.split()[:5] )  for l in self.str_Species.split('\n')  );
        self.TypeParams = PPU. loadSpeciesLines( self.str_Species.split('\n') );
        
        #print self.TypeParams;
        self.speciesEditor.textEdit.setText( self.str_Species )

        lvec=None; xyzs=None; Zs=None; qs=None; 
        print(self.mode)
        #atoms, nDim, lvec = basUtils.loadXSFGeom( "FFel_z.xsf" )
        atoms = atoms0; nDim = nDim0; lvec = lvec0;
        nDim = nDim[::-1]
        lines = [   "%i %f %f %f %f" %(atoms[0][i], atoms[1][i], atoms[2][i], atoms[3][i], atoms[4][i] ) for i in range(len(atoms[0])) ]
        self.str_Atoms = "\n".join( lines )
        Zs   = atoms[0]; qs   = atoms[4]; xyzs = np.transpose( np.array( [atoms[1],atoms[2],atoms[3]] ) ).copy()

        print(nDim)
        print(lvec)
        #print self.str_Atoms
        self.geomEditor.textEdit.setText( self.str_Atoms )
        #exit()

        self.lvec    = np.array( lvec )
        self.invCell = oclr.getInvCell(self.lvec)
        Zs, xyzs, qs = PPU.PBCAtoms( Zs, xyzs, qs, avec=self.lvec[1], bvec=self.lvec[2] )
        self.atoms   = FFcl.xyzq2float4(xyzs,qs);

        self.poss         = FFcl.getposs( self.lvec, nDim )
        self.ff_nDim = self.poss.shape[:3]

        FFel, lvec, nDim, head = GU.loadVecFieldXsf( "FFel" )
        self.FFel = FFcl.XYZ2float4(FFel[:,:,:,0],FFel[:,:,:,1],FFel[:,:,:,2])

        self.updateFF()

    def getFF(self):
        t1 = time.clock() 
        #self.FF    = FFcl.runLJC( self.ff_args, self.ff_nDim )
        self.FF    = self.func_runFF( self.ff_args, self.ff_nDim )
        print("getFF : self.FF.shape", self.FF.shape);
        self.plot_FF = True
        t2 = time.clock(); print("FFcl.func_runFF time %f [s]" %(t2-t1))
        #self.plotSlice()
        self.updateDataView()
        
    def relax(self):
        t1 = time.clock() 
        #self.composeTotalFF(); # does not work;  this is negligible slow-down
        stiffness    = np.array([self.bxKx.value(),self.bxKy.value(),0.0,self.bxKr.value()], dtype=np.float32 ); stiffness/=-16.0217662; #print "stiffness", stiffness
        dpos0        = np.array([self.bxP0x.value(),self.bxP0y.value(),0.0,self.bxP0r.value()], dtype=np.float32 ); dpos0[2] = -np.sqrt( dpos0[3]**2 - dpos0[0]**2 + dpos0[1]**2 ); #print "dpos0", dpos0
        relax_params = np.array([0.1,0.9,0.1*0.2,0.1*5.0], dtype=np.float32 ); #print "relax_params", relax_params
        self.FEout   = oclr.relax( self.relax_args, self.relax_dim, self.invCell, poss=self.relax_poss, dpos0=dpos0, stiffness=stiffness, relax_params=relax_params  )
        t2 = time.clock(); print("oclr.relax time %f [s]" %(t2-t1))
        print("self.FEin.shape",  self.FEin.shape)
        print("self.FEout.shape", self.FEout.shape)
        self.F2df()
    
    def composeTotalFF(self):
        self.Q  = self.bxQ.value()
        if np.abs(self.Q)<1e-4 : 
            self.FEin[:,:,:,:] = self.FF[:,:,:,:4]
        else:
            if self.FFel is None:
                self.FEin[:,:,:,:] = self.FF[:,:,:,:4] + self.Q*self.FF[:,:,:,4:] 
            else:
                print(self.FEin.shape, self.FF.shape, self.FFel.shape)
                self.FEin[:,:,:,:] = self.FF[:,:,:,:] + self.Q*self.FFel[:,:,:,:]

    def upload_and_relax(self):
        self.composeTotalFF()
        region = self.FEin.shape[:3]; region = region[::-1]; print("upload FEin : ", region)
        cl.enqueue_copy( oclr.oclu.queue, self.relax_args[0], self.FEin, origin=(0,0,0), region=region  )
        self.relax()
        
    def F2df(self):
        nAmp = self.bxA.value()
        if nAmp > 0:
            t1 = time.clock()
            self.df = -PPU.Fz2df( np.transpose( self.FEout[:,:,:,2], (2,1,0) ), dz=self.bxStepZ.value(), k0=self.bxCant_K.value()*1e+3, f0= self.bxCant_f0.value()*1e+3, n=nAmp )
            t2 = time.clock(); print("F2df time %f [s]" %(t2-t1))
        else:
            self.df = None
        self.plot_FF = False
        #self.plotSlice()
        self.updateDataView()
        
    def saveFig(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","Image files (*.png)")
        if fileName:
            fileName = guiw.correct_ext( fileName, ".png" )
            print("saving image to :", fileName)
            self.figCan.fig.savefig( fileName,bbox_inches='tight')

    def saveDataW(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","WSxM files (*.xyz)")
        if fileName:
            fileName = guiw.correct_ext( fileName, ".xyz" )
            print("saving data to to :", fileName)
            iz,data = self.selectDataView()
            npdata=data[iz]
            xs = np.arange(npdata.shape[1] )
            ys = np.arange(npdata.shape[0] )
            Xs, Ys = np.meshgrid(xs,ys)
            GU.saveWSxM_2D(fileName, npdata, Xs, Ys)

    def selectMode(self):
        self.mode = self.slMode.currentText()
        if ((self.mode == Modes.MorseFFel.name) or (self.mode == Modes.MorseFFel_pbc.name)) :
            self.func_runFF        = FFcl.runMorse
        else:
            print("No such mode : ",self.mode) 
            return
        self.loadInputs_New()
        self.getFF()

        #GU.saveVecFieldXsf( "DEBUG_FFcl", self.FF[:,:,:,:3].astype(np.float32), self.lvec )
        #GU.saveXSF( "DEBUG_FFcl_z.xsf", self.FF[:,:,:,2].astype(np.float32), self.lvec )
        #self.initRelax()
        self.shapeRelax()
        print(self.mode)
    
    def selectDataView(self):   # !!! Everything from TOP now !!! #
        dview = self.slDataView.currentText()
        #print "DEBUG dview : ", dview
        iz    = int( self.bxZ.value() )
        data = None;
        if   dview == DataViews.df.name:
            data = self.df
        elif dview == DataViews.FFout.name:
            data = np.transpose( self.FEout[:,:,:,2], (2,1,0) )
        elif dview == DataViews.FFin.name:
            data = self.FEin[::-1,:,:,2]
        elif dview == DataViews.FFpl.name:
            data = self.FF  [::-1,:,:,2]
        elif dview == DataViews.FFel.name:
            data = self.FFel[::-1,:,:,2]
            #print "data FFel.shape[1:3]", data.shape[1:3]
            #iz = data.shape[0]-iz-1
        return iz, data

    def updateDataView(self):
        t1 = time.clock() 
        iz,data = self.selectDataView()
        self.viewed_data = data 
        #self.figCan.plotSlice_iz(iz)
        try:
            print(data.shape)
            self.figCan.plotSlice( data[iz], title=self.slDataView.currentText()+':iz= '+str(int( self.bxZ.value() )) )
        except:
            print("cannot plot slice #", iz)
        t2 = time.clock(); print("plotSlice time %f [s]" %(t2-t1))

    '''
    def plotSlice(self):
        t1 = time.clock() 
        val = int( self.bxZ.value() )
        Fslice = None
        iz,data = self.selectDataView()
        print iz, data.shape, self.slDataView.currentText()
        Fslice = data[iz]
        if Fslice is not None:
            self.figCan.plotSlice( Fslice )
        t2 = time.clock(); print "plotSlice time %f [s]" %(t2-t1)
    '''

    def clickImshow(self,ix,iy):
        ys = self.viewed_data[ :, iy, ix ]
        self.figCurv.show()
        self.figCurv.figCan.plotDatalines( ( list(range(len(ys))), ys, "%i_%i" %(ix,iy) )  )

if __name__ == "__main__":
    qApp = QtWidgets.QApplication(sys.argv)
    aw = ApplicationWindow()
    aw.show()
    sys.exit(qApp.exec_())

