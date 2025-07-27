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
            <h1 class="header">${header}</h1>
        </div>
    </div>
    <div class="row">
        <div class="col-md-12">
            <form method="post" action="${reverse_url('music-search', 'search')}" class="form-horizontal">
                <div class="form-group">
                    <label for="query" class="col-sm-2 control-label">${_('Artist Name')}</label>
                    <div class="col-sm-10">
                        <input type="text" name="query" id="query" value="${query}" class="form-control" placeholder="${_('Artist name')}">
                    </div>
                </div>
                <div class="form-group">
                    <div class="col-sm-offset-2 col-sm-10">
                        <button type="submit" class="btn btn-primary">
                            <i class="fa fa-search"></i> ${_('Search')}
                        </button>
                    </div>
                </div>
            </form>
        </div>
    </div>
    % if search_results:
        <div class="row">
            <div class="col-md-12">
                <h2>${_('Search Results')}</h2>
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>${_('Artist')}</th>
                                <th>${_('Score')}</th>
                                <th>${_('Actions')}</th>
                            </tr>
                        </thead>
                        <tbody>
                            % for result in search_results:
                                <tr>
                                    <td>${result.get('name', '')}</td>
                                    <td>${result.get('ext:score', '0')}</td>
                                    <td>
                                        <form method="post" action="${reverse_url('music-add', 'add')}">
                                            <input type="hidden" name="musicbrainz" value="${result.get('id', '')}">
                                            <button type="submit" class="btn btn-sm btn-success">
                                                <i class="fa fa-plus"></i> ${_('Add')}
                                            </button>
                                        </form>
                                    </td>
                                </tr>
                            % endfor
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    % endif
</%block>