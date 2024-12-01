$("document").ready(function() {
    function generateChart(label, dataset) {
        if (document.getElementById('piechart') == null) {
            document.querySelector('.piechart').innerHTML = '<canvas id="piechart"></canvas>';
        }
        var data = {
            labels: label,
            datasets: [{
                label: 'Log Type',
                data: dataset,
                backgroundColor: palette('tol', dataset.length).map(function(hex) {
                    return '#' + hex;
                }),
                hoverOffset: 5,
            }]
        }
    
        let config = {
            type: 'doughnut',
            data: data
        }
    
        var piechart = new Chart(document.getElementById('piechart'), config);
        return piechart;
    }

    function check_status() {
        let items = document.querySelectorAll('.statusnode');
        items.forEach((item) => {
            if (item.innerHTML === 'Finished') {
                item.style.backgroundColor = '#37de00';
            }
            else if (item.innerHTML === 'Processing') {
                item.style.backgroundColor = '#05c9f5';
            }
            else if (item.innerHTML === 'Open') {
                item.style.backgroundColor = '#de0000';
                item.style.color = 'whitesmoke';
            }
            else {
                item.style.backgroundColor = '#454545';
                item.style.color = 'whitesmoke';
            }
        });
    }

    check_status();

    function collapsible_listeners() {
        var col = document.getElementsByClassName("collapsible");
        var i;

        for (i=0; i<col.length; i++) {
            col[i].addEventListener('click', function() {
                this.classList.toggle("active");
                var content = this.nextElementSibling;
                if (content.style.maxHeight) {
                    content.style.maxHeight = null;
                }
                else {
                    content.style.maxHeight = content.scrollHeight + "px";
                }
            });
        }
    }

    function call_for_chart(cid) {
        const xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function() {
            if (this.readyState == 4 && this.status == 200) {
                let types = JSON.parse(this.responseText);
                let keys = Object.keys(types);
                let data = [];
                keys.forEach(function(item) {
                    data.push(types[item]);
                })
                generateChart(keys, data);
                resolver();
            }
        }
        xhttp.open('GET', '/get_chartdata/' + cid, true);
        xhttp.send();
    }

    cid = document.querySelector('#title_h1 p').innerHTML;
    collapsible_listeners();
    call_for_chart(cid);

    if (document.getElementsByClassName('empty') != null) {
        var refresh = new EventSource('/check_status/' + cid);
        refresh.onmessage = function(event) {
            var e = JSON.parse(event.data.substring(2, event.data.length - 1));
            let transcript_content = document.querySelector('#transcript_template').innerHTML;
            transcript_content = transcript_content.replace('{content}', e.transcript);
            document.querySelector('.transcript').innerHTML = transcript_content;
            const logrecord = Object.values(e.json_data).map(obj => {
                let recordheader = document.querySelector('#log_template').innerHTML;
                recordheader = recordheader.replace('{source}', obj.source);
                recordheader = recordheader.replace('{host}', obj.host);
                recordheader = recordheader.replace('{index}', obj.index);
                recordheader = recordheader.replace('{time}', obj._time);
                var detailed = [];
                Object.entries(obj).map(([key, value]) => {
                    let object = document.querySelector('#logfield_template').innerHTML;
                    object = object.replace('{key}',key);
                    object = object.replace('{value}', value);
                    detailed.push(object);
                });
                recordheader += '<div class="content">' + detailed.join('') +'</div>';
                return recordheader;
            });
            document.querySelector('.logs').innerHTML = '<div class="log_header">Related Logs</div>' + logrecord.join('');
            document.querySelector('#status_proc').innerHTML = 'Finished';
            $('.collapsible').each(function(i) {
                $(this).hide();
                $(this).delay(50*i).fadeIn(50);
            })
            collapsible_listeners();
            check_status();
        }
    }

    function resolver() {
        $("#resolved_status").on("click", function(event) {
            const dataHeaders = new Headers();
            dataHeaders.append("Content-Type", "application/json");
            let json_body;
            if (event.currentTarget.innerHTML === 'Open') {
                json_body = { action:"resolve" }
            }
            else {
                json_body = { action:"open" }
            }
            res = fetch(('/case/' + cid), {
                method: 'POST',
                body: JSON.stringify(json_body),
                headers: dataHeaders
            }).then(function(response) {
                return response.json();
            }).then(function(json) {
                document.querySelector('#resolved_date').innerHTML ='Date Resolved: ' + json.resolved;
                if (json.resolved != 'None') {
                    document.querySelector('#resolved').innerHTML = 'Resolved: Yes';
                    document.querySelector('#resolved_status').innerHTML = 'Closed';
                    
                    check_status();
                }
                else {
                    document.querySelector('#resolved').innerHTML = 'Resolved: No';
                    document.querySelector('#resolved_status').innerHTML = 'Open';
                    check_status();
                }
            });
        });
    }
});