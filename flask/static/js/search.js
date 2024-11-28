$("document").ready(function(){
    const case_fields = ["Case ID", "Case No.", "Client ID"];
    const case_timefields = ["Created", "Resolved"];
    const client_fields = ["System ID", "Hostname", "IP Address", "Status"];
    const client_timefields = ["Register", "Modified"];

    function toLocaleISOString(date) {
        const localeDate = new Date(date - date.getTimezoneOffset() * 60000);
        localeDate.setSeconds(null);
        localeDate.setMilliseconds(null);
        return localeDate.toISOString().slice(0, -1);
    }

    let type;

    function selector(type, refresh) {
        if (refresh === undefined) {
            $('#fields').empty();
            $('#timefield').empty();
            $('#table_holder').empty();
            if (document.querySelector('#typeSelector').innerHTML === 'Cases') {
                case_fields.forEach(item => {
                    fields = document.getElementById('fields');
                    fields.options.add(new Option(item, item));
                });
                case_timefields.forEach(item => {
                    fields = document.getElementById('timefield');
                    fields.options.add(new Option(item, item));
                });
                first = 'cases'
                second = 'clients'
                type = 'cases'
            }
            else {
                client_fields.forEach(item => {
                    fields = document.getElementById('fields');
                    fields.options.add(new Option(item, item));
                });
                client_timefields.forEach(item => {
                    fields = document.getElementById('timefield');
                    fields.options.add(new Option(item, item));
                });
                first = 'clients'
                second = 'cases'
                type = 'client'
            }
        };
        const form = document.getElementById('searchform');
        var formData = new FormData(form);
        first_table = document.querySelector('#' + first + '_template').innerHTML;
        second_table = document.querySelector('#' + second + '_template').innerHTML;
        document.querySelector('#table_holder').innerHTML = first_table + second_table;
        send_request(type, formData);
        $('.' + second).hide();
        return type;
    }

    function send_request(type, formData) {
        formData.append('type', type);
        res = fetch('/search', {
            method: 'POST',
            body: formData
        }).then(function(response) {
            return response.json();
        }).then(function(json){
            field_map = {'cases':['.case_tbody','#case_row_temp'],'client':['.client_tbody', '#client_row_temp']}
            if (json.hasOwnProperty('pri_data')) {
                if (json.pri_data.length == 0) {
                    let blank = document.querySelector('#blank').innerHTML;
                    blank = blank.replace('{table}', json.field);
                    document.querySelector(field_map[json.field][0]).innerHTML = blank;
                }
                else {
                    const pri_table = json.pri_data.map(obj => {
                        let row_temp = document.querySelector(field_map[json.field][1]).innerHTML;
                        if (json.field === 'cases') {
                            row_temp = row_temp.replace('{case_id}', obj.case_id);
                            row_temp = row_temp.replace('{client}', obj.client);
                            row_temp = row_temp.replace('{case_num}', obj.case_num);
                            row_temp = row_temp.replace('{video_file}', obj.video_file);
                            row_temp = row_temp.replace('{datetime_created}', obj.datetime_created);
                            row_temp = row_temp.replace('{datetime_resolved}', obj.datetime_resolved);
                        }
                        else {
                            row_temp = row_temp.replace('{guid}', obj.guid);
                            row_temp = row_temp.replace('{hostname}', obj.hostname);
                            row_temp = row_temp.replace('{ip_addr}', obj.ip_addr);
                            row_temp = row_temp.replace('{date_registered}', obj.date_registered);
                            row_temp = row_temp.replace('{last_modified}', obj.last_modified);
                            row_temp = row_temp.replace('{status}', obj.status);
                        }
                        return row_temp;
                    });
                    document.querySelector(field_map[json.field][0]).innerHTML = pri_table.join('');
                }
            }
        });
    }

    window.addEventListener('load', () => {
        previous = new Date(new Date().setDate(new Date().getDate() - 7));
        document.getElementById('start-time').value = toLocaleISOString(previous);
        document.getElementById('end-time').value = toLocaleISOString(new Date());
        type = selector(type);
    });
    
    document.querySelector('#cases').onclick = function(){
        document.querySelector('#typeSelector').innerHTML = 'Cases';
        type = selector(type);
    }
    document.querySelector('#clients').onclick = function(){
        document.querySelector('#typeSelector').innerHTML = 'Clients';
        type = selector(type);
    }
    
    searchform = document.getElementById('searchform');
    searchform.addEventListener('submit', function(event) {
        event.preventDefault();
        type = selector(type,'refresh');
    })
});