$("document").ready(function(){
    let labels = ['21-11-2024 18:52:57','21-11-2024 18:53:02','21-11-2024 18:53:07','21-11-2024 18:53:12','21-11-2024 18:53:17','21-11-2024 18:53:22','21-11-2024 18:53:27','21-11-2024 18:53:32','21-11-2024 18:53:37']
    let dataset = [38, 43, 31, 42, 95, 97, 10, 95, 78, 21]
    var data = {
        labels: labels,
        datasets: [{
            label: 'Log Ingest Rate',
            data: dataset,
            fill: false,
            borderColor: 'rgb(7, 230, 226)',
            tension: 0.1
        }]
    }
    let config = {
        type: 'line',
        data: data
    }
    
    var linegraph = new Chart(data, config)
});