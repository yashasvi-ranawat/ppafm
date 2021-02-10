#!/usr/bin/python3 
# This is a sead of simple plotting script which should get AFM frequency delta 'df.xsf' and generate 2D plots for different 'z'

'''
TODO:
 * Check units of tip size 
 * try 3D effects (not flatened z-axis)
 * complex coeficients for molecular orbital phase
 * draw position and orientaion of molecules
 * move molecules by mouse

'''





import os
import sys
import __main__ as main
import numpy as np
#import GridUtils as GU
#sys.path.append("/u/25/prokoph1/unix/git/ProbeParticleModel")

import pyProbeParticle                as PPU
import pyProbeParticle.GridUtils      as GU
import pyProbeParticle.fieldFFT       as fFFT

# ======== Main

def makeBox(pos, rot, a=10.0,b=20.0, byCenter=False):
    c= np.cos(rot)
    s= np.sin(rot)
    x=pos[0]; y=pos[1]
    if byCenter:
        ca=c*a*0.5;sa=s*a*0.5; 
        cb=c*b*0.5;sb=s*b*0.5; 
        xs=[x-ca+sb,x+ca+sb,x+ca-sb,x-ca-sb,x-ca+sb]
        ys=[y-sa-cb,y+sa-cb,y+sa+cb,y-sa+cb,y-sa-cb]
    else:
        xs=[x,x+c*a,x+c*a-s*b,x-s*b,x]
        ys=[y,y+s*a,y+s*a+c*b,y+c*b,y]
    return xs,ys

def plotBoxes( poss, rots, lvec, ax=None, byCenter=False ):
    if ax is None:
        ax = plt.gca()
    #print "lvec ", lvecH
    for i in range(len(poss)):
        #xs,ys = makeBox( poss[i], rots[i], a=lvec[2][1],b=lvec[3][2] )
        if byCenter:
            xs,ys = makeBox( poss[i], rots[i], a=float(lvec[3][2]),b=float(lvec[2][1]), byCenter=True )
        else:
            xs,ys = makeBox( poss[i], rots[i], a=float(lvec[3][2]),b=float(lvec[2][1]), byCenter=False )

        ax.plot(xs,ys,linewidth=0.5)
        ax.plot(xs[0],ys[0],'.',markersize=5)

def shiftHalfAxis( X, d, n, ax=1 ):
    shift = n//2;
    if( n%2 != 0 ):  shift += 1
    X -= shift
    return np.roll( X, shift, axis=ax), shift

def getMGrid2D(nDim, dd):
    'returns coordinate arrays X, Y, Z'
    (dx, dy) = dd
    XY = np.mgrid[0:nDim[0],0:nDim[1]].astype(float)
    yshift = nDim[1]//2;  yshift_ = yshift;
    xshift = nDim[0]//2;  xshift_ = xshift;
    if( nDim[1]%2 != 0 ):  yshift_ += 1.0
    if( nDim[0]%2 != 0 ):  xshift_ += 1.0
    X = XY[0] - xshift_;
    Y = XY[1] - yshift_;
    Y = dy * np.roll( Y, yshift, axis=1)
    X = dx * np.roll( X, xshift, axis=0)
    #print X[:,0]
    return X, Y, (xshift, yshift)

def getMGrid3D( nDim, dd ):
    'returns coordinate arrays X, Y, Z'
    (dx,dy,dz) = dd
    (nx,ny,nz) = nDim[:3]
    print (dd)
    #print (nDim)
    XYZ = np.mgrid[0:nx,0:ny,0:nz].astype(float)
    X,xshift = shiftHalfAxis( XYZ[0], dx, nx, ax=0 )
    Y,yshift = shiftHalfAxis( XYZ[1], dy, ny, ax=1 )
    #Z,zshift = shiftHalfAxis( XYZ[2], dz, nz, ax=2 )
    Z = XYZ[2]
    return X*dx, Y*dy, Z*dz, (xshift, yshift, 0)

def makeTipField2D( sh, dd, z=10.0, sigma=1.0, multipole_dict={'s':1.0} ):
    Vtip = np.zeros( sh[:2] )
    #X,Y,shifts  = getMGrid2D( sh, dd )
    Y,X,shifts  = getMGrid2D( sh, dd )
    #X *= dd[0]; Y *= dd[1];  # this is already done in getMGrid
    #print "Z = ", z
    #print "(xmax,ymax) = ", X[-1,-1],Y[-1,-1],  X[0,0],Y[0,0]
    radial = 1/np.sqrt( X**2 + Y**2  + z**2 + sigma**2  ) 
    #print "radial ", radial[:,radial.shape[1]/2]
    if multipole_dict is not None:    # multipole_dict should be dictionary like { 's': 1.0, 'pz':0.1545  , 'dz2':-0.24548  }
        Vtip = np.zeros( np.shape(radial) )
        for kind, coef in multipole_dict.items():
            Vtip += radial * coef * fFFT.getSphericalHarmonic( X, Y, z, kind=kind, tilt=0 )
    else:
        Vtip = radial
    #Vtip = X
    #Vtip = radial
    #print "Vtip ", Vtip[:,Vtip.shape[1]/2]
    return Vtip, shifts

def makeTipField3D( sh, dd, z0=10.0, sigma=1.0, multipole_dict={'s':1.0} ):
    Vtip = np.zeros( sh )
    X,Y,Z,shifts  = getMGrid3D( sh, dd )
    Z += z0
    #X *= dd[0]; Y *= dd[1];  # this is already done in getMGrid
    #print "Z = ", z
    #print "(xmax,ymax) = ", X[-1,-1],Y[-1,-1],  X[0,0],Y[0,0]
    radial = 1/np.sqrt( X**2 + Y**2  + Z**2 + sigma**2 ) 
    #print "radial ", radial[:,radial.shape[1]/2]
    if multipole_dict is not None:    # multipole_dict should be dictionary like { 's': 1.0, 'pz':0.1545  , 'dz2':-0.24548  }
        Vtip = np.zeros( np.shape(radial) )
        for kind, coef in multipole_dict.items():
            Vtip += radial * coef * fFFT.getSphericalHarmonic( X, Y, Z, kind=kind, tilt=0 )
    else:
        Vtip = radial
    #print "Vtip.shape     ", Vtip.shape
    Vtip = Vtip.transpose((2,1,0)).copy()
    #print " -> Vtip.shape ", Vtip.shape
    #print "shifts ", shifts
    return Vtip, shifts

'''
def coordConv(poss,rots,center,nn):
    #poss - center positions of rhoTrans in canvas with respect to canvas center in points
    #rots - rotations in RAD
    #center - indexes of rhoTrans center (point of rotation)
    #nn - array defining the canvas size, in points
    a = center[0]
    b = center[1]
    for i in range(len(rots)):
        nposs = poss
        ph = rots[i]
        x  = poss[i][0]
        y  = poss[i][1]
        ca = np.cos(ph)
        sa = np.sin(ph)
        nposs[i][0] = x - ca*a + sa*b + nn[0]/2.
        nposs[i][1] = y + sa*a + ca*b + nn[1]/2.
    return nposs
'''

def convFFT(F1,F2):
    return np.fft.ifftn( np.fft.fftn(F1) * np.fft.fftn(F2) )

def photonMap2D( rhoTrans, tipDict, lvec, z=10.0, sigma=1.0, multipole_dict={'s':1.0}):
    sh = rhoTrans.shape
    #print "shape: ", sh
    #rho  = np.zeros( (sh[:2]) )
    rho  = np.sum(  rhoTrans, axis=2) 
    #Vtip = np.zeros( (sh[:2]) )
    #print lvec
    dx   = lvec[3][2]/sh[0]; #print lvec[3][2],sh[0]
    dy   = lvec[2][1]/sh[1]; #print lvec[2][1],sh[1]
    dd = (dx,dy)
    #print " (dx,dy) ", dd
    Vtip, shifts = makeTipField2D( sh[:2], dd, z=z, sigma=sigma, multipole_dict=multipole_dict )
    renorm = 1./( (Vtip**2).sum() * (rho**2).sum() )
    phmap  = convFFT(Vtip,rho).real * renorm
    #print "rho  ", rho.shape  
    #print "Vtip ", Vtip.shape  
    Vtip = np.roll( Vtip, -shifts[1], axis=1)
    Vtip = np.roll( Vtip, -shifts[0], axis=0)
    return phmap, Vtip, rho , dd

def photonMap2D_stamp( rhoTrans, lvec, z=10.0, sigma=1.0, multipole_dict={'s':1.0}, rots=[0.0], poss=[ [0.0,0.0] ], coefs=[ [1.0,0.0] ], ncanv=(300,300),byCenter=False ):
    sh = rhoTrans.shape
    #print "shape: ", sh
    #print lvec
    dx   = lvec[3][2]/sh[0]; #print lvec[3][2],sh[0]
    dy   = lvec[2][1]/sh[1]; #print lvec[2][1],sh[1]
    dd = (dx,dy)
    #print " (dx,dy) ", dd

    dtype=np.complex128
    if isinstance(coefs[0], float): dtype=np.float64    
    #canvas = np.zeros( ncanv[::-1], dtype=dtype )
    rho    = np.sum  (  rhoTrans, axis=2 )
    rho    = rho.astype( dtype ) 
    canvas = np.zeros( ncanv, dtype=dtype ) 
    
    #rho    = np.ascontiguousarray( rho,    dtype=np.complex128 )
    #canvas = np.ascontiguousarray( canvas, dtype=np.complex128 )

    for i in range(len(poss)):
        pos = [ poss[i][0]+ncanv[0]*0.5*dx,   poss[i][1]+ncanv[1]*0.5*dy  ]
        coef = coefs[i]
        if isinstance(coef, float):
            #print("GU.stampToGrid2D()") 
            GU.stampToGrid2D( canvas, rho, pos, rots[i], dd=dd, coef=coef, byCenter=byCenter )
        else:
            #print("GU.stampToGrid2D_complex()")
            coef = complex( coef[0], coef[1] )
            GU.stampToGrid2D_complex( canvas, rho, pos, rots[i], dd=dd, coef=coef, byCenter=byCenter)

    #canvas = np.zeros((300,300))

    Vtip, shifts = makeTipField2D( ncanv[:2], dd, z=z, sigma=sigma, multipole_dict=multipole_dict )
    #renorm = 1./( (Vtip**2).sum() * (rho.real**2+rho.imag**2).sum() )
    renorm = 1./( (Vtip**2).sum() )
    phmap  = convFFT(Vtip,canvas) * renorm
    #print "rho  ", rho.shape  
    #print "Vtip ", Vtip.shape  
    Vtip = np.roll( Vtip, (-shifts[1]), axis=1)
    Vtip = np.roll( Vtip, (-shifts[0]), axis=0)
    return phmap, Vtip, canvas, dd


def photonMap3D_stamp( rhoTrans, lvec, z=10.0, sigma=1.0, multipole_dict={'s':1.0}, rots=[0.0], poss=[ [0.0,0.0] ], coefs=[ [1.0,0.0] ], ncanv=(300,300), byCenter=False ):
    sh  = rhoTrans.shape
    if len(ncanv)<3:
        ncanv = ( (ncanv[0],ncanv[1],sh[2]) )
    dtype=np.complex128
    if isinstance(coefs[0], float): dtype=np.float64    
    canvas = np.zeros( ncanv[::-1],        dtype=dtype )
    rho    = rhoTrans.transpose((2,1,0)).astype( dtype ).copy()
    #print "shape: stamp ", rho.shape, " canvas ", canvas.shape
    #print lvec
    dx   = lvec[3][2]/sh[0]; #print lvec[3][2],sh[0]
    dy   = lvec[2][1]/sh[1]; #print lvec[2][1],sh[1]
    dz   = lvec[1][0]/sh[2]; #print lvec[1][0],sh[2]
    dd = (dx,dy,dz);    #print " dd ", dd
 
    for i in range(len(poss)):
        pos_ = poss[i]
        pos_z = 0.0
        if len(pos_)>2: pos_z=pos_[2]
        pos = [ pos_[0]+ncanv[0]*0.5*dx,   pos_[1]+ncanv[1]*0.5*dy, pos_z ]
        coef = coefs[i]
        if isinstance(coef, float):
            #print("GU.stampToGrid3D()") 
            GU.stampToGrid3D( canvas, rho, pos, rots[i], dd=dd, coef=coef, byCenter=byCenter )
        else:
            #print("GU.stampToGrid3D_complex()")
            coef = complex( coef[0], coef[1] )
            GU.stampToGrid3D_complex( canvas, rho, pos, rots[i], dd=dd, coef=coef, byCenter=byCenter )

    Vtip, shifts = makeTipField3D( ncanv, dd, z0=z, sigma=sigma, multipole_dict=multipole_dict )
    #renorm = 1./( (Vtip**2).sum() * (rho.real**2+rho.imag**2).sum() )
    renorm = 1./( (Vtip**2).sum() )
    phmap  = convFFT(Vtip,canvas) * renorm
    #print "rho  ", rho.shape  
    #print "Vtip ", Vtip.shape  
    #Vtip = np.roll( Vtip, -shifts[2], axis=2)
    Vtip = np.roll( Vtip, -shifts[1], axis=1)
    Vtip = np.roll( Vtip, -shifts[0], axis=2)
    return phmap, Vtip, canvas, dd

def makeTransformMat( ns, lvec, angle=0.0, rot=None ):
    nx,ny,nz=ns
    #nz,ny,nx=ns
    if rot is None:
        #ci = np.cos(angle)
        #si = np.sin(angle)
        #rot = np.array([[ci,+si,0.],[-si,ci,0.],[0.,0.,1.]])
        #rot = np.array([[ci,-si,0.],[+si,ci,0.],[0.,0.,1.]])
        rot = GU.rot3DFormAngle(angle)
    lvec = lvec  + 0.
    lvec[0,:]*=1./nx
    lvec[1,:]*=1./ny
    lvec[2,:]*=1./nz
    mat = np.dot( lvec, rot )
    print("mat ", mat)
    return mat

def solveExcitonSystem( rhoTrans, lvec, poss, rots, ndim=None, byCenter=False, Ediag=1.0 ):
    '''
    Solve coupled excitonic system according to :
    https://chem.libretexts.org/Bookshelves/Physical_and_Theoretical_Chemistry_Textbook_Maps/Book%3A_Time_Dependent_Quantum_Mechanics_and_Spectroscopy_(Tokmakoff)/15%3A_Energy_and_Charge_Transfer/15.03%3A_Excitons_in_Molecular_Aggregates
    '''
    print(" >>>>!!!!! DEBUG : solveExcitonSystem() .... this is WIP, do not take seriously ")
    n = len(poss)
    H = np.eye(n)*Ediag
    if ndim is not None: # down-sample ?
        ndim1 = rhoTrans.shape
        sum1 = (rhoTrans**2).sum()
        rhoTrans = GU.downSample3D( rhoTrans, ndim=ndim )
        #print rhoTrans.shape
        sum2 = (rhoTrans**2).sum()
        ndim2 = rhoTrans.shape 
        print(sum2, sum1)
        print(sum2/(ndim2[0]*ndim2[1]*ndim2[2]), sum1/(ndim1[0]*ndim1[1]*ndim1[2]))
        GU.saveXSF("rhoTrans_donw.xsf", rhoTrans, lvec )
        #exit()
    poss = np.array(poss)
    lvec=np.array(lvec[1:][::-1,::-1])
    print("lvec ", lvec)

    # check 

    # dipole-dipole interaction prefactors 
    coulomb_const = 14.3996   # [eV*A/e^2]  # https://en.wikipedia.org/wiki/Coulomb_constant
    #sh = rhoTrans.shape
    #dV            = (lvec[0,0]*lvec[1,1]*lvec[2,2])/(sh[0]*sh[1]*sh[2])  
    prefactor     = coulomb_const #/(dV*dV)
    print("checkSum rhoTrans ", (rhoTrans**2).sum())

    #DEBUG
    #print "rhoTrans.shape ", rhoTrans.shape
    #rhoTrans[:,:,:] = 0.0; rhoTrans[-2,-2,-2]=1.0    # NOTE: it is ordered as [nx,ny,nz]
    #rhoTrans[:,:,:] = 0.0; rhoTrans[0,0,0]=1.0

    ns = rhoTrans.shape

    for i in range(n):
        rot1 = makeTransformMat( rhoTrans.shape, lvec, rots[i] )
        p1=poss[i]
        print("p1 shape:",p1.shape)
        if byCenter: p1 = p1 + rot1[0,:]*(ns[0]*-0.5) + rot1[1,:]*(ns[1]*-0.5)

        coefs1 = GU.evalMultipole( rhoTrans, rot=rot1 )
        print("multipoles coefs ", coefs1)

        for j in range(i):
            #print "eva H[%i,%i] " %(i,j)
            #dpos = poss[i] - poss[j]
            rot2 = makeTransformMat( rhoTrans.shape, lvec, rots[j] )
            GU.setDebugFileName( "coulombGrid_%03i_%03i_.xyz" %(i,j) )
            #eij = GU.coulombGrid_brute( rhoTrans, rhoTrans, dpos=dpos, rot1=mat1, rot2=mat2 )
            p2 = poss[j]
            if byCenter: p2 = p2 + rot2[0,:]*(ns[0]*-0.5) + rot2[1,:]*(ns[1]*-0.5)
            eij = GU.coulombGrid_brute( rhoTrans, rhoTrans, pos1=p1, pos2=p2, rot1=rot1, rot2=rot2 )

            #coefs2 = GU.evalMultipole( rhoTrans, rot=rot2 )

            eij *= prefactor
            H[i,j]=eij
            H[j,i]=eij

            #print "mat1 ", mat1
            #print "mat2 ", mat2
            #print "dpos ", dpos
            #print "eij ",  eij
         #exit()
     
    #ABAB
#    H[1,2]*=0; H[2,1]*=0; H[2,3]*=0; H[3,2]*=0; H[3,0]*=0; H[0,3]*=0; H[0,1]*=0; H[1,0]*=0; #H[0,0]*=0.999; H[2,2]*=0.999
    

     
    #AAAB
#    H[0,3]*=0;  H[3,0]*=0;  H[1,3]*=0;  H[3,1]*=0; H[2,3]*=0; H[3,2]*=0; #H[3,3]*=0.999

    
    #AABB
#    H[2,0]*=0; H[0,2]*=0; H[1,2]*=0; H[2,1]*=0; H[0,3]*=0; H[3,0]*=0; H[3,1]*=0; H[1,3]*=0; #H[0,0]*=0.999;H[2,2]*=0.999;

    print("H  = \n", H)
    es,vs = np.linalg.eig(H)
    
#    print("eigenvalues    ", es)
#    print("eigenvectors \n", vs)

    print("!!! ordering Eigen-pairs ")
    idx          = np.argsort(es)
    es  = es[idx]
    #vs = (vs[:,idx]).transpose()
    vs = vs.transpose()
    vs = vs[idx]

    print("eigenvalues  ", es)
    print("eigenvectors \n", vs)
#    for i,v in enumerate(vs):
#        print("E[%i]=%g" %(i,es[i]), " v=",v, " |v|=",(v**2).sum())
#    print(" <<<<!!!!! DEBUG : solveExcitonSystem() DONE .... this is WIP, do not take seriously ")
    return es,vs,H

# ============== presets

def makePreset_row( n, dx=5.0, ang=0.0 ): 
    rots  = [ ang ] * n
    poss  = [ [(i-0.5*(n-1))*dx,0.0,0.0] for i in range(n) ]
    return poss, rots

def makePreset_cycle( n, R=10.0, ang0=0.0 ):
    dang = np.pi*2/n
    rots=[]; poss=[]
    for i in range(n):
        a=dang*i 
        poss.append( [-np.cos(a)*R ,np.sin(a)*R,0] )
        rots.append( -a+ang0 )
    return poss, rots

def makePreset_arr1( m,n, R=10.0 ):
    dang = np.pi/2
    rots=[]; poss=[]
    for i in range(m):
        for j in range(n):
            ii=(i-(m-1)/2.)
            jj=(j-(n-1)/2.)
            poss.append( [ii*R ,jj*R,0] )
            rots.append((j%2+((i+1)%2 * (n+1)%2))*dang )
    return poss, rots



def normalizeGridWf( F ):
    q = (F**2).sum()
    return F/np.sqrt(q)

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option( "-y", "--ydim",   action="store", type="int", default="500", help="height of canvas")
    parser.add_option( "-x", "--xdim",   action="store", type="int", default="500", help="width of canvas")
    parser.add_option( "-H", "--homo",   action="store", type="string", default="homo.cube", help="orbital of electron hole;    3D data-file (.xsf,.cube)")
    parser.add_option( "-L", "--lumo",   action="store", type="string", default="lumo.cube", help="orbital of excited electron; 3D data-file (.xsf,.cube)")
    parser.add_option( "-D", "--dens",   action="store", type="string", default="",         help="transition density; 3D data-file (.xsf,.cube)")
    parser.add_option( "-R", "--radius", action="store", type="float",  default="1.0", help="tip radius")
    parser.add_option( "-z", "--ztip",   action="store", type="float",  default="5.0", help="tip above substrate")
    parser.add_option( "-t", "--tip",    action="store", type="string", default="s",   help="tip compositon s,px,py,pz,d...")
    parser.add_option( "-e", "--excitons",   action="store_true",  default=False, help="callculate deloc. exitons of J-aggregate ( just WIP !!! )")
    parser.add_option( "-v", "--volumetric", action="store_true", default=False,  help="calculate on 2D grid, much faster")

    #parser.add_option( "-o", "--output", action="store", type="string", default="pauli", help="output 3D data-file (.xsf)")
    (options, args) = parser.parse_args()

    #rho1, lvec1, nDim1, head1 = GU.loadXSF("./pyridine/CHGCAR.xsf")
    #rho2, lvec2, nDim2, head2 = GU.loadXSF("./CO_/CHGCAR.xsf")

    np.set_printoptions(linewidth=400)


    hcanv = options.ydim
    wcanv = options.xdim

    if options.dens != "":
        rhoTrans, lvec, nDim, head = GU.loadCUBE( options.dens )
    else: 
        print(( ">>> Loading HOMO from ", options.homo, " ... " ))
        homo, lvecH, nDimH, headH = GU.loadCUBE( options.homo )
        print(( ">>> Loading LUMO from ", options.lumo, " ... " ))
        lumo, lvecL, nDimL, headL = GU.loadCUBE( options.lumo )
        lvec=lvecH; nDim=nDimH; headH=headH

        homo = normalizeGridWf( homo )
        lumo = normalizeGridWf( lumo )
        rhoTrans = homo*lumo
        # ---- check normalization   |Psi^2| = 1
        #print "lvec", lvec
        #print "Ls  ", lvec[1,0], lvec[2,1], lvec[3,2]
        #print "nDim", nDim
        #dV  = (lvec[1,0]*lvec[2,1]*lvec[3,2])/((nDim[0]+1)*(nDim[1]+1)*(nDim[2]+1))
        #print "dV ", dV
        #q = (homo**2).sum(); print "qsum ",q
        
        q = (homo**2).sum(); print("q(homo) ",q)
        q = (lumo**2).sum(); print("q(lumo) ",q)
        #q *= dV**2;          print "q    ",q
        #exit()  

    '''
    rho  = np.sum(  rhoTrans, axis=2)
    canvas = np.zeros((300,300))
    #dx   = lvec[3][2]/sh[0]; print lvec[3][2],sh[0]
    #dy   = lvec[2][1]/sh[1]; print lvec[2][1],sh[1]
    #dd = (dx,dy)
    GU.stampToGrid2D( canvas, rho, [2.0,60.0], np.pi/4.0, dd=[1.0,1.0] )
    plt.imshow(canvas)
    plt.show()
    '''

    #byCenter = False
    byCenter = True

    #tipDict =  { 's': 1.0, 'pz':0.1545  , 'dz2':-0.24548  }
    #tipDict =  { 's': 1.0, 'py':1.0  }
    #tipDict =  { 's': 1.0, 'dy2':1.0  }
    tipDict =  { 's': 1.0 }
    #tipDict =  { 'px': 1.0  }
    #tipDict =  { 'py': 1.0  }

    #phmap, Vtip, rho =  photonMap2D( rhoTrans, tipDict, lvec, z=0.5, sigma=0.0, multipole_dict=tipDict )

    fromDeg = np.pi/180.
    '''
    rots  =[-30.0*fromDeg,45.0*fromDeg]
    #poss =[ [10.0,5.0] ,  [10.0,10.0] ]
    poss  =[ [-5.0,10.0] ,  [5.0,-5.0] ]
    #poss =[ [0.0,10.0]  ]
    #poss =[ [200.0,50.0] ,  [50.0,50.0] ]
    #coefs=[ [1.0,0.0],      [0.0,1.0]     ]
    #coefs=[ [1.0,0.0],      [-1.0,0.0]     ]
    coefs=[ 1.0,      -1.0     ]
    #rots =[0.0]
    #poss =[ [300.0,50.0]]
    #coefs=[ [1.0,0.0]   ]
    '''

    #poss,rots = makePreset_row  ( 3, dx=15.9, ang=0*fromDeg ) 
    poss,rots = makePreset_cycle( 4, R=8., ang0=30*fromDeg )
    #poss,rots = makePreset_row( 2, dx=15.9, ang=-0.*fromDeg )
    #poss,rots = makePreset_arr1( 3,4,R=11.6 )
    
    #poss =[ [0.0,.0]  ]

    #rots =[-10.*180.*3.14]
    coefs = np.ones(len(rots))
    #coefs = [[0.9,0.1]]

    if options.excitons:
        print(rhoTrans.shape, nDim)
        subsamp = 6  # seems sufficient to obtain 1e-3 accuracy 
        #subsamp = 5 
        es,vs,H = solveExcitonSystem( rhoTrans, lvec, poss, rots, Ediag=1.0, ndim=(nDim[0]//subsamp,nDim[1]//subsamp,nDim[2]//subsamp), byCenter=byCenter )

        #coefs = vs[0]  # Take first eigenvector
        #coefs = vs[1]
        #coefs = vs[2]
    
        #exit()
    else:
        vs=[coefs]

    
    plt.figure(figsize=(6,len(vs)*3))

    for ipl in range(len(vs)):
        coefs=vs[ipl]

        if not options.volumetric:
            phmap, Vtip, rho, dd =  photonMap2D_stamp( rhoTrans, lvec, z=options.ztip, sigma=options.radius, multipole_dict=tipDict, rots=rots, poss=poss, coefs=coefs, ncanv=(wcanv,hcanv), byCenter=byCenter )
            (dx,dy)=dd
        else:
            phmap_, Vtip_, rho_, dd =  photonMap3D_stamp( rhoTrans, lvec, z=options.ztip, sigma=options.radius, multipole_dict=tipDict, rots=rots, poss=poss, coefs=coefs, ncanv=(wcanv,hcanv), byCenter=byCenter )
            phmap = np.sum(phmap_,axis=0)
            Vtip  = np.sum(Vtip_ ,axis=0)
            rho   = np.sum(rho_  ,axis=0)
            (dx,dy,dz)=dd

        #print("dd ",  dd)
        sh=phmap.shape
        extent=( -sh[0]*dd[0]*0.5,sh[0]*dd[0]*0.5,-sh[1]*dd[1]*0.5, sh[1]*dd[1]*0.5)
    
    
        #plt.subplot(i+1,3,2); plt.imshow( Vtip.real, extent=extent , origin='image' ,cmap='gray'); 
        #plt.xlabel('X[A]'); plt.ylabel('Y[A]'); plt.colorbar(); 
        #plt.title('Tip Field')
        #plt.subplot(1,2,1); plt.imshow( rho.real  **2 + rho.imag  **2, origin='image' ); plt.colorbar(); plt.title('Transient Density')
        plt.subplot(len(vs),2,1+2*ipl); plt.imshow( rho.real, extent=extent, origin='image',cmap='seismic');
        #plt.xlabel('X[A]'); plt.ylabel('Y[A]'); plt.colorbar(); 
        #plt.title('Transient Density')
        
        plotBoxes( poss, rots, lvec, byCenter=byCenter )

        res=(phmap.real**2+phmap.imag**2)
    
        plt.subplot(len(vs),2,2+2*ipl); plt.imshow( res, extent=extent, origin='image',cmap='gist_heat'); #plt.xlabel('X[A]'); plt.ylabel('Y[A]'); plt.colorbar(); 
        #plt.title('Photon Map')
    
    
    print("Done") 
    plt.show()
    

    '''
    
    #print( ">>> Evaluating convolution E(R) = A*Integral_r ( rho_tip^B(r-R) * rho_sample^B(r) ) using FFT ... " )
    #Fx,Fy,Fz,E = fFFT.potential2forces_mem( rhoTrans, lvec, nDimH, rho=tip, doForce=True, doPot=True, deleteV=False )

    Vtip =  fFFT.getMultiploleGrid( lvec, nDimH, sigma=1.0, multipole_dict=tip, tilt=0.0 )
    #getMultiplole( sampleSize, X, Y, Z, dd, sigma=0.7, multipole_dict=None, tilt=0.0 ):

    couplings = fFFT.convolveFFT( rhoTrans, Vtip, lvec, nDimH )

    GU.saveXSF( "couplMap.xsf", couplings, lvec, head=headH )
    GU.saveXSF( "Vtip.xsf", Vtip, lvec, head=headH )

    GU.saveXSF( "HOMO.xsf", homo, lvec, head=headH )
    GU.saveXSF( "LUMO.xsf", lumo, lvecL, head=headL )
    GU.saveXSF( "rhoTrans_HOMO_LUMO.xsf", rhoTrans, lvec, head=headH )
    '''

