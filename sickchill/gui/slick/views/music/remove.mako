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
            </div>
            <h1 class="header">${header}</h1>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-12">
            <div class="alert alert-success">
                <p>${_('Artist has been removed from your library.')}</p>
            </div>
            <p>${_('You will be redirected to the artist list in 5 seconds.')}</p>
        </div>
    </div>
    
    <script type="text/javascript">
        setTimeout(function() {
            window.location.href = "${reverse_url('music-index', 'index')}";
        }, 5000);
    </script>
</%block>