import numpy as np
import subprocess, datetime, os
from astropy.io import fits
import sys, pylab, copy

def writefits(npzfiles, repopath=None, ex_ants=[], name_dict={}):
    ### This function writes the solution from output npz files from omni_run to a fits file.   ### 
    ### npzfiles can be a list of npz files with solutions for different polarizations but for  ###.
    ### the same obs id. repopath is for writing the program of origin and git hash, e.g., if   ###
    ### the solution comes from capo, then repopath=/path/to/capo/. ex_ants is used to indicate ###
    ### which antennas are flagged. name_dict is for writing antenna names to fits.             ### 
     
    p2pol = {'EE': 'x','NN': 'y','EN': 'cross', 'NE': 'cross'}

    fn0 = npzfiles[0].split('.')
    if len(npzfiles) > 1: fn0[-2] = 'O'
    else: fn0[-2] += 'O'
    fn0[-1] = 'fits'
    outfn = '.'.join(fn0)
    print outfn
    if os.path.exists(outfn):
        print '   %s exists, skipping...' % outfn
        return 0

    today = datetime.date.today().strftime("Date: %d, %b %Y")
    if not repopath == None:
        githash = subprocess.check_output(['git','rev-parse','HEAD'], cwd=repopath)
        ori = subprocess.check_output(['git','remote','show','origin'], cwd=repopath)
        ori = ori.split('\n')[1].split(' ')[-1]
        githash = githash.replace('\n','')
    else:
        githash = ''
        ori = ''

    datadict = {}
    ant = []
    for f,filename in enumerate(npzfiles):
        data = np.load(filename)
        for ii, ss in enumerate(data):
            if ss[0].isdigit():
                datadict[ss] = data[ss]
                intss = int(ss[0:-1])
                if not intss in ant:
                    ant.append(intss)
    ant.sort()
    if name_dict == {}: tot = ant + ex_ants
    else: tot = name_dict.keys()
    tot.sort()
    time = data['jds']
    freq = data['freqs']/1e6
    pol = ['EE', 'NN', 'EN', 'NE']
    nt = time.shape[0]
    nf = freq.shape[0]
    na = len(tot)
    nam = []
    for nn in range(0,na):
        try: nam.append(name_dict[tot[nn]])
        except(KeyError): nam.append('ant'+str(tot[nn]))
    datarray = []
    flgarray = []
    for ii in range(0,4):
        dd = []
        fl = []
        for jj in range(0,na):
            try: dd.append(datadict[str(tot[jj])+p2pol[pol[ii]]])
            except(KeyError): dd.append(np.ones((nt,nf)))
            if tot[jj] in ex_ants: fl.append(np.ones((nt,nf),dtype=bool))
            else: fl.append(np.zeros((nt,nf),dtype=bool))
        datarray.append(dd)
        flgarray.append(fl)
    datarray = np.array(datarray)
    datarray = datarray.swapaxes(0,2).swapaxes(1,2).swapaxes(2,3).reshape(4*nt*nf*na)
    flgarray = np.array(flgarray)
    flgarray = flgarray.swapaxes(0,2).swapaxes(1,2).swapaxes(2,3).reshape(4*nt*nf*na)
    tarray = np.resize(time,(4*nf*na,nt)).transpose().reshape(4*nf*nt*na)
    parray = np.array((['EE']*(nf*na)+['NN']*(nf*na)+['EN']*(nf*na)+['NE']*(nf*na))*nt)
    farray = np.array(list(np.resize(freq,(na,nf)).transpose().reshape(na*nf))*4*nt)
    numarray = np.array(tot*4*nt*nf)
    namarray = np.array(nam*4*nt*nf)

    prihdr = fits.Header()
    prihdr['DATE'] = today
    prihdr['ORIGIN'] = ori
    prihdr['HASH'] = githash
    prihdr['PROTOCOL'] = 'Divide uncalibrated data by these gains to obtain calibrated data.'
    prihdr['NTIMES'] = nt
    prihdr['NFREQS'] = nf
    prihdr['NANTS'] = na
    prihdr['NPOLS'] = 4
    prihdu = fits.PrimaryHDU(header=prihdr)
    colnam = fits.Column(name='ANT NAME', format='A10', array=namarray)
    colnum = fits.Column(name='ANT INDEX', format='I',array=numarray)
    colf = fits.Column(name='FREQ (MHZ)', format='E', array=farray)
    colp = fits.Column(name='POL', format='A4', array=parray)
    colt = fits.Column(name='TIME (JD)', format='D', array=tarray)
    coldat = fits.Column(name='GAIN', format='M', array=datarray)
    colflg = fits.Column(name='FLAG', format='L', array=flgarray)
    cols = fits.ColDefs([colnam, colnum, colf, colp, colt, coldat, colflg])
    tbhdu = fits.BinTableHDU.from_columns(cols)
    hdulist = fits.HDUList([prihdu, tbhdu])
    hdulist.writeto(outfn)
    
    
def read_fits(filename, pols):
    ### This function reads in the solution from fits file, which returns a dictionary of polarization,  ###
    ### each polarization is a dictionary of antenna indexes, which has a value as an numpy array with   ###
    ### the shape (Ntimes, Nfreqs)                                                                       ###
    g0 = {}
    poldict = {'EE': 'xx', 'NN': 'yy', 'EN': 'xy', 'NE': 'yx'}
    hdu = fits.open(filename)
    Ntimes = hdu[0].header['NTIMES']
    Nfreqs = hdu[0].header['NFREQS']
    Npols = hdu[0].header['NPOLS']
    Nants = hdu[0].header['NANTS']
    ant_index = hdu[1].data['ANT INDEX'][0:Nants]
    pol_list = hdu[1].data['POL'][0:Nfreqs*Nants*Npols].reshape(Npols,Nants*Nfreqs)[:,0]
    data_list = hdu[1].data['GAIN'].reshape((Ntimes,Npols,Nfreqs,Nants)).swapaxes(0,1).swapaxes(2,3).swapaxes(1,2) #Npols,Nants,Ntimes,Nfreqs
    for ii in range(0,Npols):
        polarization = poldict[pol_list[ii]]
        if not polarization in pols: continue
        g0[polarization[0]] = {}
        for jj in range(0,Nants):
            g0[polarization[0]][ant_index[jj]]=data_list[ii][jj]
    return g0


def fc_gains_to_fits(npznames,filename,repopath=None,name_dict={}):
    #### For firstcal solution without time axis ###
    if not repopath == None:
        githash = subprocess.check_output(['git','rev-parse','HEAD'], cwd=repopath)
        ori = subprocess.check_output(['git','remote','show','origin'], cwd=repopath)
        ori = ori.split('\n')[1].split(' ')[-1]
        githash = githash.replace('\n','')
    else:
        ori = ''
        githash = ''
    today = datetime.date.today().strftime("Date: %d, %b %Y")
    outname = '%s.fc.fits'%filename
    print outname
    if os.path.exists(outname):
        print '   %s exists, skipping...' % outname
        return 0
    datadict = {}
    ant = []
    for npz in npznames:
        data = np.load(npz)
        for ii, ss in enumerate(data):
            if ss[0].isdigit():
                datadict[ss] = data[ss][0]
                intss = int(ss[0:-1])
                if not intss in ant:
                    ant.append(intss)
    ant.sort()
    try: ex_ants = list(data['ex_ants'])
    except(KeyError): ex_ants = []
    if name_dict == {}: tot = ant + ex_ants
    else: tot = name_dict.keys()
    tot.sort()
    freq = data['freqs']/1e6  #in MHz
    pol = ['x', 'y']
    Na = len(tot)
    Nf = freq.shape[0]
    parray = np.array(['x']*Nf*Na+['y']*Nf*Na)
    farray = np.array(list(np.resize(freq,(Na,Nf)).transpose().reshape(Na*Nf))*2)
    datarray = []
    flgarray = []
    for ii in range(0,2):
        dd = []
        fl = []
        for jj in range(0,Na):
            try: dd.append(datadict[str(tot[jj])+pol[ii]])
            except(KeyError): dd.append(np.ones((Nf),dtype=float))
            if tot[jj] in ex_ants: fl.append(np.ones((Nf),dtype=bool))
            else: fl.append(np.zeros((Nf),dtype=bool))
        datarray.append(dd)
        flgarray.append(fl)
    datarray = np.array(datarray)
    datarray = datarray.swapaxes(1,2).reshape(2*Nf*Na)
    flgarray = np.array(flgarray)
    flgarray = flgarray.swapaxes(1,2).reshape(2*Nf*Na)
    nam = []
    for nn in range(0,Na):
        try: nam.append(name_dict[tot[nn]])
        except(KeyError): nam.append('ant'+str(tot[nn]))
    numarray = np.array(tot*2*Nf)
    namarray = np.array(nam*2*Nf)

    prihdr = fits.Header()
    prihdr['DATE'] = today
    prihdr['ORIGIN'] = ori
    prihdr['HASH'] = githash
    prihdr['PROTOCOL'] = 'Divide uncalibrated data by these gains to obtain calibrated data.'
    prihdr['NFREQS'] = Nf
    prihdr['NANTS'] = Na
    prihdr['NPOLS'] = 2
    prihdu = fits.PrimaryHDU(header=prihdr)
    colnam = fits.Column(name='ANT NAME', format='A10', array=namarray)
    colnum = fits.Column(name='ANT INDEX', format='I',array=numarray)
    colf = fits.Column(name='FREQ (MHZ)', format='E', array=farray)
    colp = fits.Column(name='POL', format='A4', array=parray)
    coldat = fits.Column(name='GAIN', format='M', array=datarray)
    colflg = fits.Column(name='FLAG', format='L', array=flgarray)
    cols = fits.ColDefs([colnam, colnum, colf, colp, coldat, colflg])
    tbhdu = fits.BinTableHDU.from_columns(cols)
    hdulist = fits.HDUList([prihdu, tbhdu])
    hdulist.writeto(outname)

def fc_gains_from_fits(filename):
### for reading firstcal solution without time axis ###
    g0 = {}
    hdu = fits.open(filename)
    Nfreqs = hdu[0].header['NFREQS']
    Npols = hdu[0].header['NPOLS']
    Nants = hdu[0].header['NANTS']
    ant_index = hdu[1].data['ANT INDEX'][0:Nants]
    pol_list = hdu[1].data['POL'].reshape(Npols,Nants*Nfreqs)[:,0]
    data_list = hdu[1].data['GAIN'].reshape((Npols, Nfreqs, Nants)).swapaxes(1,2)
    for ii in range(0,Npols):
        p = pol_list[ii]
        g0[p] = {}
        for jj in range(0,Nants):
            g0[p][ant_index[jj]] = data_list[ii][jj]
    return g0

def read_ucla_txt(fn,pols={'xx','yy'}):
    g0 = {}
    f = open(fn,'r')
    Ntimes = []
    Nfreqs = []
    for line in f:
        temp = line.split(' ')[:7]
        if temp[0].startswith('#'): continue
        temp2 = []
        for ii, s in enumerate(temp):
            if ii == 0: continue
            elif s.strip() == 'EE': s = 'xx'
            elif s.strip() == 'NN': s = 'yy'
            elif s.strip() == 'EN': s = 'xy'
            elif s.strip() == 'NE': s = 'yx'
            temp2.append(s)
        if not temp2[2].strip() in pols: continue
        temp3 = [temp2[2], int(temp2[0]), float(temp2[3]), float(temp2[1]), float(temp2[4]), float(temp2[5])]  #temp3=[pol,ant,jds,freq,real,imag]
        if not temp3[2] in Ntimes: Ntimes.append(temp3[2])
        if not temp3[3] in Nfreqs: Nfreqs.append(temp3[3])
        if not g0.has_key(temp3[0][0]):
            g0[temp3[0][0]] = {}
        if not g0[temp3[0][0]].has_key(temp3[1]):
            g0[temp3[0][0]][temp3[1]] = []
        gg = complex(temp3[4],temp3[5])
        g0[temp3[0][0]][temp3[1]].append(gg)
    for pp in g0.keys():
        for ant in g0[pp].keys():
            g0[pp][ant] = np.array(g0[pp][ant])
            g0[pp][ant] = g0[pp][ant].reshape(len(Ntimes),len(Nfreqs))
    return g0

def plot_cal(cal1,cal2):
    c1 = copy.copy(cal1[0])
    c2 = copy.copy(cal2[0])
    for ii in range(0,c1.size):
        if c1[ii] == 0: c1[ii] = np.nan
    for ii in range(0,c2.size):
        if c2[ii] == 0: c2[ii] = np.nan
    pylab.plot(np.abs(c1),color='red')
    pylab.plot(np.abs(c2),color='blue')
    pylab.show()



