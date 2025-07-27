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
                                % if album.poster:
                                    <img src="${album.poster}" class="img-responsive" alt="${album.name}">
                                % else:
                                    <div class="no-poster">
                                        <i class="fa fa-music fa-5x"></i>
                                        <p>${_('No Cover')}</p>
                                    </div>
                                % endif
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
                                        % if album.status == 1:
                                            <span class="label label-success">${_('Downloaded')}</span>
                                        % elif album.status == 2:
                                            <span class="label label-info">${_('Snatched')}</span>
                                        % else:
                                            <span class="label label-default">${_('Wanted')}</span>
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
                    <h3 class="panel-title">${_('Search Results')}</h3>
                </div>
                <div class="panel-body">
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>${_('Name')}</th>
                                    <th>${_('Provider')}</th>
                                    <th>${_('Size')}</th>
                                    <th>${_('Seeders')}</th>
                                    <th>${_('Leechers')}</th>
                                    <th>${_('Actions')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                % if album.results:
                                    % for result in album.results:
                                        <tr>
                                            <td>${result.name}</td>
                                            <td>${result.provider}</td>
                                            <td>${pretty_file_size(result.size) if result.size else _('Unknown')}</td>
                                            <td>${result.seeders}</td>
                                            <td>${result.leechers}</td>
                                            <td>
                                                <button class="btn btn-sm btn-success">
                                                    <i class="fa fa-download"></i> ${_('Download')}
                                                </button>
                                            </td>
                                        </tr>
                                    % endfor
                                % else:
                                    <tr>
                                        <td colspan="6">${_('No results found')}</td>
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