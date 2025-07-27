// Avoid `console` errors in browsers that lack a console.
(function () {
    let method;
    const noop = function () {};

    const methods = [
        'assert',
        'clear',
        'count',
        'debug',
        'dir',
        'dirxml',
        'error',
        'exception',
        'group',
        'groupCollapsed',
        'groupEnd',
        'info',
        'log',
        'markTimeline',
        'profile',
        'profileEnd',
        'table',
        'time',
        'timeEnd',
        'timeStamp',
        'trace',
        'warn',
    ];
    let length = methods.length;
    const console = window.console || {};

    while (length > 0) {
        length--;
        method = methods[length];

        // Only stub undefined methods.
        console[method] ||= noop;
    }
})();

$(document).ready(() => {
    function setDefault(which, force) {
        if (which === undefined || which.length === 0) {
            return;
        }

        if ($('#whichDefaultMusicRootDir').val() === which && force !== true) {
            return;
        }

        console.log('setting default to ' + which);

        // Put an asterisk on the text
        if ($('#' + which).text().charAt(0) !== '*') {
            $('#' + which).text('*' + $('#' + which).text());
        }

        // If there's an existing one then take the asterisk off
        if ($('#whichDefaultMusicRootDir').val() && force !== true) {
            const oldDefault = $('#' + $('#whichDefaultMusicRootDir').val());
            oldDefault.text(oldDefault.text().slice(1));
        }

        $('#whichDefaultMusicRootDir').val(which);
    }

    function syncOptionIDs() {
        // Re-sync option ids
        let index = 0;
        $('#musicRootDirs option').each(function () {
            index++;
            $(this).attr('id', 'rd-' + index);
        });
    }

    function refreshRootDirectories() {
        if ($('#musicRootDirs').length === 0) {
            return;
        }

        let doDisable = 'true';

        // Re-sync option ids
        syncOptionIDs();

        // If nothing's selected then select the default
        if ($('#musicRootDirs option:selected').length === 0 && $('#whichDefaultMusicRootDir').val().length > 0) {
            $('#' + $('#whichDefaultMusicRootDir').val()).prop('selected', true);
        }

        // If something's selected then we have some behavior to figure out
        if ($('#musicRootDirs option:selected').length > 0) {
            doDisable = '';
        }

        // Update the elements
        $('#deleteMusicRootDir').prop('disabled', doDisable);
        $('#defaultMusicRootDir').prop('disabled', doDisable);
        $('#editMusicRootDir').prop('disabled', doDisable);

        let logString = '';
        let directoryString = '';
        if ($('#whichDefaultMusicRootDir').val().length >= 4) {
            directoryString = $('#whichDefaultMusicRootDir').val().slice(3);
        }

        $('#musicRootDirs option').each(function () {
            logString += $(this).val() + '=' + $(this).text() + '->' + $(this).attr('id') + '\n';
            if (directoryString.length > 0) {
                directoryString += '|' + $(this).val();
            }
        });
        logString += 'def: ' + $('#whichDefaultMusicRootDir').val();
        console.log(logString);

        $('#musicRootDirText').val(directoryString);
        $('#musicRootDirText').change();
        console.log('musicRootDirText: ' + $('#musicRootDirText').val());
    }

    function postRootDirectories() {
        refreshRootDirectories();
        $.post(scRoot + '/config/general/saveMusicRootDirs', {musicRootDirString: $('#musicRootDirText').val()});
    }

    function addRootDirectory(path) {
        if (path.length === 0) {
            return;
        }

        // Check if it's the first one
        let isDefault = false;
        if ($('#whichDefaultMusicRootDir').val().length === 0) {
            isDefault = true;
        }

        $('#musicRootDirs').append('<option value="' + path + '">' + path + '</option>');

        syncOptionIDs();

        if (isDefault) {
            setDefault($('#musicRootDirs option').attr('id'));
        }

        postRootDirectories();
    }

    function editRootDirectory(path) {
        if (path.length === 0) {
            return;
        }

        // As long as something is selected
        if ($('#musicRootDirs option:selected').length > 0) {
            // Update the selected one with the provided path
            if ($('#musicRootDirs option:selected').attr('id') === $('#whichDefaultMusicRootDir').val()) {
                $('#musicRootDirs option:selected').text('*' + path);
            } else {
                $('#musicRootDirs option:selected').text(path);
            }

            $('#musicRootDirs option:selected').val(path);
        }

        postRootDirectories();
    }

    $('#addMusicRootDir').on('click', function () {
        $(this).nFileBrowser(addRootDirectory);
    });
    $('#editMusicRootDir').on('click', function () {
        $(this).nFileBrowser(editRootDirectory, {
            initialDir: $('#musicRootDirs option:selected').val(),
        });
    });

    $('#deleteMusicRootDir').on('click', () => {
        if ($('#musicRootDirs option:selected').length > 0) {
            const toDelete = $('#musicRootDirs option:selected');
            const newDefault = (toDelete.attr('id') === $('#whichDefaultMusicRootDir').val());
            const deletedNumber = $('#musicRootDirs option:selected').attr('id').slice(3);

            toDelete.remove();
            syncOptionIDs();

            if (newDefault) {
                console.log('new default when deleting');

                // We deleted the default so this isn't valid anymore
                $('#whichDefaultMusicRootDir').val('');

                // If we're deleting the default and there are options left then pick a new default
                if ($('#musicRootDirs option').length > 0) {
                    setDefault($('#musicRootDirs option').attr('id'));
                }
            } else if ($('#whichDefaultMusicRootDir').val().length > 0) {
                const oldDefaultNumber = $('#whichDefaultMusicRootDir').val().slice(3);
                if (oldDefaultNumber > deletedNumber) {
                    $('#whichDefaultMusicRootDir').val('rd-' + (oldDefaultNumber - 1));
                }
            }
        }

        refreshRootDirectories();
        $.post(scRoot + '/config/general/saveMusicRootDirs', {
            musicRootDirString: $('#musicRootDirText').val(),
        });
    });

    $('#defaultMusicRootDir').on('click', () => {
        if ($('#musicRootDirs option:selected').length > 0) {
            setDefault($('#musicRootDirs option:selected').attr('id'));
        }

        refreshRootDirectories();
        $.post(scRoot + '/config/general/saveMusicRootDirs', {
            musicRootDirString: $('#musicRootDirText').val(),
        });
    });
    $('#musicRootDirs').click(refreshRootDirectories);

    // Set up buttons on page load
    syncOptionIDs();
    setDefault($('#whichDefaultMusicRootDir').val(), true);
    refreshRootDirectories();
});