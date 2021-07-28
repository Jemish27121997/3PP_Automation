# 3PP_Automation
This is the Automation scripts to register 3rd Party Product in Bazaar Internal
Use Below Commands

## First Create all necessary files in local ( you can always modify path),
addToSVLFile = "/tmp/3pp_automation/reportFiles/addToSVL.csv"
requestDataFile = "/tmp/3pp_automation/reportFiles/requestData.json"
reportFile = "/tmp/3pp_automation/reportFiles/report.csv"
svlFile = "/tmp/3pp_automation/reportFiles/svl.csv"
sentRequestFile = "/tmp/3pp_automation/reportFiles/sentRequest.csv"

## Then, run this to generate report and json file, (Modify according to need)
```sh
python 3pp_java.py CAS-c '#11306' epagjem CAS-c 82dd5b4
python 3pp_java.py <SVLname> ‘<SVLID>’ <username> <projectname> <token>
```

## Then, run this to submit into Bazaar,
```sh
python requestJson.py Cas-c '#11306' epagjem 82ddbb4
python requestJson.py <SVLname> ‘<SVLID>’ <username> <token>
```
