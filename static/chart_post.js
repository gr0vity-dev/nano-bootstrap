const address = "some_address_here"; // Replace this with the actual address you want to use

fetch('/node_data', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({address: address})
})
.then(response => response.json())
.then(data => {
    const labels = data.map(item => item.timestamp);
    const blockData = data.map(item => item.block_count);
    const cementedData = data.map(item => item.cemented_count);

    const ctx = document.getElementById('nodeChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Block Count',
                data: blockData,
                borderColor: 'blue',
                fill: false
            }, {
                label: 'Cemented Count',
                data: cementedData,
                borderColor: 'green',
                fill: false
            }]
        },
        options: {
            scales: {
                xAxes: [{
                    type: 'time',
                    time: {
                        unit: 'day'
                    }
                }]
            }
        }
    });
});
