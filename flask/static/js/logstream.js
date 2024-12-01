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
            backgroundColor: palette('tol', piedataset.length).map(function(hex) {
                return '#' + hex;
            }),
            hoverOffset: 5,
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

        piechart.data.labels = e.logtype;
        piechart.data.datasets[0].data = e.dataset;
        piechart.update();
    }

    const xhttp = new XMLHttpRequest();
    xhttp.open('GET', '/initialize', true);
    xhttp.send();

    var listsrc = new EventSource('/casestream');
    listsrc.onmessage = function(event) {
        var e = JSON.parse(event.data.substring(2, event.data.length - 1));
        if (e.cases.length > 0) {
            const casetable = e.cases.map(obj => {
                let caseitem = document.querySelector('#case_template').innerHTML;
                caseitem = caseitem.replace('{case_num}', obj.casenum);
                caseitem = caseitem.replace(/{caseid}/g, obj.cid);
                caseitem = caseitem.replace('{client}', obj.guid);
                caseitem = caseitem.replace('{created}', obj.created);
                caseitem = caseitem.replace('{resolved}', obj.resolved);
                return caseitem;
            });
            document.querySelector('#case').innerHTML = casetable.join('');
        }
        if (e.clients.length > 0) {
            const clienttable = e.clients.map(obj => {
                let clientitem = document.querySelector('#client_template').innerHTML;
                clientitem = clientitem.replace('{guid}', obj.guid);
                clientitem = clientitem.replace('{hostname}', obj.hostname);
                clientitem = clientitem.replace('{ip}', obj.ip);
                clientitem = clientitem.replace('{registered}', obj.registered);
                clientitem = clientitem.replace('{last_m}', obj.last_m);
                clientitem = clientitem.replace('{status}', obj.status);
                return clientitem;
            });
            document.querySelector('#client').innerHTML = clienttable.join('');
        }
        
        let clientrows = document.querySelectorAll('.client_row');
        for (let row of clientrows) {
            if (row.querySelector('td:nth-child(6)').innerText === 'Healthy') {
                row.querySelector('td:nth-child(6)').style.backgroundColor = '#1cbd00';
                row.querySelector('td:nth-child(6)').style.color = 'black';
            }
            else if (row.querySelector('td:nth-child(6)').innerText === 'Affected') {
                row.querySelector('td:nth-child(6)').style.backgroundColor = '#bd0d00';
            }
        }
        
        $('.client_row').each(function(i) {
            $(this).hide();
            $(this).delay(50*i).fadeIn(50);
        });

        $('.case_row').each(function(i) {
            $(this).hide();
            $(this).delay(50*i).fadeIn(50);
        });
    };


});