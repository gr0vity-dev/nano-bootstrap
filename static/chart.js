fetch(`/node_data/${node_id}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  .then(response => response.json())
  .then(data => {
    const timestamps = data.map(item => new Date(item.timestamp));
    const blockCounts = data.map(item => item.block_count);
    const cementedCounts = data.map(item => item.cemented_count);
    const versions = data.map(item => item.version);
  
    const blockTrace = {
      x: timestamps,
      y: blockCounts,
      mode: 'lines+markers',
      name: 'Block Count',
      text: versions,
      hovertemplate: 'Time: %{x|%Y-%m-%d %H:%M:%S}<br>Block Count: %{y}<br>Version: %{text}<extra></extra>',
      line: { color: '#007bff' }
    };
  
    const cementedTrace = {
      x: timestamps,
      y: cementedCounts,
      mode: 'lines+markers',
      name: 'Cemented Count',
      text: versions,
      hovertemplate: 'Time: %{x|%Y-%m-%d %H:%M:%S}<br>Cemented Count: %{y}<br>Version: %{text}<extra></extra>',
      line: { color: '#28a745' }
    };
  
    const layout = {
      title: {
        text: 'Node Metrics',
        font: {
          size: 24
        }
      },
      xaxis: {
        title: 'Time',
        type: 'date',
        tickformat: '%b %d',
        rangeselector: {
          buttons: [
            {
              count: 1,
              label: '1d',
              step: 'day',
              stepmode: 'backward'
            },
            {
              count: 7,
              label: '1w',
              step: 'day',
              stepmode: 'backward'
            },
            {
              step: 'all',
              label: 'All'
            }
          ]
        }
      },
      yaxis: {
        title: 'Count'
      },
      hovermode: 'closest'
    };
  
    Plotly.newPlot('nodeChart', [blockTrace, cementedTrace], layout);
  })
  .catch(error => {
    console.error('Error fetching node data:', error);
  });