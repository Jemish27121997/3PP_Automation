import glob
import json
import os
import subprocess
import sys
import urllib.parse
from enum import IntEnum
from xml.dom import minidom

import requests
import urllib3

import pandas as pd
from bs4 import BeautifulSoup

addToSVLFile = "/tmp/3pp_automation/reportFiles/addToSVL.csv"
requestDataFile = "/tmp/3pp_automation/reportFiles/requestData.json"
reportFile = "/tmp/3pp_automation/reportFiles/report.csv"
svlFile = "/tmp/3pp_automation/reportFiles/svl.csv"
sentRequestFile = "/tmp/3pp_automation/reportFiles/sentRequest.csv"
pairs = []
list2report = []
list2report_inAlreadySVL = []
list2report_addCurrentSVL = []
list2report_newVersion = []
list2report_newComponent = []
list2report_olderVersion = []
list2report_updateLink = []
list2report_differentVersion = []
listSentRequest = []
dict_SVL = {}
dictC_SVL = {}

os.environ["NO_PROXY"] = "ericsson.com"

# Query Command to Bazaar for reusing the component
command_query_bazaar_reuse = 'curl -k --noproxy \'*\' \'http://papi.internal.\
ericsson.com?query=\\{{"username":"{}","token":"{}","facility":"COMPONENT_QUERY"\
,"name":"{}","version":"{}"\\}}\''

# Query Command to Bazaar for the component
command_query_bazaar = 'curl -k --noproxy \'*\' \'http://papi.internal.\
ericsson.com?query=\\{{"username":"{}","token":"{}","facility":\
"COMPONENT_QUERY","name":"{}"\\}}\''

# Query Command to Bazaar for current SVL
command_query_svl = 'curl -k --noproxy \'*\' \'http://papi.internal.\
ericsson.com?query=\\{{"username":"{}","token":"{}","facility":\
"EXPORT_SVL","svl_id":"{}"\\}}\''


class Status_flag(IntEnum):
    isNewComponent = 1
    isNewVersion = 2
    isDifferentVersion = 4
    checkLoop = 5


"""
This function is for executing the querybazaar command and it
returns queryresult if component and version pair found on Bazaar.
"""


def query_bazaar_reuse(userid, token, component, version):
    command = command_query_bazaar_reuse.format(
        userid, token, component, version
    )
    queryResult = []
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        queryResult.append((line.rstrip()))
    curl_answer, err = proc.communicate()
    return queryResult


"""
This function is for executing the query to the Bazaar for the component
and it returns the all the query result with the component name provided
in the parameter.
"""


def queryBazaar(userid, token, component, version):
    command = command_query_bazaar.format(userid, token, component)
    queryResult = []
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        queryResult.append((line.rstrip()))
    curl_answer, err = proc.communicate()
    finalqueryResult = []
    for singlequeryResult in queryResult:
        dictsinglequeryResult = json.loads(singlequeryResult)
        if dictsinglequeryResult.get("name"):
            compName = dictsinglequeryResult.get("name").lower()
            compName = compName.split(",", 1)[0]
            if compName == component.lower():
                dictsinglequeryResult["component"] = component
                dictsinglequeryResult["comp_version"] = version
                singlequeryResult = json.dumps(dictsinglequeryResult)
                finalqueryResult.append(singlequeryResult)
    return finalqueryResult


def getText(nodelist):
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)


"""
This function looks for the pom.xml in current folders and
reads the artifact and version from pom.xml file
and appends to the pairs list.
"""


def readRequirement_pom():
    for file in glob.glob("**/pom.xml", recursive=True):
        print(file)
        dom = minidom.parse(file)
        depend = dom.getElementsByTagName("dependency")
        for i in depend:
            if i:
                groupId = (i.getElementsByTagName('groupId'))[0]
                component = (i.getElementsByTagName('artifactId'))[0]
                version = (i.getElementsByTagName('version'))[0]
                groupId = getText(groupId.childNodes)
                component = getText(component.childNodes)
                version = getText(version.childNodes)
                if "ericsson" in groupId or "Group" in groupId:
                    continue
                if [component, version, groupId] not in pairs:
                    pairs.append([component, version, groupId])


"""
This function reads the component and version from html file
which is generated as report and appends to the pairs list.
"""


def readRequirement():
    dfs = pd.read_html('third-party-report.html')
    df = dfs[1]['GroupId:ArtifactId:Version']
    products_list = df.values.tolist()
    for i in products_list:
        groupId, component, version = i.split(":")
        print("\n\nGroup :  " + groupId + "\nArtifact : " + component)
        print("Version:" + version)
        if "ericsson" in groupId or "Group" in groupId:
            continue
        if [component, version, groupId] not in pairs:
            pairs.append([component, version, groupId])


"""
This function reads the component and version from text file
which is generated as report and appends to the pairs list.
"""


def readRequirement_txt():
    with open("requirements.txt", "r") as f:
        lineList = f.readline().rstrip("\n\r").lstrip()
        word = ":"
        while lineList:
            lineList = lineList.rstrip("\n\r").lstrip()
            str1 = ""
            for ele in lineList:
                str1 += ele
            if str1 == "\n":
                break
            if word in str1:
                component = str1.split(":")[1]
                version = str1.split(":")[2]
                groupId = str1.split(":")[0]
                if "ericsson" not in groupId and "Group" not in groupId:
                    if [component, version, groupId] not in pairs:
                        pairs.append([component, version, groupId])
            lineList = f.readline()



"""
This function creates the JSON file with the all information
that is to be required for requesting to bazaar. It also checks
whether this information already exist in the current json file
otherwise appends the information to JSON file along with all information.
"""


def createJSON(svlId, reqtype, component, version, groupId):
    downLink = downloadLink(component, version, groupId)
    if downLink is None:
        downLink = "Update DownloadLink in bazaar"
        if [component, version] not in list2report_updateLink:
            list2report_updateLink.append([component, version])
    pairTry = component + version
    reqDict = {}
    reqDict["request_type"] = reqtype
    reqDict["community_name"] = component
    reqDict["community_link"] = (
        "https://mvnrepository.com/artifact/" + groupId + "/" + component
    )
    reqDict["component_name"] = component
    reqDict["component_version"] = version
    reqDict["download_link"] = downLink
    reqDict["component_platform"] = "Linux"
    reqDict["component_highlevel_description"] = component
    reqDict["component_programming_language"] = "java"
    reqDict["component_comment"] = ""
    if os.stat(requestDataFile).st_size != 0:
        with open(requestDataFile) as f:
            temp_data = json.load(f)
        a1 = temp_data["foss"]
        flagT = False
        for i in a1:
            pairTry2 = i["component_name"] + i["component_version"]
            if pairTry == pairTry2:
                flagT = True
        if flagT is False:
            a1.append(reqDict)
    else:
        a1 = []
        a1.append(reqDict)
    a = {}
    a["foss"] = a1
    a["svl_id"] = svlId
    with open(requestDataFile, mode="w") as f:
        f.write(json.dumps(a, indent=2))
    return reqDict


"""
This query_svl function will execute the Query command to the bazaar for
current SVL that is provided by parameter svlid and returns SVL dictionary
with component and version pair.
"""


def query_svl(userid, token, svlid):
    command = command_query_svl.format(userid, token, svlid)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    with open(svlFile, "w") as f:
        while True:
            try:
                line = proc.stdout.readline()
                f.write(str(line))
            except:
                pass
            if not line:
                f.close()
                break
            test = line.rstrip()
            parsed_json = json.loads(test)
            if parsed_json.get("svl_details"):
                lst = parsed_json["svl_details"]
                for i in lst:
                    if (
                        i.get("softwareName") is not None
                        and i.get("softwareVersion") is not None
                    ):
                        dictC_SVL[(i.get("softwareName")).lower()] = (
                            i.get("softwareVersion")
                        ).lower()
                        dict_SVL[
                            (i.get("softwareName")).lower()
                            + (i.get("softwareVersion")).lower()
                        ] = (i.get("softwareVersion")).lower()
            if parsed_json.get("svl_2400"):
                lst1 = parsed_json["svl_2400"]
                for j in lst1:
                    if(j.get("softwareName") is not None):
                        split_str = j.get("softwareName").split(",")
                        versio = split_str[-2].strip()
                        compi = ""
                        for st in range(0, len(split_str) - 2):
                            compi += split_str[st]
                        dict_SVL[compi.lower() + versio.lower()] = versio.lower()
                        dictC_SVL[compi.lower()] = versio.lower()
        curl_answer, err = proc.communicate()


"""
This function checks whether the component and version pair that is provided
exists or not in current SVl and it also determines whether it is older version
or different version if component only exist in SVL. It return true if any
pair found in current SVL otherwise return false that is not found.
"""


def already_SVL(component, version, groupId):
    keyInSerach = component + version
    keyInSearch = keyInSerach.lower()
    if keyInSearch in dict_SVL.keys():
        print("key already in component: ", keyInSearch)
        list2report_inAlreadySVL.append([component, version])
        return True
    else:
        keyInSearch1 = component + ", " + version
        keyInSearch2 = component + "," + version
        keyInSearch3 = component + " " + version
        keyInSearch1 = keyInSearch1.lower()
        keyInSearch2 = keyInSearch2.lower()
        keyInSearch3 = keyInSearch3.lower()
        if (
            (keyInSearch1 in dict_SVL.keys())
            or (keyInSearch2 in dict_SVL.keys())
            or (keyInSearch3 in dict_SVL.keys())
        ):
            print("key already in component: ", keyInSearch)
            list2report_inAlreadySVL.append([component, version])
            return True
        else:
            if component in dictC_SVL.keys():
                temo = dictC_SVL[component]
                # flags to evaluate different version
                isDifVersion1 = any(c.isalpha() for c in temo)
                isDifVersion2 = any(d.isalpha() for d in version)
                ver1 = temo.split(".")
                ver2 = version.split(".")
                if len(ver1) == len(ver2):
                    if (not isDifVersion1) and (not isDifVersion2):
                        for k in range(0, len(ver1)):
                            flagBreak = False
                            for l in range(0, len(ver2)):
                                if k == l:
                                    if (int(ver1[k])) > (int(ver2[l])):
                                        isDiffVersion = True
                                        flagBreak = True
                                        break
                                    elif (int(ver1[k])) < (int(ver2[l])):
                                        isDiffVersion = False
                                        flagBreak = True
                                        break
                            if flagBreak:
                                break
                    if isDifVersion1 or isDifVersion2:
                        if [
                            component,
                            version,
                        ] not in list2report_differentVersion:
                            list2report_differentVersion.append(
                                [component, version]
                            )
                            createJSON(svlid, "New Version", component, version, groupId)
                        return True
                    elif isDiffVersion:
                        if [
                            component,
                            version,
                        ] not in list2report_olderVersion:
                            list2report_olderVersion.append(
                                [component, version]
                            )
                            createJSON(svlid, "New Version", component, version, groupId)
                        return True
                return False
            else:
                print("\n\nkey not found in component:", keyInSearch)
                return False


"""
This function will generate downloadlink for the python project
depending upon the component and version and it returns the link
that can be used in creating JSON file for requesting the Bazaar.
"""


def downloadLink(component, version, groupId):
    session = requests.session()
    session.verify = False
    groupId = groupId.replace('.', '/')
    url = "https://repo1.maven.org/maven2/%s/%s/%s/" % (
        groupId,
        component,
        version,
    )
    resp = session.get(url)
    # If not get download link from above URL
    if resp.status_code != 200:
        return None
    installable_ = set()
    soup = BeautifulSoup(resp.content, "html.parser")
    installable_ |= process_page(soup, url)
    for candidate in installable_:
        if candidate[1].endswith('sources.jar') or candidate[1].endswith(
            '.gz'
        ):
            return candidate[1]


"""
This function processes URL link with html parser.
"""


def process_page(soup, url):
    installable_ = set()
    for link in soup.findAll("a"):
        try:
            absolute_link = urllib.parse.urljoin(url, link.get("href"))
        except Exception:
            continue
        installable_.add((url, absolute_link))
    return installable_


"""
This function is for reading the sentrequest file to keep track of
the request that is already sent.
"""


def read_sentRequestFile():
    global listSentRequest
    with open(sentRequestFile) as f:
        listSentRequest = f.readlines()


"""
This function is called if component and version is not found in current
SVL.It defines whether current component and version can be reused from
bazaar based on queryresult that is provided and if it is reused then
it adds to the list of addcurrentSVL.It returns loopflag if it is added.
"""


def addToReuse(singleQueryResult, ocomponent, oversion, groupId):
    # loopFlag is temporary variable used to just detect changes
    loopFlag = Status_flag.checkLoop
    my_string = str(singleQueryResult)
    my_string = my_string[2:]
    my_string = my_string[:-2]
    count = 0
    my_count = my_string.count("prim")
    while count < my_count:
        idx_close = my_string.rfind("}")
        idx_open = my_string.rfind("prim")
        idx_open = idx_open - 2
        idx_close = idx_close + 1
        string_dict = my_string[idx_open:idx_close]
        my_string = my_string[:idx_open]
        count = count + 1
        dictqueryResult = json.loads(str(string_dict))
        if dictqueryResult.get("name"):
            component = dictqueryResult.get("name").lower()
            component = component.split(",", 1)[0]
            version = dictqueryResult.get("version")
            # Exceptional 3PP
            if ocomponent == "jta":
                ocomponent = "Java Transaction API (JTA)".lower()
            if version == oversion:
                if [ocomponent, oversion] not in list2report_addCurrentSVL:
                    list2report_addCurrentSVL.append([ocomponent, oversion])
                    loopFlag = Status_flag.isNewComponent
    return loopFlag


"""
This function is called if component and version pair can not be
reused. It defines that component exists but whether version for
the component is new or not based on queryresult provided as parameter
and if it is new then it adds to the list of new version and creates
the Json file for requesting new version to the Bazaar.It returns loopflag
if it is added.
"""


def addToNewVersion(singleQueryResult, groupId):
    # loopFlag is temporary variable used to just detect changes
    loopFlag = Status_flag.checkLoop
    if "www.w3.org" not in singleQueryResult:
        dictqueryResult = eval(singleQueryResult)
        if dictqueryResult.get("name"):
            component = dictqueryResult.get("component")
            version = dictqueryResult.get("comp_version")
            pair_cv = component + "_" + version
            pair_cv = str(pair_cv)
            bazaarComponent = dictqueryResult.get("name").lower()
            bazaarComponent = bazaarComponent.split(",", 1)[0]
            if bazaarComponent == component.lower():
                if dictqueryResult["version"] != version:
                    isDifVersion1 = any(
                        c.isalpha() for c in dictqueryResult["version"]
                    )
                    isDifVersion2 = any(d.isalpha() for d in version)
                    if isDifVersion1 or isDifVersion2:
                        if [
                            component,
                            version,
                        ] not in list2report_differentVersion:
                            list2report_differentVersion.append(
                                [component, version]
                            )
                            createJSON(svlid, "New Version", component, version, groupId)
                        loopFlag = Status_flag.isDifferentVersion
                    else:
                        if [component, version] not in list2report_newVersion:
                            alreadySent = False
                            for myString in listSentRequest:
                                if myString == pair_cv:
                                    alreadySent = True
                            if not alreadySent:
                                print("component for new version")
                                loopFlag = Status_flag.isNewVersion
                                # list2report_newVersion.append([component,version])
                                alreadySent = False
                                for myString in listSentRequest:
                                    if myString == pair_cv:
                                        alreadySent = True
                                if not alreadySent:
                                    listSentRequest.append(pair_cv)
                        loopFlag = Status_flag.isNewVersion
    return loopFlag


"""
This function processes the element that is component and version pair
and determines whether it is belonging to the current SVL, Reuse, new Version
or New component and depending upon that it calls the function.
"""


def process_thread(element):
    component = element[0]
    version = element[1]
    groupId = element[2]
    if not (already_SVL(component, version, groupId)):
        # loopFlag is temporary variable used to just detect changes
        loopFlag = Status_flag.checkLoop
        while loopFlag > Status_flag.isDifferentVersion:
            queryResult = query_bazaar_reuse(userid, token, component, version)
            if queryResult:
                loopFlag = addToReuse(queryResult, component, version, groupId)
                if loopFlag < Status_flag.checkLoop:
                    break
            queryResult = queryBazaar(userid, token, component, version)
            for singleQueryResult in queryResult:
                loopFlag = addToNewVersion(singleQueryResult, groupId)
                if loopFlag == Status_flag.isDifferentVersion:
                    break
            if loopFlag == Status_flag.isNewVersion:
                if [component, version] not in list2report_newVersion:
                    list2report_newVersion.append([component, version])
                    createJSON(
                        svlid, "New Version", component, version, groupId
                    )
            if loopFlag < Status_flag.checkLoop:
                break
            if [component, version] not in list2report_newComponent:
                if version is not None:
                    loopFlag = Status_flag.isNewComponent
                    list2report_newComponent.append([component, version])
                    createJSON(
                        svlid, "New Component", component, version, groupId
                    )
            break


"""
This is the function for adding status of all component and
versions to the report file.
"""


def addToReportFile():
    with open(reportFile, "a+") as f:
        # f.write(image)
        if list2report_inAlreadySVL:
            for item in list2report_inAlreadySVL:
                f.write(",%s , AlreadyInSVL\n" % item)
        if list2report_addCurrentSVL:
            for item in list2report_addCurrentSVL:
                f.write(",%s , Reuse \n" % item)
        if list2report_differentVersion:
            for item in list2report_differentVersion:
                f.write(",%s, Different version \n" % item)
        if list2report_olderVersion:
            for item in list2report_olderVersion:
                f.write(",%s, Older version \n" % item)
        if list2report_newVersion:
            for item in list2report_newVersion:
                f.write(",%s, NewVersion \n" % item)
        if list2report_newComponent:
            for item in list2report_newComponent:
                f.write(",%s, NewComponent \n" % item)
        if list2report_updateLink:
            for item in list2report_updateLink:
                f.write(",%s, Update Link \n" % item)


"""
This is main function which defines whole flow of script of
3PP Automation and it reads requirement file, generate report
and writes the component details to the report depending on
the status of the element.
"""
if __name__ == "__main__":
    urllib3.disable_warnings()
    read_sentRequestFile()
    svlid = str(sys.argv[2])
    svlid = svlid.split("#", 1)[1]
    # svlid = "8494"
    userid = str(sys.argv[3])
    # userid = "esignum"
    image = str(sys.argv[4])
    token = str(sys.argv[5])
    # token = "XXXXXXX"
    my_list = listSentRequest
    listSentRequest = []
    for i in my_list:
        i = i[:-1]
        listSentRequest.append(i)
    # readRequirement()
    readRequirement_txt()
    query_svl(userid, token, svlid)
    for element in pairs:
        process_thread(element)
    addToReportFile()
    with open(sentRequestFile, "w") as f:
        if listSentRequest:
            for item in listSentRequest:
                f.write("%s\n" % item)
