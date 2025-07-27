<%inherit file="../layouts/main.mako"/>
<%!
    import datetime
    import os
    import re
    from sickchill import settings
    from sickchill.helper.common import pretty_file_size
    from sickchill.oldbeard import helpers
    
    def selected(condition):
        return 'selected="selected"' if condition else ''
%>
<%block name="content">
    <div class="row">
        <div class="col-md-12">
            % if not settings.USE_MUSICBRAINZ:
                <div class="alert alert-info">
                    <p>${_('Music support is currently disabled. To enable it, go to Settings -> General and enable MusicBrainz.')}</p>
                </div>
            % else:
                <div class="row">
                    <div class="col-md-12">
                        <div class="pull-right">
                            <a href="${reverse_url('music-search', 'search')}" class="btn btn-primary">
                                <i class="fa fa-search"></i> ${_('Search for Artist')}
                            </a>
                        </div>
                        <h1 class="header">${header}</h1>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-12">
                        <div class="text-center">
                            % if settings.MUSIC_ROOT_DIRS:
                                <span class="show-option">${_('Root')}:</span>
                                <label>
                                    <form method="post" action="" id="rootDirForm">
                                        <select id="rootDirSelect" name="root" class="form-control form-control-inline input200" title="Root Select">
                                        <option value="-1" ${selected(selected_root == '-1')}>${_('All')}</option>
                                        % for root_dir in settings.MUSIC_ROOT_DIRS.split('|')[1:]:
                                            <option value="${loop.index}" ${selected(selected_root == str(loop.index))}>${root_dir}</option>
                                        % endfor
                                        </select>
                                    </form>
                                </label>
                            % endif
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-12">
                        <div class="table-responsive">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>${_('Artist')}</th>
                                        <th>${_('Country')}</th>
                                        <th>${_('Albums')}</th>
                                        <th>${_('Actions')}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    % if music and list(music):
                                        % for artist in music:
                                            <tr>
                                                <td>
                                                    <a href="${reverse_url('music-details', 'details', artist.slug)}">
                                                        ${artist.name}
                                                    </a>
                                                </td>
                                                <td>${artist.country or 'Unknown'}</td>
                                                <td>${len(artist.albums)}</td>
                                                <td>
                                                    <a href="${reverse_url('music-details', 'details', artist.slug)}" class="btn btn-sm btn-primary">
                                                        <i class="fa fa-info-circle"></i> ${_('Details')}
                                                    </a>
                                                    <a href="${reverse_url('music-remove', 'remove', artist.pk)}" class="btn btn-sm btn-danger">
                                                        <i class="fa fa-trash"></i> ${_('Remove')}
                                                    </a>
                                                </td>
                                            </tr>
                                        % endfor
                                    % else:
                                        <tr>
                                            <td colspan="4">${_('No artists found')}</td>
                                        </tr>
                                    % endif
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            % endif
        </div>
    </div>

    <script type="text/javascript">
        document.addEventListener('DOMContentLoaded', function() {
            var rootDirSelect = document.getElementById('rootDirSelect');
            if (rootDirSelect) {
                rootDirSelect.addEventListener('change', function() {
                    document.getElementById('rootDirForm').submit();
                });
            }
        });
    </script>
</%block>