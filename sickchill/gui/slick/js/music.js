// Music page specific JavaScript
$(document).ready(function() {
    // Apply background image if FANART_BACKGROUND is enabled
    if (metaToBool('settings.FANART_BACKGROUND')) {
        const backgroundPath = getMeta('showBackgroundImage');
        if (backgroundPath) {
            $.backstretch(backgroundPath);
            $('.backstretch').css('opacity', getMeta('settings.FANART_BACKGROUND_OPACITY')).fadeIn('500');
        }
    }
});