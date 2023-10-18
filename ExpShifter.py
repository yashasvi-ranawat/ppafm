#!/usr/bin/python

# https://matplotlib.org/examples/user_interfaces/index.html
# https://matplotlib.org/examples/user_interfaces/embedding_in_qt5.html
# embedding_in_qt5.py --- Simple Qt5 application embedding matplotlib canvases


import sys
import os
import re
import time
import random
import matplotlib; matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from PyQt5 import QtCore, QtWidgets, QtGui
import numpy as np
from enum import Enum
import glob
import pickle
import scipy.ndimage as nimg
import pyProbeParticle.GuiWigets   as guiw
import pyProbeParticle.file_dat    as file_dat
import copy
import scipy.misc 
def crosscorel_2d_fft(im0,im1):
    f0 = np.fft.fft2(im0)
    f1 = np.fft.fft2(im1)
    renorm = 1/( np.std(f0)*np.std(f1) )
    #return abs(np.fft.ifft2((f0 * f1.conjugate()) / (abs(f0) * abs(f1))))
    #return np.abs( np.fft.ifft2( (    f0 * f1.conjugate() / ( np.abs(f0) * np.abs(f1) )  ) ) )
    return abs(np.fft.ifft2( f0 * f1.conjugate() ) ) * renorm

def trans_match_fft(im0, im1):
    """Return translation vector to register images."""
    print('we are in trans_match_fft')
    shape = im0.shape
    '''
    f0 = fft2(im0)
    f1 = fft2(im1)
    ir = abs(ifft2((f0 * f1.conjugate()) / (abs(f0) * abs(f1))))
    '''
    ir = crosscorel_2d_fft(im0,im1)
    t0, t1 = np.unravel_index(np.argmax(ir), shape)
    #if t0 > shape[0] // 2:
    #    t0 -= shape[0]
    #if t1 > shape[1] // 2:
    #    t1 -= shape[1]
    return [t0, t1]


def roll2d( a , shift=(10,10) ):
    a_ =np.roll( a, shift[0], axis=0 )
    return np.roll( a_, shift[1], axis=1 )

class ApplicationWindow(QtWidgets.QMainWindow):
    #path='./'
    #path="/u/25/prokoph1/unix/Desktop/CATAM/Exp_Data/Camphor/Orientation_4/"
    path="/u/85/urtevf1/unix/Documents/19august/PTCDA + Cu(111)/AFM/CO"
    divNX = 8
    divNY = 8
    bSaveDivisible = False

    def __init__(self):

        # --- init QtMain
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("application main window")
        self.main_widget = QtWidgets.QWidget(self)
        l00 = QtWidgets.QHBoxLayout(self.main_widget)
        self.figCan = guiw.FigImshow( parentWiget=self.main_widget, parentApp=self, width=5, height=4, dpi=100)
        l00.addWidget(self.figCan)
        l0 = QtWidgets.QVBoxLayout(self.main_widget); l00.addLayout(l0);

        # -------------- Potential
        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("path") )
        el = QtWidgets.QLineEdit(); el.setText(self.path); vb.addWidget(el);el.setToolTip('path to folder with .dat files');  self.txPath=el
        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("load") )
        bt = QtWidgets.QPushButton('Load all *.dat', self); bt.setToolTip('load .dat files from dir'); bt.clicked.connect(self.loadData); vb.addWidget( bt ); self.btLoad = bt
        vb.addWidget( QtWidgets.QLabel("channel") )
        bx = QtWidgets.QSpinBox();  bx.setSingleStep(1); bx.setValue(1); bx.valueChanged.connect(self.selectDataChannel); vb.addWidget(bx); bx.setToolTip('select available channels with data'); bx.setEnabled(False); self.bxChannel=bx
        ln = QtWidgets.QFrame(); l0.addWidget(ln); ln.setFrameShape(QtWidgets.QFrame.HLine); ln.setFrameShadow(QtWidgets.QFrame.Sunken)
        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb);
        vb.addWidget( QtWidgets.QLabel("slice ") );
        bx = QtWidgets.QSpinBox();bx.setToolTip('select available slices from stack'); bx.setSingleStep(1); bx.setValue(0); bx.valueChanged.connect(self.selectDataView); vb.addWidget(bx);bx.setEnabled(False); self.bxZ=bx  ; checkbox = QtWidgets.QCheckBox("show grid"); vb.addWidget(checkbox);checkbox.setChecked(True); checkbox.stateChanged.connect(self.ChkBxGrid); self.checkbox = checkbox; checkbox.setEnabled(False);


        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("shift ix,iy") )
        bx = QtWidgets.QSpinBox(); bx.setSingleStep(1); bx.setToolTip('adjust vertical shift');bx.setValue(0); bx.setRange(-1000,1000); bx.valueChanged.connect(self.shiftData); vb.addWidget(bx);bx.setEnabled(False); self.bxX=bx
        bx = QtWidgets.QSpinBox(); bx.setSingleStep(1); bx.setValue(0); bx.setToolTip('adjust horizontal shift'); bx.setRange(-1000,1000); bx.valueChanged.connect(self.shiftData); vb.addWidget(bx); bx.setEnabled(False);self.bxY=bx

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb) ; bt = QtWidgets.QPushButton('Magic fit', self); bt.setToolTip('Fit to colser slice'); bt.clicked.connect(self.magicFit); vb.addWidget( bt ); bt.setEnabled(False); self.btMagic = bt

        l0.addLayout(vb) ; bt = QtWidgets.QPushButton('MagicAll', self); bt.setToolTip('Fit all slices');bt.setEnabled(False); bt.clicked.connect(self.magicFitAll);      vb.addWidget( bt ); self.btMagicAll = bt 
        l0.addLayout(vb) ; bt = QtWidgets.QPushButton('SaveImgs', self); bt.setToolTip('save images'); bt.setEnabled(False); bt.clicked.connect(self.saveImg);      vb.addWidget( bt ); self.btSaveImg = bt 
        ln = QtWidgets.QFrame(); l0.addWidget(ln); ln.setFrameShape(QtWidgets.QFrame.HLine); ln.setFrameShadow(QtWidgets.QFrame.Sunken)
        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("Ninter ") )
        bx = QtWidgets.QSpinBox(); bx.setSingleStep(1); bx.setValue(1); vb.addWidget(bx); bx.setEnabled(False); self.bxNi=bx
        bt = QtWidgets.QPushButton('interpolate', self); bt.setToolTip('select amount of slices to add before slice'); bt.clicked.connect(self.interpolate); bt.setEnabled(False); vb.addWidget( bt ); self.btInterp = bt

        #sl = QtWidgets.QComboBox(); self.slMode = sl; vb.addWidget(sl)
        #sl.currentIndexChanged.connect(self.selectMode)

        #sl = QtWidgets.QComboBox(); self.slDataView = sl; vb.addWidget(sl)
        #sl.addItem( DataViews.FFpl.name ); sl.addItem( DataViews.FFel.name ); sl.addItem( DataViews.FFin.name ); sl.addItem( DataViews.FFout.name ); sl.addItem(DataViews.df.name );
        #sl.setCurrentIndex( sl.findText( DataViews.FFpl.name ) )
        #sl.currentIndexChanged.connect(self.updateDataView)

        # === buttons


        ln = QtWidgets.QFrame(); l0.addWidget(ln); ln.setFrameShape(QtWidgets.QFrame.HLine); ln.setFrameShadow(QtWidgets.QFrame.Sunken)

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb) 

        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("margins") )
        bx = QtWidgets.QSpinBox(); bx.setSingleStep(1); bx.setValue(0); bx.setRange(0,1000); bx.valueChanged.connect(self.marginData); bx.setToolTip('trim left border'); vb.addWidget(bx); bx.setEnabled(False);self.marginX0=bx
        bx = QtWidgets.QSpinBox(); bx.setSingleStep(1); bx.setValue(0); bx.setRange(0,1000); bx.valueChanged.connect(self.marginData); bx.setToolTip('trim bottom border'); vb.addWidget(bx); bx.setEnabled(False);self.marginY0=bx
        bx = QtWidgets.QSpinBox(); bx.setSingleStep(1); bx.setValue(0); bx.setRange(0,1000); bx.valueChanged.connect(self.marginData); bx.setToolTip('trim right border'); vb.addWidget(bx); bx.setEnabled(False); self.marginX1=bx
        bx = QtWidgets.QSpinBox(); bx.setSingleStep(1); bx.setValue(0); bx.setRange(0,1000); bx.valueChanged.connect(self.marginData); vb.addWidget(bx); bx.setToolTip('trim top border'); bx.setEnabled(False);self.marginY1=bx

        ln = QtWidgets.QFrame(); l0.addWidget(ln); ln.setFrameShape(QtWidgets.QFrame.HLine); ln.setFrameShadow(QtWidgets.QFrame.Sunken)
        # --- btSave
        vb = QtWidgets.QHBoxLayout(); l0.addLayout(vb); vb.addWidget( QtWidgets.QLabel("slices") )
        selSliceSave = QtWidgets.QLineEdit(); vb.addWidget(selSliceSave); selSliceSave.setToolTip('select slices to save, i.e.: 1,3-11'); selSliceSave.setEnabled(False);  self.txSliceSave = selSliceSave
        vb = QtWidgets.QHBoxLayout();        l0.addLayout(vb);
        self.btSave = QtWidgets.QPushButton('Save .npy', self)
        self.btSave.setToolTip('save data stack to .npy')
        self.btSave.clicked.connect(self.saveData)
        self.btSave.setEnabled(False);
        vb.addWidget( self.btSave )
        vb = QtWidgets.QHBoxLayout();        l0.addLayout(vb);
        bt = QtWidgets.QPushButton('Load .npy', self); bt.setToolTip('load .npy file  from dir'); bt.clicked.connect(self.loadNPY ); vb.addWidget( bt ); self.btLoad = bt

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)
        #self.geomEditor    = guiw.EditorWindow(self,title="Geometry Editor")
        #self.speciesEditor = guiw.EditorWindow(self,title="Species Editor")
        #self.figCurv       = guiw.PlotWindow( parent=self, width=5, height=4, dpi=100)

    def magicFit(self):
        print('magic fit')
        iz = int(self.bxZ.value())
        print('iz=',iz)  
        if (iz<len(self.data)-1 ):
            print('we are in if')            
            '''    
            image=np.float32(self.data2[iz])
            image-=image.mean()
            vmax=image.max()
            if vmax>0:
                image /= vmax
            image_target=np.float32(self.data2[iz+1])
            image_target-=image_target.mean()
            vmax=image_target.max()
            if vmax>0:
                image_target /= vmax
            '''
            [ix,iy] = trans_match_fft(self.data2[iz],self.data[iz+1]) 
            print('ix,iy=',-ix,-iy)
            if abs(int(ix))>self.data[iz].shape[0]:
                ix=ix/abs(int(ix))*(abs(int(ix))-self.data[iz].shape[0])
            if abs(int(iy))>self.data[iz].shape[1]:
                iy=iy/abs(int(iy))*(abs(int(iy))-self.data[iz].shape[1])
            if abs(int(ix))>self.data[iz].shape[0]//2:
                ix=ix/abs(int(ix))*(abs(int(ix))-self.data[iz].shape[0])
            if abs(int(iy))>self.data[iz].shape[1]//2:
                iy=iy/abs(int(iy))*(abs(int(iy))-self.data[iz].shape[1])

            self.data[iz]=nimg.shift (self.data[iz], (-ix-self.shifts[iz][0],-iy-self.shifts[iz][1]), order=3,mode='mirror' )   
            self.shifts[iz][0] =  -ix
            self.shifts[iz][1] =  -iy
            self.bxX.setValue( self.shifts[iz][0] )
            self.bxY.setValue( self.shifts[iz][1] ) 

            print(self.shifts)
            self.updateDataView()

    def magicFitAll(self):
        izs = list(range( len(self.data)-1))
        print('izs = ', izs)
        for iz in izs[::-1]:
            self.bxZ.setValue(iz);
            self.magicFit()

    def loadData(self):
        #print file_list
        #fnames
        self.path = self.txPath.text()
        self.channel = int(self.bxChannel.value())
        print(self.path)
        '''
        https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
        dlg = QtWidgets.QFileDialog()
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setFilter("Text files (*.txt)")
        filenames = QStringList()
        if dlg.exec_():
            filenames = dlg.selectedFiles()

        self.path = 
        '''

        if self.path[-1] is not '/':
            self.path   += '/'
                
        self.fnames   = glob.glob(self.path+'*.dat')
        self.fnames.sort()
        #self.data = self.loadData();
        print(self.fnames)
        data = []
        data2 = []
        headers = []
        fnames  = []
        for fname in self.fnames:
            #print fname
            fname_ = os.path.basename(fname); fnames.append( fname_ )
            #print os.path.basename(fname)
            Header = {}
            imgs = file_dat.readDat(fname, Header=Header )
            amountCh = len(imgs)
            #print fname, "Size ", Header['ScanRange_Y'],Header['ScanRange_X']," N ", imgs[0].shape," dxy ",  Header['ScanRange_Y']/imgs[0].shape[0], Header['ScanRange_X']/imgs[0].shape[1]
            #print "Lentgh [x] ", Header['LengthX']
            #print "Lentgh [y] ", Header['LengthY']
            data.append( imgs[self.channel] )
            headers.append(Header)
            #data2.append( imgs[1] )
        self.fnames = fnames
        #return data
        self.data = data
        #z=np.arange(25)
        data2=copy.copy(data)        
        self.data2= data2 #np.reshape(z, (5,5)) #data
        print('data *.dat loaded')

        self.shifts = [ [0,0] for i in range(len(self.data)) ]
        self.margins = [0,0,0,0] 
        self.bxZ.setRange( 0, len(self.data)-1 );

        # set proper scale for all slices depends from parameters:  Header['LengthX']; Header['LengthY']
        slice_lengths = [[x['LengthX'],x['LengthY']] for x in headers]
        print('slice_lengths = ', slice_lengths) 
        max_length = np.max(slice_lengths[:][0])
        print('max slice_length = ', max_length) 
        image_shape = self.data[0].shape        
        print('image_shape = ', image_shape)
        for z_slice in range(len(self.data)):
            
            if slice_lengths[z_slice][0] != max_length :
                print('slice_lengths/max_lengths = ',slice_lengths[z_slice][0]/max_length)
                scaled_size = int(image_shape[0]*slice_lengths[z_slice][0]/max_length)
                scaled_image_slice = np.zeros_like(data[z_slice]) 
                start_xy = int((image_shape[0] -  scaled_size)/2)
                scaled_image_slice[start_xy:start_xy+scaled_size, start_xy:start_xy+scaled_size] =  np.array(scipy.misc.imresize (self.data[z_slice], (scaled_size,scaled_size) )  )
                self.data[z_slice]=scaled_image_slice
                self.margins = [start_xy,image_shape[0] -scaled_size - start_xy ,image_shape[1] -scaled_size - start_xy ,start_xy] 

        imarginx0 = self.margins[0]  
        imarginx1 = self.margins[2] 
        imarginy0 = self.margins[1]
        imarginy1 = self.margins[3]
        
        for z_slice in range(len(self.data)):
            marged_size = (image_shape[0]-imarginx0-imarginx1, image_shape[1]-imarginy0-imarginy1)
            #print 'marged_size =',marged_size
            #print 'self.max_length  =', max_length 
            slice_lengths[z_slice] = [marged_size[0]*  max_length/image_shape[0]   , marged_size[1]*  max_length/image_shape[1] ]
 
        print('margins = ', self.margins)
        print('slice_lengths = ',  slice_lengths) 


   
        self.slice_lengths = slice_lengths
        self.max_length = max_length
        self.data2=copy.copy(self.data)        
        
        #print 'amountCh = ', amountCh
        self.bxChannel.setRange( 0, amountCh -1 )   
        self.marginX0.blockSignals(True); self.marginX0.setValue( self.margins[0]); self.marginX0.blockSignals(False);
        self.marginX1.blockSignals(True); self.marginX1.setValue( self.margins[2]); self.marginX1.blockSignals(False);
        self.marginY0.blockSignals(True); self.marginY0.setValue( self.margins[1]); self.marginY0.blockSignals(False);
        self.marginY1.blockSignals(True); self.marginY1.setValue( self.margins[3]); self.marginY1.blockSignals(False);
        iz    = int( self.bxZ.value() )
        self.bxX.blockSignals(True); self.bxX.setValue( self.shifts[iz][0] ); self.bxX.blockSignals(False);
        self.bxY.blockSignals(True); self.bxY.setValue( self.shifts[iz][1] ); self.bxY.blockSignals(False);
        
        self.updateDataView()
        self.bxChannel.setEnabled(True)
        self.bxZ.setEnabled(True)
        self.bxX.setEnabled(True) 
        self.bxY.setEnabled(True) 
        self.btMagicAll.setEnabled(True) 
        self.btMagic.setEnabled(True) 
        self.btSaveImg.setEnabled(True)
        self.bxNi.setEnabled(True)
        self.btInterp.setEnabled(True)
        self.marginX0.setEnabled(True)
        self.marginX1.setEnabled(True)
        self.marginY0.setEnabled(True)
        self.marginY1.setEnabled(True)
        self.btSave.setEnabled(True)
        self.txSliceSave.setEnabled(True)
        self.checkbox.setEnabled(True);

    def interpolate(self):
        iz    = int( self.bxZ.value() )
        ni    = int( self.bxNi.value() )
        dat1  = self.data[iz  ]
        dat2  = self.data[iz+1]
        for i in range(ni):
            c = (i+1)/float(ni+1)
            print(c)
            dat = c*dat1 + (1.0-c)*dat2
            #dat[:100,:] = dat1[:100,:]
            #dat[100:,:] = dat2[100:,:]
            self.data  .insert( iz+1, dat )
            self.data2  .insert( iz+1, dat )
            self.slice_lengths.insert( iz+1,self.slice_lengths[iz])
            self.shifts.insert( iz+1, [0,0] )
            self.fnames.insert( iz+1, "c%1.3f" %c )
        self.bxZ.setRange( 0, len(self.data)-1 )
        print('slice_lengths = ', self.slice_lengths)

    def saveData(self):        
        self.slices_to_save = str(self.txSliceSave.text())
        if self.slices_to_save:
            print('slices_to_save = ', self.slices_to_save)
            slices_nums = [s.strip() for s in re.split(r'[,;]+| ,', self.slices_to_save) if s]
            #print 'slices_nums = ', slices_nums
            linearrframes = [int(i) for i in slices_nums if '-' not in i]
            linearrdiapasones = sum([list(range(int(i.split('-')[0]), int(i.split('-')[1]) + 1)) for i in slices_nums if '-' in i], [])
            #print 'linearrframes = ', linearrframes
            #print 'linearrdiapasones = ', linearrdiapasones

            linearrframes.extend(linearrdiapasones)
            linearrframes = list(set(linearrframes))
            slices_indexes = [int(i) for i in linearrframes]

            print(('slices_to_save = ',slices_indexes))
            
            arr = np.array(self.data)
            endx = arr.shape[2]-self.margins[2]
            endy = arr.shape[1]-self.margins[3]
            arr = arr[slices_indexes,self.margins[1]:endy,self.margins[0]:endx]  
            
 
        else:
            arr = np.array(self.data)
            print("dat.shape ", arr.shape)
            endx = arr.shape[2]-self.margins[2]
            endy = arr.shape[1]-self.margins[3]
            arr = arr[:,self.margins[1]:endy,self.margins[0]:endx]  
            print("arr.shape ", arr.shape)

        print("saveData: arr.shape ", arr.shape) 
        if ( self.bSaveDivisible ):
            print("dat.shape ", arr.shape)
            nx=arr.shape[1]/self.divNX * self.divNX
            ny=arr.shape[2]/self.divNY * self.divNY
            arr_ = arr[:,:nx,:ny]
            arr_ = arr_.transpose((1,2,0))
            print("saveData: arr_.shape ", arr_.shape)
            np.save( self.path+"data.npy", arr_)
        else:
            arr = arr.transpose((1,2,0))
            np.save( self.path+"data.npy", arr  )


        with open(self.path+'data.pickle', 'wb') as fp:
            if self.slices_to_save:
                pickle.dump( [self.fnames[i] for i in slices_indexes], fp)
                pickle.dump( [self.shifts[i] for i in slices_indexes], fp)
                pickle.dump( [self.margins[i] for i in range(4)], fp)
                pickle.dump( [self.slice_lengths[i] for i in slices_indexes], fp)
            else:
                pickle.dump( self.fnames, fp)
                pickle.dump( self.shifts, fp)
                pickle.dump( [self.margins[i] for i in range(4)], fp)
                pickle.dump( self.slice_lengths, fp)

 
    def loadNPY(self):
        self.path = self.txPath.text()
        if self.path[-1] is not '/':
            self.path   += '/'
        
        # load image data from data.npy
        data = []
        data2 = []
        data = np.load(self.path+'data.npy')
        data = data.transpose((2,0,1))
        print("loaded Data: shape ", data.shape)
        self.data = [ s for s in data ]

        data2=copy.copy(self.data)        
        self.data2= data2 #np.reshape(z, (5,5)) #data
        print('data npy loaded')

        # load meta data from data.pickle about file names, shifts, lengths
        with open ( self.path+'data.pickle', 'rb') as fp:
            self.fnames = pickle.load(fp)
            self.shifts = pickle.load(fp)
            self.margins = pickle.load(fp)
            try: 
                self.slice_lengths = pickle.load(fp)
                print('...::: self.slice_lengths loaded!')
                print('self.slice_lengths = ', self.slice_lengths)
            except:
                print('...::: self.slice_lengths were not loaded!')
                self.slice_lengths  = [ [0,0] for i in range(len(self.data)) ]


        
        self.shifts = [ [0,0] for i in range(len(self.data)) ]

 

        self.margins = [0,0,0,0]  
        self.bxZ.setRange( 0, len(self.data)-1 );
        self.bxChannel.setEnabled(False)
        iz    = int( self.bxZ.value() )
        self.bxX.setValue( self.shifts[iz][0] )
        self.bxY.setValue( self.shifts[iz][1] )         


        self.marginX0.blockSignals(True); self.marginX0.setValue( self.margins[0]); self.marginX0.blockSignals(False);
        self.marginX1.blockSignals(True); self.marginX1.setValue( self.margins[2]); self.marginX1.blockSignals(False);
        self.marginY0.blockSignals(True); self.marginY0.setValue( self.margins[1]); self.marginY0.blockSignals(False);
        self.marginY1.blockSignals(True); self.marginY1.setValue( self.margins[3]); self.marginY1.blockSignals(False);
        self.updateDataView()
        self.bxChannel.setEnabled(True)
        self.bxZ.setEnabled(True)
        self.bxX.setEnabled(True) 
        self.bxY.setEnabled(True) 
        self.btMagicAll.setEnabled(True) 
        self.btMagic.setEnabled(True) 
        self.btSaveImg.setEnabled(True)
        self.bxNi.setEnabled(True)
        self.btInterp.setEnabled(True)
        self.marginX0.setEnabled(True)
        self.marginX1.setEnabled(True)
        self.marginY0.setEnabled(True)
        self.marginY1.setEnabled(True)
        self.btSave.setEnabled(True)
        self.txSliceSave.setEnabled(True)
        self.checkbox.setEnabled(True);

    def saveImg(self):
        n = len(self.data)
        plt.figure( figsize=(n*5,5) )
        for i in range(n):
            print(i)
            plt.subplot(1,n,i+1)
            plt.imshow(self.data[i], origin='image') #,cmap='gray')
            print('image path = ' , self.path+'data.png')
        plt.savefig(self.path+"data.png", bbox_inches='tight')

    def shiftData(self):
        print("shiftData")
        iz = int(self.bxZ.value())
        ix = int(self.bxX.value()); dix = ix - self.shifts[iz][0]; self.shifts[iz][0] = ix
        iy = int(self.bxY.value()); diy = iy - self.shifts[iz][1]; self.shifts[iz][1] = iy
        print('self.original[iz]=',self.data2[iz][:3,:3])
        print('dix,diy=', dix,diy)

        print(self.shifts)
        image=self.data2[iz]
        self.data[iz]=nimg.shift (image, (iy,ix), order=3,mode='mirror' )   
        #self.data[iz] = np.roll( self.data[iz], dix, axis=0 )
        

        #self.data[iz] = np.roll( self.data[iz], diy, axis=1 )

        self.updateDataView()

    def marginData(self):
 
        imarginx0 = int(self.marginX0.value()); self.margins[0] = imarginx0
        imarginx1 = int(self.marginX1.value()); self.margins[2] = imarginx1
        imarginy0 = int(self.marginY0.value()); self.margins[1] = imarginy0
        imarginy1 = int(self.marginY1.value()); self.margins[3] = imarginy1
        image_shape = self.data[0].shape
        print('image_shape =',image_shape)
        for z_slice in range(len(self.data)):
            marged_size = (image_shape[0]-imarginx0-imarginx1, image_shape[1]-imarginy0-imarginy1)
            #print 'marged_size =',marged_size
            #print 'self.max_length  =', self.max_length 
           
            self.slice_lengths[z_slice] = [marged_size[0]*  self.max_length/image_shape[0]   , marged_size[1]*  self.max_length/image_shape[1] ]
            #print 'self.slice_lengths[z_slice]  =', self.slice_lengths[z_slice]
   
        #self.margins = [start_xy,image_shape[0] -scaled_size - start_xy ,image_shape[1] -scaled_size - start_xy ,start_xy]    
 
        print('margins = ', self.margins)
        print('slice_lengths = ', self.slice_lengths) 

        self.updateDataView()

    def ChkBxGrid(self):
        #print "grid selector      ", self.checkbox.checkState()
        self.updateDataView()

    def selectDataView(self):
        iz    = int( self.bxZ.value() )
        print(" selectDataView iz,ix,iy ", iz, self.shifts[iz][0], self.shifts[iz][1])
        self.bxX.blockSignals(True); self.bxX.setValue( self.shifts[iz][0] ); self.bxX.blockSignals(False);
        self.bxY.blockSignals(True); self.bxY.setValue( self.shifts[iz][1] ); self.bxY.blockSignals(False);


        print("selectDataView bxXY      ", self.bxX.value(), self.bxY.value())
        self.updateDataView()

    def selectDataChannel(self):
        ichannel = int( self.bxChannel.value())
        self.loadData()
        print(" selectDataChannel ", ichannel) 

        self.updateDataView()


    def updateDataView(self):
        iz    = int( self.bxZ.value() )
        grid_selector = int(self.checkbox.checkState())
        #t1 = time.clock() 
        #iz = self.selectDataView()
        #print 'self.margins', self.margins
        #f =np.fft.fft2(self.data[iz])
        #f_shift = np.fft.fftshift(f)
        #print 'f_shift.shape = ',f_shift.shape
        #f_complex = f_shift[:,:,0] + 1j*f_shift[:,:,1]
        #f_abs = np.abs(f_shift) + 1 # lie between 1 and 1e6
        #f_bounded = 20 * np.log(f_abs)
        #f_img = 255 * f_bounded / np.max(f_bounded)
        #f_img = f_img.astype(np.uint8)
        try:
            self.figCan.plotSlice( self.data, iz, self.fnames[iz], self.margins,grid_selector,self.slice_lengths[iz] )

            #self.figCan.plotSlice(f_img, self.fnames[iz], self.margins )
            #print 'self.data[iz].shape = ', self.data[iz].shape
        except:
            print("cannot plot slice #", iz)
        #t2 = time.clock(); print "plotSlice time %f [s]" %(t2-t1)

if __name__ == "__main__":
    qApp = QtWidgets.QApplication(sys.argv)
    aw = ApplicationWindow()
    aw.show()
    sys.exit(qApp.exec_())

