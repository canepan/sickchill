<%inherit file="../layouts/main.mako"/>
<%!
    import datetime
    import os
    import re
    from sickchill import settings
    from sickchill.helper.common import pretty_file_size
    from sickchill.oldbeard import helpers
    from sickchill.oldbeard.databases.music import AlbumStatus
%>
<%block name="metas">
    <meta data-var="showBackgroundImage" data-content="${static_url(album.image_url('poster'))}">
</%block>
<%block name="content">
    <div class="row">
        <div class="col-md-12">
            <div class="pull-right">
                <a href="${reverse_url('music-details', 'details', album.artist.slug)}" class="btn btn-default">
                    <i class="fa fa-arrow-left"></i> ${_('Back to Artist')}
                </a>
            </div>
            <h1 class="header">${album.name}</h1>
            <h4>${album.artist.name}</h4>
        </div>
    </div>

    <div class="row">
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">${_('Album Information')}</h3>
                </div>
                <div class="panel-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="album-cover">
                                <img src="${static_url(album.image_url('poster'))}" class="img-responsive" alt="${album.name}">
                            </div>
                        </div>
                        <div class="col-md-9">
                            <table class="table">
                                <tr>
                                    <th>${_('Title')}</th>
                                    <td>${album.name}</td>
                                </tr>
                                <tr>
                                    <th>${_('Artist')}</th>
                                    <td>
                                        <a href="${reverse_url('music-details', 'details', album.artist.slug)}">
                                            ${album.artist.name}
                                        </a>
                                    </td>
                                </tr>
                                <tr>
                                    <th>${_('Year')}</th>
                                    <td>${album.year or _('Unknown')}</td>
                                </tr>
                                <tr>
                                    <th>${_('Type')}</th>
                                    <td>${album.type}</td>
                                </tr>
                                <tr>
                                    <th>${_('Tracks')}</th>
                                    <td>${album.tracks}</td>
                                </tr>
                                <tr>
                                    <th>${_('MusicBrainz ID')}</th>
                                    <td>${album.musicbrainz_id}</td>
                                </tr>
                                <tr>
                                    <th>${_('Status')}</th>
                                    <td>
                                        % if album.status == AlbumStatus.WANTED:
                                            <span class="label label-info">${_('Wanted')}</span>
                                        % elif album.status == AlbumStatus.SNATCHED:
                                            <span class="label label-primary">${_('Snatched')}</span>
                                        % elif album.status == AlbumStatus.DOWNLOADED:
                                            <span class="label label-success">${_('Downloaded')}</span>
                                        % elif album.status == AlbumStatus.SKIPPED:
                                            <span class="label label-default">${_('Skipped')}</span>
                                        % elif album.status == AlbumStatus.IGNORED:
                                            <span class="label label-warning">${_('Ignored')}</span>
                                        % else:
                                            <span class="label label-default">${_('Unknown')}</span>
                                        % endif
                                    </td>
                                </tr>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">${_('Track List')}</h3>
                </div>
                <div class="panel-body">
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>${_('#')}</th>
                                    <th>${_('Title')}</th>
                                    <th>${_('Duration')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                % if album.musicbrainz_data and 'tracks' in album.musicbrainz_data:
                                    % for track in album.musicbrainz_data['tracks']:
                                        <tr>
                                            <td>${track.get('position', '')}</td>
                                            <td>${track.get('title', '')}</td>
                                            <td>${track.get('duration', '')}</td>
                                        </tr>
                                    % endfor
                                % else:
                                    <tr>
                                        <td colspan="3">${_('No track information available')}</td>
                                    </tr>
                                % endif
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>

</%block>

<%block name="scripts">
    <script type="text/javascript" src="${static_url('js/music.js')}"></script>
</%block>
