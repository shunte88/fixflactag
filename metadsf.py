import io
import subprocess
from pathlib import Path

# class wrapper for metadsf CLI utility.


class MetaDsf:

    def __init__(self, filename):
        self.__block_id3_tags = None

        dsf = Path(filename)

        if dsf.exists():
            self.filename = filename
        else:
            raise FileExistsError('invalid, file does not exist')

    def get_id3_tags(self):

        cmd = ['metadsf -t -eUTF8 "{}"'.format(self.filename)]
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                shell=True)

        (out, err) = proc.communicate()
        id3_tags = dict()
        if not err:
            for user_comment in out.splitlines():
                try:
                    # retain copyright symbol etc
                    user_comment = str(user_comment, 'windows-1252')
                    if '=' in user_comment:
                        key, value = user_comment.split('=', 1)
                        # fix the encoding????
                        key = key.upper().replace("B'", '', 1)
                        if value:
                            id3_tags[key] = value
                except:
                    pass

        return id3_tags