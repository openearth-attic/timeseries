function loadPlot(options) {

    if (_.has(options, 'url')) {
        $.get(options.url, function(data) {
            var content = $(data);
            var plotDiv = _.filter(content, ['className', 'bk-root']);
            var plotScript = _.last(_.filter(content, ['tagName', 'SCRIPT']));
            $(options.plotDiv).html(plotDiv);
            $(options.plotScript).html(plotScript);
        });
    } else {
        $(options.plotDiv).html($(options.div));
        $(options.plotScript).html($(options.script));
    }


}
