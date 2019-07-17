import time
import pytz
import datetime
import dateutil.parser
import subprocess



def utc_time_duration(start_time,end_time):
    format = '%Y-%m-%dT%H:%M:%S%z'
    start_time_utc = dateutil.parser.parse(start_time)
    end_time_utc = dateutil.parser.parse(end_time)
    return str(end_time_utc - start_time_utc)

def get_console_content(fileName):
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
                time_stamp = (line.split("</b> </span>", 1)[0]).split('<span class="timestamp"><b>',1)[1]
                line_content = line.split("</span>", 1)[1]

                #host info
                if 'Building remotely on <a href=\'/computer/' in line_content :
                    host_info = (line_content.split('Building remotely on <a href=\'/computer/',1)[1]).split('\'')[0]
                    print(host_info)

                #hash
                if 'git checkout -f ' in line_content:
                    hash=line_content.split('git checkout -f ',1)[1]
                    print(hash)


                if 'Cloning the remote Git repository' in line_content:
                    git_operation_start_time = time_stamp
                if '*********** RESTRICTING IPTABLES TO WHITELISTED IPs ONLY! ***********' in line_content:
                    git_operation_end_time = time_stamp



                #Compilation time
                if 'Time to build' in line_content:
                    print(line_content.split('Time to build ',1)[1])

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
                if 'Go tests: ' in line_content:
                    go_test_end_time = time_stamp


                if "bazel test '--test_tag_filters=unit-test' '--test_output=errors' //'src/cpp'/..." in line_content:
                    cpp_test_start_time = time_stamp
                if 'Cpp tests: ' in line_content:
                    cpp_test_end_time = time_stamp


                if 'Running Bazel tests for Java: ' in line_content:
                    java_test_start_time = time_stamp
                if 'Java tests: ' in line_content:
                    java_test_end_time = time_stamp


                if 'Building Web and running tests...' in line_content:
                    web_test_start_time = time_stamp
                if 'Web tests: ' in line_content:
                    web_test_end_time = time_stamp


                if 'Archiving artifacts' in line_content:
                    archiving_start_time = time_stamp
                if 'Finished: ' in line_content:
                    archiving_end_time = time_stamp

                #print(time_stamp + ' ' +  line_content)
                #print(line)

        if git_operation_start_time and git_operation_end_time:
            print('git operation time : ' + utc_time_duration(git_operation_start_time, git_operation_end_time))

        if python_test_start_time and python_test_end_time:
            print('Python test time : ' + utc_time_duration(python_test_start_time, python_test_end_time))

        if pant_test_start_time and pant_test_end_time:
            print('Pant test time : ' + utc_time_duration(pant_test_start_time, pant_test_end_time))

        if rk_py_test_start_time and rk_py_test_end_time:
            print('RK_Py test time : ' + utc_time_duration(rk_py_test_start_time, rk_py_test_end_time))

        if go_test_start_time and go_test_end_time:
            print('Go test time : ' + utc_time_duration(go_test_start_time, go_test_end_time))

        if cpp_test_start_time and cpp_test_end_time:
            print('CPP test time : ' + utc_time_duration(cpp_test_start_time, cpp_test_end_time))

        if java_test_start_time and java_test_end_time:
            print('JAVA test time : ' + utc_time_duration(java_test_start_time, java_test_end_time))

        if web_test_start_time and web_test_end_time:
            print('WEB test time : ' + utc_time_duration(web_test_start_time, web_test_end_time))

        if archiving_start_time and archiving_end_time:
            print('Archiving time : ' + utc_time_duration(archiving_start_time, archiving_end_time))


def get_build_file(build_number):
    build_url= 'http://cdm-builds.corp.rubrik.com/job/Compile_CDM/%d/consoleFull'% (build_number)
    subprocess.call(["wget",'-O' ,'data/%d.html' %(build_number),build_url])



def main():
    for i in range(6802, 6803):
        get_build_file(i)
        get_console_content('data/%d.html'%(i))

if __name__ == "__main__":
    main()

