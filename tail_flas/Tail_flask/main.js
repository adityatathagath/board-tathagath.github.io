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

    // Handle form submission for Excel upload
    $('#uploadForm').submit(function(event) {
        event.preventDefault(); // Prevent default form submission

        var formData = new FormData(this);

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
            url: '/process_excel',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
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

        // Define the colors based on BARCLAYS_COLOR_PALETTE from Python
        const NEGATIVE_COLOR_BG = '#ffe6e6'; // BARCLAYS_COLOR_PALETTE[6] - light red
        const POSITIVE_COLOR_BG = '#e6ffe6'; // BARCLAYS_COLOR_PALETTE[7] - light green
        const BLACK_TEXT = 'black'; // Explicitly set text color to black

        function changeCellStyle(params) {
            if (params.value < 0) {
                return { backgroundColor: NEGATIVE_COLOR_BG, color: BLACK_TEXT };
            } else if (params.value > 0) {
                return { backgroundColor: POSITIVE_COLOR_BG, color: BLACK_TEXT };
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
                filter: true, // Enable filters by default
                floatingFilter: true, // Show floating filters
            },
            // For enterprise features like row grouping, etc. (requires license)
            // enableEnterpriseModules: true,
        };

        var gridDiv = document.getElementById(containerId);
        if (gridDiv && gridDiv.__ag_grid_instance) {
            gridDiv.__ag_grid_instance.destroy(); // Destroy existing grid to re-render cleanly
        }
        new agGrid.Grid(gridDiv, gridOptions);
    }
});
