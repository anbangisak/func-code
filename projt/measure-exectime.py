import pandas as pd
import numpy as np
import datetime

def str_to_date_obj(strObj):
  print(dir(strObj))
  if(strObj.endswith("Z")):
    return datetime.strptime(strObj, '%Y-%m-%dT%H:%M:%S.%fZ')
  else:
    return datetime.strptime(strObj, '%Y-%m-%d %H:%M:%S.%f%z')

def diffInTimeObj(dateObj1, dateObj2):
  duration = str_to_date_obj(dateObj1)-str_to_date_obj(dateObj2)
  return duration.microseconds

def isTargetExecTimeHigh(strObj1, strObj2):
  print(strObj1)
  dateObj1 = str_to_date_obj(strObj1)
  dateObj2 = str_to_date_obj(strObj2)
  return dateObj1 >= dateObj2

def numpy_where(df):
  
  # targetTimeVsActReqTime TTvsART TgtExec_time
#   return df.assign(TTvsART=np.where(df['TgtExec_time'] >= df['Exec_time'], df['TgtExec_time']-df['Exec_time'], df['Exec_time']-df['TgtExec_time']))
    return df.assign(TTvsART=np.where(df['Exec_time'] >= df['TgtExec_time'], df['Exec_time']-df['TgtExec_time'], pd.NA))

def list_comp(df):
  return df.assign(TTvsART=['yes' if x >= 50 else 'no' for x in df['salary']])

filename = "records-log/records.log"
# filename = "records-log/single-cli.log"
jsonRdr = pd.read_json(filename, lines=True, chunksize=3000, convert_dates=True, date_unit="ns", keep_default_dates=True)
df = pd.DataFrame()
df = pd.concat(jsonRdr)
columnNames = ['Url', 'Client', 'Exec_time', 'TgtExec_time', 'TTvsART']
# df.to_csv("rec.csv", columns=columnNames)
# df = df.head(3)
# print(df["Client"])
# filtered_values = np.where(df['Url'].str.endswith('-0.ts') | df['Url'].str.endswith('-1.ts'))
# date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f%z')
filtered_values = np.where(df['Url'].str.endswith('.ts'))
print(filtered_values)
outputfile = "rec1.csv"
df = df.loc[filtered_values]
df['TgtExec_time']= pd.to_datetime(df['TgtExec_time'], format='ISO8601')
# df['TgtExec_time']= pd.to_datetime(df['TgtExec_time'], format='%Y-%m-%dT%H:%M:%S.%f%z')
df['Exec_time']= pd.to_datetime(df['Exec_time'], format='ISO8601')
df = numpy_where(df)
df.to_csv(outputfile, columns=columnNames, encoding='utf8')
# print(df.loc[filtered_values].head(500))
# df = df.loc[filtered_values].head(500)
# for url in df['Url']:
#     print(url)

# print(df[['Url', 'Client', 'Exec_time']])
# df1 = df(columns=['Url', 'Client', 'Exec_time'])
