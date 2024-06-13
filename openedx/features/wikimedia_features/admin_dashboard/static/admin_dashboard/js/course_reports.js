(function() {
    'use strict';
    let getCookie, ReportDownloads, AjaxCall, ReportDownloadsForMultipleCourses, PendingTasks;
    let course_name = null;
    let endpoint =  null;
    let pendingTaskEndpoint = "/wikimedia/pending_tasks/all_courses";
    let report_for_single_courses = true;
    let prev_data_download_len = 0;

    getCookie = function(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            let cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                let cookie = jQuery.trim(cookies[i]);
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    ReportDownloads = function(){
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: endpoint,
            success: function(data) {
                if (data.downloads.length > 0) {
                    $('.download-section, #report-downloads-list').show();
                    if ($('#report-downloads-list').find('a').length == 0){
                        prev_data_download_len = data.downloads.length;
                        for (let i = 0; i < data.downloads.length; i++) {
                            if(data.downloads[i]['name'].split("_")[0] != 'multiple')
                            {
                                $('#report-downloads-list').append('<li>'+data.downloads[i]['link']+'</li>');
                            }
                        }
                    }
                    else if (data.downloads.length > prev_data_download_len){
                        let newReportsFetched = data.downloads.length - prev_data_download_len;
                        prev_data_download_len = data.downloads.length;
                        for (let i = newReportsFetched; i > 0; i--) {
                            if(data.downloads[i-1]['name'].split("_")[0] != 'multiple')
                            {
                                $('#report-downloads-list').prepend('<li>'+data.downloads[i-1]['link']+'</li>');
                            }
                        }
                    }
                }
            },
            error: function() {
                console.log("There is an error in the list report downloads api")
            }
        });
    };

    const GetPreviousLinks = function(){
        var aTags = $('#report-downloads-list li a')
        var previousLinks = [];
        for ( let counter = 0; counter < aTags.length; counter++){
            previousLinks.push( aTags[ counter ].getAttribute("href") );
        }
        return previousLinks
    }

    ReportDownloadsForMultipleCourses = function(){
        $.ajax({
            type: 'POST',
            dataType: 'json',
            url: endpoint,
            success: function(data) {
                if (data.downloads.length > 0) {
                    $('.download-section, #report-downloads-list').show();
                    if (report_for_single_courses != false){
                        const previousLinks = GetPreviousLinks()
                        for (let i = 0; i < data.downloads.length; i++) {
                            if(data.downloads[i]['name'].split("_")[0] == 'multiple' && !previousLinks.includes(data.downloads[i]['url']))
                            {
                                $('#report-downloads-list').append('<li>'+data.downloads[i]['link']+'</li>');
                            }
                        }
                    }
                    else if (report_for_single_courses == false) {
                        report_for_single_courses = null;
                        if(data.downloads[0]['name'].split("_")[0] == 'multiple')
                        {
                            $('#report-downloads-list').prepend('<li>'+data.downloads[0]['link']+'</li>');
                        }
                    }
                }
            },
            error: function() {
                console.log("There is an error in the list report downloads api")
            }
        });
    };

    AjaxCall = function(url, data={}){
        $.ajaxSetup({
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
        });
        $.ajax({
            type: 'POST',
            dataType: 'json',
            data: data,
            url: url,
            error: function(error) {
                if (error.responseText) {
                    $('.request-response-error').text(error.responseText).show();
                }
            },
            success: function(data) {
                $('.request-response').text(data.status).show();
                PendingTasks()
            }
        });
    };

    PendingTasks = function() {
        var $no_tasks_message = $('.no-pending-tasks-message'),
            $running_tasks_section = $('.running-tasks-section')
        return $.ajax({
            type: 'GET',
            dataType: 'json',
            url: pendingTaskEndpoint,
            success: function(tasks) {
                if (tasks.length) {
                    $("#pending-tasks").empty().show()
                    for(const task of tasks){
                        $("#pending-tasks").append('<li>'+`${task.task_type}_${task.created}`+'</li>')
                    }
                    $no_tasks_message.hide();
                    return $running_tasks_section.show();
                } else {
                    $("#pending-tasks").hide()
                    $running_tasks_section.hide();
                    $no_tasks_message.empty();
                    $no_tasks_message.append($('<p>').text(gettext('No tasks currently running.')));
                    return $no_tasks_message.show();
                }
            },
            error: function() {
                console.log("There is an error in the pending tasks api")
            }
        });
    };

    setInterval(function() {
        if(endpoint != null)
        {
            if(report_for_single_courses == true) {
                ReportDownloads();
            }
            else{
                ReportDownloadsForMultipleCourses();
            }
        }
        PendingTasks()
    }, 20000);

    $('#select-courses').select2({
        placeholder: "Browse Courses",
    });

    $('#select-enrollment-year').change(function (e) {
        e.preventDefault();
        const today = new Date();
        const selected_year = Number($(this).val())
        const current_year = today.getFullYear()
        var quarters = 4;

        var quarter_select = $("#select-enrollment-quarter")
        quarter_select.empty()

        if(!selected_year){
            var opt = document.createElement('option');
            opt.value = "";
            opt.innerHTML = "Select Quarter";
            quarter_select.append(opt);
        }

        if (selected_year === current_year){
            quarters = Math.floor((today.getMonth() + 3) / 3) - 1;
        }

        for (var i = 1; i<=quarters; i++){
            var opt = document.createElement('option');
            opt.value = i;
            opt.innerHTML = i;
            quarter_select.append(opt);
        }
    })

    $('#select-courses').change(function (e) {
        e.preventDefault();
        let list_of_single_course_elements = $('.single-course-report');
        let list_of_multiple_course_elements = $('.multiple-course-report');
        let list_of_course_version_elements = $('.course-version-report');
        let list_of_all_courses_elements = $('.all-courses-report')
        prev_data_download_len = 0;
        if ($(this).val())
        {
            $('.btn-primary').attr('disabled', false);
            $('.div-tooltip').each(function() {
                const $this = $(this);
                $this.attr('data', $this.attr('title'));
                $this.removeAttr('title');
            });
            list_of_all_courses_elements.hide();
            pendingTaskEndpoint = `/wikimedia/pending_tasks/${$(this).val().toString()}`
            if ($(this).val().length > 1) {
                course_name = $(this).val().toString();
                list_of_single_course_elements.hide();
                list_of_multiple_course_elements.show();
                list_of_course_version_elements.hide()
                if(report_for_single_courses == true)
                {
                    $('#report-request-response,#report-request-response-error,#report-downloads-list').empty().hide();
                    for (let i = 0; i < $("#select-courses")[0].length; i++) {
                        endpoint = `/courses/${$("#select-courses")[0].options[i].value}/instructor/api/list_report_downloads`;
                        ReportDownloadsForMultipleCourses();
                    }
                }
                endpoint = `/courses/${$(this).val()[0]}/instructor/api/list_report_downloads`;
                report_for_single_courses = null;
            }
            else {
                var base_courses_list = JSON.parse(document.getElementById("base_courses_list").innerHTML)
                list_of_course_version_elements.hide()
                for (const [_, value] of Object.entries(base_courses_list)) {
                    if(value == $(this).val()[0])
                    {
                        list_of_course_version_elements.show();
                    }
                }
                $('#report-request-response,#report-request-response-error,#report-downloads-list').empty().hide();
                course_name = $(this).val()[0];
                report_for_single_courses = true;
                list_of_single_course_elements.show();
                list_of_multiple_course_elements.hide();
                endpoint = `/courses/${$(this).val()[0]}/instructor/api/list_report_downloads`;
                ReportDownloads();
            }
        }
        else {
            $('.div-tooltip').each(function() {
                const $this = $(this);
                $this.attr('title', $this.attr('data'));
                $this.removeAttr('data');
            });
            list_of_single_course_elements.show();
            list_of_multiple_course_elements.show();
            list_of_course_version_elements.show();
            list_of_all_courses_elements.show();
            $('.btn-primary').attr('disabled', true);
            $('.all-courses-report .action .btn-primary').attr('disabled', false);
            course_name = null;
            endpoint = '/wikimedia/list_all_courses_report_downloads';
            pendingTaskEndpoint = "/wikimedia/pending_tasks/all_courses";
            report_for_single_courses = true;
            $('#report-request-response,#report-request-response-error,#report-downloads-list').empty().hide();
            ReportDownloads()
        }
        PendingTasks()
    });

    $("[name='list-profiles-csv']").click(function() {
        let url_for_list_profiles_csv = '/courses/' + course_name + '/instructor/api/get_students_features' + '/csv';
        AjaxCall(url_for_list_profiles_csv);
    });

    $("[name='calculate-grades-csv']").click(function() {
        let url_for_calculate_grades = '/courses/' + course_name + '/instructor/api/calculate_grades_csv';
        AjaxCall(url_for_calculate_grades);
    });

    $("[name='list-anon-ids']").click(function() {
        let url_for_list_anon_ids = '/courses/' + course_name + '/instructor/api/get_anon_ids';
        AjaxCall(url_for_list_anon_ids);
    });

    $("[name='problem-grade-report']").click(function() {
        let url_for_problem_grade_report = '/courses/' + course_name + '/instructor/api/problem_grade_report';
        AjaxCall(url_for_problem_grade_report);
    });

    $("[name='list-may-enroll-csv']").click(function() {
        let url_for_list_may_enroll = '/courses/' + course_name + '/instructor/api/get_students_who_may_enroll';
        AjaxCall(url_for_list_may_enroll);
    });

    $("[name='average-calculate-grades-csv']").click(function() {
        let url_for_average_calculate_grades = '/admin_dashboard/average_calculate_grades_csv/' + course_name ;
        AjaxCall(url_for_average_calculate_grades);
        report_for_single_courses = false;
    })

    $("[name='course-version-report-detailed']").click(function() {
        let url_for_course_version_report = '/admin_dashboard/course_version_report/' + course_name ;
        AjaxCall(url_for_course_version_report);
    })

    $("[name='course-version-report-total']").click(function() {
        let url_for_course_version_report = '/admin_dashboard/course_version_report/' + course_name ;
        AjaxCall(url_for_course_version_report, {'csv_type': 'course_version_aggregate'});
    })

    $("[name='progress-report-csv']").click(function() {
        let url_for_average_calculate_grades = '/admin_dashboard/progress_report_csv/' + course_name ;
        AjaxCall(url_for_average_calculate_grades);
    })
    $("[name='courses-enrollments-csv']").click(function() {
        let url_for_courses_enrollment_report = $(this).attr('data-endpoint');
        let year = $('#select-enrollment-year').val()
        let quarter = $('#select-enrollment-quarter').val()
        AjaxCall(url_for_courses_enrollment_report, {year: Number(year), quarter: Number(quarter)});
    })
    $("[name='all-courses-enrollments-csv']").click(function() {
        let data_url = $(this).attr('data-endpoint');
        AjaxCall(data_url);
    })
    $("[name='user-pref-lang-csv']").click(function() {
        let data_url = $(this).attr('data-endpoint');
        AjaxCall(data_url);
    })
    $(document).ready(function() {
        endpoint = '/wikimedia/list_all_courses_report_downloads';
        ReportDownloads();
        PendingTasks()
    });


}).call(this);
