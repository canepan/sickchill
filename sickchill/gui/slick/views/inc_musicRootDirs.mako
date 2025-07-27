<%
    from sickchill import settings

    if settings.MUSIC_ROOT_DIRS:
        backend_pieces = settings.MUSIC_ROOT_DIRS.split('|')
        backend_default = 'rd-' + backend_pieces[0]
        backend_dirs = backend_pieces[1:]
    else:
        backend_default = ''
        backend_dirs = []
%>

<div class="row">
    <div class="col-md-12">
        <span id="sampleMusicRootDir"></span>

        <input type="hidden" id="whichDefaultMusicRootDir" value="${backend_default}" />
        <div class="rootdir-selectbox">
            <select name="musicRootDir" id="musicRootDirs" size="6" title="Music root directory">
                % for cur_dir in backend_dirs:
                    <option value="${cur_dir}">${cur_dir}</option>
                % endfor
            </select>
        </div>
    </div>
</div>
<div class="row">
    <div class="col-md-12">
        <div id="musicRootDirsControls" class="rootdir-controls">
            <input class="btn" type="button" id="addMusicRootDir" value="${_('New')}" />
            <input class="btn" type="button" id="editMusicRootDir" value="${_('Edit')}" />
            <input class="btn" type="button" id="deleteMusicRootDir" value="${_('Delete')}" />
            <input class="btn" type="button" id="defaultMusicRootDir" value="${_('Set as default')} *" />
        </div>
        <input type="text" style="display: none" id="musicRootDirText" autocapitalize="off" />
    </div>
</div>