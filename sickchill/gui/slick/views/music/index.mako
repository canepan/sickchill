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
</%block>