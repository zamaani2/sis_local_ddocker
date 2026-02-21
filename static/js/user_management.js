document.addEventListener('DOMContentLoaded', function () {
    // Handle select all checkbox
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            const userCheckboxes = document.querySelectorAll('.user-checkbox');
            userCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
        });
    }

    // Create user form submission
    const createUserForm = document.getElementById('createUserForm');
    if (createUserForm) {
        createUserForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(this);

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Append new user row
                        document.getElementById('userTableBody').insertAdjacentHTML('beforeend', data.html);

                        // Close modal and reset form
                        const modal = bootstrap.Modal.getInstance(document.getElementById('createUserModal'));
                        modal.hide();
                        createUserForm.reset();

                        // Show success message
                        showToast('Success', data.message, 'success');
                    } else {
                        showToast('Error', data.message, 'error');
                    }
                })
                .catch(error => console.error('Error:', error));
        });
    }

    // Edit user functionality
    document.addEventListener('click', function (e) {
        if (e.target.closest('.edit-user')) {
            const button = e.target.closest('.edit-user');
            const userId = button.dataset.id;
            const editModal = document.getElementById('editUserModal');
            const editUserContent = document.getElementById('editUserContent');

            // Show loading state
            editUserContent.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';

            // Initialize modal
            const modal = new bootstrap.Modal(editModal);
            modal.show();

            fetch(`/users/get/${userId}/`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.html) {
                        editUserContent.innerHTML = data.html;

                        // Initialize any form elements that need it
                        const editForm = editModal.querySelector('#updateUserForm');
                        if (editForm) {
                            // Re-initialize any select2 elements if present
                            $(editForm).find('select').select2({
                                dropdownParent: editModal
                            });

                            setupUpdateFormSubmission(editForm, userId, modal);
                        }
                    } else {
                        throw new Error('No form HTML received');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    editUserContent.innerHTML = `<div class="alert alert-danger">Error loading form: ${error.message}</div>`;
                });
        }
    });

    function setupUpdateFormSubmission(form, userId, modal) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const existingRow = document.getElementById(`user-row-${userId}`);
                        if (existingRow) {
                            existingRow.outerHTML = data.html;
                            modal.hide();
                        }
                        showToast('Success', data.message, 'success');
                    } else {
                        showToast('Error', data.message || 'Update failed', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Error', 'Failed to update user', 'error');
                });
        });
    }

    // Delete user functionality
    document.addEventListener('click', function (e) {
        if (e.target.closest('.delete-user')) {
            const button = e.target.closest('.delete-user');
            const userId = button.dataset.id;
            const userName = button.dataset.name;

            document.getElementById('deleteUserName').textContent = userName;

            document.getElementById('confirmDelete').onclick = function () {
                fetch(`/users/delete/${userId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // Remove the row
                            document.getElementById(`user-row-${userId}`).remove();

                            // Close modal
                            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteUserModal'));
                            modal.hide();

                            showToast('Success', data.message, 'success');
                        } else {
                            showToast('Error', data.message, 'error');
                        }
                    })
                    .catch(error => console.error('Error:', error));
            };
        }
    });

    // Clear individual filters
    document.querySelectorAll('.clear-filter').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const filterName = this.dataset.filter;
            const searchParams = new URLSearchParams(window.location.search);
            searchParams.delete(filterName);
            window.location.search = searchParams.toString();
        });
    });
});

// Helper function to get CSRF token
function getCookie(name) {
    let value = `; ${document.cookie}`;
    let parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// Add this function to handle form submission
function updateQueryString(form) {
    const formData = new FormData(form);
    const searchParams = new URLSearchParams(formData);
    const queryString = searchParams.toString();
    window.location.search = queryString;
    return false;
}

// Update the showToast function at the bottom of the file
function showToast(title, message, type = 'info') {
    // Configure toastr options
    toastr.options = {
        "closeButton": true,
        "debug": false,
        "newestOnTop": true,
        "progressBar": true,
        "positionClass": "toast-top-right",
        "preventDuplicates": false,
        "showDuration": "300",
        "hideDuration": "1000",
        "timeOut": "5000",
        "extendedTimeOut": "1000",
        "showEasing": "swing",
        "hideEasing": "linear",
        "showMethod": "fadeIn",
        "hideMethod": "fadeOut"
    };

    // Show toast based on type
    switch (type) {
        case 'success':
            toastr.success(message, title);
            break;
        case 'error':
            toastr.error(message, title);
            break;
        case 'warning':
            toastr.warning(message, title);
            break;
        default:
            toastr.info(message, title);
    }
}
