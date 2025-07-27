<%inherit file="../layouts/main.mako"/>
<%!
    import datetime
    import os
    import re
    from sickchill import settings
    from sickchill.helper.common import pretty_file_size
    from sickchill.oldbeard import helpers
%>
<%block name="content">
    <div class="row">
        <div class="col-md-12">
            <div class="pull-right">
                <a href="${reverse_url('music-index', 'index')}" class="btn btn-default">
                    <i class="fa fa-arrow-left"></i> ${_('Back to Artist List')}
                </a>
                <a href="${reverse_url('music-remove', 'remove', artist.pk)}" class="btn btn-danger">
                    <i class="fa fa-trash"></i> ${_('Remove Artist')}
                </a>
            </div>
            <h1 class="header">${artist.name}</h1>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">${_('Artist Information')}</h3>
                </div>
                <div class="panel-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="artist-poster">
                                % if artist.poster:
                                    <img src="${artist.poster}" class="img-responsive" alt="${artist.name}">
                                % else:
                                    <div class="no-poster">
                                        <i class="fa fa-user fa-5x"></i>
                                        <p>${_('No Poster')}</p>
                                    </div>
                                % endif
                            </div>
                        </div>
                        <div class="col-md-9">
                            <table class="table">
                                <tr>
                                    <th>${_('Name')}</th>
                                    <td>${artist.name}</td>
                                </tr>
                                <tr>
                                    <th>${_('Sort Name')}</th>
                                    <td>${artist.sort_name}</td>
                                </tr>
                                <tr>
                                    <th>${_('Country')}</th>
                                    <td>${artist.country or _('Unknown')}</td>
                                </tr>
                                <tr>
                                    <th>${_('MusicBrainz ID')}</th>
                                    <td>${artist.musicbrainz_id}</td>
                                </tr>
                                <tr>
                                    <th>${_('Genres')}</th>
                                    <td>
                                        % if artist.musicbrainz_genres:
                                            ${', '.join([genre.pk for genre in artist.musicbrainz_genres])}
                                        % else:
                                            ${_('No genres')}
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
                    <h3 class="panel-title">${_('Albums')}</h3>
                </div>
                <div class="panel-body">
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>${_('Album')}</th>
                                    <th>${_('Year')}</th>
                                    <th>${_('Type')}</th>
                                    <th>${_('Tracks')}</th>
                                    <th>${_('Actions')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                % if artist.albums:
                                    % for album in artist.albums:
                                        <tr>
                                            <td>
                                                <a href="${reverse_url('music-album_details', 'album_details', album.slug)}">
                                                    ${album.name}
                                                </a>
                                            </td>
                                            <td>${album.year or _('Unknown')}</td>
                                            <td>${album.type}</td>
                                            <td>${album.tracks}</td>
                                            <td>
                                                <a href="${reverse_url('music-album_details', 'album_details', album.slug)}" class="btn btn-sm btn-primary">
                                                    <i class="fa fa-info-circle"></i> ${_('Details')}
                                                </a>
                                            </td>
                                        </tr>
                                    % endfor
                                % else:
                                    <tr>
                                        <td colspan="5">${_('No albums found')}</td>
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