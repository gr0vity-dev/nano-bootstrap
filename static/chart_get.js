// Get the address from the URL
const address = window.location.pathname.split('/')[2];


fetch(`/node_data/${address}`)
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
