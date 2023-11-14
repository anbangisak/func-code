#/usr/bin/python3
valList = [1, 7, 8, 12, 13, 27]
filVal = filter(lambda val: val>10, valList)
print(list(filVal))