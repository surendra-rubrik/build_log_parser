import time
import pytz
import datetime
import dateutil.parser
import subprocess
import json
import re
import collections
import requests

build_matrix = []
JENKINS_URL = "http://cdm-builds.corp.rubrik.com/job/"
REQUIRED_DETAILS = "duration,result,timestamp"

INFRA_RELATED_FAILURE_SIGNATURE = [
    "Caused: java.io.IOException: Backing channel",
    'hudson.plugins.git.GitException: Command "git checkout -f',
    "ERROR: error loading package '': Encountered error while reading"
]



def utc_time_duration(start_time,end_time):
    format = '%Y-%m-%dT%H:%M:%S%z'
    start_time_utc = dateutil.parser.parse(start_time)
    end_time_utc = dateutil.parser.parse(end_time)
    return str(end_time_utc - start_time_utc)


def reassign_bug(bug_id, failure_matrix):
    pass


def check_for_non_test_failures(passed_line):
    infra_failure_tags = [i for i in INFRA_RELATED_FAILURE_SIGNATURE if i in
                           passed_line]
    if infra_failure_tags:
        failure_type = {
            'failure_type': 'INFRA',
            'bug_owner': 'manuel.flamerich@rubrik.com',
            'error': infra_failure_tags[0]
        }
        return failure_type

    return None


def process_test_log(tmp_log,is_passed=True):
    #print(len(tmp_log))
    testcase_matrix = {}
    failure_type = {}
    count = 0
    for line in tmp_log:
        if is_passed:
            if 'PASS ' in line or 'FAIL ' in line:
                key = re.sub(r'[^\x00-\x7F]+','', line.split()[2])
                time_taken = re.sub(r'[^\x00-\x7F]+','', line.split()[1])
                time_taken = time_taken.split(';')[1] if len(time_taken.split(';')) > 1 else time_taken
                status = 'PASSED'
                testcase_matrix[key] = {'time_taken' : time_taken,'status':status}
        else:
            if 'PASSED ' in line or 'FAILED ' in line or 'TIMEOUT ' in line:
                key = re.sub(r'[^\x00-\x7F]+', '', line.split()[0])
                time_taken = re.sub(r'[^\x00-\x7F]+', '', line.split()[3])
                time_taken = time_taken.split(';')[1] if len(time_taken.split(';')) > 1 else time_taken
                status = line.split()[1]
                if status in ['FAILED', 'TIMEOUT']:
                    failure_type.update({
                        'failure_type': 'TEST',
                        'bug_owner': 'owner'
                    })
                testcase_matrix[key] = {
                    'time_taken': time_taken,
                    'status': status,
                }

    return testcase_matrix, failure_type


def parse_console_content(fileName,buildNumber):

    build_details ={}
    compile_details = {}
    build_details['id']='%s'%(buildNumber)

    git_operation_start_time = False
    git_operation_end_time = False
    python_test_start_time = False
    python_test_end_time = False
    pant_test_start_time = False
    pant_test_end_time = False
    rk_py_test_start_time = False
    rk_py_test_end_time = False
    go_test_start_time = False
    go_test_end_time = False
    cpp_test_start_time = False
    cpp_test_end_time = False
    java_test_start_time = False
    java_test_end_time = False
    web_test_start_time = False
    web_test_end_time = False
    archiving_start_time = False
    archiving_end_time = False
    overral_status = 'FAILED'
    type_of_failure = None

    tmp_log = []


    contentFound = False
    contentComplete = False
    with open(fileName, "r") as ins:
        for line in ins:
            if '<pre' in line:
                contentFound = True
                continue
            if '</pre>' in line:
                contentComplete = True
                continue
            if contentFound and contentComplete == False:
                if not "</b> </span>" in line:
                    continue
                time_stamp = (line.split("</b> </span>", 1)[0]).split('<span class="timestamp"><b>',1)[1]
                line_content = line.split("</span>", 1)[1]

                #host info
                if 'Building remotely on <a href=\'/computer/' in line_content :
                    host_info = (line_content.split('Building remotely on <a href=\'/computer/',1)[1]).split('\'')[0]
                    #print(host_info)
                    build_details['host_info'] = host_info

                #hash
                if 'git checkout -f ' in line_content:
                    hash=line_content.split('git checkout -f ',1)[1]
                    #print(hash)
                    build_details['hash'] = hash


                if 'Cloning the remote Git repository' in line_content:
                    git_operation_start_time = time_stamp
                if '*********** RESTRICTING IPTABLES TO WHITELISTED IPs ONLY! ***********' in line_content:
                    git_operation_end_time = time_stamp

                #Compilation time
                if 'Time to build' in line_content:
                    #print(line_content.split('Time to build ',1)[1])
                    compile_name,duration = (line_content.split('Time to build ',1)[1]).split('=')
                    compile_details[compile_name] = duration


                #Python Test time :
                if 'Running py.test ...' in line_content:
                    python_test_start_time = time_stamp
                if 'Python tests: ' in line_content:
                    python_test_end_time = time_stamp

                #Pant_test_time
                if 'Running Pants tests...' in line_content:
                    pant_test_start_time = time_stamp
                if 'Runnning rk_pytest ' in line_content or 'Running rk_pytest ' in line_content:
                    pant_test_end_time = time_stamp


                if 'Runnning rk_pytest ' in line_content or 'Running rk_pytest ' in line_content:
                    rk_py_test_start_time = time_stamp
                if 'Pants tests: ' in line_content:
                    rk_py_test_end_time = time_stamp


                if 'Running Go tests...' in line_content:
                    go_test_start_time = time_stamp
                    tmp_log = []
                if go_test_start_time and 'Go tests: ' in line_content:
                    go_test_end_time = time_stamp
                    build_details['go_test_cases'] = process_test_log(tmp_log)
                    tmp_log = []
                elif go_test_start_time and not go_test_end_time and 'FAILURE SUMMARY:' in line_content:
                    go_test_end_time = time_stamp
                    build_details['go_test_cases'] = process_test_log(
                        tmp_log, False)
                    tmp_log =[]

                    #break

                if "bazel test '--test_tag_filters=unit-test' '--test_output=errors' //'src/cpp'/..." in line_content:
                    cpp_test_start_time = time_stamp
                    tmp_log = []
                if cpp_test_start_time and 'Cpp tests: ' in line_content:
                    cpp_test_end_time = time_stamp
                    build_details['cpp_test_cases'] = process_test_log(tmp_log)
                    tmp_log = []
                elif cpp_test_start_time and not cpp_test_end_time and 'FAILURE SUMMARY:' in line_content:
                    cpp_test_end_time = time_stamp
                    build_details['cpp_test_cases'], build_details[
                        'failure_type'] = process_test_log(
                        tmp_log, False)
                    build_details['failed_test_key'] = 'cpp_test_cases'
                    #break

                if 'Running Bazel tests for Java: ' in line_content:
                    java_test_start_time = time_stamp
                elif java_test_start_time and 'Java tests: ' in line_content:
                    java_test_end_time = time_stamp
                    build_details['java_test_cases'] = process_test_log(tmp_log)
                    tmp_log = []
                elif java_test_start_time and not java_test_end_time and 'FAILURE SUMMARY:' in line_content:
                    java_test_end_time = time_stamp
                    build_details['java_test_cases'], build_details[
                        'failure_type'] = process_test_log(
                        tmp_log, False)
                    build_details['failed_test_key'] = 'java_test_cases'


                if 'Building Web and running tests...' in line_content:
                    web_test_start_time = time_stamp
                if 'Web tests: ' in line_content:
                    web_test_end_time = time_stamp


                if 'Archiving artifacts' in line_content:
                    archiving_start_time = time_stamp
                if 'Finished: SUCCESS' in line_content:
                    archiving_end_time = time_stamp
                    overral_status = 'SUCCESS'
                elif 'Finished:' in line_content:
                    overral_status = line_content.split('Finished:')[1]

                if 'Filed issue' in line_content:
                    bug_id = line_content.split('Filed issue u\'')[1].split('\'')[0]
                    build_details['bug_id'] = bug_id
                    if 'failed_test_key' in build_details:
                        reassign_bug(bug_id, build_details[build_details[
                            'failed_test_key']])


                tmp_log.append(line_content)
                if not build_details.get('failure_type', None):
                    build_details['failure_type'] = check_for_non_test_failures(
                        line_content)


                #print(time_stamp + ' ' +  line_content)
                #print(line)

        if git_operation_start_time and git_operation_end_time:
            git_operation_time = utc_time_duration(git_operation_start_time, git_operation_end_time)
            build_details['git_operation_time']= git_operation_time

        if python_test_start_time and python_test_end_time:
            python_test_time = utc_time_duration(python_test_start_time, python_test_end_time)
            build_details['python_test_time']=python_test_time

        if pant_test_start_time and pant_test_end_time:
            pant_test_time = utc_time_duration(pant_test_start_time, pant_test_end_time)
            build_details['pant_test_time'] = pant_test_time

        if rk_py_test_start_time and rk_py_test_end_time:
            rk_test_time = utc_time_duration(rk_py_test_start_time, rk_py_test_end_time)
            build_details['rk_test_time'] = rk_test_time

        if go_test_start_time and go_test_end_time:
            go_test_time = utc_time_duration(go_test_start_time, go_test_end_time)
            build_details['go_test_time'] = go_test_time

        if cpp_test_start_time and cpp_test_end_time:
            cpp_test_time = utc_time_duration(cpp_test_start_time, cpp_test_end_time)
            build_details['cpp_test_time'] = cpp_test_time

        if java_test_start_time and java_test_end_time:
            java_test_time = utc_time_duration(java_test_start_time, java_test_end_time)
            build_details['java_test_time'] = java_test_time

        if web_test_start_time and web_test_end_time:
            web_test_time = utc_time_duration(web_test_start_time, web_test_end_time)
            build_details['web_test_time'] = web_test_time

        if archiving_start_time and archiving_end_time:
            archiving_time = utc_time_duration(archiving_start_time, archiving_end_time)
            build_details['archiving_time'] = archiving_time

        #print("Build Status : %s"%(overral_status))
        #build_details['status'] = overral_status
        build_details['compile_details'] = compile_details

        build_rest_url = JENKINS_URL + \
            'Compile_CDM/%s/api/json?tree=%s'%(buildNumber, REQUIRED_DETAILS)
        response = requests.get(build_rest_url)
        response = response.json()
        build_details['duration'] = response['duration']
        build_details['result'] = response['result']
        build_details['start_epoch_timestamp'] = response['timestamp']
        build_details['end_epoch_timestamp'] = response['timestamp'] + response[
            'duration']
        if 'FAILED' in build_details['result'] and not build_details[\
                'failure_type']:
            build_details['failure_type'].update({
                "bug_owner": "owner",
                "failure_type": "UKNOWN"
            })
        return build_details


def get_build_file(build_number):
    build_url= JENKINS_URL + "Compile_CDM/%d/consoleFull"% (build_number)
    subprocess.call(["wget", '-O', 'data/%d.html' %(build_number),build_url])


def main():
    for buildNumber in range(7013, 7014):
        #get_build_file(buildNumber)
        #print('==============================================\n')
        build_matrix.append(parse_console_content('data/%d.html'%(buildNumber),buildNumber))
    print(json.dumps(build_matrix, indent=4, sort_keys=True))
    with open('data.json', 'w') as f:
        json.dump(build_matrix,f, indent=4, sort_keys=True)


if __name__ == "__main__":
    main()

