$(document).ready(function() {
    $(".details").each(function() {
        $(this).text($(this).text().substring(0,300));
    });
});