import numpy as n
import pylab as pl
import capo as C
from glob import glob
import aipy as a


folded=True
#dirty = n.load('pspec_PGProcessedFiltered_DirtyWideFRF_95_115_I.npz')
dirtylist = glob('pspec_PGProcessed*DirtyWideFRF*.npz')
#res = n.load('pspec_PGProcessedFiltered_ResidualWideFRF_95_115_I.npz')
#resW = n.load('pspec_Vanilla_ResidualWideFRF_95_115_I.npz')   #old_dirtywidefrf.npz')
reslist = glob('pspec_PGProcessed*ResidualWideFRF*.npz')
#resW = n.load('pspec_PGInHorizon_ResidualWideFRF_95_115_I.npz')
#resW = n.load('pspec_FilterAtHorizon.npz')
chans=203.
uv = a.miriad.UV('ZeroDayNoiseInjection.uvB')
aa = a.cal.get_aa('psa6240_FHD', uv['sdf'], uv['sfreq'], uv['nchan'])
filters = C.dspec.wedge_width_by_bl(aa, uv['sdf'], uv['nchan'], offset=15.0)
bins = filters[(41,49)]

k_d = []
pk_d = []
for i in dirtylist:
    print i
    dirty = n.load(i)
    k_d.append(dirty['k'])
    pk_d.append(dirty['k3pk'])
pk_d = n.array(pk_d)
k_r = []
pk_r = []
for j in reslist:
    print j
    residual = n.load(j)
    k_r.append(residual['k'])
    pk_r.append(residual['k3pk'])
pk_r = n.array(pk_r)
print n.corrcoef(pk_d,pk_r)
pl.plot(pk_d[0,:],pk_r[0,:],'.')
pl.show()
#k_d = dirty['k']
#k_rW = resW['k']
#k_r = res['k']

#pk_d = n.abs(dirty['k3pk'])
#pk_rW = resW['k3pk']
#pk_r = n.abs(res['k3pk'])

#err_d = dirty['k3err']
#err_r = res['k3err']
#err_rW = resW['k3err']

fig = pl.figure()
ax = fig.add_subplot(211)

tau_h = 100 + 15. #in ns
k_h = C.pspec.dk_deta(C.pspec.f2z(dirty['freq'])) * tau_h

pl.vlines(k_h, -1e7, 1e13, linestyles='--', linewidth=1.5)
#pl.vlines(-k_h, -1e7, 1e13, linestyles='--', linewidth=1.5)
pl.axvspan(-k_h,k_h,color='red',alpha=0.5)

ax.set_yscale("log",nonposx='noclip')
ax.errorbar(k_d,n.abs(pk_d),yerr=err_d,fmt='ko')
ax.errorbar(k_rW,n.abs(pk_rW),yerr=err_rW,fmt='r.')
ax.errorbar(k_r,n.abs(pk_r),yerr=err_r,fmt='b.')
ax.set_ylim(n.min(n.append(pk_d,pk_r))+err_r.min(),n.max(n.append(pk_r,pk_d))+err_d.max())
ax.set_xticklabels([])

pl.xlabel(r'$k_\parallel\ [h\ {\rm Mpc}^{-1}]$', fontsize='large')
pl.ylabel(r'$P(k)[\ {\rm mK}^2\ (h^{-1}\ {\rm Mpc})^3]$',fontsize='large')
pl.title('z = '+str(round(1.42/dirty['freq'] - 1,2)))

#tau_h = 100 + 15. #in ns
#k_h = C.pspec.dk_deta(C.pspec.f2z(dirty['freq'])) * tau_h

pl.vlines(k_h, -1e7, 1e13, linestyles='--', linewidth=1.5)
pl.vlines(-k_h, -1e7, 1e13, linestyles='--', linewidth=1.5)

ax2 = fig.add_subplot(212)
err = (pk_r/pk_d)*n.sqrt((err_r/pk_r)**2 +(err_d/pk_d)**2 - 2*(err_d*err_r)/(pk_d*pk_r))#/n.sqrt(100)
ax2.errorbar(k_r,pk_r/pk_d,yerr=err,fmt='+')
pl.hlines(1,-0.5,0.5,linestyles='--')
ax2.set_xticklabels(k_d)
ax2.set_ylim(0,1.1)
pl.vlines(k_h, 0, 1.1, linestyles='--', linewidth=1.5)
pl.vlines(-k_h, 0, 1.1, linestyles='--', linewidth=1.5)
pl.axvspan(-k_h,k_h,color='red',alpha=0.5)
#ax2.set_yscale("log",nonposx='clip')
#ax2.errorbar(k_d,n.abs(pk_d),yerr=err_d,fmt='ko')
#ax2.errorbar(k_r,n.abs(pk_r),yerr=err_r,fmt='.')
#ax2.set_ylim(n.min(n.append(pk_r,pk_d))+err_r.min(),n.max(n.append(pk_d,pk_r))+err_d.max())

#pl.xlabel(r'$k_\parallel\ [h\ {\rm Mpc}^{-1}]$', fontsize='large')
#pl.ylabel(r'$P(k)[\ {\rm mK}^2\ (h^{-1}\ {\rm Mpc})^3]$',fontsize='large')
#pl.title('z = '+str(round(1.42/dirty['freq'] - 1,2)))


#pl.semilogy(k_d,pk_d,'.')
pl.show()
print dirty.keys()
