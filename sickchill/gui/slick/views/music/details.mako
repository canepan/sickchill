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
    <meta data-var="showBackgroundImage" data-content="${static_url(artist.image_url('poster'))}">
</%block>

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
                                <img src="${static_url(artist.image_url('poster'))}" class="img-responsive" alt="${artist.name}">
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
                                <tr>
                                    <th>${_('Location')}</th>
                                    <td>
                                        <form action="${reverse_url('music-set_artist_location', 'set_artist_location', artist.pk)}" method="post" class="form-inline">
                                            <div class="input-group">
                                                <input type="text" name="location" value="${artist.location or ''}" class="form-control" placeholder="${_('Artist location')}">
                                                <span class="input-group-btn">
                                                    <button class="btn btn-primary" type="submit">${_('Set Location')}</button>
                                                </span>
                                            </div>
                                        </form>
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
                    <!-- Album status filter -->
                    <div class="row">
                        <div class="col-lg-8 col-md-8 col-sm-12 col-xs-12 pull-right">
                            <div class="pull-right" id="checkboxControls">
                                <div style="padding-bottom: 5px;">
                                    <label class="pull-right" for="wanted"><span class="wanted"><input type="checkbox" id="wanted" checked="checked" /> ${_('Wanted')}</span></label>
                                    <label class="pull-right" for="snatched"><span class="snatched"><input type="checkbox" id="snatched" checked="checked" /> ${_('Snatched')}</span></label>
                                    <label class="pull-right" for="downloaded"><span class="good"><input type="checkbox" id="downloaded" checked="checked" /> ${_('Downloaded')}</span></label>
                                    <label class="pull-right" for="skipped"><span class="skipped"><input type="checkbox" id="skipped" checked="checked" /> ${_('Skipped')}</span></label>
                                    <label class="pull-right" for="ignored"><span class="ignored"><input type="checkbox" id="ignored" checked="checked" /> ${_('Ignored')}</span></label>
                                </div>
                                <div class="clearfix"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Album selector -->
                    <div class="row">
                        <div class="col-lg-12 col-md-12 col-sm-12 col-xs-12" style="padding-bottom: 5px; padding-top: 5px;">
                            ${_('Change selected albums to')}:<br>
                            <select id="statusSelect" class="form-control form-control-inline input-sm" title="Change Status">
                                <option value="${AlbumStatus.WANTED}">${_('Wanted')}</option>
                                <option value="${AlbumStatus.SKIPPED}">${_('Skipped')}</option>
                                <option value="${AlbumStatus.IGNORED}">${_('Ignored')}</option>
                            </select>
                            <input type="hidden" id="artistID" value="${artist.pk}" />
                            <input class="btn btn-inline" type="button" id="changeStatus" value="Go" />
                        </div>
                    </div>

                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th class="col-checkbox">
                                        <input type="checkbox" class="albumCheck" id="selectAll" />
                                    </th>
                                    <th>${_('Album')}</th>
                                    <th>${_('Year')}</th>
                                    <th>${_('Type')}</th>
                                    <th>${_('Tracks')}</th>
                                    <th>${_('Status')}</th>
                                    <th>${_('Actions')}</th>
                                </tr>
                            </thead>
                            <tbody>
                                % if artist.albums:
                                    % for album in artist.albums:
                                        <%
                                            status_class = ""
                                            if album.status == AlbumStatus.WANTED:
                                                status_class = "wanted"
                                            elif album.status == AlbumStatus.SNATCHED:
                                                status_class = "snatched"
                                            elif album.status == AlbumStatus.DOWNLOADED:
                                                status_class = "good"
                                            elif album.status == AlbumStatus.SKIPPED:
                                                status_class = "skipped"
                                            elif album.status == AlbumStatus.IGNORED:
                                                status_class = "ignored"
                                        %>
                                        <tr class="${status_class}">
                                            <td class="col-checkbox">
                                                <input type="checkbox" class="albumCheck" id="album-${album.pk}" name="album-${album.pk}" />
                                            </td>
                                            <td>
                                                <a href="${reverse_url('music-album_details', 'album_details', album.slug)}">
                                                    ${album.name}
                                                </a>
                                            </td>
                                            <td>${album.year or _('Unknown')}</td>
                                            <td>${album.type}</td>
                                            <td>${album.tracks}</td>
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
                                            <td>
                                                <div class="btn-group">
                                                    <a href="${reverse_url('music-album_details', 'album_details', album.slug)}" class="btn btn-sm btn-primary">
                                                        <i class="fa fa-info-circle"></i> ${_('Details')}
                                                    </a>
                                                    <button type="button" class="btn btn-sm btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                                        <span class="caret"></span>
                                                    </button>
                                                    <ul class="dropdown-menu dropdown-menu-right">
                                                        <li><a href="${reverse_url('music-set_album_status', 'set_album_status', album.pk)}?status=${AlbumStatus.WANTED}"><i class="fa fa-search"></i> ${_('Set Wanted')}</a></li>
                                                        <li><a href="${reverse_url('music-set_album_status', 'set_album_status', album.pk)}?status=${AlbumStatus.SKIPPED}"><i class="fa fa-step-forward"></i> ${_('Set Skipped')}</a></li>
                                                        <li><a href="${reverse_url('music-set_album_status', 'set_album_status', album.pk)}?status=${AlbumStatus.IGNORED}"><i class="fa fa-ban"></i> ${_('Set Ignored')}</a></li>
                                                        <li role="separator" class="divider"></li>
                                                        <li><a href="${reverse_url('music-search_album', 'search_album', album.pk)}"><i class="fa fa-search"></i> ${_('Search Now')}</a></li>
                                                    </ul>
                                                </div>
                                            </td>
                                        </tr>
                                    % endfor
                                % else:
                                    <tr>
                                        <td colspan="7">${_('No albums found')}</td>
                                    </tr>
                                % endif
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- JavaScript for album status management -->
    <script type="text/javascript">
        // Use vanilla JavaScript instead of jQuery to avoid dependency issues
        document.addEventListener('DOMContentLoaded', function() {
            // Filter albums by status
            var statusFilters = document.querySelectorAll('#wanted, #snatched, #downloaded, #skipped, #ignored');
            statusFilters.forEach(function(filter) {
                filter.addEventListener('click', function() {
                    var statusClass = this.id;
                    var rows = document.querySelectorAll('.' + statusClass);
                    rows.forEach(function(row) {
                        row.style.display = filter.checked ? '' : 'none';
                    });
                });
            });

            // Select all albums
            var selectAll = document.getElementById('selectAll');
            selectAll.addEventListener('click', function() {
                var albumChecks = document.querySelectorAll('.albumCheck');
                albumChecks.forEach(function(check) {
                    check.checked = selectAll.checked;
                });
            });

            // Change status for selected albums
            var changeStatus = document.getElementById('changeStatus');
            changeStatus.addEventListener('click', function() {
                var selectedAlbums = [];
                var albumChecks = document.querySelectorAll('.albumCheck:checked');
                albumChecks.forEach(function(check) {
                    if (check.id !== 'selectAll') {
                        selectedAlbums.push(check.id.replace('album-', ''));
                    }
                });

                if (selectedAlbums.length === 0) {
                    alert('${_("No albums selected")}');
                    return;
                }

                var status = document.getElementById('statusSelect').value;
                var artistID = document.getElementById('artistID').value;

                // Send AJAX request to update album status
                var xhr = new XMLHttpRequest();
                xhr.open('POST', '${reverse_url('music-set_albums_status', 'set_albums_status')}', true);
                xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        // Reload the page to show updated statuses
                        window.location.reload();
                    } else {
                        alert('${_("Error updating album status")}: ' + xhr.statusText);
                        console.log("Error details:", xhr.responseText);
                    }
                };
                xhr.onerror = function() {
                    alert('${_("Error updating album status")}: Network error');
                };
                xhr.send('albums=' + encodeURIComponent(selectedAlbums.join(',')) +
                         '&status=' + encodeURIComponent(status) +
                         '&artist=' + encodeURIComponent(artistID));
            });
        });
    </script>
</%block>

<%block name="scripts">
    <script type="text/javascript" src="${static_url('js/music.js')}"></script>
</%block>
