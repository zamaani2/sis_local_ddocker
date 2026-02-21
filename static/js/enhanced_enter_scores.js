// Note: handleTeacherFilterChange and updateAssignmentSelection are defined in the template
// for inline event handlers. They are not duplicated here.

// Remove any existing alerts on page load (wait for jQuery)
if (typeof $ !== 'undefined') {
    $('.ajax-alert').remove();
}

// Enhanced scoring validation and calculation
$(document).ready(function () {
    // Verify config object is available
    if (typeof window.enhancedScoresConfig === 'undefined') {
        console.error('Enhanced Scores Config not found! Make sure the config script is loaded before this file.');
        return;
    }

    // Scoring configuration from backend (loaded from config object)
    const scoringConfig = window.enhancedScoresConfig.scoringConfig;

    // Prevent any unwanted form submissions
    $('form').on('submit', function (e) {
        console.log('Form submission detected, preventing default');
        e.preventDefault();
        return false;
    });

    // Prevent Enter key from submitting forms
    $(document).on('keypress', 'input', function (e) {
        if (e.which === 13) { // Enter key
            e.preventDefault();
            return false;
        }
    });

    // Auto-save setting
    let autoSaveEnabled = false;

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Debug function to check table structure
    window.debugTable = function () {
        console.log('=== TABLE STRUCTURE DEBUG ===');
        $('tbody tr:first').find('td').each(function (index) {
            console.log(`Column ${index + 1} (index ${index}):`, $(this).html().substring(0, 50));
        });
    };

    // Call debug function on page load
    setTimeout(debugTable, 1000);

    // Real-time calculation for class score components
    $(document).on('input', '.individual-score, .class-test-score, .project-score, .group-work-score', function () {
        const row = $(this).closest('tr');
        calculateClassScore(row);
        calculateTotalScore(row);
        updateGradeAndRemarks(row);

        // Highlight changed row
        row.addClass('modified-row');
        setTimeout(() => row.removeClass('modified-row'), 2000);
    });

    // Real-time calculation for exam score
    $(document).on('input', '.exam-score', function () {
        console.log('Exam score input detected:', $(this).val());
        const row = $(this).closest('tr');

        // Prevent any form submission or page refresh
        event.stopPropagation();

        calculateTotalScore(row);
        updateGradeAndRemarks(row);

        // Highlight changed row
        row.addClass('modified-row');
        setTimeout(() => row.removeClass('modified-row'), 2000);

        console.log('Calculation completed for row');
    });

    // Ensure exam score fields remain editable
    $(document).on('focus', '.exam-score', function () {
        $(this).prop('readonly', false);
    });

    // Prevent exam score from becoming readonly
    $(document).on('click', '.exam-score', function () {
        $(this).prop('readonly', false);
        $(this).focus();
    });

    // Enhanced score validation with proper limits
    $(document).on('blur', '.score-input:not([readonly])', function () {
        const value = parseFloat($(this).val());
        const max = parseFloat($(this).attr('max'));
        const min = parseFloat($(this).attr('min'));

        // Clear previous validation states
        $(this).removeClass('is-invalid is-valid');

        if ($(this).val() !== '' && !isNaN(value)) {
            if (value > max || value < min) {
                $(this).addClass('is-invalid');
                showToast(`Score must be between ${min} and ${max}`, 'warning');
            } else {
                $(this).removeClass('is-invalid');
            }
        } else if ($(this).val() !== '' && isNaN(value)) {
            $(this).addClass('is-invalid');
            showToast('Please enter a valid number', 'error');
        }
    });

    // Calculate class score from components
    function calculateClassScore(row) {
        const individual = parseFloat(row.find('.individual-score').val()) || 0;
        const classTest = parseFloat(row.find('.class-test-score').val()) || 0;
        const project = parseFloat(row.find('.project-score').val()) || 0;
        const groupWork = parseFloat(row.find('.group-work-score').val()) || 0;

        // Calculate total actual score achieved by student
        const totalActualScore = individual + classTest + project + groupWork;

        // Calculate total maximum possible score
        const totalMaxPossibleScore = scoringConfig.individualMaxMark + scoringConfig.classTestMaxMark +
            scoringConfig.projectMaxMark + scoringConfig.groupWorkMaxMark;

        // If total max possible score is 0, return 0 to avoid division by zero
        if (totalMaxPossibleScore === 0) {
            const roundedScore = 0;
            row.find('.calculated-class-score').val(roundedScore.toFixed(2));
            row.find('.calculated-class-score-input').val(roundedScore);
            return roundedScore;
        }

        // Calculate the scaled class score
        // Formula: (total_actual_score / total_max_possible_score) × class_score_percentage
        const scaledScore = (totalActualScore / totalMaxPossibleScore) * scoringConfig.classScorePercentage;

        // Update display and hidden input
        const roundedScore = Math.round(scaledScore * 100) / 100;
        row.find('.calculated-class-score').val(roundedScore.toFixed(2));
        row.find('.calculated-class-score-input').val(roundedScore);

        return roundedScore;
    }


    // Calculate total score
    function calculateTotalScore(row) {
        const classScore = parseFloat(row.find('.calculated-class-score-input').val()) || 0;
        const examScore = parseFloat(row.find('.exam-score').val()) || 0;

        if (classScore > 0 || examScore > 0) {
            // Calculate scaled exam score
            const examScoreScaled = (examScore / 100) * scoringConfig.examScorePercentage;

            // Calculate total score
            const totalScore = classScore + examScoreScaled;

            const roundedTotal = Math.round(totalScore * 100) / 100;
            row.find('.total-score').val(roundedTotal.toFixed(2));
            row.find('.total-score-input').val(roundedTotal);

            return roundedTotal;
        } else {
            row.find('.total-score').val('--');
            row.find('.total-score-input').val('');
            return 0;
        }
    }

    // Update grade and remarks based on total score using grading system configuration
    function updateGradeAndRemarks(row) {
        const totalScore = parseFloat(row.find('.total-score-input').val());

        // Debug: Log the total score
        console.log('Updating grade for total score:', totalScore);

        if (!isNaN(totalScore) && totalScore > 0) {
            // Fetch grade and remarks from grading system configuration via API
            fetch(`/api/get-grading-info/?score=${totalScore}`)
                .then(response => response.json())
                .then(data => {
                    const grade = data.grade || '--';
                    const remarks = data.remarks || '--';

                    if (grade !== '--' && remarks !== '--') {
                        // Generate CSS classes based on grade
                        const gradeFirstChar = grade.charAt(0).toLowerCase();
                        const gradeClass = `grade-${gradeFirstChar}`;
                        const remarksClass = `remarks-${remarks.toLowerCase().replace(/\s+/g, "")}`;

                        // Update grade display (column 10)
                        const gradeCell = row.find('td').eq(9); // 0-based index, so column 10 is index 9
                        console.log('Updating grade cell:', gradeCell.length, 'with grade:', grade);
                        gradeCell.html(`
                            <div class="badge-grade ${gradeClass}">
                                ${grade}
                            </div>
                        `);
                        row.find('.grade').val(grade);

                        // Update remarks display (column 11)
                        const remarksCell = row.find('td').eq(10); // 0-based index, so column 11 is index 10
                        console.log('Updating remarks cell:', remarksCell.length, 'with remarks:', remarks);
                        remarksCell.html(`
                            <span class="remarks-badge ${remarksClass}">
                                ${remarks}
                            </span>
                        `);
                        row.find('.remarks').val(remarks);
                    } else {
                        // Clear grade and remarks if no valid grade found
                        row.find('td').eq(9).html('<span>--</span>'); // Grade column
                        row.find('.grade').val('');
                        row.find('td').eq(10).html('<span>--</span>'); // Remarks column
                        row.find('.remarks').val('');
                    }
                })
                .catch(error => {
                    console.error('Error fetching grade from grading system:', error);
                    // Fallback: Clear grade and remarks on error
                    row.find('td').eq(9).html('<span>--</span>'); // Grade column
                    row.find('.grade').val('');
                    row.find('td').eq(10).html('<span>--</span>'); // Remarks column
                    row.find('.remarks').val('');
                });
        } else {
            // Clear grade and remarks
            row.find('td').eq(9).html('<span>--</span>'); // Grade column
            row.find('.grade').val('');
            row.find('td').eq(10).html('<span>--</span>'); // Remarks column
            row.find('.remarks').val('');
        }

        // Calculate positions after all scores are updated
        calculatePositions();
    }

    // Calculate and update positions for all students
    function calculatePositions() {
        // Get all rows with total scores
        const rows = [];
        $('tbody tr').each(function () {
            const row = $(this);
            const totalScore = parseFloat(row.find('.total-score-input').val());
            if (!isNaN(totalScore) && totalScore > 0) {
                rows.push({
                    row: row,
                    score: totalScore
                });
            }
        });

        // Sort by score (highest first)
        rows.sort((a, b) => b.score - a.score);

        // Assign positions
        rows.forEach((item, index) => {
            const position = index + 1;
            const positionCell = item.row.find('td').eq(11); // 0-based index, so column 12 is index 11

            let positionClass;
            if (position === 1) {
                positionClass = 'position-1';
            } else if (position === 2) {
                positionClass = 'position-2';
            } else if (position === 3) {
                positionClass = 'position-3';
            } else {
                positionClass = 'position-other';
            }

            positionCell.html(`
                    <div class="position-badge ${positionClass}">
                        ${position}
                    </div>
                `);
            item.row.find('.position').val(position);
        });

        // Clear positions for students without scores
        $('tbody tr').each(function () {
            const row = $(this);
            const totalScore = parseFloat(row.find('.total-score-input').val());
            if (isNaN(totalScore) || totalScore <= 0) {
                row.find('td').eq(11).html('<span>--</span>'); // Position column
                row.find('.position').val('');
            }
        });
    }

    // Auto-save functionality
    $('#enableAutoSave').change(function () {
        autoSaveEnabled = $(this).is(':checked');
    });

    let autoSaveTimeout;
    $(document).on('input', '.score-input:not([readonly])', function () {
        // Disable auto-save for now to prevent conflicts
        console.log('Input detected on:', $(this).attr('class'));
        return;

        if (!autoSaveEnabled) return;

        const row = $(this).closest('tr');
        clearTimeout(autoSaveTimeout);
        autoSaveTimeout = setTimeout(() => {
            row.addClass('saved-row');
            setTimeout(() => row.removeClass('saved-row'), 1500);
        }, 2000);
    });

    // Manual form submission handler
    $(document).on('click', 'button[type="submit"]', function (e) {
        e.preventDefault();
        console.log('Manual save button clicked');

        Swal.fire({
            title: 'Save All Scores?',
            text: 'This will save scores for all students in this class.',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Yes, save all',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                const form = $('#enhancedScoreForm')[0];
                const formData = new FormData(form);

                // Show loading
                Swal.fire({
                    title: 'Saving...',
                    text: 'Please wait while we save all scores.',
                    allowOutsideClick: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });

                $.ajax({
                    url: window.location.href,
                    method: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: function (response) {
                        Swal.fire({
                            title: 'Success!',
                            text: 'All scores have been saved successfully.',
                            icon: 'success',
                            timer: 2000,
                            showConfirmButton: false
                        });

                        // Add animation to all rows
                        $('tbody tr').addClass('saved-row');
                        setTimeout(() => $('tbody tr').removeClass('saved-row'), 1500);
                    },
                    error: function (xhr) {
                        Swal.fire({
                            title: 'Error!',
                            text: 'There was an error saving the scores: ' + xhr.responseText,
                            icon: 'error'
                        });
                    }
                });
            }
        });
    });

    // Reset form function
    window.resetForm = function () {
        Swal.fire({
            title: 'Confirm Reset',
            text: 'Are you sure you want to reset all entered scores?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, reset all',
            confirmButtonColor: '#dc3545',
            cancelButtonText: 'Cancel'
        }).then((result) => {
            if (result.isConfirmed) {
                $('.individual-score, .class-test-score, .project-score, .group-work-score, .exam-score').val('');
                $('.calculated-class-score, .total-score').val('--');
                $('.calculated-class-score-input, .total-score-input, .grade, .remarks, .position').val('');

                // Clear grade, remarks, and position columns using correct selectors
                $('tbody tr').each(function () {
                    const row = $(this);
                    row.find('td').eq(9).html('<span>--</span>'); // Grade column
                    row.find('td').eq(10).html('<span>--</span>'); // Remarks column
                    row.find('td').eq(11).html('<span>--</span>'); // Position column
                });

                Swal.fire({
                    icon: 'success',
                    title: 'Form has been reset',
                    timer: 2000,
                    showConfirmButton: false
                });
            }
        });
    };

    // Toast notification system
    function showToast(message, type = 'info') {
        const toastHtml = `
                <div class="toast-modern toast-${type}" role="alert">
                <div class="d-flex align-items-center">
                    <div class="me-2">
                            ${type === 'success' ? '<i class="fas fa-check-circle text-success"></i>' :
                type === 'error' ? '<i class="fas fa-exclamation-circle text-danger"></i>' :
                    type === 'warning' ? '<i class="fas fa-exclamation-triangle text-warning"></i>' :
                        '<i class="fas fa-info-circle text-info"></i>'}
                    </div>
                    <div class="flex-grow-1">${message}</div>
                    <button type="button" class="btn-close btn-sm ms-2" onclick="$(this).closest('.toast-modern').remove()"></button>
                </div>
            </div>
        `;

        $('#toastContainer').append(toastHtml);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            $('#toastContainer .toast-modern:first').remove();
        }, 5000);
    }

    // Batch operations button
    $('#batchProcess').on('click', function () {
        $('#batchProcessModal').modal('show');
    });

    // Import/Export Tools functionality
    $('#toolsQuickAccess').on('click', function () {
        // Toggle the import/export tools section
        const importExportTools = document.getElementById('importExportTools');
        if (importExportTools) {
            const bsCollapse = new bootstrap.Collapse(importExportTools, {
                toggle: true
            });
        }
    });

    // Shared function to handle single class export
    function handleSingleExport() {
        const assignmentId = new URLSearchParams(window.location.search).get("assignment_id") || $('#assignment').val();

        if (!assignmentId) {
            Swal.fire({
                icon: 'warning',
                title: 'No Class Selected',
                text: 'Please select a class from the dropdown above before exporting a single class.',
                confirmButtonText: 'OK'
            });
            return;
        }

        // Single class enhanced export - preserve teacher filter if present
        let exportUrl = window.enhancedScoresConfig.urls.exportSingle + "?assignment_id=" + assignmentId;
        const teacherId = new URLSearchParams(window.location.search).get("teacher_id");
        if (teacherId) {
            exportUrl += "&teacher_id=" + teacherId;
        }
        window.location.href = exportUrl;
    }

    // Shared function to handle single class import
    function handleSingleImport() {
        const assignmentId = new URLSearchParams(window.location.search).get("assignment_id") || $('#assignment').val();

        if (!assignmentId) {
            Swal.fire({
                icon: 'warning',
                title: 'No Class Selected',
                text: 'Please select a class from the dropdown above before importing scores for a single class.',
                confirmButtonText: 'OK'
            });
            return;
        }

        // Single class import
        showSingleClassImportDialog(assignmentId);
    }

    // Enhanced Export functionality - Single Class (from Import/Export Tools section)
    $('#exportScoresSingle').on('click', handleSingleExport);

    // Enhanced Export functionality - Batch (from Import/Export Tools section)
    $('#exportScoresBatch').on('click', function () {
        // Show class selection dialog for batch enhanced export
        showEnhancedBatchExportDialog();
    });

    // Quick Export buttons from class selection card
    $('#quickExportSingle').on('click', handleSingleExport);
    $('#quickExportBatch').on('click', function () {
        showEnhancedBatchExportDialog();
    });

    // Enhanced Batch Export Dialog Function
    function showEnhancedBatchExportDialog() {
        // Show loading state while fetching data
        Swal.fire({
            title: "Loading Classes",
            html: "Fetching your class assignments...",
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            },
        });

        // Fetch the assignments - respect teacher filter for admins
        let apiUrl = "/api/teacher-assignments/";
        const teacherId = new URLSearchParams(window.location.search).get("teacher_id");
        const userRole = window.enhancedScoresConfig.userRole;
        if (userRole === 'admin' && teacherId) {
            apiUrl += "?teacher_id=" + teacherId;
        }

        fetch(apiUrl, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": getCookie("csrftoken"),
            },
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then((data) => {
                Swal.close();

                // Check if the API returned an error
                if (!data.success) {
                    console.error("API Error:", data.error);
                    Swal.fire({
                        icon: "error",
                        title: "Error Loading Classes",
                        text: data.error || "Could not load your class assignments. Please try again or contact support if the problem persists.",
                    });
                    return;
                }

                if (!data.assignments || data.assignments.length === 0) {
                    console.log("No assignments found");
                    const userRole = window.enhancedScoresConfig.userRole;
                    const errorText = userRole === 'admin'
                        ? "No class assignments found for the current academic year in your school."
                        : "You don't have any classes assigned to you for the current academic year.";
                    Swal.fire({
                        icon: "info",
                        title: "No Classes Found",
                        text: errorText,
                    });
                    return;
                }

                console.log("Assignments found:", data.assignments.length);

                // Group assignments by class
                const classesByForm = {};
                data.assignments.forEach((assignment) => {
                    const className = assignment.class_name;
                    if (!classesByForm[className]) {
                        classesByForm[className] = [];
                    }
                    classesByForm[className].push(assignment);
                });

                // Create HTML for the multi-select dialog
                let html = `<div class="text-start">
                <p>Select the classes you want to export enhanced score templates for:</p>
                <div style="max-height: 300px; overflow-y: auto;">`;

                // Add classes grouped by class name
                Object.keys(classesByForm).forEach((className) => {
                    html += `<h6 class="mt-3 text-primary">${className}</h6>`;
                    classesByForm[className].forEach((assignment) => {
                        const teacherInfo = assignment.teacher_name ? ` <small class="text-muted">(${assignment.teacher_name})</small>` : '';
                        html += `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="${assignment.id}" id="assignment_${assignment.id}">
                            <label class="form-check-label" for="assignment_${assignment.id}">
                                ${assignment.class_name} - ${assignment.subject}${teacherInfo}
                            </label>
                        </div>`;
                    });
                });

                html += `</div></div>`;

                // Show the multi-select dialog
                Swal.fire({
                    title: "Export Enhanced Score Templates",
                    html: html,
                    showCancelButton: true,
                    confirmButtonText: "Export Selected",
                    cancelButtonText: "Cancel",
                    width: '600px',
                    preConfirm: () => {
                        const selectedIds = [];
                        document.querySelectorAll(".form-check-input:checked").forEach((checkbox) => {
                            selectedIds.push(checkbox.value);
                        });

                        if (selectedIds.length === 0) {
                            Swal.showValidationMessage("Please select at least one class");
                            return false;
                        }

                        return selectedIds;
                    },
                }).then((result) => {
                    if (result.isConfirmed && result.value) {
                        // Show loading state
                        Swal.fire({
                            title: "Preparing Enhanced Export",
                            html: "Creating Excel file with enhanced score templates...",
                            timer: 3000,
                            timerProgressBar: true,
                            allowOutsideClick: false,
                            didOpen: () => {
                                Swal.showLoading();

                                // Use iframe for more reliable download
                                setTimeout(() => {
                                    // Create an iframe for download to avoid browser popup blockers
                                    let batchExportUrl = `${window.enhancedScoresConfig.urls.exportBatch}?assignment_ids=${result.value.join(",")}`;
                                    // Preserve teacher filter if present
                                    const teacherId = new URLSearchParams(window.location.search).get("teacher_id");
                                    if (teacherId) {
                                        batchExportUrl += "&teacher_id=" + teacherId;
                                    }
                                    const iframe = document.createElement('iframe');
                                    iframe.style.display = 'none';
                                    iframe.src = batchExportUrl;
                                    document.body.appendChild(iframe);

                                    // Set a timeout to remove the iframe after download starts
                                    setTimeout(() => {
                                        document.body.removeChild(iframe);
                                    }, 5000);
                                }, 500);
                            },
                            didClose: () => {
                                // Show success message after timer
                                Swal.fire({
                                    icon: "success",
                                    title: "Export Complete",
                                    text: "Your enhanced score templates should begin downloading. If not, please check your browser settings.",
                                    timer: 3000,
                                    timerProgressBar: true,
                                });
                            }
                        });
                    }
                });
            })
            .catch((error) => {
                console.error("Error fetching assignments:", error);
                Swal.fire({
                    icon: "error",
                    title: "Error Loading Classes",
                    text: "Could not load your class assignments. Please try again or contact support if the problem persists.",
                });
            });
    }

    // Function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            const cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Enhanced Import functionality - Single Class (from Import/Export Tools section)
    $('#importScoresSingle').on('click', function (e) {
        e.preventDefault();
        handleSingleImport();
    });

    // Enhanced Import functionality - Batch (from Import/Export Tools section)
    $('#importScoresBatch').on('click', function (e) {
        e.preventDefault();
        // Always show batch import dialog
        showEnhancedBatchImportDialog();
    });

    // Quick Import buttons from class selection card
    $('#quickImportSingle').on('click', function (e) {
        e.preventDefault();
        handleSingleImport();
    });
    $('#quickImportBatch').on('click', function (e) {
        e.preventDefault();
        showEnhancedBatchImportDialog();
    });

    // Quick Import buttons from class selection card
    $('#quickImportSingle').on('click', function (e) {
        e.preventDefault();
        handleSingleImport();
    });
    $('#quickImportBatch').on('click', function (e) {
        e.preventDefault();
        showEnhancedBatchImportDialog();
    });

    // Single class import dialog
    function showSingleClassImportDialog(assignmentId) {
        Swal.fire({
            title: 'Import Enhanced Scores for This Class',
            html: `
                <div class="text-start mb-3">
                    <p>Upload an Excel file with enhanced scores for this class.</p>
                    <p class="text-muted small">The file should contain individual score components (Individual Score, Class Test Score, Project Score, Group Work Score, Exam Score).</p>
                </div>
            `,
            input: 'file',
            inputAttributes: {
                accept: '.xlsx,.xls',
                'aria-label': 'Upload Excel file'
            },
            showCancelButton: true,
            confirmButtonText: 'Upload',
            cancelButtonText: 'Cancel',
            showLoaderOnConfirm: true,
            preConfirm: (file) => {
                if (!file) {
                    Swal.showValidationMessage('Please select a file');
                    return false;
                }
                if (!file.name.match(/\.(xlsx|xls)$/i)) {
                    Swal.showValidationMessage('Please select a valid Excel file');
                    return false;
                }
                return file;
            },
        }).then((result) => {
            if (result.isConfirmed && result.value) {
                const file = result.value;
                uploadEnhancedSingleFile(file, assignmentId);
            }
        });
    }

    // Batch import dialog
    function showEnhancedBatchImportDialog() {
        Swal.fire({
            title: 'Import Enhanced Scores (Multiple Classes)',
            html: `
                <div class="text-start mb-3">
                    <p>Upload an Excel file with multiple sheets for different classes.</p>
                    <p class="text-muted small">Each sheet should contain enhanced scores with individual score components.</p>
                </div>
            `,
            input: 'file',
            inputAttributes: {
                accept: '.xlsx,.xls',
                'aria-label': 'Upload Excel file'
            },
            showCancelButton: true,
            confirmButtonText: 'Upload',
            cancelButtonText: 'Cancel',
            showLoaderOnConfirm: true,
            preConfirm: (file) => {
                if (!file) {
                    Swal.showValidationMessage('Please select a file');
                    return false;
                }
                if (!file.name.match(/\.(xlsx|xls)$/i)) {
                    Swal.showValidationMessage('Please select a valid Excel file');
                    return false;
                }
                return file;
            },
        }).then((result) => {
            if (result.isConfirmed && result.value) {
                const file = result.value;
                uploadEnhancedBatchFile(file);
            }
        });
    }

    // Handle file upload for batch import
    function uploadEnhancedBatchFile(file) {
        // Show progress
        Swal.fire({
            title: "Uploading...",
            html: `
                <div class="progress mb-3">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
                </div>
                <div id="upload-status">Preparing upload...</div>
            `,
            showConfirmButton: false,
            allowOutsideClick: false,
            allowEscapeKey: false,
            didOpen: () => {
                const progressBar = Swal.getPopup().querySelector(".progress-bar");
                const statusText = Swal.getPopup().querySelector("#upload-status");

                // Create FormData
                const formData = new FormData();
                formData.append("batchFile", file);
                formData.append("csrfmiddlewaretoken", getCookie("csrftoken"));

                // Create XHR
                const xhr = new XMLHttpRequest();

                // Track upload progress
                xhr.upload.addEventListener("progress", (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        progressBar.style.width = percentComplete + "%";
                        statusText.textContent = `Uploading: ${Math.round(percentComplete)}%`;
                    }
                });

                xhr.addEventListener("load", () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            if (response.success) {
                                Swal.fire({
                                    icon: "success",
                                    title: "Import Successful",
                                    html: `
                                        <div class="text-start">
                                            <p>Successfully imported enhanced scores for ${response.total_updated} students across ${response.results.length} classes.</p>
                                            ${response.results.map(r => `<div class="mb-1"><strong>${r.class_name} - ${r.subject_name}:</strong> ${r.processed} students</div>`).join('')}
                                        </div>
                                    `,
                                }).then(() => {
                                    window.location.reload();
                                });
                            } else {
                                Swal.fire({
                                    icon: "error",
                                    title: "Import Failed",
                                    html: `
                                        <div class="text-start">
                                            <p>${response.error || "An error occurred during import."}</p>
                                            ${response.error_messages && response.error_messages.length ?
                                            `<p>Details:</p>
                                                <ul class="text-danger">
                                                    ${response.error_messages.map(err => `<li>${err}</li>`).join('')}
                                                </ul>` : ''}
                                        </div>
                                    `,
                                });
                            }
                        } catch (e) {
                            // If not JSON, it might be an HTML response (e.g., redirect)
                            if (xhr.status >= 200 && xhr.status < 300) {
                                Swal.fire({
                                    icon: "success",
                                    title: "Import Successful",
                                    text: "Enhanced scores were imported successfully.",
                                }).then(() => {
                                    window.location.reload();
                                });
                            } else {
                                Swal.fire({
                                    icon: "error",
                                    title: "Import Failed",
                                    text: "An error occurred during import.",
                                });
                            }
                        }
                    } else {
                        Swal.fire({
                            icon: "error",
                            title: "Upload Failed",
                            text: "A network error occurred. Please try again.",
                        });
                    }
                });

                xhr.addEventListener("error", () => {
                    Swal.fire({
                        icon: "error",
                        title: "Upload Failed",
                        text: "A network error occurred. Please try again.",
                    });
                });

                xhr.open("POST", window.enhancedScoresConfig.urls.importBatch, true);
                xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
                xhr.send(formData);
            }
        });
    }

    // Handle file upload for single class import
    function uploadEnhancedSingleFile(file, assignmentId) {
        // Show progress
        Swal.fire({
            title: "Uploading...",
            html: `
                <div class="progress mb-3">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
                </div>
                <div id="upload-status">Preparing upload...</div>
            `,
            showConfirmButton: false,
            allowOutsideClick: false,
            allowEscapeKey: false,
            didOpen: () => {
                const progressBar = Swal.getPopup().querySelector(".progress-bar");
                const statusText = Swal.getPopup().querySelector("#upload-status");

                // Create FormData
                const formData = new FormData();
                formData.append("scoreFile", file);
                formData.append("assignment_id", assignmentId);
                formData.append("csrfmiddlewaretoken", getCookie("csrftoken"));

                // Create XHR
                const xhr = new XMLHttpRequest();

                // Track upload progress
                xhr.upload.addEventListener("progress", (e) => {
                    if (e.lengthComputable) {
                        const percentComplete = (e.loaded / e.total) * 100;
                        progressBar.style.width = percentComplete + "%";
                        statusText.textContent = `Uploading: ${Math.round(percentComplete)}%`;
                    }
                });

                xhr.addEventListener("load", () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            if (response.success) {
                                Swal.fire({
                                    icon: "success",
                                    title: "Import Successful",
                                    text: `Successfully imported enhanced scores for ${response.updated_count} students.`,
                                }).then(() => {
                                    window.location.reload();
                                });
                            } else {
                                let errorDetails = '';
                                if (response.error_messages && response.error_messages.length) {
                                    errorDetails = `<br><br><strong>Details:</strong><ul>${response.error_messages.map(err => `<li>${err}</li>`).join('')}</ul>`;
                                }
                                Swal.fire({
                                    icon: "error",
                                    title: "Import Failed",
                                    html: `${response.error || "Error importing file"}${errorDetails}`,
                                });
                            }
                        } catch (e) {
                            // If not JSON, it might be an HTML response (e.g., redirect)
                            if (xhr.status >= 200 && xhr.status < 300) {
                                Swal.fire({
                                    icon: "success",
                                    title: "Import Successful",
                                    text: "Enhanced scores were imported successfully.",
                                }).then(() => {
                                    window.location.reload();
                                });
                                return;
                            } else {
                                Swal.fire({
                                    icon: "error",
                                    title: "Import Failed",
                                    text: "An error occurred during import.",
                                });
                            }
                        }
                    } else {
                        Swal.fire({
                            icon: "error",
                            title: "Upload Failed",
                            text: "A network error occurred. Please try again.",
                        });
                    }
                });

                xhr.addEventListener("error", () => {
                    Swal.fire({
                        icon: "error",
                        title: "Upload Failed",
                        text: "A network error occurred. Please try again.",
                    });
                });

                xhr.open("POST", window.enhancedScoresConfig.urls.importSingle, true);
                xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
                xhr.send(formData);
            }
        });
    }

    // Batch operations implementation
    window.applyBatchOperation = function (operation) {
        // Close the modal
        const batchModal = bootstrap.Modal.getInstance(document.getElementById('batchProcessModal'));
        batchModal.hide();

        // Perform operation
        switch (operation) {
            case 'fillZeros':
                Swal.fire({
                    title: 'Confirm Action',
                    text: 'Are you sure you want to fill all empty scores with zeros?',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonText: 'Yes, fill with zeros',
                    cancelButtonText: 'Cancel'
                }).then((result) => {
                    if (result.isConfirmed) {
                        const emptyInputs = document.querySelectorAll('.individual-score:not(:disabled):not([readonly]), .class-test-score:not(:disabled):not([readonly]), .project-score:not(:disabled):not([readonly]), .group-work-score:not(:disabled):not([readonly]), .exam-score:not(:disabled):not([readonly])');
                        emptyInputs.forEach(input => {
                            if (input.value === '') {
                                input.value = '0';
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                            }
                        });
                        Swal.fire({
                            icon: 'success',
                            title: 'Empty scores filled with zeros',
                            timer: 2000,
                            showConfirmButton: false
                        });
                    }
                });
                break;

            case 'clearAll':
                Swal.fire({
                    title: 'Confirm Reset',
                    text: 'Are you sure you want to clear all scores? This action cannot be undone.',
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonText: 'Yes, clear all',
                    confirmButtonColor: '#dc3545',
                    cancelButtonText: 'Cancel'
                }).then((result) => {
                    if (result.isConfirmed) {
                        resetForm();
                    }
                });
                break;

            case 'calculateMissing':
                // Find all rows with at least one score entered
                const rows = document.querySelectorAll('tbody tr');
                let updatedCount = 0;

                rows.forEach(row => {
                    const individualScore = row.querySelector('.individual-score');
                    const examScore = row.querySelector('.exam-score');

                    if ((individualScore.value || examScore.value) &&
                        (row.querySelector('.total-score').value === '--' || !row.querySelector('.grade').value)) {
                        // Trigger recalculation
                        individualScore.dispatchEvent(new Event('input', { bubbles: true }));
                        updatedCount++;
                    }
                });

                Swal.fire({
                    icon: 'success',
                    title: `Updated ${updatedCount} student records`,
                    timer: 2000,
                    showConfirmButton: false
                });
                break;
        }
    };

    // Initialize the import/export tools collapse
    const importExportTools = document.getElementById('importExportTools');
    const toolsHeader = document.querySelector('[data-bs-target="#importExportTools"]');

    if (importExportTools && toolsHeader) {
        // Create a Bootstrap collapse instance for the import/export tools
        const collapse = new bootstrap.Collapse(importExportTools, {
            toggle: false // Don't toggle on initialization
        });

        // Add click event to the header
        toolsHeader.addEventListener('click', function (e) {
            e.preventDefault();
            collapse.toggle();
        });

        // Listen for Bootstrap collapse events
        importExportTools.addEventListener('show.bs.collapse', function () {
            toolsHeader.setAttribute('aria-expanded', 'true');
        });

        importExportTools.addEventListener('hide.bs.collapse', function () {
            toolsHeader.setAttribute('aria-expanded', 'false');
        });
    }

    // Keyboard shortcuts
    $(document).on('keydown', function (e) {
        // Ctrl+S to save
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            $('#enhancedScoreForm').submit();
        }

        // Ctrl+R to reset (with confirmation)
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            resetForm();
        }
    });

    // Calculate initial values for existing scores
    $('tbody tr').each(function () {
        const row = $(this);
        if (row.find('.individual-score').val() || row.find('.class-test-score').val() ||
            row.find('.project-score').val() || row.find('.group-work-score').val()) {
            calculateClassScore(row);
        }
        if (row.find('.individual-score').val() || row.find('.class-test-score').val() ||
            row.find('.project-score').val() || row.find('.group-work-score').val() ||
            row.find('.exam-score').val()) {
            calculateTotalScore(row);
            updateGradeAndRemarks(row);
        }
    });

    // Mobile-specific functionality
    let currentMobileSection = 'scores';

    // Mobile section navigation
    window.showMobileSection = function (section) {
        // Update active nav button
        $('.mobile-nav-btn').removeClass('active');
        $(`.mobile-nav-btn[onclick="showMobileSection('${section}')"]`).addClass('active');

        // Hide all sections
        $('.mobile-table-container, .mobile-search, .mobile-tools, .mobile-stats').hide();

        // Show selected section
        switch (section) {
            case 'scores':
                $('.mobile-table-container').show();
                break;
            case 'search':
                $('.mobile-search').show();
                $('#mobileStudentSearch').focus();
                break;
            case 'tools':
                $('.mobile-tools').show();
                break;
            case 'stats':
                $('.mobile-stats').show();
                break;
        }

        currentMobileSection = section;
    };

    // Mobile search functionality
    $('#mobileSearchBtn').on('click', function () {
        performMobileSearch();
    });

    $('#mobileClearSearchBtn').on('click', function () {
        $('#mobileStudentSearch').val('');
        performMobileSearch();
        $('#mobileStudentSearch').focus();
    });

    $('#mobileStudentSearch').on('keypress', function (e) {
        if (e.which === 13) { // Enter key
            e.preventDefault();
            performMobileSearch();
        }
    });

    function performMobileSearch() {
        const searchTerm = $('#mobileStudentSearch').val().toLowerCase().trim();
        const cards = $('.mobile-student-card');
        let visibleCount = 0;

        cards.each(function () {
            const card = $(this);
            const studentName = card.find('.mobile-student-name').text().toLowerCase();
            const studentId = card.find('.mobile-student-id').text().toLowerCase();

            if (searchTerm === '' ||
                studentName.includes(searchTerm) ||
                studentId.includes(searchTerm)) {
                card.show();
                visibleCount++;
            } else {
                card.hide();
            }
        });

        // Show search results count
        const totalStudents = cards.length;
        if (searchTerm === '') {
            showToast(`Showing all ${totalStudents} students`);
        } else {
            showToast(`Found ${visibleCount} of ${totalStudents} students`);
        }
    }

    // Mobile batch operations
    window.showMobileBatchModal = function () {
        Swal.fire({
            title: 'Batch Operations',
            html: `
                <div class="list-group">
                    <button type="button" class="list-group-item list-group-item-action" onclick="applyBatchOperation('fillZeros')">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">Fill Empty Scores with Zeros</h6>
                            <small class="text-primary">Apply</small>
                        </div>
                        <p class="mb-1 small text-muted">Sets all empty scores to 0 for all component scores.</p>
                    </button>
                    <button type="button" class="list-group-item list-group-item-action" onclick="applyBatchOperation('clearAll')">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">Clear All Scores</h6>
                            <small class="text-danger">Apply</small>
                        </div>
                        <p class="mb-1 small text-muted">Remove all entered scores for this class and subject.</p>
                    </button>
                    <button type="button" class="list-group-item list-group-item-action" onclick="applyBatchOperation('calculateMissing')">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">Calculate Missing Values</h6>
                            <small class="text-primary">Apply</small>
                        </div>
                        <p class="mb-1 small text-muted">Auto-calculate grades and remarks for all students with scores.</p>
                    </button>
                </div>
            `,
            showConfirmButton: false,
            showCancelButton: true,
            cancelButtonText: 'Close',
            width: '90%',
            maxWidth: '500px'
        });
    };

    // Mobile import/export
    window.showMobileImportExport = function () {
        Swal.fire({
            title: 'Import/Export Tools',
            html: `
                <div class="d-grid gap-2">
                    <button class="btn btn-primary" onclick="exportMobileScores()">
                        <i class="bi bi-download me-2"></i>Export Scores
                    </button>
                    <button class="btn btn-success" onclick="importMobileScores()">
                        <i class="bi bi-upload me-2"></i>Import Scores
                    </button>
                </div>
            `,
            showConfirmButton: false,
            showCancelButton: true,
            cancelButtonText: 'Close',
            width: '90%',
            maxWidth: '400px'
        });
    };

    // Mobile help
    window.showMobileHelp = function () {
        Swal.fire({
            title: 'Mobile Help',
            html: `
                <div class="text-start">
                    <h6>How to use on mobile:</h6>
                    <ul class="list-unstyled">
                        <li><i class="bi bi-check-circle text-success me-2"></i>Tap score inputs to enter values</li>
                        <li><i class="bi bi-check-circle text-success me-2"></i>Scores auto-calculate as you type</li>
                        <li><i class="bi bi-check-circle text-success me-2"></i>Use search to find students quickly</li>
                        <li><i class="bi bi-check-circle text-success me-2"></i>Tap Save to save all changes</li>
                        <li><i class="bi bi-check-circle text-success me-2"></i>Use Tools for batch operations</li>
                    </ul>
                    <h6>Touch Tips:</h6>
                    <ul class="list-unstyled">
                        <li><i class="bi bi-lightbulb text-warning me-2"></i>Tap and hold for context menus</li>
                        <li><i class="bi bi-lightbulb text-warning me-2"></i>Pinch to zoom if needed</li>
                        <li><i class="bi bi-lightbulb text-warning me-2"></i>Rotate device for landscape mode</li>
                    </ul>
                </div>
            `,
            showConfirmButton: false,
            showCancelButton: true,
            cancelButtonText: 'Got it!',
            width: '90%',
            maxWidth: '500px'
        });
    };

    // Mobile export function
    function exportMobileScores() {
        Swal.close();
        console.log('Mobile export clicked');

        // Show dialog to choose single or batch
        Swal.fire({
            title: "Export Scores",
            html: "Choose export type:",
            icon: "question",
            showCancelButton: true,
            confirmButtonText: "Single Class",
            cancelButtonText: "Multiple Classes (Batch)",
            showCloseButton: true,
            cancelButtonColor: "#3085d6",
        }).then((result) => {
            const assignmentId = new URLSearchParams(window.location.search).get("assignment_id") || $('#assignment').val();

            if (result.isConfirmed) {
                // Single class export
                if (!assignmentId) {
                    Swal.fire({
                        icon: 'warning',
                        title: 'No Class Selected',
                        text: 'Please select a class before exporting.',
                        confirmButtonText: 'OK'
                    });
                    return;
                }
                console.log('Triggering single class export for assignment:', assignmentId);
                window.location.href = window.enhancedScoresConfig.urls.exportSingle + "?assignment_id=" + assignmentId;
            } else if (result.dismiss === Swal.DismissReason.cancel) {
                // Batch export
                console.log('Triggering batch export');
                showEnhancedBatchExportDialog();
            }
        });
    }

    // Mobile import function
    function importMobileScores() {
        Swal.close();
        console.log('Mobile import clicked');

        // Show dialog to choose single or batch
        Swal.fire({
            title: "Import Scores",
            html: "Choose import type:",
            icon: "question",
            showCancelButton: true,
            confirmButtonText: "Single Class",
            cancelButtonText: "Multiple Classes (Batch)",
            showCloseButton: true,
            cancelButtonColor: "#3085d6",
        }).then((result) => {
            const assignmentId = new URLSearchParams(window.location.search).get("assignment_id") || $('#assignment').val();

            if (result.isConfirmed) {
                // Single class import
                if (!assignmentId) {
                    Swal.fire({
                        icon: 'warning',
                        title: 'No Class Selected',
                        text: 'Please select a class before importing.',
                        confirmButtonText: 'OK'
                    });
                    return;
                }
                console.log('Triggering single class import for assignment:', assignmentId);
                showSingleClassImportDialog(assignmentId);
            } else if (result.dismiss === Swal.DismissReason.cancel) {
                // Batch import
                console.log('Triggering batch import');
                showEnhancedBatchImportDialog();
            }
        });
    }

    // Mobile save function
    window.saveAllScores = function () {
        console.log('Mobile save clicked');

        // Show confirmation dialog
        Swal.fire({
            title: 'Save All Scores?',
            text: 'This will save scores for all students in this class.',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Yes, save all',
            cancelButtonText: 'Cancel',
            width: '90%',
            maxWidth: '400px'
        }).then((result) => {
            if (result.isConfirmed) {
                // Collect all mobile form data
                const formData = new FormData();
                formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));
                formData.append('assignment_id', new URLSearchParams(window.location.search).get("assignment_id"));

                // Collect all mobile score inputs
                $('.mobile-student-card').each(function () {
                    const card = $(this);
                    const studentId = card.data('student-id');

                    // Add all score inputs for this student
                    card.find('input[name^="individual_score_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="class_test_score_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="project_score_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="group_work_score_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="exam_score_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="class_score_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="total_score_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="grade_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="remarks_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                    card.find('input[name^="position_"]').each(function () {
                        formData.append($(this).attr('name'), $(this).val());
                    });
                });

                // Show loading
                Swal.fire({
                    title: 'Saving...',
                    text: 'Please wait while we save all scores.',
                    allowOutsideClick: false,
                    didOpen: () => {
                        Swal.showLoading();
                    }
                });

                // Submit the form data
                $.ajax({
                    url: window.location.href,
                    method: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false,
                    success: function (response) {
                        Swal.fire({
                            title: 'Success!',
                            text: 'All scores have been saved successfully.',
                            icon: 'success',
                            timer: 2000,
                            showConfirmButton: false
                        });

                        // Add animation to all cards
                        $('.mobile-student-card').addClass('saved-row');
                        setTimeout(() => $('.mobile-student-card').removeClass('saved-row'), 1500);
                    },
                    error: function (xhr) {
                        Swal.fire({
                            title: 'Error!',
                            text: 'There was an error saving the scores: ' + xhr.responseText,
                            icon: 'error'
                        });
                    }
                });
            }
        });
    };

    // Mobile input handling
    $(document).on('input', '.mobile-score-input:not([readonly])', function () {
        const card = $(this).closest('.mobile-student-card');
        const studentId = card.data('student-id');

        // Trigger calculations
        calculateMobileClassScore(card);
        calculateMobileTotalScore(card);
        updateMobileGradeAndRemarks(card);

        // Highlight changed card
        card.addClass('modified-row');
        setTimeout(() => card.removeClass('modified-row'), 2000);
    });

    // Mobile calculation functions
    function calculateMobileClassScore(card) {
        const individual = parseFloat(card.find('.individual-score').val()) || 0;
        const classTest = parseFloat(card.find('.class-test-score').val()) || 0;
        const project = parseFloat(card.find('.project-score').val()) || 0;
        const groupWork = parseFloat(card.find('.group-work-score').val()) || 0;

        const totalActualScore = individual + classTest + project + groupWork;
        const totalMaxPossibleScore = scoringConfig.individualMaxMark + scoringConfig.classTestMaxMark +
            scoringConfig.projectMaxMark + scoringConfig.groupWorkMaxMark;

        if (totalMaxPossibleScore === 0) {
            const roundedScore = 0;
            card.find('.calculated-class-score').val(roundedScore.toFixed(2));
            card.find('.calculated-class-score-input').val(roundedScore);
            return roundedScore;
        }

        const scaledScore = (totalActualScore / totalMaxPossibleScore) * scoringConfig.classScorePercentage;
        const roundedScore = Math.round(scaledScore * 100) / 100;

        card.find('.calculated-class-score').val(roundedScore.toFixed(2));
        card.find('.calculated-class-score-input').val(roundedScore);

        return roundedScore;
    }

    function calculateMobileTotalScore(card) {
        const classScore = parseFloat(card.find('.calculated-class-score-input').val()) || 0;
        const examScore = parseFloat(card.find('.exam-score').val()) || 0;

        if (classScore > 0 || examScore > 0) {
            const examScoreScaled = (examScore / 100) * scoringConfig.examScorePercentage;
            const totalScore = classScore + examScoreScaled;
            const roundedTotal = Math.round(totalScore * 100) / 100;

            card.find('.mobile-result-value').text(roundedTotal.toFixed(2));
            card.find('.total-score-input').val(roundedTotal);

            return roundedTotal;
        } else {
            card.find('.mobile-result-value').text('--');
            card.find('.total-score-input').val('');
            return 0;
        }
    }

    function updateMobileGradeAndRemarks(card) {
        const totalScore = parseFloat(card.find('.total-score-input').val());

        if (!isNaN(totalScore) && totalScore > 0) {
            let grade, remarks, gradeClass, remarksClass;

            if (totalScore >= 80) {
                grade = 'A';
                remarks = 'Excellent';
                gradeClass = 'grade-a';
                remarksClass = 'remarks-excellent';
            } else if (totalScore >= 70) {
                grade = 'B';
                remarks = 'Very Good';
                gradeClass = 'grade-b';
                remarksClass = 'remarks-vgood';
            } else if (totalScore >= 60) {
                grade = 'C';
                remarks = 'Good';
                gradeClass = 'grade-c';
                remarksClass = 'remarks-good';
            } else if (totalScore >= 50) {
                grade = 'D';
                remarks = 'Average';
                gradeClass = 'grade-d';
                remarksClass = 'remarks-average';
            } else if (totalScore >= 40) {
                grade = 'E';
                remarks = 'Poor';
                gradeClass = 'grade-e';
                remarksClass = 'remarks-poor';
            } else {
                grade = 'F';
                remarks = 'Fail';
                gradeClass = 'grade-f';
                remarksClass = 'remarks-fail';
            }

            // Update grade display
            const gradeElement = card.find('.mobile-grade');
            gradeElement.text(grade);
            gradeElement.removeClass('grade-a grade-b grade-c grade-d grade-e grade-f');
            gradeElement.addClass(gradeClass);
            card.find('.grade').val(grade);

            // Update remarks display
            const remarksElement = card.find('.mobile-remarks');
            remarksElement.text(remarks);
            remarksElement.removeClass('remarks-excellent remarks-vgood remarks-good remarks-average remarks-poor remarks-fail');
            remarksElement.addClass(remarksClass);
            card.find('.remarks').val(remarks);
        } else {
            // Clear grade and remarks
            card.find('.mobile-grade').text('--');
            card.find('.grade').val('');
            card.find('.mobile-remarks').text('--');
            card.find('.remarks').val('');
        }

        // Calculate positions
        calculateMobilePositions();
    }

    function calculateMobilePositions() {
        const cards = [];
        $('.mobile-student-card').each(function () {
            const card = $(this);
            const totalScore = parseFloat(card.find('.total-score-input').val());
            if (!isNaN(totalScore) && totalScore > 0) {
                cards.push({
                    card: card,
                    score: totalScore
                });
            }
        });

        // Sort by score (highest first)
        cards.sort((a, b) => b.score - a.score);

        // Assign positions
        cards.forEach((item, index) => {
            const position = index + 1;
            const positionElement = item.card.find('.mobile-position');

            let positionClass;
            if (position === 1) {
                positionClass = 'position-1';
            } else if (position === 2) {
                positionClass = 'position-2';
            } else if (position === 3) {
                positionClass = 'position-3';
            } else {
                positionClass = 'position-other';
            }

            positionElement.text(position);
            positionElement.removeClass('position-1 position-2 position-3 position-other');
            positionElement.addClass(positionClass);
            item.card.find('.position').val(position);
        });

        // Clear positions for students without scores
        $('.mobile-student-card').each(function () {
            const card = $(this);
            const totalScore = parseFloat(card.find('.total-score-input').val());
            if (isNaN(totalScore) || totalScore <= 0) {
                card.find('.mobile-position').text('--');
                card.find('.position').val('');
            }
        });
    }

    // Initialize mobile calculations for existing scores
    $('.mobile-student-card').each(function () {
        const card = $(this);
        if (card.find('.individual-score').val() || card.find('.class-test-score').val() ||
            card.find('.project-score').val() || card.find('.group-work-score').val()) {
            calculateMobileClassScore(card);
        }
        if (card.find('.individual-score').val() || card.find('.class-test-score').val() ||
            card.find('.project-score').val() || card.find('.group-work-score').val() ||
            card.find('.exam-score').val()) {
            calculateMobileTotalScore(card);
            updateMobileGradeAndRemarks(card);
        }
    });

    // Student Search Functionality
    function performSearch() {
        const searchTerm = $('#studentSearch').val().toLowerCase().trim();
        const rows = $('tbody tr');
        let visibleCount = 0;

        rows.each(function () {
            const row = $(this);
            const studentName = row.find('td:first').text().toLowerCase();
            const studentId = row.find('td:eq(1)').text().toLowerCase();

            if (searchTerm === '' ||
                studentName.includes(searchTerm) ||
                studentId.includes(searchTerm)) {
                row.show();
                visibleCount++;
            } else {
                row.hide();
            }
        });

        // Update search results count
        const totalStudents = rows.length;
        if (searchTerm === '') {
            $('#searchResultsCount').text(`Showing all ${totalStudents} students`);
        } else {
            $('#searchResultsCount').text(`Showing ${visibleCount} of ${totalStudents} students`);
        }
    }

    // Search input event handlers
    $('#studentSearch').on('input', function () {
        performSearch();
    });

    $('#searchBtn').on('click', function () {
        performSearch();
    });

    $('#clearSearchBtn').on('click', function () {
        $('#studentSearch').val('');
        performSearch();
        $('#studentSearch').focus();
    });

    // Enter key to search
    $('#studentSearch').on('keypress', function (e) {
        if (e.which === 13) { // Enter key
            e.preventDefault();
            performSearch();
        }
    });
});
