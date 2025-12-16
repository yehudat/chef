document.addEventListener('DOMContentLoaded', function() {
    // Handle tree item expansion
    document.querySelectorAll('.tree-header.expandable').forEach(function(header) {
        header.addEventListener('click', function() {
            this.parentElement.classList.toggle('expanded');
        });
    });

    // Handle nested field expansion
    document.querySelectorAll('.field-item.expandable').forEach(function(field) {
        field.addEventListener('click', function(e) {
            e.stopPropagation();
            this.classList.toggle('expanded');
        });
    });

    // Filter functionality
    var filterInput = document.getElementById('filter-input');
    var excludeCheckbox = document.getElementById('filter-exclude');
    var clearButton = document.getElementById('filter-clear');
    var statusText = document.getElementById('filter-status');

    if (!filterInput) return;

    function applyFilter() {
        var pattern = filterInput.value.trim();
        var exclude = excludeCheckbox.checked;
        var regex = null;

        // Clear error state
        filterInput.classList.remove('error');

        // Try to compile regex
        if (pattern) {
            try {
                regex = new RegExp(pattern, 'i');
            } catch (e) {
                filterInput.classList.add('error');
                statusText.textContent = 'Invalid regex';
                return;
            }
        }

        // Filter signal tree items
        var treeItems = document.querySelectorAll('.tree-item');
        var visibleSignals = 0;
        var totalSignals = treeItems.length;

        treeItems.forEach(function(item) {
            var header = item.querySelector('.tree-header');
            var name = header.querySelector('.signal-name').textContent;
            var type = header.querySelector('.signal-type').textContent;
            var direction = header.querySelector('.signal-direction').textContent;
            var searchText = name + ' ' + type + ' ' + direction;

            var matches = !regex || regex.test(searchText);
            var show = exclude ? !matches : matches;

            if (show) {
                item.classList.remove('hidden');
                visibleSignals++;
            } else {
                item.classList.add('hidden');
            }
        });

        // Filter parameter table rows
        var paramRows = document.querySelectorAll('.param-table tbody tr');
        var visibleParams = 0;
        var totalParams = paramRows.length;

        paramRows.forEach(function(row) {
            var cells = row.querySelectorAll('td');
            var searchText = Array.from(cells).map(function(c) { return c.textContent; }).join(' ');

            var matches = !regex || regex.test(searchText);
            var show = exclude ? !matches : matches;

            if (show) {
                row.classList.remove('hidden');
                visibleParams++;
            } else {
                row.classList.add('hidden');
            }
        });

        // Update status
        if (pattern) {
            var mode = exclude ? 'hiding' : 'showing';
            statusText.textContent = mode + ' ' + visibleSignals + '/' + totalSignals + ' signals, ' + visibleParams + '/' + totalParams + ' params';
        } else {
            statusText.textContent = totalSignals + ' signals, ' + totalParams + ' params';
        }
    }

    // Event listeners
    filterInput.addEventListener('input', applyFilter);
    excludeCheckbox.addEventListener('change', applyFilter);
    clearButton.addEventListener('click', function() {
        filterInput.value = '';
        excludeCheckbox.checked = false;
        applyFilter();
    });

    // Initial status
    applyFilter();
});
