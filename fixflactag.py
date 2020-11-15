#/usr/bin/python3

import os
import sys
import argparse
import logging
import subprocess
import glob
import datetime
from pathlib import Path
from metaflac import MetaFlac
from metadsf import MetaDsf
import re
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
                 replay_gain='+8.500000 dB',
                 discnumber=-1,
                 disctotal=-1,
                 tracktotal=-1,
                 swaptags=0):

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
        add_tags = f"--add-tag=TORY={dsf_tags['TDRC']}"
        logging.debug('Add TORY Tag')
        changed = True

    if changed:
        logging.debug(f'Rewrite DSF tags on "{filename}"')
        # metadsf command line - heavily buttoned down
        cmd = 'metadsf --encoding=UTF8'
        if 0 != len(remove_tags):
            cmd += ' --remove-tags={}'.format(','.join(remove_tags))
        if add_tags:
            cmd += f' {add_tags}'
        cmd += f' "{filename}"'
        run_command(cmd, 1)


def fix_flac_tags(filename,
                  isvarious=0,
                  replay_gain='+8.500000 dB',
                  discnumber=0,
                  disctotal=0,
                  tracktotal=0,
                  swaptags=0):

    changed = False
    vinyl_rip = '24bVR'
    today = datetime.date.today()

    metaflac = MetaFlac(filename)
    flac_comment, changed, ID3_tags = metaflac.get_vorbis_comment()

    if ID3_tags:
        changed = True

    tags_file = '%d.tag' % (os.getpid())
    tf = Path(tags_file)

    if tf.exists():
        tf.unlink()

    if 0 == isvarious:
        with ignored(KeyError, IndexError):
            isvarious = int('Y' == flac_comment['COMPILATION'][0])
            if 0 == isvarious:
                with ignored(KeyError, IndexError):
                    isvarious = int(0 != flac_comment['ALBUMARTIST'][0].lower().find("various"))
                    if 0 == isvarious:
                        with ignored(KeyError, IndexError):
                            isvarious = int(0 != flac_comment['ALBUM ARTIST'][0].lower().find("various"))

    # add the replaygain bump for vinyl rips
    if 'CONTACT' in flac_comment and \
       'VinylStudio' == flac_comment['CONTACT'][0]:
        if 'REPLAYGAIN_TRACK_GAIN' not in flac_comment:
            flac_comment['REPLAYGAIN_TRACK_GAIN'].append(replay_gain)
            logging.debug('Adding REPLAYGAIN_TRACK_GAIN Tag')
            changed = True

    with ignored(KeyError, IndexError):
        if 'ffz' in flac_comment['COMMENTS'][0] or 'FFZ' in flac_comment['COMMENTS'][0]:
            logging.debug('Default COMMENT Tag')
            flac_comment.pop('COMMENTS', None)
            changed = True
    with ignored(KeyError, IndexError):
        if 'fzz' in flac_comment['COMMENTS'][0] or 'FZZ' in flac_comment['COMMENTS'][0]:
            logging.debug('Default COMMENT Tag')
            flac_comment.pop('COMMENTS', None)
            changed = True

    with ignored(KeyError, IndexError):
        if 'ffz' in flac_comment['COMMENT'][0] or 'FFZ' in flac_comment['COMMENT'][0]:
            logging.debug('Default COMMENT Tag')
            flac_comment.pop('COMMENT', None)
            changed = True
    with ignored(KeyError, IndexError):
        if 'fzz' in flac_comment['COMMENT'][0] or 'FZZ' in flac_comment['COMMENT'][0]:
            logging.debug('Default COMMENT Tag')
            flac_comment.pop('COMMENT', None)
            changed = True

    with ignored(KeyError, IndexError):
        if 'inyl' in flac_comment['COMMENTS'][0] or \
        'Digitally' in flac_comment['COMMENTS'][0] or \
        'inyl' in flac_comment['COMMENT'][0] or \
        'Digitally' in flac_comment['COMMENT'][0]:
            if 'REPLAYGAIN_TRACK_GAIN' not in flac_comment:
                flac_comment['REPLAYGAIN_TRACK_GAIN'].append(replay_gain)
                logging.debug('Add REPLAYGAIN_TRACK_GAIN Tag')
                changed = True
            flac_comment.pop('COMMENTS', None)
            changed = True

    with ignored(KeyError, IndexError):
        if 'ffz' in flac_comment['COMMENTS'][0] or 'FFZ' in flac_comment['COMMENTS'][0]:
            logging.debug('Default COMMENT Tag')
            flac_comment.pop('COMMENTS', None)
            changed = True
        if 'fzz' in flac_comment['COMMENT'][0] or 'FZZ' in flac_comment['COMMENT'][0]:
            logging.debug('Default COMMENT Tag')
            flac_comment.pop('COMMENT', None)
            changed = True
        if 'NAD' in flac_comment['COMMENTS'][0]:
            if 'REPLAYGAIN_TRACK_GAIN' not in flac_comment:
                flac_comment['REPLAYGAIN_TRACK_GAIN'].append(replay_gain)
                logging.debug('Add REPLAYGAIN_TRACK_GAIN Tag')
                flac_comment.pop('COMMENTS', None)
                changed = True
        if 'NAD' in flac_comment['COMMENT'][0]:
            if 'REPLAYGAIN_TRACK_GAIN' not in flac_comment:
                flac_comment['REPLAYGAIN_TRACK_GAIN'].append(replay_gain)
                logging.debug('Add REPLAYGAIN_TRACK_GAIN Tag')
                changed = True
        if vinyl_rip in flac_comment['ALBUM'][0]:
            if 'REPLAYGAIN_TRACK_GAIN' not in flac_comment:
                flac_comment['REPLAYGAIN_TRACK_GAIN'].append(replay_gain)
                logging.debug('Add REPLAYGAIN_TRACK_GAIN Tag')
                changed = True
        if 'inyl' in flac_comment['COMMENT'][0] or 'Digitally' in flac_comment['COMMENT'][0]:
            if 'REPLAYGAIN_TRACK_GAIN' not in flac_comment:
                flac_comment['REPLAYGAIN_TRACK_GAIN'].append(replay_gain)
                logging.debug('Add REPLAYGAIN_TRACK_GAIN Tag')
                changed = True
            flac_comment.pop('COMMENT', None)
            changed = True
        if 'inyl' in flac_comment['COMMENTS'][0] or 'Digitally' in flac_comment['COMMENTS'][0]:
            if 'REPLAYGAIN_TRACK_GAIN' not in flac_comment:
                flac_comment['REPLAYGAIN_TRACK_GAIN'].append(replay_gain)
                logging.debug('Add REPLAYGAIN_TRACK_GAIN Tag')
                changed = True
            flac_comment.pop('COMMENTS', None)
            changed = True

    if 'CATALOGNUMBER' not in flac_comment:
        if '[' in flac_comment['ALBUM'][0]:
            regex = r'\[([^\[]*)\][^\[]*$'
            unpack = re.split(regex,
                              flac_comment['ALBUM'][0],
                              maxsplit=1)
            if unpack:
                flac_comment['CATALOGNUMBER'].append(unpack[1].strip())
                logging.debug('Adding CATALOGNUMBER Tag')
                changed = True

    # dump redundant tags
    red_tags = ('CONTACT', 'LOCATION', 'GROUPING')
    if 1 == isvarious:
        red_tags += ('ALBUMARTIST', 'ALBUM ARTIST')
        if 'COMPILATION' not in flac_comment:
            flac_comment['COMPILATION'].append('Y')

    for redundant in red_tags:
        if redundant in flac_comment:
            flac_comment.pop(redundant, None)
            logging.debug(f'Delete {redundant} Tag')
            changed = True

    if swaptags:
        print(f">> {flac_comment['ARTIST'][0]}:: {flac_comment['TITLE'][0]}")
        flac_comment['ARTIST'][0], flac_comment['TITLE'][0] = \
            flac_comment['TITLE'][0], flac_comment['ARTIST'][0]
        print(f"<< {flac_comment['ARTIST'][0]}:: {flac_comment['TITLE'][0]}")
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

    if 'DATE' in flac_comment:
        if len(flac_comment['DATE']) > 1:
            flac_comment['DATE'] = flac_comment['DATE'][:1]
            logging.debug('Cleanup DATE Tag')
            changed = True

    # add signature if not present
    if 'COMMENT' not in flac_comment:
        flac_comment['COMMENT'].append(f'FixFlac {today}')
        logging.debug('Adding COMMENT Tag')
        changed = True
    else:
        # address multi-line comments
        if "\n" in flac_comment['COMMENT']:
            logging.debug('Fix multi-line COMMENT Tag')
            flac_comment.pop('COMMENT', None)
            changed = True

    if 'COMMENT' not in flac_comment:
        flac_comment['COMMENT'].append(f'FixFlac {today}')
        logging.debug('Adding COMMENT Tag')
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
                logging.debug(f'Adding {new_tag} Tag')
            logging.debug(f'Cleanup {test_tag} Tag')
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
                    logging.debug(f'Adding {test_tag} Tag')
                    changed = True

    if changed:
        logging.debug(f'Rewrite FLAC tags on "{filename}"')
        text = ''
        for k, v in sorted(flac_comment.items()):
            for vv in v:
                if "\n" in vv:
                    vv = vv.replace('\r\n', ' ')
                    vv = vv.replace('\n', ' ')
                    vv = vv.replace('\r', ' ')
                text += f"{k}={vv}\n"
        tf.write_text(text)

        if tf.exists():

            if ID3_tags:
                cmd = f'id3v2 --delete-all "{filename}"'
                run_command(cmd, 1)

            # metaflac command line
            cmd = 'metaflac --preserve-modtime --no-utf8-convert'
            cmd += ' --remove-all-tags'
            if '"' in filename:
                cmd += f" --import-tags-from={tags_file} '{filename}'"
            else:
                cmd += f' --import-tags-from={tags_file} "{filename}"'
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
                      tracktotal=args.tracktotal,
                      swaptags=args.swap)

    logging.info('Processing DSF')
    pathlist = Path(args.folder).glob('*/*.dsf')
    for path in sorted(pathlist):
        fix_dsf_tags(str(path),
                     isvarious=args.various,
                     discnumber=args.discnumber,
                     disctotal=args.disctotal,
                     tracktotal=args.tracktotal,
                     swaptags=args.swap)


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
parser.add_argument('--swap', '-s',
                    help='Swap Artist and Title',
                    type=int,
                    default=0)
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
