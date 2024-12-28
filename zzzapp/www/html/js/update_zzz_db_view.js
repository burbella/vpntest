function load_js_update_zzz_db_view()
{
    $('#view_schema').click(function(){
        lookup_schema();
    });

    $('#view_table').click(function(){
        lookup_table_data();
    });

    $('#query_with_where').click(function(){
        let include_where=true;
        let include_order_by=false;
        lookup_table_data(include_where, include_order_by);
    });

    $('#query_with_order_by').click(function(){
        let include_where=false;
        let include_order_by=true;
        lookup_table_data(include_where, include_order_by);
    });

    $('#query_with_both').click(function(){
        let include_where=true;
        let include_order_by=true;
        lookup_table_data(include_where, include_order_by);
    });

    $("#format_menu option[value='html']").attr("selected","selected");

    $('#table_menu').change(function(){
        lookup_table_columns($(this).val());
    });

}

//--------------------------------------------------------------------------------

function show_loading() {
    $('#db_output').hide();
    $('#db_status').html('Loading table data...');
}

//--------------------------------------------------------------------------------

function lookup_table_columns(table_name) {
    let default_option = '<option>select a table</option>';

    let postdata = `action=db_view_table_info&table=${table_name}`;
    $.post(url_db_view, postdata)
    .done(function(data){
        $('#column_menu').html(data);
        $('#order_column_menu').html(data);
    })
    .fail(function(){
        console.log('ERROR looking up table columns');
        $('#column_menu').html(default_option);
        $('#order_column_menu').html(default_option);
    });
}

//--------------------------------------------------------------------------------

function lookup_schema() {
    setTimeout(show_loading, 1);

    let postdata = `action=db_view&table=schema`;
    $.post(url_db_view, postdata)
    .done(function(data){
        $('#db_output').html(data);
        $('#db_status').html('');
    })
    .fail(function(){
        $('#db_output').html('ERROR: schema lookup failed');
        $('#db_status').html('');
    }).always(function(){
        $('#db_output').show();
    });
}

//--------------------------------------------------------------------------------

function lookup_table_data(include_where=false, include_order_by=false) {
    setTimeout(show_loading, 1);

    let table = $('#table_menu>option:selected').val();
    let format = $('#format_menu>option:selected').val();
    let max_rows = $('#max_rows').val();
    let max_table_cell_data = $('#max_table_cell_data').val();

    let case_insensitive = String($('#case_insensitive').is(':checked'));
    let case_insensitive_param = `&case_insensitive=${case_insensitive}`;

    let query_data = '';
    if (include_where) {
        let query_colname = $('#column_menu>option:selected').val();
        let comparison_name = $('#compare_menu>option:selected').val();
        let column_value = $('#column_value').val();
        query_data = `${case_insensitive_param}&comparison_name=${comparison_name}&colname=${query_colname}&column_value=` + encodeURIComponent(column_value);
    }

    let order_by = '';
    if (include_order_by) {
        let order_by_colname = $('#order_column_menu>option:selected').val();
        let order_asc_desc = $('#order_asc_desc>option:selected').val();
        order_by = `&order_by=${order_by_colname}&order_asc_desc=${order_asc_desc}`;
    }

    let postdata = `action=db_view&table=${table}&format=${format}&max_rows=${max_rows}&max_table_cell_data=${max_table_cell_data}${query_data}${order_by}`;
    $.post(url_db_view, postdata)
    .done(function(data){
        $('#db_output').html(data);
        $('#db_status').html('');
    })
    .fail(function(){
        $('#db_output').html('ERROR: table lookup failed');
        $('#db_status').html('');
    }).always(function(){
        attach_content_collapsed_toggle();
        $('#db_output').show();
    });
}

//--------------------------------------------------------------------------------

