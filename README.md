# fixflactag

Windows 10 introduced a bug on FLAC tagging in the October 2018 update

Ripping Vinyl and CD's on Windows 10 editing FLAC tags is now problematic

This simple utility fixes several problem tags

It expands on tags that are multi-value

It removes tags that are non-standard

And, finally it adds tags that are missing

Leverages a modified version of metaflac that supports multi-value tags


Almost pure python3 only requires the metaflac command line utility and should be cross-platform - the later is untested


Could likely do all of this with mutagen but as yet I've not found a simple recipe

