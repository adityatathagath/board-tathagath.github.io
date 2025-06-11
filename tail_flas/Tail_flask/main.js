// static/js/main.js

$(document).ready(function() {
    // Show/hide debug output
    $('#debugModeCheckbox').change(function() {
        if ($(this).is(':checked')) {
            $('#debugOutput').show();
        } else {
            $('#debugOutput').hide();
        }
    });

    // Handle "Process Data" button click
    $('#processDataBtn').click(function() {
        // Clear previous messages and output
        $('#flashMessages').empty();
        $('#debugOutput').empty();
        $('#lowestDVarValue').text('Loading...');
        $('#lowestDVarDetails').text('');
        $('#lowestSVarValue').text('Loading...');
        $('#lowestSVarDetails').text('');
        renderAgGrid([]); // Clear grid
        renderAgGrid([], 'topNegativeTailsGrid'); // Clear grid for negative


        $.ajax({
            url: '/process_data', // Changed route from /process_excel
            type: 'POST',
            // No formData needed as file path is fixed on backend
            beforeSend: function() {
                // Show loading indicator
                $('#lowestDVarValue').text('Processing...');
                $('#lowestSVarValue').text('Processing...');
                // You might want a global spinner here
            },
            success: function(response) {
                if (response.success) {
                    $('#flashMessages').html('<div class="alert alert-success alert-dismissible fade show" role="alert">Data processed successfully!<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>');
                    
                    // Update key metrics cards
                    if (response.key_metrics && response.key_metrics.lowest_dvar) {
                        $('#lowestDVarValue').text(response.key_metrics.lowest_dvar.value);
                        $('#lowestDVarDetails').text('Date: ' + response.key_metrics.lowest_dvar.date + ', P&L Vector: ' + response.key_metrics.lowest_dvar.pnl_vector);
                    } else {
                        $('#lowestDVarValue').text('N/A');
                        $('#lowestDVarDetails').text('No data.');
                    }
                    if (response.key_metrics && response.key_metrics.lowest_svar) {
                        $('#lowestSVarValue').text(response.key_metrics.lowest_svar.value);
                        $('#lowestSVarDetails').text('Date: ' + response.key_metrics.lowest_svar.date + ', P&L Vector: ' + response.key_metrics.lowest_svar.pnl_vector);
                    } else {
                        $('#lowestSVarValue').text('N/A');
                        $('#lowestSVarDetails').text('No data.');
                    }

                    // Fetch and render top/bottom tails table
                    fetchTopBottomTails();
                    // Fetch and render DVaR trends plot
                    fetchDVaRTrendsPlot();

                } else {
                    $('#flashMessages').html('<div class="alert alert-danger alert-dismissible fade show" role="alert">Error processing data: ' + response.error + '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>');
                    $('#lowestDVarValue').text('Error');
                    $('#lowestSVarValue').text('Error');
                }
            },
            error: function(xhr, status, error) {
                var errorMessage = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : 'An unknown error occurred.';
                $('#flashMessages').html('<div class="alert alert-danger alert-dismissible fade show" role="alert">AJAX Error: ' + errorMessage + '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button></div>');
                $('#lowestDVarValue').text('Error');
                $('#lowestSVarValue').text('Error');
            },
            complete: function() {
                // Hide any global spinner
            }
        });
    });

    // Function to fetch and render Top/Bottom Tails table
    function fetchTopBottomTails() {
        $.ajax({
            url: '/get_top_bottom_tails',
            type: 'GET',
            success: function(response) {
                if (response.positive_tails && response.negative_tails) {
                    renderAgGrid(response.positive_tails, 'topPositiveTailsGrid');
                    renderAgGrid(response.negative_tails, 'topNegativeTailsGrid');
                } else {
                    $('#flashMessages').html('<div class="alert alert-warning" role="alert">No data for top/bottom tails.</div>');
                }
            },
            error: function(xhr, status, error) {
                var errorMessage = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : 'Failed to fetch top/bottom tails.';
                $('#flashMessages').html('<div class="alert alert-danger" role="alert">Error: ' + errorMessage + '</div>');
            }
        });
    }

    // Function to fetch and render DVaR Trends plot
    function fetchDVaRTrendsPlot() {
        $.ajax({
            url: '/get_dvar_trends_plot',
            type: 'GET',
            success: function(response) {
                if (response.doc) {
                    Bokeh.embed.embed_item(response, "dvar_trends_plot_div");
                } else {
                    $('#flashMessages').html('<div class="alert alert-warning" role="alert">No data for DVaR trends plot.</div>');
                }
            },
            error: function(xhr, status, error) {
                var errorMessage = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : 'Failed to fetch DVaR trends plot.';
                $('#flashMessages').html('<div class="alert alert-danger" role="alert">Error: ' + errorMessage + '</div>');
            }
        });
    }

    // ag-Grid rendering function
    function renderAgGrid(rowData, containerId = 'topPositiveTailsGrid') {
        var columnDefs = [
            { field: "Date", headerName: "Date", filter: 'agDateColumnFilter', sortable: true,
                cellRenderer: function(params) {
                    // Custom date formatting for display
                    if (params.value) {
                        const date = new Date(params.value);
                        const day = String(date.getDate()).padStart(2, '0');
                        const month = String(date.getMonth() + 1).padStart(2, '0'); // Month is 0-indexed
                        const year = date.getFullYear();
                        return `${day}-${month}-${year}`;
                    }
                    return '';
                }
            },
            { field: "Pnl_Vector_Name", headerName: "P&L Vector", sortable: true, filter: true },
            { field: "Macro_DVaR_Value_Current", headerName: "Macro Current", type: 'numericColumn', valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "Macro_DVaR_Value_Previous", headerName: "Macro Previous", type: 'numericColumn', valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "Macro_DVaR_Change", headerName: "Macro Change", type: 'numericColumn', cellStyle: changeCellStyle, valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "FX_DVaR_Value_Current", headerName: "FX Current", type: 'numericColumn', valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "FX_DVaR_Value_Previous", headerName: "FX Previous", type: 'numericColumn', valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "FX_DVaR_Change", headerName: "FX Change", type: 'numericColumn', cellStyle: changeCellStyle, valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "Rates_DVaR_Value_Current", headerName: "Rates Current", type: 'numericColumn', valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "Rates_DVaR_Value_Previous", headerName: "Rates Previous", type: 'numericColumn', valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "Rates_DVaR_Change", headerName: "Rates Change", type: 'numericColumn', cellStyle: changeCellStyle, valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "EM_Macro_DVaR_Value_Current", headerName: "EM Macro Current", type: 'numericColumn', valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "EM_Macro_DVaR_Value_Previous", headerName: "EM Macro Previous", type: 'numericColumn', valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
            { field: "EM_Macro_DVaR_Change", headerName: "EM Macro Change", type: 'numericColumn', cellStyle: changeCellStyle, valueFormatter: numberFormatter, sortable: true, filter: 'agNumberColumnFilter' },
        ];

        // Define the colors consistent with BARCLAYS_COLOR_PALETTE.
        // These need to match the CSS classes defined in style.css
        // Note: For JsCode directly in Python, you'd embed the hex codes.
        // For direct JS, we use class names and let CSS handle the colors.
        function changeCellStyle(params) {
            if (typeof params.value === 'number') {
                if (params.value < 0) {
                    return { className: 'negative-change' };
                } else if (params.value > 0) {
                    return { className: 'positive-change' };
                }
            }
            return null;
        }

        function numberFormatter(params) {
            if (typeof params.value === 'number') {
                return params.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            }
            return params.value;
        }

        var gridOptions = {
            columnDefs: columnDefs,
            rowData: rowData,
            domLayout: 'autoHeight',
            suppressColumnVirtualization: true,
            defaultColDef: {
                resizable: true,
                filter: true,
                floatingFilter: true,
            },
        };

        var gridDiv = document.getElementById(containerId);
        if (gridDiv && gridDiv.__ag_grid_instance) {
            gridDiv.__ag_grid_instance.destroy();
        }
        // Initialize grid on document ready or after content loaded
        new agGrid.Grid(gridDiv, gridOptions);
    }
});
