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
        const tbody_map = {'cases': 'case_tbody', 'clients': 'client_tbody'}
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
        document.querySelector('.' + tbody_map[first]).setAttribute('id', 'primary');
        send_request(type, formData);
        $('.' + second).hide();
        return type;
    }

    function populate(fieldinput, datamap) {
        field_map = {'cases':['.case_tbody','#case_row_temp'],'client':['.client_tbody', '#client_row_temp']}
        if (datamap.length == 0) {
            let blank = document.querySelector('#blank').innerHTML;
            blank = blank.replace('{table}', fieldinput);
            document.querySelector(field_map[fieldinput][0]).innerHTML = blank; 
        }
        else {
            const data_table = datamap.map(obj => {
                let row_temp = document.querySelector(field_map[fieldinput][1]).innerHTML;
                    if (fieldinput === 'cases') {
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
            document.querySelector(field_map[fieldinput][0]).innerHTML = data_table.join('');
        }
    }

    function send_request(type, formData, guid) {
        formData.append('type', type);
        if (guid !== undefined) {
            formData.append('guid', guid);
        }
        res = fetch('/search', {
            method: 'POST',
            body: formData
        }).then(function(response) {
            return response.json();
        }).then(function(json){
            table_map = {'cases':'.cases','client':'.clients'}
            if (json.hasOwnProperty('pri_data')) {
                populate(json.field, json.pri_data);
            }
            else if (json.hasOwnProperty('sec_data')) {
                populate(json.field, json.sec_data);
            }
            $(table_map[json.field]).fadeIn(200);
            $(table_map[json.field] + ' tr').hide();
            $(table_map[json.field] + ' tr').each(function(i) {
                $(this).delay(50*i).fadeIn(50);
            })

            if (json.field === 'client') {
                let c_rows = document.querySelectorAll('.c_row');
                for (let row of c_rows) {
                    if (row.querySelector('td:nth-child(6)').innerText === 'Healthy') {
                        row.querySelector('td:nth-child(6)').style.backgroundColor = '#1cbd00';
                        row.querySelector('td:nth-child(6)').style.color = 'black';
                    }
                    else if (row.querySelector('td:nth-child(6)').innerText === 'Affected') {
                        row.querySelector('td:nth-child(6)').style.backgroundColor = '#bd0d00';
                    }
                }
            }
        });
    }

    window.addEventListener('load', () => {
        previous = new Date(new Date().setDate(new Date().getDate() - 1));
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

    $('#table_holder').on('click', '.selectable', function(event) {
        if ($(event.currentTarget).parent()[0].id === 'primary') {
            const guid = $(event.currentTarget).children('.sec_info')[0].innerHTML;
            const form = document.getElementById('searchform');
            var formData = new FormData(form);
            if (type === 'cases') {
                send_request('client', formData, guid);
            }
            else {send_request('cases', formData, guid);}
        }
    });
});