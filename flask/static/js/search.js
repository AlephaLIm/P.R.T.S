$("document").ready(function(){
    const case_fields = ["Case ID", "Case No.", "Client ID"];
    const client_fields = ["Client ID", "Hostname", "IP Address", "Status"];

    if (document.querySelector('#typeSelector').innerHTML === 'Cases') {
        case_fields.forEach(item => {
            fields = document.getElementById('fields');
            fields.options.add(new Option(item, item));
        });
    }

    document.querySelector('#cases').onclick = function(){
        document.querySelector('#typeSelector').innerHTML = 'Cases';
        $('#fields').empty();
        case_fields.forEach(item => {
            fields = document.getElementById('fields');
            fields.options.add(new Option(item, item));
        });
    }
    document.querySelector('#clients').onclick = function(){
        document.querySelector('#typeSelector').innerHTML = 'Clients';
        $('#fields').empty();
        client_fields.forEach(item => {
            fields = document.getElementById('fields');
            fields.options.add(new Option(item, item));
        });
    }
});