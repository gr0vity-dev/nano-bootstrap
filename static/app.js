$(document).ready(function () {
    $.get('/get_metrics', function (data) {
        const metrics = data.metrics;
        const maxBlockCount = data.max_block_count;
        const maxCementedCount = data.max_cemented_count;
        

        let bootstrappingNodes = [];
        let otherNodes = [];

        metrics.forEach(metric => {
            const blockPercentage = (parseInt(metric.block_count) / maxBlockCount * 100).toFixed(2);
            const cementedPercentage = (parseInt(metric.cemented_count) / maxCementedCount * 100).toFixed(2);
            const versionString = `${metric.major_version}.${metric.minor_version}.${metric.patch_version}${metric.pre_release_version !== "0" ? `_DB${metric.pre_release_version}` : ''}`;


            const metricHtml = `
                <div class="metric">
                    <div class="label">Block count: ${metric.block_count} (${blockPercentage}%) :V${versionString} </div>
                    <div class="bar-container">
                        <div class="bar" style="width: ${blockPercentage}%"></div>
                    </div>                    
                    <div class="bar-container">
                        <div class="bar_cemented" style="width: ${cementedPercentage}%"></div>
                    </div>
                    <div class="label">Cemented count: ${metric.cemented_count} (${cementedPercentage}%)</div>
                </div>
            `;

            if (cementedPercentage < 95) {
                bootstrappingNodes.push({ html: metricHtml, percentage: parseFloat(cementedPercentage) });
            } else {
                otherNodes.push({ html: metricHtml, percentage: parseFloat(cementedPercentage) });
            }
        });

        // Sort otherNodes by highest percentage first
        otherNodes.sort((a, b) => b.percentage - a.percentage);
        bootstrappingNodes.sort((a, b) => b.percentage - a.percentage);

        // Add bootstrapping nodes section
        $('#metrics-container').append('<h2>Bootstrapping Nodes</h2>');
        bootstrappingNodes.forEach(node => $('#metrics-container').append(node.html));

        // Add other nodes section
        $('#metrics-container').append('<h2>Other Nodes</h2>');
        otherNodes.forEach(node => $('#metrics-container').append(node.html));
    });
});