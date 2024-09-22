function formatNumber(num) {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

$(document).ready(function () {
    const environment = $('#environment').val();
    const requestData = { environment: environment };

    // Fetch metrics data from the server
    $.post('/get_metrics', requestData, function (data) {
        const metrics = data.metrics;
        const maxBlockCount = data.max_block_count;
        const maxCementedCount = data.max_cemented_count;

        function censorIpAddress(ipAddress) {
            const ipv4Address = ipAddress.replace("::ffff:", "");
            const octets = ipv4Address.split(".");
            return `${octets[0]}.X.X.${octets[3]}`;
        }

        let bootstrappingNodes = [];
        let otherNodes = [];

        metrics.forEach(metric => {
            const blockPercentage = (parseInt(metric.block_count) / maxBlockCount * 100).toFixed(2);
            const cementedPercentage = (parseInt(metric.cemented_count) / maxCementedCount * 100).toFixed(2);
            const versionString = `${metric.major_version}.${metric.minor_version}.${metric.patch_version}${metric.pre_release_version !== "0" ? `_DB${metric.pre_release_version}` : ''}`;
            const censoredAddress = censorIpAddress(metric.address);

            const blocksPerHour = metric.hourly_blocks ? formatNumber(metric.hourly_blocks.toFixed(0)) : null;
            const blocksPerDay = metric.daily_blocks ? formatNumber(metric.daily_blocks.toFixed(0)) : null;
            const cementedPerHour = metric.hourly_cemented ? formatNumber(metric.hourly_cemented.toFixed(0)) : null;
            const cementedPerDay = metric.daily_cemented ? formatNumber(metric.daily_cemented.toFixed(0)) : null;

            let blockMetricText = `Block count: ${metric.block_count} (${blockPercentage}%)`;
            if (blocksPerHour && blocksPerDay) {
                blockMetricText += ` [${blocksPerHour}/h | ${blocksPerDay}/day]`;
            }
            let cementedMetricText = `Cemented count: ${metric.cemented_count} (${cementedPercentage}%)`;
            if (cementedPerHour && cementedPerDay) {
                cementedMetricText += ` [${cementedPerHour}/h | ${cementedPerDay}/day]`;
            }

            const metricHtml = `
            <div class="metric" id="V${versionString}" data-category="${cementedPercentage < 95 ? 'bootstrapping' : 'other'}">
                <div class="label">
                    <form action="/node_chart/${metric.node_id}" method="GET">
                        <button type="submit" class="link-button">Node: ${censoredAddress} (V${versionString})</button>
                    </form>
                </div>            
                <div class="bar-container">
                    <div class="bar" style="width: ${blockPercentage}%">
                        <div class="bar-text">${blockMetricText}</div>
                    </div>
                </div>
                <div class="bar-container">
                    <div class="bar_cemented" style="width: ${cementedPercentage}%">
                        <div class="bar-text">${cementedMetricText}</div>
                    </div>
                </div>
            </div>
            `;

            if (cementedPercentage < 95) {
                bootstrappingNodes.push({ html: metricHtml, percentage: parseFloat(cementedPercentage), version: versionString });
            } else {
                otherNodes.push({ html: metricHtml, percentage: parseFloat(cementedPercentage), version: versionString });
            }
        });

        // Sort nodes by percentage
        otherNodes.sort((a, b) => b.percentage - a.percentage);
        bootstrappingNodes.sort((a, b) => b.percentage - a.percentage);

        // Add bootstrapping nodes section
        $('#metrics-container').append(`<h2>Bootstrapping Nodes (${bootstrappingNodes.length})</h2>`);
        bootstrappingNodes.forEach(node => $('#metrics-container').append(node.html));

        // Add other nodes section
        $('#metrics-container').append(`<h2>Other Nodes (${otherNodes.length})</h2>`);
        otherNodes.forEach(node => $('#metrics-container').append(node.html));

        // Populate the version filter options
        const versionFilter = $('#version-filter');
        const versionCounts = {};

        metrics.forEach(metric => {
            const versionString = `${metric.major_version}.${metric.minor_version}.${metric.patch_version}${metric.pre_release_version !== "0" ? `_DB${metric.pre_release_version}` : ''}`;
            if (versionCounts[versionString]) {
                versionCounts[versionString]++;
            } else {
                versionCounts[versionString] = 1;
            }
        });

        Object.entries(versionCounts)
            .sort((a, b) => b[0].localeCompare(a[0])) // Sort versions in descending order
            .forEach(([version, count]) => {
                versionFilter.append(`<option value="${version}">${version} (${count})</option>`);
            });

        // Handle version filter change event
        versionFilter.on('change', function () {
            const selectedVersion = $(this).val();
            filterNodesByVersion(selectedVersion);
        });
    }).fail(function () {
        alert("Failed to fetch metrics data.");
    });
});

function filterNodesByVersion(version) {
    const allMetrics = $('.metric');
    allMetrics.hide(); // Hide all metrics

    let bootstrappingNodesCount = 0;
    let otherNodesCount = 0;

    if (version === '') {
        allMetrics.show(); // Show all metrics when no version selected
        bootstrappingNodesCount = $('.metric[data-category="bootstrapping"]').length; // Count of bootstrapping nodes
        otherNodesCount = $('.metric[data-category="other"]').length; // Count of other nodes
    } else {
        allMetrics.each(function () {
            const metricVersion = $(this).attr('id').substring(1); // Remove the 'V' prefix
            if (metricVersion === version) {
                $(this).show(); // Show metrics with matching version
                if($(this).data('category') === 'bootstrapping') {
                    bootstrappingNodesCount++;
                } else {
                    otherNodesCount++;
                }
            }
        });
    }

    // Update counts in UI
    $('#metrics-container').find('h2:contains("Bootstrapping Nodes")').html(`Bootstrapping Nodes (${bootstrappingNodesCount})`);
    $('#metrics-container').find('h2:contains("Other Nodes")').html(`Other Nodes (${otherNodesCount})`);
}
