$("document").ready(function(){
    const d = new Date().toLocaleTimeString();
    let label = Array(10).fill(d)
    let dataset = Array(10).fill(0)
    var data = {
        labels: label,
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
    
    var linegraph = new Chart(document.getElementById('logstream'), config)

    let pielabel = ['WinEventLog:Security', 'WinEventLog:Application', 'WinEventLog:System']
    let piedataset = [16593, 1068, 1063]
    var piedata = {
        labels: pielabel,
        datasets: [{
            label: 'Log Ingest Type',
            data: piedataset,
            backgroundColor: [
                'rgb(7, 7, 232)',
                'rgb(232, 7, 56)',
                'rgb(232, 228, 7)'
            ],
            hoverOffset: 5
        }]
    }

    let pieconfig = {
        type: 'doughnut',
        data: piedata
    }

    var piechart = new Chart(document.getElementById('piechart'), pieconfig)

    var source = new EventSource('/datastream');
    source.onmessage = function(event) {
        var e = JSON.parse(event.data.substring(2, event.data.length - 1));
        var newdata = JSON.parse(e.data);
        let newdatetime = new Date().toLocaleTimeString();
        linegraph.data.labels.shift();
        linegraph.data.labels.push(newdatetime);
        linegraph.data.datasets[0].data.shift();
        linegraph.data.datasets[0].data.push(newdata);
        linegraph.update();

        piechart.data.datasets[0].data = e.logtype;
        piechart.update();
    }
});