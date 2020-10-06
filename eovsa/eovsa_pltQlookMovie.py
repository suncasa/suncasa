import os
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from sunpy import map as smap
import sunpy.cm.cm as cm_smap
import astropy.units as u
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.colorbar as colorbar
import matplotlib.patches as patches
from datetime import timedelta
from datetime import datetime
from glob import glob
import numpy as np
from astropy.time import Time
import calendar
from suncasa.utils import plot_mapX as pmX
import urllib.request
from sunpy.physics.differential_rotation import diffrot_map
from suncasa.utils import DButil
from tqdm import tqdm

# imgfitsdir = '/Users/fisher/myworkspace/'
# imgfitstmpdir = '/Users/fisher/myworkspace/fitstmp/'
# pltfigdir = '/Users/fisher/myworkspace/SynopticImg/eovsamedia/eovsa-browser/'

imgfitsdir = '/data1/eovsa/fits/synoptic/'
imgfitstmpdir = '/data1/workdir/fitstmp/'
pltfigdir = '/common/webplots/SynopticImg/eovsamedia/eovsa-browser/'


def clearImage():
    for (dirpath, dirnames, filenames) in os.walk(pltfigdir):
        for filename in filenames:
            for k in ['0094', '0193', '0335', '4500', '0171', '0304', '0131', '1700', '0211', '1600', '_HMIcont',
                      '_HMImag']:
                # for k in ['_Halph_fr']:
                if k in filename:
                    print(os.path.join(dirpath, filename))
                    os.system('rm -rf ' + os.path.join(dirpath, filename))


def pltEovsaQlookImageSeries(timobjs, spw, vmax, vmin, aiawave, fig=None, axs=None, imgoutdir=None, overwrite=False,
                             verbose=False):
    from astropy.visualization.stretch import AsinhStretch
    from astropy.visualization import ImageNormalize
    plt.ioff()
    imgfiles = []
    dpi = 512. / 4
    aiaDataSource = {"0094": 8,
                     "0193": 11,
                     "0335": 14,
                     # "4500": 17,
                     "0171": 10,
                     "0304": 13,
                     "0131": 9,
                     "1700": 16,
                     "0211": 12,
                     # "1600": 15,
                     "_HMIcont": 18,
                     "_HMImag": 19}

    tmjd = timobjs.mjd
    tmjd_base = np.floor(tmjd)
    tmjd_hr = (tmjd - tmjd_base) * 24
    for tidx, timobj in enumerate(tqdm(timobjs)):
        dateobj = timobj.to_datetime()
        timestr = dateobj.strftime("%Y-%m-%dT%H:%M:%SZ")
        tstrname = dateobj.strftime("%Y%m%dT%H%M%SZ")
        datestrdir = dateobj.strftime("%Y/%m/%d/")
        imgindir = imgfitsdir + datestrdir
        timobj_prevday = Time(tmjd[tidx] - 1, format='mjd')
        dateobj_prevday = timobj_prevday.to_datetime()
        datestrdir_prevday = dateobj_prevday.strftime("%Y/%m/%d/")
        imgindir_prevday = imgfitsdir + datestrdir_prevday

        # if not os.path.exists(imgindir): os.makedirs(imgindir)
        cmap = cm_smap.get_cmap('sdoaia304')

        if verbose: print('Processing EOVSA images for date {}'.format(dateobj.strftime('%Y-%m-%d')))
        key, sourceid = aiawave, aiaDataSource[aiawave]
        s, sp = 0, spw[0]

        figoutname = os.path.join(imgoutdir, 'eovsa_bd{:02d}_aia{}_{}.jpg'.format(s + 1, key, tstrname))

        if overwrite or (not os.path.exists(figoutname)):
            ax = axs[0]
            ax.cla()
            spwstr = '-'.join(['{:02d}'.format(int(sp_)) for sp_ in sp.split('~')])
            eofile = imgindir + 'eovsa_{}.spw{}.tb.disk.fits'.format(dateobj.strftime('%Y%m%d'), spwstr)
            if not os.path.exists(eofile):
                continue

            stretch = AsinhStretch(a=0.15)
            norm = ImageNormalize(vmin=vmin[s], vmax=vmax[s], stretch=stretch)
            eomap = smap.Map(eofile)
            eomap = eomap.resample(u.Quantity(eomap.dimensions) / 2)
            eomap.data[np.isnan(eomap.data)] = 0.0
            eomap_rot = diffrot_map(eomap, time=timobj)
            eomap_rot.data[np.where(eomap_rot.data < 0)] = 0.0
            eomap_rot.data[np.isnan(eomap_rot.data)] = 0.0

            t_hr = tmjd_hr[tidx]
            t_hr_st_blend = 0.0
            t_hr_ed_blend = 12.0
            if t_hr_st_blend <= t_hr < t_hr_ed_blend:
                eofile_prevday = imgindir_prevday + 'eovsa_{}.spw{}.tb.disk.fits'.format(
                    dateobj_prevday.strftime('%Y%m%d'), spwstr)
                if not os.path.exists(eofile_prevday):
                    continue
                eomap_prevd = smap.Map(eofile_prevday)
                eomap_prevd = eomap_prevd.resample(u.Quantity(eomap_prevd.dimensions) / 2)
                eomap_prevd.data[np.isnan(eomap_prevd.data)] = 0.0
                eomap_rot_prevd = diffrot_map(eomap_prevd, time=timobj)
                eomap_rot_prevd.data[np.where(eomap_rot_prevd.data < 0)] = 0.0
                alpha = (t_hr - t_hr_st_blend) / (t_hr_ed_blend - t_hr_st_blend)
                alpha_prevd = 1.0 - alpha
                # eomap_plt = smap.Map((eomap.data * alpha + eomap_prevd.data * alpha_prevd), eomap.meta)
                eomap_rot_plt = smap.Map((eomap_rot.data * alpha + eomap_rot_prevd.data * alpha_prevd), eomap_rot.meta)
            else:
                # eomap_plt = eomap
                eomap_rot_plt = eomap_rot

            # eomap_plt.plot(axes=ax, cmap=cmap, norm=norm)
            eomap_rot_plt.plot(axes=ax, cmap=cmap, norm=norm)

            ax.set_xlabel('')
            ax.set_ylabel('')
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.text(0.02, 0.02,
                    'EOVSA {:.1f} GHz  {}'.format(eomap.meta['CRVAL3'] / 1e9, dateobj.strftime('%d-%b-%Y %H:%M UT')),
                    transform=ax.transAxes, color='w', ha='left', va='bottom', fontsize=9)
            ax.text(0.98, 0.02, 'Max Tb {:.0f} K'.format(np.nanmax(eomap.data)),
                    transform=ax.transAxes, color='w', ha='right', va='bottom', fontsize=9)
            ax.set_xlim(-1227, 1227)
            ax.set_ylim(-1227, 1227)

            ax = axs[1]
            # for key, sourceid in aiaDataSource.items():
            ax.cla()

            if not os.path.exists(imgoutdir): os.makedirs(imgoutdir)
            sdourl = 'https://api.helioviewer.org/v2/getJP2Image/?date={}&sourceId={}'.format(timestr, sourceid)
            sdofile = os.path.join(imgoutdir, 'AIA' + key + '.{}.jp2'.format(tstrname))
            if not os.path.exists(sdofile):
                urllib.request.urlretrieve(sdourl, sdofile)

            if not os.path.exists(sdofile): continue
            sdomap = smap.Map(sdofile)
            norm = colors.Normalize()
            # sdomap_ = pmX.Sunmap(sdomap)
            if "HMI" in key:
                cmap = plt.get_cmap('gray')
            else:
                cmap = cm_smap.get_cmap('sdoaia' + key.lstrip('0'))
            sdomap.plot(axes=ax, cmap=cmap, norm=norm)
            # sdomap_.imshow(axes=ax, cmap=cmap, norm=norm)
            # sdomap_.draw_limb(axes=ax, lw=0.25, alpha=0.5)
            # sdomap_.draw_grid(axes=ax, grid_spacing=10. * u.deg, lw=0.25)
            ax.set_xlabel('')
            ax.set_ylabel('')
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.text(0.02, 0.02,
                    '{}/{} {}  {}'.format(sdomap.observatory, sdomap.instrument.split(' ')[0], sdomap.measurement,
                                          sdomap.date.strftime('%d-%b-%Y %H:%M UT')),
                    transform=ax.transAxes, color='w', ha='left', va='bottom', fontsize=9)
            ax.set_xlim(-1227, 1227)
            ax.set_ylim(-1227, 1227)
            fig.savefig(figoutname, dpi=np.int(dpi), quality=85)
        imgfiles.append(figoutname)

    return imgfiles


def main(year, month, day=None, ndays=30, show_warning=False):
    '''
    By default, the subroutine create EOVSA monthly movie
    '''
    if not show_warning:
        import warnings
        warnings.filterwarnings("ignore")
    # tst = datetime.strptime("2017-04-01", "%Y-%m-%d")
    # ted = datetime.strptime("2019-12-31", "%Y-%m-%d")
    if day is None:
        dst, ded = calendar.monthrange(year, month)
        tst = datetime(year, month, 1)
        ted = datetime(year, month, ded)
    else:
        if year:
            ted = datetime(year, month, day)
        else:
            ted = datetime.now() - timedelta(days=2)
        tst = Time(np.fix(Time(ted).mjd) - ndays, format='mjd').datetime
    tsep = datetime.strptime('2019-02-22', "%Y-%m-%d")

    vmaxs = [70.0e4, 30e4, 18e4, 13e4, 8e4, 6e4, 6e4]
    vmins = [-18.0e3, -8e3, -4.8e3, -3.4e3, -2.1e3, -1.6e3, -1.6e3]
    plt.ioff()
    fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(8, 4))
    fig.subplots_adjust(bottom=0.0, top=1.0, left=0.0, right=1.0, hspace=0.0, wspace=0.0)

    dateobs = tst
    imgfileslist = []
    while dateobs < ted:
        monthstrdir = dateobs.strftime("%Y/%m/")
        imgoutdir = imgfitstmpdir + monthstrdir
        movieoutdir = pltfigdir + monthstrdir
        for odir in [imgoutdir, movieoutdir]:
            if not os.path.exists(odir):
                os.makedirs(odir)

        # dateobs = datetime.strptime("2019-12-21", "%Y-%m-%d")

        if dateobs > tsep:
            spws = ['0~1', '2~5', '6~10', '11~20', '21~30', '31~43', '44~49']
        else:
            spws = ['1~3', '4~9', '10~16', '17~24', '25~30']
        spw = spws[2:3]
        vmax = vmaxs[2:3]
        vmin = vmins[2:3]
        aiawave = '0304'

        tdateobs = Time(Time(dateobs).mjd + np.arange(0, 24, 1) / 24, format='mjd')
        imgfiles = pltEovsaQlookImageSeries(tdateobs, spw, vmax, vmin, aiawave, fig=fig, axs=axs, overwrite=False,
                                            imgoutdir=imgoutdir)
        imgfileslist = imgfileslist + imgfiles
        dateobs = dateobs + timedelta(days=1)
    moviename = 'eovsa_bd01_aia304_{}'.format(dateobs.strftime("%Y%m"))
    DButil.img2movie(imgprefix=imgfileslist, outname=moviename, img_ext='jpg')
    os.system('mv {} {}'.format(os.path.join(imgoutdir + '../', moviename + '.mp4'),
                                os.path.join(movieoutdir, moviename + '.mp4')))
    plt.close('all')


# if __name__ == '__main__':
#     import sys
#     import numpy as np
#
#     # import subprocess
#     # shell = subprocess.check_output('echo $0', shell=True).decode().replace('\n', '').split('/')[-1]
#     # print("shell " + shell + " is using")
#
#     print(sys.argv)
#     try:
#         argv = sys.argv[1:]
#         if '--clearcache' in argv:
#             clearcache = True
#             argv.remove('--clearcache')  # Allows --clearcache to be either before or after date items
#         else:
#             clearcache = False
#
#         year = np.int(argv[0])
#         month = np.int(argv[1])
#         day = np.int(argv[2])
#         if len(argv) == 3:
#             dayspan = 30
#         else:
#             dayspan = np.int(argv[3])
#     except:
#         print('Error interpreting command line argument')
#         year = None
#         month = None
#         day = None
#         dayspan = 30
#         clearcache = True
#     print("Running pipeline_plt for date {}-{}-{}".format(year, month, day))
#     main(year, month, None, dayspan)


if __name__ == '__main__':
    '''
    Name: 
    eovsa_pltQlookMovie --- pipeline for plotting EOVSA daily full-disk image movie at multi frequencies.

    Synopsis:
    eovsa_pltQlookMovie.py [options]... [DATE_IN_YY_MM_DD]

    Description:
    Make EOVSA daily full-disk image movie at multi frequencies of the date specified
    by DATE_IN_YY_MM_DD (or from ndays before the DATE_IN_YY_MM_DD if option --ndays/-n is provided).
    If DATE_IN_YY_MM_DD is omitted, it will be set to 2 days before now by default. 
    The are no mandatory arguments in this command.


    -n, --ndays
            Processing the date spanning from DATE_IN_YY_MM_DD-ndays to DATE_IN_YY_MM_DD. Default is 30                                


    Example: 
    eovsa_pltQlookMovie.py -n 20 2020 06 10
    '''

    import sys
    import numpy as np
    import getopt

    year = None
    month = None
    day = None
    ndays = 30
    show_warning = False
    try:
        argv = sys.argv[1:]
        opts, args = getopt.getopt(argv, "n:w:",
                                   ['ndays=', 'show_warning='])
        print(opts, args)
        for opt, arg in opts:
            if opt in ('-n', '--ndays'):
                ndays = np.int(arg)
            elif opt in ('-w', '--show_warning'):
                if arg in ['True', 'T', '1']:
                    show_warning = True
                elif arg in ['False', 'F', '0']:
                    show_warning = False
                else:
                    show_warning = np.bool(arg)
        nargs = len(args)
        if nargs == 3:
            year = np.int(args[0])
            month = np.int(args[1])
            day = np.int(args[2])
        else:
            year = None
            month = None
            day = None
    except getopt.GetoptError as err:
        print(err)
        print('Error interpreting command line argument')
        year = None
        month = None
        day = None
        ndays = 30
        show_warning = False

    print("Running pipeline_plt for date {}-{}-{}.".format(year, month, day))
    kargs = {'ndays': ndays}
    for k, v in kargs.items():
        print(k, v)

    main(year=year, month=month, day=day, ndays=ndays, show_warning=show_warning)
