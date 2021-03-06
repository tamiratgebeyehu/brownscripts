#! /usr/bin/env python
"""
Filter visibilites per-baseline using a delay transform.
"""

import aipy as a, numpy as n, os, sys, optparse 
import capo as C
import scipy.signal

o = optparse.OptionParser()
o.set_usage('pspec_prep.py [options] *.uv')
o.set_description(__doc__)
a.scripting.add_standard_options(o, cal=True, ant=True, pol=True)
o.add_option('--nophs', dest='nophs', action='store_true',
    help='Do not phase to zenith bin.')
o.add_option('--nogain', dest='nogain', action='store_true',
    help='Do not normalize gain.')
o.add_option('--window', dest='window', default='none',
    help='DSP window to use.  Default: none')
o.add_option('--horizon', dest='offset', type=float, default=0.,
    help='An additional additive term (in ns) applied to the baseline length to determine horizon cutoff.  Default is 0.')
o.add_option('--clean', dest='clean', type='float', default=1e-5,
    help='Deconvolve delay-domain data by the response that results from flagged data.  Specify a tolerance for termination.  Default 1e-5')
o.add_option('--model', dest='model', action='store_true',
    help='Return the foreground model summed with the residuals (in Fourier space).')
o.add_option('--fftpad', dest='fftpad', action='store_true',
    help='Pad the data with zeros prior to ffting.')
opts, args = o.parse_args(sys.argv[1:])

uv = a.miriad.UV(args[0])
aa = a.cal.get_aa(opts.cal, uv['sdf'], uv['sfreq'], uv['nchan'])
if opts.fftpad == True:
    fftadd = 1024 - uv['nchan']
else:
    fftadd = 0
filters = C.dspec.wedge_width_by_bl(aa, uv['sdf'], uv['nchan']+fftadd, offset=opts.offset)

for uvfile in args:
    if opts.model: uvofile = uvfile + 'F'
    else: uvofile = uvfile + 'B'
    print uvfile,'->',uvofile
    if os.path.exists(uvofile):
        print uvofile, 'exists, skipping.'
        continue
    uvi = a.miriad.UV(uvfile)
    a.scripting.uv_selector(uvi, opts.ant, opts.pol)
    uvo = a.miriad.UV(uvofile, status='new')
    uvo.init_from_uv(uvi)
    uvo.add_var('bin','d')
    if opts.fftpad == True:
        padw = n.zeros(1024)
        #padw[0:203] = window
        
    if opts.window == 'chebyshev':
        window = scipy.signal.chebwin(uvi['nchan'],300,sym=True)
    else:
        print opts.window
        window = a.dsp.gen_window(uvi['nchan'], window=opts.window)
#    padw[0:203] = window
#    window = padw
    curtime, zen = None, None
    def mfunc(uv, p, d, f):
        global curtime,zen
        crd,t,(i,j) = p
        if t != curtime:
            aa.set_jultime(t)
            lst = aa.sidereal_time()
            ubin,vbin,lstbin = C.pspec.bin2uv(C.pspec.uv2bin(0,0,lst))
            zen = a.phs.RadioFixedBody(lstbin, aa.lat, epoch=aa.epoch)
            zen.compute(aa)
            curtime = t
            print t
        pol = a.miriad.pol2str[uv['pol']]
        aa.set_active_pol(pol)
        u,v,w = aa.gen_uvw(i,j, src=zen)
        u,v = u.flatten()[-1], v.flatten()[-1]
        conj = False
        if u < 0: 
            u,v = -u, -v
            if not opts.nophs: conj = True
        uvo['bin'] = n.float(C.pspec.uv2bin(u, v, aa.sidereal_time()))
        if i == j: return p, d, f
        w = n.logical_not(f).astype(n.float)
        if n.average(w) < .5: return p, n.zeros_like(d), n.ones_like(f)
        if not opts.nophs: d = aa.phs2src(d, zen, i, j)
        if not opts.nogain: d /= aa.passband(i,j)
        if conj: d = n.conj(d)
        #### Do FFT padding
        if opts.fftpad == True:
            dp = n.zeros(1024,dtype=complex)
            dlen = len(d)
            dp[0:dlen] = d
            d = dp
            wp = n.zeros(1024,dtype=complex)
            wp[0:dlen] = w
            w = wp

        d *= w
        _d = n.fft.ifft(d * window)
        _w = n.fft.ifft(w * window)
        uthresh,lthresh = filters[(i,j)]
#        uthresh += 1
#        lthresh += 1
        area = n.ones(_d.size, dtype=n.int)
        area[uthresh:lthresh] = 0
        _d_cl, info = a.deconv.clean(_d, _w, tol=opts.clean, area=area, stop_if_div=False, maxiter=1000)
        if opts.model:
            #d_mdl = n.fft.fft(_d_cl + info['res'])
            #f = n.zeros_like(d_mdl)
            d_mdl = n.fft.fft(_d_cl)
            if opts.fftpad == True:
                d_mdl = d_mdl[0:dlen]
            #f = n.zeros_like(d_mdl)
            return p, d_mdl, f
        else:
            d_mdl = n.fft.fft(_d_cl)
            d_res = d - d_mdl*w
            if opts.fftpad == True:
                d_res = d_res[0:dlen]
            ## Edited flag array to only flag zeros
            #f = n.zeros_like(d_res)
            #f[n.where(d_res==0j)] = 1
            return p, d_res, f
 
    # Apply the pipe to the data
    uvo.pipe(uvi, mfunc=mfunc, raw=True, append2hist=' '.join(sys.argv)+'\n')
