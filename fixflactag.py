#!/usr/bin/python3

import os
import sys
import argparse
import logging
import subprocess
import glob
from pathlib import Path
from metaflac import MetaFlac
from metadsf import MetaDsf
import contextlib


@contextlib.contextmanager
def ignored(*exceptions):
    try:
        yield
    except exceptions:
        pass


def run_command(cmd, exc=0):

    logging.debug(cmd)
    if 1 == exc:
        try:
            rc = subprocess.run(cmd, shell=True)
            if 0 == rc.returncode:
                return True
        except subprocess.CalledProcessError as err:
            logger.warning(err.output)
            return False
    return False


def fix_dsf_tags(filename,
                 isvarious=0,
                 replay_gain='+5.500000 dB',
                 discnumber=-1,
                 disctotal=-1,
                 tracktotal=-1):

    changed = False
    remove_tags = []
    add_tags = None

    metadsf = MetaDsf(filename)
    dsf_tags = metadsf.get_id3_tags()

    if 'TENC' in dsf_tags and 'VinylStudio' == dsf_tags['TENC']:
        dsf_tags.pop('TENC', None)
        remove_tags.append('TENC')
        logging.debug('Delete TENC Tag')
        changed = True

    if 'TIT1' in dsf_tags and \
       'COMM' in dsf_tags and \
       dsf_tags['TIT1'] == dsf_tags['COMM']:
        dsf_tags.pop('TIT1', None)
        remove_tags.append('TIT1')
        logging.debug('Delete TIT1 Tag')
        changed = True

    if 'TORY' not in dsf_tags and \
       'TDRC' in dsf_tags:
        dsf_tags['TORY'] = dsf_tags['TDRC']
        add_tags = '--add-tag=TORY={}'.format(dsf_tags['TDRC'])
        logging.debug('Add TORY Tag')
        changed = True

    if changed:
        logging.debug('Rewrite DSF tags on "{}"'.format(filename))
        # metadsf command line - heavily buttoned down
        cmd = 'metadsf --encoding=UTF8'
        if 0 != len(remove_tags):
            cmd += ' --remove-tags={}'.format(','.join(remove_tags))
        if add_tags:
            cmd += ' {}'.format(add_tags)
        cmd += ' "{}"'.format(filename)
        run_command(cmd, 1)


def fix_flac_tags(filename,
                  isvarious=0,
                  replay_gain='+5.500000 dB',
                  discnumber=0,
                  disctotal=0,
                  tracktotal=0):

    changed = False

    metaflac = MetaFlac(filename)
    flac_comment, changed = metaflac.get_vorbis_comment()

    tags_file = '%d.tag' % (os.getpid())
    tf = Path(tags_file)

    if tf.exists():
        tf.unlink()

    if 0 == isvarious:
        with ignored(KeyError, IndexError):
            isvarious = int('Y' == flac_comment['COMPILATION'][0])

    # add the replaygain bump for vinyl rips
    if 'CONTACT' in flac_comment and \
       'VinylStudio' == flac_comment['CONTACT'][0]:
        if 'REPLAYGAIN_TRACK_GAIN' not in flac_comment:
            flac_comment['REPLAYGAIN_TRACK_GAIN'].append(replay_gain)
            logging.debug('Adding REPLAYGAIN_TRACK_GAIN Tag')
            changed = True

    # dump redundant tags
    for redundant in ('CONTACT', 'LOCATION', 'GROUPING'):
        if redundant in flac_comment:
            flac_comment.pop(redundant, None)
            logging.debug('Delete {} Tag'.format(redundant))
            changed = True

    # patch for missing album artist
    # isvarious we should really delete the album artist tag if exists
    if 0 == isvarious and \
       'ALBUMARTIST' not in flac_comment and \
       'ALBUM ARTIST' not in flac_comment:
        for artist in flac_comment['ARTIST']:
            flac_comment['ALBUMARTIST'].append(artist)
            logging.debug('Adding ALBUMARTIST Tag')
            changed = True

    # patch for missing year
    if 'YEAR' not in flac_comment:
        if 'DATE' in flac_comment:
            for year in flac_comment['DATE']:
                flac_comment['YEAR'].append(year)
                logging.debug('Adding YEAR Tag')
                changed = True

    # fix disktotal, disknumber tag typo

    for test_tag in ('DISKNUMBER', 'DISKTOTAL'):
        if test_tag in flac_comment:
            new_tag = test_tag.replace('K', 'C')
            if new_tag not in flac_comment:
                value = '01'
                with ignored(KeyError, ValueError):
                    value = str(int(flac_comment[test_tag][0])).zfill(2)
                flac_comment[new_tag].append(value)
                logging.debug('Adding {} Tag'.format(new_tag))
            logging.debug('Cleanup {} Tag'.format(test_tag))
            flac_comment.pop(test_tag, None)
            changed = True

    if (discnumber+disctotal+tracktotal) > 0:
        for test_tag in ('DISCNUMBER', 'DISCTOTAL', 'TRACKTOTAL'):
            if test_tag not in flac_comment:
                if 'DISCNUMBER' == test_tag:
                    value = discnumber
                elif 'DISCTOTAL' == test_tag:
                    value = disctotal
                else:
                    value = tracktotal
                if value > 0:
                    flac_comment[test_tag].append(str(value).zfill(2))
                    logging.debug('Adding {} Tag'.format(test_tag))
                    changed = True

    if changed:
        logging.debug('Rewrite FLAC tags on "{}"'.format(filename))
        text = ''
        for k, v in sorted(flac_comment.items()):
            for vv in v:
                text += "{}={}\n".format(k, vv)
        tf.write_text(text)

        if tf.exists():
            # metaflac command line
            cmd = 'metaflac --preserve-modtime --no-utf8-convert'
            cmd += ' --remove-all-tags'
            cmd += ' --import-tags-from={} "{}"'.format(tags_file, filename)
            run_command(cmd, 1)
            # cleanup
            tf.unlink()


def main(args):

    logging.info('Processing FLAC')
    pathlist = Path(args.folder).glob('*/*.flac')
    for path in sorted(pathlist):
        fix_flac_tags(str(path),
                      isvarious=args.various,
                      discnumber=args.discnumber,
                      disctotal=args.disctotal,
                      tracktotal=args.tracktotal)

    logging.info('Processing DSF')
    pathlist = Path(args.folder).glob('*/*.dsf')
    for path in sorted(pathlist):
        fix_dsf_tags(str(path),
                     isvarious=args.various,
                     discnumber=args.discnumber,
                     disctotal=args.disctotal,
                     tracktotal=args.tracktotal)


log_file = '/tmp/flactag.log'
parser = argparse.ArgumentParser()

parser.add_argument('--folder', '-f',
                    help='Folder to process',
                    type=str)
parser.add_argument('--various', '-v',
                    help='Is Various Artists',
                    type=int,
                    default=0)
parser.add_argument('--backup', '-b',
                    help='Backup original files',
                    type=int,
                    default=0)
parser.add_argument('--discnumber', '-n',
                    help='Disc Number',
                    type=int,
                    default=1)
parser.add_argument('--disctotal', '-d',
                    help='Disc Total',
                    type=int,
                    default=1)
parser.add_argument('--tracktotal', '-t',
                    help='Track Total',
                    type=int,
                    default=0)

args = parser.parse_args()

if __name__ == "__main__":

    log_format = '%(asctime)s %(levelname)-8s %(message)s'
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(log_format)
    console.setFormatter(formatter)
    logging.basicConfig(level=logging.DEBUG,
                        format=log_format,
                        datefmt='%m-%d-%y %H:%M',
                        filename=log_file,
                        filemode='a')

    logging.getLogger('').addHandler(console)

    main(args)

sys.exit(0)
