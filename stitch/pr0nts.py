#!/usr/bin/python
'''
pr0ntile: IC die image stitching and tile generation
Copyright 2012 John McMaster <JohnDMcMaster@gmail.com>
Licensed under a 2 clause BSD license, see COPYING for details
'''

'''
pr0nts: pr0ntools tile stitcher
This takes in a .pto project and outputs 
Described in detail here: 
http://uvicrec.blogspot.com/2012/02/tile-stitch.html
'''

from pr0ntools.stitch.tiler import Tiler
from pr0ntools.stitch.pto.project import PTOProject
from pr0ntools.config import config
from pr0ntools.stitch.single import singlify, HugeJPEG
from pr0ntools.util import logwt

import argparse
import glob
import multiprocessing
import os
import re
import sys
import time

def size2str(d):
    if d < 1000:
        return '%g' % d
    if d < 1000**2:
        return '%gk' % (d / 1000.0)
    if d < 1000**3:
        return '%gm' % (d / 1000.0**2)
    return '%gg' % (d / 1000.0**3)

def mksize(s):
    # To make feeding args easier
    if s is None:
        return None

    m = re.match(r"(\d*)([A-Za-z]*)", s)
    if not m:
        raise ValueError("Bad size string %s" % s)
    num = int(m.group(1))
    modifier = m.group(2)
    '''
    s: square
    k: 1000
    K: 1024
    m: 1000 * 1000
    M: 1024 * 1024
    ...
    '''    
    for mod in modifier:
        if mod == 'k':
            num *= 1000
        elif mod == 'K':
            num *= 1024
        elif mod == 'm':
            num *= 1000 * 1000
        elif mod == 'M':
            num *= 1024 * 1024
        elif mod == 'g':
            num *= 1000 * 1000 * 1000
        elif mod == 'G':
            num *= 1024 * 1024 * 1024
        elif mod == 's':
            num *= num
        else:
            raise ValueError('Bad modifier %s on number string %s', mod, s)
    return num

def mem2pix(mem):
    # Rough heuristic from some of my trials (1 GB => 51 MP)
    return mem * 51 / 1000
    # Maybe too aggressive, think ran out at 678 MP / 18240 MB => 37 MP?
    # Maybe its a different error
    # ahah: I think it was disk space and I had misinterpreted it as memory
    # since the files got deleted after the run it wasn't obvious
    #return mem * 35 / 1000

def parser_add_bool_arg(yes_arg, default=False, **kwargs):
    dashed = yes_arg.replace('--', '')
    dest = dashed.replace('-', '_')
    parser.add_argument(yes_arg, dest=dest, action='store_true', default=default, **kwargs)
    parser.add_argument('--no-' + dashed, dest=dest, action='store_false', **kwargs)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='create tiles from unstitched images')
    parser.add_argument('pto', default='out.pto', nargs='?', help='pto project')
    parser.add_argument('--stw', help='Supertile width')
    parser.add_argument('--sth', help='Supertile height')
    parser.add_argument('--stp', help='Supertile pixels')
    parser.add_argument('--stm', help='Supertile memory')
    parser.add_argument('--force', action="store_true", help='Force by replacing old files')
    parser.add_argument('--merge', action="store_true", help="Don't delete anything and only generate things missing")
    parser.add_argument('--out-ext', default='.jpg', help='Select output image extension (and type), .jpg, .png, .tif, etc')
    parser.add_argument('--full', action="store_true", help='use only 1 supertile')
    parser.add_argument('--st-xstep', action="store", dest="super_t_xstep", type=int, help='Supertile x step (advanced)')
    parser.add_argument('--st-ystep', action="store", dest="super_t_ystep", type=int, help='Supertile y step (advanced)')
    parser.add_argument('--clip-width', action="store", dest="clip_width", type=int, help='x clip (advanced)')
    parser.add_argument('--clip-height', action="store", dest="clip_height", type=int, help='y clip (advanced)')
    parser.add_argument('--ignore-crop', action="store_true", help='Continue even if not cropped')
    parser.add_argument('--nona-args')
    parser.add_argument('--enblend-args')
    parser.add_argument('--ignore-errors', action="store_true", dest="ignore_errors", help='skip broken tile stitches (advanced)')
    parser.add_argument('--verbose', '-v', action="store_true", help='spew lots of info')
    parser.add_argument('--st-dir', default='st', help='store intermediate supertiles to given dir')
    parser.add_argument('--st-limit', default='inf', help='debug (exit after # supertiles, typically --st-limit 1 --threads 1)')
    parser.add_argument('--single-dir', default='single', help='folder to put final output composite image')
    parser.add_argument('--single-fn', default=None, help='file name to write in single dir')
    parser_add_bool_arg('--enblend-lock', default=False, help='use lock file to only enblend (memory intensive part) one at a time')
    parser.add_argument('--threads', type=int, default= multiprocessing.cpu_count())
    parser.add_argument('--log', default='pr0nts', help='Output log file name')
    args = parser.parse_args()

    if args.threads < 1:
        raise Exception('Bad threads')
    print 'Using %d threads' % args.threads
    
    log_dir = args.log
    out_dir = 'out'
    _dt = logwt(log_dir, 'main.log', shift_d=True)

    fn = args.pto[0]
    
    auto_size = not (args.stp or args.stm or args.stw or args.sth)
    
    print 'Assuming input %s is pto project to be stitched' % args.pto
    project = PTOProject.from_file_name(args.pto)
    print 'Creating tiler'
    stp = None
    if args.stp:
        stp = mksize(args.stp)
    elif args.stm:
        stp = mem2pix(mksize(args.stm))
        print 'Memory %s => %s pix' % (args.stm, size2str(stp))
    elif auto_size:
        stm = config.super_tile_memory()
        if stm:
            stp = mem2pix(mksize(stm))
            # having issues creating very large 
            if stp > 2**32/4:
                # 66 GB max useful as currently written
                print 'WARNING: reducing to maximum tile size'
                stp = 2**32/4

    
    t = Tiler(project, out_dir, stw=mksize(args.stw), sth=mksize(args.sth), stp=stp, clip_width=args.clip_width, clip_height=args.clip_height, log_dir=log_dir)
    t.threads = args.threads
    t.verbose = args.verbose
    t.st_dir = args.st_dir
    t.force = args.force
    t.merge = args.merge
    t.out_extension = args.out_ext
    t.ignore_errors = args.ignore_errors
    t.ignore_crop = args.ignore_crop
    t.st_limit = float(args.st_limit)

    # TODO: make this more proper?
    if args.nona_args:
        t.nona_args = args.nona_args.replace('"', '').split(' ')
    if args.enblend_args:
        t.enblend_args = args.enblend_args.replace('"', '').split(' ')
    
    if args.super_t_xstep:
        t.super_t_xstep = args.super_t_xstep
    if args.super_t_ystep:
        t.super_t_ystep = args.super_t_ystep
    if args.clip_width:
        t.clip_width = args.clip_width
    if args.clip_height:
        t.clip_height = args.clip_height
    # if they specified clip but not supertile step recalculate the step so they don't have to do it
    if args.clip_width or args.clip_height and not (args.super_t_xstep or args.super_t_ystep):
        t.recalc_step()

    if args.full:
        t.make_full()
    t.enblend_lock = args.enblend_lock

    if args.single_dir and not os.path.exists(args.single_dir):
        os.mkdir(args.single_dir)
        
    print 'Running tiler'
    try:
        t.run()
    except KeyboardInterrupt:
        if t.stale_worker:
            print 'WARNING: forcing exit on stuck worker'
            time.sleep(0.5)
            os._exit(1)
    print 'Tiler done!'

    print 'Creating single image'
    single_fn = args.single_fn
    if single_fn is None:
        single_fn = 'out.jpg'
    if args.single_dir:
        single_fn = os.path.join(args.single_dir, single_fn)
    # sometimes I restitch with different supertile size
    # this results in excessive merge, although really I should just delete the old files
    if args.merge:
        print 'Single: using glob strategy on merge'
        s_fns = glob.glob(os.path.join(args.st_dir, 'st_*x_*y.jpg'))
    else:
        print 'Single: using output strategy'
        s_fns = t.st_fns

    single_fn_alt = None
    if args.single_fn is None:
        single_fn_alt = single_fn.replace('.jpg', '.tif')

    try:
        singlify(s_fns, single_fn, single_fn_alt)
    except HugeJPEG:
        print 'WARNING: single: exceeds max image size'

