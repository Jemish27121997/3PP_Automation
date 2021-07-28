import subprocess
import sys

# Query Command to request Bazaar for new facility
command_request_bazaar = 'curl -v -H "Connection: Keep-Alive" \
-H "Content-Type:application/json" --data @/tmp/3pp_automation/reportFiles\
/requestData.json -k --noproxy  --url \'http://papi.internal.ericsson.com?\
query=\\{{"username":"{}","token":"{}","facility":"{}"\\}}\''


"""
This function will request bazaar for new facility depending on the
data provided in the request Json file.
"""


def requestBazaar(userid, token, svlid):
    command = command_request_bazaar.format(userid, token, "NEW_3PP")
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
    curl_answer, err = proc.communicate()
    exit_value = proc.returncode
    return exit_value, curl_answer, err


if __name__ == "__main__":
    svlid = str(sys.argv[2])
    svlid = svlid.split("#", 1)[1]
    userid = str(sys.argv[3])
    token = str(sys.argv[4])
    return_value, curl_answer, err = requestBazaar(userid, token, svlid)